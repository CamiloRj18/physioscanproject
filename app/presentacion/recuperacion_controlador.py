"""Controlador de recuperación: reset por correo + por archivo de 12 códigos.

TODO: implementar delegando en recuperacion_email_servicio y recuperacion_archivo_servicio.
"""
from flask import Blueprint, render_template

bp_recuperacion = Blueprint("recuperacion", __name__, url_prefix="/recuperacion")


@bp_recuperacion.get("/solicitar")
def solicitar():
    # TODO: implementar formulario de solicitud de reset por correo
    return render_template("recuperacion/solicitar.html")
