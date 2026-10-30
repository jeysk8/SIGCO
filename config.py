import os

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL_UNPOOLED") or os.environ.get("DATABASE_URL")
print("DATABASE_URL presente:", bool(os.environ.get("DATABASE_URL")))   # <-- AQUÍ

def conectar():
    try:
        conexion = psycopg2.connect(
            user = "postgres",
            password = "123456",
            host = "localhost",
            port = "5432",
            database = "conjuntoresidencial"
        )
        return conexion
        desconectar(conexion)
    except (Exception, psycopg2.Error) as error:
        print("Error al conectar a PostgreSQL", error)

def desconectar(conexion):
    if conexion is not None:
        conexion.close()
        print("Conexion a PostgreSQL cerrada")

conexion = conectar()


if conexion is not None:
    print("Conexion a PostgreSQL establecida correctamente")
else:
    print("Error al conectar a PostgreSQL. No se pudo establecer la conexion.")
