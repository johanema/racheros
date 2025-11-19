# CAMBIO: Usamos la librería estándar de seguridad de Flask
from werkzeug.security import generate_password_hash, check_password_hash
from app.backend.db_connection import get_connection

# =====================================================
#  login_usuario
# =====================================================
def login_usuario(correo: str, contrasena: str):
    """
    Valida las credenciales de un usuario.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_usuario, nombre, correo, contrasena_hash,
                       genero, edad, estado
                FROM usuarios
                WHERE correo = %s
                """,
                (correo,)
            )
            user = cursor.fetchone()

        if not user:
            return {"ok": False, "user": None, "error": "Usuario no encontrado"}

        # CAMBIO: Usamos check_password_hash para validar de forma segura
        if not check_password_hash(user["contrasena_hash"], contrasena):
            return {"ok": False, "user": None, "error": "Contraseña incorrecta"}

        if user["estado"] != "activo":
            return {"ok": False, "user": None, "error": "Usuario inactivo"}

        return {"ok": True, "user": user, "error": None}

    except Exception as e:
        return {"ok": False, "user": None, "error": str(e)}
    finally:
        conn.close()


# =====================================================
#  crear_usuario
# =====================================================
def crear_usuario(nombre: str, correo: str, contrasena: str,
                  genero: str = "otro", edad: int | None = None):
    """
    Crea un nuevo usuario en la base de datos.
    """
    conn = get_connection()
    try:
        # CAMBIO: Encriptamos con salt automático
        contrasena_hash = generate_password_hash(contrasena)

        with conn.cursor() as cursor:
            # Verificar que no exista ese correo
            cursor.execute(
                "SELECT id_usuario FROM usuarios WHERE correo = %s",
                (correo,)
            )
            existe = cursor.fetchone()
            if existe:
                return {
                    "ok": False,
                    "id_usuario": None,
                    "error": "El correo ya está registrado"
                }

            cursor.execute(
                """
                INSERT INTO usuarios (nombre, correo, contrasena_hash, genero, edad, estado)
                VALUES (%s, %s, %s, %s, %s, 'activo')
                """,
                (nombre, correo, contrasena_hash, genero, edad)
            )
            conn.commit()
            nuevo_id = cursor.lastrowid

        return {"ok": True, "id_usuario": nuevo_id, "error": None}

    except Exception as e:
        conn.rollback()
        return {"ok": False, "id_usuario": None, "error": str(e)}
    finally:
        conn.close()


# =====================================================
#  FUNCIONES DE RECUPERACIÓN (NECESARIAS PARA ROUTES.PY)
# =====================================================

def verificar_correo_existe(correo: str):
    """Verifica si un correo existe en la BD para recuperación."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id_usuario, nombre FROM usuarios WHERE correo = %s", (correo,))
            user = cursor.fetchone()
            return user 
    except Exception:
        return None
    finally:
        conn.close()

def actualizar_contrasena(correo: str, nueva_contrasena: str):
    """Actualiza la contraseña de un usuario."""
    conn = get_connection()
    try:
        # CAMBIO: Encriptamos la nueva contraseña con el método seguro
        nuevo_hash = generate_password_hash(nueva_contrasena)
        
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET contrasena_hash = %s WHERE correo = %s",
                (nuevo_hash, correo)
            )
            conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()