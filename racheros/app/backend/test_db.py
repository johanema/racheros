from db_connection import get_connection

try:
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        print("Conexión exitosa. Tablas encontradas:")
        for row in cursor.fetchall():
            print(row)
except Exception as e:
    print("ERROR:", e)
