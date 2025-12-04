from app.backend.db_connection import get_connection

def verificar_es_admin(id_usuario):
    """
    Verifica si un usuario existe en la tabla de administradores.
    No toca la tabla de usuarios original.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Consultamos la tabla satélite
            sql = "SELECT nivel FROM administradores WHERE id_usuario = %s"
            cursor.execute(sql, (id_usuario,))
            resultado = cursor.fetchone()
            
        if resultado:
            return {"es_admin": True, "nivel": resultado["nivel"]}
        else:
            return {"es_admin": False, "nivel": None}
    except Exception as e:
        print("Error verificando admin:", e)
        return {"es_admin": False, "nivel": None}
    finally:
        conn.close()

def obtener_dashboard_admin():
    """
    Obtiene los KPIs globales desde la vista SQL que creamos.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Usamos la vista para no hacer cálculos pesados en Python
            cursor.execute("SELECT * FROM vista_admin_dashboard")
            kpis = cursor.fetchone()
            
            # Obtenemos la lista de usuarios con sus estadísticas
            cursor.execute("SELECT * FROM vista_lista_usuarios_admin")
            usuarios = cursor.fetchall()
            
        return {"ok": True, "kpis": kpis, "usuarios": usuarios}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

def eliminar_usuario_desde_admin(id_admin, id_usuario_a_eliminar, motivo):
    """
    Registra el log y elimina al usuario usando transacciones.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Verificar nivel del admin (opcional, por seguridad extra)
            cursor.execute("SELECT nivel FROM administradores WHERE id_usuario = %s", (id_admin,))
            admin = cursor.fetchone()
            if not admin:
                raise Exception("No tienes permisos de administrador")

            # 2. Registrar en LOGS (Tabla logs_admin)
            cursor.execute("""
                INSERT INTO logs_admin (id_usuario_admin, accion, descripcion)
                VALUES (%s, 'ELIMINAR_USUARIO', %s)
            """, (id_admin, f"Se eliminó al usuario ID {id_usuario_a_eliminar}. Motivo: {motivo}"))

            # 3. Eliminar usuario (CASCADE borrará sus hábitos y reportes automáticamente)
            cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario_a_eliminar,))
        
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()