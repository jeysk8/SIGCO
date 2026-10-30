import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from flask import Blueprint, request, render_template, session, flash, abort
import psycopg2
from config import conectar, desconectar
from auth import requiere_sesion, login_requerido, roles_sesion

certificados_bp = Blueprint('certificado', __name__)

TIPOS_CERTIFICADO = ("pagos",)
MAX_DOCUMENTO = 2147483647


def formulario(mensaje, tipo_certificado, fecha, numero_identificacion):
    flash(mensaje)
    return render_template(
        "certificados.html",
        tipo_certificado=tipo_certificado,
        fecha=fecha,
        numero_identificacion=numero_identificacion,
    )


@certificados_bp.route("/certificados", methods=["POST"])
@requiere_sesion("pages.certificados")
def buscar_certificados():
    tipo_certificado = request.form.get("tipo_certificado", "").strip()
    fecha = request.form.get("fecha", "").strip()
    numero_identificacion = request.form.get("numero_identificacion", "").strip()
    datos = (tipo_certificado, fecha, numero_identificacion)

    if tipo_certificado not in TIPOS_CERTIFICADO:
        return formulario("Selecciona un tipo de certificado válido", *datos)

    try:
        fecha_consulta = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        return formulario("La fecha del certificado no es válida", *datos)

    if (not numero_identificacion.isascii()
            or not numero_identificacion.isdigit()
            or int(numero_identificacion) > MAX_DOCUMENTO):
        return formulario("El número de identificación no es válido", *datos)

    documento = int(numero_identificacion)

    conexion = None
    cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()

        if "admin" not in roles_sesion():
            cursor.execute("SELECT documento FROM usuario WHERE id = %s", (session.get("id"),))
            fila = cursor.fetchone()
            if fila is None or fila[0] != documento:
                return formulario(
                    "Solo puedes consultar los certificados de tu propio número de identificación",
                    *datos,
                )

        cursor.execute(
            """
            SELECT c.id_certificado, c.tipo_certificado, c.fecha_certificado,
                   c.hora_certificado, u.documento
            FROM certificados c
            JOIN usuario u ON u.id = c.idu
            WHERE c.tipo_certificado = %s
              AND c.fecha_certificado = %s
              AND u.documento = %s
            ORDER BY c.hora_certificado, c.id_certificado
            """,
            (tipo_certificado, fecha_consulta, documento),
        )
        columnas = [columna[0] for columna in cursor.description]
        certificados = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    except (Exception, psycopg2.Error) as error:
        print("Error al consultar los certificados:", error)
        return formulario("No se pudieron consultar los certificados", *datos)
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)

    return render_template(
        "certificados_resultados.html",
        certificados=certificados,
        tipo_certificado=tipo_certificado,
        fecha=fecha_consulta,
        numero_identificacion=documento,
    )


CONSULTA_CERTIFICADO = """
    SELECT c.id_certificado, c.tipo_certificado, c.fecha_certificado,
           c.hora_certificado, c.idu,
           u.nombre, u.apellido, u.tipo_documento, u.documento, u.correo,
           pr.tipo_vivienda, pr.numvivienda,
           p.idpago, p.fecha_pago, p.monto_pago, p.metodo, p.codigo_certificado
    FROM certificados c
    JOIN usuario u ON u.id = c.idu
    LEFT JOIN pago p ON p.idpago = c.id_pagos
    LEFT JOIN cuotas cu ON cu.idcuo = p.idcuo1
    LEFT JOIN propiedad pr ON pr.idpro = cu.idpro
    WHERE c.id_certificado = %s
"""


def obtener_certificado(cursor, id_certificado):
    cursor.execute(CONSULTA_CERTIFICADO, (id_certificado,))
    fila = cursor.fetchone()
    if fila is None:
        return None
    columnas = [columna[0] for columna in cursor.description]
    return dict(zip(columnas, fila))


def texto_certificado(c):
    lineas = [
        f"Certificado de {c['tipo_certificado']} N.º {c['id_certificado']}",
        "",
        f"Residente: {c['nombre']} {c['apellido']}",
        f"Documento: {c['tipo_documento']} {c['documento']}",
    ]
    if c["numvivienda"]:
        lineas.append(f"Vivienda: {c['tipo_vivienda']} {c['numvivienda']}")
    if c["idpago"]:
        lineas.append(f"Pago: N.º {c['idpago']}")
        if c["fecha_pago"]:
            lineas.append(f"Fecha del pago: {c['fecha_pago'].strftime('%d/%m/%Y')}")
        if c["monto_pago"] is not None:
            lineas.append(f"Monto: {c['monto_pago']:,.2f}")
        if c["metodo"]:
            lineas.append(f"Método: {c['metodo']}")
    if c["codigo_certificado"]:
        lineas.append(f"Código de certificación: {c['codigo_certificado']}")
    lineas.append(
        f"Generado el {c['fecha_certificado'].strftime('%d/%m/%Y')} a las {c['hora_certificado'].strftime('%H:%M:%S')}"
    )
    return "\n".join(lineas)


def enviar_certificado_por_correo(id_certificado):
    servidor = "smtp-mail.outlook.com"
    puerto = 587
    usuario_smtp = "rawmusic2025@outlook.com"
    clave_smtp = "osmupnevlccazvuo"
    remitente = usuario_smtp

    if not usuario_smtp or not clave_smtp:
        print("Correo no enviado: faltan las variables SMTP_USER y SMTP_PASSWORD")
        return False

    conexion = None
    cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        certificado = obtener_certificado(cursor, id_certificado)
    except (Exception, psycopg2.Error) as error:
        print("Error al preparar el correo del certificado:", error)
        return False
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)

    if certificado is None or not certificado["correo"]:
        print("Correo no enviado: el certificado no existe o el usuario no tiene correo")
        return False

    mensaje = EmailMessage()
    mensaje["Subject"] = f"SIGCO - Certificado de {certificado['tipo_certificado']} N.º {certificado['id_certificado']}"
    mensaje["From"] = f"SIGCO <{remitente}>"
    mensaje["To"] = certificado["correo"]
    mensaje.set_content(
        f"Hola {certificado['nombre']},\n\n"
        "Tu pago fue aprobado y se generó tu certificado.\n\n"
        f"{texto_certificado(certificado)}\n\n"
        "También puedes consultarlo en la sección Certificados de SIGCO.\n"
    )

    
    for modo, p in (("ssl", 465), ("tls", 587)):
        try:
            if modo == "ssl":
                smtp = smtplib.SMTP_SSL(servidor, p, timeout=20)
            else:
                smtp = smtplib.SMTP(servidor, p, timeout=20)
                smtp.starttls()
            with smtp:
                smtp.login(usuario_smtp, clave_smtp)
                smtp.send_message(mensaje)
            print(f"Correo enviado por el puerto {p}")
            return True
        except Exception as error:
            print(f"Falló el envío por el puerto {p}: {error!r}")
    return False


@certificados_bp.route("/certificados/<int:id_certificado>")
@login_requerido()
def ver_certificado(id_certificado):
    conexion = None
    cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        certificado = obtener_certificado(cursor, id_certificado)
        if certificado is None:
            abort(404)
    except psycopg2.Error as error:
        print("Error al obtener el certificado:", error)
        return "No se pudo obtener el certificado", 500
    finally:
        if cursor:
            cursor.close()
        if conexion:
            desconectar(conexion)

    if certificado["idu"] != session.get("id") and "admin" not in roles_sesion():
        return "No autorizado", 403

    return render_template("certificado_ver.html", c=certificado)
