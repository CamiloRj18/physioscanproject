"""Helpers para respuestas JSON uniformes de la API REST.

Estructura siempre: { "ok": bool, "datos": any | null, "error": str | null }
"""
from __future__ import annotations

from typing import Any

from flask import jsonify


def ok(datos: Any = None, estado: int = 200):
    """Respuesta de éxito con datos opcionales."""
    return jsonify({"ok": True, "datos": datos, "error": None}), estado


def creado(datos: Any = None):
    """Respuesta 201 Created."""
    return ok(datos, 201)


def error(mensaje: str, estado: int = 400, datos: Any = None):
    """Respuesta de error con mensaje y estado HTTP."""
    return jsonify({"ok": False, "datos": datos, "error": mensaje}), estado


def no_encontrado(mensaje: str = "Recurso no encontrado."):
    return error(mensaje, 404)


def no_autorizado(mensaje: str = "No autorizado."):
    return error(mensaje, 401)


def forbidden(mensaje: str = "Sin permiso."):
    return error(mensaje, 403)
