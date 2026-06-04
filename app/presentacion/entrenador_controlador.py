"""Controlador de entrenador: lista y métricas de deportistas asignados.

TODO: implementar rutas protegidas con @rol_requerido("entrenador").
"""
from flask import Blueprint

bp_entrenador = Blueprint("entrenador", __name__, url_prefix="/entrenador")

# TODO: GET /entrenador/deportistas
# TODO: GET /entrenador/deportistas/<id>
