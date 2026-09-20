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
| **RF-08 / HU-07 / CU-07** | Generar ejercicio de práctica | ✅ **Completo** | Botón contextual `🎯 Practicar este tema` al final de cada burbuja (`chat.html`) + botón general + `POST /api/ejercicio` con tema contextual. |
| **RF-09 / RF-10 / HU-08 / HU-09**| Revisar ejercicio y señalar errores | ✅ **Completo** | Revisión con Gemini y **persistencia** en `respuestas_ejercicios` vía `guardar_respuesta_ejercicio()` invocada en `POST /api/revisar` (`main.py`) + contadores RF-13. |
| **RF-11 / RF-12 / RF-13** | Nivel individual, técnica por asociación y progreso | ✅ **Completo** | RF-11: nivel por materia recalculado por IA cada 20 mensajes (`evaluar_nivel()` + `nivel_usuario`). RF-12: perfil en `dashboard.html` + `GET/PUT /api/perfil` (`perfiles_aprendizaje`). RF-13: `intentos/aciertos` + la IA informa progreso real ante "¿cómo voy?". |

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
