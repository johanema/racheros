from app.backend.db_connection import get_connection

def verificar_es_admin(id_usuario):
    """
    Verifica si un usuario tiene privilegios de administrador.
    Retorna un diccionario con el estado y el nivel de acceso.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Consultamos la tabla satélite 'administradores'
            sql = "SELECT nivel FROM administradores WHERE id_usuario = %s"
            cursor.execute(sql, (id_usuario,))
            resultado = cursor.fetchone()
            
        if resultado:
            return {"es_admin": True, "nivel": resultado["nivel"]}
        else:
            return {"es_admin": False, "nivel": None}
            
    except Exception as e:
        print(f"Error crítico verificando admin: {e}")
        return {"es_admin": False, "nivel": None}
    finally:
        if conn:
            conn.close()

def obtener_dashboard_admin():
    """
    Obtiene toda la información necesaria para el panel de control:
    - KPIs globales (Usuarios, Actividad, Cumplimiento)
    - Lista detallada de usuarios
    - Logs recientes del sistema
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Obtener KPIs desde la vista SQL optimizada
            cursor.execute("SELECT * FROM vista_admin_dashboard")
            kpis = cursor.fetchone()
            
            # 2. Obtener lista de usuarios con sus estadísticas
            # Ordenamos por fecha de registro descendente (los nuevos primero)
            cursor.execute("SELECT * FROM vista_lista_usuarios_admin ORDER BY fecha_registro DESC")
            usuarios = cursor.fetchall()

            # 3. Obtener los últimos 5 logs de auditoría (Quién hizo qué)
            cursor.execute("""
                SELECT l.accion, l.descripcion, l.fecha, u.nombre as admin_nombre
                FROM logs_admin l
                LEFT JOIN usuarios u ON l.id_usuario_admin = u.id_usuario
                ORDER BY l.fecha DESC LIMIT 5
            """)
            logs = cursor.fetchall()
            
        return {
            "ok": True, 
            "kpis": kpis, 
            "usuarios": usuarios,
            "logs": logs
        }

    except Exception as e:
        print(f"Error cargando dashboard admin: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

def eliminar_usuario_desde_admin(id_admin, id_usuario_a_eliminar, motivo):
    """
    Elimina un usuario de forma segura y auditada.
    Usa transacciones para asegurar que si falla el log, no se borre el usuario.
    """
    conn = get_connection()
    try:
        # Iniciamos transacción manualmente (autocommit=False en db_connection)
        conn.begin()
        
        with conn.cursor() as cursor:
            # 1. VERIFICACIÓN DE SEGURIDAD
            # Validamos que quien ejecuta esto sea realmente admin
            cursor.execute("SELECT nivel FROM administradores WHERE id_usuario = %s", (id_admin,))
            admin_request = cursor.fetchone()
            
            if not admin_request:
                raise Exception("Acceso denegado: No tienes privilegios.")

            # 2. PROTECCIÓN DE SUPERADMINS
            # Verificamos que no estemos intentando borrar a otro admin (opcional, pero recomendado)
            cursor.execute("SELECT nivel FROM administradores WHERE id_usuario = %s", (id_usuario_a_eliminar,))
            target_is_admin = cursor.fetchone()
            
            if target_is_admin:
                raise Exception("No se puede eliminar a otro Administrador desde la web. Contacta a soporte DB.")

            # 3. OBTENER DATOS PARA EL LOG (Antes de borrar)
            cursor.execute("SELECT nombre, correo FROM usuarios WHERE id_usuario = %s", (id_usuario_a_eliminar,))
            usuario_target = cursor.fetchone()
            nombre_target = usuario_target['nombre'] if usuario_target else 'Desconocido'
            correo_target = usuario_target['correo'] if usuario_target else 'Sin correo'

            # 4. REGISTRAR EN LOGS (Auditoría)
            detalle_log = f"Usuario eliminado: {nombre_target} ({correo_target}). ID: {id_usuario_a_eliminar}. Motivo: {motivo}"
            cursor.execute("""
                INSERT INTO logs_admin (id_usuario_admin, accion, descripcion)
                VALUES (%s, 'ELIMINAR_USUARIO', %s)
            """, (id_admin, detalle_log))

            # 5. ELIMINAR USUARIO
            # Gracias al ON DELETE CASCADE en la BD, esto borrará sus hábitos, reportes y progresos automáticamente.
            cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario_a_eliminar,))
        
        # Si todo salió bien, guardamos cambios
        conn.commit()
        return {"ok": True, "mensaje": f"Usuario {nombre_target} eliminado correctamente."}

    except Exception as e:
        # Si algo falla, deshacemos todo (Rollback)
        conn.rollback()
        print(f"Error eliminando usuario: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if conn:
            conn.close()