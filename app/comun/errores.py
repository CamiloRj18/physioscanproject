"""Excepciones de dominio y manejadores de error HTTP.

Los handlers devuelven JSON para rutas /api/* y HTML genérico para el resto.
NUNCA exponen stack traces: los registran en app.logger pero no en la respuesta.
"""
from __future__ import annotations

from flask import Flask, jsonify, request


# ── Excepciones de dominio ───────────────────────────────────────────────────

class ErrorDominio(Exception):
    """Raíz de todas las excepciones de negocio de PhysioScan."""


class AutenticacionError(ErrorDominio):
    """Credenciales inválidas o cuenta no verificada."""


class AutorizacionError(ErrorDominio):
    """El usuario no tiene permisos para esta acción."""


class RecursoNoEncontradoError(ErrorDominio):
    """El recurso solicitado no existe."""


class ValidacionError(ErrorDominio):
    """Error de validación semántica de datos de entrada."""


class ConflictoError(ErrorDominio):
    """Conflicto de estado (p.ej. email ya registrado)."""


class BloqueadoError(ErrorDominio):
    """Cuenta bloqueada temporalmente por intentos fallidos."""


# ── Registro de handlers HTTP ────────────────────────────────────────────────

def registrar_handlers(app: Flask) -> None:
    """Registra los manejadores de error 400/403/404/429/500 en la app."""

    @app.errorhandler(400)
    def bad_request(e):
        app.logger.debug("400 Bad Request: %s", e)
        return _respuesta_error(400, "Solicitud incorrecta.")

    @app.errorhandler(403)
    def forbidden(e):
        app.logger.info("403 Forbidden: %s | %s", request.path, e)
        return _respuesta_error(403, "No tienes permiso para esta acción.")

    @app.errorhandler(404)
    def not_found(e):
        return _respuesta_error(404, "El recurso solicitado no existe.")

    @app.errorhandler(429)
    def too_many_requests(e):
        app.logger.warning("429 Rate limit: %s | %s", request.remote_addr, request.path)
        return _respuesta_error(429, "Demasiadas solicitudes. Intenta más tarde.")

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("500 Internal Server Error: %s", e)
        return _respuesta_error(500, "Error interno del servidor.")

    @app.errorhandler(ErrorDominio)
    def dominio_error(e: ErrorDominio):
        # Mapeo de excepción → código HTTP
        codigos = {
            AutenticacionError:       401,
            AutorizacionError:        403,
            RecursoNoEncontradoError: 404,
            ValidacionError:          422,
            ConflictoError:           409,
            BloqueadoError:           403,
        }
        status = codigos.get(type(e), 400)
        return _respuesta_error(status, str(e))


def _respuesta_error(status: int, mensaje: str):
    """Devuelve JSON para rutas /api/*, HTML genérico para el resto."""
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "datos": None, "error": mensaje}), status
    # Para vistas HTML: respuesta mínima sin stack trace
    html = (
        f"<!doctype html><html><head><title>{status}</title></head>"
        f"<body><h1>{status}</h1><p>{mensaje}</p></body></html>"
    )
    return html, status
