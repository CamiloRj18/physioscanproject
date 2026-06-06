"""Controlador de deportista: lista de sesiones, detalle y panel en vivo."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.comun.decoradores import doble_factor_verificado, rol_requerido
from app.datos import alerta_repositorio as ar
from app.datos import deportista_repositorio as dr
from app.datos import dispositivo_repositorio as disp_r
from app.datos import lectura_repositorio as lr
from app.datos import sesion_repositorio as sr
from app.negocio import metricas_servicio

bp_deportista = Blueprint("deportista", __name__, url_prefix="/deportista")


def _get_deportista_o_404():
    dep = dr.buscar_por_id_usuario(current_user.id_usuario)
    if not dep:
        abort(404)
    dep = dict(dep)
    for field in ("primer_nombre", "primer_apellido", "email", "codigo_usuario", "nombre_rol"):
        if field not in dep:
            dep[field] = getattr(current_user, field, None)
    return dep


# ── GET /deportista/sesiones ─────────────────────────────────────────────────

@bp_deportista.get("/sesiones")
@rol_requerido("deportista")
@doble_factor_verificado
def sesiones():
    dep = _get_deportista_o_404()
    sesiones_lista = sr.listar_con_metricas(dep["id_deportista"])
    return render_template(
        "deportista/sesiones.html",
        deportista=dep,
        sesiones=sesiones_lista,
    )


# ── GET/POST /deportista/sesiones/nueva ─────────────────────────────────────

@bp_deportista.route("/sesiones/nueva", methods=["GET", "POST"])
@rol_requerido("deportista")
@doble_factor_verificado
def nueva_sesion():
    dep = _get_deportista_o_404()
    dispositivo = disp_r.buscar_por_id_deportista(dep["id_deportista"])

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip() or None
        id_dispositivo = dispositivo["id_dispositivo"] if dispositivo else None
        nueva = sr.crear_sesion(dep["id_deportista"], id_dispositivo, titulo)
        flash("Sesión iniciada. ¡Comienza tu entrenamiento!", "success")
        return redirect(url_for("deportista.en_vivo", id_sesion=nueva["id_sesion"]))

    return render_template(
        "deportista/nueva_sesion.html",
        deportista=dep,
        dispositivo=dispositivo,
    )


# ── GET /deportista/sesiones/<id> ────────────────────────────────────────────

@bp_deportista.get("/sesiones/<int:id_sesion>")
@rol_requerido("deportista")
@doble_factor_verificado
def sesion_detalle(id_sesion: int):
    dep = _get_deportista_o_404()
    sesion = sr.buscar_por_id(id_sesion)
    if not sesion or sesion["id_deportista"] != dep["id_deportista"]:
        abort(403)
    metrica = sr.obtener_metrica(id_sesion) or {}
    alertas = ar.listar_por_sesion(id_sesion)
    return render_template(
        "deportista/sesion_detalle.html",
        deportista=dep,
        sesion=sesion,
        metrica=metrica,
        alertas=alertas,
    )


# ── GET /deportista/en-vivo/<id> ─────────────────────────────────────────────

@bp_deportista.get("/en-vivo/<int:id_sesion>")
@rol_requerido("deportista")
@doble_factor_verificado
def en_vivo(id_sesion: int):
    dep = _get_deportista_o_404()
    sesion = sr.buscar_por_id(id_sesion)
    if not sesion or sesion["id_deportista"] != dep["id_deportista"]:
        abort(403)
    if sesion["estado"] != "en_curso":
        abort(410)
    alertas = ar.listar_por_sesion(id_sesion)
    ultima_ecg = lr.ultima_lectura_ecg(id_sesion) or {}
    ultimo_bpm = ultima_ecg.get("bpm")
    return render_template(
        "deportista/en_vivo.html",
        deportista=dep,
        sesion=sesion,
        alertas=alertas,
        ultimo_bpm=ultimo_bpm,
    )


# ── POST /deportista/sesiones/<id>/finalizar ─────────────────────────────────

@bp_deportista.post("/sesiones/<int:id_sesion>/finalizar")
@rol_requerido("deportista")
@doble_factor_verificado
def finalizar_sesion(id_sesion: int):
    dep = _get_deportista_o_404()
    sesion = sr.buscar_por_id(id_sesion)
    if not sesion or sesion["id_deportista"] != dep["id_deportista"]:
        abort(403)
    if sesion["estado"] != "en_curso":
        flash("La sesión ya no está en curso.", "info")
    else:
        sr.finalizar_sesion(id_sesion)
        try:
            metricas_servicio.calcular_metricas(id_sesion)
        except Exception:
            pass
        flash("Sesión finalizada correctamente.", "success")
    next_url = request.form.get("next", "")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(url_for("deportista.sesiones"))
