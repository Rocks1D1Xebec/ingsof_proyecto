"""
credenciales.py
───────────────
Utilidades compartidas para comprobar si la configuración de Cloudflare está
realmente puesta, sin exponer ningún valor.

Por qué existe: `.env.example` se copia a `.env` tal cual para tener la
plantilla a mano. Si alguien no rellena los valores, las variables existen y
están "vacias" solo en apariencia: cualquier comprobación del tipo
`if os.getenv("R2_BUCKET_NAME")` da True y la aplicación intenta connectarse a
Cloudflare con datos de ejemplo. El resultado es un error 502 confuso o un
arranque lento por timeouts, en lugar de un mensaje que diga qué falta.

Reglas de este módulo:
  * NUNCA imprime, registra ni devuelve el valor de una credencial.
  * Solo devuelve nombres de variable y motivos legibles.
"""

# Textos que aparecen en los valores de ejemplo de .env.example.
# Si un valor contiene alguno de ellos, todavía no se ha rellenado.
# Se busca como subcadena y no solo al principio porque hay placeholders con
# prefijo, como el endpoint "https://your-account-id.r2.cloudflarestorage.com".
_MARCAS_DE_EJEMPLO = (
    "your-",
    "your_",
    "cambia-",
    "cambia_",
    "changeme",
    "pendiente",
    "pega-aqui",
    "pega_aqui",
    "ejemplo",
)

# Valores que corresponden a "no configurado" aunque la variable exista.
# Se comparan exactos, no como subcadena.
_VALOR_VACIO = {"", "none", "null", "undefined", "false", "todo", "x"}


def es_valor_de_ejemplo(valor: str | None) -> bool:
    """
    True si el valor sigue siendo un placeholder de la plantilla, es decir,
    si el usuario copió `.env.example` a `.env` pero no lo editó.
    """
    if valor is None:
        return True
    limpio = str(valor).strip().strip("'\"").lower()
    if limpio in _VALOR_VACIO:
        return True
    return any(marca in limpio for marca in _MARCAS_DE_EJEMPLO)


def falta_alguna(credenciales: dict) -> list[str]:
    """
    Devuelve los NOMBRES de las variables que no están rellenadas.

    `credenciales` es un diccionario {nombre: valor}. Solo se devuelven
    nombres, jamás los valores, para poder mostrarlos en un log o en la UI.
    """
    faltantes = []
    for nombre, valor in credenciales.items():
        if es_valor_de_ejemplo(valor):
            faltantes.append(nombre)
    return sorted(faltantes)


def esta_usable(credenciales: dict) -> bool:
    """True si todas las variables dadas tienen un valor utilizable."""
    return not falta_alguna(credenciales)


def resumen_para_usuario(credenciales: dict) -> str:
    """
    Mensaje listo para mostrar, con los nombres de lo que falta.

    No incluye ningún valor, solo nombres de variable.
    """
    faltantes = falta_alguna(credenciales)
    if not faltantes:
        return "Configuración correcta."
    if len(faltantes) == 1:
        return (
            f"Falta configurar '{faltantes[0]}' en el archivo .env. "
            "Sigue con el valor de ejemplo de la plantilla."
        )
    return (
        "Faltan configurar estas variables en el archivo .env, siguen con el "
        "valor de ejemplo de la plantilla: " + ", ".join(faltantes) + "."
    )
