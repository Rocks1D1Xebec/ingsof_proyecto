"""
gemini_helper.py
────────────────
Helper para interactuar con la API de Google Gemini.
Descubre dinámicamente los modelos disponibles para tu API Key
y genera explicaciones paso a paso, ejercicios y revisiones.
"""

import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Cache de modelos disponibles en la cuenta
_MODELOS_DISPONIBLES_CACHE = []


def obtener_cliente():
    """Obtiene el cliente de Gemini."""
    api_key = os.getenv("API") or os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


def obtener_lista_modelos_activos() -> list[str]:
    """Descubre dinámicamente los modelos que realmente están activos en tu API Key."""
    global _MODELOS_DISPONIBLES_CACHE
    if _MODELOS_DISPONIBLES_CACHE:
        return _MODELOS_DISPONIBLES_CACHE

    try:
        client = obtener_cliente()
        modelos = []
        for m in client.models.list():
            nombre = (m.name or "").replace("models/", "")
            # Filtrar modelos de texto/chat (descartar embeddings o imagen pura como imagen-3 o text-embedding)
            if "embedding" not in nombre and "imagen" not in nombre and "aqa" not in nombre:
                modelos.append(nombre)

        # Ordenar priorizando modelos flash rápidos si existen
        modelos.sort(key=lambda x: (0 if "flash" in x else 1, 0 if "2" in x or "3" in x else 1))

        if modelos:
            _MODELOS_DISPONIBLES_CACHE = modelos
            return _MODELOS_DISPONIBLES_CACHE
    except Exception as err:
        print("Aviso al consultar modelos dinámicos:", err)

    # Lista de respaldo por si falla la llamada de listado
    return ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]


# ─── Prompts del sistema ────────────────────────────────────────
PROMPT_SISTEMA = """Eres "EduAsistente", un tutor virtual amigable y paciente diseñado
para estudiantes de secundaria que tienen dificultades académicas.

REGLAS FUNDAMENTALES:
1. Siempre responde en español, con lenguaje claro y sencillo.
2. Usa un tono cálido, motivador y empático.
3. Explica TODO paso a paso, como si fueras un profesor particular paciente.
4. Usa ejemplos cotidianos que un estudiante pueda entender.
5. Si el tema involucra fórmulas (ej. MRUV, álgebra, etc.), escríbelas de forma clara.
6. Sé conciso pero completo.
7. Usa viñetas (•) y pasos ("Paso 1:", "Paso 2:") bien estructurados.
"""

MATERIAS_CONTEXTO = {
    "Matemáticas": "Eres experto en matemáticas de secundaria: álgebra, geometría, trigonometría, ecuaciones, funciones.",
    "Física": "Eres experto en física de secundaria: cinemática (MRU, MRUV), dinámica, fuerzas, energía, velocidad, aceleración.",
    "Química": "Eres experto en química de secundaria: tabla periódica, enlaces, reacciones químicas, estequiometría, soluciones.",
    "Lenguaje": "Eres experto en lenguaje y literatura: gramática, ortografía, comprensión lectora, redacción y textos.",
}


def _obtener_contexto_materia(materia: str) -> str:
    return MATERIAS_CONTEXTO.get(materia, "Eres un tutor escolar general de secundaria.")


def _generar_con_modelos(contents, system_instruction: str, temperature: float = 0.7) -> str:
    """Intenta generar contenido probando con los modelos descubiertos en tu cuenta."""
    client = obtener_cliente()
    modelos_a_probar = obtener_lista_modelos_activos()
    ultimo_error = None

    for modelo in modelos_a_probar:
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
            continue

    raise Exception(f"Error con los modelos {modelos_a_probar}: {ultimo_error}")


# ─── Explicar un tema / responder pregunta ──────────────────────
def explicar_tema(pregunta: str, materia: str, historial: list | None = None) -> str:
    """Genera una explicación paso a paso para la duda del estudiante."""
    contexto_materia = _obtener_contexto_materia(materia)

    prompt_usuario = f"""El estudiante está en la materia de {materia} y tiene esta duda:

"{pregunta}"

Responde siguiendo esta estructura:
1. ¿De qué se trata? (Explica el concepto en palabras sencillas y con un ejemplo de la vida cotidiana)
2. Fórmulas o definiciones necesarias (si aplica)
3. Explicación paso a paso
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
        return _generar_con_modelos(
            contents=mensajes,
            system_instruction=f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
            temperature=0.7,
        )
    except Exception as e:
        return f"Lo siento, tuve un problema al procesar tu pregunta. Por favor intenta de nuevo. (Detalle: {str(e)})"


# ─── Generar ejercicio de práctica ──────────────────────────────
def generar_ejercicio(materia: str, tema: str = "") -> dict:
    """Genera un ejercicio práctico de la materia."""
    contexto_materia = _obtener_contexto_materia(materia)
    tema_txt = f' sobre "{tema}"' if tema else ""

    prompt = f"""Genera UN ejercicio de práctica de {materia}{tema_txt} para un estudiante de secundaria.

IMPORTANTE: Responde ÚNICAMENTE con un JSON válido con esta estructura:
{{
    "enunciado": "El enunciado del ejercicio",
    "respuesta_correcta": "La respuesta correcta (breve y concreta)",
    "explicacion": "Explicación paso a paso de cómo se resuelve"
}}"""

    try:
        texto = _generar_con_modelos(
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
            "enunciado": f"Ejercicio de {materia}: Plantea un problema de cinemática/operación y resuelve el primer paso.",
            "respuesta_correcta": "Paso resuelto",
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
    "feedback": "Explicación formativa y empática indicando aciertos o dónde estuvo el error."
}}"""

    try:
        texto = _generar_con_modelos(
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
            "feedback": res.get("feedback", "No se pudo evaluar."),
        }
    except Exception as e:
        return {
            "es_correcta": False,
            "feedback": f"Error al evaluar: {str(e)}",
        }
