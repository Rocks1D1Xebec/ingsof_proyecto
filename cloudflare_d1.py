"""
cloudflare_d1.py
────────────────
Funciones para conectarse a Cloudflare D1 (Base de datos SQLite)
mediante la API REST de Cloudflare.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Credenciales de Cloudflare D1 desde las variables de entorno
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
DATABASE_ID = os.getenv("CLOUDFLARE_DATABASE_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


def ejecutar_sql(sql: str, params: list | None = None) -> list[dict]:
    """Ejecuta una consulta SQL en Cloudflare D1 y devuelve una lista con los resultados."""
    if not ACCOUNT_ID or not DATABASE_ID or not API_TOKEN:
        return []

    cuerpo = {"sql": sql}
    if params:
        cuerpo["params"] = params

    try:
        respuesta = requests.post(BASE_URL, headers=HEADERS, json=cuerpo, timeout=15)
        datos = respuesta.json()

        if not datos.get("success"):
            print("Aviso Cloudflare D1:", datos.get("errors"))
            return []

        resultado = datos.get("result", [])
        if resultado and "results" in resultado[0]:
            return resultado[0]["results"]
        return []
    except Exception as e:
        print(f"Error de conexión con Cloudflare D1: {e}")
        return []


def _tiene_columna(tabla: str, columna: str) -> bool:
    """Verifica si una columna ya existe (evita el ruido 'duplicate column' en D1)."""
    try:
        filas = ejecutar_sql(f"PRAGMA table_info({tabla})")
        return any(f.get("name") == columna for f in filas)
    except Exception:
        return True  # ante la duda, no intentar el ALTER


def asegurar_inicializacion():
    """Crea las tablas y materias base automáticamente si aún no existen."""
    try:
        # 1. Crear tablas
        ejecutar_sql("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                contrasena TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        ejecutar_sql("""
            CREATE TABLE IF NOT EXISTS materias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                usuario_id INTEGER,
                es_base INTEGER DEFAULT 0
            )
        """)
        # Migración aditiva para D1 viva: materias privadas por usuario
        # (solo si falta la columna; ejecutar_sql no lanza excepción, solo avisa)
        for _col, _sql_mig in (
            ("usuario_id", "ALTER TABLE materias ADD COLUMN usuario_id INTEGER"),
            ("es_base", "ALTER TABLE materias ADD COLUMN es_base INTEGER DEFAULT 0"),
        ):
            if not _tiene_columna("materias", _col):
                ejecutar_sql(_sql_mig)
        ejecutar_sql("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                materia_id INTEGER,
                contenido TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        ejecutar_sql("""
            CREATE TABLE IF NOT EXISTS respuestas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mensaje_id INTEGER,
                contenido TEXT NOT NULL,
                imagen_url TEXT,
                creado_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # Asegurar columna imagen_url si la tabla ya existía
        if not _tiene_columna("respuestas", "imagen_url"):
            ejecutar_sql("ALTER TABLE respuestas ADD COLUMN imagen_url TEXT")

        ejecutar_sql("""
            CREATE TABLE IF NOT EXISTS ejercicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia_id INTEGER,
                enunciado TEXT NOT NULL,
                respuesta_correcta TEXT NOT NULL,
                explicacion TEXT
            )
        """)
        ejecutar_sql("""
            CREATE TABLE IF NOT EXISTS respuestas_ejercicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ejercicio_id INTEGER,
                usuario_id INTEGER,
                respuesta_enviada TEXT NOT NULL,
                es_correcta INTEGER DEFAULT 0,
                feedback TEXT,
                respuesta_correcta TEXT,
                creado_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        ejecutar_sql("""
            CREATE TABLE IF NOT EXISTS perfiles_aprendizaje (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL UNIQUE,
                estilo TEXT DEFAULT '',
                creado_en TEXT NOT NULL DEFAULT (datetime('now')),
                actualizado_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        ejecutar_sql("""
            CREATE TABLE IF NOT EXISTS nivel_usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                materia_id INTEGER NOT NULL,
                nivel TEXT DEFAULT 'basico',
                prompt_nivel TEXT DEFAULT '',
                total_mensajes INTEGER DEFAULT 0,
                intentos INTEGER DEFAULT 0,
                aciertos INTEGER DEFAULT 0,
                actualizado_en TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(usuario_id, materia_id)
            )
        """)

        # 2. Insertar materias base si no existen (globales: usuario_id NULL + es_base=1)
        materias = ejecutar_sql("SELECT COUNT(*) as total FROM materias WHERE es_base = 1")
        total = materias[0]["total"] if materias else 0
        if total == 0:
            materias_base = [
                ("Matemáticas", "Álgebra, Geometría, Aritmética"),
                ("Física", "Fuerzas, Velocidad, Energía, MRUV"),
                ("Química", "Elementos, Reacciones, Enlaces"),
                ("Lenguaje", "Gramática, Lectura, Ortografía"),
            ]
            for nombre, desc in materias_base:
                existe = ejecutar_sql("SELECT id FROM materias WHERE nombre = ? AND es_base = 1", [nombre])
                if not existe:
                    ejecutar_sql(
                        "INSERT INTO materias (nombre, descripcion, usuario_id, es_base) VALUES (?, ?, NULL, 1)",
                        [nombre, desc],
                    )
                else:
                    ejecutar_sql("UPDATE materias SET es_base = 1 WHERE nombre = ?", [nombre])

        # 3. Insertar usuario inicial si no existe
        usuarios = ejecutar_sql("SELECT COUNT(*) as total FROM usuarios")
        total_u = usuarios[0]["total"] if usuarios else 0
        if total_u == 0:
            ejecutar_sql("INSERT INTO usuarios (id, nombre, email, contrasena) VALUES (1, 'Estudiante', 'estudiante@colegio.com', '1234')")
    except Exception as err:
        print("Aviso al asegurar inicialización:", err)


# =====================================================================
# FUNCIONES DE USUARIOS
# =====================================================================
def crear_usuario(nombre: str, email: str, contrasena: str) -> dict | None:
    """Registra un nuevo estudiante en la base de datos."""
    sql = """
        INSERT INTO usuarios (nombre, email, contrasena)
        VALUES (?, ?, ?)
        RETURNING id, nombre, email
    """
    filas = ejecutar_sql(sql, [nombre, email, contrasena])
    return filas[0] if filas else None


def buscar_usuario_por_email(email: str) -> dict | None:
    """Busca un usuario por su correo."""
    sql = "SELECT id, nombre, email, contrasena FROM usuarios WHERE email = ?"
    filas = ejecutar_sql(sql, [email])
    return filas[0] if filas else None


# =====================================================================
# FUNCIONES DE MATERIAS
# =====================================================================
def obtener_materias(usuario_id: int | None = None) -> list[dict]:
    """Obtiene las materias visibles para un usuario: 4 base globales + sus privadas.

    Filtra en SQL cuando la D1 viva ya tiene las columnas migradas; si la
    migración aún no corrió, cae al comportamiento anterior sin romper.
    """
    try:
        if usuario_id is not None:
            filas = ejecutar_sql(
                """SELECT id, nombre, descripcion FROM materias
                   WHERE es_base = 1 OR usuario_id = ? ORDER BY id ASC""",
                [usuario_id],
            )
        else:
            filas = ejecutar_sql(
                "SELECT id, nombre, descripcion FROM materias WHERE es_base = 1 ORDER BY id ASC"
            )
        if filas:
            return filas
    except Exception:
        pass
    # Fallback (D1 sin migrar o vacía): materias base en memoria
    return [
        {"id": 1, "nombre": "Matemáticas", "descripcion": "Álgebra, Geometría, Aritmética"},
        {"id": 2, "nombre": "Física", "descripcion": "Fuerzas, Velocidad, Energía, MRUV"},
        {"id": 3, "nombre": "Química", "descripcion": "Elementos, Reacciones, Enlaces"},
        {"id": 4, "nombre": "Lenguaje", "descripcion": "Gramática, Lectura, Ortografía"},
    ]


def crear_materia(nombre: str, descripcion: str = "", usuario_id: int | None = None) -> dict | None:
    """Crea una materia PRIVADA del usuario (usuario_id NOT NULL, es_base=0)."""
    sql = """
        INSERT INTO materias (nombre, descripcion, usuario_id, es_base)
        VALUES (?, ?, ?, 0)
        RETURNING id, nombre, descripcion
    """
    filas = ejecutar_sql(sql, [nombre, descripcion, usuario_id])
    return filas[0] if filas else None


def materia_visible_para(materia_id: int, usuario_id: int | None) -> bool:
    """Verifica que una materia sea base global o privada del usuario."""
    try:
        filas = ejecutar_sql("SELECT es_base, usuario_id FROM materias WHERE id = ?", [materia_id])
        if not filas:
            # Materia base por defecto (IDs 1-4) si la D1 aún no migró
            return int(materia_id) in (1, 2, 3, 4)
        fila = filas[0]
        if fila.get("es_base") == 1:
            return True
        return usuario_id is not None and fila.get("usuario_id") == usuario_id
    except Exception:
        return int(materia_id) in (1, 2, 3, 4)


# =====================================================================
# FUNCIONES DE MENSAJES Y CHAT
# =====================================================================
def guardar_mensaje(usuario_id: int, materia_id: int, contenido: str) -> dict | None:
    """Guarda la pregunta del estudiante de forma segura."""
    try:
        sql = """
            INSERT INTO mensajes (usuario_id, materia_id, contenido)
            VALUES (?, ?, ?)
            RETURNING id, usuario_id, materia_id, contenido
        """
        filas = ejecutar_sql(sql, [usuario_id, materia_id, contenido])
        return filas[0] if filas else None
    except Exception:
        return None


def guardar_respuesta(mensaje_id: int, contenido: str, imagen_url: str | None = None) -> dict | None:
    """Guarda la respuesta de la IA (incluyendo la imagen si generó una) de forma segura."""
    try:
        sql = """
            INSERT INTO respuestas (mensaje_id, contenido, imagen_url)
            VALUES (?, ?, ?)
            RETURNING id, mensaje_id, contenido, imagen_url
        """
        filas = ejecutar_sql(sql, [mensaje_id, contenido, imagen_url])
        return filas[0] if filas else None
    except Exception:
        # Fallback en caso de que la tabla aún no tenga la columna
        try:
            sql_fallback = """
                INSERT INTO respuestas (mensaje_id, contenido)
                VALUES (?, ?)
                RETURNING id, mensaje_id, contenido
            """
            filas = ejecutar_sql(sql_fallback, [mensaje_id, contenido])
            return filas[0] if filas else None
        except Exception:
            return None


def obtener_historial(usuario_id: int, materia_id: int, limite: int = 20) -> list[dict]:
    """Obtiene el historial de conversación de la materia."""
    try:
        sql = """
            SELECT m.id as mensaje_id, m.contenido as pregunta,
                   r.contenido as respuesta, r.imagen_url as imagen_url, m.creado_en
            FROM mensajes m
            LEFT JOIN respuestas r ON r.mensaje_id = m.id
            WHERE m.usuario_id = ? AND m.materia_id = ?
            ORDER BY m.creado_en DESC
            LIMIT ?
        """
        filas = ejecutar_sql(sql, [usuario_id, materia_id, limite])
        filas.reverse()
        return filas
    except Exception:
        return []



# =====================================================================
# PERFIL DE APRENDIZAJE (RF-12: técnica por asociación)
# =====================================================================
def obtener_perfil(usuario_id: int) -> str:
    """Devuelve el estilo de aprendizaje del estudiante ('' si no lo definió)."""
    try:
        filas = ejecutar_sql(
            "SELECT estilo FROM perfiles_aprendizaje WHERE usuario_id = ?", [usuario_id]
        )
        return (filas[0].get("estilo") or "") if filas else ""
    except Exception:
        return ""


def guardar_perfil(usuario_id: int, estilo: str) -> dict | None:
    """Crea o actualiza el perfil de aprendizaje (editable en cualquier momento)."""
    estilo = (estilo or "").strip()[:500]
    try:
        filas = ejecutar_sql(
            "SELECT id FROM perfiles_aprendizaje WHERE usuario_id = ?", [usuario_id]
        )
        if filas:
            ejecutar_sql(
                """UPDATE perfiles_aprendizaje
                   SET estilo = ?, actualizado_en = datetime('now')
                   WHERE usuario_id = ?""",
                [estilo, usuario_id],
            )
        else:
            ejecutar_sql(
                "INSERT INTO perfiles_aprendizaje (usuario_id, estilo) VALUES (?, ?)",
                [usuario_id, estilo],
            )
        return {"usuario_id": usuario_id, "estilo": estilo}
    except Exception:
        return None


# =====================================================================
# NIVEL POR MATERIA (RF-11 deducido + RF-13 progreso guardado)
# =====================================================================
def obtener_nivel(usuario_id: int, materia_id: int) -> dict:
    """Devuelve (y crea si falta) la fila de nivel de una materia."""
    try:
        filas = ejecutar_sql(
            """SELECT nivel, prompt_nivel, total_mensajes, intentos, aciertos
               FROM nivel_usuario WHERE usuario_id = ? AND materia_id = ?""",
            [usuario_id, materia_id],
        )
        if filas:
            return filas[0]
        ejecutar_sql(
            """INSERT INTO nivel_usuario (usuario_id, materia_id)
               VALUES (?, ?)""",
            [usuario_id, materia_id],
        )
    except Exception:
        pass
    return {"nivel": "basico", "prompt_nivel": "", "total_mensajes": 0,
            "intentos": 0, "aciertos": 0}


def sumar_mensaje_nivel(usuario_id: int, materia_id: int) -> int:
    """Incrementa el contador de mensajes; devuelve el total actual."""
    try:
        obtener_nivel(usuario_id, materia_id)  # asegura la fila
        ejecutar_sql(
            """UPDATE nivel_usuario SET total_mensajes = total_mensajes + 1,
               actualizado_en = datetime('now')
               WHERE usuario_id = ? AND materia_id = ?""",
            [usuario_id, materia_id],
        )
        fila = obtener_nivel(usuario_id, materia_id)
        return int(fila.get("total_mensajes", 0))
    except Exception:
        return 0


def sumar_revision_nivel(usuario_id: int, materia_id: int | None, es_correcta: bool) -> None:
    """Suma intentos/aciertos de práctica (RF-13). Sin materia, no hace nada."""
    if not materia_id:
        return
    try:
        obtener_nivel(usuario_id, materia_id)
        ejecutar_sql(
            """UPDATE nivel_usuario
               SET intentos = intentos + 1,
                   aciertos = aciertos + ?,
                   actualizado_en = datetime('now')
               WHERE usuario_id = ? AND materia_id = ?""",
            [1 if es_correcta else 0, usuario_id, materia_id],
        )
    except Exception:
        pass


def actualizar_nivel(usuario_id: int, materia_id: int, nivel: str, prompt_nivel: str) -> None:
    """Guarda el nivel recalculado por la IA cada 20 mensajes."""
    try:
        ejecutar_sql(
            """UPDATE nivel_usuario SET nivel = ?, prompt_nivel = ?,
               actualizado_en = datetime('now')
               WHERE usuario_id = ? AND materia_id = ?""",
            [nivel, (prompt_nivel or "")[:1000], usuario_id, materia_id],
        )
    except Exception:
        pass


# =====================================================================
# FUNCIONES DE EJERCICIOS Y PRÁCTICAS
# =====================================================================
def guardar_ejercicio(materia_id: int, enunciado: str, respuesta_correcta: str, explicacion: str = "") -> dict | None:
    """Guarda un ejercicio generado por la IA."""
    try:
        sql = """
            INSERT INTO ejercicios (materia_id, enunciado, respuesta_correcta, explicacion)
            VALUES (?, ?, ?, ?)
            RETURNING id, materia_id, enunciado, respuesta_correcta
        """
        filas = ejecutar_sql(sql, [materia_id, enunciado, respuesta_correcta, explicacion])
        return filas[0] if filas else None
    except Exception:
        return None


def guardar_respuesta_ejercicio(ejercicio_id: int | None, usuario_id: int,
                                respuesta_enviada: str, es_correcta: bool,
                                feedback: str, respuesta_correcta: str = "") -> dict | None:
    """Guarda la revisión de un ejercicio (HU-08/HU-09, RF-09/RF-10).

    Requerido por `historias_usuario.md` y `basedatos.sql` (tabla
    `respuestas_ejercicios`). Se invoca desde `POST /api/revisar`.
    `ejercicio_id` puede ser None (ejercicio generado sin persistir);
    en ese caso se guarda igualmente con NULL para no perder el progreso.
    """
    try:
        sql = """
            INSERT INTO respuestas_ejercicios
                (ejercicio_id, usuario_id, respuesta_enviada, es_correcta, feedback, respuesta_correcta)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id, ejercicio_id, usuario_id, respuesta_enviada, es_correcta, feedback
        """
        filas = ejecutar_sql(sql, [
            ejercicio_id,
            usuario_id,
            respuesta_enviada,
            1 if es_correcta else 0,
            feedback,
            respuesta_correcta,
        ])
        return filas[0] if filas else None
    except Exception:
        return None
