CREATE TABLE usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  contrasena TEXT NOT NULL,
  creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE materias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  descripcion TEXT
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
  contenido TEXT NOT NULL,
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
  ejercicio_id INTEGER NOT NULL,
  usuario_id INTEGER NOT NULL,
  respuesta_enviada TEXT NOT NULL,
  es_correcta INTEGER DEFAULT 0,
  feedback TEXT,
  respuesta_correcta TEXT,
  creado_en TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (ejercicio_id) REFERENCES ejercicios(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);


