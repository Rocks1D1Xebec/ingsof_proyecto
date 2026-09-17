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
from flask import Flask, jsonify, request, send_file, send_from_directory, session
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

import cloudflare_d1 as db
import gemini_helper as gemini

# Cargar variables del archivo .env
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
# Llave secreta para manejar las sesiones en el navegador
app.secret_key = os.getenv("SECRET_KEY", "mi_clave_secreta_escolar_123")

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

    # 4. Detectar si Gemini incluyó una solicitud de ilustración visual [IMAGEN_EDUCATIVA: ...]
    img_data_url = None
    patron_imagen = r"\[IMAGEN_EDUCATIVA:\s*(.*?)\]"
    match_imagen = re.search(patron_imagen, respuesta_ia, re.IGNORECASE)

    if match_imagen:
        prompt_visual = match_imagen.group(1).strip()
        # Generar imagen con Cloudflare Workers AI
        img_data_url = cf_ai.generar_imagen_educativa(prompt_visual)
        # Tope de tamaño: data-URLs gigantes reventaban D1/historial/RAM en Render
        if img_data_url and len(img_data_url) > 700_000:
            img_data_url = None
    # La imagen viaja SIEMPRE separada (columna imagen_url + JSON); el texto
    # queda limpio para que el historial pese KB y no cientos de KB.
    respuesta_ia = re.sub(patron_imagen, "", respuesta_ia, flags=re.IGNORECASE)

    # 5. Guardar la respuesta en la base de datos:
    #    contenido = texto limpio (sin base64 embebido), imagen_url = columna separada
    if mensaje and "id" in mensaje:
        db.guardar_respuesta(mensaje["id"], respuesta_ia, img_data_url)


    return jsonify({
        "ok": True,
        "respuesta": respuesta_ia,
        "imagen_url": img_data_url,
    })


@app.route("/api/ilustrar", methods=["POST"])
def api_ilustrar():
    """Genera bajo demanda una ilustración (botón manual 🎨) sin romper el chat si falla."""
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return jsonify({"ok": False, "error": "Debes iniciar sesión"}), 401

    data = request.get_json() or {}
    tema = data.get("tema", "").strip()
    texto = data.get("texto", "").strip()
    prompt = tema or texto[:300]
    if not prompt:
        return jsonify({"ok": False, "error": "Indica un tema para ilustrar"}), 400

    img = cf_ai.generar_imagen_educativa(prompt[:300])
    if not img:
        return jsonify({"ok": False, "error": "No se pudo generar la imagen en este momento"}), 502
    return jsonify({"ok": True, "imagen_url": img})


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

    return jsonify({
        "ok": True,
        "ejercicio": {
            "id": guardado["id"] if guardado else None,
            "enunciado": ejercicio["enunciado"],
            "respuesta_correcta": ejercicio["respuesta_correcta"]
        }
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

    return jsonify({
        "ok": True,
        "es_correcta": evaluacion["es_correcta"],
        "feedback": evaluacion["feedback"],
        "revision_id": revision["id"] if revision else None,
    })


# =====================================================================
# EJECUCIÓN LOCAL O EN RENDER
# =====================================================================
if __name__ == "__main__":
    # Toma el puerto que asigne el entorno (Render usa la variable PORT) o 5000 en local
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=True)