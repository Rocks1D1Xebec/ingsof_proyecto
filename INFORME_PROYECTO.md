# 📘 INFORME DEL PROYECTO: ASISTENTE ESCOLAR (EduAsistente v1.2)

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
| **RNF-05** | **Protección**: Contraseñas con hash y sal. | ✅ Completado | `werkzeug.security` en `POST /api/register` y `/api/login` (con migración automática de claves antiguas en texto plano). |
| **Accesibilidad** | **Lectura en voz alta**: las explicaciones se leen al estudiante. | ✅ Completado | Toggle `🔊 Voz` + botón por burbuja en `chat.html` → `POST /api/audio-verbalizado` → `verbalizar_para_audio()` + `speechSynthesis`. |
| **Aislamiento** | **Materias privadas ajenas bloqueadas**. | ✅ Completado | `materia_visible_para()` en `/api/chat`, `/api/historial` y `/api/ejercicio` (HTTP 403). |

---

## 3. 🛠️ Tecnologías y Librerías Utilizadas

| Componente | Tecnología / Librería | Justificación y Uso |
| :--- | :--- | :--- |
| **Backend** | `Python 3` + `Flask` | Micro-framework ligero que permite estructurar rutas API claras y servir los archivos web sin configuraciones complejas. |
| **Servidor en la Nube** | `Gunicorn` | Servidor de producción WSGI utilizado por **Render** para desplegar aplicaciones Python de forma eficiente. |
| **Base de Datos** | `Cloudflare D1` (SQLite Serverless) | Base de datos relacional en la nube que persiste usuarios, materias, mensajes, respuestas, ejercicios, niveles y perfiles. Acceso vía API REST desde `cloudflare_d1.py`. |
| **Imágenes educativas** | `Cloudflare Workers AI` | Generación bajo demanda de ilustraciones (`/api/ilustrar`, modo Preciso/Creativo) desde `cloudflare_ai.py`; el esquema alternativo (`/api/esquema`) devuelve etiquetas y el frontend dibuja un SVG determinista. |
| **Hosting / Despliegue** | `Render` (Web Service + `Gunicorn`) | Ejecución en producción con `gunicorn main:app --bind 0.0.0.0:$PORT`. Variables en el dashboard de Render. |
| **Conector HTTP** | `Requests` | Librería estándar de Python para realizar peticiones HTTP seguras hacia la API REST de Cloudflare D1. |
| **Inteligencia Artificial** | `Google GenAI SDK` (`google-genai`) | SDK oficial para conectar con los modelos de **Google Gemini** y generar explicaciones pedagógicas adaptadas al nivel escolar. Soporta varias API Keys (`API1`, `API2`, `API`, `GEMINI_API_KEY`) con rotación automática de clave y modelo. |
| **Voz (Accesibilidad)** | `Web Speech API` (`speechSynthesis`) | Síntesis de voz nativa del navegador, sin librerías ni descargas extra; lee en español las explicaciones verbalizadas por el backend. |
| **Seguridad** | `Werkzeug` (`werkzeug.security`) | Hash con sal de contraseñas (`generate/check_password_hash`). Viene como dependencia de Flask (RNF-05). |
| **Renderizado matemático** | `KaTeX 0.16.11` (CDN) | Renderiza fórmulas LaTeX `$...$` / `$$...$$` en `chat.html` (CSS + `katex.min.js` + `auto-render`). |
| **Variables de Entorno** | `Python-Dotenv` | Permite cargar configuraciones y llaves secretas desde el archivo `.env` o desde el panel de Render. |
| **Frontend** | `HTML5`, `CSS3` y `JavaScript Vanilla` | Interfaz limpia, responsiva, moderna y sin dependencias pesadas (React, Vue, etc.), facilitando su mantenimiento y velocidad de carga. |

---

## 4. 📂 Estructura de Archivos del Proyecto

```plaintext
ingsof_proyecto/
│
├── .env                      # Variables de entorno (credenciales de Cloudflare y Gemini)
├── requirements.txt          # Dependencias de Python para Render
├── basedatos.sql             # Esquema SQL (8 tablas) para Cloudflare D1
├── init_db.py                # Script manual de inicialización de tablas y datos
│
├── main.py                   # Servidor web principal Flask y endpoints de la API
├── cloudflare_d1.py          # Módulo de conexión y consultas a Cloudflare D1
├── cloudflare_ai.py          # Generador de imágenes educativas (Workers AI) + esquemas
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
├── README.md                 # Guion de estudio y defensa del proyecto
├── cosas faltantes.md        # Matriz de cumplimiento documentación vs código
└── INFORME_PROYECTO.md       # Este informe técnico
```

---

## 5. 🔍 Explicación Detallada del Código y Funcionamiento

### A. Backend Principal (`main.py`)
El archivo `main.py` es el núcleo del backend. Administra las rutas del servidor y las peticiones enviadas desde el navegador:
- **Autenticación Segura con Hash (RNF-05)**:
  - `POST /api/register`: Recibe nombre, correo y contraseña. Si el correo no existe, crea el registro con `generate_password_hash` (werkzeug con sal) y asigna sesión activa.
  - `POST /api/login`: Busca por correo y verifica con `check_password_hash`. Incluye migración automática de cuentas antiguas en texto plano al hash.
  - `GET /api/sesion`: Retorna si el visitante está autenticado y su nombre para mostrarlo en el menú superior.
  - `POST /api/logout`: Limpia las cookies de sesión y desconecta al usuario.
- **Gestión de Materias**:
  - `GET /api/materias`: Devuelve la lista de materias guardadas en Cloudflare D1.
  - `POST /api/materias`: Permite a los estudiantes añadir materias personalizadas (ej. Historia, Biología).
- **Perfil de Aprendizaje (RF-12)**:
  - `GET /api/perfil`: Devuelve el estilo de aprendizaje guardado del estudiante.
  - `PUT /api/perfil`: Guarda o edita el texto "cómo aprendo mejor" (tabla `perfiles_aprendizaje`).
- **Tutoría con IA y Ejercicios**:
  - `POST /api/chat`: Recibe la pregunta del estudiante, consulta el historial previo en la base de datos, envía el contexto (perfil, nivel y progreso) a Gemini, guarda pregunta y respuesta y devuelve el campo `advertencia` de disclaimer. Verifica antes que la materia le pertenezca al usuario.
  - `GET /api/historial`: Carga la conversación previa de la materia seleccionada.
  - `POST /api/ejercicio`: Solicita a Gemini un problema práctico con enunciado y solución, lo persiste en la BD y también como par de mensaje/respuesta en el historial de chat. Si la IA falla, devuelve `respaldo: true` con el detalle.
  - `POST /api/revisar`: Envía la solución del estudiante a Gemini para evaluar si es correcta, guarda el resultado en `respuestas_ejercicios`, suma intentos/aciertos (RF-13) y también lo replica en el historial.
- **Apoyo Visual**:
  - `POST /api/ilustrar`: Re-analiza pregunta+respuesta con Gemini (`generar_prompt_imagen`) y genera la imagen con Cloudflare Workers AI según el modo Preciso/Creativo.
  - `POST /api/esquema`: Devuelve las etiquetas del concepto para que el navegador dibuje un esquema SVG determinista, sin inferencia de imagen.
- **Accesibilidad (Voz)**:
  - `POST /api/audio-verbalizado`: Convierte la explicación a texto de locución en español (fórmulas LaTeX a palabras habladas), usando Gemini con respaldo de reglas regex (`limpiar_formulas_reglas`).
- **Soporte**:
  - `GET /api/modelos`: Endpoint público para consultar en JSON qué modelos de Gemini están activos en la cuenta.

---

### B. Base de Datos en la Nube (`cloudflare_d1.py`)
Conecta la aplicación con la base de datos Cloudflare D1 mediante peticiones HTTP a su API REST:
- **Auto-inicialización Segura (`asegurar_inicializacion()`)**:
  Al encender el servidor en Render, este método verifica y crea automáticamente las 8 tablas (`usuarios`, `materias`, `perfiles_aprendizaje`, `nivel_usuario`, `mensajes`, `respuestas`, `ejercicios`, `respuestas_ejercicios`) y puebla las 4 materias base globales (Matemáticas, Física, Química, Lenguaje). Ver esquema completo en `basedatos.sql`.
- **Tolerancia a Fallos**:
  Si la base de datos tarda en responder o hay un retraso de conexión, las funciones de chat capturan la excepción sin interrumpir el flujo, garantizando que el estudiante siempre reciba la respuesta de la IA.

---

### C. Inteligencia Artificial Adaptativa (`gemini_helper.py` y `listar_modelos.py`)
- **Detección Dinámica de Modelos**:
  Para evitar errores de modelos obsoletos (como `404 NOT_FOUND` en versiones anteriores), `gemini_helper.py` consulta en tiempo real qué modelos tiene habilitados la API Key del usuario (`client.models.list()`).
- **Sistema de Respaldo (*Fallback*)**:
  Si un modelo específico no responde o se encuentra saturado, el sistema cambia automáticamente al siguiente modelo disponible de la lista (ej. `gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`) sin mostrar mensajes de error al usuario. Igual rotación se aplica a las **API Keys** (`API1`, `API2`, `API`, `GEMINI_API_KEY`) y, si el modo JSON es rechazado por un modelo, se reintenta sin `response_mime_type`.
- **Prompts Pedagógicos**:
  Configura a la IA bajo el rol de **"EduAsistente"**, forzándola a responder siempre en español, con tono empático, dividiendo las explicaciones en 4 secciones claras (Concepto, Fórmulas/Reglas, Procedimiento paso a paso y Conclusión).
- **Verbalización para Voz (`verbalizar_para_audio`)**:
  Reescribe la respuesta como locución en español («raíz cuadrada de cuatro», «tres cuartos», «metros por segundo al cuadrado»), eliminando Markdown, HTML y símbolos; si la IA no responde, aplica `limpiar_formulas_reglas()` con expresiones regulares.
- **Robustez de contexto (`_limpiar_historial`)**:
  Recorta el historial (6 mensajes / 600 caracteres) y elimina imágenes `base64` y etiquetas HTML antes de enviarlo a Gemini, para no agotar la memoria ni el tiempo del worker en Render.

---

### D. Frontend Interactivo
- **`register.html`**:
  - Se corrigió el campo de nombre eliminando valores predeterminados fijos. Ahora incluye un texto de sugerencia (`placeholder="Ej. Carlos"`) que se borra automáticamente en cuanto el usuario comienza a escribir.
  - Validaciones en cliente y servidor: campos obligatorios y correo con terminación `@gmail.com`; alterna la visibilidad de la contraseña.
- **`login.html`**:
  - Formulario limpio con botón para alternar la visibilidad de la contraseña (👁 / 🙈) y mensajes de error claros en caso de credenciales inválidas.
- **`dashboard.html`**:
  - Muestra el nombre real del estudiante autenticado.
  - Carga las materias dinámicamente desde Cloudflare D1 con tarjetas estilizadas y temáticas.
  - Incluye una ventana modal para añadir nuevas materias en un clic.
  - Modal **"Dile a la IA cómo entiendes mejor"** para editar el perfil de aprendizaje (RF-12) con `GET/PUT /api/perfil`.
- **`chat.html`**:
  - Muestra el encabezado de la materia en estudio (ej. Física, Matemáticas) y un botón **"← Cambiar materia"** que se oculta al bajar el scroll y reaparece al subir.
  - Carga el historial previo de conversación y envía dudas en tiempo real.
  - Renderiza la respuesta con un **parser de Markdown propio** (`formatearMarkdown`: títulos, listas, negritas, reglas) y **KaTeX** para las fórmulas, protegiendo la matemática antes de escapar el HTML.
  - Acciones por burbuja: **🔊 Escuchar** (voz), **📋 Copiar**, **🎯 Practicar este tema** y **🎨 Ver ilustración**.
  - **🎨 Ver ilustración** abre un selector: *Imagen IA* (`/api/ilustrar`, modo guardado por materia) o *Esquema texto* (`/api/esquema` → SVG dibujado en el navegador).
  - **Voz global:** el toggle `🔊 Voz` de la barra superior guarda su estado en `localStorage` y, al activarse, lee automáticamente cada respuesta nueva; el backend verbaliza las fórmulas antes de pronunciarlas.
  - El botón **"🎯 Dame un ejercicio de práctica"** abre una caja interactiva donde el estudiante escribe su solución y recibe retroalimentación inmediata con verificación.

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

2. **Variables de Entorno en el Dashboard de Render** (nombres exactos):
   - `API`: Clave de Google Gemini (`AIzaSy...`). Opcionales y acumulativas: `API1`, `API2`, `GEMINI_API_KEY` (el backend rota entre ellas si una se satura).
   - `CLOUDFLARE_ACCOUNT_ID`: ID de la cuenta de Cloudflare.
   - `CLOUDFLARE_DATABASE_ID`: ID de la base D1.
   - `CLOUDFLARE_API_TOKEN`: Token con permisos D1 (lectura/escritura).
   - `CLOUDFLARE_API_TOKEN_IMAGEN`: Token para Workers AI (si no se define, se reutiliza `CLOUDFLARE_API_TOKEN`).
   - `SECRET_KEY`: (opcional, recomendado) Firma de sesiones Flask. Si no se define, se usa valor por defecto.

3. **Verificación de Modelos**:
   Una vez desplegado, puedes abrir en tu navegador:
   `https://<tu-subdominio-en-render>.onrender.com/api/modelos`
   para comprobar la lista de modelos de IA activos en tu cuenta.

---

## 8. ✅ Conclusión

El proyecto **EduAsistente v1.2** se encuentra completamente operativo y optimizado para la nube. Posee una estructura limpia, contraseñas protegidas con hash `werkzeug` con sal (RNF-05), conexión persistente a Cloudflare D1, integración inteligente con Google Gemini, apoyo visual bajo demanda (imagen IA o esquema SVG), lectura en voz alta de las explicaciones y una interfaz de usuario atractiva, accesible y orientada a estudiantes de secundaria.

## 9. 🆕 v1.1 — Ilustración coherente Preciso/Creativo + disclaimer IA

* **Solo-manual:** `/api/chat` ya no genera imagen automática; solo texto primero. La imagen nace al pulsar `🎨 Ver ilustración`.
* **Re-analizador:** `/api/ilustrar` recibe `{pregunta, respuesta, materia, modo}`, llama `gemini_helper.generar_prompt_imagen()` —prompt visual en inglés coherente con la explicación— y luego `cloudflare_ai.generar_imagen_educativa(prompt, modo)` con `negative_prompt`.
* **Toggle estudiante:** `🎯 Preciso` —diagrama lineal sin texto dibujado, etiquetas como HTML— para Matemáticas/Física/Química; `🎨 Creativo` —cartoon con etiquetas cortas— para Lenguaje/decorativo. Persistente por materia en `localStorage`.
* **Fidelidad:** envolver en PDF no corrige difusión; este cambio sí mejora coherencia porque el prompt nace de la respuesta final, no de la duda inicial.
* **Disclaimer:** banner en `chat.html` + pie por burbuja/imagen + campo `advertencia` en API + regla 13 del system prompt: la IA puede equivocarse en texto e imágenes, verificar con libro/profe.

---

## 10. 🆕 v1.2 — Accesibilidad auditiva + esquema SVG + refuerzo de seguridad

* **Lectura en voz alta (Nuevo):** toggle `🔊 Voz` en la navbar del chat (estado en `localStorage.lectura_voz_activa`) y botón **🔊 Escuchar / ⏹ Detener** en cada burbuja. Si la voz está activa, cada respuesta nueva se lee sola.
* **Verbalización de fórmulas:** `POST /api/audio-verbalizado` → `gemini_helper.verbalizar_para_audio()` reescribe `$\frac{3}{4}$`, `$\sqrt{16}$`, `m/s²` y `$H_2O$` como texto hablado en español; respaldos en cascada con `limpiar_formulas_reglas()` (servidor) y `verbalizarReglasCliente()` (navegador). La síntesis la hace `speechSynthesis` con voz `es-ES` a velocidad 0.95.
* **Selector de visualización:** `🎨 Ver ilustración` ya no genera la imagen directamente; pregunta *Imagen IA* o *Esquema texto*. El modo (Preciso/Creativo) se recuerda por materia en `localStorage` (`modo_imagen_<materia>`), con *Creativo* por defecto en Lenguaje.
* **Esquema determinista:** `/api/esquema` devuelve solo `etiquetas` (hasta 5) y `dibujarEsquemaSVG()` dibuja en el navegador un nodo central unido a sus hojas con letras reales: cero inferencia, cero costo, legible siempre.
* **Registro más estricto:** el correo debe terminar en `@gmail.com` y se rechaza el duplicado antes de tocar la BD.
* **Aislamiento de materias privadas:** `materia_visible_para()` valida el acceso en `/api/chat`, `/api/historial` y `/api/ejercicio` (HTTP 403 si la materia no es base ni propia).
* **Varias API Keys:** rotación `API1` → `API2` → `API` → `GEMINI_API_KEY` junto a la rotación de modelos, para que una clave cuota no corte la tutoría.
* **Ejercicios en el historial:** `/api/ejercicio` y `/api/revisar` persisten también su par mensaje/respuesta en el chat, de modo que al salir y volver el ejercicio y la corrección siguen visibles.
