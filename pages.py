# pages.py
import os
from flask import (
    Blueprint, 
    render_template,
    redirect, 
    url_for, 
    request, 
    session, 
    send_from_directory, 
    current_app
)

from auth import login_requerido, ruta_segura
from comunidad import vista_comunidad

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/sigco')
def sigco():
    return render_template('index.html')

@pages_bp.route('/acerca')
def acerca():
    return render_template('acerca.html')

@pages_bp.route('/contact')
def contact():
    return render_template('contact.html')

@pages_bp.route('/comunidad')
def comunidad():
    return vista_comunidad()   # CAMBIADO

@pages_bp.route('/visitas')
def visitas():
    return render_template('visitas.html')

@pages_bp.route('/menu_usuario')
def menu_usuario():
    return render_template('menu_usuario.html')

@pages_bp.route('/elegir_menu')
@login_requerido('admin')
def elegir_menu():
    # Página que ven los admins justo después de iniciar sesión
    return render_template('elegir_menu.html', siguiente=ruta_segura(request.args.get('next')))


@pages_bp.route('/pagos')
def pagos():
    return render_template("pagos.html")

@pages_bp.route('/certificados')
def certificados():
   return render_template("certificados.html")

@pages_bp.route('/solicitudes')
def solicitudes():
   return render_template("solicitudes.html")

@pages_bp.route('/comunicados')
def comunicados():
   return render_template("comunicados.html")

@pages_bp.route('/servicios')
def servicios():
   return render_template("servicios.html")

@pages_bp.route('/manual_convivencia')
def manual_convivencia():
   return render_template("manual_convivencia.html")

@pages_bp.route("/-manual_convivencia/descargar")
def descargar_manual_convivencia():
    directorio_pdf = os.path.join(
        current_app.root_path,
        "static",
        "stile",
    )

    nombre_archivo = (
        "MANUAL DE CONVIVENCIA CONJUNTO RESIDENCIAL PUERTO GAITA.pdf"
    )

    return send_from_directory(
        directorio_pdf,
        nombre_archivo,
        as_attachment=True,
    )

@pages_bp.route('/crud_elegir')
def crud_elegir():
    return render_template("crud_elegir.html")

@pages_bp.route("/pagos_usuario")
def pagos_usuario():
    return redirect(url_for('pago.pagos_usuario'))

@pages_bp.route("/menu_vigilante")
@login_requerido()
def menu_vigilante():
    from auth import roles_sesion

    roles = roles_sesion()

    if "vigilante" not in roles and "admin" not in roles:
        return "No autorizado", 403

    return render_template("menu_vigilante.html")