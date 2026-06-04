"""Controlador de sesiones de entrenamiento: inicio, seguimiento en vivo, cierre.

TODO: implementar rutas delegando en sesion_servicio.
"""
from flask import Blueprint

bp_sesion = Blueprint("sesion", __name__, url_prefix="/sesion")

# TODO: GET  /sesion/
# TODO: POST /sesion/nueva
# TODO: GET  /sesion/<id>
# TODO: POST /sesion/<id>/cerrar
