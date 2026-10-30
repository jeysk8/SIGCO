from flask import Blueprint, request, render_template, redirect, url_for, flash
from config import conectar, desconectar
from auth import login_requerido
import psycopg2

cuota_bp = Blueprint('cuota', __name__)


@cuota_bp.route("/consultar_cuota", methods=["GET", "POST"])
def consultar_cuota():
    if request.method == "POST":
        accion = request.form.get("accion")
        resultado = "Acción no válida"

        if accion == "registrar":
            resultado = registrar_cuota()
        elif accion == "actualizar":
            resultado = actualizar_cuota()
        elif accion == "eliminar":
            resultado = eliminar_cuota()

        if not isinstance(resultado, str):
            return resultado

        flash(resultado)
        return redirect(url_for("cuota.consultar_cuota"))

    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT c.idcuo,                                              -- 0
                   CONCAT_WS(' ', p.tipo_vivienda, p.numvivienda),       -- 1 propiedad
                   c.fecha_gen,                                          -- 2
                   c.fecha_lim,                                          -- 3
                   c.monto,                                              -- 4
                   c.estado,                                             -- 5
                   c.idpro,                                              -- 6
                   c.activo                                              -- 7
            FROM cuotas c
            LEFT JOIN propiedad p ON p.idpro = c.idpro
            ORDER BY c.idcuo DESC;
        """)
        cuotas = cursor.fetchall()

        cursor.execute("""
            SELECT idpro, CONCAT_WS(' ', tipo_vivienda, numvivienda)
            FROM propiedad ORDER BY idpro
        """)
        propiedades = cursor.fetchall()

        return render_template("CRUD/consultacuotas.html",
                               cuotas=cuotas, propiedades=propiedades)
    except Exception as error:
        import traceback
        traceback.print_exc()
        return f"Error al obtener las cuotas: {type(error).__name__}: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


def registrar_cuota():
    f = request.form
    conexion = cursor = None
    try:
        if f["fecha_lim"] < f["fecha_gen"]:
            return "Error: la fecha límite no puede ser anterior a la de generación"
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO cuotas (idpro, fecha_gen, fecha_lim, monto, estado, activo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (f["idpro"], f["fecha_gen"], f["fecha_lim"],
              float(f["monto"]), f["estado"], f["activo"]))
        conexion.commit()
        return "La cuota fue registrada con éxito"
    except ValueError:
        if conexion: conexion.rollback()
        return "Error: el monto debe ser numérico"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al registrar:", error)
        return f"Error al registrar la cuota: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def actualizar_cuota():
    f = request.form
    conexion = cursor = None
    try:
        if f["fecha_lim"] < f["fecha_gen"]:
            return "Error: la fecha límite no puede ser anterior a la de generación"
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE cuotas
            SET idpro=%s, fecha_gen=%s, fecha_lim=%s, monto=%s, estado=%s, activo=%s
            WHERE idcuo=%s
        """, (f["idpro"], f["fecha_gen"], f["fecha_lim"],
              float(f["monto"]), f["estado"], f["activo"], f["idcuo"]))
        conexion.commit()
        return "La cuota fue actualizada con éxito"
    except ValueError:
        if conexion: conexion.rollback()
        return "Error: el monto debe ser numérico"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al actualizar:", error)
        return f"Error al actualizar la cuota: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def eliminar_cuota():
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE cuotas SET activo = FALSE WHERE idcuo = %s",
                       (request.form["idcuo"],))
        conexion.commit()
        return "La cuota fue desactivada correctamente"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al desactivar:", error)
        return f"Error al desactivar: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)