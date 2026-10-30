from flask import Blueprint, request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from config import conectar, desconectar
from auth import login_requerido
import psycopg2

usuario_rol_bp = Blueprint('usuario_rol', __name__)


@usuario_rol_bp.route("/consultar_usuario_rol", methods=["GET", "POST"])
def consultar_usuario_rol():
    print(">>> ENTRÓ A consultar_usuario_rol")
    if request.method == "POST":
        accion = request.form.get("accion")
        resultado = "Acción no válida"

        if accion == "registrar":
            resultado = registrar_usuario_rol()
        elif accion == "actualizar":
            resultado = actualizar_usuario_rol()
        elif accion == "eliminar":
            resultado = eliminar_usuario_rol()

        if not isinstance(resultado, str):
            return resultado

        flash(resultado)
        return redirect(url_for("usuario_rol.consultar_usuario_rol"))


    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
                SELECT ur.idur,
                    CONCAT_WS(' ', u.nombre, u.apellido) AS usuario,
                    r.tipo_rol AS rol,
                    ur.idu,
                    ur.idrol1,
                    ur.activo
                FROM usuario_rol ur
                LEFT JOIN usuario u ON u.id = ur.idu
                LEFT JOIN rol r ON r.idrol = ur.idrol1
                ORDER BY ur.idur;
            """)
        usuario_rol = cursor.fetchall()

        cursor.execute("SELECT id, CONCAT_WS(' ', nombre, apellido) FROM usuario ORDER BY nombre")
        usuarios = cursor.fetchall()

        cursor.execute("SELECT idrol, tipo_rol FROM rol ORDER BY tipo_rol")
        roles = cursor.fetchall()

        cursor.execute("SELECT idu, idrol1 FROM usuario_rol")
        asignados = [[a, b] for a, b in cursor.fetchall()]

        return render_template("CRUD/consultausurol.html",
                            usuario_rol=usuario_rol, usuarios=usuarios,
                            roles=roles, asignados=asignados)

    except Exception as error:
        import traceback
        traceback.print_exc()
        return f"Error al obtener la lista de usuario_rol: {type(error).__name__}: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)




def registrar_usuario_rol():
    f = request.form
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO usuario_rol (idu, idrol1, activo)
            VALUES (%s, %s, %s)
        """, (f["idu"], f["idrol1"], f["activo"]))
        conexion.commit()
        return "El rol fue registrado con éxito al usuario"
    except psycopg2.errors.UniqueViolation:
        if conexion: conexion.rollback()
        return "Error: ese usuario ya tiene ese rol asignado"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al registrar:", error)
        return f"Error al registrar el rol al usuario: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)

@login_requerido(rol_requerido='admin')
def actualizar_usuario_rol():
    f = request.form
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE usuario_rol SET idu=%s, idrol1=%s, activo=%s
            WHERE idur=%s
        """, (f["idu"], f["idrol1"], f["activo"], f["idur"]))
        conexion.commit()
        return "El rol del usuario fue actualizado con éxito"
    except psycopg2.errors.UniqueViolation:
        if conexion: conexion.rollback()
        return "Error: ese usuario ya tiene ese rol asignado"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al actualizar:", error)
        return f"Error al actualizar el rol del usuario: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)

@login_requerido(rol_requerido='admin')
def eliminar_usuario_rol():
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE usuario_rol SET activo = FALSE WHERE idur = %s",
                       (request.form["idur"],))
        conexion.commit()
        return "El rol fue desactivado correctamente"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al desactivar:", error)
        return f"Error al desactivar: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)