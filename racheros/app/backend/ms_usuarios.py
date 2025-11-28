import os
import requests
from werkzeug.security import generate_password_hash, check_password_hash

# =============================
#  Cargar URL de AWS
# =============================
API_USUARIOS = os.getenv("API_USUARIOS")  # ← RECUERDA AGREGARLO EN .env


# =============================
#  login_usuario
# =============================
def login_usuario(correo: str, contrasena: str):
    """
    Llama al microservicio AWS ms_usuarios/login
    para validar credenciales.
    """
    try:
        payload = {
            "action": "login",
            "correo": correo,
            "contrasena": contrasena
        }

        r = requests.post(API_USUARIOS, json=payload, timeout=10)
        print("DEBUG AWS RESPONSE:", r.text)

        data = r.json()

        return data

    except Exception as e:
        return {"ok": False, "user": None, "error": str(e)}


# =============================
#  crear_usuario
# =============================
def crear_usuario(nombre: str, correo: str, contrasena: str,
                  genero: str = "otro", edad: int | None = None):
    """
    Llama al microservicio AWS para crear usuario.
    """
    try:
        payload = {
            "action": "register",
            "nombre": nombre,
            "correo": correo,
            "contrasena": contrasena,
            "genero": genero,
            "edad": edad
        }

        r = requests.post(API_USUARIOS, json=payload, timeout=10)
        data = r.json()

        return data

    except Exception as e:
        return {"ok": False, "id_usuario": None, "error": str(e)}


# =============================
# Recuperación de correo
# =============================
def verificar_correo_existe(correo: str):
    """Llama al microservicio AWS para verificar correo existente."""
    try:
        payload = {
            "action": "check_email",
            "correo": correo
        }

        r = requests.post(API_USUARIOS, json=payload, timeout=10)
        return r.json()

    except Exception as e:
        return None


def actualizar_contrasena(correo: str, nueva_contrasena: str):
    """Llama al microservicio AWS para actualizar contraseña."""
    try:
        payload = {
            "action": "update_password",
            "correo": correo,
            "nueva_contrasena": nueva_contrasena
        }

        r = requests.post(API_USUARIOS, json=payload, timeout=10)
        return r.json().get("ok", False)

    except:
        return False
