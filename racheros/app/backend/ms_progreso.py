# ms_progreso.py
# --------------
# Microservicio de PROGRESO:
# - registrar check diario
# - obtener progreso por hábito

import json
from datetime import date
from app.backend.db_connection import get_connection



def registrar_progreso(id_habito, fecha=None, completado=True, comentario=None):
    if fecha is None:
        fecha = date.today().isoformat()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Intentamos insertar y si ya existe, actualizamos
            sql_insert = """
                INSERT INTO registro_progreso (id_habito, fecha, completado, comentario)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    completado = VALUES(completado),
                    comentario = VALUES(comentario)
            """
            cursor.execute(sql_insert, (id_habito, fecha, completado, comentario))
        conn.commit()
        return {"ok": True, "message": "Progreso registrado"}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def obtener_progreso_habito(id_habito):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT * FROM registro_progreso
                WHERE id_habito = %s
                ORDER BY fecha DESC
            """
            cursor.execute(sql, (id_habito,))
            rows = cursor.fetchall()
        return {"ok": True, "progreso": rows}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ---------- Handler para AWS Lambda ----------
def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        body = {}

    action = body.get("action")

    if action == "registrar":
        resp = registrar_progreso(
            id_habito=body.get("id_habito"),
            fecha=body.get("fecha"),
            completado=body.get("completado", True),
            comentario=body.get("comentario")
        )
    elif action == "listar":
        resp = obtener_progreso_habito(body.get("id_habito"))
    else:
        resp = {"ok": False, "error": "Acción no válida en ms_progreso"}

    return {
        "statusCode": 200 if resp.get("ok") else 400,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(resp, default=str)
    }
