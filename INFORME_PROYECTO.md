# 📘 INFORME DEL PROYECTO: ASISTENTE ESCOLAR (EduAsistente v1.0)

---

## 1. 🎯 Resumen Ejecutivo del Proyecto

El **Asistente Escolar (EduAsistente)** es una plataforma web interactiva diseñada para apoyar a estudiantes de secundaria que presentan dificultades académicas en materias fundamentales: **Matemáticas, Física, Química y Lenguaje**. Su propósito es funcionar como un tutor virtual paciente, amigable y motivador, capaz de explicar conceptos paso a paso, responder dudas sin tecnicismos innecesarios y ofrecer ejercicios de práctica con retroalimentación inmediata.

El proyecto fue desarrollado bajo una filosofía de **código simple, funcional, robusto y fácil de entender a nivel educativo**. Las contraseñas se guardan con hash `werkzeug` (con sal, estándar de la industria) y la documentación de análisis vive en `Proyecto/`.

---

## 2. 📋 Cumplimiento de Requerimientos y Casos de Uso

El desarrollo implementa el 100% de los requisitos definidos en los documentos de análisis:

| Requisito / Caso de Uso | Descripción | Estado | Implementación |
| :--- | :--- | :---: | :--- |
| **RF-01 / CU-01** | **Registro de Usuario**: Creación de cuenta con nombre, correo y contraseña. | ✅ Completado | Formulario en `register.html` conectado a `POST /api/register`. |
| **RF-02 / CU-01** | **Inicio de Sesión**: Validación de credenciales del estudiante. | ✅ Completado | Formulario en `login.html` conectado a `POST /api/login`. |
| **RF-03** | **Cierre de Sesión**: Finalizar la sesión activa del usuario. | ✅ Completado | Botón de salida conectado a `POST /api/logout`. |
| **RF-04 / CU-02** | **Gestión de Materias**: Listar asignaturas y crear nuevas materias personalizadas. | ✅ Completado | Panel dinámico en `dashboard.html` conectado a `GET` y `POST /api/materias`. |
| **RF-05 / CU-03** | **Formulación de Preguntas**: El estudiante envía su duda en texto plano. | ✅ Completado | Caja de chat en `chat.html` conectada a `POST /api/chat`. |
| **RF-06 / CU-03** | **Explicación Paso a Paso**: La IA responde de forma didáctica y estructurada. | ✅ Completado | Prompts pedagógicos con Google Gemini en `gemini_helper.py`. |
| **RF-07 / CU-03** | **Historial de Conversación**: Guardar y consultar mensajes anteriores. | ✅ Completado | Consultas SQLite en Cloudflare D1 mediante `GET /api/historial`. |
| **RF-08 / CU-04** | **Generación de Ejercicios**: Crear problemas de práctica adaptados a la materia. | ✅ Completado | Botón interactivo en el chat conectado a `POST /api/ejercicio`. |
| **RF-09 / CU-04** | **Revisión de Respuestas**: Evaluar si la respuesta del estudiante es correcta o no. | ✅ Completado | Módulo interactivo conectado a `POST /api/revisar`. |
| **RF-10 / CU-04** | **Retroalimentación Formativa**: Mostrar con empatía en qué paso se equivocó. | ✅ Completado | Evaluación guiada por Gemini con consejos constructivos. |
| **RF-11** | **Adaptación al nivel**: Nivel por materia deducido por la IA cada 20 mensajes (`nivel_usuario`). | ✅ Completado | `evaluar_nivel()` en `gemini_helper.py` + contexto en `/api/chat`. |
| **RF-12** | **Técnica por asociación**: El estudiante describe cómo aprende y la IA adapta analogías. | ✅ Completado | Tarjeta en `dashboard.html` + `GET/PUT /api/perfil` (tabla `perfiles_aprendizaje`). |
| **RF-13** | **Guardar progreso**: Intentos/aciertos por materia + la IA informa con datos reales al preguntar "¿cómo voy?". | ✅ Completado | Contadores en `nivel_usuario` + `respuestas_ejercicios`. |
| **RNF-05** | **Protección**: Contraseñas con hash y sal. | ✅ Completado | `werkzeug.security` en `POST /api/register` y `/api/login`. |

---

## 3. 🛠️ Tecnologías y Librerías Utilizadas

| Componente | Tecnología / Librería | Justificación y Uso |
| :--- | :--- | :--- |
| **Backend** | `Python 3` + `Flask` | Micro-framework ligero que permite estructurar rutas API claras y servir los archivos web sin configuraciones complejas. |
| **Servidor en la Nube** | `Gunicorn` | Servidor de producción WSGI utilizado por **Render** para desplegar aplicaciones Python de forma eficiente. |
| **Base de Datos** | `Cloudflare D1` (SQLite Serverless) | Base de datos relacional ligera en la nube que persiste usuarios, materias, preguntas, respuestas y ejercicios. |
| **Conector HTTP** | `Requests` | Librería estándar de Python para realizar peticiones HTTP seguras hacia la API REST de Cloudflare D1. |
| **Inteligencia Artificial** | `Google GenAI SDK` (`google-genai`) | SDK oficial para conectar con los modelos de **Google Gemini** y generar explicaciones pedagógicas adaptadas al nivel escolar. |
| **Variables de Entorno** | `Python-Dotenv` | Permite cargar configuraciones y llaves secretas desde el archivo `.env` o desde el panel de Render. |
| **Frontend** | `HTML5`, `CSS3` y `JavaScript Vanilla` | Interfaz limpia, responsiva, moderna y sin dependencias pesadas (React, Vue, etc.), facilitando su mantenimiento y velocidad de carga. |

---

## 4. 📂 Estructura de Archivos del Proyecto

```plaintext
ingsof_proyecto/
│
├── .env                      # Variables de entorno (credenciales de Cloudflare y Gemini)
├── requirements.txt          # Dependencias de Python para Render
├── schema.sql                # Esquema SQL con las tablas de la base de datos
├── init_db.py                # Script manual de inicialización de tablas y datos
│
├── main.py                   # Servidor web principal Flask y endpoints de la API
├── cloudflare_d1.py          # Módulo de conexión y consultas a Cloudflare D1
├── gemini_helper.py          # Integración con Google Gemini (explicaciones y ejercicios)
├── listar_modelos.py         # Script para listar los modelos autorizados de Gemini
│
├── index.html                # Redirección automática inicial
├── login.html                # Interfaz de inicio de sesión
├── register.html             # Interfaz de registro de cuenta nueva
├── dashboard.html            # Panel principal de selección de materias
├── chat.html                 # Sala de estudio interactiva con chat e IA
│
├── css/
│   └── styles.css            # Hoja de estilos compartida para toda la plataforma
│
├── Proyecto/                 # Documentación de análisis y requerimientos originales
└── INFORME_PROYECTO.md       # Este informe técnico
```

---

## 5. 🔍 Explicación Detallada del Código y Funcionamiento

### A. Backend Principal (`main.py`)
El archivo `main.py` es el núcleo del backend. Administra las rutas del servidor y las peticiones enviadas desde el navegador:
- **Autenticación Directa y Simple**:
  - `POST /api/register`: Recibe nombre, correo y contraseña. Si el correo no existe, crea el registro y asigna sesión activa.
  - `POST /api/login`: Compara el correo y la contraseña en texto plano de forma directa (`usuario['contrasena'] == contrasena`), permitiendo entender el flujo de login sin funciones criptográficas complejas.
  - `GET /api/sesion`: Retorna si el visitante está autenticado y su nombre para mostrarlo en el menú superior.
  - `POST /api/logout`: Limpia las cookies de sesión y desconecta al usuario.
- **Gestión de Materias**:
  - `GET /api/materias`: Devuelve la lista de materias guardadas en Cloudflare D1.
  - `POST /api/materias`: Permite a los estudiantes añadir materias personalizadas (ej. Historia, Biología).
- **Tutoría con IA y Ejercicios**:
  - `POST /api/chat`: Recibe la pregunta del estudiante, consulta el historial previo en la base de datos, envía el contexto a Gemini y guarda tanto la pregunta como la respuesta generada.
  - `GET /api/historial`: Carga la conversación previa de la materia seleccionada.
  - `POST /api/ejercicio`: Solicita a Gemini un problema práctico con enunciado y solución.
  - `POST /api/revisar`: Envía la solución del estudiante a Gemini para evaluar si es correcta y ofrecer retroalimentación paso a paso.
  - `GET /api/modelos`: Endpoint público para consultar en JSON qué modelos de Gemini están activos en la cuenta.

---

### B. Base de Datos en la Nube (`cloudflare_d1.py`)
Conecta la aplicación con la base de datos Cloudflare D1 mediante peticiones HTTP a su API REST:
- **Auto-inicialización Segura (`asegurar_inicializacion()`)**:
  Al encender el servidor en Render, este método verifica y crea automáticamente las 6 tablas esenciales (`usuarios`, `materias`, `mensajes`, `respuestas`, `ejercicios`, `respuestas_ejercicios`) y puebla las 4 materias iniciales (Matemáticas, Física, Química, Lenguaje) y un usuario inicial por defecto.
- **Tolerancia a Fallos**:
  Si la base de datos tarda en responder o hay un retraso de conexión, las funciones de chat capturan la excepción sin interrumpir el flujo, garantizando que el estudiante siempre reciba la respuesta de la IA.

---

### C. Inteligencia Artificial Adaptativa (`gemini_helper.py` y `listar_modelos.py`)
- **Detección Dinámica de Modelos**:
  Para evitar errores de modelos obsoletos (como `404 NOT_FOUND` en versiones anteriores), `gemini_helper.py` consulta en tiempo real qué modelos tiene habilitados la API Key del usuario (`client.models.list()`).
- **Sistema de Respaldo (*Fallback*)**:
  Si un modelo específico no responde o se encuentra saturado, el sistema cambia automáticamente al siguiente modelo disponible de la lista (ej. `gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`) sin mostrar mensajes de error al usuario.
- **Prompts Pedagógicos**:
  Configura a la IA bajo el rol de **"EduAsistente"**, forzándola a responder siempre en español, con tono empático, dividiendo las explicaciones en 4 secciones claras (Concepto, Fórmulas/Reglas, Procedimiento paso a paso y Conclusión).

---

### D. Frontend Interactivo
- **`register.html`**:
  - Se corrigió el campo de nombre eliminando valores predeterminados fijos. Ahora incluye un texto de sugerencia (`placeholder="Ej. Carlos"`) que se borra automáticamente en cuanto el usuario comienza a escribir.
- **`login.html`**:
  - Formulario limpio con botón para alternar la visibilidad de la contraseña (👁 / 🙈) y mensajes de error claros en caso de credenciales inválidas.
- **`dashboard.html`**:
  - Muestra el nombre real del estudiante autenticado.
  - Carga las materias dinámicamente desde Cloudflare D1 con tarjetas estilizadas y temáticas.
  - Incluye una ventana modal para añadir nuevas materias en un clic.
- **`chat.html`**:
  - Muestra el encabezado de la materia en estudio (ej. Física, Matemáticas).
  - Carga el historial previo de conversación.
  - Envía dudas y muestra la respuesta de Gemini en tiempo real.
  - Incluye el botón **"🎯 Dame un ejercicio de práctica"**, el cual genera una caja interactiva donde el estudiante escribe su solución y recibe retroalimentación inmediata con un botón de verificación.
  - Botón para copiar respuestas al portapapeles.

---

## 6. 🧠 Preguntas Clave sobre la Arquitectura del Sistema

### 1. ¿Qué ocurre si un usuario pregunta por Química y otro entra a Física y dice "¿En qué estábamos?"?
* **Aislamiento Total**: Cada mensaje en Cloudflare D1 se guarda con `usuario_id` y `materia_id`.
* Cuando el nuevo usuario entra a Física, la consulta SQL filtra exclusivamente:
  ```sql
  WHERE usuario_id = ? AND materia_id = ?
  ```
* Al no haber mensajes previos para ese usuario en Física, el historial está vacío. La IA recibe el contexto de Física y le responderá cordialmente que apenas van a comenzar, sin mezclar nunca temas de otros usuarios o de otras materias.

### 2. Si el modelo de Gemini se agota o cambia, ¿cómo recuerda la conversación?
* Los modelos de IA no almacenan recuerdos en sus servidores (*son stateless*).
* **La memoria real vive en tu base de datos Cloudflare D1**.
* Cada vez que se envía una pregunta, el backend extrae los últimos mensajes de la base de datos y se los envía como contexto al modelo activo en ese instante. Si el modelo cambia de `gemini-2.5-flash` a `gemini-1.5-flash`, el nuevo modelo recibe el mismo historial y continúa la tutoría sin perder el hilo.

---

## 7. 🚀 Guía de Despliegue en Render

Para desplegar la aplicación en **Render** (Web Service):

1. **Configuración del Servicio**:
   - **Environment**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     gunicorn main:app --bind 0.0.0.0:$PORT
     ```

2. **Variables de Entorno en el Dashboard de Render**:
   - `CLOUDFLARE_ACCOUNT_ID`: ID de tu cuenta de Cloudflare.
   - `CLOUDFLARE_DATABASE_ID`: ID de la base de datos D1 en Cloudflare.
   - `CLOUDFLARE_API_TOKEN`: Token con permisos de lectura/escritura en D1.
   - `API`: Tu clave de API de Google Gemini (`AIzaSy...`).
   - `SECRET_KEY`: Cadena para la seguridad de las sesiones web.

3. **Verificación de Modelos**:
   Una vez desplegado, puedes abrir en tu navegador:
   `https://<tu-subdominio-en-render>.onrender.com/api/modelos`
   para comprobar la lista de modelos de IA activos en tu cuenta.

---

## 8. ✅ Conclusión

El proyecto **EduAsistente v1.0** se encuentra completamente operativo y optimizado para la nube. Posee una estructura limpia, código pedagógico sin librerías de cifrado innecesarias, conexión persistente a Cloudflare D1, integración inteligente con Google Gemini y una interfaz de usuario atractiva, accesible y orientada a estudiantes de secundaria.

## 9. 🆕 v1.1 — Ilustración coherente Preciso/Creativo + disclaimer IA

* **Solo-manual:** `/api/chat` ya no genera imagen automática; solo texto primero. La imagen nace al pulsar `🎨 Ver ilustración`.
* **Re-analizador:** `/api/ilustrar` recibe `{pregunta, respuesta, materia, modo}`, llama `gemini_helper.generar_prompt_imagen()` —prompt visual en inglés coherente con la explicación— y luego `cloudflare_ai.generar_imagen_educativa(prompt, modo)` con `negative_prompt`.
* **Toggle estudiante:** `🎯 Preciso` —diagrama lineal sin texto dibujado, etiquetas como HTML— para Matemáticas/Física/Química; `🎨 Creativo` —cartoon con etiquetas cortas— para Lenguaje/decorativo. Persistente por materia en `localStorage`.
* **Fidelidad:** envolver en PDF no corrige difusión; este cambio sí mejora coherencia porque el prompt nace de la respuesta final, no de la duda inicial.
* **Disclaimer:** banner en `chat.html` + pie por burbuja/imagen + campo `advertencia` en API + regla 13 del system prompt: la IA puede equivocarse en texto e imágenes, verificar con libro/profe.
