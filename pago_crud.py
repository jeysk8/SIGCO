from flask import Blueprint, request, render_template, redirect, url_for, flash
from config import conectar, desconectar
from auth import login_requerido
import psycopg2

pago_crud_bp = Blueprint('pago_crud', __name__)


def _vacio_a_none(valor):
    valor = (valor or "").strip()
    return valor if valor else None


@pago_crud_bp.route("/consultar_pago", methods=["GET", "POST"])
def consultar_pago():
    if request.method == "POST":
        accion = request.form.get("accion")
        resultado = "Acción no válida"

        if accion == "registrar":
            resultado = registrar_pago()
        elif accion == "actualizar":
            resultado = actualizar_pago()
        elif accion == "eliminar":
            resultado = eliminar_pago()

        if not isinstance(resultado, str):
            return resultado

        flash(resultado)
        return redirect(url_for("pago_crud.consultar_pago"))

    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT pg.idpago,                                              -- 0
                   CONCAT('Cuota #', c.idcuo, ' - ',
                          CONCAT_WS(' ', p.tipo_vivienda, p.numvivienda)), -- 1
                   pg.idcuo1,                                              -- 2
                   pg.fecha_pago,                                          -- 3
                   pg.monto_pago,                                          -- 4
                   pg.metodo,                                              -- 5
                   pg.referencia,                                          -- 6
                   pg.comprobante_url,                                     -- 7
                   pg.estado_validacion,                                   -- 8
                   pg.observacion_admin,                                   -- 9
                   CONCAT_WS(' ', u.nombre, u.apellido),                   -- 10
                   pg.idusuario,                                           -- 11
                   pg.activo                                               -- 12
            FROM pago pg
            LEFT JOIN cuotas c    ON c.idcuo = pg.idcuo1
            LEFT JOIN propiedad p ON p.idpro = c.idpro
            LEFT JOIN usuario u   ON u.id = pg.idusuario
            ORDER BY pg.idpago DESC;
        """)
        pagos = cursor.fetchall()

        cursor.execute("""
            SELECT c.idcuo,
                   CONCAT('Cuota #', c.idcuo, ' - ',
                          CONCAT_WS(' ', p.tipo_vivienda, p.numvivienda),
                          ' ($', c.monto, ')')
            FROM cuotas c
            LEFT JOIN propiedad p ON p.idpro = c.idpro
            ORDER BY c.idcuo DESC
        """)
        cuotas = cursor.fetchall()

        cursor.execute("SELECT id, CONCAT_WS(' ', nombre, apellido) FROM usuario ORDER BY nombre")
        usuarios = cursor.fetchall()

        return render_template("CRUD/consultapagos.html",
                               pagos=pagos, cuotas=cuotas, usuarios=usuarios)
    except Exception as error:
        import traceback
        traceback.print_exc()
        return f"Error al obtener los pagos: {type(error).__name__}: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


def registrar_pago():
    """Los pagos creados aquí quedan 'pendiente': se validan en admin/pagos."""
    f = request.form
    conexion = cursor = None
    try:
        monto = float(f["monto_pago"])
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO pago
                (idcuo1, fecha_pago, monto_pago, metodo, referencia,
                 comprobante_url, estado_validacion, observacion_admin,
                 idusuario, activo)
            VALUES (%s, %s, %s, %s, %s, %s, 'pendiente', %s, %s, %s)
        """, (f["idcuo1"], f["fecha_pago"], monto, f["metodo"],
              _vacio_a_none(f.get("referencia")),
              _vacio_a_none(f.get("comprobante_url")),
              _vacio_a_none(f.get("observacion_admin")),
              f["idusuario"], f["activo"]))
        conexion.commit()
        return "El pago fue registrado como pendiente de validación"
    except ValueError:
        if conexion: conexion.rollback()
        return "Error: el monto debe ser numérico"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al registrar:", error)
        return f"Error al registrar el pago: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def actualizar_pago():
    """No toca estado_validacion, id_admin_valida, fecha_validacion ni comprobante_url."""
    f = request.form
    conexion = cursor = None
    try:
        monto = float(f["monto_pago"])
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE pago
            SET idcuo1=%s, fecha_pago=%s, monto_pago=%s, metodo=%s, referencia=%s,
                observacion_admin=%s, idusuario=%s, activo=%s
            WHERE idpago=%s
        """, (f["idcuo1"], f["fecha_pago"], monto, f["metodo"],
              _vacio_a_none(f.get("referencia")),
              _vacio_a_none(f.get("observacion_admin")),
              f["idusuario"], f["activo"], f["idpago"]))
        conexion.commit()
        return "El pago fue actualizado con éxito"
    except ValueError:
        if conexion: conexion.rollback()
        return "Error: el monto debe ser numérico"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al actualizar:", error)
        return f"Error al actualizar el pago: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)


@login_requerido(rol_requerido='admin')
def eliminar_pago():
    conexion = cursor = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE pago SET activo = FALSE WHERE idpago = %s",
                       (request.form["idpago"],))
        conexion.commit()
        return "El pago fue desactivado correctamente"
    except (Exception, psycopg2.Error) as error:
        if conexion: conexion.rollback()
        print("Error al desactivar:", error)
        return f"Error al desactivar: {error}"
    finally:
        if cursor: cursor.close()
        if conexion: desconectar(conexion)