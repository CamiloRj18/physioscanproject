"""Controlador API de ingesta: /api/v1 — recibe datos del chaleco ESP32.

TODO: implementar autenticación HMAC por dispositivo y delegar en ingesta_servicio.
"""
from flask import Blueprint

bp_api_ingesta = Blueprint("api_ingesta", __name__, url_prefix="/api/v1")

# TODO: POST /api/v1/sesiones/iniciar
# TODO: POST /api/v1/sesiones/<id>/lecturas
# TODO: POST /api/v1/sesiones/<id>/finalizar
# TODO: GET  /api/v1/sesiones/<id>/tiempo-real
