import os
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def cargar_env(ruta):
    variables = {}
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            variables[clave.strip()] = valor.strip()
    return variables


def main():
    if ENV_PATH.exists():
        variables = cargar_env(ENV_PATH)
        os.environ.update(variables)

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    database_id = os.getenv("CLOUDFLARE_DATABASE_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not all([account_id, database_id, api_token]):
        print("ERROR: Faltan variables de conexion en .env")
        sys.exit(1)

    url = (
        "https://api.cloudflare.com/client/v4/"
        f"accounts/{account_id}/d1/database/{database_id}/query"
    )
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {"sql": "SELECT 1 AS ok", "params": []}

    try:
        respuesta = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"HTTP {respuesta.status_code}")
        if respuesta.status_code == 200:
            datos = respuesta.json()
            if datos.get("success"):
                print("CONEXION EXITOSA: la base de datos Cloudflare D1 responde correctamente.")
                print(datos.get("result"))
            else:
                print("La API respondio pero hubo errores:")
                print(datos.get("errors"))
        elif respuesta.status_code == 401:
            print("ERROR DE AUTENTICACION: el token de Cloudflare no es valido o no tiene permisos.")
            print(respuesta.text)
        else:
            print("ERROR AL CONECTAR:")
            print(respuesta.text)
    except Exception as e:
        print(f"ERROR DE CONEXION: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()