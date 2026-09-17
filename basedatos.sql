-- =====================================================================
-- EduAsistente — BASE DE DATOS NUEVA DESDE CERO (Cloudflare D1)
-- INSTRUCCIONES: borra la D1 vieja (o crea una nueva), abre la consola SQL
-- de Cloudflare D1, pega TODO este archivo y ejecútalo de una vez.
-- Deja: 9 tablas + 4 materias base globales. Sin usuarios semilla.
-- =====================================================================

-- 1) Limpieza (hijas primero por las FOREIGN KEY)
DROP TABLE IF EXISTS respuestas_ejercicios;
DROP TABLE IF EXISTS respuestas;
DROP TABLE IF EXISTS mensajes;
DROP TABLE IF EXISTS ejercicios;
DROP TABLE IF EXISTS nivel_usuario;
DROP TABLE IF EXISTS perfiles_aprendizaje;
DROP TABLE IF EXISTS materias;
DROP TABLE IF EXISTS usuarios;

-- 2) Tablas
CREATE TABLE usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  contrasena TEXT NOT NULL, -- hash werkzeug (generate_password_hash), jamás texto plano
  creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE materias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  descripcion TEXT,
  usuario_id INTEGER, -- NULL = global/base, NOT NULL = privada del usuario
  es_base INTEGER DEFAULT 0, -- 1 = las 4 base visibles para todos
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE perfiles_aprendizaje (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL UNIQUE, -- 1 perfil por estudiante (RF-12)
  estilo TEXT DEFAULT '', -- "aprendo con ejemplos de cocina, fútbol..." (opcional)
  creado_en TEXT NOT NULL DEFAULT (datetime('now')),
  actualizado_en TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE nivel_usuario (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL,
  materia_id INTEGER NOT NULL,
  nivel TEXT DEFAULT 'basico', -- basico | intermedio | avanzado (RF-11)
  prompt_nivel TEXT DEFAULT '', -- descripción viva para la IA, se recalcula cada 20 mensajes
  total_mensajes INTEGER DEFAULT 0,
  intentos INTEGER DEFAULT 0, -- ejercicios intentados (RF-13)
  aciertos INTEGER DEFAULT 0, -- ejercicios correctos (RF-13)
  actualizado_en TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(usuario_id, materia_id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  FOREIGN KEY (materia_id) REFERENCES materias(id)
);

CREATE TABLE mensajes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL,
  materia_id INTEGER NOT NULL,
  contenido TEXT NOT NULL,
  creado_en TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  FOREIGN KEY (materia_id) REFERENCES materias(id)
);

CREATE TABLE respuestas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mensaje_id INTEGER NOT NULL,
  contenido TEXT NOT NULL, -- texto limpio (sin base64 embebido)
  imagen_url TEXT, -- ilustración separada (data URL o URL)
  creado_en TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (mensaje_id) REFERENCES mensajes(id)
);

CREATE TABLE ejercicios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  materia_id INTEGER NOT NULL,
  enunciado TEXT NOT NULL,
  respuesta_correcta TEXT NOT NULL,
  explicacion TEXT,
  dificultad TEXT DEFAULT 'basico',
  FOREIGN KEY (materia_id) REFERENCES materias(id)
);

CREATE TABLE respuestas_ejercicios (
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
);

-- 3) Materias base globales (visibles para todos)
INSERT INTO materias (nombre, descripcion, usuario_id, es_base) VALUES
  ('Matemáticas', 'Álgebra, Geometría, Aritmética', NULL, 1),
  ('Física', 'Fuerzas, Velocidad, Energía, MRUV', NULL, 1),
  ('Química', 'Elementos, Reacciones, Enlaces', NULL, 1),
  ('Lenguaje', 'Gramática, Lectura, Ortografía', NULL, 1);

-- 4) Verificación (ejecuta estos SELECT para confirmar):
-- SELECT COUNT(*) AS tablas FROM sqlite_master WHERE type='table'; -- debe dar 10 (9 + sqlite_sequence)
-- SELECT id, nombre, es_base FROM materias; -- debe dar las 4 base
-- SELECT COUNT(*) AS usuarios FROM usuarios; -- debe dar 0
