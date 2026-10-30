from flask import Blueprint, render_template, request, redirect, url_for, flash

comunicados_bp = Blueprint('comunicados', __name__)

# Lista en memoria para simular los comunicados (puedes reemplazar esto con tu modelo de Base de Datos)
lista_comunicados = []

# Ruta para que los residentes vean los comunicados activos
@comunicados_bp.route('/comunicados')
def listar_comunicados():
    # Enviamos la lista de comunicados a la plantilla HTML
    return render_template('comunicados.html', comunicados=lista_comunicados)

# Ruta para que el administrador publique un comunicado
@comunicados_bp.route('/admin/comunicados', methods=['GET', 'POST'])
def admin_comunicados():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        tipo = request.form.get('tipo', 'Aviso General') # Ej: Urgente, Mantenimiento, Plan Candado
        fecha = request.form.get('fecha', 'Reciente')
        icono = request.form.get('icono', 'fas fa-bullhorn')

        # Creamos el diccionario del nuevo comunicado y lo guardamos
        nuevo_aviso = {
            'titulo': titulo,
            'descripcion': descripcion,
            'tipo': tipo,
            'fecha': fecha,
            'icono': icono
        }
        
        lista_comunicados.insert(0, nuevo_aviso) # Lo agregamos al inicio para que sea el más reciente
        flash('¡Comunicado publicado con éxito!', 'success')
        return redirect(url_for('comunicados.admin_comunicados'))
        
    return render_template('admin_comunicados.html', comunicados=lista_comunicados)