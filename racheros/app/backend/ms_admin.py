from app.backend.db_connection import get_connection
from datetime import date, timedelta

def verificar_es_admin(id_usuario):
    """Verifica si el usuario es administrador."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT nivel FROM administradores WHERE id_usuario = %s"
            cursor.execute(sql, (id_usuario,))
            resultado = cursor.fetchone()
        
        if resultado:
            return {"es_admin": True, "nivel": resultado["nivel"]}
        return {"es_admin": False, "nivel": None}
    except Exception as e:
        print(f"Error admin: {e}")
        return {"es_admin": False, "nivel": None}
    finally:
        if conn: conn.close()

def obtener_datos_graficas():
    """
    Calcula los datos REALES para las gráficas de Chart.js
    basados en la actividad de la base de datos.
    """
    conn = get_connection()
    graficas = {
        "actividad": {"labels": [], "data": []},
        "categorias": {"labels": [], "data": []}
    }
    try:
        with conn.cursor() as cursor:
            # --- 1. ACTIVIDAD SEMANAL (Últimos 7 días) ---
            # Obtenemos los días que tuvieron hábitos completados
            cursor.execute("""
                SELECT DATE(fecha) as dia, COUNT(*) as total 
                FROM registro_progreso
                WHERE completado = 1 AND fecha >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
                GROUP BY DATE(fecha)
            """)
            rows = cursor.fetchall()
            
            # Convertimos a un diccionario para fácil acceso: {'2023-10-20': 5, ...}
            data_map = {str(r['dia']): r['total'] for r in rows}
            
            # Rellenamos los 7 días (incluso si no hubo actividad)
            hoy = date.today()
            dias_semana = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
            
            # Iteramos desde hace 6 días hasta hoy
            for i in range(6, -1, -1):
                d = hoy - timedelta(days=i)
                d_str = d.isoformat()
                
                # Etiqueta: Nombre del día (ej: "Lun")
                # weekday(): 0=Lun, 6=Dom. Ajustamos índice para nuestro array dias_semana que empieza en Dom(0)
                # python weekday es 0=Lunes. Mi array dias_semana: 0=Dom, 1=Lun.
                # Truco: (d.weekday() + 1) % 7 da el índice correcto para ["Dom","Lun",...]
                idx_dia = (d.weekday() + 1) % 7
                graficas["actividad"]["labels"].append(dias_semana[idx_dia])
                
                # Dato: Valor real o 0
                graficas["actividad"]["data"].append(data_map.get(d_str, 0))

            # --- 2. DISTRIBUCIÓN POR CATEGORÍA ---
            cursor.execute("""
                SELECT c.nombre_categoria, COUNT(h.id_habito) as total
                FROM habitos h
                LEFT JOIN categorias c ON h.id_categoria = c.id_categoria
                WHERE h.activo = 1
                GROUP BY c.nombre_categoria
            """)
            rows_cat = cursor.fetchall()
            
            for r in rows_cat:
                cat_name = r["nombre_categoria"] if r["nombre_categoria"] else "Sin Categoría"
                graficas["categorias"]["labels"].append(cat_name)
                graficas["categorias"]["data"].append(r["total"])

        return graficas
    except Exception as e:
        print(f"Error generando gráficas: {e}")
        return graficas
    finally:
        if conn: conn.close()

def obtener_top_rankings():
    """Genera los Top 10 para el Salón de la Fama."""
    conn = get_connection()
    rankings = {"top_rachas": [], "top_cumplimiento": [], "top_disciplinados": []}
    try:
        with conn.cursor() as cursor:
            # 1. Top Rachas (Aproximación: días completados en el último mes)
            cursor.execute("""
                SELECT u.nombre, COUNT(DISTINCT r.fecha) as racha_aprox
                FROM usuarios u
                JOIN habitos h ON u.id_usuario = h.id_usuario
                JOIN registro_progreso r ON h.id_habito = r.id_habito
                WHERE r.completado = 1 AND r.fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY u.id_usuario
                ORDER BY racha_aprox DESC LIMIT 10
            """)
            rankings["top_rachas"] = cursor.fetchall()

            # 2. Top Tasa de Éxito (Histórica)
            cursor.execute("""
                SELECT u.nombre, 
                       ROUND((SUM(r.completado) / COUNT(r.id_registro)) * 100, 1) as porcentaje
                FROM usuarios u
                JOIN habitos h ON u.id_usuario = h.id_usuario
                JOIN registro_progreso r ON h.id_habito = r.id_habito
                GROUP BY u.id_usuario
                HAVING COUNT(r.id_registro) >= 5 -- Mínimo 5 registros para participar
                ORDER BY porcentaje DESC LIMIT 10
            """)
            rankings["top_cumplimiento"] = cursor.fetchall()

            # 3. Más Disciplinados (Cantidad de hábitos activos)
            cursor.execute("""
                SELECT u.nombre, COUNT(h.id_habito) as total_habitos
                FROM usuarios u
                JOIN habitos h ON u.id_usuario = h.id_usuario
                WHERE h.activo = 1
                GROUP BY u.id_usuario
                ORDER BY total_habitos DESC LIMIT 10
            """)
            rankings["top_disciplinados"] = cursor.fetchall()
            
        return rankings
    except Exception as e:
        print(f"Error rankings: {e}")
        return rankings
    finally:
        if conn: conn.close()

def obtener_dashboard_admin():
    """Recopila TODA la información para el dashboard."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # KPIs Generales
            cursor.execute("SELECT * FROM vista_admin_dashboard")
            kpis = cursor.fetchone()
            
            # Lista de Usuarios
            cursor.execute("SELECT * FROM vista_lista_usuarios_admin ORDER BY fecha_registro DESC")
            usuarios = cursor.fetchall()
            
            # Logs Recientes
            cursor.execute("""
                SELECT l.accion, l.descripcion, l.fecha, u.nombre as admin_nombre
                FROM logs_admin l
                LEFT JOIN usuarios u ON l.id_usuario_admin = u.id_usuario
                ORDER BY l.fecha DESC LIMIT 5
            """)
            logs = cursor.fetchall()
            
        # Obtenemos datos complejos
        rankings = obtener_top_rankings()
        graficas = obtener_datos_graficas()
            
        return {
            "ok": True, "kpis": kpis, "usuarios": usuarios, 
            "logs": logs, "rankings": rankings, "graficas": graficas
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if conn: conn.close()

def eliminar_usuario_desde_admin(id_admin, id_usuario_a_eliminar, motivo):
    """Elimina usuario usando transacción."""
    conn = get_connection()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            # Validar Admin
            cursor.execute("SELECT nivel FROM administradores WHERE id_usuario = %s", (id_admin,))
            if not cursor.fetchone(): raise Exception("No autorizado")
            
            # Validar que no borre a otro admin
            cursor.execute("SELECT nivel FROM administradores WHERE id_usuario = %s", (id_usuario_a_eliminar,))
            if cursor.fetchone(): raise Exception("No puedes eliminar a otro administrador.")

            # Log
            cursor.execute("SELECT nombre, correo FROM usuarios WHERE id_usuario = %s", (id_usuario_a_eliminar,))
            u = cursor.fetchone()
            nombre = u['nombre'] if u else '?'
            
            cursor.execute("INSERT INTO logs_admin (id_usuario_admin, accion, descripcion) VALUES (%s, 'ELIMINAR', %s)",
                           (id_admin, f"Eliminado: {nombre} (ID {id_usuario_a_eliminar}). Razón: {motivo}"))
            
            # Borrar
            cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario_a_eliminar,))
        
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        if conn: conn.close()