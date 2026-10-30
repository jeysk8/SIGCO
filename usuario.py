from flask import Blueprint, request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from config import conectar, desconectar
from auth import login_requerido
import psycopg2

usuario_bp = Blueprint('usuario', __name__)


@usuario_bp.route("/consulta_usuario", methods=["GET", "POST"])
def consulta_usuario():
    print(">>> ENTRÓ A consulta_usuario")
    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "registrar":
            resultado = registrar_user()
        elif accion == "actualizar":
            resultado = actualizar_user()
        elif accion == "eliminar":
            resultado = eliminar_user()
        else:
            resultado = "Acción no válida"

        # Si el decorador devolvió una redirección (ej. sin permisos), se respeta
        if not isinstance(resultado, str):
            return resultado
        

        flash(resultado)
        return redirect(url_for("usuario.consulta_usuario"))  # evita reenviar el form al recargar

    # GET: listar

    # consulta de usuarios !!
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT u.id, u.nombre, u.apellido, u.fecha_nac, u.genero, u.tipo_documento,
                   u.documento, u.correo, u.contrasena, u.activo, u.idp,
                   CONCAT_WS(' ', p.tipo_vivienda, p.numvivienda) AS nombre_propiedad
            FROM usuario u
            LEFT JOIN propiedad p ON p.idpro = u.idp
            ORDER BY u.id;
        """)
        usuarios = cursor.fetchall()

        # consulta de propiedades lista desplegable
        cursor.execute("""
                SELECT idpro, numvivienda, tipo_vivienda
                FROM propiedad
                ORDER BY tipo_vivienda, numvivienda;
            """)
        propiedades = cursor.fetchall()

        print(">>> USUARIOS:", len(usuarios), "| PROPIEDADES:", len(propiedades))
        # Se mandan AMBAS listas !!!
        return render_template("CRUD/consultausu.html", datos=usuarios, propiedades=propiedades)
    except (Exception, psycopg2.Error) as error:
        print("Error en PostgreSQL:", error)
        return f"Error al obtener la lista de usuarios: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


# ---------- Funciones auxiliares: devuelven un mensaje (str) ----------

def registrar_user():
    f = request.form
    idp = f.get("idp") or None
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO usuario (nombre, apellido, fecha_nac, genero, tipo_documento,
                                 documento, correo, contrasena, activo, idp)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (f["nombre"], f["apellido"], f["fecha_nac"], f["genero"],
              f["tipo_documento"], f["documento"], f["correo"],
              generate_password_hash(f["contrasena"]), f["activo"], idp))
        conexion.commit()
        return "El usuario fue registrado con éxito"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al registrar:", error)
        return f"Error al registrar el usuario: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def actualizar_user():
    f = request.form
    idp = f.get("idp") or None
    nueva = f.get("contrasena", "").strip()
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        if nueva:
            cursor.execute("""
                UPDATE usuario SET nombre=%s, apellido=%s, fecha_nac=%s, genero=%s,
                tipo_documento=%s, documento=%s, correo=%s, contrasena=%s, activo=%s, idp=%s
                WHERE id=%s
            """, (f["nombre"], f["apellido"], f["fecha_nac"], f["genero"], f["tipo_documento"],
                  f["documento"], f["correo"], generate_password_hash(nueva),
                  f["activo"], idp, f["id"]))
        else:
            cursor.execute("""
                UPDATE usuario SET nombre=%s, apellido=%s, fecha_nac=%s, genero=%s,
                tipo_documento=%s, documento=%s, correo=%s, activo=%s, idp=%s
                WHERE id=%s
            """, (f["nombre"], f["apellido"], f["fecha_nac"], f["genero"], f["tipo_documento"],
                  f["documento"], f["correo"], f["activo"], idp, f["id"]))
        conexion.commit()
        return "El usuario fue actualizado con éxito"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al actualizar:", error)
        return f"Error al actualizar el usuario: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def eliminar_user():
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE usuario SET activo = FALSE WHERE id = %s", (request.form["id"],))
        conexion.commit()
        return "El usuario fue desactivado correctamente"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al desactivar:", error)
        return f"Error al desactivar el usuario: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)