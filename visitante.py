from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from config import conectar, desconectar
from auth import login_requerido, requiere_sesion
import psycopg2

visitante_bp = Blueprint('visitante', __name__)

TABLA = "visitante"
@visitante_bp.route("/visitas", methods=["POST"])
@requiere_sesion("pages.visitas")
def guardar_visit():
    nombre = request.form["nombre"].strip()
    apellido = request.form["apellido"].strip()
    fecha_nac = request.form["fecha_nac"]
    genero = request.form["genero"]
    tipodoc = request.form["tipodoc"]
    documento = request.form["documento"]
    tipo_vehiculo = request.form.get("tipo_vehiculo") or None
    placa = request.form.get("placa", "").strip().upper() or None
    idusu = session.get("id")

    if tipo_vehiculo in (None, "ninguno"):
        placa = None

    conexion = None
    cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO visitante
                (nombre, apellido, fecha_nac, genero, activo,
                 placa, tipodoc, documento, idusu, tipo_vehiculo)
            VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s, %s, %s)
            """,
            (nombre, apellido, fecha_nac, genero,
             placa, tipodoc, documento, idusu, tipo_vehiculo),
        )
        conexion.commit()
        flash("Visitante registrado exitosamente")
    except (Exception, psycopg2.Error) as error:
        print("Error al guardar el visitante:", error)
        flash("No se pudo registrar el visitante")
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)

    return redirect(url_for("pages.visitas"))

@visitante_bp.route("/Proyecto_conjunto/registrar_visit", methods=["GET", "POST"])
def registrar_visit():
    if request.method == "POST":
        idvisi = request.form["idvisi"]
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        fecha_nac = request.form["fecha_nac"]
        genero = request.form["genero"]
        activo = request.form["activo"]
        placa = request.form["placa"]
        tipodoc = request.form["tipodoc"]
        documento = request.form["documento"]
        idusu = request.form["idusu"]

        conexion = None
        cursor = None
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            consulta = f"""
            INSERT INTO {TABLA} (idvisi, nombre, apellido, fecha_nac, genero, activo, placa, tipodoc, documento, idusu)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            datos = (idvisi, nombre, apellido, fecha_nac, genero, activo, placa, tipodoc, documento, idusu)
            cursor.execute(consulta, datos)
            conexion.commit()
            return "El visitante fue registrado con exito"
        except (Exception, psycopg2.Error) as error:
            print("Error al registrar el visitante:", error)
            return "Error al registrar el visitante"
        finally:
            if cursor:
                cursor.close()
            if conexion:
                desconectar(conexion)
    else:
        return render_template("registrar.html")


def _datos_visitante_form():
    """Lee y limpia los campos que comparten los formularios de registrar y actualizar.
    Orden: nombre, apellido, fecha_nac, genero, tipodoc, documento,
           placa, tipo_vehiculo, idusu, activo"""
    tipo_vehiculo = request.form.get("tipo_vehiculo") or None
    placa = request.form.get("placa", "").strip().upper() or None
    if tipo_vehiculo is None:
        placa = None          # sin vehículo no puede haber placa
    return (
        request.form["nombre"].strip(),
        request.form["apellido"].strip(),
        request.form["fecha_nac"],
        request.form["genero"],
        request.form["tipodoc"],
        request.form["documento"],
        placa,
        tipo_vehiculo,
        request.form["idusu"],
        request.form.get("activo") == "true",
    )


@visitante_bp.route("/Proyecto_conjunto/consultar_visit", methods=["GET", "POST"])
@login_requerido(rol_requerido='admin')
def consulta_visit():
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()

        # ---------- POST: registrar / actualizar / desactivar ----------
        if request.method == "POST":
            accion = request.form.get("accion")
            try:
                if accion == "registrar":
                    cursor.execute("""
                        INSERT INTO visitante
                            (nombre, apellido, fecha_nac, genero, tipodoc, documento,
                             placa, tipo_vehiculo, idusu, activo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, _datos_visitante_form())
                    flash("Visitante registrado exitosamente")

                elif accion == "actualizar":
                    cursor.execute("""
                        UPDATE visitante
                        SET nombre = %s, apellido = %s, fecha_nac = %s, genero = %s,
                            tipodoc = %s, documento = %s, placa = %s,
                            tipo_vehiculo = %s, idusu = %s, activo = %s
                        WHERE idvisi = %s
                    """, _datos_visitante_form() + (request.form["idvisi"],))
                    flash("Visitante actualizado correctamente")

                elif accion == "eliminar":
                    cursor.execute(
                        "UPDATE visitante SET activo = FALSE WHERE idvisi = %s",
                        (request.form["idvisi"],))
                    flash("Visitante desactivado")

                else:
                    flash("Error: acción no válida")

                conexion.commit()
            except (KeyError, psycopg2.Error) as error:
                conexion.rollback()
                print("Error en consulta_visit:", error)
                flash("Error: no se pudo guardar el cambio")

            return redirect(url_for("visitante.consulta_visit"))

        # ---------- GET: lista ----------
        # Orden de columnas (lo que esperan las plantillas):
        # 0 idvisi, 1 nombre, 2 apellido, 3 fecha_nac, 4 genero, 5 tipodoc,
        # 6 documento, 7 placa, 8 tipo_vehiculo, 9 nombre del residente,
        # 10 idusu, 11 activo
        cursor.execute("""
            SELECT v.idvisi, v.nombre, v.apellido, v.fecha_nac, v.genero,
                   v.tipodoc, v.documento, v.placa, v.tipo_vehiculo,
                   COALESCE(u.nombre || ' ' || u.apellido, 'Sin residente'),
                   v.idusu, v.activo
            FROM visitante v
            LEFT JOIN usuario u ON u.id = v.idusu
            ORDER BY v.idvisi
        """)
        visitantes = cursor.fetchall()

        # Residentes para los desplegables de los modales
        cursor.execute("""
            SELECT id, nombre || ' ' || apellido
            FROM usuario
            WHERE activo = TRUE
            ORDER BY nombre
        """)
        usuarios = cursor.fetchall()

        return render_template("CRUD/consultavisitante.html",
                               visitantes=visitantes, usuarios=usuarios)

    except (Exception, psycopg2.Error) as error:
        print("Detalle del error en PostgreSQL:", error)
        return f"Error al obtener la lista de visitantes: {error}"
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)

@visitante_bp.route("/Proyecto_conjunto/actualizar_visit", methods=["POST"])
@login_requerido(rol_requerido='admin')
def actualizar_visit():
    idvisi = request.form["idvisi"]
    nombre = request.form["nombre"]
    apellido = request.form["apellido"]
    fecha_nac = request.form["fecha_nac"]
    genero = request.form["genero"]
    activo = request.form["activo"]
    placa = request.form["placa"]
    tipodoc = request.form["tipodoc"]
    documento = request.form["documento"]
    idusu = request.form["idusu"]

    conexion = None
    cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        consulta = f"""
        UPDATE {TABLA} SET
        nombre = %s, apellido = %s, fecha_nac = %s, genero = %s, activo = %s,
        placa = %s, tipodoc = %s, documento = %s, idusu = %s
        WHERE idvisi = %s;
        """
        datos = (nombre, apellido, fecha_nac, genero, activo, placa, tipodoc, documento, idusu, idvisi)
        cursor.execute(consulta, datos)
        conexion.commit()
        return "El visitante fue actualizado con exito"
    except (Exception, psycopg2.Error) as error:
        print("Error al actualizar:", error)
        return f"Error al actualizar el visitante: {error}"
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)


@visitante_bp.route("/Proyecto_4/eliminar_visit", methods=["GET", "POST"])
@login_requerido(rol_requerido='admin')
def eliminar_visit():
    if request.method == "POST":
        doc = request.form["idvisi"]
        conexion = None
        cursor = None
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            consulta = f"DELETE FROM {TABLA} WHERE idvisi = %s"
            cursor.execute(consulta, (doc,))
            conexion.commit()
            return "El visitante fue eliminado correctamente"
        except (Exception, psycopg2.Error) as error:
            print("Error al eliminar el visitante:", error)
            return f"Error al eliminar el visitante: {error}"
        finally:
            if cursor:
                cursor.close()
            if conexion:
                desconectar(conexion)
    else:
        return render_template("eliminar.html")


@visitante_bp.route("/vigilante/visitantes")
@login_requerido()
def vigilante_visitantes():
    from auth import roles_sesion

    roles = roles_sesion()

    if "vigilante" not in roles and "admin" not in roles:
        return "No autorizado", 403

    conexion = None
    cursor = None

    try:
        conexion = conectar()

        if conexion is None:
            return "No se pudo conectar a la base de datos", 500

        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                v.idvisi,
                v.nombre,
                v.apellido,
                v.fecha_nac,
                v.genero,
                v.tipodoc,
                v.documento,
                v.placa,
                v.tipo_vehiculo,
                v.idusu,
                COALESCE(u.nombre || ' ' || u.apellido, 'Sin residente'),
                v.activo
            FROM visitante v
            LEFT JOIN usuario u ON u.id = v.idusu
            WHERE v.activo = TRUE
            ORDER BY v.idvisi DESC
        """)

        visitantes = cursor.fetchall()

        return render_template(
            "CRUD/vigilante_visitantes.html",
            visitantes=visitantes
        )

    except Exception as error:
        print("Error al consultar visitantes:", error)
        return "No se pudieron consultar los visitantes", 500

    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)