"""Controlador de deportista: dashboard propio, sesiones y métricas.

TODO: implementar rutas protegidas con @rol_requerido("deportista").
"""
from flask import Blueprint

bp_deportista = Blueprint("deportista", __name__, url_prefix="/deportista")

# TODO: GET /deportista/dashboard
# TODO: GET /deportista/sesiones
# TODO: GET /deportista/sesiones/<id>
