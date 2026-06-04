"""Controlador público: home, visión/misión/objetivos (§7 del blueprint)."""
from flask import Blueprint, render_template

bp_publico = Blueprint("publico", __name__)


@bp_publico.get("/")
def home():
    return render_template("publico/home.html")
