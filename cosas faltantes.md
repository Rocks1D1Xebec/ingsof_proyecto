# Cosas Faltantes para Cumplir con la Documentación del Proyecto

> **ESTADO 2026-09-24: TODO IMPLEMENTADO** ✅ — Los 3 puntos MVP están en código,
> más RF-11 (nivel por materia cada 20 mensajes), RF-12 (perfil en dashboard),
> RF-13 (progreso que la IA informa) y RNF-05 (hash werkzeug). BD recreada desde cero.
> Además están en código las mejoras **v1.1** (ilustración Preciso/Creativo + disclaimer)
> y **v1.2** (voz, esquema SVG y seguridad) detalladas en la sección 4.

Este documento resume el análisis de la carpeta `Proyecto/` frente al estado actual del código del **Asistente Web Escolar (EduAsistente)**.

---

## 📊 1. Matriz de Cumplimiento (Documentación vs Código)

| Requerimiento / HU | Descripción en los Documentos | Estado Actual | Observación |
| :--- | :--- | :---: | :--- |
| **RF-01 / HU-01 / CU-01** | Registro de cuenta | ✅ **Completo** | Formulario simple y funcional (`register.html`, BD D1). |
| **RF-02 / HU-02 / CU-02** | Iniciar sesión | ✅ **Completo** | Autenticación y manejo de sesión (`login.html`, Flask session). |
| **RF-03 / HU-03 / CU-03** | Cerrar sesión | ✅ **Completo** | Botón salir en navbar y endpoint `/api/logout`. |
| **RF-04 / HU-04 / CU-04** | Selección de Materias | ✅ **Completo** | 4 materias base (Matemáticas, Física, Química, Lenguaje) + materias privadas del usuario en `dashboard.html`. |
| **RF-05 / HU-05 / CU-05** | Enviar preguntas | ✅ **Completo** | Caja de texto adaptada a móvil en `chat.html`. |
| **RF-06 / RF-07 / HU-06** | Explicación didáctica paso a paso | ✅ **Completo** | 4 pasos guiados con Gemini y diagramas educativos con Cloudflare Workers AI. |
| **RF-08 / HU-07 / CU-07** | Generar ejercicio de práctica | ✅ **Completo** | Botón contextual `🎯 Practicar este tema` al final de cada burbuja (`chat.html`) + botón general + `POST /api/ejercicio` con tema contextual. |
| **RF-09 / RF-10 / HU-08 / HU-09**| Revisar ejercicio y señalar errores | ✅ **Completo** | Revisión con Gemini y **persistencia** en `respuestas_ejercicios` vía `guardar_respuesta_ejercicio()` invocada en `POST /api/revisar` (`main.py`) + contadores RF-13. |
| **RF-11 / RF-12 / RF-13** | Nivel individual, técnica por asociación y progreso | ✅ **Completo** | RF-11: nivel por materia recalculado por IA cada 20 mensajes (`evaluar_nivel()` + `nivel_usuario`). RF-12: perfil en `dashboard.html` + `GET/PUT /api/perfil` (`perfiles_aprendizaje`). RF-13: `intentos/aciertos` + la IA informa progreso real ante "¿cómo voy?". |
| **v1.1 — Apoyo visual** | Ilustración coherente con la respuesta + disclaimer | ✅ **Completo** | Modos Preciso/Creativo por materia, re-analizador `generar_prompt_imagen()` y campo `advertencia` en las respuestas (selector *Imagen IA / Esquema texto*, en §4). |
| **v1.2 — Voz** | Lectura en voz alta de las explicaciones | ✅ **Completo** | Toggle `🔊 Voz` + botón por burbuja en `chat.html` → `POST /api/audio-verbalizado` → `verbalizar_para_audio()` con respaldos regex y `speechSynthesis`. |
| **v1.2 — Esquema SVG** | Dibujo con letras reales sin IA generativa | ✅ **Completo** | `POST /api/esquema` devuelve `etiquetas` y `dibujarEsquemaSVG()` dibuja el nodo central y sus hojas en el navegador. |
| **v1.2 — Seguridad** | Validación de correo, aislamiento de materias y límites | ✅ **Completo** | Correo `@gmail.com`, `materia_visible_para()` (403) en chat/historial/ejercicio, historial recortado (`_limpiar_historial`) y rechazo de imágenes > 700 KB. |

---

## 🔍 2. Puntos MVP (Versión 1.0) — Verificados como COMPLETADOS

### 1. Guardar las revisiones de ejercicios en la Base de Datos ✅ HECHO
- **Documento:** `historias_usuario.md` (HU-08 y HU-09) y `basedatos.sql`.
- **Estado actual:** La tabla `respuestas_ejercicios` está creada y `main.py` (`POST /api/revisar`) **sí guarda** la respuesta, `es_correcta` y `feedback` vía `guardar_respuesta_ejercicio(...)` en `cloudflare_d1.py`, además de sumar `intentos/aciertos` en `nivel_usuario` (RF-13).

---

### 2. Botón "Practicar un ejercicio sobre este tema" al final de la explicación ✅ HECHO
- **Documento:** `historias_usuario.md` (HU-06: Criterios de Aceptación) y `informe_requerimientos_asistente_escolar.md` (CU-06: Paso 4).
  > *"Al final de la explicación aparece el botón 'Practicar un ejercicio sobre este tema'."*
- **Estado actual:** Cada burbuja del asistente en `chat.html` (`agregarMensajeAsistente`) incluye `[🎯 Practicar este tema]`, que llama a `practicarTema()` → `POST /api/ejercicio` con el tema recién explicado como contexto. Además se mantiene el botón general `btn-practice` para ejercicio representativo (HU-07).

---

### 3. Cargar imágenes guardadas en el Historial del Chat ✅ HECHO
- **Documento:** Requerimiento de persistencia y continuidad de la sesión.
- **Estado actual:** La columna `imagen_url` existe en `respuestas`, `obtener_historial()` la devuelve y `cargarHistorial()` en `chat.html` la renderiza (`agregarMensajeAsistente(respuesta, imagen_url)`). Modo solo-manual v1.1: la imagen se genera bajo demanda con `/api/ilustrar` (Preciso/Creativo) o esquema de texto con `/api/esquema`.

---

## 🚀 3. Requerimientos v2.0 — ADELANTADOS E IMPLEMENTADOS
1. **RF-11:** ✅ Nivel por materia (`nivel_usuario.nivel` + `prompt_nivel`), recalculado por la IA cada 20 mensajes.
2. **RF-12:** ✅ Perfil de aprendizaje (`perfiles_aprendizaje.estilo`), editable en `dashboard.html` → `GET/PUT /api/perfil`, usado en prompts como analogías.
3. **RF-13:** ✅ Progreso (`intentos/aciertos` por materia); la IA cita cifras reales ante "¿cómo voy?".

---

## 🆕 4. Novedades v1.1 / v1.2 — IMPLEMENTADAS (2026-09-24)

> Estas mejoras nacieron **después** de los documentos de análisis de `Proyecto/`
> (que siguen siendo la especificación original). No había nada faltante:
> son funcionalidades nuevas, ya completas.

### Voz / Accesibilidad auditiva ✅
- `chat.html`: toggle **🔊 Voz** en la navbar (persiste en `localStorage.lectura_voz_activa`) y botón **Escuchar/Detener** en cada burbuja; si la voz está activa, lee sola cada respuesta nueva.
- `POST /api/audio-verbalizado` → `gemini_helper.verbalizar_para_audio()` (Gemini como locutor) con respaldo `limpiar_formulas_reglas()` y, en el navegador, `verbalizarReglasCliente()`. La síntesis final usa `speechSynthesis` (`es-ES`, rate 0.95).

### Esquema SVG determinista ✅
- `POST /api/esquema` ya no genera texto largo: devuelve `etiquetas` y `prompt_en`.
- `dibujarEsquemaSVG()` en `chat.html` dibuja un nodo central + hojas con letras reales: sin inferencia, sin costo, siempre legible.

### Selector de ilustración ✅
- **🎨 Ver ilustración** → *Imagen IA* (`/api/ilustrar`, re-analiza con `generar_prompt_imagen()`) o *Esquema texto* (`/api/esquema` + SVG).
- Modo Preciso/Creativo recordado por materia (`localStorage.modo_imagen_<materia>`); *Creativo* por defecto solo en Lenguaje.

### Robustez y seguridad ✅
- Rotación de **varias API Keys** (`API1`, `API2`, `API`, `GEMINI_API_KEY`) además de la rotación de modelos.
- Validación de registro: solo correos `@gmail.com` y sin duplicados.
- `materia_visible_para()` bloquea con **403** el acceso a materias privadas ajenas en `/api/chat`, `/api/historial` y `/api/ejercicio`.
- Historial recortado para la IA (`_limpiar_historial`) e imágenes > 700 KB rechazadas: sin workers caídos en Render.
- Ejercicios y revisiones se replican en el historial de chat, por lo que sobreviven a salir y volver.
