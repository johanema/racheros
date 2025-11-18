# ms_notificaciones.py
# --------------------
# Microservicio de NOTIFICACIONES:
# - simula envío de correo cuando un reporte está listo.
import json
from app.backend.db_connection import get_connection


def enviar_notificacion_correo(correo_destino, asunto, mensaje):
    # LOCAL: solo simulamos
    print("=== ENVIANDO CORREO ===")
    print("Para:", correo_destino)
    print("Asunto:", asunto)
    print("Mensaje:", mensaje)
    print("========================")
    return {"ok": True, "message": "Correo simulado (local)"}


# ---------- Handler para AWS Lambda ----------
def lambda_handler(event, context):
    """
    En AWS, EventBridge mandaría algo como:
    {
      "detail-type": "reporte.generado",
      "detail": {
        "correo": "alguien@correo.com",
        "id_usuario": 1,
        "ruta_pdf_s3": "s3://...."
      }
    }
    """
    # Si viene de API Gateway, puede venir en body. Si viene de EventBridge, viene en "detail".
    body = {}
    if "detail" in event:
        body = event["detail"]
    else:
        try:
            body = json.loads(event.get("body") or "{}")
        except Exception:
            body = {}

    correo = body.get("correo")
    ruta_pdf = body.get("ruta_pdf_s3", "(sin PDF)")
    id_usuario = body.get("id_usuario", "desconocido")

    if not correo:
        resp = {"ok": False, "error": "Falta correo en notificación"}
    else:
        asunto = "Tu reporte semanal está listo"
        mensaje = f"Hola, tu reporte semanal del usuario {id_usuario} está listo.\nPDF: {ruta_pdf}"
        resp = enviar_notificacion_correo(correo, asunto, mensaje)

    return {
        "statusCode": 200 if resp.get("ok") else 400,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(resp, default=str)
    }
