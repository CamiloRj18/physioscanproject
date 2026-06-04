"""Controlador de recuperación: reset por correo + por archivo de 12 códigos.

TODO: implementar rutas delegando en recuperacion_email_servicio y recuperacion_archivo_servicio.
"""
from flask import Blueprint

bp_recuperacion = Blueprint("recuperacion", __name__, url_prefix="/recuperacion")

# TODO: GET/POST /recuperacion/solicitar
# TODO: GET/POST /recuperacion/por-archivo
# TODO: GET/POST /recuperacion/nueva-contrasena/<token>
