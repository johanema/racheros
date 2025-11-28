# db_connection.py
# ----------------
# ARCHIVO SEGURO: CARGA VARIABLES DESDE .env

import os
import pymysql
from dotenv import load_dotenv

# Carga automática del archivo .env
load_dotenv()

def get_connection():
    print("🔥 DEBUG DB_HOST:", os.environ.get("DB_HOST"))
    print("🔥 DEBUG DB_USER:", os.environ.get("DB_USER"))
    print("🔥 DEBUG DB_PASSWORD:", os.environ.get("DB_PASSWORD"))
    print("🔥 DEBUG DB_NAME:", os.environ.get("DB_NAME"))

    """
    Regresa una conexión a la base de datos RDS.
    Usa las variables almacenadas en el archivo .env
    (solo en tu máquina local).
    """
    connection = pymysql.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME", "gestor_habitos"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    return connection
