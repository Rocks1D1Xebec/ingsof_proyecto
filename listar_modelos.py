"""
listar_modelos.py
─────────────────
Script para consultar en tiempo real todos los modelos de Google Gemini
disponibles para tu API Key.

Ejecutar en terminal:
    python listar_modelos.py
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()


def obtener_modelos_disponibles():
    """Consulta la API de Gemini y retorna una lista de modelos compatibles con generateContent."""
    api_key = os.getenv("API1") or os.getenv("API2") or os.getenv("API") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: No se encontró la variable 'API1', 'API2' ni 'API' en el archivo .env o en el entorno.")
        return []

    try:
        client = genai.Client(api_key=api_key)
        todos_los_modelos = list(client.models.list())
        
        modelos_compatibles = []
        for m in todos_los_modelos:
            nombre = m.name or ""
            # Limpiar prefijo 'models/' si viene incluido
            nombre_limpio = nombre.replace("models/", "")
            
            # Verificar si soporta generación de contenido
            acciones = getattr(m, "supported_actions", []) or getattr(m, "supported_generation_methods", []) or []
            if not acciones or "generateContent" in acciones or "generate_content" in str(acciones):
                modelos_compatibles.append(nombre_limpio)
        
        return modelos_compatibles
    except Exception as e:
        print(f"❌ Error al consultar la lista de modelos: {e}")
        return []


if __name__ == "__main__":
    print("🔍 Consultando modelos disponibles con tu API Key...")
    modelos = obtener_modelos_disponibles()
    if modelos:
        print(f"\n✅ Se encontraron {len(modelos)} modelos disponibles para tu cuenta:")
        for idx, mod in enumerate(modelos, 1):
            print(f"   {idx}. {mod}")
    else:
        print("⚠️ No se pudieron obtener los modelos. Verifica tu clave de API.")
