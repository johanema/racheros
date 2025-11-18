# app/backend/ms_usuarios.py

import hashlib
from app.backend.db_connection import get_connection


def _hash_password(contrasena: str) -> str:
    """Genera un hash SHA256 de la contraseña."""
    return hashlib.sha256(contrasena.encode("utf-8")).hexdigest()


# =====================================================
#  login_usuario
# =====================================================
def login_usuario(correo: str, contrasena: str):
    """
    Valida las credenciales de un usuario.
    Retorna:
        {
            "ok": True/False,
            "user": { ...datos usuario... } o None,
            "error": "mensaje" (cuando ok=False)
        }
    """
    conn = get_connection()
    try:
        contrasena_hash = _hash_password(contrasena)

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

        if user["contrasena_hash"] != contrasena_hash:
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
    Retorna:
        { "ok": True/False, "id_usuario": int|None, "error": str|None }
    """
    conn = get_connection()
    try:
        contrasena_hash = _hash_password(contrasena)

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
