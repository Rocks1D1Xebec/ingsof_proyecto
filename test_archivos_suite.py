"""
test_archivos_suite.py
──────────────────────
Suite de pruebas unitarias e integración para la gestión de archivos (Cloudflare R2 + D1).
Verifica:
- Seguridad y autenticación (401 en endpoints sin sesión)
- Validaciones de formato, extensiones permitidas, MIME types, magic bytes y tamaño (10MB)
- Aislamiento multiusuario (un usuario no puede ver, descargar ni eliminar archivos de otro)
- Sincronización entre D1 (metadatos) y R2 (objeto físico)
- Reversión/rollback en caso de fallo
- No regresión en endpoints preexistentes
"""

import io
import unittest
from unittest.mock import patch, MagicMock
from main import app

# `main.r2` y `cloudflare_r2` son el mismo objeto. Se parchea el módulo ya
# importado con patch.object en lugar de "main.r2.motivo_de_configuracion":
# la forma con punto y coma obliga a mock a resolver el nombre contra el
# importador, y con Python 3.11 eso puede chocar con el lock de importación
# y fallar de forma intermitente al resolver muchos parches seguidos.
import cloudflare_r2 as _cloudflare_r2

_MOTIVO_R2_REAL = _cloudflare_r2.motivo_de_configuracion
_SUBIR_R2_REAL = _cloudflare_r2.subir_archivo


def _parche_r2_configurado():
    """Parche de R2 'operativo', para probar el camino de éxito."""
    return patch.object(_cloudflare_r2, "motivo_de_configuracion", return_value="")

class TestGestionArchivos(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        # Por defecto las pruebas se ejecutan como si R2 estuviera operativo.
        # La configuración real se comprueba en su propio test y en
        # test_subida_devuelve_503_con_detalle_si_r2_no_esta_configurado.
        self._parche_r2_ok = _parche_r2_configurado()
        self._parche_r2_ok.start()
        self.addCleanup(self._parche_r2_ok.stop)

    # -------------------------------------------------------------
    # 1. Pruebas de Autenticación
    # -------------------------------------------------------------
    def test_subir_sin_autenticacion_retorna_401(self):
        data = {
            "archivo": (io.BytesIO(b"%PDF-1.4 test"), "test.pdf")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 401)
        self.assertFalse(res.get_json()["ok"])

    def test_listar_sin_autenticacion_retorna_401(self):
        res = self.client.get("/api/archivos")
        self.assertEqual(res.status_code, 401)
        self.assertFalse(res.get_json()["ok"])

    def test_descargar_sin_autenticacion_retorna_401(self):
        res = self.client.get("/api/archivos/1/descargar")
        self.assertEqual(res.status_code, 401)

    def test_eliminar_sin_autenticacion_retorna_401(self):
        res = self.client.delete("/api/archivos/1")
        self.assertEqual(res.status_code, 401)

    # -------------------------------------------------------------
    # 2. Validaciones de Entrada (Extensiones, Mimes, Magic Bytes)
    # -------------------------------------------------------------
    def test_subir_sin_archivo_retorna_400(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        res = self.client.post("/api/archivos/subir", data={}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("No se envió ningún archivo", res.get_json()["error"])

    def test_subir_extension_no_permitida_retorna_400(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {
            "archivo": (io.BytesIO(b"print('hack')"), "malicioso.py")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Extensión no permitida", res.get_json()["error"])

    def test_subir_mime_no_permitido_retorna_400(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {
            "archivo": (io.BytesIO(b"%PDF-1.4 test"), "doc.pdf", "text/plain")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Formato MIME no admitido", res.get_json()["error"])

    def test_subir_archivo_vacio_retorna_400(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {
            "archivo": (io.BytesIO(b""), "vacio.pdf", "application/pdf")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("vacío", res.get_json()["error"])

    def test_magic_bytes_invalidos_en_pdf_retorna_400(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {
            "archivo": (io.BytesIO(b"NO_SOY_UN_PDF_REAL"), "falso.pdf", "application/pdf")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("no corresponde a un PDF", res.get_json()["error"])

    def test_magic_bytes_invalidos_en_png_retorna_400(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {
            "archivo": (io.BytesIO(b"NO_SOY_PNG"), "falso.png", "image/png")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("no corresponde a un PNG", res.get_json()["error"])

    def test_limite_tamano_mayor_a_10mb_retorna_413(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        # Generar un PDF ficticio que exceda 10MB
        diez_mb_mas_uno = 10 * 1024 * 1024 + 100
        contenido_pesado = b"%PDF-1.4 " + (b"0" * diez_mb_mas_uno)
        data = {
            "archivo": (io.BytesIO(contenido_pesado), "gigante.pdf", "application/pdf")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        # 413 es el código correcto para "el cuerpo de la petición es demasiado grande".
        # 400 se acepta porque el servidor web puede cortar la petición antes.
        self.assertIn(res.status_code, (400, 413))

    # -------------------------------------------------------------
    # 3. Flujo Exitoso de Subida (Formatos soportados)
    # -------------------------------------------------------------
    @patch("main.r2.subir_archivo")
    @patch("main.db.guardar_archivo")
    def test_subir_pdf_valido_exitoso(self, mock_d1_guardar, mock_r2_subir):
        mock_r2_subir.return_value = True
        mock_d1_guardar.return_value = {
            "id": 101,
            "usuario_id": 1,
            "materia_id": 2,
            "nombre_original": "guia.pdf",
            "r2_key": "usuarios/1/test-uuid.pdf",
            "mime_type": "application/pdf",
            "extension": "pdf",
            "tamano_bytes": 1024,
            "creado_en": "2026-09-28 22:00:00"
        }
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1

        data = {
            "archivo": (io.BytesIO(b"%PDF-1.4 encabezado correcto"), "guia.pdf", "application/pdf"),
            "materia_id": "2"
        }
        # La validación de materia es estricta y propia del módulo de archivos
        # (`_materia_asociable`), no la permisiva que usan chat y ejercicios.
        with patch("main._materia_asociable", return_value=True) as mock_materia:
            res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")

        self.assertEqual(res.status_code, 201)
        json_data = res.get_json()
        self.assertTrue(json_data["ok"])
        self.assertEqual(json_data["archivo"]["id"], 101)
        self.assertTrue(mock_r2_subir.called)
        self.assertTrue(mock_d1_guardar.called)
        # El nombre que se guarda debe ser el que se muestra, con acentos intactos.
        self.assertEqual(
            mock_d1_guardar.call_args.kwargs["nombre_original"], "guia.pdf"
        )
        # La materia se valida antes de tocar R2.
        mock_materia.assert_called_once_with(2, 1)

    @patch("main.r2.subir_archivo")
    @patch("main.db.guardar_archivo")
    def test_subir_png_valido_exitoso(self, mock_d1_guardar, mock_r2_subir):
        mock_r2_subir.return_value = True
        mock_d1_guardar.return_value = {
            "id": 102,
            "usuario_id": 1,
            "nombre_original": "captura.png"
        }
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        data = {
            "archivo": (io.BytesIO(png_bytes), "captura.png", "image/png")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.get_json()["ok"])

    @patch("main.r2.subir_archivo")
    @patch("main.db.guardar_archivo")
    def test_subir_jpg_valido_exitoso(self, mock_d1_guardar, mock_r2_subir):
        mock_r2_subir.return_value = True
        mock_d1_guardar.return_value = {"id": 103}
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1

        jpg_bytes = b"\xff\xd8\xff" + b"\x00" * 50
        data = {
            "archivo": (io.BytesIO(jpg_bytes), "foto.jpg", "image/jpeg")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 201)

    @patch("main.r2.subir_archivo")
    @patch("main.db.guardar_archivo")
    def test_subir_webp_valido_exitoso(self, mock_d1_guardar, mock_r2_subir):
        mock_r2_subir.return_value = True
        mock_d1_guardar.return_value = {"id": 104}
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1

        webp_bytes = b"RIFF\x20\x00\x00\x00WEBP" + b"\x00" * 30
        data = {
            "archivo": (io.BytesIO(webp_bytes), "esquema.webp", "image/webp")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 201)

    # -------------------------------------------------------------
    # 4. Rollback en caso de fallo en D1
    # -------------------------------------------------------------
    @patch("main.r2.subir_archivo")
    @patch("main.r2.eliminar_archivo")
    @patch("main.db.guardar_archivo")
    def test_falla_d1_hace_rollback_en_r2(self, mock_d1_guardar, mock_r2_eliminar, mock_r2_subir):
        mock_r2_subir.return_value = True
        # D1 falla y retorna None
        mock_d1_guardar.return_value = None

        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1

        data = {
            "archivo": (io.BytesIO(b"%PDF-1.4 prueba"), "doc.pdf", "application/pdf")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 500)
        self.assertTrue(mock_r2_eliminar.called, "Debe llamar a eliminar_archivo en R2 para evitar huérfanos")

    # -------------------------------------------------------------
    # 5. Listar Archivos y Filtro por Materia
    # -------------------------------------------------------------
    @patch("main.db.obtener_archivos")
    def test_listar_archivos_usuario(self, mock_db_obtener):
        mock_db_obtener.return_value = [
            {"id": 1, "nombre_original": "guia1.pdf", "usuario_id": 5},
            {"id": 2, "nombre_original": "ejercicios.jpg", "usuario_id": 5}
        ]
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 5

        res = self.client.get("/api/archivos?materia_id=3")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["archivos"]), 2)
        mock_db_obtener.assert_called_with(5, 3)

    # -------------------------------------------------------------
    # 6. Aislamiento Multiusuario en Descarga
    # -------------------------------------------------------------
    @patch("main.db.obtener_archivo_por_id")
    def test_descargar_archivo_ajeno_retorna_404(self, mock_db_archivo):
        # Usuario 2 intenta acceder a archivo de Usuario 1; db.obtener_archivo_por_id valida usuario_id y da None
        mock_db_archivo.return_value = None

        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 2

        res = self.client.get("/api/archivos/99/descargar")
        self.assertEqual(res.status_code, 404)
        self.assertIn("no tienes permisos", res.get_json()["error"])

    @patch("main.db.obtener_archivo_por_id")
    @patch("main.r2.obtener_archivo")
    def test_descargar_archivo_propio_exitoso(self, mock_r2_obtener, mock_db_archivo):
        mock_db_archivo.return_value = {
            "id": 10,
            "usuario_id": 3,
            "r2_key": "usuarios/3/archivo.pdf",
            "nombre_original": "tesis.pdf",
            "mime_type": "application/pdf"
        }
        mock_stream = MagicMock()
        mock_stream.iter_chunks.return_value = [b"%PDF-1.4 contenido de prueba"]
        mock_r2_obtener.return_value = {
            "body": mock_stream,
            "content_type": "application/pdf",
            "content_length": 28
        }

        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 3

        res = self.client.get("/api/archivos/10/descargar?descargar=1")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"%PDF-1.4 contenido de prueba")
        self.assertIn('attachment; filename="tesis.pdf"', res.headers.get("Content-Disposition", ""))

    # -------------------------------------------------------------
    # 7. Aislamiento Multiusuario y Flujo de Eliminación
    # -------------------------------------------------------------
    @patch("main.db.obtener_archivo_por_id")
    def test_eliminar_archivo_ajeno_retorna_404(self, mock_db_archivo):
        mock_db_archivo.return_value = None

        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 2

        res = self.client.delete("/api/archivos/50")
        self.assertEqual(res.status_code, 404)

    @patch("main.r2.esta_configurado", return_value=True)
    @patch("main.db.obtener_archivo_por_id")
    @patch("main.r2.eliminar_archivo")
    @patch("main.db.eliminar_archivo_db")
    def test_eliminar_archivo_propio_exitoso(self, mock_db_del, mock_r2_del, mock_db_archivo, _mock_conf):
        mock_db_archivo.return_value = {
            "id": 50,
            "usuario_id": 2,
            "r2_key": "usuarios/2/foto.png"
        }
        mock_r2_del.return_value = True
        mock_db_del.return_value = True

        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 2

        res = self.client.delete("/api/archivos/50")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["ok"])
        mock_r2_del.assert_called_with("usuarios/2/foto.png")
        mock_db_del.assert_called_with(50, 2)

    # -------------------------------------------------------------
    # 8. Pruebas directas de cloudflare_r2
    # -------------------------------------------------------------
    def test_r2_generar_key_segura(self):
        import cloudflare_r2 as r2_mod
        key = r2_mod.generar_key_segura(42, ".pdf")
        self.assertTrue(key.startswith("usuarios/42/"))
        self.assertTrue(key.endswith(".pdf"))
        self.assertNotIn("..", key)

    def test_r2_esta_configurado(self):
        import cloudflare_r2 as r2_mod
        with patch.dict("os.environ", {
            "R2_BUCKET_NAME": "test-bucket",
            "R2_ACCESS_KEY_ID": "test-key",
            "R2_SECRET_ACCESS": "test-secret",
            "R2_ENDPOINT": "https://test.r2.cloudflarestorage.com"
        }):
            self.assertTrue(r2_mod.esta_configurado())

    @patch("main.r2.subir_archivo", return_value=False)
    def test_fallo_r2_retorna_502(self, mock_subir):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {
            "archivo": (io.BytesIO(b"%PDF-1.4 prueba"), "doc.pdf", "application/pdf")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 502)
        self.assertIn("Cloudflare R2", res.get_json()["error"])

    @patch("main.r2.subir_archivo", return_value=True)
    @patch("main.db.guardar_archivo")
    def test_subir_gif_valido_exitoso(self, mock_d1_guardar, mock_r2_subir):
        mock_d1_guardar.return_value = {"id": 105}
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        gif_bytes = b"GIF89a" + b"\x00" * 30
        data = {
            "archivo": (io.BytesIO(gif_bytes), "animacion.gif", "image/gif")
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 201)

    # -------------------------------------------------------------
    # 9. No Regresión en Rutas Preexistentes
    # -------------------------------------------------------------
    def test_login_endpoint_sigue_activo(self):
        res = self.client.post("/api/login", json={})
        self.assertEqual(res.status_code, 400)

    def test_historial_sin_sesion_sigue_retornando_401(self):
        res = self.client.get("/api/historial")
        self.assertEqual(res.status_code, 401)


# =====================================================================
# PRUEBAS DE LAS CORRECCIONES
# =====================================================================
class TestCorreccionesArchivos(unittest.TestCase):
    """
    Cubre los problemas detectados en la revisión de la implementación:

    - límite de 10 MB aplicado solo a la subida (sin regresión en el resto);
    - nombre original con acentos conservado, r2_key siempre con UUID;
    - validación estricta de `materia_id`;
    - contador por materia sin archivos de otras materias;
    - coherencia R2/D1 al subir y al borrar;
    - reacción ante respuestas inesperadas de la API de D1.
    """

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        # Igual que en TestGestionArchivos: el camino de éxito se prueba con R2
        # dado por operativo. El caso "no configurado" tiene su propio test.
        self._parche_r2_ok = _parche_r2_configurado()
        self._parche_r2_ok.start()
        self.addCleanup(self._parche_r2_ok.stop)
    # -------------------------------------------------------------
    # 10. Límite de tamaño solo en la subida de archivos
    # -------------------------------------------------------------
    def test_limite_global_no_rompe_peticiones_grandes_de_otras_rutas(self):
        """
        Regresión corregida: con el límite global en 10 MB, /api/chat fallaba
        cuando el historial incluía imágenes en base64. El límite de archivo
        debe seguir existiendo, pero el global debe ser mayor.
        """
        import main as main_mod

        self.assertEqual(main_mod.TAMANO_MAXIMO_BYTES, 10 * 1024 * 1024)
        self.assertGreater(
            main_mod.app.config["MAX_CONTENT_LENGTH"],
            main_mod.TAMANO_MAXIMO_BYTES,
            "El límite global debe ser mayor que el de archivos para no affectar al chat",
        )

    def test_limite_de_10mb_se_aplica_a_la_subida(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        # 10 MB exactos de contenido + cabecera: supera el límite del módulo.
        contenido = b"%PDF-1.4 " + (b"0" * (10 * 1024 * 1024))
        data = {"archivo": (io.BytesIO(contenido), "grande.pdf", "application/pdf")}
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertIn(res.status_code, (400, 413))

    def test_chat_acepta_peticion_de_varios_megabytes(self):
        """
        /api/chat reenvía el historial, que puede incluir imágenes en base64.
        Con el antiguo límite global de 10 MB esta ruta quedaba bloqueada.
        """
        # Se desactiva TESTING para que una excepción dentro de la ruta se
        # convierta en un 500 y no en una excepción que corte la prueba: lo que
        # se comprueba aquí es que la petición NO se rechaza por tamaño.
        self.app.config["TESTING"] = False
        pregunta = "x" * (12 * 1024 * 1024)  # 12 MB: por encima del antiguo límite
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        with patch("main.db.guardar_mensaje", return_value={"id": 1}), \
             patch("main.db.obtener_historial", return_value=[]), \
             patch("main.db.obtener_perfil", return_value={}), \
             patch("main.db.obtener_nivel", return_value={"aciertos": 0, "intentos": 0, "nivel": "basico"}), \
             patch("main.db.sumar_mensaje_nivel", return_value=0), \
             patch("main.gemini.explicar_tema", return_value="Respuesta de prueba"):
            res = self.client.post("/api/chat", json={
                "pregunta": pregunta, "materia_id": 1, "materia_nombre": "Matemáticas"
            })
        # Lo relevante es que no se rechace por tamaño (413).
        self.assertNotEqual(res.status_code, 413)

    # -------------------------------------------------------------
    # 11. Nombre original con acentos
    # -------------------------------------------------------------
    def test_nombre_mostrable_conserva_acentos_y_espacios(self):
        import main as main_mod

        nombre = main_mod._nombre_mostrable("Tarea de Física — Guía 1.pdf", ".pdf", 7)
        self.assertEqual(nombre, "Tarea de Física — Guía 1.pdf")

    def test_nombre_mostrable_quita_rutas_y_caracteres_peligrosos(self):
        import main as main_mod

        # Intentos de traversal y de romper la cabecera de descarga.
        nombre = main_mod._nombre_mostrable('../../etc/passwd"mal.pdf', ".pdf", 7)
        self.assertNotIn("/", nombre)
        self.assertNotIn('"', nombre)
        self.assertNotIn("..", nombre)

    def test_nombre_mostrable_limpia_nombres_sin_contenido_util(self):
        import main as main_mod

        # Sin nada reconocible se cae al nombre genérico, conservando el formato.
        self.assertEqual(main_mod._nombre_mostrable("..", ".pdf", 7), "archivo_7.pdf")
        self.assertEqual(main_mod._nombre_mostrable("", ".pdf", 7), "archivo_7.pdf")
        self.assertEqual(main_mod._nombre_mostrable("   ", ".png", 7), "archivo_7.png")
        # Un nombre que solo era la extensión se queda sin el punto inicial,
        # que en la interfaz se vería como un archivo oculto.
        self.assertEqual(main_mod._nombre_mostrable('<<<>.pdf', ".pdf", 7), "pdf")

    @patch("main.r2.subir_archivo", return_value=True)
    @patch("main.db.guardar_archivo")
    def test_subida_conserva_acentos_y_no_usa_el_nombre_en_la_key(self, mock_d1, mock_subir):
        import main as main_mod

        mock_d1.return_value = {"id": 1}
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 3

        data = {"archivo": (io.BytesIO(b"%PDF-1.4 x"), "Examen de Física 2.pdf", "application/pdf")}
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 201)

        # Lo que se guarda para mostrar conserva el nombre del usuario.
        self.assertEqual(
            mock_d1.call_args.kwargs["nombre_original"], "Examen de Física 2.pdf"
        )
        # La clave de R2 se genera aparte con UUID: no depende del nombre.
        r2_key = mock_d1.call_args.kwargs["r2_key"]
        self.assertTrue(r2_key.startswith("usuarios/3/"))
        self.assertNotIn("Física", r2_key)
        self.assertNotIn(" ", r2_key)

    # -------------------------------------------------------------
    # 12. Validación estricta de materia_id
    # -------------------------------------------------------------
    @patch("main.r2.subir_archivo")
    @patch("main._materia_asociable", return_value=False)
    def test_materia_ajena_retorna_403_y_no_toca_r2(self, mock_materia, mock_subir):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {
            "archivo": (io.BytesIO(b"%PDF-1.4 x"), "guia.pdf", "application/pdf"),
            "materia_id": "99"
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 403)
        self.assertFalse(mock_subir.called, "No se debe subir nada si la materia no es válida")

    def test_materia_inexistente_es_rechazada(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        # Sin credenciales de D1 la comprobación estricta no puede confirmarse.
        data = {
            "archivo": (io.BytesIO(b"%PDF-1.4 x"), "guia.pdf", "application/pdf"),
            "materia_id": "5"
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 403)

    @patch("main.db.ejecutar_sql_estricto", return_value=[{"es_base": 1, "usuario_id": None}])
    def test_materia_base_si_es_asociable(self, _mock_sql):
        import main as main_mod

        self.assertTrue(main_mod._materia_asociable(1, 1))

    @patch("main.db.ejecutar_sql_estricto", return_value=[{"es_base": 0, "usuario_id": 77}])
    def test_materia_privada_de_otro_usuario_rechazada(self, _mock_sql):
        import main as main_mod

        self.assertFalse(main_mod._materia_asociable(4, 1))

    @patch("main.db.ejecutar_sql_estricto", return_value=[])
    def test_materia_inexistente_rechazada_en_estricto(self, _mock_sql):
        import main as main_mod

        self.assertFalse(main_mod._materia_asociable(4, 1))

    def test_materia_id_no_numerico_retorna_400(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {
            "archivo": (io.BytesIO(b"%PDF-1.4 x"), "guia.pdf", "application/pdf"),
            "materia_id": "no-es-un-numero"
        }
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)

    # -------------------------------------------------------------
    # 13. Contador por materia sin archivos ajenos
    # -------------------------------------------------------------
    def test_filtro_por_materia_es_estricto(self):
        """Los archivos con materia_id NULL no deben aparecer en el filtro."""
        import cloudflare_d1 as d1_mod

        capturado = {}

        def fake(sql, params=None):
            capturado["sql"] = " ".join(sql.split())
            capturado["params"] = params
            return []

        with patch.object(d1_mod, "ejecutar_sql", side_effect=fake):
            d1_mod.obtener_archivos(5, 3)

        self.assertIn("WHERE usuario_id = ? AND materia_id = ?", capturado["sql"])
        self.assertNotIn("IS NULL", capturado["sql"])
        self.assertEqual(capturado["params"], [5, 3])

    def test_listado_global_devuelve_todos_los_archivos(self):
        import cloudflare_d1 as d1_mod

        capturado = {}

        def fake(sql, params=None):
            capturado["sql"] = " ".join(sql.split())
            capturado["params"] = params
            return []

        with patch.object(d1_mod, "ejecutar_sql", side_effect=fake):
            d1_mod.obtener_archivos(5, None)

        self.assertIn("WHERE usuario_id = ?", capturado["sql"])
        self.assertNotIn("materia_id = ?", capturado["sql"])
        self.assertEqual(capturado["params"], [5])

    def test_materia_id_invalido_en_listado_retorna_400(self):
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        res = self.client.get("/api/archivos?materia_id=abc")
        self.assertEqual(res.status_code, 400)

    # -------------------------------------------------------------
    # 14. Coherencia R2 / D1
    # -------------------------------------------------------------
    @patch("main.r2.subir_archivo", return_value=True)
    @patch("main.r2.eliminar_archivo", return_value=True)
    @patch("main.db.guardar_archivo")
    def test_d1_falla_revierte_r2(self, mock_d1, mock_r2_del, _mock_subir):
        import cloudflare_d1 as d1_mod

        mock_d1.return_value = None  # INSERT no escrito
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {"archivo": (io.BytesIO(b"%PDF-1.4 x"), "guia.pdf", "application/pdf")}
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")

        self.assertEqual(res.status_code, 500)
        self.assertTrue(mock_r2_del.called, "Sin metadato en D1, el objeto de R2 debe revertirse")

    @patch("main.r2.subir_archivo", return_value=True)
    @patch("main.r2.eliminar_archivo", return_value=True)
    @patch("main.db.guardar_archivo")
    def test_d1_escrito_pero_no_verificado_no_borra_r2(self, mock_d1, mock_r2_del, _mock_subir):
        """
        Si el INSERT ocurrió pero no se pudo leer el id, el metadato YA existe en
        D1. Borrar el objeto de R2 dejaría un registro apuntando a nada.
        """
        import cloudflare_d1 as d1_mod

        mock_d1.side_effect = d1_mod.D1Error("no se pudo leer")
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1
        data = {"archivo": (io.BytesIO(b"%PDF-1.4 x"), "guia.pdf", "application/pdf")}
        res = self.client.post("/api/archivos/subir", data=data, content_type="multipart/form-data")

        self.assertEqual(res.status_code, 503)
        self.assertFalse(
            mock_r2_del.called,
            "No se debe borrar R2 si el metadato ya quedó escrito en D1",
        )

    @patch("main.r2.esta_configurado", return_value=True)
    @patch("main.r2.eliminar_archivo", return_value=False)
    @patch("main.db.eliminar_archivo_db")
    def test_si_r2_no_borra_conserva_el_metadato(self, mock_db_del, mock_r2_del, _mock_conf):
        """Si el objeto de R2 sobrevive, el registro debe sobrevivir para poder reintentar."""
        with patch("main.db.obtener_archivo_por_id", return_value={
            "id": 7, "usuario_id": 2, "r2_key": "usuarios/2/foto.png"
        }):
            with self.client.session_transaction() as sess:
                sess["usuario_id"] = 2
            res = self.client.delete("/api/archivos/7")

        self.assertEqual(res.status_code, 502)
        self.assertFalse(
            mock_db_del.called,
            "No se debe borrar el metadato si el objeto de R2 sigue existiendo",
        )

    @patch("main.r2.motivo_de_configuracion", return_value="")
    @patch.object(_cloudflare_r2, "eliminar_archivo", return_value=True)
    @patch("main.db.eliminar_archivo_db")
    def test_eliminar_borro_r2_y_luego_d1(self, mock_db_del, _mock_r2_del, _mock_conf):
        """Camino feliz: primero R2, después D1."""
        mock_db_del.return_value = True
        with patch("main.db.obtener_archivo_por_id", return_value={
            "id": 8, "usuario_id": 2, "r2_key": "usuarios/2/foto.png"
        }):
            with self.client.session_transaction() as sess:
                sess["usuario_id"] = 2
            res = self.client.delete("/api/archivos/8")

        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["ok"])
        self.assertNotIn("aviso", res.get_json())
        mock_db_del.assert_called_once_with(8, 2)

    @patch("main.db.obtener_archivo_por_id")
    @patch.object(_cloudflare_r2, "eliminar_archivo")
    @patch("main.db.eliminar_archivo_db")
    def test_sin_r2_configurado_el_borrado_conserva_el_registro(
        self, mock_db_del, mock_r2_del, mock_meta
    ):
        """
        Si R2 no está configurado NO se puede confirmar el borrado del objeto.
        Borrar el metadato dejaría un archivo huérfano en el bucket que nadie
        podría encontrar ni eliminar, así que el registro se conserva.
        """
        mock_meta.return_value = {
            "id": 8, "usuario_id": 2, "r2_key": "usuarios/2/foto.png"
        }
        motivo = (
            "Faltan configurar estas variables en el archivo .env, siguen con "
            "el valor de ejemplo de la plantilla: R2_BUCKET_NAME."
        )
        with patch.object(_cloudflare_r2, "motivo_de_configuracion", return_value=motivo):
            with self.client.session_transaction() as sess:
                sess["usuario_id"] = 2
            res = self.client.delete("/api/archivos/8")

        self.assertEqual(res.status_code, 503)
        cuerpo = res.get_json()
        self.assertFalse(cuerpo["ok"])
        self.assertIn("R2_BUCKET_NAME", cuerpo["detalle"])
        self.assertFalse(mock_r2_del.called, "No se intenta borrar sin configuración")
        self.assertFalse(
            mock_db_del.called,
            "El metadato NO debe borrarse si el objeto no se pudo eliminar",
        )

    # -------------------------------------------------------------
    # 15. Reacción ante respuestas inesperadas de la API de D1
    # -------------------------------------------------------------
    def test_guardar_archivo_devuelve_none_si_el_insert_falla(self):
        import cloudflare_d1 as d1_mod

        with patch.object(d1_mod, "ejecutar_sql_estricto", side_effect=d1_mod.D1Error("no such table: archivos")):
            resultado = d1_mod.guardar_archivo(1, "guia.pdf", "usuarios/1/x.pdf", "application/pdf", "pdf", 10, 1)

        self.assertIsNone(resultado, "Sin escritura se devuelve None para poder revertir R2")

    def test_guardar_archivo_reintenta_lectura_antes_de_render_error(self):
        """D1 puede responder la lectura desde una réplica con retraso."""
        import cloudflare_d1 as d1_mod

        respuestas = [d1_mod.D1Error("replica"), d1_mod.D1Error("replica")]

        def fake(sql, params=None):
            if sql.strip().upper().startswith("INSERT"):
                return []
            if respuestas:
                raise respuestas.pop(0)
            return []

        with patch.object(d1_mod, "ejecutar_sql_estricto", side_effect=fake), \
             patch.object(d1_mod.time, "sleep"):
            with self.assertRaises(d1_mod.D1Error):
                d1_mod.guardar_archivo(1, "guia.pdf", "usuarios/1/x.pdf", "application/pdf", "pdf", 10, 1)

    def test_guardar_archivo_usa_insert_y_select_por_r2_key(self):
        """No se depende de INSERT ... RETURNING: el id se lee con un SELECT."""
        import cloudflare_d1 as d1_mod

        llamadas = []

        def fake(sql, params=None):
            llamadas.append(" ".join(sql.split()))
            if sql.strip().upper().startswith("INSERT"):
                return []
            return [{"id": 42, "r2_key": "usuarios/1/x.pdf", "nombre_original": "guia.pdf"}]

        with patch.object(d1_mod, "ejecutar_sql_estricto", side_effect=fake):
            fila = d1_mod.guardar_archivo(1, "guia.pdf", "usuarios/1/x.pdf", "application/pdf", "pdf", 10, 1)

        self.assertEqual(fila["id"], 42)
        self.assertTrue(llamadas[0].upper().startswith("INSERT"))
        self.assertNotIn("RETURNING", llamadas[0].upper())
        self.assertIn("WHERE r2_key = ?", llamadas[1])

    def test_ejecutar_sql_estricto_propaga_error_de_d1(self):
        import cloudflare_d1 as d1_mod

        with patch.object(d1_mod, "ACCOUNT_ID", "cuenta"), \
             patch.object(d1_mod, "DATABASE_ID", "db"), \
             patch.object(d1_mod, "API_TOKEN", "token"):
            respuesta = MagicMock()
            respuesta.status_code = 200
            respuesta.json.return_value = {
                "success": False,
                "errors": [{"message": "table archivos already exists"}],
                "result": [],
            }
            with patch.object(d1_mod.requests, "post", return_value=respuesta):
                with self.assertRaises(d1_mod.D1Error) as ctx:
                    d1_mod.ejecutar_sql_estricto("SELECT 1")

        self.assertIn("already exists", str(ctx.exception))

    def test_ejecutar_sql_estricto_avisa_si_faltan_credenciales(self):
        import cloudflare_d1 as d1_mod

        with patch.object(d1_mod, "ACCOUNT_ID", None), \
             patch.object(d1_mod, "DATABASE_ID", None), \
             patch.object(d1_mod, "API_TOKEN", None):
            with self.assertRaises(d1_mod.D1Error):
                d1_mod.ejecutar_sql_estricto("SELECT 1")

    def test_ejecutar_sql_estricto_no_filtra_el_token_en_el_error(self):
        """El mensaje de error no debe filtrar credenciales."""
        import cloudflare_d1 as d1_mod

        with patch.object(d1_mod, "ACCOUNT_ID", "cuenta"), \
             patch.object(d1_mod, "DATABASE_ID", "db"), \
             patch.object(d1_mod, "API_TOKEN", "TOKEN-SECRETO-XYZ"):
            respuesta = MagicMock()
            respuesta.status_code = 200
            respuesta.json.return_value = {
                "success": False,
                "errors": [{"message": "D1_ERROR: near SELECT: syntax error"}],
                "result": [],
            }
            with patch.object(d1_mod.requests, "post", return_value=respuesta):
                with self.assertRaises(d1_mod.D1Error) as ctx:
                    d1_mod.ejecutar_sql_estricto("SELECT 1")

        self.assertNotIn("TOKEN-SECRETO-XYZ", str(ctx.exception))

    # -------------------------------------------------------------
    # 16. Coherencia del esquema entre los tres sitios
    # -------------------------------------------------------------
    def test_las_tres_definiciones_de_archivos_coinciden(self):
        """
        basedatos.sql, cloudflare_d1.SQL_TABLA_ARCHIVOS e init_db.py deben
        describing la misma tabla. Se compara contra basedatos.sql leído del disco.
        """
        import os
        import re
        import cloudflare_d1 as d1_mod

        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, "basedatos.sql"), encoding="utf-8") as f:
            sql = f.read()

        bloque = re.search(
            r"CREATE TABLE IF NOT EXISTS archivos(.*?);", sql, re.DOTALL
        )
        self.assertIsNotNone(bloque, "basedatos.sql debe seguir definiendo la tabla archivos")

        def normalizar(texto):
            return " ".join(texto.split())

        esperado = normalizar(bloque.group(1))
        compartido = normalizar(d1_mod.SQL_TABLA_ARCHIVOS)
        # La definición compartida no lleva el "IF NOT EXISTS" que usa el script.
        self.assertIn("ON DELETE CASCADE", esperado)
        self.assertIn("ON DELETE SET NULL", esperado)
        self.assertIn("ON DELETE CASCADE", compartido)
        self.assertIn("ON DELETE SET NULL", compartido)

        for columna in (
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "usuario_id INTEGER NOT NULL",
            "materia_id INTEGER",
            "nombre_original TEXT NOT NULL",
            "r2_key TEXT NOT NULL UNIQUE",
            "mime_type TEXT NOT NULL",
            "extension TEXT NOT NULL",
            "tamano_bytes INTEGER NOT NULL",
            "creado_en TEXT NOT NULL DEFAULT (datetime('now'))",
        ):
            self.assertIn(columna, esperado, f"Falta {columna} en basedatos.sql")
            self.assertIn(columna, compartido, f"Falta {columna} en la definición compartida")

    def test_init_db_importa_la_definicion_compartida(self):
        """init_db.py no debe volver a declarar la tabla por su cuenta."""
        import os

        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, "init_db.py"), encoding="utf-8") as f:
            contenido = f.read()

        self.assertIn("SQL_TABLA_ARCHIVOS", contenido)
        # Solo puede aparecer en el import y en la lista, nunca en un CREATE propio.
        self.assertEqual(contenido.count("CREATE TABLE IF NOT EXISTS archivos"), 0)

    def test_esquema_de_archivos_es_solo_metadatos(self):
        """D1 guarda referencia y tamaño, nunca el contenido del archivo."""
        import cloudflare_d1 as d1_mod

        esquema = d1_mod.SQL_TABLA_ARCHIVOS.lower()
        self.assertNotIn("blob", esquema)
        self.assertNotIn("base64", esquema)
        self.assertNotIn("contenido", esquema)
        self.assertIn("r2_key", esquema)
        self.assertIn("tamano_bytes", esquema)

    # -------------------------------------------------------------
    # 17. Seguridad del repositorio
    # -------------------------------------------------------------
    def test_gitignore_ignora_env_y_cache_pero_no_el_ejemplo(self):
        import os

        base = os.path.dirname(os.path.abspath(__file__))
        ruta_gitignore = os.path.join(base, ".gitignore")
        self.assertTrue(os.path.isfile(ruta_gitignore), "Falta .gitignore")

        with open(ruta_gitignore, encoding="utf-8") as f:
            reglas = [linea.strip() for linea in f]

        self.assertIn(".env", reglas)
        self.assertIn(".env.*", reglas)
        self.assertIn("__pycache__/", reglas)
        self.assertIn("*.py[cod]", reglas)
        self.assertIn("!.env.example", reglas)

    def test_env_example_no_contiene_secretos_reales(self):
        """
        La plantilla se versiona: debe documentar las variables sin valores reales.
        """
        import os
        import re

        base = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(base, ".env.example")
        self.assertTrue(os.path.isfile(ruta), "Falta .env.example")

        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()

        for variable in (
            "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS",
            "R2_ENDPOINT", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_DATABASE_ID",
            "CLOUDFLARE_API_TOKEN", "SECRET_KEY",
        ):
            self.assertIn(f"{variable}=", contenido, f"Falta documentar {variable}")

        # Ningún valor debe parecer una credencial real.
        for linea in contenido.splitlines():
            if "=" not in linea or linea.strip().startswith("#"):
                continue
            valor = linea.split("=", 1)[1].strip()
            self.assertTrue(
                valor == "" or "your-" in valor or valor.startswith("cambia-"),
                f"La plantilla no debe traer valores reales: {linea}",
            )
        # Un token de Cloudflare real es un JWT largo; el de ejemplo es corto.
        self.assertIsNone(re.search(r"eyJ[A-Za-z0-9_-]{20,}", contenido))

    def test_env_real_no_esta_versionado_en_git(self):
        """
        El `.env` real SÍ debe existir en local para poder probar: lo que no
        puede pasar es que acabe en el repositorio con las credenciales dentro.

        Por eso la comprobación correcta es "está ignorado por git", no
        "no existe".
        """
        import os
        import subprocess

        base = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(base, ".env")
        self.assertTrue(
            os.path.isfile(ruta),
            "Debería existir un .env local para poder probar contra Cloudflare",
        )

        # Ignorado por .gitignore
        ignorado = subprocess.run(
            ["git", "check-ignore", "-q", ".env"],
            cwd=base, capture_output=True,
        )
        self.assertEqual(
            ignorado.returncode, 0,
            ".env debe estar ignorado por .gitignore",
        )

        # Y tampoco debe estar ya versionado
        versionado = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env"],
            cwd=base, capture_output=True,
        )
        self.assertNotEqual(
            versionado.returncode, 0,
            ".env no debe estar versionado en el repositorio",
        )

    def test_env_example_si_se_versiona(self):
        """La plantilla sin secretos debe poder entrar en el repositorio."""
        import os
        import subprocess

        base = os.path.dirname(os.path.abspath(__file__))
        self.assertTrue(os.path.isfile(os.path.join(base, ".env.example")))

        ignorado = subprocess.run(
            ["git", "check-ignore", "-q", ".env.example"],
            cwd=base, capture_output=True,
        )
        self.assertNotEqual(
            ignorado.returncode, 0,
            ".env.example NO debe estar ignorado: hay que versionarlo",
        )

    # -------------------------------------------------------------
    # 18. Detección de credenciales sin rellenar
    # -------------------------------------------------------------
    def test_detector_reconoce_placeholders_de_la_plantilla(self):
        import credenciales as cfg

        for valor in (
            None, "", "   ", "your-bucket-name", "your-cloudflare-account-id",
            "cambia-esta-cadena-por-una-larga-y-aleatoria",
            "https://your-account-id.r2.cloudflarestorage.com",
            "'your-r2-access-key-id'",
        ):
            self.assertTrue(
                cfg.es_valor_de_ejemplo(valor),
                f"Debería detectar como placeholder: {valor!r}",
            )

    def test_detector_acepta_valores_reales(self):
        import credenciales as cfg

        for valor in (
            "eduasistente-archivos",
            "a1b2c3d4e5f6",
            "00000000aaaabbbbcccc0000111122223333",
            "https://9f8e7d6c5b4a.r2.cloudflarestorage.com",
        ):
            self.assertFalse(
                cfg.es_valor_de_ejemplo(valor),
                f"No debería marcar como placeholder: {valor!r}",
            )

    def test_faltantes_devuelve_solo_nombres(self):
        """El diagnóstico puede decir QUÉ falta, nunca el valor."""
        import credenciales as cfg

        faltantes = cfg.falta_alguna({
            "R2_BUCKET_NAME": "eduasistente-archivos",   # real
            "R2_ACCESS_KEY_ID": "your-r2-access-key-id", # ejemplo
            "R2_SECRET_ACCESS": "",                      # vacio
        })
        self.assertEqual(faltantes, ["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS"])

        mensaje = cfg.resumen_para_usuario({
            "R2_BUCKET_NAME": "eduasistente-archivos",
            "R2_ACCESS_KEY_ID": "your-r2-access-key-id",
        })
        self.assertIn("R2_ACCESS_KEY_ID", mensaje)
        # Ningún valor de ejemplo debe aparecer en el mensaje.
        self.assertNotIn("your-r2-access-key-id", mensaje)
        self.assertNotIn("eduasistente-archivos", mensaje)

    def test_r2_no_se_considera_configurado_con_placeholders(self):
        """Un .env sin rellenar no debe dar por operativo el almacenamiento."""
        import cloudflare_r2 as r2_mod

        with patch.dict("os.environ", {
            "R2_BUCKET_NAME": "your-bucket-name",
            "R2_ACCESS_KEY_ID": "your-r2-access-key-id",
            "R2_SECRET_ACCESS": "your-r2-secret-access-key",
            "R2_ENDPOINT": "https://your-account-id.r2.cloudflarestorage.com",
        }, clear=False):
            # `esta_configurado` no está parcheado en setUp, así que es la
            # función real y lee estos valores de ejemplo.
            self.assertFalse(r2_mod.esta_configurado())
            # `motivo_de_configuracion` sí está parcheado, de ahí la copia real.
            self.assertIn("R2_BUCKET_NAME", _MOTIVO_R2_REAL())

    def test_subida_devuelve_503_con_detalle_si_r2_no_esta_configurado(self):
        """El error debe decir qué falta, no un 502 genérico."""
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1

        motivo = (
            "Faltan configurar estas variables en el archivo .env, siguen con "
            "el valor de ejemplo de la plantilla: R2_BUCKET_NAME."
        )
        with patch.object(_cloudflare_r2, "motivo_de_configuracion", return_value=motivo), \
             patch.object(_cloudflare_r2, "subir_archivo") as mock_subir, \
             patch("main.db.guardar_archivo") as mock_d1:
            data = {"archivo": (io.BytesIO(b"%PDF-1.4 x"), "guia.pdf", "application/pdf")}
            res = self.client.post("/api/archivos/subir", data=data,
                                   content_type="multipart/form-data")

        self.assertEqual(res.status_code, 503)
        cuerpo = res.get_json()
        self.assertFalse(cuerpo["ok"])
        self.assertIn("R2_BUCKET_NAME", cuerpo["detalle"])
        # No debe intentarse ni subir a R2 ni escribir en D1
        self.assertFalse(mock_subir.called)
        self.assertFalse(mock_d1.called)

    def test_subida_devuelve_502_si_r2_falla_de_verdad(self):
        """Con R2 configurado pero caido, el error es 502 (reintentable)."""
        with self.client.session_transaction() as sess:
            sess["usuario_id"] = 1

        with patch.object(_cloudflare_r2, "motivo_de_configuracion", return_value=""), \
             patch.object(_cloudflare_r2, "subir_archivo", return_value=False):
            data = {"archivo": (io.BytesIO(b"%PDF-1.4 x"), "guia.pdf", "application/pdf")}
            res = self.client.post("/api/archivos/subir", data=data,
                                   content_type="multipart/form-data")

        self.assertEqual(res.status_code, 502)
        self.assertFalse(res.get_json()["ok"])


# =====================================================================
# PRUEBAS DE INTEGRACIÓN REAL (no se ejecutan sin credenciales)
# =====================================================================
# Estas NO forman parte de `python test_archivos_suite.py`. Requieren un
# bucket de R2 y una base D1configured, y dejan objetos reales, por lo que
# deben lanzarse a mano y con cuidado.
#
#   1. Crear un bucket de R2 y copiar .env.example a .env con los valores
#      reales de la cuenta de Cloudflare.
#   2. En la consola SQL de D1 confirmar que existe la tabla `archivos`
#      (la crea `asegurar_inicializacion` al arrancar la app).
#   3. Ejecutar el guion de abajo con la sesión iniciada.
#
# Lo que NO se puede comprobar con la suite unitaria, y que conviene
# verificar al menos una vez contra los servicios reales:
#
#   * que la API REST de D1 acepte el INSERT y el SELECT por `r2_key`
#     (esto ya no depende de `INSERT ... RETURNING`);
#   * que `PRAGMA foreign_key_list` y la migración de `archivos` se comporten
#     bien sobre una tabla creada sin FOREIGN KEY;
#   * que el objeto aparezca en el bucket con el `Content-Type` correcto;
#   * que la descarga por streaming devuelva el archivo intacto;
#   * que borrar el usuario en D1 (ON DELETE CASCADE) quite el metadato y que
#     el objeto de R2 quede fuera de esa cascada: es una limitación
#     conocida, el objeto hay que borrarlo desde el panel de R2.
#
# class TestIntegracionReal(unittest.TestCase):
#     def test_ciclo_completo_subir_listar_descargar_borrar(self):
#         ...  # usar app.test_client() con sesión real, sin mocks de R2 ni D1
#     pass


if __name__ == "__main__":
    unittest.main()
