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
        # Ejercicios autónomos completos por materia para que el estudiante siempre tenga una pregunta concreta
        ejercicios_base = {
            "Matemáticas": {
                "enunciado": "Resuelve la siguiente ecuación de primer grado paso a paso:\n\n$$2x + 6 = 18$$\n\nEncuentra el valor de $x$.",
                "respuesta_correcta": "6",
                "explicacion": "Restamos 6 a ambos lados: 2x = 12. Luego dividimos entre 2: x = 6."
            },
            "Física": {
                "enunciado": "Un automóvil viaja a velocidad constante de $20\\text{ m/s}$ en línea recta durante $15\\text{ segundos}$. ¿Qué distancia total recorre?",
                "respuesta_correcta": "300 metros",
                "explicacion": "Usamos la fórmula del MRU: $d = v \\cdot t$. Sustituyendo: $d = 20 \\cdot 15 = 300\\text{ m}$."
            },
            "Química": {
                "enunciado": "Indica cuál es el número atómico ($Z$) y la cantidad de protones de un átomo neutro de Carbono ($C$).",
                "respuesta_correcta": "Z = 6 (6 protones)",
                "explicacion": "El carbono ocupa la posición 6 en la tabla periódica, por lo que su número atómico Z es 6 y tiene 6 protones."
            },
            "Lenguaje": {
                "enunciado": "Identifica el sujeto y el predicado en la siguiente oración:\n\n*\"Los estudiantes dedicados comprenden el tema con facilidad.\"*",
                "respuesta_correcta": "Sujeto: Los estudiantes dedicados | Predicado: comprenden el tema con facilidad",
                "explicacion": "El sujeto es quien realiza la acción ('Los estudiantes dedicados') y el predicado es todo lo que se dice del sujeto a partir del verbo."
            }
        }
        fallback = ejercicios_base.get(materia, {
            "enunciado": f"Explica un concepto clave de {materia} con un ejemplo práctico.",
            "respuesta_correcta": "Concepto con ejemplo",
            "explicacion": "Presenta una definición clara y acompáñala de una aplicación cotidiana."
        })
        if tema:
            fallback = {
                "enunciado": f"Ejercicio práctico sobre **{tema}** ({materia}):\n\nPlantea la definición o fórmula principal de este tema y calcula o explica un caso con tus propias palabras.",
                "respuesta_correcta": f"Aplicación correcta de {tema}",
                "explicacion": f"Demostración paso a paso sobre {tema}."
            }
        return fallback


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


# ─── Verbalización y Audio para Accesibilidad (Lectura Natural de Fórmulas) ───
def limpiar_formulas_reglas(texto: str) -> str:
    """Transformación determinista de símbolos comunes a español hablado."""
    import re
    t = str(texto or "")
    # Quitar imágenes y data urls
    t = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"!\[.*?\]\(.*?\)", " ", t)
    
    # Reemplazos de notaciones matemáticas comunes
    t = re.sub(r"\\sqrt\[(\d+)\]\{([^}]+)\}", r"raíz \1-ésima de \2", t)
    t = re.sub(r"\\sqrt\{([^}]+)\}", r"raíz cuadrada de \1", t)
    t = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"\1 sobre \2", t)
    t = re.sub(r"([A-Za-z0-9_]+)\^2", r"\1 al cuadrado", t)
    t = re.sub(r"([A-Za-z0-9_]+)\^3", r"\1 al cubo", t)
    t = re.sub(r"([A-Za-z0-9_]+)\^\{([^}]+)\}", r"\1 elevado a la \2", t)
    t = re.sub(r"([A-Za-z0-9_]+)\^(\d+)", r"\1 elevado a la \2", t)
    t = re.sub(r"\\times|\\cdot", " por ", t)
    t = re.sub(r"\\pm", " más o menos ", t)
    t = re.sub(r"\\le|\\leq", " menor o igual que ", t)
    t = re.sub(r"\\ge|\\geq", " mayor o igual que ", t)
    t = re.sub(r"\\neq", " no es igual a ", t)
    t = re.sub(r"\\approx", " aproximadamente ", t)
    t = re.sub(r"\\pi", " pi ", t)
    t = re.sub(r"\\alpha", " alfa ", t)
    t = re.sub(r"\\beta", " beta ", t)
    t = re.sub(r"\\theta", " zeta ", t)
    t = re.sub(r"\\Delta", " delta ", t)
    t = re.sub(r"\\vec\{([^}]+)\}", r"vector \1", t)
    t = re.sub(r"\b(\d+)\s*/\s*(\d+)\b", r"\1 sobre \2", t)
    
    # Unidades y química
    t = re.sub(r"m/s\^2", "metros por segundo al cuadrado", t)
    t = re.sub(r"m/s\b", "metros por segundo", t)
    t = re.sub(r"km/h\b", "kilómetros por hora", t)
    t = re.sub(r"\$H_2O\$|H_2O\b", "H dos O (agua)", t)
    t = re.sub(r"\$CO_2\$|CO_2\b", "C O dos (dióxido de carbono)", t)
    
    # Signos matemáticos
    t = t.replace("$", " ")
    t = t.replace("=", " es igual a ")
    t = t.replace("+", " más ")
    t = t.replace("-", " menos ")
    t = t.replace("±", " más o menos ")
    t = t.replace("×", " por ")
    t = t.replace("÷", " entre ")
    t = t.replace("√", " raíz cuadrada de ")
    t = t.replace("²", " al cuadrado ")
    t = t.replace("³", " al cubo ")
    
    # Markdown
    t = re.sub(r"[#*`_~]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def verbalizar_para_audio(texto: str, materia: str = "General") -> str:
    """Convierte el mensaje a texto fluido en español para ser leído por voz humana con Gemini.

    Convierte fórmulas LaTeX, KaTeX, fracciones y símbolos a palabras naturales.
    Si Gemini no está disponible o falla, utiliza reglas deterministas regex.
    """
    if not texto:
        return ""

    limpio_inicial = str(texto).replace("```", "").strip()[:2500]
    
    prompt = (
        f"Materia: {materia}.\n"
        f"Adapta este texto de una clase para ser leído en voz alta por un profesor virtual de secundaria:\n\n"
        f'"{limpio_inicial}"\n\n'
        "INSTRUCCIONES CLAVE:\n"
        "1. Transforma TODAS las fórmulas matemáticas, físicas o químicas a palabras habladas fluidas en español "
        "(ejemplo: √4 = 2 dilo como 'raíz cuadrada de cuatro es igual a dos'; 3/4 dilo como 'tres cuartos' o 'tres sobre cuatro'; "
        "x^2 dilo como 'equis al cuadrado'; 9.8 m/s² dilo como 'nueve coma ocho metros por segundo al cuadrado').\n"
        "2. Elimina símbolos de código, Markdown, asteriscos, signos de dólar ($), corchetes y formatos visuales.\n"
        "3. Mantén las explicaciones intactas con tono cálido, claro y docente.\n"
        "4. Devuelve ÚNICAMENTE el texto verbalizado listo para hablar, sin introducciones ni notas."
    )

    try:
        resultado = _generar_con_modelos(
            contents=prompt,
            system_instruction="Eres un profesor locutor de secundaria. Escribes exclusivamente texto fonético y natural para ser leído en voz alta.",
            temperature=0.2,
            max_tokens=1000
        ).strip()
        if resultado and len(resultado) > 10:
            return resultado
    except Exception as e:
        print("Aviso verbalizar_para_audio con IA (usando reglas):", e)

    return limpiar_formulas_reglas(limpio_inicial)

