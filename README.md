# 🎓 GUION DE ESTUDIO Y DEFENSA DEL PROYECTO: "EduAsistente"
### Documento Oficial de Preparación para la Defensa de Grado / Evaluación Académica
**Proyecto:** Asistente Web Móvil de Tutoría Académica Escolar ("EduAsistente")  
**Carrera:** Ingeniería de Sistemas — Universidad de Los Andes (UNANDES)  
**Materia:** Ingeniería de Software  
**Docente / Tutor:** Ing. Cortes Montes Alejandro Marco  
**Autores:** Apaza Chavez Alejandro Nyls & Poma Jurado Cruz Cohen  
**Documento base de referencia:** *Informe Final de Ingeniería de Software (`Informe IS EA.docx.pdf`)*  

---

> 💡 **¿Cómo usar este guion de estudio?**  
> Este documento traduce todo el contenido formal de tu informe técnico de 52 páginas a un **lenguaje oral, fluido, directo y fácil de explicar**.  
> Siempre que debas mencionar un término técnico o palabra formal de Ingeniería de Software (ej. *Scrum, MoSCoW, Caja Negra, IEEE 830, Hash con Sal, Andamiaje Socrático, KaTeX, Stateless*), encontrarás una **caja explicativa inmediata** para que sepas qué significa y cómo defenderlo ante las preguntas del docente o jurado.

---

## 🧭 MAPA RÁPIDO PARA TU APERTURA (Los primeros 2 a 3 minutos)

> 🗣️ **Discurso recomendado de apertura:**  
> *"Buenos días docente y miembros del jurado. Hoy presentamos **EduAsistente**, un Asistente Web Móvil de Tutoría Académica Escolar diseñado bajo los estándares de la Ingeniería de Software para resolver un problema humano real.*  
> *Diagnosticamos el caso de la señora **Yola Chávez Espinoza**, madre de familia cuyos hijos en educación secundaria presentan dificultades en Ciencias Exactas (**Matemáticas, Física, Química**) y **Lenguaje**. En su hogar enfrentan una restricción técnica crítica: **no cuentan con computadora de escritorio ni laptop**, su único medio digital es el **teléfono celular** y no tienen apoyo pedagógico en casa.*  
> *Para dar solución, desarrollamos una plataforma web móvil inteligente, ligera y accesible 24/7 que aplica **tutoría socrática en 4 pasos**, ejercicios de práctica contextualizados, adaptación según el estilo de aprendizaje del estudiante ('aprender por asociación'), renderizado de fórmulas con **KaTeX** y diagramas conceptuales con **Cloudflare Workers AI**, todo respaldado por una base de datos serverless en **Cloudflare D1** y un backend en **Python con Flask** desplegado en **Render**."*

---

## 📚 ÍNDICE GENERAL DEL GUION

1. [El Problema Real, Pregunta de Investigación y Justificación](#1-el-problema-real-pregunta-de-investigación-y-justificación)
2. [Objetivos del Proyecto (General y Específicos por Fases)](#2-objetivos-del-proyecto-general-y-específicos-por-fases)
3. [Marco Metodológico: IEEE 830, Scrum, MoSCoW y UML](#3-marco-metodológico-ieee-830-scrum-moscow-y-uml)
4. [Librerías y Tecnologías: Justificación Técnica ("¿Por qué usamos esto?")](#4-librerías-y-tecnologías-justificación-técnica-por-qué-usamos-esto)
5. [Desarrollo por Sprints (1, 2 y 3) y Pruebas de Caja Negra](#5-desarrollo-por-sprints-1-2-y-3-y-pruebas-de-caja-negra)
6. [La Base de Datos: Modelo Entidad-Relación (8 Tablas en Cloudflare D1)](#6-la-base-de-datos-modelo-entidad-relación-8-tablas-en-cloudflare-d1)
7. [Inteligencia Artificial: Andamiaje Socrático, KaTeX y Workers AI](#7-inteligencia-artificial-andamiaje-socrático-katex-y-workers-ai)
8. [Seguridad, Ética y Disclaimer Educativo](#8-seguridad-ética-y-disclaimer-educativo)
9. [Catálogo de Endpoints de la API REST](#9-catálogo-de-endpoints-de-la-api-rest)
10. [Banco de Preguntas Típicas del Jurado y Respuestas Maestras](#10-banco-de-preguntas-típicas-del-jurado-y-respuestas-maestras)

---

## 1. EL PROBLEMA REAL, PREGUNTA DE INVESTIGACIÓN Y JUSTIFICACIÓN

### 1.1 El Diagnóstico del Problema (Árbol de Causas y Efectos)
- **Cliente:** Sra. Yola Chávez Espinoza.
- **Causas Raíz:**
  1. *Ritmo pedagógico rígido en el aula:* El profesor en el colegio avanza al ritmo del promedio y no cubre los tiempos individuales de los estudiantes.
  2. *Carencia de apoyo en el hogar:* La madre desconoce los contenidos curriculares de secundaria y no tiene recursos para clases particulares.
  3. *Brecha de dispositivos:* **No hay PC ni laptop.** Solo celulares inteligentes.
  4. *Hábitos de estudio truncados:* Los jóvenes leen por 2 horas, pero cuando surge una duda se bloquean y "no hacen nada" por falta de respuesta inmediata.
- **Efectos:** Frustración, rezago en calificaciones, desmotivación escolar y dependencia académica.

### 1.2 La Pregunta de Investigación Formal
> *"¿De qué manera el desarrollo de un asistente web móvil basado en inteligencia artificial y andamiaje pedagógico estructurado permite mejorar la comprensión conceptual y el aprendizaje autónomo en materias de ciencias exactas y lenguaje en estudiantes de secundaria que solo disponen de teléfonos inteligentes?"*

### 1.3 Las 3 Justificaciones del Proyecto
- **Justificación Técnica:** Demuestra cómo integrar microframeworks web modernos (`Flask`), bases de datos distribuidas en el borde (`Cloudflare D1`), modelos fundacionales de IA (`Google Gemini`) y herramientas tipográficas (`KaTeX`) en una arquitectura cliente-servidor optimizada para teléfonos celulares de gama media y baja.
- **Justificación Social:** Democratiza el acceso a tutoría de alta calidad para familias de escasos recursos o sin computadoras, cerrando la brecha educativa.
- **Justificación Económica:** Costo de desarrollo e infraestructura prácticamente nulo ($0 USD gracias al aprovechamiento eficiente de capas gratuitas en Cloudflare, Google AI Studio y Render).

> 💡 **Término Clave: Andamiaje Pedagógico (Scaffolding)**  
> **¿Qué significa?** Es una teoría educativa (creada por psicólogos como Vygotsky y Bruner) donde el tutor le da apoyos temporales al alumno y los va retirando a medida que el alumno aprende a resolver los problemas por sí mismo.  
> **¿Cómo aplica en el proyecto?** EduAsistente no le da el resultado masticado al alumno; le explica el concepto con una analogía, le muestra las reglas, lo guía paso a paso y luego le pide resolver un ejercicio para comprobar si entendió.

---

## 2. OBJETIVOS DEL PROYECTO (GENERAL Y ESPECÍFICOS)

### Objetivo General
Desarrollar un asistente web móvil de tutoría académica escolar accesible desde teléfonos inteligentes, que proporcione explicaciones guiadas paso a paso, ejercicios contextualizados, adaptación al estilo de aprendizaje y retroalimentación formativa de errores en Matemáticas, Física, Química y Lenguaje, con el fin de fortalecer el aprendizaje autónomo en estudiantes de secundaria.

### Objetivos Específicos (Mapeados a las 4 Fases de la Ingeniería de Software):
1. **Fase de Análisis:** Analizar y formalizar los requerimientos aplicando el estándar **IEEE 830** y la técnica de priorización **MoSCoW** para delimitar el alcance del MVP bajo entorno móvil estricto.
2. **Fase de Diseño:** Diseñar la arquitectura del software mediante diagramas **UML** (casos de uso, secuencia, comunicación), historias de usuario (plantilla Connextra) y el modelo entidad-relación normalizado de **8 tablas** en Cloudflare D1.
3. **Fase de Implementación:** Construir los módulos funcionales integrando **Flask, Gunicorn, Google Gemini SDK**, adaptación de analogías ("aprender por asociación"), soporte visual con **Cloudflare Workers AI** y notación **KaTeX**.
4. **Fase de Pruebas:** Validar la calidad, seguridad y usabilidad del sistema mediante **pruebas de caja negra** en cada Sprint de desarrollo.

---

## 3. MARCO METODOLÓGICO: IEEE 830, SCRUM, MOSCOW Y UML

Si el jurado pregunta por el proceso formal de ingeniería de software:

### 3.1 Estándar IEEE 830 (Especificación de Requerimientos de Software - SRS)
- **¿Qué es?** Es una norma internacional del Instituto de Ingenieros Eléctricos y Electrónicos (IEEE) que establece cómo redactar requerimientos de software para que sean correctos, claros, consistentes, verificables y rastreables.
- **¿Cómo se usó?** Se redactó el catálogo de Requerimientos Funcionales (**RF-01** al **RF-13**) y Requerimientos No Funcionales (**RNF-01** al **RNF-05**).

### 3.2 Priorización MoSCoW
- **M (Must have - Indispensables / MVP):** Registro, inicio de sesión, materias, envío de preguntas, explicación paso a paso, generación y corrección de ejercicios en celular.
- **S (Should have - Importantes):** Historial persistente, apoyo visual con imágenes/esquemas.
- **C (Could have - Deseables):** Adaptación automática al nivel del alumno cada 20 mensajes y perfil de gustos para analogías. *(¡En nuestro proyecto logramos implementarlos todos!)*.
- **W (Won't have this time - Para futuras versiones):** Tutoría por voz o reconocimiento de escritura a mano en fotos de cuaderno.

> 💡 **Término Clave: Metodología Ágil y Marco Scrum**  
> **¿Qué significa?** Es una forma de construir software en pequeños bloques de tiempo llamados **Sprints** (de 1 a 2 semanas cada uno), entregando en cada ciclo una parte del sistema completamente terminada y probada.  
> **¿Cómo aplica en el proyecto?** Dividimos el desarrollo en **3 Sprints**:  
> - **Sprint 1:** Acceso, seguridad y materias.  
> - **Sprint 2:** Motor de tutoría con IA, historial y personalización.  
> - **Sprint 3:** Práctica interactiva, evaluación y retroalimentación formativa.

### 3.3 Historias de Usuario (Plantilla Connextra)
Todas las historias del Product Backlog siguen el formato formal:  
> *"**Como** [rol de usuario], **quiero** [funcionalidad] **para** [beneficio o valor de negocio]."*

---

## 4. LIBRERÍAS Y TECNOLOGÍAS: JUSTIFICACIÓN TÉCNICA

Aquí tienes la respuesta exacta ante la típica pregunta: **"¿Por qué elegiste esta tecnología y no otra?"**:

| Tecnología / Librería | ¿Qué es en palabras simples? | ¿Por qué se eligió? (Justificación Técnica) |
| :--- | :--- | :--- |
| **Python 3** | Lenguaje de programación base. | Sintaxis limpia, altamente legible y soporte nativo indiscutible para las principales APIs de Inteligencia Artificial. |
| **Flask** | Microframework web para el backend. | A diferencia de *Django* (que es pesado y tiene miles de archivos innecesarios), Flask es minimalista, rápido, no impone estructuras rígidas y permite crear endpoints API en pocas líneas. |
| **Gunicorn** | Servidor web WSGI de producción. | El servidor interno de Flask es solo para pruebas locales. Gunicorn administra múltiples procesos de trabajo (*workers*) en Linux (Render) para soportar múltiples conexiones simultáneas sin congelarse. |
| **Google GenAI SDK (`google-genai`)** | Librería cliente de Google Gemini. | Es la versión oficial más moderna de Google. Permite inspeccionar qué modelos están activos dinámicamente (`client.models.list()`) e interactuar con Gemini 2.5 Flash y 1.5 Flash con latencia ultra baja. |
| **Cloudflare D1** | Base de datos SQLite Serverless en la nube. | En servicios como Render, el disco duro es efímero (se borra al reiniciar). Cloudflare D1 almacena la base de datos en la nube con réplicas globales, costo cero y consultas SQL relacionales clásicas. |
| **Requests** | Conector HTTP para Python. | Permite enviar consultas SQL en formato JSON mediante llamadas HTTP seguras (`requests.post`) hacia la API de Cloudflare sin depender de controladores pesados de base de datos. |
| **Cloudflare Workers AI** | Motor de inferencia de IA en la nube. | Genera ilustraciones educativas bajo demanda (`@cf/black-forest-labs/flux-1-schnell` o *Stable Diffusion*) para ayudar a estudiantes visuales en temas abstractos (células, átomos, vectores). |
| **Werkzeug (`werkzeug.security`)** | Módulo de seguridad criptográfica. | Cumple el requerimiento **RNF-05**. Aplica algoritmos de hashing con sal (`pbkdf2:sha256` o `scrypt`) para que ninguna contraseña se almacene jamás en texto plano. |
| **KaTeX 0.16.11 (CDN)** | Motor de renderizado matemático web. | Creado por Khan Academy. Es hasta 10 veces más rápido que *MathJax*. Renderiza código LaTeX (`$...$` o `$$...$$`) como fracciones, raíces y exponentes reales directamente en la pantalla del celular sin consumir datos excesivos. |
| **HTML5, CSS3 puro y JavaScript Vanilla** | Frontend nativo sin frameworks. | **Decisión crítica de ingeniería:** No usamos *React, Angular o Vue* porque descargan paquetes de varios megabytes que agotan el plan de datos y enlentecen celulares modestos. El código nativo vuela en cualquier smartphone. |
| **Python-Dotenv** | Gestor de variables de entorno. | Lee el archivo `.env` en local o las variables del panel de Render, protegiendo las credenciales de API para no subirlas nunca a GitHub por error. |

> 💡 **Término Clave: WSGI (Web Server Gateway Interface)**  
> **¿Qué significa?** Es el traductor estándar entre los servidores de internet (como Nginx o Gunicorn) y las aplicaciones hechas en Python (como Flask).  
> **¿Cómo aplica en el proyecto?** Render ejecuta `gunicorn main:app --bind 0.0.0.0:$PORT` para atender a los usuarios de manera rápida y estable.

---

## 5. DESARROLLO POR SPRINTS Y PRUEBAS DE CAJA NEGRA

El desarrollo se organizó en 3 Sprints formales. En cada uno se ejecutaron **Pruebas de Aceptación de Caja Negra**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PRODUCT BACKLOG                                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
   [ SPRINT 1 ]                  [ SPRINT 2 ]                  [ SPRINT 3 ]
   Autenticación &               Tutoría Socrática,            Práctica Interactiva &
   Gestión de Materias           Historial & Perfil            Evaluación Formativa
   • HU-01: Registro             • HU-06: Preguntas & Chat     • HU-10: Generar Ejercicios
   • HU-02: Inicio Sesión        • HU-07: Tutoría Socrática    • HU-11: Enviar Solución
   • HU-03: Cierre Sesión        • HU-08: Historial en D1      • HU-12: Retroalimentación
   • HU-04: Ver Materias         • HU-09: Apoyo Visual AI      • HU-13: Progreso y Nivel
   • HU-05: Crear Materia        • Perfil de Asociación (RF12) • Métricas aciertos (RF13)
```

> 💡 **Término Clave: Pruebas de Caja Negra (Black Box Testing)**  
> **¿Qué significa?** Son pruebas donde el evaluador prueba el sistema desde afuera (como un usuario normal), ingresando datos y verificando que la salida sea la correcta, sin mirar el código interno.  
> **¿Cómo aplica en el proyecto?** En el informe (páginas 28-29, 35-36 y 43-44) se documentaron casos de prueba como `CP-S1-01` (Registro válido) o `CP-S1-02` (Rechazo de correo duplicado por restricción `UNIQUE` en la base de datos). Todas las pruebas obtuvieron estado **PASÓ**.

### Resumen de Pruebas Destacadas del Informe:
1. **CP-S1-01 (Registro con datos válidos):** Se envía nombre, correo y clave $\rightarrow$ se guarda con hash y sal en D1 $\rightarrow$ **PASÓ**.
2. **CP-S1-02 (Control de correo duplicado):** Se intenta registrar un correo ya existente $\rightarrow$ la BD rechaza por `UNIQUE` y el backend retorna error 400 $\rightarrow$ **PASÓ**.
3. **CP-S1-03 (Login con clave errónea):** `check_password_hash` da falso y no permite iniciar sesión $\rightarrow$ **PASÓ**.
4. **CP-S2-04 (Persistencia del chat):** El estudiante envía una pregunta, recarga el navegador y la conversación sigue visible gracias a `GET /api/historial` $\rightarrow$ **PASÓ**.
5. **CP-S3-08 (Evaluación con error en el procedimiento):** El estudiante da una respuesta numérica incorrecta en un problema de física $\rightarrow$ la IA detecta en qué paso falló, lo anima con empatía y le muestra la solución correcta $\rightarrow$ **PASÓ**.

---

## 6. LA BASE DE DATOS: MODELO ENTIDAD-RELACIÓN (8 TABLAS)

El sistema utiliza una base de datos relacional normalizada en **Cloudflare D1** (`basedatos.sql`), compuesta por 8 tablas:

1. **`usuarios`**: Almacena `id`, `nombre`, `email` (con restricción `UNIQUE`) y `contrasena` (hash con sal).
2. **`materias`**: Contiene las 4 materias base (`es_base = 1`) más las materias privadas creadas por los estudiantes (`usuario_id`).
3. **`perfiles_aprendizaje`**: Cumple el **RF-12**. Guarda el estilo o intereses del alumno (ej. *"aprendo con ejemplos de cocina o fútbol"*). Relación 1:1 con `usuarios`.
4. **`nivel_usuario`**: Cumple el **RF-11** y **RF-13**. Registra el nivel por materia (`basico`, `intermedio`, `avanzado`), el total de mensajes, intentos y aciertos de ejercicios.
5. **`mensajes`**: Registra cada duda formulada por el estudiante con fecha, `usuario_id` y `materia_id`.
6. **`respuestas`**: Guarda la explicación paso a paso de la IA conectada mediante Foreign Key a `mensajes(id)`. Incluye la columna `imagen_url` si se generó una ilustración.
7. **`ejercicios`**: Repositorio de problemas generados por la IA con enunciado, respuesta esperada y nivel de dificultad.
8. **`respuestas_ejercicios`**: Registra cada respuesta enviada por el estudiante, si fue correcta (`es_correcta = 1/0`), la retroalimentación recibida y la fecha.

> 💡 **Término Clave: Restricción UNIQUE y Clave Foránea (Foreign Key)**  
> **¿Qué significan?**  
> - `UNIQUE`: Regla que prohíbe que existan dos filas con el mismo valor (ej. dos cuentas con el mismo correo).  
> - `FOREIGN KEY`: Un enlace que garantiza que un registro hijo (como un mensaje) pertenezca obligatoriamente a un registro padre existente (como un usuario registrado).  
> **¿Cómo aplica en el proyecto?** Evita registros huérfanos y garantiza integridad referencial en Cloudflare D1.

---

## 7. INTELIGENCIA ARTIFICIAL: ANDAMIAJE SOCRÁTICO, KATEX Y WORKERS AI

En `gemini_helper.py` reside la lógica pedagógica del tutor virtual:

### 7.1 El Método Socrático y las 4 Secciones Obligatorias
El modelo no responde como un chatbot ordinario, sino que sigue una plantilla pedagógica estricta:
1. **Concepto Clave:** Explicado con lenguaje llano y una analogía del mundo real.
2. **Fórmulas y Reglas:** Específicas para la materia, formateadas con KaTeX.
3. **Procedimiento Paso a Paso:** Desglose numerado ("Paso 1", "Paso 2") sin asumir conocimientos previos del estudiante.
4. **Conclusión y Consejo Práctico:** Regla mnemotécnica o tip para no olvidar el tema.

### 7.2 Renderizado Tipográfico con KaTeX
- Transforma código matemático como `$\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$` en ecuaciones tipográficas perfectas.
- Permite que las fórmulas químicas ($H_2O$, $CO_2$, $H_2SO_4$) se lean con subíndices exactos en la pantalla del celular.

### 7.3 Generación Visual con Cloudflare Workers AI
En `cloudflare_ai.py` se implementaron dos modos de apoyo visual:
- **Modo Preciso (`POST /api/ilustrar`):** Emplea modelos Text-to-Image como `@cf/black-forest-labs/flux-1-schnell` con un prompt enriquecido para generar diagramas esquemáticos en blanco y negro con trazo grueso y fondo limpio.
- **Modo Creativo / Esquema (`POST /api/esquema`):** Produce un esquema conceptual estructurado de texto y viñetas para resumir las ideas visualmente sin consumo excesivo de inferencia.

### 7.4 Detección Dinámica de Modelos y Mecanismo Fallback
- **Problema:** En el desarrollo de software con IA, las APIs actualizan y deprecian nombres de modelos frecuentemente (provocando errores `404 NOT_FOUND`).
- **Nuestra Solución:** `gemini_helper.py` consulta en tiempo real `client.models.list()`. Si un modelo se satura, el código salta automáticamente al siguiente (`gemini-2.5-flash` $\rightarrow$ `gemini-1.5-flash` $\rightarrow$ `gemini-1.5-pro`) sin interrumpir la sesión del estudiante.

---

## 8. SEGURIDAD, ÉTICA Y DISCLAIMER EDUCATIVO

Si el docente pregunta sobre la ética y la seguridad del sistema:

1. **Seguridad Criptográfica (RNF-05):** Las contraseñas se almacenan mediante `generate_password_hash` con algoritmo `scrypt` o `pbkdf2` con sal aleatoria. Las sesiones de Flask se firman mediante cookies encriptadas con `SECRET_KEY`.
2. **Aislamiento Multiusuario:** Las consultas SQL aplican aislamiento estricto:
   ```sql
   WHERE usuario_id = ? AND materia_id = ?
   ```
   Un estudiante jamás puede ver los mensajes, preguntas o ejercicios de otro.
3. **Disclaimer Ético de Inteligencia Artificial (Apartado 8.7.6 del Informe):**  
   En la interfaz del dashboard y del chat se incluye un aviso transparente informando que EduAsistente es una **herramienta de apoyo pedagógico** y que el estudiante debe contrastar siempre sus dudas con sus libros oficiales o con su profesor del colegio, fomentando el pensamiento crítico y el uso responsable de la IA.

---

## 9. CATÁLOGO DE ENDPOINTS DE LA API REST

| Método | Endpoint | Sprint | Descripción Funcional |
| :---: | :--- | :---: | :--- |
| `POST` | `/api/register` | Sprint 1 | Registra nuevo estudiante con hash seguro (RNF-05). |
| `POST` | `/api/login` | Sprint 1 | Valida credenciales e inicializa la cookie de sesión. |
| `POST` | `/api/logout` | Sprint 1 | Destruye la sesión activa en el servidor. |
| `GET` | `/api/sesion` | Sprint 1 | Verifica el estado de autenticación y nombre del usuario. |
| `GET` | `/api/materias` | Sprint 1 | Obtiene las 4 materias base más las materias privadas. |
| `POST` | `/api/materias` | Sprint 1 | Registra una nueva materia personalizada del estudiante. |
| `POST` | `/api/chat` | Sprint 2 | Procesa la duda del alumno, consulta D1 y responde con Gemini. |
| `GET` | `/api/historial` | Sprint 2 | Recupera el historial de chat por usuario y materia. |
| `GET/PUT`| `/api/perfil` | Sprint 2 | Consulta o actualiza el estilo de aprendizaje (RF-12). |
| `POST` | `/api/ilustrar` | Sprint 2 | Genera diagrama visual con Cloudflare Workers AI. |
| `POST` | `/api/esquema` | Sprint 2 | Genera esquema conceptual en texto estructurado. |
| `POST` | `/api/ejercicio` | Sprint 3 | Genera un ejercicio práctico adaptado al tema (RF-08). |
| `POST` | `/api/revisar` | Sprint 3 | Evalúa la solución, da feedback y actualiza aciertos (RF-09/10/13). |
| `GET` | `/api/modelos` | Soporte | Monitorea qué modelos de Gemini están activos en la cuenta. |

---

## 10. BANCO DE PREGUNTAS TÍPICAS DEL JURADO Y RESPUESTAS MAESTRAS

### ❓ Pregunta 1: "¿Por qué afirman que el sistema está diseñado exclusivamente para celulares si es una página web?"
> **Respuesta:**  
> *"Porque se diseñó bajo la filosofía **Mobile-First (Móvil Primero)**. Los elementos táctiles tienen un tamaño mínimo de 48 píxeles para ser cómodamente pulsados con los dedos, las cuadrículas del dashboard son de 2x2 para pantallas angostas, el chat ajusta su campo de texto al teclado virtual del smartphone y el peso de las páginas es inferior a 50 KB para que cargue velozmente incluso con conexiones móviles 3G o 4G inestables."*

### ❓ Pregunta 2: "¿Cómo manejan el problema de que los modelos de Inteligencia Artificial 'no tienen memoria'?"
> **Respuesta:**  
> *"Los modelos de lenguaje son por naturaleza **stateless** (sin estado propio). La memoria reside en nuestra base de datos **Cloudflare D1**. Cada vez que el estudiante formula una nueva pregunta, el backend recupera los últimos mensajes de esa materia y se los envía como contexto a Gemini en el mismo cuerpo de la petición. De esta forma, el modelo siempre sabe de qué venían hablando sin saturar la memoria."*

### ❓ Pregunta 3: "¿Qué diferencia a EduAsistente de que el alumno simplemente use ChatGPT directamente?"
> **Respuesta:**  
> *"ChatGPT estándar tiende a entregar las respuestas resueltas de inmediato, fomentando que el alumno copie y pegue la tarea sin reflexionar. EduAsistente está calibrado mediante un **System Prompt socrático** que prohíbe dar la tarea hecha: divide el aprendizaje en 4 pasos didácticos, evalúa las respuestas paso a paso indicando con empatía dónde se cometió el error, adapta analogías a los gustos del alumno (RF-12) y guarda el progreso cuantitativo de aciertos por materia (RF-13)."*

### ❓ Pregunta 4: "¿Por qué no utilizaron una base de datos local como `sqlite3.connect('database.db')`?"
> **Respuesta:**  
> *"Porque en plataformas de computación en la nube como **Render**, los contenedores son efímeros. Esto significa que cada vez que el servicio se reinicia o se despliega una nueva versión, el disco duro local se restaura y los datos de los estudiantes se habrían borrado. Con **Cloudflare D1**, la base de datos SQLite vive en la infraestructura distribuida de Cloudflare, asegurando persistencia permanente y alta disponibilidad sin costo."*

### ❓ Pregunta 5: "¿Cómo verificaron que el sistema funciona correctamente y cumple con los requerimientos?"
> **Respuesta:**  
> *"Siguiendo las mejores prácticas de la Ingeniería de Software, definimos una **Matriz de Trazabilidad** que vincula cada Requerimiento Funcional con una Historia de Usuario del Backlog y con su respectivo endpoint en la API REST. Además, en cada Sprint ejecutamos **Pruebas de Caja Negra** (documentadas en las tablas de aceptación del informe técnico), comprobando que todos los casos de prueba obtuvieron estado PASÓ."*

---

## 🏆 SÍNTESIS FINAL PARA EL CIERRE DE TU DEFENSA

> 🗣️ *"Para concluir, EduAsistente demuestra cómo la Ingeniería de Software rigurosa —desde el levantamiento formal de necesidades con IEEE 830 y MoSCoW hasta el diseño en Sprints con Scrum y pruebas de caja negra— permite construir soluciones tecnológicas de alto impacto social. Logramos un software funcional, seguro, rápido y de costo cero que transforma un teléfono celular común en un tutor escolar paciente y de calidad para estudiantes que más lo necesitan. Muchas gracias, quedamos a disposición de sus preguntas."*
