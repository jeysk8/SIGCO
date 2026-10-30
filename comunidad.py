import os
import uuid
from datetime import datetime

import psycopg2
from flask import Blueprint, request, session, redirect, url_for, render_template, current_app

from auth import login_requerido
from config import conectar, desconectar

comunidad_bp = Blueprint('comunidad', __name__)

MAX_CARACTERES = 1000
MAX_BYTES_IMAGEN = 3 * 1024 * 1024  # 3 MB
POR_PAGINA = 12
CARPETA_SUBIDAS = os.path.join('static', 'uploads', 'comunidad')

_MESES = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')


def _extension_imagen(cabecera):
    if cabecera.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if cabecera.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if cabecera[:4] == b'RIFF' and cabecera[8:12] == b'WEBP':
        return 'webp'
    if cabecera[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    return None


def _borrar_imagen(nombre):
    if not nombre:
        return
    try:
        os.remove(os.path.join(current_app.root_path, CARPETA_SUBIDAS, nombre))
    except OSError:
        pass


def _formatear_fecha(fecha):
    """Equivale al formatearFecha() que antes hacía comunidad.js: 'Hoy, 3:45 p. m.'"""
    hora = f"{fecha.hour % 12 or 12}:{fecha.minute:02d} {'a. m.' if fecha.hour < 12 else 'p. m.'}"
    dias = (datetime.now().date() - fecha.date()).days
    if dias == 0:
        return f'Hoy, {hora}'
    if dias == 1:
        return f'Ayer, {hora}'
    return f'{fecha.day} {_MESES[fecha.month - 1]} {fecha.year}, {hora}'


def _cargar_publicaciones(antes_de):
    """Devuelve (publicaciones, hay_mas, error). Paginación por id: trae las anteriores a 'antes_de'."""
    conn = conectar()
    if not conn:
        return [], False, 'No se pudo conectar a la base de datos.'

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.idpub, p.contenido, p.imagen, p.fecha_pub, u.nombre, u.apellido
            FROM comunidad_publicacion p
            JOIN usuario u ON u.id = p.idu
            WHERE p.activo = true
              AND (%s::integer IS NULL OR p.idpub < %s::integer)
            ORDER BY p.idpub DESC
            LIMIT %s
        """, (antes_de, antes_de, POR_PAGINA + 1))
        filas = cursor.fetchall()
    except (Exception, psycopg2.Error) as error:
        print('Error al listar publicaciones:', error)
        return [], False, 'No se pudieron cargar las publicaciones.'
    finally:
        if cursor:
            cursor.close()
        desconectar(conn)

    hay_mas = len(filas) > POR_PAGINA
    publicaciones = []
    for f in filas[:POR_PAGINA]:
        autor = f'{f[4] or ""} {f[5] or ""}'.strip() or 'Residente'
        publicaciones.append({
            'id': f[0],
            'contenido': f[1],
            'imagen': f[2],
            'fecha_iso': f[3].isoformat(),
            'fecha': _formatear_fecha(f[3]),
            'autor': autor,
            'inicial': autor[0].upper(),
        })
    return publicaciones, hay_mas, None


def vista_comunidad(error=None, contenido='', texto_invalido=False):
    """Arma y devuelve la página Comunidad (la usa pages.py para GET /comunidad).

    Si 'error' viene con texto, se muestra en el formulario y se conserva lo que el
    residente había escrito ('contenido') para que no tenga que volver a escribirlo.
    """
    autenticado = 'id' in session
    mensaje_ok = session.pop('com_mensaje', None)  

    antes_de = request.args.get('antes_de', type=int)
    publicaciones, hay_mas, error_carga = [], False, None
    if autenticado:
        publicaciones, hay_mas, error_carga = _cargar_publicaciones(antes_de)

    if error:
        mensaje, mensaje_tipo = error, 'error'
    elif mensaje_ok:
        mensaje, mensaje_tipo = mensaje_ok, 'ok'
    else:
        mensaje, mensaje_tipo = None, None

    return render_template(
        'comunidad.html',
        autenticado=autenticado,
        publicaciones=publicaciones,
        hay_mas=hay_mas,
        ultimo_id=publicaciones[-1]['id'] if publicaciones else None,
        antes_de=antes_de,
        error_carga=error_carga,
        mensaje=mensaje,
        mensaje_tipo=mensaje_tipo,
        contenido=contenido,
        texto_invalido=texto_invalido,
        max_caracteres=MAX_CARACTERES,
    )


@comunidad_bp.route('/comunidad/publicar', methods=['GET', 'POST'])
@login_requerido()
def publicar():
    if request.method == 'GET':
        return redirect(url_for('pages.comunidad'))
    contenido = (request.form.get('contenido') or '').replace('\r\n', '\n').strip()
    if not contenido:
        return vista_comunidad(error='Escribe algo antes de publicar.',
                               contenido=contenido, texto_invalido=True), 400
    if len(contenido) > MAX_CARACTERES:
        return vista_comunidad(error=f'La publicación no puede superar {MAX_CARACTERES} caracteres.',
                               contenido=contenido, texto_invalido=True), 400

    nombre_imagen = None
    archivo = request.files.get('imagen')
    if archivo and archivo.filename:
        datos = archivo.read(MAX_BYTES_IMAGEN + 1)
        if len(datos) > MAX_BYTES_IMAGEN:
            return vista_comunidad(error='La imagen no puede superar 3 MB. Vuelve a elegir una foto más liviana.',
                                   contenido=contenido), 400
        extension = _extension_imagen(datos[:16])
        if not extension:
            return vista_comunidad(error='La imagen debe ser JPG, PNG, WEBP o GIF. Vuelve a elegir la foto.',
                                   contenido=contenido), 400

        carpeta = os.path.join(current_app.root_path, CARPETA_SUBIDAS)
        os.makedirs(carpeta, exist_ok=True)
        nombre_imagen = f'{uuid.uuid4().hex}.{extension}'
        with open(os.path.join(carpeta, nombre_imagen), 'wb') as destino:
            destino.write(datos)

    conn = conectar()
    if not conn:
        _borrar_imagen(nombre_imagen)  
        return vista_comunidad(error='No se pudo conectar a la base de datos. Inténtalo de nuevo.',
                               contenido=contenido), 500

    cursor = None
    error_guardado = False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comunidad_publicacion (idu, contenido, imagen)
            VALUES (%s, %s, %s)
        """, (session['id'], contenido, nombre_imagen))
        conn.commit()
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print('Error al guardar la publicación:', error)
        error_guardado = True
    finally:
        if cursor:
            cursor.close()
        desconectar(conn)

    if error_guardado:
        _borrar_imagen(nombre_imagen)  
        return vista_comunidad(error='No se pudo guardar la publicación. Inténtalo de nuevo.',
                               contenido=contenido), 500

    session['com_mensaje'] = 'Tu publicación se compartió con la comunidad.'
    return redirect(url_for('pages.comunidad'))