"""
init_db.py
──────────
Script para inicializar las tablas en Cloudflare D1
y poblar las 4 materias base del sistema.

Ejecutar una sola vez:
    python init_db.py
"""

from cloudflare_d1 import ejecutar_sql


def inicializar():
    """Crea las tablas y agrega las materias base."""

    print("🔧 Creando tabla 'usuarios'...")
    ejecutar_sql("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    print("🔧 Creando tabla 'materias'...")
    ejecutar_sql("""
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT
        )
    """)

    print("🔧 Creando tabla 'mensajes'...")
    ejecutar_sql("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            materia_id INTEGER NOT NULL,
            contenido TEXT NOT NULL,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (materia_id) REFERENCES materias(id)
        )
    """)

    print("🔧 Creando tabla 'respuestas'...")
    ejecutar_sql("""
        CREATE TABLE IF NOT EXISTS respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensaje_id INTEGER NOT NULL,
            contenido TEXT NOT NULL,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (mensaje_id) REFERENCES mensajes(id)
        )
    """)

    print("🔧 Creando tabla 'ejercicios'...")
    ejecutar_sql("""
        CREATE TABLE IF NOT EXISTS ejercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia_id INTEGER NOT NULL,
            enunciado TEXT NOT NULL,
            respuesta_correcta TEXT NOT NULL,
            explicacion TEXT,
            dificultad TEXT DEFAULT 'basico',
            FOREIGN KEY (materia_id) REFERENCES materias(id)
        )
    """)

    print("🔧 Creando tabla 'respuestas_ejercicios'...")
    ejecutar_sql("""
        CREATE TABLE IF NOT EXISTS respuestas_ejercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ejercicio_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            respuesta_enviada TEXT NOT NULL,
            es_correcta INTEGER DEFAULT 0,
            feedback TEXT,
            respuesta_correcta TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (ejercicio_id) REFERENCES ejercicios(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    # Verificar si ya existen materias
    materias = ejecutar_sql("SELECT COUNT(*) as total FROM materias")
    total = materias[0]["total"] if materias else 0

    if total == 0:
        print("📚 Insertando materias base...")
        materias_base = [
            ("Matemáticas", "Álgebra, Geometría, Aritmética, Trigonometría"),
            ("Física", "Fuerzas, Velocidad, Energía, Ondas"),
            ("Química", "Elementos, Reacciones, Fórmulas, Enlaces"),
            ("Lenguaje", "Gramática, Lectura, Ortografía, Redacción"),
        ]
        for nombre, desc in materias_base:
            ejecutar_sql(
                "INSERT INTO materias (nombre, descripcion) VALUES (?, ?)",
                [nombre, desc],
            )
            print(f"   ✅ {nombre}: {desc}")
    else:
        print(f"📚 Ya existen {total} materias, no se insertan duplicados.")

    print("\n✅ Base de datos inicializada correctamente.")


if __name__ == "__main__":
    inicializar()
