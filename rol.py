from flask import Blueprint, request, render_template, redirect, url_for, flash
from config import conectar, desconectar
from auth import login_requerido
import psycopg2

rol_bp = Blueprint('rol', __name__)


@rol_bp.route("/consultar_rol", methods=["GET", "POST"])
def consultar_rol():
    if request.method == "POST":
        accion = request.form.get("accion")
        resultado = "Acción no válida"

        if accion == "registrar":
            resultado = registrar_rol()
        elif accion == "actualizar":
            resultado = actualizar_rol()
        elif accion == "eliminar":
            resultado = eliminar_rol()

        if not isinstance(resultado, str):
            return resultado

        flash(resultado)
        return redirect(url_for("rol.consultar_rol"))

    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT idrol, tipo_rol, activo FROM rol ORDER BY idrol;")
        roles = cursor.fetchall()
        return render_template("CRUD/consultarol.html", roles=roles)
    except Exception as error:
        import traceback
        traceback.print_exc()
        return f"Error al obtener la lista de roles: {type(error).__name__}: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


def registrar_rol():
    f = request.form
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO rol (tipo_rol, activo)
            VALUES (%s, %s)
        """, (f["tipo_rol"], f["activo"]))
        conexion.commit()
        return "El rol fue registrado con éxito"
    except psycopg2.errors.UniqueViolation:
        if conexion: conexion.rollback()
        return "Error: ese rol ya existe"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al registrar:", error)
        return f"Error al registrar el rol: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def actualizar_rol():
    f = request.form
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE rol SET tipo_rol=%s, activo=%s
            WHERE idrol=%s
        """, (f["tipo_rol"], f["activo"], f["idrol"]))
        conexion.commit()
        return "El rol fue actualizado con éxito"
    except psycopg2.errors.UniqueViolation:
        if conexion: conexion.rollback()
        return "Error: ese rol ya existe"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al actualizar:", error)
        return f"Error al actualizar el rol: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def eliminar_rol():
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE rol SET activo = FALSE WHERE idrol = %s",
                       (request.form["idrol"],))
        conexion.commit()
        return "El rol fue desactivado correctamente"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al desactivar:", error)
        return f"Error al desactivar: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)