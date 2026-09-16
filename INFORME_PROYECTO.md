# 📘 INFORME DEL PROYECTO: ASISTENTE ESCOLAR (EduAsistente v1.0)

---

## 1. 🎯 Resumen del Proyecto

Este proyecto es una plataforma web educativa diseñada para estudiantes de secundaria que enfrentan dificultades académicas en materias como **Matemáticas, Física, Química y Lenguaje**. Su objetivo es brindar explicaciones paso a paso, resolución guiada de dudas y ejercicios prácticos con retroalimentación inmediata, funcionando como un tutor virtual amigable y paciente.

El desarrollo se realizó cumpliendo los requerimientos y casos de uso especificados en la carpeta `Proyecto/`:
- **RF-01 / CU-01**: Registro de nuevos estudiantes.
- **RF-02 / CU-01**: Inicio de sesión simple y directo.
- **RF-03**: Cierre de sesión seguro.
- **RF-04 / CU-02**: Selección y gestión de materias.
- **RF-05, RF-06, RF-07 / CU-03**: Formulación de dudas y generación de explicaciones detalladas paso a paso mediante Inteligencia Artificial (Google Gemini).
- **RF-08, RF-09, RF-10 / CU-04**: Generación de ejercicios de práctica y revisión de respuestas con retroalimentación formativa y empática.

---

## 2. 🛠️ Tecnologías y Librerías Utilizadas

El sistema fue diseñado con un enfoque **simple, claro, funcional y educativo**, sin algoritmos complejos ni cifrados avanzados para facilitar su comprensión académica:

| Tecnología / Librería | Propósito | ¿Por qué se utilizó? |
| :--- | :--- | :--- |
| **Python 3** | Lenguaje de programación backend | Sintaxis clara, fácil de aprender y muy potente. |
| **Flask (`flask`)** | Micro-framework web | Permite crear rutas y APIs REST de manera muy sencilla y rápida. |
| **Gunicorn (`gunicorn`)** | Servidor de producción WSGI para **Render** | Es el servidor estándar para desplegar aplicaciones Flask en la nube (Render). |
| **Requests (`requests`)** | Cliente HTTP | Permite enviar y recibir consultas SQL a la API de **Cloudflare D1**. |
| **Google GenAI (`google-genai`)** | SDK oficial de Inteligencia Artificial de Gemini | Para conectar con el modelo `gemini-2.0-flash` y generar explicaciones pedagógicas. |
| **Python Dotenv (`python-dotenv`)** | Manejo de variables de entorno | Para leer las credenciales (`.env`) sin exponer contraseñas ni tokens en el código. |
| **Cloudflare D1** | Base de datos SQLite Serverless en la nube | Almacena usuarios, materias, mensajes, respuestas y ejercicios de forma permanente. |
| **HTML5 / CSS3 / JavaScript Vanilla** | Frontend interactivo | Interfaz moderna, amigable, limpia y responsive sin dependencias pesadas. |

---

## 3. 📂 Estructura y Explicación de los Archivos

```plaintext
ingsof_proyecto/
│
├── .env                      # Variables de entorno (tokens y llaves de API)
├── requirements.txt          # Lista de librerías para Render / Python
├── schema.sql                # Estructura de las tablas de la base de datos
├── init_db.py                # Script para inicializar tablas y materias base
│
├── main.py                   # Servidor Flask principal (Rutas y API)
├── cloudflare_d1.py          # Conexión simple a la base de datos Cloudflare D1
├── gemini_helper.py          # Conexión inteligente a modelos activos de Gemini
├── listar_modelos.py         # Script para consultar los modelos disponibles en tu cuenta
│
├── index.html                # Redirección inicial
├── login.html                # Pantalla de inicio de sesión
├── register.html             # Pantalla de registro de estudiantes
├── dashboard.html            # Panel principal de selección de materias
├── chat.html                 # Sala de estudio interactiva con IA y ejercicios
│
├── css/
│   └── styles.css            # Estilos visuales de la aplicación
│
└── Proyecto/                 # Documentos de análisis y requerimientos originales
```

---

## 4. 📝 Detalle de lo que se Hizo en el Código

### A. Backend (`main.py`)
- Se crearon rutas sencillas y comentadas:
  - `/api/register` y `/api/login`: Manejan la autenticación guardando y comparando las credenciales de forma directa (sin cifrados complejos, cumpliendo el nivel requerido de clase).
  - `/api/sesion` y `/api/logout`: Manejan la sesión activa del estudiante en el navegador.
  - `/api/materias`: Permite listar las materias existentes y añadir nuevas materias.
  - `/api/chat`: Recibe la pregunta del estudiante, consulta el historial, invoca a Gemini y devuelve la explicación paso a paso.
  - `/api/ejercicio` y `/api/revisar`: Genera ejercicios automáticos y evalúa las respuestas del estudiante indicando aciertos y errores detallados.

### B. Base de Datos Cloudflare D1 (`cloudflare_d1.py` y `init_db.py`)
- Se implementó la comunicación mediante la API REST de Cloudflare D1 usando la función `ejecutar_sql(sql, params)`.
- Se crearon las 6 tablas esenciales:
  1. `usuarios`: Datos del estudiante (id, nombre, email, contrasena, creado_en).
  2. `materias`: Catálogo de asignaturas (Matemáticas, Física, Química, Lenguaje, etc.).
  3. `mensajes`: Preguntas enviadas por los estudiantes.
  4. `respuestas`: Explicaciones generadas por el asistente.
  5. `ejercicios`: Problemas y ejercicios para practicar.
  6. `respuestas_ejercicios`: Registro de los intentos y evaluaciones de los estudiantes.

### C. Inteligencia Artificial (`gemini_helper.py`)
- Se configuró el modelo `gemini-2.0-flash` con un rol pedagógico (**"EduAsistente"**).
- Se establecieron reglas didácticas para que la IA responda siempre:
  1. En español y con lenguaje claro.
  2. Paso a paso (Paso 1, Paso 2, etc.).
  3. Con ejemplos cotidianos y tono motivador.
  4. Sin inventar datos y con retroalimentación constructiva al detectar errores.

### D. Frontend Dinámico (`login.html`, `register.html`, `dashboard.html`, `chat.html`)
- **Login y Registro**: Validación de campos, mensajes claros en pantalla y redirección fluida.
- **Dashboard**: Muestra el nombre del estudiante conectado, carga las materias desde la base de datos y permite agregar nuevas materias mediante una ventana modal.
- **Chat Interactivo**:
  - Permite chatear con el tutor virtual en tiempo real.
  - Conserva el historial de conversación.
  - Incluye botón de **"🎯 Dame un ejercicio de práctica"** que muestra una caja interactiva para responder y verificar la solución en el momento.
  - Permite copiar explicaciones con un solo clic.

---

## 5. 🚀 Guía de Ejecución y Despliegue

### Ejecución Local en tu Computadora:
1. Instalar las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Inicializar la base de datos (solo la primera vez):
   ```bash
   python init_db.py
   ```
3. Iniciar el servidor:
   ```bash
   python main.py
   ```
4. Abrir en el navegador:
   ```
   http://127.0.0.1:5000
   ```

### Despliegue en Render:
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  gunicorn main:app --bind 0.0.0.0:$PORT
  ```
- **Environment Variables (Variables de Entorno)** en Render:
  - `CLOUDFLARE_ACCOUNT_ID`: ID de cuenta de Cloudflare.
  - `CLOUDFLARE_DATABASE_ID`: ID de la base de datos D1.
  - `CLOUDFLARE_API_TOKEN`: Token de API de Cloudflare.
  - `API`: Clave de API de Google Gemini.
  - `SECRET_KEY`: Clave para las sesiones.

---

## 6. ✅ Conclusión
El sistema se encuentra 100% operativo, con un código limpio, estructurado y fácil de mantener, satisfaciendo todos los requerimientos funcionales del proyecto escolar.
