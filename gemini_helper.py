"""
gemini_helper.py
────────────────
Helper para interactuar con la API de Google Gemini.
Genera explicaciones paso a paso, ejercicios de práctica y revisión.
Incluye respaldo automático entre modelos (gemini-2.5-flash, gemini-1.5-flash, etc.).
"""

import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Modelos en orden de preferencia
MODELOS_GEMINI = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",
]

def obtener_cliente():
    """Obtiene el cliente de Gemini usando la variable de entorno API o GEMINI_API_KEY."""
    api_key = os.getenv("API") or os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


# ─── Prompts del sistema ────────────────────────────────────────
PROMPT_SISTEMA = """Eres "EduAsistente", un tutor virtual amigable y paciente diseñado
para estudiantes de secundaria que tienen dificultades académicas.

REGLAS FUNDAMENTALES:
1. Siempre responde en español, con lenguaje claro y sencillo.
2. Usa un tono cálido, motivador y empático. Nunca hagas sentir mal al estudiante.
3. Explica TODO paso a paso, como si fueras un profesor particular paciente.
4. Usa ejemplos cotidianos que un adolescente pueda entender.
5. Si el tema involucra fórmulas, escríbelas de forma clara y legible.
6. Sé conciso pero completo. No te extiendas innecesariamente.
7. Usa emojis moderadamente para hacer las explicaciones más amigables.
8. NUNCA inventes información falsa. Si no estás seguro, dilo.

FORMATO DE RESPUESTAS:
- Usa texto plano con saltos de línea claros
- Para pasos usa: "Paso 1:", "Paso 2:", etc.
- Para fórmulas usa formato simple: v = d / t
- Para listas usa viñetas con •
"""

MATERIAS_CONTEXTO = {
    "Matemáticas": "Eres experto en matemáticas de secundaria: álgebra, geometría, trigonometría, ecuaciones, funciones.",
    "Física": "Eres experto en física de secundaria: cinemática (MRU, MRUV), dinámica, fuerzas, energía, velocidad, aceleración.",
    "Química": "Eres experto en química de secundaria: tabla periódica, enlaces, reacciones químicas, estequiometría, átomos y moléculas.",
    "Lenguaje": "Eres experto en lenguaje y literatura: gramática, ortografía, comprensión lectora, redacción y tipos de textos.",
}


def _obtener_contexto_materia(materia: str) -> str:
    return MATERIAS_CONTEXTO.get(materia, "Eres un tutor escolar general de secundaria.")


def _generar_con_fallback(contents, system_instruction: str, temperature: float = 0.7) -> str:
    """Intenta generar contenido probando los modelos disponibles hasta que uno responda con éxito."""
    client = obtener_cliente()
    ultimo_error = None

    for modelo in MODELOS_GEMINI:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=contents,
                config={
                    "system_instruction": system_instruction,
                    "temperature": temperature,
                },
            )
            if response and response.text:
                return response.text
        except Exception as e:
            ultimo_error = e
            # Si el modelo no está disponible, continúa con el siguiente de la lista
            continue

    raise Exception(f"No se pudo conectar con los modelos de Gemini. Detalle: {ultimo_error}")


# ─── Explicar un tema / responder pregunta ──────────────────────
def explicar_tema(pregunta: str, materia: str, historial: list | None = None) -> str:
    """Genera una explicación paso a paso para la duda del estudiante."""
    contexto_materia = _obtener_contexto_materia(materia)

    prompt_usuario = f"""El estudiante está en la materia de {materia} y tiene esta duda:

"{pregunta}"

Responde siguiendo esta estructura pedagógica:
1. ¿De qué se trata? (Explica el concepto en palabras muy sencillas y con un ejemplo de la vida diaria)
2. ¿Qué fórmulas o reglas necesitamos? (Si aplica)
3. Explicación o desarrollo paso a paso
4. Conclusión o resumen claro"""

    mensajes = []
    if historial:
        for h in historial[-6:]:
            if h.get("pregunta"):
                mensajes.append({"role": "user", "parts": [{"text": h["pregunta"]}]})
            if h.get("respuesta"):
                mensajes.append({"role": "model", "parts": [{"text": h["respuesta"]}]})

    mensajes.append({"role": "user", "parts": [{"text": prompt_usuario}]})

    try:
        return _generar_con_fallback(
            contents=mensajes,
            system_instruction=f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
            temperature=0.7,
        )
    except Exception as e:
        return f"Lo siento, tuve un problema al procesar tu pregunta. Por favor intenta de nuevo. (Error: {str(e)})"


# ─── Generar ejercicio de práctica ──────────────────────────────
def generar_ejercicio(materia: str, tema: str = "") -> dict:
    """Genera un ejercicio práctico de la materia."""
    contexto_materia = _obtener_contexto_materia(materia)
    tema_txt = f' sobre "{tema}"' if tema else ""

    prompt = f"""Genera UN ejercicio de práctica de {materia}{tema_txt} para un estudiante de secundaria.

IMPORTANTE: Responde ÚNICAMENTE con un JSON válido, sin bloques ```json, con esta estructura exacta:
{{
    "enunciado": "El enunciado del ejercicio",
    "respuesta_correcta": "La respuesta correcta (breve y concreta)",
    "explicacion": "Explicación paso a paso de cómo se resuelve"
}}"""

    try:
        texto = _generar_con_fallback(
            contents=prompt,
            system_instruction=f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
            temperature=0.8,
        ).strip()

        if texto.startswith("```"):
            texto = texto.split("\n", 1)[1]
            texto = texto.rsplit("```", 1)[0].strip()

        return json.loads(texto)
    except Exception as e:
        return {
            "enunciado": f"Ejercicio de {materia}: Plantea un problema básico y escribe tu procedimiento para que lo revisemos juntos.",
            "respuesta_correcta": "Procedimiento del estudiante",
            "explicacion": f"Detalle: {str(e)}",
        }


# ─── Revisar respuesta del estudiante ──────────────────────────
def revisar_respuesta(enunciado: str, respuesta_estudiante: str,
                      respuesta_correcta: str, materia: str) -> dict:
    """Revisa la respuesta del estudiante y le da retroalimentación detallada."""
    contexto_materia = _obtener_contexto_materia(materia)

    prompt = f"""El estudiante de {materia} respondió a este ejercicio:

ENUNCIADO: {enunciado}
RESPUESTA CORRECTA: {respuesta_correcta}
RESPUESTA DEL ESTUDIANTE: {respuesta_estudiante}

Evalúa la respuesta y responde ÚNICAMENTE con un JSON válido:
{{
    "es_correcta": true/false,
    "feedback": "Tu explicación aquí: si acertó felicítalo; si falló, muéstrale con cariño el paso donde se equivocó y cómo corregirlo."
}}"""

    try:
        texto = _generar_con_fallback(
            contents=prompt,
            system_instruction=f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
            temperature=0.5,
        ).strip()

        if texto.startswith("```"):
            texto = texto.split("\n", 1)[1]
            texto = texto.rsplit("```", 1)[0].strip()

        res = json.loads(texto)
        return {
            "es_correcta": bool(res.get("es_correcta", False)),
            "feedback": res.get("feedback", "No pude evaluar la respuesta."),
        }
    except Exception as e:
        return {
            "es_correcta": False,
            "feedback": f"No se pudo evaluar automáticamente. Intenta de nuevo. ({str(e)})",
        }
