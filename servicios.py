from flask import Blueprint, request, redirect, url_for, session, flash
from config import conectar, desconectar
import psycopg2
import psycopg2.errors
from auth import requiere_sesion

servicios_bp = Blueprint('servicio', __name__)

@servicios_bp.route("/servicios", methods=["POST"])
@requiere_sesion("pages.servicios")
def guardar_servicio():
    # 1) Leer lo que el usuario escribió en el formulario
    tipo_servicio = request.form["tipo_servicio"]
    fecha = request.form["fecha"]
    hora = request.form["hora"]
    idusu = session.get("id")  # vacío si nadie inició sesión

    try:
        cantidad_invitados = int(request.form["cantidad_invitados"])
    except ValueError:
        flash("La cantidad de invitados no es válida")
        return redirect(url_for("pages.servicios"))

    # 2) Validaciones del lado del servidor (el JavaScript se puede saltar)
    if cantidad_invitados < 0:
        flash("La cantidad de invitados no es válida")
        return redirect(url_for("pages.servicios"))

    if tipo_servicio == "piscinas" and cantidad_invitados > 5:
        flash("La piscina permite máximo 5 invitados")
        return redirect(url_for("pages.servicios"))

    # 3) Guardar en la base de datos
    conexion = None
    cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO reserva_servicio
                (tipo_servicio, fecha, hora, cantidad_invitados, idusu)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (tipo_servicio, fecha, hora, cantidad_invitados, idusu),
        )
        conexion.commit()
        flash("Reserva registrada exitosamente")

    except psycopg2.errors.UniqueViolation:
        # El salón de eventos ya está reservado a esa fecha y hora
        if conexion:
            conexion.rollback()
        flash("Ese servicio ya está reservado a esa fecha y hora")

    except (Exception, psycopg2.Error) as error:
        if conexion:
            conexion.rollback()
        print("Error al guardar la reserva:", error)
        flash("No se pudo registrar la reserva")

    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)

    # 4) Volver a la página del formulario
    return redirect(url_for("pages.servicios"))