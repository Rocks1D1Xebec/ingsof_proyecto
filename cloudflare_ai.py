"""
cloudflare_ai.py
────────────────
Módulo para interactuar con Cloudflare Workers AI.
Se utiliza exclusivamente para generar imágenes ilustrativas y diagramas educativos
que complementan las explicaciones de la IA para los estudiantes.
"""

import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

# Modelos recomendados de Text-to-Image en Cloudflare
MODELOS_IMAGEN = [
    "@cf/black-forest-labs/flux-1-schnell",
    "@cf/bytedance/stable-diffusion-xl-lightning",
    "@cf/stabilityai/stable-diffusion-xl-base-1.0",
]


def generar_imagen_educativa(prompt: str) -> str | None:
    """
    Genera una imagen con Cloudflare Workers AI y la devuelve como un string Data URL
    listo para incrustar directamente en HTML (data:image/png;base64,...).
    Retorna None si no se pudo generar.
    """
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID") or ACCOUNT_ID
    api_token = os.getenv("CLOUDFLARE_API_TOKEN_IMAGEN") or os.getenv("CLOUDFLARE_API_TOKEN") or API_TOKEN

    if not account_id or not api_token:
        return None

    # Enriquecer el prompt para estilo didáctico y educativo
    prompt_enriquecido = f"Educational illustration, clean, clear diagram or cartoon style: {prompt}, high quality, vibrant colors"

    for modelo in MODELOS_IMAGEN:
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{modelo}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        body = {"prompt": prompt_enriquecido}

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=25)
            if resp.status_code == 200:
                img_b64 = None
                
                # Caso 1: JSON con Base64
                try:
                    datos = resp.json()
                    if datos.get("success") and "result" in datos:
                        img_b64 = datos["result"].get("image")
                except Exception:
                    pass

                # Caso 2: Bytes directos
                if not img_b64 and len(resp.content) > 1000:
                    img_b64 = base64.b64encode(resp.content).decode("utf-8")

                if img_b64:
                    return f"data:image/jpeg;base64,{img_b64}"
        except Exception as err:
            print(f"Aviso al generar imagen con {modelo}:", err)
            continue

    return None
