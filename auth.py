from flask import Blueprint, request, render_template, redirect, url_for, session, flash, abort
from werkzeug.security import check_password_hash
from functools import wraps
from config import conectar, desconectar

auth_bp = Blueprint('auth', __name__)


def ruta_segura(destino):
    """Devuelve `destino` solo si es una ruta interna del sitio ('/visitas').
    Rechaza direcciones externas ('http://...', '//otra.com') para que nadie
    pueda usar ?next= para sacar al usuario del portal."""
    if not destino or not destino.startswith('/'):
        return None
    if destino.startswith('//') or '\\' in destino:
        return None
    if destino.split('?')[0] in ('/login', '/logout'):
        return None
    return destino

def roles_sesion():
    """Lista de roles del usuario con sesión (['admin', 'residente'], etc.).
    Si la sesión es de antes de este cambio (solo tenía 'rol'), se usa ese."""
    roles = session.get('roles')
    if roles is None and session.get('rol'):
        roles = [session['rol']]
    return roles or []

def login_requerido(rol_requerido=None):
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'id' not in session:
                return redirect(url_for('auth.login'))
            if rol_requerido and rol_requerido not in roles_sesion():
                return "No autorizado", 403
            return f(*args, **kwargs)
        return wrapper
    return decorador

def requiere_sesion(pagina):
    """Para rutas que GUARDAN datos (POST).
    Si no hay sesión iniciada, no guarda nada: muestra el aviso
    "Debes iniciar sesión..." y devuelve al usuario a `pagina`
    (por ejemplo 'pages.servicios')."""
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'id' not in session:
                flash('Debes iniciar sesión para completar esta acción')
                return redirect(url_for(pagina))
            return f(*args, **kwargs)
        return wrapper
    return decorador


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    siguiente = ruta_segura(request.values.get('next'))

    if request.method == 'POST':
        documento = request.form.get('documento', '').strip()
        password = request.form.get('contrasena', '')

        if not documento.isdigit():
            flash('El documento debe contener solo números')
            return redirect(url_for('auth.login', next=siguiente))

        conn = conectar()
        if not conn:
            flash('No se pudo conectar a la base de datos')
            return redirect(url_for('auth.login', next=siguiente))

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.contrasena, r.tipo_rol, u.nombre
                FROM usuario u
                JOIN usuario_rol ur ON ur.idu = u.id
                JOIN rol r ON r.idrol = ur.idrol1
                WHERE u.documento = %s AND u.activo = TRUE AND ur.activo = TRUE
                ORDER BY r.idrol
            """, (documento,))
            filas = cursor.fetchall()
        finally:
            if cursor:
                cursor.close()
            desconectar(conn)

        if filas and check_password_hash(filas[0][1], password):
            roles = [f[2] for f in filas]
            session['id'] = filas[0][0]
            session['nombre'] = filas[0][3]
            session['roles'] = roles
            session.pop('rol', None)

            if 'admin' in roles:
                session.pop('vista', None)
                return redirect(url_for('pages.elegir_menu', next=siguiente))

            if 'vigilante' in roles:
                session['vista'] = 'vigilante'
                return redirect(url_for('pages.menu_vigilante'))

            session['vista'] = 'usuario'
            return redirect(url_for('pages.sigco'))

        flash('Usuario o contraseña incorrectos')
        return redirect(url_for('auth.login', next=siguiente))

    return render_template('login.html', siguiente=siguiente)

@auth_bp.route('/vista/<vista>')
def cambiar_vista(vista):
    """Cambia entre el menú de admin y el de usuario.
    Solo quien tiene el rol 'admin' en la base de datos puede pedir la vista admin."""
    if 'id' not in session:
        return redirect(url_for('auth.login'))
    if vista not in ('admin', 'usuario'):
        abort(404)
    if vista == 'admin' and 'admin' not in roles_sesion():
        return "No autorizado", 403

    session['vista'] = vista
    if vista == 'admin':
        return redirect(url_for('admin.administracion'))
    return redirect(ruta_segura(request.args.get('next')) or url_for('pages.menu_usuario'))



@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente')
    return redirect(url_for('auth.login'))