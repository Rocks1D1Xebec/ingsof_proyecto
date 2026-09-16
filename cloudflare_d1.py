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
                descripcion TEXT
            )
        """)
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
                creado_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
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

        # 2. Insertar materias base si no existen
        materias = ejecutar_sql("SELECT COUNT(*) as total FROM materias")
        total = materias[0]["total"] if materias else 0
        if total == 0:
            materias_base = [
                ("Matemáticas", "Álgebra, Geometría, Aritmética"),
                ("Física", "Fuerzas, Velocidad, Energía, MRUV"),
                ("Química", "Elementos, Reacciones, Enlaces"),
                ("Lenguaje", "Gramática, Lectura, Ortografía"),
            ]
            for nombre, desc in materias_base:
                ejecutar_sql("INSERT INTO materias (nombre, descripcion) VALUES (?, ?)", [nombre, desc])

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
def obtener_materias() -> list[dict]:
    """Obtiene todas las materias disponibles."""
    filas = ejecutar_sql("SELECT id, nombre, descripcion FROM materias ORDER BY id ASC")
    if not filas:
        return [
            {"id": 1, "nombre": "Matemáticas", "descripcion": "Álgebra, Geometría, Aritmética"},
            {"id": 2, "nombre": "Física", "descripcion": "Fuerzas, Velocidad, Energía, MRUV"},
            {"id": 3, "nombre": "Química", "descripcion": "Elementos, Reacciones, Enlaces"},
            {"id": 4, "nombre": "Lenguaje", "descripcion": "Gramática, Lectura, Ortografía"},
        ]
    return filas


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


def guardar_respuesta(mensaje_id: int, contenido: str) -> dict | None:
    """Guarda la respuesta de la IA de forma segura."""
    try:
        sql = """
            INSERT INTO respuestas (mensaje_id, contenido)
            VALUES (?, ?)
            RETURNING id, mensaje_id, contenido
        """
        filas = ejecutar_sql(sql, [mensaje_id, contenido])
        return filas[0] if filas else None
    except Exception:
        return None


def obtener_historial(usuario_id: int, materia_id: int, limite: int = 20) -> list[dict]:
    """Obtiene el historial de conversación de la materia."""
    try:
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
        filas.reverse()
        return filas
    except Exception:
        return []


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
