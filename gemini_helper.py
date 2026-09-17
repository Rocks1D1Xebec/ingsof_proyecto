"""
gemini_helper.py
────────────────
Helper para interactuar con la API de Google Gemini.
Descubre dinámicamente los modelos disponibles para tu API Key
y genera explicaciones paso a paso, ejercicios y revisiones.
Opcionalmente sugiere una descripción de imagen educativa para que
Cloudflare Workers AI la genere e inserte en la explicación.
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
7. Si el tema es visual o conceptual (ej. átomos, células, movimiento, triángulos, velocidad, circuitos, etc.), puedes incluir en una línea especial la etiqueta:
[IMAGEN_EDUCATIVA: descripción breve en inglés para dibujar un esquema o diagrama claro]
Solo incluye [IMAGEN_EDUCATIVA: ...] una sola vez y únicamente cuando una ilustración ayude realmente a comprender mejor la explicación.
8. Usa viñetas (•) y pasos ("Paso 1:", "Paso 2:") bien estructurados.
9. FORMATO MATEMÁTICO OBLIGATORIO: escribe TODA notación matemática en LaTeX entre $...$ (inline)
o $$...$$ (display). Ejemplos: $\\sqrt{16}=4$, $\\frac{3}{4}$, $x^2$, $\\vec{F}=m\\vec{a}$.
PROHIBIDO usar "/raiz$", "sqrt textual", "raiz cuadrada de..." como símbolo, o arte ASCII.
Las fórmulas de química (ej. $H_2O$, $CO_2$) también van entre $...$.
10. NIVEL UNIVERSAL: explica siempre desde cero, sin asumir conocimientos previos: primero la idea
en palabras sencillas y luego el término técnico entre paréntesis. Así te entiende tanto quien no sabe
nada como quien ya sabe.
11. PROGRESO REAL: si recibes un bloque "PROGRESO DEL ESTUDIANTE", úsalo solo cuando te pregunten
cómo van ("¿cómo voy?", "¿cómo me fue?"). Cita EXACTAMENTE esas cifras; PROHIBIDO inventar números.
"""


def _bloque_personalizacion(perfil: str = "", prompt_nivel: str = "",
                            nivel: str = "", stats: str = "") -> str:
    """Arma el bloque de contexto personal (RF-11/RF-12/RF-13). Vacío si no hay datos."""
    partes = []
    if perfil:
        partes.append(f"El estudiante aprende mejor cuando: {perfil}\n"
                      f"Adapta tus analogías y ejemplos a eso (cocina, fútbol, series, etc.).")
    if prompt_nivel:
        partes.append(f"Nivel detectado ({nivel or 'basico'}): {prompt_nivel}\n"
                      f"Ajusta la dificultad y el vocabulario a ese nivel.")
    if stats:
        partes.append(f"PROGRESO DEL ESTUDIANTE (cifras reales, no inventar otras):\n{stats}")
    if not partes:
        return ""
    return "\n\nPERSONALIZACIÓN:\n" + "\n\n".join(partes)

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
def explicar_tema(pregunta: str, materia: str, historial: list | None = None,
                  perfil: str = "", prompt_nivel: str = "",
                  nivel: str = "", stats: str = "") -> str:
    """Genera una explicación paso a paso para la duda del estudiante."""
    contexto_materia = _obtener_contexto_materia(materia)

    prompt_usuario = f"""El estudiante está en la materia de {materia} y tiene esta duda:

"{pregunta}"

Responde siguiendo esta estructura:
1. ¿De qué se trata? (Explica el concepto en palabras sencillas y con un ejemplo de la vida cotidiana)
2. Fórmulas o definiciones necesarias (si aplica)
3. Explicación paso a paso
4. Conclusión o resumen claro{_bloque_personalizacion(perfil, prompt_nivel, nivel, stats)}"""

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


# ─── Evaluar nivel del estudiante (RF-11, cada 20 mensajes) ─────
def evaluar_nivel(materia: str, historial_reciente: list, intentos: int = 0,
                  aciertos: int = 0) -> dict:
    """Analiza los últimos intercambios y devuelve {nivel, prompt_nivel}.

    Llamada barata: solo se invoca cada 20 mensajes por materia.
    """
    contexto_materia = _obtener_contexto_materia(materia)
    muestra = []
    for h in (historial_reciente or [])[-20:]:
        if h.get("pregunta"):
            muestra.append(f"ESTUDIANTE: {str(h['pregunta'])[:300]}")
        if h.get("respuesta"):
            muestra.append(f"TUTOR: {str(h['respuesta'])[:300]}")
    conversacion = "\n".join(muestra) or "(sin historial)"
    prompt = f"""Analiza esta conversación de {materia} y el rendimiento en ejercicios
(intentos: {intentos}, aciertos: {aciertos}).

CONVERSACIÓN:
{conversacion}

Responde ÚNICAMENTE con un JSON válido:
{{
    "nivel": "basico" | "intermedio" | "avanzado",
    "prompt_nivel": "2-3 frases describiendo qué domina y en qué falla, para que otro tutor ajuste su explicación"
}}"""
    try:
        texto = _generar_con_modelos(
            contents=prompt,
            system_instruction=f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
            temperature=0.3,
        ).strip()
        if texto.startswith("```"):
            texto = texto.split("\n", 1)[1]
            texto = texto.rsplit("```", 1)[0].strip()
        res = json.loads(texto)
        nivel = str(res.get("nivel", "basico")).lower()
        if nivel not in ("basico", "intermedio", "avanzado"):
            nivel = "basico"
        return {"nivel": nivel,
                "prompt_nivel": str(res.get("prompt_nivel", ""))[:1000]}
    except Exception:
        return {"nivel": "basico", "prompt_nivel": ""}


# ─── Generar ejercicio de práctica ──────────────────────────────
def generar_ejercicio(materia: str, tema: str = "", perfil: str = "",
                      prompt_nivel: str = "", nivel: str = "") -> dict:
    """Genera un ejercicio práctico de la materia."""
    contexto_materia = _obtener_contexto_materia(materia)
    tema_txt = f' sobre "{tema}"' if tema else ""

    prompt = f"""Genera UN ejercicio de práctica de {materia}{tema_txt} para un estudiante de secundaria.
{_bloque_personalizacion(perfil, prompt_nivel, nivel)}

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
