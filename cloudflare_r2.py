"""
cloudflare_r2.py
────────────────
Módulo para interactuar con Cloudflare R2 (Object Storage compatible con S3).
Se utiliza para el almacenamiento físico de archivos (imágenes y PDFs) subidos por los estudiantes.

NO contiene secretos ni credenciales en código: lee todo desde variables de entorno.
"""

import os
import uuid
import boto3
from botocore.config import Config
from dotenv import load_dotenv

import credenciales as cfg

load_dotenv()

# Nombre del bucket y credenciales S3 para Cloudflare R2
BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS") or os.getenv("R2_SECRET_ACCESS_KEY")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
ENDPOINT_URL = os.getenv("R2_ENDPOINT")

# Si R2_ENDPOINT no fue configurado explícitamente pero existe ACCOUNT_ID, armar endpoint estándar
if not ENDPOINT_URL and ACCOUNT_ID:
    ENDPOINT_URL = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"


def _credenciales_actuales() -> dict:
    """Valores actuales de las variables de R2, para poder diagnosticarlas."""
    return {
        "R2_BUCKET_NAME": os.getenv("R2_BUCKET_NAME") or BUCKET_NAME,
        "R2_ACCESS_KEY_ID": os.getenv("R2_ACCESS_KEY_ID") or ACCESS_KEY_ID,
        "R2_SECRET_ACCESS": (
            os.getenv("R2_SECRET_ACCESS")
            or os.getenv("R2_SECRET_ACCESS_KEY")
            or SECRET_ACCESS_KEY
        ),
        "R2_ENDPOINT": os.getenv("R2_ENDPOINT") or ENDPOINT_URL,
    }


def esta_configurado() -> bool:
    """
    Verifica si las credenciales mínimas de Cloudflare R2 están presentes.

    Also devuelve False si el `.env` es una copia sin rellenar de
    `.env.example`: en ese caso las variables existen pero valen
    "your-bucket-name", y conectar con ellas solo produce un error confuso.
    """
    return cfg.esta_usable(_credenciales_actuales())


def motivo_de_configuracion() -> str:
    """
    Explica por qué R2 no está operativo, sin revelar ningún valor.

    Si todo está bien devuelve una cadena vacía.
    """
    credenciales = _credenciales_actuales()
    if cfg.esta_usable(credenciales):
        return ""
    return cfg.resumen_para_usuario(credenciales)


def obtener_cliente_s3():
    """Crea y devuelve un cliente S3 de boto3 conectado a Cloudflare R2."""
    if not esta_configurado():
        return None

    key_id = os.getenv("R2_ACCESS_KEY_ID") or ACCESS_KEY_ID
    secret = os.getenv("R2_SECRET_ACCESS") or os.getenv("R2_SECRET_ACCESS_KEY") or SECRET_ACCESS_KEY
    endpoint = os.getenv("R2_ENDPOINT") or ENDPOINT_URL

    try:
        s3 = boto3.client(
            service_name="s3",
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            region_name="auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=30
            )
        )
        return s3
    except Exception as e:
        print(f"Error al inicializar cliente S3 para Cloudflare R2: {e}")
        return None


def generar_key_segura(usuario_id: int, extension: str) -> str:
    """
    Genera una clave (key) segura y única para el almacenamiento en R2.
    Formato: usuarios/{usuario_id}/{uuid}.{ext}
    No depende del nombre original provisto por el usuario para evitar colisiones y path traversal.
    """
    ext_limpia = extension.lstrip(".").lower()
    identificador_unico = uuid.uuid4().hex
    return f"usuarios/{usuario_id}/{identificador_unico}.{ext_limpia}"


def subir_archivo(datos_archivo, r2_key: str, mime_type: str) -> bool:
    """
    Sube un archivo al bucket de Cloudflare R2.
    Acepta bytes, un objeto file-like o stream.
    Retorna True si la subida fue exitosa, False en caso contrario.
    """
    s3 = obtener_cliente_s3()
    bucket = os.getenv("R2_BUCKET_NAME") or BUCKET_NAME
    if not s3 or not bucket:
        print("Aviso R2: almacenamiento no configurado.")
        return False

    try:
        s3.put_object(
            Bucket=bucket,
            Key=r2_key,
            Body=datos_archivo,
            ContentType=mime_type
        )
        return True
    except Exception as e:
        print(f"Error al subir archivo a Cloudflare R2 ({r2_key}): {e}")
        return False


def obtener_archivo(r2_key: str) -> dict | None:
    """
    Obtiene un archivo de Cloudflare R2.
    Retorna un diccionario con 'body' (StreamingBody de boto3), 'content_type' y 'content_length',
    o None si ocurrió un error o el archivo no existe.
    """
    s3 = obtener_cliente_s3()
    bucket = os.getenv("R2_BUCKET_NAME") or BUCKET_NAME
    if not s3 or not bucket:
        return None

    try:
        respuesta = s3.get_object(Bucket=bucket, Key=r2_key)
        return {
            "body": respuesta["Body"],
            "content_type": respuesta.get("ContentType", "application/octet-stream"),
            "content_length": respuesta.get("ContentLength", 0)
        }
    except Exception as e:
        print(f"Error al obtener archivo de Cloudflare R2 ({r2_key}): {e}")
        return None


def eliminar_archivo(r2_key: str) -> bool:
    """
    Elimina físicamente un objeto de Cloudflare R2.
    Retorna True si fue eliminado o no existía, False si hubo error.
    """
    s3 = obtener_cliente_s3()
    bucket = os.getenv("R2_BUCKET_NAME") or BUCKET_NAME
    if not s3 or not bucket:
        return False

    try:
        s3.delete_object(Bucket=bucket, Key=r2_key)
        return True
    except Exception as e:
        print(f"Error al eliminar objeto de Cloudflare R2 ({r2_key}): {e}")
        return False


def generar_url_temporal(r2_key: str, expiracion_segundos: int = 3600) -> str | None:
    """
    Genera una URL prefirmada temporal para visualización/descarga directa desde R2.

    Nota de diseño: la app NO usa esta función. La descarga de
    `GET /api/archivos/<id>/descargar` pasa por Flask a propósito, porque la
    ruta comprueba la sesión y la pertenencia del archivo antes de servirlo.

    Se conserva como utilidad para dos casos futuros:
      * descargas o previsualizaciones de archivos muy grandes, donde no
        conviene arrastrar el tráfico por el servidor de Render;
      * miniaturas o vistas donde el cliente necesita la URL directamente.
    Quien la use debe recordar que una URL prefirmada es un acceso público
    temporal: no se debe generar para archivos privados sin aplicar antes las
    mismas comprobaciones de sesión.

    Por eso, el flujo actual de la aplicación sigue pasando siempre por Flask.
    """
    s3 = obtener_cliente_s3()
    bucket = os.getenv("R2_BUCKET_NAME") or BUCKET_NAME
    if not s3 or not bucket:
        return None

    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": r2_key},
            ExpiresIn=expiracion_segundos
        )
        return url
    except Exception as e:
        print(f"Error al generar presigned URL para {r2_key}: {e}")
        return None
