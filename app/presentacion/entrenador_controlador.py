"""Controlador de entrenador: deportistas asignados, historial y métricas."""
from __future__ import annotations

from flask import Blueprint, abort, render_template
from flask_login import current_user

from app.comun.decoradores import doble_factor_verificado, rol_requerido
from app.datos import alerta_repositorio as ar
from app.datos import deportista_repositorio as dr
from app.datos import sesion_repositorio as sr

bp_entrenador = Blueprint("entrenador", __name__, url_prefix="/entrenador")


# ── GET /entrenador/deportistas ──────────────────────────────────────────────

@bp_entrenador.get("/deportistas")
@rol_requerido("entrenador")
@doble_factor_verificado
def deportistas():
    asignaciones = dr.listar_asignaciones_entrenador(current_user.id_usuario)
    filas = []
    for asig in asignaciones:
        id_dep = asig["id_deportista"]
        sesion_activa = sr.sesion_en_curso(id_dep)
        severidad = None
        if sesion_activa:
            severidad = ar.severidad_actual(sesion_activa["id_sesion"])
        filas.append({**asig, "sesion_activa": sesion_activa, "severidad": severidad})
    return render_template("entrenador/deportistas.html", deportistas=filas)


# ── GET /entrenador/deportistas/<id> ─────────────────────────────────────────

@bp_entrenador.get("/deportistas/<int:id_deportista>")
@rol_requerido("entrenador")
@doble_factor_verificado
def deportista_detalle(id_deportista: int):
    asig = dr.buscar_asignacion(current_user.id_usuario, id_deportista)
    if not asig:
        abort(403)
    deportista = dr.buscar_por_id(id_deportista)
    if not deportista:
        abort(404)
    sesiones_lista = sr.listar_con_metricas(id_deportista)
    sesion_activa = sr.sesion_en_curso(id_deportista)
    severidad = None
    if sesion_activa:
        severidad = ar.severidad_actual(sesion_activa["id_sesion"])
    return render_template(
        "entrenador/deportista_detalle.html",
        deportista=deportista,
        sesiones=sesiones_lista,
        sesion_activa=sesion_activa,
        severidad=severidad,
    )
