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
12. FORMATO DE RESPUESTA: usa Markdown limpio: ### para títulos de pasos, **negrita** para ideas
clave, listas con - o 1. y --- para separar secciones. PROHIBIDO usar etiquetas HTML.
13. HONESTIDAD: la IA puede equivocarse en texto e imágenes. Cierra temas sensibles o
numéricos con: "⚠️ Verifica con tu libro o profe, la IA puede cometer errores."
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


def _generar_con_modelos(contents, system_instruction: str, temperature: float = 0.7,
                          max_tokens: int = 1200, json_mode: bool = False) -> str:
    """Intenta generar contenido probando con los modelos descubiertos en tu cuenta.

    `max_tokens` acota la respuesta: más rápido, menos memoria en Render free
    y mejor para leer en celular.
    `json_mode=True` pide a Gemini `application/json` para no recibir Markdown.
    """
    client = obtener_cliente()
    modelos_a_probar = obtener_lista_modelos_activos()
    ultimo_error = None

    # Si json_mode falla en todos los modelos (algunos no soportan
    # response_mime_type), se reintenta sin esa opción.
    intentos_cfg = [True, False] if json_mode else [False]
    for usar_json in intentos_cfg:
        for modelo in modelos_a_probar:
            try:
                cfg = {
                    "system_instruction": system_instruction,
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
                if usar_json:
                    cfg["response_mime_type"] = "application/json"
                response = client.models.generate_content(
                    model=modelo,
                    contents=contents,
                    config=cfg,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                ultimo_error = e
                continue
        # Si ya probamos sin JSON, no hay más que intentar
        if not usar_json:
            break

    raise Exception(f"Error con los modelos {modelos_a_probar}: {ultimo_error}")


def _extraer_json(texto: str) -> dict:
    """Extrae el primer objeto JSON válido de la respuesta de la IA.

    Gemini suele devolver ```json ... ``` o texto extra aunque se le pida
    SOLO JSON. Esta función limpia cercas, busca el bloque { ... } más
    grande y lo parsea. Lanza excepción si no hay JSON válido.
    """
    import re as _re
    t = (texto or "").strip()
    # Quitar cercas de código en cualquier posición
    t = _re.sub(r"```(?:json)?", "", t).strip()
    # Intento directo
    try:
        return json.loads(t)
    except Exception:
        pass
    # Buscar el primer { ... } balanceado
    inicio = t.find("{")
    fin = t.rfind("}")
    if inicio != -1 and fin != -1 and fin > inicio:
        candidato = t[inicio:fin + 1]
        try:
            return json.loads(candidato)
        except Exception:
            pass
        # Limpieza extra: comas colgantes antes de } o ]
        candidato2 = _re.sub(r",\s*([}\]])", r"\1", candidato)
        return json.loads(candidato2)
    raise ValueError(f"Sin JSON válido en: {t[:200]}")


def _limpiar_historial(historial: list | None, max_mensajes: int = 6,
                       max_chars: int = 600) -> list:
    """Recorta el historial para la IA: sin HTML, sin imágenes base64/data-URL.

    Evita que historiales viejos y pesados (ej. 648 KB) tumben el worker
    de gunicorn en Render por falta de memoria/tiempo.
    """
    import re
    limpio = []
    for h in (historial or [])[-max_mensajes:]:
        item = {}
        for clave in ("pregunta", "respuesta"):
            texto = str(h.get(clave) or "")
            texto = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[imagen]", texto)
            texto = re.sub(r"<[^>]+>", " ", texto)
            texto = re.sub(r"\s+", " ", texto).strip()
            if len(texto) > max_chars:
                texto = texto[:max_chars] + "…"
            if texto:
                item[clave] = texto
        if item:
            limpio.append(item)
    return limpio


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
    for h in _limpiar_historial(historial):
        if h.get("pregunta"):
            mensajes.append({"role": "user", "parts": [{"text": h["pregunta"]}]})
        if h.get("respuesta"):
            mensajes.append({"role": "model", "parts": [{"text": h["respuesta"]}]})

    mensajes.append({"role": "user", "parts": [{"text": prompt_usuario[:2000]}]})

    try:
        return _generar_con_modelos(
            contents=mensajes,
            system_instruction=f"{PROMPT_SISTEMA}\n\n{contexto_materia}",
            temperature=0.7,
            # Explicación en 4 pasos + fórmulas: necesita margen para no cortarse
            max_tokens=3500,
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
    for h in _limpiar_historial(historial_reciente, max_mensajes=20, max_chars=300):
        if h.get("pregunta"):
            muestra.append(f"ESTUDIANTE: {h['pregunta']}")
        if h.get("respuesta"):
            muestra.append(f"TUTOR: {h['respuesta']}")
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
            system_instruction=(
                "Eres un evaluador de nivel escolar. "
                f"{contexto_materia} "
                "Respondes ÚNICAMENTE con un objeto JSON válido, sin markdown."
            ),
            temperature=0.3,
            max_tokens=500,  # solo un JSON corto
        ).strip()
        res = _extraer_json(texto)
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

REGLAS DEL ENUNCIADO:
- El "enunciado" debe plantear el PROBLEMA COMPLETO (datos + pregunta clara de qué resolver).
- PROHIBIDO pedir solo el resultado final (ej. "dame solo el número"). Pide resolver el problema.
- PROHIBIDO incluir la respuesta, ni pistas con el valor, dentro del "enunciado".
- La "respuesta_correcta" va SOLO en su campo, breve y concreta.
- La "explicacion" va SOLO en su campo, paso a paso.

IMPORTANTE: Responde ÚNICAMENTE con un JSON válido con esta estructura:
{{
    "enunciado": "El enunciado del ejercicio",
    "respuesta_correcta": "La respuesta correcta (breve y concreta)",
    "explicacion": "Explicación paso a paso de cómo se resuelve"
}}"""

    try:
        texto = _generar_con_modelos(
            contents=prompt,
            # CORREGIDO: instrucción estricta SOLO-JSON. Antes se usaba
            # PROMPT_SISTEMA (que ordena Markdown/pasos) y Gemini devolvía
            # texto + JSON, json.loads fallaba y caía al fallback genérico.
            system_instruction=(
                "Eres un generador de ejercicios escolares. "
                f"{contexto_materia} "
                "Respondes ÚNICAMENTE con un objeto JSON válido, sin markdown, "
                "sin cercas ```, sin explicaciones fuera del JSON."
            ),
            temperature=0.8,
            json_mode=True,
        ).strip()

        datos = _extraer_json(texto)
        enunciado = str(datos.get("enunciado", "")).strip()
        resp = str(datos.get("respuesta_correcta", "")).strip()
        expl = str(datos.get("explicacion", "")).strip()
        # Validar que sea un ejercicio real, no un texto vacío
        if len(enunciado) < 20 or not resp:
            raise ValueError(f"Ejercicio incompleto: {texto[:200]}")
        return {"enunciado": enunciado,
                "respuesta_correcta": resp,
                "explicacion": expl}
    except Exception as e:
        print("Aviso generar_ejercicio, usando respaldo:", e)
        tema_seguro = f" de {tema[:80]}" if tema else f" de {materia}"
        return {
            "enunciado": f"Ejercicio de {materia}{tema_seguro}: resuelve el problema planteado en tu última duda, mostrando datos, procedimiento y resultado.",
            "respuesta_correcta": "Revisar con el procedimiento",
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
            system_instruction=(
                "Eres un evaluador escolar justo. "
                f"{contexto_materia} "
                "Respondes ÚNICAMENTE con un objeto JSON válido, sin markdown, "
                "sin cercas ```, sin texto fuera del JSON."
            ),
            temperature=0.5,
            json_mode=True,
        ).strip()

        res = _extraer_json(texto)
        return {
            "es_correcta": bool(res.get("es_correcta", False)),
            "feedback": res.get("feedback", "No se pudo evaluar."),
        }
    except Exception as e:
        return {
            "es_correcta": False,
            "feedback": f"Error al evaluar: {str(e)}",
        }


# ─── Re-analizador de imagen (coherencia Preciso/Creativo) ───
def generar_prompt_imagen(pregunta: str, respuesta: str, materia: str = "",
                          modo: str = "preciso") -> dict:
    """Re-analiza la explicación ya dada y devuelve un prompt visual óptimo.

    Retorna {"prompt_en": str, "etiquetas": [str], "estilo": "lineal|ilustrativo"}.
    `modo=preciso`: solo formas, prohibido dibujar letras/números.
    `modo=creativo`: se permiten 1-3 etiquetas cortas en inglés.
    """
    import re as _re
    modo = (modo or "preciso").lower()
    if modo not in ("preciso", "creativo"):
        modo = "preciso"

    # Limpiar respuesta: sin HTML, sin data-URL, sin LaTeX largo
    texto = _re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[imagen]", str(respuesta or ""))
    texto = _re.sub(r"<[^>]+>", " ", texto)
    texto = _re.sub(r"\$\$[\s\S]+?\$\$|\$[^$\n]+?\$", " [formula] ", texto)
    texto = _re.sub(r"\s+", " ", texto).strip()[:2000]
    preg = str(pregunta or "").strip()[:500]

    if modo == "preciso":
        instruccion = ("Describe ONLY the visual shapes in 1-2 English sentences. "
                       "FLAT BLACK LINE-ART diagram, white background, thick outlines, "
                       "minimal schematic, NO text, NO letters, NO numbers, NO words inside the image.")
    else:
        instruccion = ("Describe the scene in 1-2 English sentences as a clean educational "
                       "cartoon illustration, vibrant flat colors. At most 1-3 SHORT English "
                       "labels (single letters like O, H) if strictly needed.")

    prompt = (f"Materia: {materia}. Duda: {preg}. Explicación dada: {texto}. "
              f"{instruccion} Responde ÚNICAMENTE JSON válido: "
              '{"prompt_en": "...", "etiquetas": ["..."], "estilo": "lineal|ilustrativo"}')
    try:
        bruto = _generar_con_modelos(
            contents=prompt,
            system_instruction="Eres un director de arte educativo. Respondes SOLO JSON válido.",
            temperature=0.3,
            max_tokens=250,
        ).strip()
        res = _extraer_json(bruto)
        prompt_en = str(res.get("prompt_en", ""))[:500] or f"educational diagram about {preg[:100]}"
        etiquetas = [str(e)[:20] for e in (res.get("etiquetas") or [])][:6]
        estilo = str(res.get("estilo", "lineal" if modo == "preciso" else "ilustrativo"))
        return {"prompt_en": prompt_en, "etiquetas": etiquetas, "estilo": estilo}
    except Exception:
        base = f"educational {'line diagram, no text' if modo == 'preciso' else 'cartoon illustration'} about {preg[:120]}"
        return {"prompt_en": base, "etiquetas": [],
                "estilo": "lineal" if modo == "preciso" else "ilustrativo"}
