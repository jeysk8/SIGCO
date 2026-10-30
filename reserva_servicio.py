from flask import Blueprint, request, render_template, redirect, url_for, flash
from config import conectar, desconectar
from auth import login_requerido
import psycopg2

reserva_bp = Blueprint('reserva', __name__)


@reserva_bp.route("/consultar_reserva", methods=["GET", "POST"])
def consultar_reserva():
    if request.method == "POST":
        accion = request.form.get("accion")
        resultado = "Acción no válida"

        if accion == "registrar":
            resultado = registrar_reserva()
        elif accion == "actualizar":
            resultado = actualizar_reserva()
        elif accion == "eliminar":
            resultado = eliminar_reserva()

        if not isinstance(resultado, str):
            return resultado

        flash(resultado)
        return redirect(url_for("reserva.consultar_reserva"))

    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT rs.idreserva,        -- 0
                   rs.tipo_servicio,    -- 1
                   rs.fecha,            -- 2
                   rs.hora,             -- 3
                   rs.cantidad_invitados, -- 4
                   rs.estado,           -- 5
                   CONCAT_WS(' ', u.nombre, u.apellido) AS usuario, -- 6
                   rs.idusu,            -- 7
                   rs.activo            -- 8
            FROM reserva_servicio rs
            LEFT JOIN usuario u ON u.id = rs.idusu
            ORDER BY rs.fecha DESC, rs.hora DESC;
        """)
        reservas = cursor.fetchall()

        cursor.execute("SELECT id, CONCAT_WS(' ', nombre, apellido) FROM usuario ORDER BY nombre")
        usuarios = cursor.fetchall()

        return render_template("CRUD/consultareserva.html",
                               reservas=reservas, usuarios=usuarios)
    except Exception as error:
        import traceback
        traceback.print_exc()
        return f"Error al obtener las reservas: {type(error).__name__}: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


def registrar_reserva():
    f = request.form
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO reserva_servicio
                (tipo_servicio, fecha, hora, cantidad_invitados, estado, idusu, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (f["tipo_servicio"], f["fecha"], f["hora"], f["cantidad_invitados"],
              f["estado"], f["idusu"], f["activo"]))
        conexion.commit()
        return "La reserva fue registrada con éxito"
    except psycopg2.errors.UniqueViolation:
        if conexion: conexion.rollback()
        return "Error: el salón ya está reservado en esa fecha y hora"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al registrar:", error)
        return f"Error al registrar la reserva: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def actualizar_reserva():
    f = request.form
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE reserva_servicio
            SET tipo_servicio=%s, fecha=%s, hora=%s, cantidad_invitados=%s,
                estado=%s, idusu=%s, activo=%s
            WHERE idreserva=%s
        """, (f["tipo_servicio"], f["fecha"], f["hora"], f["cantidad_invitados"],
              f["estado"], f["idusu"], f["activo"], f["idreserva"]))
        conexion.commit()
        return "La reserva fue actualizada con éxito"
    except psycopg2.errors.UniqueViolation:
        if conexion: conexion.rollback()
        return "Error: el salón ya está reservado en esa fecha y hora"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al actualizar:", error)
        return f"Error al actualizar la reserva: {error}"
    except psycopg2.errors.CheckViolation:
        if conexion: conexion.rollback()
        return "Error: la piscina permite máximo 5 invitados"
    except (Exception, psycopg2.Error) as error:
        ...
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def eliminar_reserva():
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE reserva_servicio SET activo = FALSE WHERE idreserva = %s",
                       (request.form["idreserva"],))
        conexion.commit()
        return "La reserva fue desactivada correctamente"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al desactivar:", error)
        return f"Error al desactivar: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)