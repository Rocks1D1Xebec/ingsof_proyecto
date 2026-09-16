# HISTORIAS DE USUARIO - EduAsistente V1.0 (MVP)

## Proyecto: Asistente Web Móvil de Tutoría Académica Escolar
## Cliente: Yola Chávez Espinoza

---

## HU-01: Registro de Cuenta

**Como** estudiante de secundaria,
**quiero** crear una cuenta con mi nombre, correo y contraseña,
**para** poder acceder al asistente desde mi celular.

**Criterios de Aceptación:**

- El estudiante está en la página principal y presiona el botón "Crear Cuenta".
- El sistema muestra un formulario con los campos: Nombre, Correo y Contraseña.
- El estudiante ingresa sus datos y presiona "Registrarse".
- El sistema valida que los campos no estén vacíos, registra la cuenta en la BD e inicia sesión automáticamente.
- Si el correo ya está registrado, el sistema muestra: "Este usuario ya está registrado. Por favor, inicia sesión".
- Si algún campo está vacío, el sistema muestra: "Por favor, completa todos los campos".

**Tareas:**

- [ ] El sistema debe permitir almacenar datos de usuario (nombre, correo, contraseña).
- [ ] El sistema debe validar que ningún campo quede vacío al registrarse.
- [ ] El sistema debe validar que el correo no esté duplicado.
- [ ] El sistema debe almacenar la contraseña de forma segura.
- [ ] El sistema debe iniciar sesión automáticamente después del registro.
- [ ] El sistema debe redirigir al estudiante a la pantalla de materias tras el registro.

---

## HU-02: Inicio de Sesión

**Como** estudiante con cuenta registrada,
**quiero** iniciar sesión con mi correo y contraseña,
**para** acceder a las funcionalidades del asistente.

**Criterios de Aceptación:**

- El estudiante está en la pantalla de login, ingresa su correo y contraseña y presiona "Entrar".
- El sistema valida las credenciales y muestra la pantalla de materias.
- Si las credenciales son incorrectas, el sistema muestra: "Usuario o contraseña no coinciden. Intenta de nuevo".
- La sesión se mantiene activa mientras el navegador esté abierto.

**Tareas:**

- [ ] El sistema debe permitir validar credenciales de usuario.
- [ ] El sistema debe mantener la sesión del estudiante activa.
- [ ] El sistema debe redirigir a la pantalla de materias tras login exitoso.
- [ ] El sistema debe mostrar un mensaje de error si las credenciales son incorrectas.

---

## HU-03: Cierre de Sesión

**Como** estudiante con sesión activa,
**quiero** cerrar sesión de forma segura,
**para** proteger mi cuenta cuando termine de usar el asistente.

**Criterios de Aceptación:**

- El estudiante tiene sesión activa y toca el botón "Cerrar Sesión" en la barra superior.
- El sistema destruye la sesión y redirige a la pantalla de inicio de sesión.
- Si se intenta acceder a funciones protegidas sin sesión, el sistema redirige al login.

**Tareas:**

- [ ] El sistema debe permitir cerrar la sesión del estudiante.
- [ ] El sistema debe eliminar los datos de sesión al cerrar.
- [ ] El sistema debe redirigir a la pantalla de login tras cerrar sesión.
- [ ] El sistema debe bloquear el acceso a funciones protegidas sin sesión activa.

---

## HU-04: Selección de Materia

**Como** estudiante con sesión activa,
**quiero** elegir la materia que deseo consultar (Matemáticas, Física, Química o Lenguaje),
**para** que el asistente se enfoque en el tema que necesito.

**Criterios de Aceptación:**

- El estudiante acaba de iniciar sesión y el sistema muestra una cuadrícula con 4 botones grandes: Matemáticas, Física, Química, Lenguaje.
- El estudiante toca una materia y el sistema carga la pantalla del asistente con el contexto de esa materia.
- El estudiante puede volver al menú de selección con el botón "Cambiar de Materia".

**Tareas:**

- [ ] El sistema debe permitir mostrar las 4 materias disponibles.
- [ ] El sistema debe permitir seleccionar una materia.
- [ ] El sistema debe recordar la materia seleccionada por el estudiante.
- [ ] El sistema debe permitir cambiar de materia en cualquier momento.
- [ ] El sistema debe cargar el contexto del asistente según la materia elegida.

---

## HU-05: Enviar Pregunta sobre un Tema

**Como** estudiante con materia seleccionada,
**quiero** escribir mi duda o ejercicio en una caja de texto y enviarla,
**para** recibir una respuesta aclaratoria del asistente.

**Criterios de Aceptación:**

- El estudiante seleccionó una materia y visualiza una caja de texto con el placeholder: "Escribe aquí tu duda o ejercicio...".
- El estudiante escribe su duda y presiona el botón "Preguntar".
- El sistema valida que no esté vacío y envía la consulta al servicio de explicaciones.
- Si el campo está vacío, el sistema muestra: "Por favor escribe tu duda antes de presionar Preguntar".

**Tareas:**

- [ ] El sistema debe permitir ingresar texto con la duda o ejercicio del estudiante.
- [ ] El sistema debe validar que el campo de texto no esté vacío.
- [ ] El sistema debe enviar la consulta junto con la materia seleccionada.
- [ ] El sistema debe mostrar la respuesta del asistente después de enviar la pregunta.

---

## HU-06: Recibir Explicación Paso a Paso

**Como** estudiante que envió una pregunta,
**quiero** recibir una respuesta organizada en 4 pasos didácticos,
**para** comprender el tema y aprender a resolverlo por mí mismo.

**Criterios de Aceptación:**

- El estudiante envió una pregunta y el sistema muestra la respuesta estructurada en 4 pasos:
  1. ¿De qué se trata? (concepto en palabras sencillas)
  2. ¿Qué datos o reglas necesitamos? (fórmulas/definiciones)
  3. Desarrollo paso a paso
  4. Conclusión o resultado final
- Al final de la explicación aparece el botón "Practicar un ejercicio sobre este tema".

**Tareas:**

- [ ] El sistema debe generar una explicación según la materia y la pregunta enviada.
- [ ] El sistema debe mostrar la explicación en 4 pasos organizados.
- [ ] El sistema debe mostrar la información de forma clara y legible en pantalla de celular.
- [ ] El sistema debe permitir al estudiante solicitar un ejercicio de práctica al final de la explicación.

---

## HU-07: Solicitar Ejercicio de Práctica

**Como** estudiante que recibió una explicación,
**quiero** que el asistente genere un ejercicio de práctica sobre el tema,
**para** comprobar que lo comprendí.

**Criterios de Aceptación:**

- El estudiante presiona "Practicar este tema" y el sistema genera un ejercicio acorde a la materia y tema consultado.
- El sistema muestra el enunciado del problema y un campo para ingresar la respuesta.
- Si el estudiante está en la materia sin haber preguntado nada, el sistema genera un ejercicio general de esa materia.

**Tareas:**

- [ ] El sistema debe generar ejercicios de práctica según la materia y tema.
- [ ] El sistema debe mostrar el enunciado del ejercicio en pantalla.
- [ ] El sistema debe permitir al estudiante ingresar su respuesta.
- [ ] El sistema debe permitir generar ejercicios sin haber preguntado antes.

---

## HU-08: Enviar Respuesta de Ejercicio

**Como** estudiante con un ejercicio activo en pantalla,
**quiero** escribir mi respuesta y enviarla para su revisión,
**para** saber si lo hice bien o dónde me equivoqué.

**Criterios de Aceptación:**

- El estudiante tiene un ejercicio en pantalla, escribe su respuesta y presiona "Revisar mi respuesta".
- El sistema valida que se haya ingresado texto y envía la respuesta a evaluación.
- Si el campo está vacío, el sistema muestra un mensaje indicando que debe ingresar su respuesta.

**Tareas:**

- [ ] El sistema debe permitir al estudiante ingresar la respuesta al ejercicio.
- [ ] El sistema debe validar que la respuesta no esté vacía.
- [ ] El sistema debe enviar la respuesta junto con el ejercicio para su evaluación.

---

## HU-09: Revisar Respuesta y Mostrar Errores

**Como** estudiante que envió la respuesta de un ejercicio,
**quiero** recibir retroalimentación inmediata indicándome si está correcta o cuáles son mis errores,
**para** aprender de mis equivocaciones y conocer la respuesta correcta.

**Criterios de Aceptación:**

- El estudiante envió su respuesta y el sistema la evalúa.
- Si la respuesta es correcta, el sistema muestra un mensaje motivador, un resumen del procedimiento y la opción de hacer otro ejercicio o volver al menú.
- Si la respuesta contiene errores, el sistema indica dónde estuvo el error (ej: "Te equivocaste en el signo al despejar"), muestra la respuesta correcta paso a paso y ofrece la opción de intentar otro ejercicio similar.

**Tareas:**

- [ ] El sistema debe permitir comparar la respuesta del estudiante con la respuesta correcta.
- [ ] El sistema debe mostrar un mensaje cuando la respuesta sea correcta.
- [ ] El sistema debe indicar dónde estuvo el error cuando la respuesta sea incorrecta.
- [ ] El sistema debe mostrar la respuesta correcta explicada paso a paso.
- [ ] El sistema debe permitir al estudiante intentar otro ejercicio o volver al menú.

---

## MATRIZ DE Trazabilidad

| Historia de Usuario | Requerimiento Funcional | Caso de Uso |
|:---|:---|:---|
| HU-01: Registro de Cuenta | RF-01 | CU-01 |
| HU-02: Inicio de Sesión | RF-02 | CU-02 |
| HU-03: Cierre de Sesión | RF-03 | CU-03 |
| HU-04: Selección de Materia | RF-04 | CU-04 |
| HU-05: Enviar Pregunta | RF-05 | CU-05 |
| HU-06: Recibir Explicación | RF-06, RF-07 | CU-06 |
| HU-07: Solicitar Ejercicio | RF-08 | CU-07 |
| HU-08: Enviar Respuesta | RF-09 | CU-08 |
| HU-09: Revisar Respuesta | RF-10 | CU-09 |
