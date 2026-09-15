"""
cloudflare_d1.py
----------------
Funciones simples para conectarse a Cloudflare D1 (Base de datos SQLite)
mediante peticiones HTTP (API REST de Cloudflare).
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Credenciales de Cloudflare D1 desde el archivo .env
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
    cuerpo = {"sql": sql}
    if params:
        cuerpo["params"] = params

    try:
        respuesta = requests.post(BASE_URL, headers=HEADERS, json=cuerpo, timeout=15)
        datos = respuesta.json()

        if not datos.get("success"):
            print("Error en Cloudflare D1:", datos.get("errors"))
            return []

        resultado = datos.get("result", [])
        if resultado and "results" in resultado[0]:
            return resultado[0]["results"]
        return []
    except Exception as e:
        print(f"Error de conexión con Cloudflare D1: {e}")
        return []


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
def obtener_materias() -> list[dict]:
    """Obtiene todas las materias disponibles."""
    return ejecutar_sql("SELECT id, nombre, descripcion FROM materias ORDER BY id ASC")


def crear_materia(nombre: str, descripcion: str = "") -> dict | None:
    """Crea una nueva materia."""
    sql = """
        INSERT INTO materias (nombre, descripcion)
        VALUES (?, ?)
        RETURNING id, nombre, descripcion
    """
    filas = ejecutar_sql(sql, [nombre, descripcion])
    return filas[0] if filas else None


# =====================================================================
# FUNCIONES DE MENSAJES Y CHAT
# =====================================================================
def guardar_mensaje(usuario_id: int, materia_id: int, contenido: str) -> dict | None:
    """Guarda la pregunta del estudiante."""
    sql = """
        INSERT INTO mensajes (usuario_id, materia_id, contenido)
        VALUES (?, ?, ?)
        RETURNING id, usuario_id, materia_id, contenido
    """
    filas = ejecutar_sql(sql, [usuario_id, materia_id, contenido])
    return filas[0] if filas else None


def guardar_respuesta(mensaje_id: int, contenido: str) -> dict | None:
    """Guarda la respuesta explicada que dio la IA."""
    sql = """
        INSERT INTO respuestas (mensaje_id, contenido)
        VALUES (?, ?)
        RETURNING id, mensaje_id, contenido
    """
    filas = ejecutar_sql(sql, [mensaje_id, contenido])
    return filas[0] if filas else None


def obtener_historial(usuario_id: int, materia_id: int, limite: int = 20) -> list[dict]:
    """Obtiene el historial de preguntas y respuestas de una materia."""
    sql = """
        SELECT m.id as mensaje_id, m.contenido as pregunta,
               r.contenido as respuesta, m.creado_en
        FROM mensajes m
        LEFT JOIN respuestas r ON r.mensaje_id = m.id
        WHERE m.usuario_id = ? AND m.materia_id = ?
        ORDER BY m.creado_en DESC
        LIMIT ?
    """
    filas = ejecutar_sql(sql, [usuario_id, materia_id, limite])
    filas.reverse()  # Orden cronológico (más antiguo primero)
    return filas


# =====================================================================
# FUNCIONES DE EJERCICIOS Y PRÁCTICAS
# =====================================================================
def guardar_ejercicio(materia_id: int, enunciado: str, respuesta_correcta: str, explicacion: str = "") -> dict | None:
    """Guarda un ejercicio generado por la IA."""
    sql = """
        INSERT INTO ejercicios (materia_id, enunciado, respuesta_correcta, explicacion)
        VALUES (?, ?, ?, ?)
        RETURNING id, materia_id, enunciado, respuesta_correcta
    """
    filas = ejecutar_sql(sql, [materia_id, enunciado, respuesta_correcta, explicacion])
    return filas[0] if filas else None
