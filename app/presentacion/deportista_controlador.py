"""Controlador de deportista: lista de sesiones, detalle y panel en vivo."""
from __future__ import annotations

from flask import Blueprint, abort, render_template
from flask_login import current_user

from app.comun.decoradores import doble_factor_verificado, rol_requerido
from app.datos import alerta_repositorio as ar
from app.datos import deportista_repositorio as dr
from app.datos import sesion_repositorio as sr

bp_deportista = Blueprint("deportista", __name__, url_prefix="/deportista")


def _get_deportista_o_404():
    dep = dr.buscar_por_id_usuario(current_user.id_usuario)
    if not dep:
        abort(404)
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
    return render_template(
        "deportista/en_vivo.html",
        deportista=dep,
        sesion=sesion,
    )
