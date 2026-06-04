"""Controlador público: home, visión/misión/objetivos.

TODO: implementar templates Jinja2 (§7 del blueprint).
"""
from flask import Blueprint, render_template

bp_publico = Blueprint("publico", __name__)


@bp_publico.get("/")
def home():
    # TODO: render_template("publico/home.html")
    return (
        "<!doctype html><html><head><title>PhysioScan</title></head>"
        "<body><h1>PhysioScan</h1><p>Servidor activo. "
        "Próximamente la home con el holograma 3D.</p></body></html>"
    )
