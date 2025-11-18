import json
from app.backend.db_connection import get_connection

# Crear hábito
def crear_habito(id_usuario, id_categoria, nombre_habito, descripcion, frecuencia, hora_objetivo):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO habitos (id_usuario, id_categoria, nombre_habito, descripcion, frecuencia, hora_objetivo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_usuario, id_categoria, nombre_habito, descripcion, frecuencia, hora_objetivo))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        print("ERROR CREANDO HÁBITO:", e)
        return {"ok": False}


# Listar por usuario
def listar_habitos_por_usuario(id_usuario):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT h.*, c.nombre_categoria AS categoria
                FROM habitos h
                LEFT JOIN categorias c ON h.id_categoria = c.id_categoria
                WHERE h.id_usuario = %s AND h.activo = 1
            """, (id_usuario,))
            habitos = cursor.fetchall()

        return {"ok": True, "habitos": habitos}
    except Exception as e:
        print("ERROR LISTANDO HABITOS:", e)
        return {"ok": False, "habitos": []}


# Actualizar hábito
def actualizar_habito(id_habito, nombre_habito, descripcion, frecuencia, hora_objetivo=None, activo=True):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE habitos
                SET nombre_habito=%s, descripcion=%s, frecuencia=%s, hora_objetivo=%s, activo=%s
                WHERE id_habito=%s
            """, (nombre_habito, descripcion, frecuencia, hora_objetivo, activo, id_habito))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        print("ERROR ACTUALIZANDO HABITO:", e)
        return {"ok": False}


# Eliminar hábito
def eliminar_habito(habito_id):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM habitos WHERE id_habito = %s
            """, (habito_id,))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        print("ERROR ELIMINANDO HABITO:", e)
        return {"ok": False}

