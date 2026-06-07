"""Controlador de perfil de usuario.

Rutas:
    GET/POST /usuario/perfil   → ver y editar datos básicos + perfil deportivo
"""
from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.comun.decoradores import doble_factor_verificado
from app.comun.errores import ConflictoError, ValidacionError
from app.datos import deportista_repositorio as dr
from app.negocio import deportista_servicio as ds
from app.negocio.seguridad import recuperacion_archivo_servicio as ras
from app.negocio.seguridad.auditoria_servicio import registrar as audit

bp_usuario = Blueprint("usuario", __name__, url_prefix="/usuario")


@bp_usuario.route("/perfil", methods=["GET", "POST"])
@login_required
@doble_factor_verificado
def perfil():
    id_usuario  = int(current_user.get_id())
    deportista  = dr.buscar_por_id_usuario(id_usuario)

    if request.method == "POST":
        accion = request.form.get("accion", "")

        if accion == "basico":
            _actualizar_basico(id_usuario)
            return redirect(url_for("usuario.perfil"))

        if accion == "deportivo":
            if deportista:
                _actualizar_deportivo(id_usuario)
            else:
                _completar_perfil(id_usuario)
            # Reload para reflejar posible cambio de rol en la sesión
            return redirect(url_for("usuario.perfil"))

    # Refresca deportista tras posible cambio
    deportista = dr.buscar_por_id_usuario(id_usuario)
    return render_template("usuario/perfil.html", deportista=deportista)


@bp_usuario.post("/codigos/regenerar")
@login_required
@doble_factor_verificado
def codigos_regenerar():
    id_usuario = int(current_user.get_id())
    try:
        _, _, _, pdf_bytes = ras.generar_lote(id_usuario)
        audit("CODIGOS_DESCARGADOS", id_usuario, request.remote_addr)
        resp = make_response(pdf_bytes)
        resp.headers["Content-Type"] = "application/pdf"
        resp.headers["Content-Disposition"] = 'attachment; filename="codigos-physioscan.pdf"'
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception as exc:
        flash(f"No se pudo generar el PDF de códigos: {exc}", "error")
        return redirect(url_for("usuario.perfil"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _actualizar_basico(id_usuario: int) -> None:
    try:
        ds.actualizar_perfil_basico(
            id_usuario      = id_usuario,
            primer_nombre   = request.form.get("primer_nombre", "").strip(),
            segundo_nombre  = request.form.get("segundo_nombre", "").strip() or None,
            primer_apellido = request.form.get("primer_apellido", "").strip(),
            segundo_apellido= request.form.get("segundo_apellido", "").strip() or None,
            telefono        = request.form.get("telefono", "").strip() or None,
            ip              = request.remote_addr,
        )
        flash("Datos personales actualizados.", "success")
    except (ValidacionError, ConflictoError) as exc:
        flash(str(exc), "error")


def _completar_perfil(id_usuario: int) -> None:
    try:
        ds.completar_perfil(
            id_usuario       = id_usuario,
            fecha_nacimiento = request.form.get("fecha_nacimiento", "").strip() or None,
            sexo             = request.form.get("sexo", "").strip() or None,
            altura_cm        = _int_or_none("altura_cm"),
            peso_kg          = _float_or_none("peso_kg"),
            deporte          = request.form.get("deporte", "").strip() or None,
            categoria        = request.form.get("categoria", "").strip() or None,
            ip               = request.remote_addr,
        )
        flash("¡Perfil deportivo completado! Ya tienes acceso a tus sesiones.", "success")
    except (ValidacionError, ConflictoError) as exc:
        flash(str(exc), "error")


def _actualizar_deportivo(id_usuario: int) -> None:
    try:
        ds.actualizar_perfil_deportivo(
            id_usuario       = id_usuario,
            fecha_nacimiento = request.form.get("fecha_nacimiento", "").strip() or None,
            sexo             = request.form.get("sexo", "").strip() or None,
            altura_cm        = _int_or_none("altura_cm"),
            peso_kg          = _float_or_none("peso_kg"),
            deporte          = request.form.get("deporte", "").strip() or None,
            categoria        = request.form.get("categoria", "").strip() or None,
            fc_max_estimada  = _int_or_none("fc_max_estimada"),
            fc_reposo        = _int_or_none("fc_reposo"),
            ip               = request.remote_addr,
        )
        flash("Perfil deportivo actualizado.", "success")
    except (ValidacionError, ConflictoError) as exc:
        flash(str(exc), "error")


def _int_or_none(campo: str) -> int | None:
    val = request.form.get(campo, "").strip()
    try:
        return int(val) if val else None
    except ValueError:
        return None


def _float_or_none(campo: str) -> float | None:
    val = request.form.get(campo, "").strip()
    try:
        return float(val) if val else None
    except ValueError:
        return None
