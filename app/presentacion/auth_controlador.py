"""Controlador de autenticación: login, registro, logout, verificar-2fa.

TODO: implementar rutas delegando en auth_servicio y doble_factor_servicio.
"""
from flask import Blueprint

bp_auth = Blueprint("auth", __name__, url_prefix="/auth")

# TODO: GET/POST /auth/login
# TODO: GET/POST /auth/registro
# TODO: POST     /auth/logout
# TODO: GET/POST /auth/verificar-2fa
