# db_connection.py
# ----------------
# ESTE ARCHIVO sirve para local y para AWS.
# Local: host=localhost, user=root, password=lo_que_uses
# AWS: solo cambias las variables de entorno.

import os
import pymysql


def get_connection():
    """
    Regresa una conexión a MySQL.
    - Para local: usa localhost, root, sin password (o la que tengas).
    - Para AWS: cambias las variables de entorno en Lambda.
    """
    connection = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "gestor_habitos"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    return connection
