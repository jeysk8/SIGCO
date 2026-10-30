import os
import uuid
from datetime import datetime

import psycopg2
from flask import (Blueprint, request, render_template, redirect, url_for,
                   session, flash, abort, send_from_directory)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

from config import conectar, desconectar
from auth import login_requerido
from certificados import enviar_certificado_por_correo

pago_bp = Blueprint('pago', __name__)

# Carpeta FUERA de /static para que los comprobantes no sean públicos
CARPETA_COMPROBANTES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'uploads', 'comprobantes')
EXT_PERMITIDAS = {'pdf', 'jpg', 'jpeg', 'png'}

# En app.py agrega:  app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024


# ---------------------------------------------------------------- utilidades
def id_usuario_sesion():
    """Busca el id del usuario logueado probando los nombres de clave más comunes."""
    for clave in ('usuario_id', 'id_usuario', 'user_id', 'idu', 'id'):
        if session.get(clave) is not None:
            return session[clave]
    return None


def extension_valida(nombre):
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in EXT_PERMITIDAS


def saldo_cuota(cursor, idcuo):
    """Devuelve (monto, pagado, saldo) contando solo abonos APROBADOS."""
    cursor.execute("""
        SELECT c.monto,
               COALESCE(SUM(p.monto_pago) FILTER (
                   WHERE p.estado_validacion = 'aprobado' AND p.activo), 0)
        FROM cuotas c
        LEFT JOIN pago p ON p.idcuo1 = c.idcuo
        WHERE c.idcuo = %s
        GROUP BY c.idcuo
    """, (idcuo,))
    monto, pagado = cursor.fetchone()
    return monto, pagado, monto - pagado


# ------------------------------------------------------------ RESIDENTE
@pago_bp.route("/Proyecto_conjunto/pagos_usuario", methods=["GET", "POST"])
@login_requerido()
def pagos_usuario():
    idusuario = id_usuario_sesion()
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()

        if request.method == "POST":
            try:
                idcuo = int(request.form.get("idcuo", ""))
                monto = float(request.form.get("monto_pago", ""))
            except ValueError:
                flash("Datos inválidos.", "error")
                return redirect(url_for('pago.pagos_usuario'))

            metodo = request.form.get("tipo_pago") or 'general'
            archivo = request.files.get("comprobante")

            if not archivo or not archivo.filename or not extension_valida(archivo.filename):
                flash("Adjunta un comprobante PDF, JPG o PNG.", "error")
                return redirect(url_for('pago.pagos_usuario'))

            # Confirmación con contraseña
            password = request.form.get("password", "")
            cursor.execute("SELECT contrasena FROM usuario WHERE id = %s", (idusuario,))
            fila_pw = cursor.fetchone()
            if not password or not fila_pw or not check_password_hash(fila_pw[0], password):
                flash("Contraseña incorrecta. El pago no fue enviado.", "error")
                return redirect(url_for('pago.pagos_usuario'))

            # La cuota debe pertenecer al residente que está logueado
            cursor.execute("""
                SELECT c.idcuo
                FROM cuotas c
                JOIN usuario u ON u.idp = c.idpro
                WHERE c.idcuo = %s AND u.id = %s AND c.activo
            """, (idcuo, idusuario))
            if not cursor.fetchone():
                abort(403)

            _, _, saldo = saldo_cuota(cursor, idcuo)
            if monto <= 0 or monto > saldo + 0.009:
                flash(f"El abono debe ser mayor a 0 y no superar el saldo (${saldo:,.0f}).", "error")
                return redirect(url_for('pago.pagos_usuario'))

            os.makedirs(CARPETA_COMPROBANTES, exist_ok=True)
            ext = secure_filename(archivo.filename).rsplit('.', 1)[1].lower()
            nombre_archivo = f"{uuid.uuid4().hex}.{ext}"
            archivo.save(os.path.join(CARPETA_COMPROBANTES, nombre_archivo))

            cursor.execute("""
                INSERT INTO pago (idcuo1, fecha_pago, monto_pago, metodo,
                                  comprobante_url, estado_validacion, idusuario)
                VALUES (%s, NOW(), %s, %s, %s, 'pendiente', %s)
            """, (idcuo, monto, metodo, nombre_archivo, idusuario))
            conexion.commit()
            flash("Comprobante enviado. Quedó pendiente de revisión.", "ok")
            return redirect(url_for('pago.pagos_usuario'))

        # GET: cuotas que el residente aún puede abonar
        cursor.execute("""
            SELECT c.idcuo, c.fecha_lim, c.monto, c.estado
            FROM cuotas c
            JOIN usuario u ON u.idp = c.idpro
            WHERE u.id = %s AND c.activo AND COALESCE(c.estado,'') <> 'pagada'
            ORDER BY c.fecha_lim
        """, (idusuario,))
        cuotas = cursor.fetchall()

        if not cuotas:
            # --- DIAGNÓSTICO (puedes borrar este bloque cuando todo funcione) ---
            if idusuario is None:
                flash("DIAGNÓSTICO: la sesión no contiene el id del usuario. "
                      "Claves en sesión: " + ", ".join(session.keys()), "error")
            else:
                cursor.execute("SELECT idp FROM usuario WHERE id = %s", (idusuario,))
                fila_u = cursor.fetchone()
                if not fila_u:
                    flash(f"DIAGNÓSTICO: no existe un usuario con id {idusuario}.", "error")
                elif fila_u[0] is None:
                    flash("DIAGNÓSTICO: tu usuario no tiene vivienda asignada "
                          "(usuario.idp está vacío).", "error")
                else:
                    flash(f"DIAGNÓSTICO: tu vivienda es idpro {fila_u[0]} y no tiene cuotas "
                          "pendientes. El administrador debe generarlas.", "error")

        return render_template("pagos_usuario.html", cuotas=cuotas)
    except (Exception, psycopg2.Error) as error:
        if conexion:
            conexion.rollback()
        print("Error en pagos_usuario:", error)
        flash("Ocurrió un error al procesar el pago.", "error")
        return redirect(url_for('pago.pagos_usuario'))
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)


# ---------------------------------------------------------------- ADMIN
@pago_bp.route("/Proyecto_conjunto/admin/pagos", methods=["GET"])
@login_requerido(rol_requerido='admin')
def admin_pagos():
    filtro = request.args.get("residencia", "").strip()
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()

        consulta = """
            SELECT p.idpago, p.idcuo1, p.fecha_pago, p.monto_pago, p.metodo,
                   p.estado_validacion, p.comprobante_url,
                   pr.tipo_vivienda || ' ' || pr.numvivienda AS vivienda,
                   c.monto,
                   COALESCE(u.nombre || ' ' || u.apellido, 'Sin dato') AS residente,
                   u.documento
            FROM pago p
            JOIN cuotas c ON c.idcuo = p.idcuo1
            JOIN propiedad pr ON pr.idpro = c.idpro
            LEFT JOIN usuario u ON u.id = p.idusuario
            WHERE p.estado_validacion = 'pendiente' AND p.activo
        """
        params = []
        if filtro:
            consulta += """
                AND (u.documento::text ILIKE %s
                     OR pr.numvivienda ILIKE %s
                     OR pr.tipo_vivienda ILIKE %s
                     OR (u.nombre || ' ' || u.apellido) ILIKE %s
                     OR (pr.tipo_vivienda || ' ' || pr.numvivienda) ILIKE %s)
            """
            params.extend([f"%{filtro}%"] * 5)
        consulta += " ORDER BY p.fecha_pago"

        cursor.execute(consulta, params)
        pagos = cursor.fetchall()

        # Residentes que coinciden con la búsqueda (haya o no pagos pendientes)
        residentes = []
        if filtro:
            cursor.execute("""
                SELECT u.nombre || ' ' || u.apellido, u.documento,
                       COALESCE(pr.tipo_vivienda || ' ' || pr.numvivienda, 'Sin vivienda'),
                       (SELECT count(*) FROM cuotas c
                         WHERE c.idpro = u.idp AND c.activo
                           AND COALESCE(c.estado, '') <> 'pagada')
                FROM usuario u
                LEFT JOIN propiedad pr ON pr.idpro = u.idp
                WHERE u.documento::text ILIKE %s
                   OR (u.nombre || ' ' || u.apellido) ILIKE %s
                   OR pr.numvivienda ILIKE %s
                   OR pr.tipo_vivienda ILIKE %s
                   OR (pr.tipo_vivienda || ' ' || pr.numvivienda) ILIKE %s
                ORDER BY u.nombre
                LIMIT 20
            """, [f"%{filtro}%"] * 5)
            residentes = cursor.fetchall()

        return render_template("pago.html", pagos=pagos, filtro=filtro,
                               residentes=residentes)
    except (Exception, psycopg2.Error) as error:
        print("Error en admin_pagos:", error)
        return f"Error al cargar los pagos: {error}"
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)


@pago_bp.route("/Proyecto_conjunto/admin/pagos/<int:idpago>/validar", methods=["POST"])
@login_requerido(rol_requerido='admin')
def validar_pago(idpago):
    accion = request.form.get("accion")
    observacion = request.form.get("observacion", "").strip() or None
    if accion not in ('aprobar', 'rechazar'):
        abort(400)
    if accion == 'rechazar' and not observacion:
        flash("Indica el motivo del rechazo.", "error")
        return redirect(url_for('pago.admin_pagos'))

    conexion = cursor = None
    id_certificado = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()

        # Bloquea la fila para evitar doble validación
        cursor.execute("""
            SELECT p.idcuo1, p.monto_pago, p.idusuario
            FROM pago p
            WHERE p.idpago = %s AND p.estado_validacion = 'pendiente'
            FOR UPDATE
        """, (idpago,))
        fila = cursor.fetchone()
        if not fila:
            flash("Ese pago ya fue procesado.", "error")
            return redirect(url_for('pago.admin_pagos'))
        idcuo, monto_pago, idusuario = fila
        if idusuario is None:
            flash("Este pago no tiene un residente asociado (registro antiguo).", "error")
            return redirect(url_for('pago.admin_pagos'))

        nuevo_estado = 'aprobado' if accion == 'aprobar' else 'rechazado'
        cursor.execute("""
            UPDATE pago
            SET estado_validacion = %s, id_admin_valida = %s,
                fecha_validacion = NOW(), observacion_admin = %s
            WHERE idpago = %s
        """, (nuevo_estado, id_usuario_sesion(), observacion, idpago))

        if nuevo_estado == 'rechazado':
            mensaje = (f"Tu pago #{idpago} fue RECHAZADO. Motivo: {observacion}. "
                       f"Puedes subir un nuevo comprobante.")
        else:
            _, _, saldo = saldo_cuota(cursor, idcuo)
            if saldo <= 0.009:
                # La cuota quedó completa: se marca como pagada y se crea el
                # certificado en la tabla `certificados` (la que usa ese módulo)
                cursor.execute("UPDATE cuotas SET estado = 'pagada' WHERE idcuo = %s", (idcuo,))
                cursor.execute("""
                    INSERT INTO certificados (tipo_certificado, idu, id_pagos)
                    VALUES ('pagos', %s, %s)
                    RETURNING id_certificado
                """, (idusuario, idpago))
                id_certificado = cursor.fetchone()[0]
                mensaje = (f"Tu pago #{idpago} fue APROBADO y la cuota quedó al día. "
                           f"Tu certificado fue enviado a tu correo.")
            else:
                cursor.execute("UPDATE cuotas SET estado = 'parcial' WHERE idcuo = %s", (idcuo,))
                mensaje = (f"Tu abono #{idpago} por ${monto_pago:,.0f} fue APROBADO. "
                           f"Saldo pendiente: ${saldo:,.0f}.")

        # Si la notificación falla, no se pierde la validación ni el certificado
        cursor.execute("SAVEPOINT notificacion_pago")
        try:
            cursor.execute("""
                INSERT INTO notificacion (idusuario, idpago, mensaje)
                VALUES (%s, %s, %s)
            """, (idusuario, idpago, mensaje))
        except psycopg2.Error as e:
            print("No se pudo crear la notificación:", e)
            cursor.execute("ROLLBACK TO SAVEPOINT notificacion_pago")

        conexion.commit()
        flash("Pago procesado.", "ok")

    except (Exception, psycopg2.Error) as error:
        if conexion:
            conexion.rollback()
        print("Error en validar_pago:", error)
        flash("No se pudo procesar el pago.", "error")
        return redirect(url_for('pago.admin_pagos'))
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)

    # El correo se envía DESPUÉS del commit: si falla, la validación no se pierde
    if id_certificado:
        try:
            enviar_certificado_por_correo(id_certificado)
        except Exception as e:
            print("Error enviando certificado:", e)

    return redirect(url_for('pago.admin_pagos'))


@pago_bp.route("/Proyecto_conjunto/admin/cuotas/generar", methods=["POST"])
@login_requerido(rol_requerido='admin')
def generar_cuotas():
    """Crea la cuota del mes para todas las propiedades (sin duplicar)."""
    try:
        monto = float(request.form.get("monto", ""))
        primer_dia = datetime.strptime(request.form.get("mes", "") + "-01", "%Y-%m-%d").date()
        fecha_lim = datetime.strptime(request.form.get("fecha_lim", ""), "%Y-%m-%d").date()
    except ValueError:
        flash("Revisa el mes, el monto y la fecha límite.", "error")
        return redirect(url_for('pago.admin_pagos'))

    if monto <= 0 or fecha_lim < primer_dia:
        flash("El monto debe ser mayor a 0 y la fecha límite no puede ser anterior al mes.", "error")
        return redirect(url_for('pago.admin_pagos'))

    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO cuotas (idpro, fecha_gen, fecha_lim, monto, estado)
            SELECT pr.idpro, %s, %s, %s, 'pendiente'
            FROM propiedad pr
            WHERE pr.activo AND NOT EXISTS (
                SELECT 1 FROM cuotas c
                WHERE c.idpro = pr.idpro AND c.activo
                  AND date_trunc('month', c.fecha_gen) = date_trunc('month', %s::date)
            )
        """, (primer_dia, fecha_lim, monto, primer_dia))
        creadas = cursor.rowcount
        conexion.commit()
        if creadas > 0:
            flash(f"Se generaron {creadas} cuotas para {primer_dia:%m/%Y}.", "ok")
        else:
            cursor.execute("SELECT count(*) FROM propiedad WHERE activo")
            activas = cursor.fetchone()[0]
            if activas == 0:
                flash("No se generó nada: no hay propiedades activas en la tabla propiedad.", "error")
            else:
                flash(f"No se generó nada: las {activas} propiedades activas ya tienen "
                      f"cuota en {primer_dia:%m/%Y}.", "error")
    except (Exception, psycopg2.Error) as error:
        if conexion:
            conexion.rollback()
        print("Error en generar_cuotas:", error)
        flash("No se pudieron generar las cuotas.", "error")
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)
    return redirect(url_for('pago.admin_pagos'))


@pago_bp.route("/Proyecto_conjunto/admin/comprobante/<nombre>")
@login_requerido(rol_requerido='admin')
def ver_comprobante(nombre):
    return send_from_directory(CARPETA_COMPROBANTES, secure_filename(nombre))