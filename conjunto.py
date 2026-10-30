from flask import Blueprint, request, render_template
from config import conectar, desconectar
from auth import login_requerido
import psycopg2

conjunto_bp = Blueprint('conjunto', __name__)


@conjunto_bp.route("/Proyecto_conjunto/registrar_conj", methods=["GET", "POST"])
def registrar_conj():
    if request.method == "POST":
        idconjunto = request.form["idconjunto"]
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        direccion = request.form["direccion"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]

        conexion = None
        cursor = None
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            consulta = """
            INSERT INTO conjunto (idconjunto, nombre, apellido, direccion, correo, telefono)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            datos = (idconjunto, nombre, apellido, direccion, correo, telefono)
            cursor.execute(consulta, datos)
            conexion.commit()
            return "El conjunto fue registrado con exito"
        except (Exception, psycopg2.Error) as error:
            print("Error al registrar el conjunto:", error)
            return "Error al registrar el conjunto"
        finally:
            if cursor:
                cursor.close()
            if conexion:
                desconectar(conexion)
    else:
        return render_template("registrar.html")


@conjunto_bp.route("/Proyecto_conjunto/consultar_conj")
def consulta_conj():
    conexion = None
    cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        consulta = "SELECT idconjunto, nombre, apellido, direccion, correo, telefono FROM conjunto;"
        cursor.execute(consulta)
        conjunto = cursor.fetchall()
        return render_template("consultar.html", datos=conjunto)
    except (Exception, psycopg2.Error) as error:
        print("Detalle del error en PostgreSQL:", error)
        return f"Error al obtener la lista de conjuntos: {error}"
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)


@conjunto_bp.route("/Proyecto_conjunto/actualizar_conj", methods=["POST"])
@login_requerido(rol_requerido='admin')
def actualizar_conj():
    idconjunto = request.form["idconjunto"]
    nombre = request.form["nombre"]
    apellido = request.form["apellido"]
    direccion = request.form["direccion"]
    correo = request.form["correo"]
    telefono = request.form["telefono"]

    conexion = None
    cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        consulta = """
        UPDATE conjunto SET
        nombre = %s, apellido = %s, direccion = %s, correo = %s, telefono = %s
        WHERE idconjunto = %s;
        """
        datos = (nombre, apellido, direccion, correo, telefono, idconjunto)
        cursor.execute(consulta, datos)
        conexion.commit()
        return "El conjunto fue actualizado con exito"
    except (Exception, psycopg2.Error) as error:
        print("Error al actualizar:", error)
        return f"Error al actualizar el conjunto: {error}"
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)


@conjunto_bp.route("/Proyecto_4/eliminar_conj", methods=["GET", "POST"])
@login_requerido(rol_requerido='admin')
def eliminar_conj():
    if request.method == "POST":
        doc = request.form["idconjunto"]
        conexion = None
        cursor = None
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            consulta = "DELETE FROM conjunto WHERE idconjunto = %s"
            cursor.execute(consulta, (doc,))
            conexion.commit()
            return "El conjunto fue eliminado correctamente"
        except (Exception, psycopg2.Error) as error:
            print("Error al eliminar el conjunto:", error)
            return f"Error al eliminar el conjunto: {error}"
        finally:
            if cursor:
                cursor.close()
            if conexion:
                desconectar(conexion)
    else:
        return render_template("eliminar.html")
