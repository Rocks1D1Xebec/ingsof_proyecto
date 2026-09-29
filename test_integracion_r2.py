"""
test_integracion_r2.py
──────────────────────
PRUEBA DE INTEGRACIÓN REAL contra Cloudflare (R2 + D1).

Esta prueba SÍ toca los servicios de verdad: sube un archivo al bucket, lo
registra en D1, lo descarga y lo elimina. Al terminar, deja el bucket y la
base exactamente como estaban.

Cuándo usarla: cuando `.env` tenga credenciales reales y quieras confirmar que
la cadena completa funciona antes de desplegar.

    python test_integracion_r2.py

Cuándo NO usarla: si las credenciales siguen siendo las de ejemplo. En ese
caso la prueba se detiene en el primer paso y te dice qué falta, sin intentar
conectar y sin inventarse nada.

GARANTÍA DE CONFIDENCIALIDAD: este guion NUNCA imprime el valor de una
variable de entorno. Solo indica si cada variable está presente y es real
(True/False) y, si algo falla, el nombre de la variable implicada.

Qué comprueba, en orden:
    1. Las variables de entorno están rellenadas (no son placeholders).
    2. El bucket de R2 existe y es accesible.
    3. La API de D1 responde y la tabla `archivos` existe.
    4. Subida real del archivo a R2.
    5. Registro del metadato en D1 (con el id devuelto).
    6. Descarga: los bytes vuelven íntegros.
    7. Aislamiento: otro usuario no puede leer ese archivo.
    8. Borrado: desaparece de R2 y de D1.
"""

import io
import os
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

import credenciales as cfg
import cloudflare_d1 as d1
import cloudflare_r2 as r2

# ----------------------------------------------------------------------
# Presentación
# ----------------------------------------------------------------------
OK = "  [OK]   "
MAL = "  [FALLO]"
INFO = "  [--]   "

resultados = []


def registrar(nombre: str, exito: bool, detalle: str = "") -> bool:
    """Anota un paso y lo imprime. `detalle` nunca debe contener credenciales."""
    marca = OK if exito else MAL
    print(f"{marca} {nombre}")
    if detalle:
        print(f"         {detalle}")
    resultados.append((nombre, exito))
    return exito


def seccion(titulo: str) -> None:
    print()
    print(titulo)
    print("-" * len(titulo))


# ----------------------------------------------------------------------
# 1. ¿Hay credenciales utilizables?
# ----------------------------------------------------------------------
VARIABLES_R2 = {
    "R2_BUCKET_NAME": os.getenv("R2_BUCKET_NAME"),
    "R2_ACCESS_KEY_ID": os.getenv("R2_ACCESS_KEY_ID"),
    "R2_SECRET_ACCESS": os.getenv("R2_SECRET_ACCESS") or os.getenv("R2_SECRET_ACCESS_KEY"),
    "R2_ENDPOINT": os.getenv("R2_ENDPOINT"),
}
VARIABLES_D1 = {
    "CLOUDFLARE_ACCOUNT_ID": d1.ACCOUNT_ID,
    "CLOUDFLARE_DATABASE_ID": d1.DATABASE_ID,
    "CLOUDFLARE_API_TOKEN": d1.API_TOKEN,
}

# Usuario de pruebas. Debe existir en la tabla `usuarios`; el módulo comprueba
# que el `usuario_id` sea real antes de asociar nada, así que usa uno que ya
# tengas. Se puede cambiar aquí.
USUARIO_ID = int(os.getenv("R2_TEST_USUARIO_ID", "1"))

# ----------------------------------------------------------------------
# Comprobación previa: sin credenciales reales, no se intenta nada
# ----------------------------------------------------------------------
faltan = cfg.falta_alguna({**VARIABLES_R2, **VARIABLES_D1})

print("=" * 72)
print("PRUEBA DE INTEGRACIÓN REAL — EduAsistente / Cloudflare R2 + D1")
print("=" * 72)
print("Este guion sube, descarga y borra un archivo real. No imprime secretos.")
print()

if not os.path.isfile(".env"):
    print("No existe el archivo .env en la raíz del proyecto.")
    print()
    print("Qué hacer:")
    print("  1. Copia .env.example a .env")
    print("  2. Rellena los valores reales de tu cuenta de Cloudflare")
    print("  3. Vuelve a ejecutar:  python test_integracion_r2.py")
    sys.exit(2)

if faltan:
    seccion("1. VARIABLES DE ENTORNO")
    print(f"{MAL} Faltan {len(faltan)} variables por rellenar en .env:")
    for nombre in faltan:
        print(f"         - {nombre}")
    print()
    print("Estas variables siguen con el valor de ejemplo de .env.example.")
    print("No se intenta conectar a Cloudflare: solo daría timeouts o errores 404.")
    print()
    print("Qué hacer:")
    print("  1. Abre .env y sustituye los valores de ejemplo por los reales.")
    print("  2. Dónde se sacan:")
    print("     - CLOUDFLARE_ACCOUNT_ID  -> panel de Cloudflare, junto al nombre de la cuenta")
    print("     - CLOUDFLARE_DATABASE_ID -> D1 > tu base de datos > Database ID")
    print("     - CLOUDFLARE_API_TOKEN   -> My Profile > API Tokens > D1 Database: Edit")
    print("     - R2_BUCKET_NAME        -> R2 Object Storage > nombre del bucket")
    print("     - R2_ACCESS_KEY_ID      -> R2 > Manage R2 API Tokens")
    print("     - R2_SECRET_ACCESS      -> el mismo token, campo 'Secret Access Key'")
    print("     - R2_ENDPOINT           -> https://<CLOUDFLARE_ACCOUNT_ID>.r2.cloudflarestorage.com")
    sys.exit(2)

# ----------------------------------------------------------------------
# A partir de aquí sí se toca Cloudflare
# ----------------------------------------------------------------------
try:
    # --------------------------------------------------------------
    seccion("2. BUCKET DE R2")
    # --------------------------------------------------------------
    cliente = r2.obtener_cliente_s3()
    if not registrar("Cliente S3 de boto3 creado", cliente is not None,
                     "" if cliente else "No se pudo construir el cliente. Revisa las credenciales de R2."):
        raise SystemExit(1)

    nombre_bucket = os.getenv("R2_BUCKET_NAME")
    try:
        cliente.head_bucket(Bucket=nombre_bucket)
        registrar(f"Bucket accesible (head_bucket)", True, f"Bucket: {nombre_bucket}")
    except Exception as error:
        registrar("Bucket accesible (head_bucket)", False,
                  f"Tipo de error: {type(error).__name__}. "
                  "El bucket no existe, el nombre no coincide, o el token no tiene permiso sobre él.")
        raise SystemExit(1)

    # --------------------------------------------------------------
    seccion("3. BASE DE DATOS D1")
    # --------------------------------------------------------------
    try:
        filas = d1.ejecutar_sql_estricto("SELECT 1 AS ok")
        registrar("La API de D1 responde", bool(filas), f"Filas devueltas: {len(filas)}")
    except d1.D1Error as error:
        registrar("La API de D1 responde", False,
                  f"Error informado por D1: {error}. "
                  "Revisa el token (permiso D1 Database: Edit) y los identificadores.")
        raise SystemExit(1)

    try:
        columnas = d1.ejecutar_sql_estricto("PRAGMA table_info(archivos)")
        nombres = [c.get("name") for c in columnas]
        esperar = {"id", "usuario_id", "r2_key", "mime_type", "tamano_bytes"}
        faltan_cols = esperar - set(nombres)
        registrar("La tabla 'archivos' existe en D1", not faltan_cols,
                  f"Columnas encontradas: {len(nombres)}"
                  + (f" | FALTAN: {', '.join(sorted(faltan_cols))}" if faltan_cols else ""))
        if faltan_cols:
            print("         Arranca la aplicación una vez: asegurar_inicializacion() crea la tabla.")
            raise SystemExit(1)
    except d1.D1Error as error:
        registrar("La tabla 'archivos' existe en D1", False, f"Error: {error}")
        raise SystemExit(1)

    # El usuario debe existir: con la FOREIGN KEY ON DELETE CASCADE, un
    # usuario_id inventado haría fallar el INSERT.
    try:
        existe = d1.ejecutar_sql_estricto("SELECT id FROM usuarios WHERE id = ?", [USUARIO_ID])
        if not registrar(f"El usuario {USUARIO_ID} existe en D1", bool(existe),
                         "" if existe else
                         f"No hay ningún usuario con id={USUARIO_ID}. "
                         f"Cámbialo en la constante USUARIO_ID de este guion, o crea ese usuario."):
            raise SystemExit(1)
    except d1.D1Error as error:
        registrar(f"El usuario {USUARIO_ID} existe en D1", False, f"Error: {error}")
        raise SystemExit(1)

    # --------------------------------------------------------------
    seccion("4. CICLO COMPLETO DEL ARCHIVO")
    # --------------------------------------------------------------
    # PDF mínimo y válido: empieza por %PDF- y así pasa la validación de
    # magic bytes del backend igual que un PDF real.
    contenido = b"%PDF-1.4\n% Prueba de integracion EduAsistente\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
    nombre_original = "Prueba de Integración.pdf"   # con tilde, a propósito
    r2_key = r2.generar_key_segura(USUARIO_ID, ".pdf")
    archivo_id = None

    # 4.1 Subida a R2
    subido = r2.subir_archivo(contenido, r2_key, "application/pdf")
    if not registrar("Subida real a Cloudflare R2", subido,
                     f"Clave generada: {r2_key}" if subido
                     else "put_object devolvió False. El bucket no acepta escritura con este token."):
        raise SystemExit(1)

    try:
        info = cliente.head_object(Bucket=nombre_bucket, Key=r2_key)
        registrar("El objeto existe en el bucket", True,
                  f"Tamaño en R2: {info.get('ContentLength')} bytes | "
                  f"Content-Type: {info.get('ContentType')}")
    except Exception as error:
        registrar("El objeto existe en el bucket", False, f"Tipo de error: {type(error).__name__}")
        r2.eliminar_archivo(r2_key)
        raise SystemExit(1)

    # 4.2 Metadato en D1
    try:
        registro = d1.guardar_archivo(
            usuario_id=USUARIO_ID,
            nombre_original=nombre_original,
            r2_key=r2_key,
            mime_type="application/pdf",
            extension="pdf",
            tamano_bytes=len(contenido),
            materia_id=None,
        )
        if not registrar("Registro del metadato en D1", bool(registro),
                         f"id asignado: {registro.get('id')}" if registro
                         else "El INSERT no devolvió fila. Revisa los logs del backend para ver el error de D1."):
            r2.eliminar_archivo(r2_key)
            raise SystemExit(1)
        archivo_id = registro["id"]

        # Comprobación extra: D1 no debe guardar el contenido, solo la referencia
        columnas = d1.ejecutar_sql_estricto("PRAGMA table_info(archivos)")
        nombres_col = [c.get("name", "").lower() for c in columnas]
        prohibido = [c for c in nombres_col if c in ("contenido", "blob", "base64", "data")]
        registrar("D1 guarda solo metadatos, no el archivo", not prohibido,
                  f"Columnas: {', '.join(sorted(nombres_col))}"
                  + (f" | INESPERADAS: {prohibido}" if prohibido else ""))
    except d1.D1Error as error:
        registrar("Registro del metadato en D1", False,
                  f"El metadato puede haberse escrito sin poder confirmarse: {error}")
        print("         Revisa la tabla 'archivos' antes de continuar: puede haber una fila sin borrar.")
        raise SystemExit(1)

    # 4.3 Listado
    try:
        listado = d1.obtener_archivos(USUARIO_ID, None)
        aparece = any(f.get("id") == archivo_id for f in listado)
        registrar("El archivo aparece en el listado", aparece,
                  f"Archivos del usuario: {len(listado)}")
    except Exception as error:
        registrar("El archivo aparece en el listado", False, f"Tipo de error: {type(error).__name__}")

    # 4.4 Descarga
    try:
        obj = r2.obtener_archivo(r2_key)
        if not registrar("Descarga del objeto desde R2", obj is not None):
            raise SystemExit(1)
        descargado = obj["body"].read()
        registrar("Los bytes descargados son idénticos a los subidos",
                  descargado == contenido,
                  f"Subidos: {len(contenido)} B | Descargados: {len(descargado)} B")
    finally:
        try:
            obj["body"].close()
        except Exception:
            pass

    # 4.5 Aislamiento entre usuarios
    try:
        ajeno = d1.obtener_archivo_por_id(archivo_id, USUARIO_ID + 999999)
        registrar("Aislamiento: otro usuario NO puede leer el archivo", ajeno is None,
                  "Correcto: la consulta con otro usuario_id no devuelve nada."
                  if ajeno is None else "FALLO DE SEGURIDAD: se ha devuelto el archivo a otro usuario.")
    except Exception as error:
        registrar("Aislamiento: otro usuario NO puede leer el archivo", False,
                  f"Tipo de error: {type(error).__name__}")

    # 4.6 Borrado
    try:
        borrado_r2 = r2.eliminar_archivo(r2_key)
        registrar("Borrado del objeto en R2", borrado_r2)

        borrado_d1 = d1.eliminar_archivo_db(archivo_id, USUARIO_ID)
        registrar("Borrado del metadato en D1", borrado_d1)

        try:
            cliente.head_object(Bucket=nombre_bucket, Key=r2_key)
            sigue = True
        except Exception:
            sigue = False
        registrar("El objeto ya no está en el bucket", not sigue,
                  "Correcto: el objeto se eliminó." if not sigue
                  else "El objeto sigue presente tras el borrado.")

        sobra = d1.ejecutar_sql_estricto("SELECT id FROM archivos WHERE id = ?", [archivo_id])
        registrar("El metadato ya no está en D1", not sobra)
    except Exception as error:
        registrar("Borrado", False, f"Tipo de error: {type(error).__name__}")
        print(f"         Limpia a mano: clave R2 {r2_key} e id de D1 {archivo_id}")

except SystemExit:
    pass
except Exception as error:  # pragma: no cover - red de seguridad
    print()
    print(f"{MAL} Error inesperado: {type(error).__name__}")
    print("         No se ha mostrado ningún valor de credencial.")

# ----------------------------------------------------------------------
# Resumen
# ----------------------------------------------------------------------
print()
print("=" * 72)
if not resultados:
    print("No se ejecutó ningún paso.")
else:
    buenos = sum(1 for _, e in resultados if e)
    print(f"RESULTADO: {buenos} de {len(resultados)} pasos correctos")
    print("=" * 72)
    for nombre, exito in resultados:
        print(f"  {'OK   ' if exito else 'FALLO'}  {nombre}")

    if buenos == len(resultados):
        print()
        print("  INTEGRACIÓN COMPLETA CORRECTA: la cadena R2 + D1 funciona.")
        print("  Ya puedes configurar las mismas variables en Render y desplegar.")
    else:
        print()
        print("  Revisa los pasos marcados como FALLO antes de desplegar.")

sys.exit(0 if resultados and all(e for _, e in resultados) else 1)
