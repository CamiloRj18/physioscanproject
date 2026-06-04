"""Controlador de administración: gestión de usuarios, reemisión del archivo de recuperación.

TODO: implementar rutas protegidas con @rol_requerido("administrador").
"""
from flask import Blueprint

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")

# TODO: GET  /admin/usuarios
# TODO: POST /admin/usuarios/<id>/reemitir-archivo
# TODO: GET  /admin/auditoria
