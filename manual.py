from flask import Blueprint, render_template, send_from_directory, current_app
import os

manual_bp = Blueprint('manual', __name__)

@manual_bp.route('/manual-convivencia')
def manual_convivencia():
    return render_template('manual_convivencia.html')

@manual_bp.route('/descargar-manual-pdf')
def descargar_manual():
    directorio = os.path.join(current_app.root_path,'static')
    nombre_archivo = "MANUAL DE CONVIVENCIA CONJUNTO RESIDENCIAL PUERTO GAITA.pdf"
    return send_from_directory(
        directory=directorio,
        path=nombre_archivo,
        as_attachment=True
    )