"""
gemini_helper.py
────────────────
Helper para interactuar con Google Gemini API.
Genera explicaciones pedagógicas paso a paso, ejercicios de práctica
y revisión de respuestas con retroalimentación formativa.
"""

import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Configurar el cliente de Gemini
client = genai.Client(api_key=os.getenv("API"))
MODELO = "gemini-2.0-flash"


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
- Para fórmulas usa formato simple: a² + b² = c²
- Para listas usa viñetas con •
"""

MATERIAS_CONTEXTO = {
    "Matemáticas": "Eres experto en matemáticas de nivel secundaria: álgebra, aritmética, geometría, trigonometría, funciones, ecuaciones, estadística.",
    "Física": "Eres experto en física de nivel secundaria: cinemática, dinámica, fuerzas, energía, trabajo, ondas, óptica, electricidad.",
    "Química": "Eres experto en química de nivel secundaria: tabla periódica, enlaces químicos, reacciones, estequiometría, ácidos y bases, soluciones.",
    "Lenguaje": "Eres experto en lenguaje y comunicación de nivel secundaria: gramática, ortografía, comprensión lectora, análisis de textos, redacción, literatura.",
}


def _obtener_contexto_materia(materia: str) -> str:
    """Obtiene el contexto específico de la materia."""
    return MATERIAS_CONTEXTO.get(materia, "Eres un tutor general de nivel secundaria.")


# ─── Explicar un tema / responder pregunta ──────────────────────
def explicar_tema(pregunta: str, materia: str, historial: list | None = None) -> str:
    """
    Genera una explicación paso a paso para la pregunta del estudiante.
    RF-05, RF-06, RF-07
    """
    contexto_materia = _obtener_contexto_materia(materia)

    prompt_usuario = f"""El estudiante está en la materia de {materia} y tiene esta duda:

"{pregunta}"

Responde siguiendo esta estructura:
1. ¿De qué se trata? (Explica el concepto en palabras sencillas)
2. ¿Qué datos o reglas necesitamos? (Fórmulas, propiedades o definiciones)
3. Desarrollo paso a paso (Procedimiento detallado)
4. Conclusión o resultado final

Si la pregunta es un ejercicio, resuélvelo paso a paso.
Si es una duda conceptual, explica con ejemplos claros."""

    # Construir mensajes del historial si existe
    mensajes = []
    if historial:
        for h in historial[-6:]:  # Últimos 6 mensajes para contexto
            if h.get("pregunta"):
                mensajes.append({"role": "user", "parts": [{"text": h["pregunta"]}]})
            if h.get("respuesta"):
                mensajes.append({"role": "model", "parts": [{"text": h["respuesta"]}]})

    mensajes.append({"role": "user", "parts": [{"text": prompt_usuario}]})

    try:
        response = client.models.generate_content(
            model=MODELO,
            contents=mensajes,
            config={
                "system_instruction": f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
                "temperature": 0.7,
                "max_output_tokens": 2048,
            },
        )
        return response.text
    except Exception as e:
        return f"Lo siento, tuve un problema al procesar tu pregunta. Por favor intenta de nuevo. (Error: {str(e)})"


# ─── Generar ejercicio de práctica ──────────────────────────────
def generar_ejercicio(materia: str, tema: str = "") -> dict:
    """
    Genera un ejercicio de práctica para la materia.
    RF-08
    Retorna: {"enunciado": str, "respuesta_correcta": str, "explicacion": str}
    """
    contexto_materia = _obtener_contexto_materia(materia)

    tema_instruccion = f' sobre el tema "{tema}"' if tema else ""

    prompt = f"""Genera UN ejercicio de práctica de {materia}{tema_instruccion} para un estudiante de secundaria.

IMPORTANTE: Responde ÚNICAMENTE con un JSON válido, sin texto adicional, sin bloques de código, con esta estructura exacta:
{{
    "enunciado": "El enunciado completo del ejercicio",
    "respuesta_correcta": "La respuesta correcta (breve y concreta)",
    "explicacion": "Explicación paso a paso de cómo se resuelve"
}}

El ejercicio debe ser:
- De dificultad básica-intermedia para un estudiante de secundaria
- Claro y con datos concretos
- Resoluble sin calculadora si es numérico"""

    try:
        response = client.models.generate_content(
            model=MODELO,
            contents=prompt,
            config={
                "system_instruction": f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
                "temperature": 0.8,
                "max_output_tokens": 1024,
            },
        )
        texto = response.text.strip()
        # Limpiar posibles bloques de código markdown
        if texto.startswith("```"):
            texto = texto.split("\n", 1)[1]  # Quitar primera línea
            texto = texto.rsplit("```", 1)[0]  # Quitar última línea
            texto = texto.strip()

        return json.loads(texto)
    except (json.JSONDecodeError, Exception) as e:
        return {
            "enunciado": f"Resuelve el siguiente problema de {materia}: Si tienes que practicar un tema, escribe tu duda y te generaré un ejercicio personalizado.",
            "respuesta_correcta": "Pide un ejercicio específico",
            "explicacion": f"No pude generar un ejercicio automáticamente. Error: {str(e)}",
        }


# ─── Revisar respuesta del estudiante ──────────────────────────
def revisar_respuesta(enunciado: str, respuesta_estudiante: str,
                      respuesta_correcta: str, materia: str) -> dict:
    """
    Revisa la respuesta del estudiante y genera retroalimentación.
    RF-09, RF-10
    Retorna: {"es_correcta": bool, "feedback": str}
    """
    contexto_materia = _obtener_contexto_materia(materia)

    prompt = f"""El estudiante de {materia} resolvió este ejercicio:

ENUNCIADO: {enunciado}
RESPUESTA CORRECTA: {respuesta_correcta}
RESPUESTA DEL ESTUDIANTE: {respuesta_estudiante}

Evalúa la respuesta y responde ÚNICAMENTE con un JSON válido, sin texto adicional, sin bloques de código:
{{
    "es_correcta": true/false,
    "feedback": "Tu retroalimentación aquí"
}}

Si es CORRECTA:
- Felicita al estudiante con entusiasmo
- Confirma brevemente por qué es correcta
- Anímalo a seguir practicando

Si tiene ERRORES:
- Indica CON PRECISIÓN dónde se equivocó (ej: "Te equivocaste en el signo al despejar")
- Muestra el procedimiento correcto paso a paso
- Sé empático y motivador, nunca hagas sentir mal al estudiante
- Termina con un mensaje de ánimo"""

    try:
        response = client.models.generate_content(
            model=MODELO,
            contents=prompt,
            config={
                "system_instruction": f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
                "temperature": 0.5,
                "max_output_tokens": 1024,
            },
        )
        texto = response.text.strip()
        if texto.startswith("```"):
            texto = texto.split("\n", 1)[1]
            texto = texto.rsplit("```", 1)[0]
            texto = texto.strip()

        resultado = json.loads(texto)
        return {
            "es_correcta": bool(resultado.get("es_correcta", False)),
            "feedback": resultado.get("feedback", "No pude evaluar tu respuesta."),
        }
    except (json.JSONDecodeError, Exception) as e:
        return {
            "es_correcta": False,
            "feedback": f"No pude evaluar tu respuesta automáticamente. Por favor intenta de nuevo. (Error: {str(e)})",
        }
