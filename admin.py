from flask import Blueprint, render_template
from auth import login_requerido

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/menu_admin')
@login_requerido(rol_requerido='admin')
def administracion():
    return render_template('menu_admin.html')
