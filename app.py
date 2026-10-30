from flask import Flask, render_template, request, session, redirect, url_for
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "...")  # mejor sacarla a variable de entorno

from auth import auth_bp, roles_sesion
from pages import pages_bp
from menu import menu_bp
from admin import admin_bp
from conjunto import conjunto_bp
from cuotas import cuota_bp
from pagos import pago_bp
from propiedad import propiedad_bp
from rol import rol_bp
from usuario import usuario_bp
from usuario_rol import usuario_rol_bp
from visitante import visitante_bp
from servicios import servicios_bp
from comunidad import comunidad_bp
from manual import manual_bp
from rol import rol_bp
from reserva_servicio import reserva_bp
from propiedad import propiedad_bp
from comunicado import comunicados_bp
from certificados import certificados_bp
from pago_crud import pago_crud_bp



app.register_blueprint(auth_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(menu_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(conjunto_bp)
app.register_blueprint(cuota_bp)
app.register_blueprint(pago_bp)
app.register_blueprint(propiedad_bp)
app.register_blueprint(rol_bp)
app.register_blueprint(usuario_bp)
app.register_blueprint(usuario_rol_bp)
app.register_blueprint(visitante_bp)
app.register_blueprint(servicios_bp)
app.register_blueprint(comunidad_bp)
app.register_blueprint(manual_bp)
app.register_blueprint(reserva_bp)
app.register_blueprint(comunicados_bp)
app.register_blueprint(certificados_bp)
app.register_blueprint(pago_crud_bp)

@app.context_processor
def inyectar_sesion():
    return {
        'autenticado': 'id' in session,
        'nombre_usuario': session.get('nombre'),
        'es_admin': 'admin' in roles_sesion(),          # muestra el ícono de cambiar menú
        'vista_actual': session.get('vista', 'usuario'),  # 'admin' o 'usuario'
    }

@app.route('/')
def inicio():
    return redirect(url_for('auth.login'))

@app.route("/dbtest")
def dbtest():
    import psycopg2
    url = os.environ.get("DATABASE_URL")
    if not url:
        return "RESULTADO: DATABASE_URL NO llega a esta app"
    try:
        c = psycopg2.connect(url)
        cur = c.cursor()
        cur.execute("select current_database()")
        r = cur.fetchone()
        c.close()
        return f"RESULTADO: conexion OK a {r[0]}"
    except Exception as e:
        return f"RESULTADO: ERROR -> {e}"

if __name__ == '__main__':
    app.run(debug=True)
