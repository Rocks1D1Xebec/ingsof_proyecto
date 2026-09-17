# Cosas Faltantes para Cumplir con la Documentación del Proyecto

> **ESTADO 2026-09-17: TODO IMPLEMENTADO** ✅ — Los 3 puntos MVP están en código,
> más RF-11 (nivel por materia cada 20 mensajes), RF-12 (perfil en dashboard),
> RF-13 (progreso que la IA informa) y RNF-05 (hash werkzeug). BD recreada desde cero.

Este documento resume el análisis de la carpeta `Proyecto/` frente al estado actual del código del **Asistente Web Escolar (EduAsistente)**.

---

## 📊 1. Matriz de Cumplimiento (Documentación vs Código)

| Requerimiento / HU | Descripción en los Documentos | Estado Actual | Observación |
| :--- | :--- | :---: | :--- |
| **RF-01 / HU-01 / CU-01** | Registro de cuenta | ✅ **Completo** | Formulario simple y funcional (`register.html`, BD D1). |
| **RF-02 / HU-02 / CU-02** | Iniciar sesión | ✅ **Completo** | Autenticación y manejo de sesión (`login.html`, Flask session). |
| **RF-03 / HU-03 / CU-03** | Cerrar sesión | ✅ **Completo** | Botón salir en navbar y endpoint `/api/logout`. |
| **RF-04 / HU-04 / CU-04** | Selección de Materias | ✅ **Completo** | 4 materias (Matemáticas, Física, Química, Lenguaje) en `dashboard.html`. |
| **RF-05 / HU-05 / CU-05** | Enviar preguntas | ✅ **Completo** | Caja de texto adaptada a móvil en `chat.html`. |
| **RF-06 / RF-07 / HU-06** | Explicación didáctica paso a paso | ✅ **Completo** | 4 pasos guiados con Gemini y diagramas educativos con Cloudflare Workers AI. |
| **RF-08 / HU-07 / CU-07** | Generar ejercicio de práctica | 🟡 **Parcial** | Falta botón contextual al final de cada explicación de la IA. |
| **RF-09 / RF-10 / HU-08 / HU-09**| Revisar ejercicio y señalar errores | 🟡 **Parcial** | Funciona la revisión, pero **no se almacena** en la tabla `respuestas_ejercicios`. |
| **RF-11 / RF-12 / RF-13** | Nivel individual, técnica por asociación y progreso | ⚪ **Pendiente** | Catalogado en el documento como **Versión 2.0 (Backlog futuro)**. |

---

## 🔍 2. Puntos Exactos que Faltan para Cumplir al 100% el MVP (Versión 1.0)

### 1. Guardar las revisiones de ejercicios en la Base de Datos
- **Documento:** `historias_usuario.md` (HU-08 y HU-09) y `basedatos.sql`.
- **Situación actual:** La tabla `respuestas_ejercicios` ya está creada en la base de datos, pero en `main.py` la ruta `/api/revisar` no guarda la respuesta enviada por el estudiante, si fue correcta ni el feedback recibido.
- **Acción requerida:**
  - Crear la función `guardar_respuesta_ejercicio(...)` en `cloudflare_d1.py`.
  - Invocarla en la ruta `/api/revisar` de `main.py`.

---

### 2. Botón "Practicar un ejercicio sobre este tema" al final de la explicación
- **Documento:** `historias_usuario.md` (HU-06: Criterios de Aceptación) y `informe_requerimientos_asistente_escolar.md` (CU-06: Paso 4).
  > *"Al final de la explicación aparece el botón 'Practicar un ejercicio sobre este tema'."*
- **Situación actual:** Actualmente solo existe un botón genérico en la barra de acciones rápidas (`btn-practice`), el cual no toma como contexto el tema específico que la IA acaba de responder.
- **Acción requerida:**
  - Agregar al final de cada burbuja de respuesta del asistente un botón directo: `[🎯 Practicar un ejercicio sobre este tema]`.
  - Al presionarlo, solicitar a `/api/ejercicio` un problema basado en el tema recién explicado.

---

### 3. Cargar imágenes guardadas en el Historial del Chat
- **Documento:** Requerimiento de persistencia y continuidad de la sesión.
- **Situación actual:** Se añadió la columna `imagen_url` en la tabla `respuestas`, pero la función `cargarHistorial()` de `chat.html` solo inyecta el texto plano de las respuestas antiguas.
- **Acción requerida:**
  - Si la fila del historial contiene `imagen_url` o etiquetas HTML, renderizarlas correctamente en la vista móvil al reabrir el chat.

---

## 🚀 3. Requerimientos Planificados para la Versión 2.0 (Fase Posterior)
Según el documento `informe_requerimientos_asistente_escolar.md`, estos puntos no bloquean la entrega actual (MVP v1.0), pero forman parte de la siguiente etapa:
1. **RF-11:** Adaptación de explicaciones y ejercicios según el nivel (básico, intermedio, avanzado) del estudiante.
2. **RF-12:** Adaptación de explicaciones según temas de interés del estudiante (ej: analogías con videojuegos, fútbol, música).
3. **RF-13:** Panel de seguimiento de progreso del estudiante (porcentaje de ejercicios correctos y temas dominados).
