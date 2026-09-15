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

import cloudflare_d1 as db
import gemini_helper as gemini

# Cargar variables del archivo .env
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
# Llave secreta para manejar las sesiones en el navegador
app.secret_key = os.getenv("SECRET_KEY", "mi_clave_secreta_escolar_123")


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

    # Crear el usuario en la base de datos (guardado directo y simple)
    usuario = db.crear_usuario(nombre, email, contrasena)
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
    """Inicia sesión comparando correo y contraseña en texto plano."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    contrasena = data.get("contrasena", "").strip()

    if not email or not contrasena:
        return jsonify({"ok": False, "error": "Por favor ingresa tu correo y contraseña"}), 400

    usuario = db.buscar_usuario_por_email(email)
    if not usuario:
        return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos"}), 401

    # Comparación directa y simple de contraseña
    if usuario["contrasena"] != contrasena:
        return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos"}), 401

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
    """Devuelve la lista de materias disponibles."""
    materias = db.obtener_materias()
    return jsonify({"ok": True, "materias": materias})


@app.route("/api/materias", methods=["POST"])
def api_materias_crear():
    """Crea una nueva materia personalizada."""
    data = request.get_json() or {}
    nombre = data.get("nombre", "").strip()
    descripcion = data.get("descripcion", "").strip()

    if not nombre:
        return jsonify({"ok": False, "error": "El nombre de la materia es obligatorio"}), 400

    materia = db.crear_materia(nombre, descripcion)
    if not materia:
        return jsonify({"ok": False, "error": "No se pudo crear la materia"}), 500

    return jsonify({"ok": True, "materia": materia}), 201


# =====================================================================
# CHAT / EXPLICACIONES CON INTELIGENCIA ARTIFICIAL (GEMINI)
# =====================================================================
@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Recibe la duda del estudiante y responde con IA paso a paso."""
    data = request.get_json() or {}
    pregunta = data.get("pregunta", "").strip()
    materia_id = data.get("materia_id")
    materia_nombre = data.get("materia_nombre", "General").strip()

    if not pregunta:
        return jsonify({"ok": False, "error": "Debes escribir una pregunta"}), 400

    usuario_id = session.get("usuario_id", 1)  # Si no hay sesión, usa 1 por defecto

    # 1. Guardar la pregunta en la base de datos
    mensaje = db.guardar_mensaje(usuario_id, int(materia_id or 1), pregunta)

    # 2. Obtener historial previo para darle contexto a la IA
    historial = db.obtener_historial(usuario_id, int(materia_id or 1), limite=6)

    # 3. Consultar a Gemini para obtener la respuesta explicada paso a paso
    respuesta_ia = gemini.explicar_tema(pregunta, materia_nombre, historial)

    # 4. Guardar la respuesta de la IA en la base de datos
    if mensaje and "id" in mensaje:
        db.guardar_respuesta(mensaje["id"], respuesta_ia)

    return jsonify({
        "ok": True,
        "respuesta": respuesta_ia
    })


@app.route("/api/historial", methods=["GET"])
def api_historial():
    """Devuelve las preguntas y respuestas anteriores de una materia."""
    materia_id = request.args.get("materia_id", 1)
    usuario_id = session.get("usuario_id", 1)

    historial = db.obtener_historial(usuario_id, int(materia_id), limite=20)
    return jsonify({"ok": True, "historial": historial})


# =====================================================================
# PRÁCTICA Y EJERCICIOS (GENERACIÓN Y REVISIÓN)
# =====================================================================
@app.route("/api/ejercicio", methods=["POST"])
def api_ejercicio():
    """Genera un ejercicio práctico con Gemini."""
    data = request.get_json() or {}
    materia_id = data.get("materia_id", 1)
    materia_nombre = data.get("materia_nombre", "General")
    tema = data.get("tema", "")

    # Generar con Gemini
    ejercicio = gemini.generar_ejercicio(materia_nombre, tema)

    # Guardar en base de datos
    guardado = db.guardar_ejercicio(
        int(materia_id),
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
    """Revisa la respuesta del estudiante y le dice si es correcta con feedback."""
    data = request.get_json() or {}
    enunciado = data.get("enunciado", "")
    respuesta_estudiante = data.get("respuesta", "")
    respuesta_correcta = data.get("respuesta_correcta", "")
    materia_nombre = data.get("materia_nombre", "General")

    if not respuesta_estudiante:
        return jsonify({"ok": False, "error": "Debes ingresar tu respuesta"}), 400

    # Revisar con Gemini
    evaluacion = gemini.revisar_respuesta(enunciado, respuesta_estudiante, respuesta_correcta, materia_nombre)

    return jsonify({
        "ok": True,
        "es_correcta": evaluacion["es_correcta"],
        "feedback": evaluacion["feedback"]
    })


# =====================================================================
# EJECUCIÓN LOCAL O EN RENDER
# =====================================================================
if __name__ == "__main__":
    # Toma el puerto que asigne el entorno (Render usa la variable PORT) o 5000 en local
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=True)