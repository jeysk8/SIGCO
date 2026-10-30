from flask import Blueprint, request, render_template, redirect, url_for, flash
from config import conectar, desconectar
from auth import login_requerido
import psycopg2

propiedad_bp = Blueprint('propiedad', __name__)


@propiedad_bp.route("/consultar_propiedad", methods=["GET", "POST"])
def consultar_propiedad():
    if request.method == "POST":
        accion = request.form.get("accion")
        resultado = "Acción no válida"

        if accion == "registrar":
            resultado = registrar_propiedad()
        elif accion == "actualizar":
            resultado = actualizar_propiedad()
        elif accion == "eliminar":
            resultado = eliminar_propiedad()

        if not isinstance(resultado, str):
            return resultado

        flash(resultado)
        return redirect(url_for("propiedad.consultar_propiedad"))

    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT idpro, tipo_vivienda, numvivienda, activo
            FROM propiedad
            ORDER BY idpro;
        """)
        propiedades = cursor.fetchall()
        return render_template("CRUD/consultapropiedad.html", propiedades=propiedades)
    except Exception as error:
        import traceback
        traceback.print_exc()
        return f"Error al obtener las propiedades: {type(error).__name__}: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


def registrar_propiedad():
    f = request.form
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO propiedad (tipo_vivienda, numvivienda, activo)
            VALUES (%s, %s, %s)
        """, (f["tipo_vivienda"], f["numvivienda"], f["activo"]))
        conexion.commit()
        return "La propiedad fue registrada con éxito"
    except psycopg2.errors.UniqueViolation:
        if conexion: conexion.rollback()
        return "Error: esa propiedad ya existe"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al registrar:", error)
        return f"Error al registrar la propiedad: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def actualizar_propiedad():
    f = request.form
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE propiedad
            SET tipo_vivienda=%s, numvivienda=%s, activo=%s
            WHERE idpro=%s
        """, (f["tipo_vivienda"], f["numvivienda"], f["activo"], f["idpro"]))
        conexion.commit()
        return "La propiedad fue actualizada con éxito"
    except psycopg2.errors.UniqueViolation:
        if conexion: conexion.rollback()
        return "Error: esa propiedad ya existe"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al actualizar:", error)
        return f"Error al actualizar la propiedad: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def eliminar_propiedad():
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE propiedad SET activo = FALSE WHERE idpro = %s",
                       (request.form["idpro"],))
        conexion.commit()
        return "La propiedad fue desactivada correctamente"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al desactivar:", error)
        return f"Error al desactivar: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)