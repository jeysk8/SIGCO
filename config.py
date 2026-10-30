import os
import psycopg2

def conectar():
    url = os.environ.get("DATABASE_URL")
    try:
        if url:
            return psycopg2.connect(url)
        if os.environ.get("VERCEL"):
            raise RuntimeError("DATABASE_URL no llega en Vercel")
        return psycopg2.connect(
            user="postgres",
            password="123456",
            host="localhost",
            port="5432",
            database="conjuntoresidencial"
        )
    except (Exception, psycopg2.Error) as error:
        print("Error al conectar a PostgreSQL", error)
        return None

def desconectar(conexion):
    if conexion is not None:
        conexion.close()
