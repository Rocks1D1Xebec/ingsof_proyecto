"""
init_db.py
─────────
Script para inicializar DESDE CERO las tablas en Cloudflare D1
y poblar las 4 materias base globales.

Equivalente local del bloque copiar-pegar de `basedatos.sql`.
Ejecutar una sola vez (o tras borrar la D1):

    python init_db.py
"""

from cloudflare_d1 import ejecutar_sql

TABLAS = [
    """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """,
    """
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            usuario_id INTEGER,
            es_base INTEGER DEFAULT 0
        )
    """,
    """
        CREATE TABLE IF NOT EXISTS perfiles_aprendizaje (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE,
            estilo TEXT DEFAULT '',
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """,
    """
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
    """,
    """
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            materia_id INTEGER NOT NULL,
            contenido TEXT NOT NULL,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (materia_id) REFERENCES materias(id)
        )
    """,
    """
        CREATE TABLE IF NOT EXISTS respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensaje_id INTEGER NOT NULL,
            contenido TEXT NOT NULL,
            imagen_url TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (mensaje_id) REFERENCES mensajes(id)
        )
    """,
    """
        CREATE TABLE IF NOT EXISTS ejercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia_id INTEGER NOT NULL,
            enunciado TEXT NOT NULL,
            respuesta_correcta TEXT NOT NULL,
            explicacion TEXT,
            dificultad TEXT DEFAULT 'basico',
            FOREIGN KEY (materia_id) REFERENCES materias(id)
        )
    """,
    """
        CREATE TABLE IF NOT EXISTS respuestas_ejercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ejercicio_id INTEGER,
            usuario_id INTEGER NOT NULL,
            respuesta_enviada TEXT NOT NULL,
            es_correcta INTEGER DEFAULT 0,
            feedback TEXT,
            respuesta_correcta TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (ejercicio_id) REFERENCES ejercicios(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """,
]

MATERIAS_BASE = [
    ("Matemáticas", "Álgebra, Geometría, Aritmética"),
    ("Física", "Fuerzas, Velocidad, Energía, MRUV"),
    ("Química", "Elementos, Reacciones, Enlaces"),
    ("Lenguaje", "Gramática, Lectura, Ortografía"),
]


def inicializar():
    """Crea las 9 tablas y agrega las 4 materias base globales."""
    for sql in TABLAS:
        print("🔧 Creando/verificando tabla...")
        ejecutar_sql(sql)

    materias = ejecutar_sql("SELECT COUNT(*) as total FROM materias WHERE es_base = 1")
    total = materias[0]["total"] if materias else 0

    if total == 0:
        print("📚 Insertando materias base globales...")
        for nombre, desc in MATERIAS_BASE:
            existe = ejecutar_sql("SELECT id FROM materias WHERE nombre = ? AND es_base = 1", [nombre])
            if not existe:
                ejecutar_sql(
                    "INSERT INTO materias (nombre, descripcion, usuario_id, es_base) VALUES (?, ?, NULL, 1)",
                    [nombre, desc],
                )
            print(f"   ✅ {nombre}: {desc}")
    else:
        print(f"📚 Ya existen {total} materias base, no se insertan duplicados.")

    print("\n✅ Base de datos inicializada correctamente.")


if __name__ == "__main__":
    inicializar()
