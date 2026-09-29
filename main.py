"""
main.py
-------
Servidor principal del Asistente Escolar (EduAsistente).
Hecho con Flask, conectado a Cloudflare D1 (Base de datos SQLite)
y a la API de Google Gemini (Inteligencia Artificial).

Sin librerías complejas de cifrado para mantener el código simple,
educativo y fácil de entender.
"""

import os
from flask import Flask, Response, jsonify, request, send_file, send_from_directory, session
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

import cloudflare_d1 as db
import cloudflare_r2 as r2
import gemini_helper as gemini

# Cargar variables del archivo .env
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
# Llave secreta para manejar las sesiones en el navegador
app.secret_key = os.getenv("SECRET_KEY", "mi_clave_secreta_escolar_123")

# Límite global de petición: es una red de seguridad para que ninguna ruta
# pueda agotar la memoria del proceso, NO el límite del módulo de archivos.
#
# El límite real de 10 MB por archivo se aplica SOLO en
# POST /api/archivos/subir (ver TAMANO_MAXIMO_BYTES más abajo). Antes esta
# variable valía 10 MB para toda la app, lo que rompía endpoints que sí
# necesitan peticiones grandes: /api/chat reenvía el historial, y ese
# historial incluye `respuestas.imagen_url`, que puede ser un data URL
# generado por Gemini. Ese valor de 32 MB deja margen de sobra para el
# chat, la generación de imágenes, los esquemas y el audio verbalizado.
LIMITE_MAXIMO_PETICION_BYTES = 32 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = LIMITE_MAXIMO_PETICION_BYTES

# Asegurar tablas y materias base en Cloudflare D1
db.asegurar_inicializacion()


# =====================================================================
# RUTAS PARA SERVIR LAS PÁGINAS WEB (HTML, CSS, JS)
# =====================================================================
@app.route("/")
def index():
    """Página de inicio (redirige a login si no hay sesión)."""
    return send_file(os.path.join(BASE_DIR, "index.html"))


@app.route("/<path:filename>")
def servir_archivos(filename):
    """Permite abrir archivos .html, .css y .js directamente."""
    ruta = os.path.join(BASE_DIR, filename)
    if os.path.isfile(ruta):
        return send_from_directory(BASE_DIR, filename)
    return "Archivo no encontrado", 404


@app.route("/api/modelos", methods=["GET"])
def api_modelos():
    """Consulta y devuelve los modelos de Gemini disponibles para tu API Key."""
    modelos = gemini.obtener_lista_modelos_activos()
    return jsonify({"ok": True, "total": len(modelos), "modelos": modelos})


# =====================================================================
# AUTENTICACIÓN SIMPLE (REGISTRO, LOGIN, SESIÓN, LOGOUT)
# =====================================================================
@app.route("/api/register", methods=["POST"])
def api_register():
    """Registra un nuevo usuario guardando nombre, correo y contraseña."""
    data = request.get_json() or {}
    nombre = data.get("nombre", "").strip()
    email = data.get("email", "").strip().lower()
    contrasena = data.get("contrasena", "").strip()

    # Validaciones básicas
    if not nombre or not email or not contrasena:
        return jsonify({"ok": False, "error": "Por favor completa todos los campos"}), 400

    if not email.endswith("@gmail.com"):
        return jsonify({"ok": False, "error": "El correo debe terminar en @gmail.com"}), 400

    # Verificar si el correo ya existe
    existente = db.buscar_usuario_por_email(email)
    if existente:
        return jsonify({"ok": False, "error": "Este correo ya está registrado"}), 400

    # Crear el usuario con contraseña hasheada (RNF-05, estándar werkzeug con sal)
    usuario = db.crear_usuario(nombre, email, generate_password_hash(contrasena))
    if not usuario:
        return jsonify({"ok": False, "error": "No se pudo registrar el usuario"}), 500

    # Iniciar sesión automáticamente
    session["usuario_id"] = usuario["id"]
    session["usuario_nombre"] = usuario["nombre"]

    return jsonify({
        "ok": True,
        "mensaje": "¡Registro exitoso!",
        "usuario": {
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "email": email
        }
    }), 201


@app.route("/api/login", methods=["POST"])
def api_login():
    """Inicia sesión verificando el hash de la contraseña (RNF-05)."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    contrasena = data.get("contrasena", "").strip()

    if not email or not contrasena:
        return jsonify({"ok": False, "error": "Por favor ingresa tu correo y contraseña"}), 400

    usuario = db.buscar_usuario_por_email(email)
    if not usuario:
        return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos"}), 401

    # Verificar hash (con compatibilidad para cuentas viejas en texto plano:
    # si coincide en plano, se migra al hash automáticamente)
    guardada = usuario.get("contrasena", "")
    if guardada != contrasena and not check_password_hash(guardada, contrasena):
        return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos"}), 401
    if guardada == contrasena:
        try:
            db.ejecutar_sql("UPDATE usuarios SET contrasena = ? WHERE id = ?",
                            [generate_password_hash(contrasena), usuario["id"]])
        except Exception:
            pass

    # Guardar en sesión
    session["usuario_id"] = usuario["id"]
    session["usuario_nombre"] = usuario["nombre"]

    return jsonify({
        "ok": True,
        "mensaje": "¡Bienvenido!",
        "usuario": {
            "id": usuario["id"],
            "nombre": usuario["nombre"]
        }
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Cierra la sesión del usuario."""
    session.clear()
    return jsonify({"ok": True, "mensaje": "Sesión cerrada correctamente"})


@app.route("/api/sesion", methods=["GET"])
def api_sesion():
    """Verifica si el usuario tiene sesión activa."""
    uid = session.get("usuario_id")
    if not uid:
        return jsonify({"autenticado": False}), 401

    return jsonify({
        "autenticado": True,
        "usuario": {
            "id": uid,
            "nombre": session.get("usuario_nombre", "Estudiante")
        }
    })


# =====================================================================
# MATERIAS (OBTENER Y CREAR)
# =====================================================================
@app.route("/api/materias", methods=["GET"])
def api_materias_listar():
    """Devuelve las materias visibles: 4 base globales + privadas del usuario."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401
    materias = db.obtener_materias(int(usuario_id))
    return jsonify({"ok": True, "materias": materias})


@app.route("/api/materias", methods=["POST"])
def api_materias_crear():
    """Crea una materia PRIVADA del usuario autenticado."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401

    data = request.get_json() or {}
    nombre = data.get("nombre", "").strip()
    descripcion = data.get("descripcion", "").strip()

    if not nombre:
        return jsonify({"ok": False, "error": "El nombre de la materia es obligatorio"}), 400

    materia = db.crear_materia(nombre, descripcion, int(usuario_id))
    if not materia:
        return jsonify({"ok": False, "error": "No se pudo crear la materia"}), 500

    return jsonify({"ok": True, "materia": materia}), 201


# =====================================================================
# PERFIL DE APRENDIZAJE (RF-12)
# =====================================================================
@app.route("/api/perfil", methods=["GET"])
def api_perfil_obtener():
    """Devuelve el estilo de aprendizaje del usuario."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401
    return jsonify({"ok": True, "estilo": db.obtener_perfil(int(usuario_id))})


@app.route("/api/perfil", methods=["PUT"])
def api_perfil_guardar():
    """Guarda el estilo de aprendizaje (opcional, editable siempre)."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401
    data = request.get_json() or {}
    guardado = db.guardar_perfil(int(usuario_id), data.get("estilo", ""))
    if not guardado:
        return jsonify({"ok": False, "error": "No se pudo guardar"}), 500
    return jsonify({"ok": True, "estilo": guardado["estilo"]})


# =====================================================================
import re
import cloudflare_ai as cf_ai

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Recibe la duda del estudiante y responde con IA paso a paso, generando imágenes cuando sea necesario."""
    data = request.get_json() or {}
    pregunta = data.get("pregunta", "").strip()
    materia_id = data.get("materia_id")
    materia_nombre = data.get("materia_nombre", "General").strip()

    if not pregunta:
        return jsonify({"ok": False, "error": "Debes escribir una pregunta"}), 400

    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401
    usuario_id = int(usuario_id)

    try:
        materia_id = int(materia_id or 1)
    except (TypeError, ValueError):
        materia_id = 1
    if not db.materia_visible_para(materia_id, usuario_id):
        return jsonify({"ok": False, "error": "Materia no disponible para tu cuenta"}), 403

    # 1. Guardar la pregunta en la base de datos
    mensaje = db.guardar_mensaje(usuario_id, materia_id, pregunta)

    # 2. Obtener historial previo para darle contexto a la IA
    historial = db.obtener_historial(usuario_id, materia_id, limite=6)

    # 2b. Personalización RF-11/RF-12/RF-13: perfil + nivel + progreso real
    perfil = db.obtener_perfil(usuario_id)
    nivel_info = db.obtener_nivel(usuario_id, materia_id)
    stats = (f"- {materia_nombre}: {nivel_info.get('aciertos', 0)}/"
             f"{nivel_info.get('intentos', 0)} ejercicios correctos, "
             f"nivel {nivel_info.get('nivel', 'basico')}.")
    total_msgs = db.sumar_mensaje_nivel(usuario_id, materia_id)

    # 3. Consultar a Gemini para obtener la respuesta explicada paso a paso
    respuesta_ia = gemini.explicar_tema(
        pregunta, materia_nombre, historial,
        perfil=perfil,
        prompt_nivel=nivel_info.get("prompt_nivel", ""),
        nivel=nivel_info.get("nivel", "basico"),
        stats=stats,
    )

    # 3b. Recalibrar nivel cada 20 mensajes (1 llamada IA barata)
    if total_msgs and total_msgs % 20 == 0:
        try:
            historial_amp = db.obtener_historial(usuario_id, materia_id, limite=20)
            ev = gemini.evaluar_nivel(
                materia_nombre, historial_amp,
                intentos=int(nivel_info.get("intentos", 0)),
                aciertos=int(nivel_info.get("aciertos", 0)),
            )
            db.actualizar_nivel(usuario_id, materia_id, ev["nivel"], ev["prompt_nivel"])
        except Exception:
            pass

    # 4. Modo solo-manual: no se genera imagen automática en el chat.
    # Si Gemini incluyó [IMAGEN_EDUCATIVA: ...] se retira del texto; la imagen
    # solo se genera cuando el estudiante pulsa "Ver ilustración" (/api/ilustrar),
    # que re-analiza pregunta+respuesta con el modo Preciso/Creativo elegido.
    img_data_url = None
    patron_imagen = r"\[IMAGEN_EDUCATIVA:\s*(.*?)\]"
    respuesta_ia = re.sub(patron_imagen, "", respuesta_ia, flags=re.IGNORECASE)

    # 5. Guardar la respuesta en la base de datos:
    #    contenido = texto limpio (sin base64 embebido), imagen_url = columna separada
    if mensaje and "id" in mensaje:
        db.guardar_respuesta(mensaje["id"], respuesta_ia, img_data_url)


    return jsonify({
        "ok": True,
        "respuesta": respuesta_ia,
        "imagen_url": img_data_url,
        "advertencia": "Contenido generado por IA, puede contener errores. Verifica con tu libro o profe.",
    })


@app.route("/api/ilustrar", methods=["POST"])
def api_ilustrar():
    """Genera bajo demanda una ilustración con re-análisis (modo Preciso/Creativo).

    Espera {pregunta, respuesta, materia_nombre, modo}. Re-analiza la explicación
    con Gemini para crear un prompt visual coherente y genera con Cloudflare AI.
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401

    data = request.get_json() or {}
    modo = (data.get("modo") or "preciso").lower()
    if modo not in ("preciso", "creativo"):
        modo = "preciso"
    pregunta = (data.get("pregunta") or "").strip()[:500]
    respuesta = (data.get("respuesta") or "").strip()[:4000]
    materia_nombre = (data.get("materia_nombre") or "General").strip()
    # Compatibilidad con el cliente antiguo: tema/texto sueltos
    if not respuesta:
        respuesta = (data.get("texto") or data.get("tema") or "").strip()[:4000]
    if not pregunta:
        pregunta = (data.get("tema") or "")[:500]
    if not (pregunta or respuesta):
        return jsonify({"ok": False, "error": "Indica un tema para ilustrar"}), 400

    try:
        plan = gemini.generar_prompt_imagen(pregunta, respuesta, materia_nombre, modo)
    except Exception as err:
        print("Aviso re-analizador imagen:", err)
        plan = {"prompt_en": (pregunta or respuesta[:200]), "etiquetas": [],
                "estilo": "lineal" if modo == "preciso" else "ilustrativo"}

    try:
        img = cf_ai.generar_imagen_educativa(plan.get("prompt_en", "")[:500], modo=modo)
    except Exception as err:
        print("Aviso imagen manual:", err)
        img = None
    if img and len(img) > 700_000:
        img = None
    if not img:
        return jsonify({"ok": False, "error": "No se pudo generar la imagen en este momento"}), 502
    return jsonify({
        "ok": True,
        "imagen_url": img,
        "modo": modo,
        "prompt_en": plan.get("prompt_en", ""),
        "etiquetas": plan.get("etiquetas", []),
        "estilo": plan.get("estilo", ""),
        "advertencia": ("Esquema aproximado generado por IA, no a escala. "
                        "La IA puede equivocarse en imágenes y texto: verifica con tu libro o profe."),
    })


@app.route("/api/esquema", methods=["POST"])
def api_esquema():
    """Devuelve etiquetas para el esquema de texto (sin generar imagen IA).

    El frontend dibuja un SVG determinista con letras reales.
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401
    data = request.get_json() or {}
    pregunta = (data.get("pregunta") or "").strip()[:500]
    respuesta = (data.get("respuesta") or "").strip()[:4000]
    materia_nombre = (data.get("materia_nombre") or "General").strip()
    if not (pregunta or respuesta):
        return jsonify({"ok": False, "error": "Indica un tema"}), 400
    try:
        plan = gemini.generar_prompt_imagen(pregunta, respuesta, materia_nombre, "preciso")
    except Exception as err:
        print("Aviso esquema:", err)
        plan = {"prompt_en": pregunta or respuesta[:200], "etiquetas": [], "estilo": "lineal"}
    etiquetas = plan.get("etiquetas") or []
    if not etiquetas:
        # Fallback: iniciales de la pregunta como etiquetas legibles
        palabras = [p for p in __import__("re").sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ ]", " ", pregunta).split() if len(p) > 2][:3]
        etiquetas = [(p[0] or "A").upper() for p in palabras] or ["A", "B"]
    return jsonify({"ok": True, "etiquetas": etiquetas[:5],
                    "prompt_en": plan.get("prompt_en", "")})


@app.route("/api/audio-verbalizado", methods=["POST"])
def api_audio_verbalizado():
    """Convierte el contenido del mensaje a texto fonético y natural para ser leído en voz alta.

    Transforma fórmulas matemáticas (raíces, fracciones, potencias), químicas y símbolos
    a palabras habladas fluidas usando Gemini o reglas deterministas especializadas.
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401

    data = request.get_json() or {}
    texto = (data.get("texto") or "").strip()
    materia_nombre = (data.get("materia_nombre") or "General").strip()

    if not texto:
        return jsonify({"ok": False, "error": "No hay texto para verbalizar"}), 400

    texto_hablado = gemini.verbalizar_para_audio(texto, materia_nombre)
    return jsonify({
        "ok": True,
        "texto_hablado": texto_hablado
    })



@app.route("/api/historial", methods=["GET"])
def api_historial():
    """Devuelve las preguntas y respuestas anteriores de una materia."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401

    try:
        materia_id = int(request.args.get("materia_id", 1))
    except (TypeError, ValueError):
        materia_id = 1
    if not db.materia_visible_para(materia_id, int(usuario_id)):
        return jsonify({"ok": False, "error": "Materia no disponible para tu cuenta"}), 403

    historial = db.obtener_historial(int(usuario_id), materia_id, limite=20)
    return jsonify({"ok": True, "historial": historial})


# =====================================================================
# PRÁCTICA Y EJERCICIOS (GENERACIÓN Y REVISIÓN)
# =====================================================================
@app.route("/api/ejercicio", methods=["POST"])
def api_ejercicio():
    """Genera un ejercicio práctico con Gemini (con tema contextual o general)."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401

    data = request.get_json() or {}
    materia_nombre = data.get("materia_nombre", "General")
    tema = data.get("tema", "").strip()
    try:
        materia_id = int(data.get("materia_id", 1))
    except (TypeError, ValueError):
        materia_id = 1
    if not db.materia_visible_para(materia_id, int(usuario_id)):
        return jsonify({"ok": False, "error": "Materia no disponible para tu cuenta"}), 403

    # Generar con Gemini (tema contextual o general HU-07 + perfil/nivel RF-11/12)
    perfil_ej = db.obtener_perfil(int(usuario_id))
    nivel_ej = db.obtener_nivel(int(usuario_id), materia_id)
    ejercicio = gemini.generar_ejercicio(
        materia_nombre, tema,
        perfil=perfil_ej,
        prompt_nivel=nivel_ej.get("prompt_nivel", ""),
        nivel=nivel_ej.get("nivel", "basico"),
    )

    # Guardar en base de datos
    guardado = db.guardar_ejercicio(
        materia_id,
        ejercicio["enunciado"],
        ejercicio["respuesta_correcta"],
        ejercicio.get("explicacion", "")
    )

    # Persistir en el historial de chat para que aparezca al salir y volver
    texto_solicitud = f"🎯 Practicar: {tema}" if tema else "🎯 Ejercicio de práctica"
    msg_chat = db.guardar_mensaje(int(usuario_id), materia_id, texto_solicitud)
    if msg_chat:
        texto_resp = f"**📝 Ejercicio de Práctica:**\n\n{ejercicio['enunciado']}"
        db.guardar_respuesta(msg_chat["id"], texto_resp)

    # Si es respaldo (la IA falló), exponer el detalle en el log y al frontend
    # para diagnosticar. El frontend lo muestra en console.log.
    explicacion = str(ejercicio.get("explicacion", ""))
    es_respaldo = explicacion.startswith("Detalle:")
    if es_respaldo:
        print(f"Aviso /api/ejercicio respaldo para '{materia_nombre}' tema='{tema[:80]}': {explicacion[:300]}")

    return jsonify({
        "ok": True,
        "ejercicio": {
            "id": guardado["id"] if guardado else None,
            "enunciado": ejercicio["enunciado"],
            "respuesta_correcta": ejercicio["respuesta_correcta"]
        },
        "respaldo": es_respaldo,
        "detalle": explicacion if es_respaldo else ""
    })


@app.route("/api/revisar", methods=["POST"])
def api_revisar():
    """Revisa la respuesta del estudiante, la guarda (HU-08/HU-09) y devuelve feedback."""
    data = request.get_json() or {}
    enunciado = data.get("enunciado", "")
    respuesta_estudiante = data.get("respuesta", "")
    respuesta_correcta = data.get("respuesta_correcta", "")
    materia_nombre = data.get("materia_nombre", "General")
    ejercicio_id = data.get("ejercicio_id")
    try:
        materia_id_rev = int(data.get("materia_id")) if data.get("materia_id") else None
    except (TypeError, ValueError):
        materia_id_rev = None

    if not respuesta_estudiante:
        return jsonify({"ok": False, "error": "Debes ingresar tu respuesta"}), 400

    # Normalizar ejercicio_id (el frontend puede enviar "" cuando no se persistió)
    try:
        ejercicio_id = int(ejercicio_id) if ejercicio_id not in (None, "") else None
    except (TypeError, ValueError):
        ejercicio_id = None

    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401

    # Revisar con Gemini
    evaluacion = gemini.revisar_respuesta(enunciado, respuesta_estudiante, respuesta_correcta, materia_nombre)

    # Persistir la revisión (tabla respuestas_ejercicios + contadores RF-13)
    es_ok = bool(evaluacion.get("es_correcta", False))
    revision = db.guardar_respuesta_ejercicio(
        ejercicio_id,
        int(usuario_id),
        respuesta_estudiante,
        es_ok,
        evaluacion.get("feedback", ""),
        respuesta_correcta,
    )
    if materia_id_rev and db.materia_visible_para(materia_id_rev, int(usuario_id)):
        db.sumar_revision_nivel(int(usuario_id), materia_id_rev, es_ok)

    # Persistir en el historial de chat
    msg_rev = db.guardar_mensaje(int(usuario_id), materia_id_rev or 1, f"Mi respuesta: {respuesta_estudiante}")
    if msg_rev:
        icono_res = "✅ **¡Excelente trabajo!**" if es_ok else "⚠️ **Revisemos juntos:**"
        texto_feedback = f"{icono_res}\n\n{evaluacion.get('feedback', '')}"
        db.guardar_respuesta(msg_rev["id"], texto_feedback)

    return jsonify({
        "ok": True,
        "es_correcta": evaluacion["es_correcta"],
        "feedback": evaluacion["feedback"],
        "revision_id": revision["id"] if revision else None,
    })


# =====================================================================
# GESTIÓN DE ARCHIVOS (CLOUDFLARE R2 + CLOUDFLARE D1)
# =====================================================================
EXTENSIONES_PERMITIDAS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"}
MIME_TYPES_PERMITIDOS = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "application/pdf"
}
# Límite del módulo de archivos. Se aplica solo en POST /api/archivos/subir.
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB

# Firmas binarias (magic bytes) admitidas por extensión. Evita que un
# ejecutable o un script se suba disfrazado de imagen o PDF.
FIRMAS_POR_EXTENSION = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    # WEBP: "RIFF" al inicio y "WEBP" en los bytes 8-11.
    ".webp": (b"RIFF",),
}
PREFIJOS_ESPECIALES = {".webp": (8, b"WEBP")}

# Caracteres que no deben viajar en un nombre de archivo.
_CARACTERES_PROHIBIDOS_EN_NOMBRE = '"<>|:*?'


def _nombre_mostrable(nombre_bruto: str, ext: str, usuario_id: int) -> str:
    """
    Limpia el nombre que eligió el usuario para poder MOSTRARLO, conservando
    acentos, espacios y mayúsculas.

    No se usa para construir la clave en R2: esa la genera
    `r2.generar_key_segura()` con un UUID, así que un nombre con
    acentos no afecta en absoluto a la seguridad del almacenamiento.

    Se eliminan las carpetas del camino, los caracteres de control y los
    símbolos que romperían la cabecera `Content-Disposition` de la descarga.
    """
    # Normaliza separadores de Windows y POSIX y se queda con el nombre final.
    base = os.path.basename(str(nombre_bruto).replace("\\", "/")).strip()
    # isprintable() ya descarta \r y \n y el resto de caracteres de control.
    base = "".join(c for c in base if c.isprintable())
    base = "".join(c for c in base if c not in _CARACTERES_PROHIBIDOS_EN_NOMBRE)
    base = base.strip()

    # Se quitan los puntos iniciales: un nombre que empieza por punto se
    # mostraría como un archivo oculto y no aporta nada ("<<<>.pdf" -> "pdf").
    base = base.lstrip(".")

    # Si no queda un nombre reconocible, se usa el genérico conservando la
    # extensión, para que el usuario siga viendo de qué formato se trata.
    if not base or not os.path.splitext(base)[0].strip("._- "):
        return f"archivo_{usuario_id}{ext}"

    # 180 caracteres de sobra para el nombre; el nombre NO es la clave en R2.
    if len(base) > 180:
        base = base[:180].strip()
    return base


def _firma_valida(contenido: bytes, ext: str) -> bool:
    """
    Comprueba que los primeros bytes correspondan al formato declarado.

    Los formatos sin firma especial (PNG, JPEG, GIF, PDF) solo comparan el
    prefijo. El WEBP es el caso aparte: empieza por "RIFF" y lleva "WEBP" en los
    bytes 8-11, así que se comprueba en dos sitios.
    """
    firmas = FIRMAS_POR_EXTENSION.get(ext)
    if not firmas:
        return True
    if not any(contenido.startswith(firma) for firma in firmas):
        return False
    # Comprobación adicional del WEBP: "WEBP" va en los bytes 8-11.
    posicion, esperado = PREFIJOS_ESPECIALES.get(ext, (None, None))
    if posicion is not None:
        return contenido[posicion:posicion + len(esperado)] == esperado
    return True


def _materia_asociable(materia_id: int, usuario_id: int) -> bool:
    """
    Verificación estricta de la materia a la que se asocia un archivo.

    `db.materia_visible_para` es permisiva a propósito: si D1 no responde,
    deja pasar las materias base 1-4 para no cortar el chat ni los ejercicios.
    Para asociar un archivo no se hereda esa permisividad: se exige que la
    materia exista de verdad y sea visible para el usuario, y ante la duda se
    rechaza en lugar de guardar un archivo en una materia ajena.
    """
    try:
        filas = db.ejecutar_sql_estricto(
            "SELECT es_base, usuario_id FROM materias WHERE id = ?", [materia_id]
        )
    except db.D1Error as error:
        print(f"[D1] No se pudo validar la materia {materia_id} para un archivo: {error}")
        return False

    if not filas:
        return False
    materia = filas[0]
    if materia.get("es_base") == 1:
        return True
    return materia.get("usuario_id") == usuario_id


@app.errorhandler(413)
def request_entity_too_large(error):
    """
    Respuesta cuando la petición supera el límite global del proceso.

    Se distingue el caso de una subida de archivos para poder dar el mensaje
    correcto en lugar de un error genérico.
    """
    es_subida = request.path.rstrip("/").endswith("/api/archivos/subir")
    if es_subida:
        return jsonify({
            "ok": False,
            "error": "El archivo excede el tamaño máximo permitido de 10 MB"
        }), 413
    return jsonify({
        "ok": False,
        "error": "La petición es demasiado grande para el servidor"
    }), 413


@app.route("/api/archivos/subir", methods=["POST"])
def api_archivos_subir():
    """
    Sube un archivo (imagen o PDF) a Cloudflare R2 y registra sus metadatos en Cloudflare D1.
    Valida extensión, MIME type, tamaño y magic bytes en el backend.
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión para subir archivos"}), 401
    usuario_id = int(usuario_id)

    if "archivo" not in request.files:
        return jsonify({"ok": False, "error": "No se envió ningún archivo en la petición"}), 400

    archivo = request.files["archivo"]
    if not archivo or not archivo.filename:
        return jsonify({"ok": False, "error": "Nombre de archivo inválido o vacío"}), 400

    nombre_bruto = archivo.filename
    _, ext = os.path.splitext(nombre_bruto.lower())

    # 0. Rechazo temprano por el tamaño declarado en la petición, antes de
    #    leer el archivo en memoria. El límite real se vuelve a comprobar abajo
    #    sobre los bytes leídos, que es el dato fiable.
    if request.content_length and request.content_length > TAMANO_MAXIMO_BYTES:
        return jsonify({
            "ok": False,
            "error": (
                "El archivo excede el tamaño máximo de 10 MB "
                f"({request.content_length / (1024 * 1024):.2f} MB)"
            )
        }), 413

    # 1. Validar extensión permitida
    if ext not in EXTENSIONES_PERMITIDAS:
        return jsonify({
            "ok": False,
            "error": f"Extensión no permitida ({ext}). Tipos admitidos: PNG, JPG, JPEG, WEBP, GIF y PDF"
        }), 400

    # 2. Validar MIME type
    mime_type = (archivo.mimetype or "").lower()
    if mime_type not in MIME_TYPES_PERMITIDOS:
        return jsonify({
            "ok": False,
            "error": f"Formato MIME no admitido ({mime_type}). Solo se admiten imágenes y PDF"
        }), 400

    # 3. Validar contenido y tamaño
    contenido_bytes = archivo.read()
    tamano_bytes = len(contenido_bytes)
    if tamano_bytes == 0:
        return jsonify({"ok": False, "error": "El archivo enviado está vacío (0 bytes)"}), 400
    if tamano_bytes > TAMANO_MAXIMO_BYTES:
        return jsonify({
            "ok": False,
            "error": f"El archivo excede el tamaño máximo de 10 MB ({tamano_bytes / (1024*1024):.2f} MB)"
        }), 413

    # 4. Validación de firma binaria (magic bytes): evita subir un ejecutable o
    #    un script renombrado a .png o .pdf.
    if not _firma_valida(contenido_bytes, ext):
        return jsonify({
            "ok": False,
            "error": f"El contenido del archivo no corresponde a un {ext.lstrip('.').upper()} válido"
        }), 400

    # Materia ID opcional asociada al archivo. La validación es estricta: la
    # materia debe existir de verdad y ser visible para este usuario.
    materia_id_form = request.form.get("materia_id")
    materia_id = None
    if materia_id_form:
        try:
            materia_id = int(materia_id_form)
        except (TypeError, ValueError):
            return jsonify({
                "ok": False,
                "error": "El identificador de materia no es válido"
            }), 400
        if not _materia_asociable(materia_id, usuario_id):
            return jsonify({
                "ok": False,
                "error": "La materia indicada no existe o no está disponible para tu cuenta"
            }), 403

    # Nombre que verá el usuario en el modal y en la tarjeta del chat.
    # Se conservan acentos y espacios. La clave de R2 se genera aparte con un
    # UUID, así que este nombre nunca forma parte de una ruta de almacenamiento.
    nombre_para_mostrar = _nombre_mostrable(nombre_bruto, ext, usuario_id)

    # 5. Generar key única en R2 (usuarios/{usuario_id}/{uuid}.{ext})
    r2_key = r2.generar_key_segura(usuario_id, ext)

    # 6. Almacenamiento físico en Cloudflare R2
    #    Se comprueba la configuración ANTES de subir para poder distinguir un
    #    "no está configurado" de un "falló la subida". Sin este paso, un .env
    #    sin rellenar devolvía un 502 genérico que no decía qué corregir.
    motivo_r2 = r2.motivo_de_configuracion()
    if motivo_r2:
        print(f"[ARCHIVOS] Subida rechazada: {motivo_r2}")
        return jsonify({
            "ok": False,
            "error": "El almacenamiento de archivos no está configurado en el servidor.",
            "detalle": motivo_r2,
        }), 503

    subido_r2 = r2.subir_archivo(contenido_bytes, r2_key, mime_type)
    if not subido_r2:
        return jsonify({
            "ok": False,
            "error": "No se pudo guardar el archivo en Cloudflare R2. Inténtalo de nuevo."
        }), 502

    # 7. Registrar metadatos en Cloudflare D1
    try:
        registro_d1 = db.guardar_archivo(
            usuario_id=usuario_id,
            nombre_original=nombre_para_mostrar,
            r2_key=r2_key,
            mime_type=mime_type,
            extension=ext.lstrip("."),
            tamano_bytes=tamano_bytes,
            materia_id=materia_id
        )
    except db.D1Error:
        # El INSERT sí ocurrió pero no se pudo leer el id. NO se borra el objeto
        # de R2: el metadato ya existe en D1 y borrarlo dejaría un registro
        # apuntando a un archivo inexistente. Se avisa por consola para que se
        # pueda revisar a mano.
        print(
            "[ARCHIVOS] El archivo se subió a R2 y su metadato quedó en D1, "
            f"pero no se pudo confirmar la operación (r2_key={r2_key}). "
            "No se eliminó de R2 para no dejar una referencia rota en D1."
        )
        return jsonify({
            "ok": False,
            "error": (
                "El archivo se guardó, pero no se pudo confirmar el registro. "
                "Revisa el material ya subido antes de volver a intentarlo."
            )
        }), 503

    # Si el metadato no llegó a escribirse, se revierte la subida en R2 para no
    # dejar un objeto huérfano que el usuario no puede ver ni borrar.
    if not registro_d1:
        revertido = r2.eliminar_archivo(r2_key)
        if not revertido:
            print(
                "[ARCHIVOS] ADVERTENCIA: no se pudo escribir el metadato en D1 "
                f"ni revertir la subida en R2. Quedó un objeto huérfano: {r2_key}"
            )
        return jsonify({
            "ok": False,
            "error": "Error al registrar metadatos en Cloudflare D1. El archivo físico fue descartado de R2"
        }), 500

    return jsonify({
        "ok": True,
        "mensaje": "¡Archivo subido exitosamente!",
        "archivo": registro_d1
    }), 201


@app.route("/api/archivos", methods=["GET"])
def api_archivos_listar():
    """
    Lista los archivos del usuario autenticado.

    - `?materia_id=N` : solo los archivos de esa materia. Es lo que usa el
      modal "Materiales" y el contador del chat, así que ambos siempre coinciden.
    - sin `materia_id` : todos los archivos del usuario, incluidos los que no
      están asociados a ninguna materia.
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401
    usuario_id = int(usuario_id)

    materia_id_param = request.args.get("materia_id")
    materia_id = None
    if materia_id_param:
        try:
            materia_id = int(materia_id_param)
        except (TypeError, ValueError):
            return jsonify({
                "ok": False,
                "error": "El parámetro materia_id no es un número válido"
            }), 400

    archivos = db.obtener_archivos(usuario_id, materia_id)
    return jsonify({"ok": True, "archivos": archivos})


@app.route("/api/archivos/<int:archivo_id>/descargar", methods=["GET"])
def api_archivos_descargar(archivo_id):
    """
    Descarga o previsualiza de forma segura un archivo almacenado en Cloudflare R2.
    Verifica estrictamente que pertenezca al usuario de la sesión (aislamiento multiusuario).
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401
    usuario_id = int(usuario_id)

    # 1. Obtener metadatos desde D1 verificando usuario_id
    meta = db.obtener_archivo_por_id(archivo_id, usuario_id)
    if not meta:
        return jsonify({"ok": False, "error": "Archivo no encontrado o no tienes permisos de acceso"}), 404

    # 2. Obtener objeto físico desde Cloudflare R2
    obj = r2.obtener_archivo(meta["r2_key"])
    if not obj:
        return jsonify({"ok": False, "error": "El archivo físico no se encuentra en Cloudflare R2"}), 404

    forzar_descarga = request.args.get("descargar", "0") == "1"
    disposition = "attachment" if forzar_descarga else "inline"
    extension = meta.get("extension") or "bin"
    mime = meta.get("mime_type") or obj.get("content_type") or "application/octet-stream"

    # Nombre para la cabecera de descarga. `_nombre_mostrable` ya elimina comillas
    # y caracteres de control, así que no puede inyectar cabeceras HTTP. Aun así
    # se vuelve a filtrar aquí: es la última línea antes de la respuesta.
    nombre = meta.get("nombre_original") or f"archivo_{archivo_id}.{extension}"
    nombre = "".join(c for c in str(nombre) if c.isprintable() and c not in '"\\')
    if not nombre:
        nombre = f"archivo_{archivo_id}.{extension}"

    # Streaming seguro al navegador por bloques
    def generar_flujo():
        for chunk in obj["body"].iter_chunks(chunk_size=64 * 1024):
            yield chunk

    response = Response(generar_flujo(), mimetype=mime)
    response.headers["Content-Disposition"] = f'{disposition}; filename="{nombre}"'
    if obj.get("content_length"):
        response.headers["Content-Length"] = str(obj["content_length"])
    return response


@app.route("/api/archivos/<int:archivo_id>", methods=["DELETE"])
def api_archivos_eliminar(archivo_id):
    """
    Elimina un archivo: primero el objeto físico de Cloudflare R2 y después el
    metadato de D1. Verifica estrictamente que pertenezca al usuario de sesión.

    Regla de coherencia: la referencia de D1 no se borra hasta que el objeto
    físico se ha confirmado como borrado. Si R2 no está configurado o falla,
    el registro se conserva.

    Motivo: si se borrara el metadato sin poder tocar el bucket, el objeto
    quedaría en R2 sin ninguna forma de encontrarlo ni de eliminarlo desde la
    aplicación. Seguiría ocupando espacio y pagando almacenamiento y salida
    para siempre. Conservando la referencia, el alumno puede reintentar en
    cuanto se configure el servicio.
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401
    usuario_id = int(usuario_id)

    # 1. Obtener metadatos verificando usuario_id
    meta = db.obtener_archivo_por_id(archivo_id, usuario_id)
    if not meta:
        return jsonify({"ok": False, "error": "Archivo no encontrado o no tienes permisos"}), 404

    # 2. Eliminar físicamente de R2. Se distingue el caso "no configurado"
    #    del caso "falló", porque el mensaje al usuario y al admin son distintos.
    motivo_r2 = r2.motivo_de_configuracion()
    if motivo_r2:
        print(f"[ARCHIVOS] Borrado retenido: {motivo_r2} (archivo_id={archivo_id})")
        return jsonify({
            "ok": False,
            "error": "No se pudo eliminar el archivo porque el servidor no tiene configurado el almacenamiento.",
            "detalle": motivo_r2,
        }), 503

    borrado_r2 = r2.eliminar_archivo(meta["r2_key"])
    if not borrado_r2:
        return jsonify({
            "ok": False,
            "error": (
                "No se pudo eliminar el archivo de Cloudflare R2. "
                "El registro se conservó: vuelve a intentarlo para no dejar "
                "un archivo huérfano en el almacenamiento."
            )
        }), 502

    # 3. Eliminar metadatos en D1
    eliminado = db.eliminar_archivo_db(archivo_id, usuario_id)
    if not eliminado:
        return jsonify({"ok": False, "error": "No se pudo eliminar el registro en la base de datos"}), 500

    respuesta = {"ok": True, "mensaje": "Archivo eliminado correctamente"}
    return jsonify(respuesta)


# =====================================================================
# EJECUCIÓN LOCAL O EN RENDER
# =====================================================================
if __name__ == "__main__":
    # Toma el puerto que asigne el entorno (Render usa la variable PORT) o 5000 en local
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=True)