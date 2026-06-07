"""Decoradores de control de acceso.

@rol_requerido(*roles)      — RBAC: verifica que current_user tenga uno de los roles dados.
@doble_factor_verificado    — Exige que el 2FA esté confirmado en la sesión Flask.

Regla de capas: estos decoradores son Flask-aware (usan flask_login y flask.session),
pero no contienen lógica de negocio.
"""
from __future__ import annotations

from functools import wraps

from flask import abort, redirect, session, url_for
from flask_login import current_user, login_required


def rol_requerido(*roles: str):
    """Decorador de RBAC. Requiere que current_user.nombre_rol esté en `roles`.

    Ejemplo::

        @bp_admin.get("/panel")
        @rol_requerido("administrador")
        def panel():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            nombre_rol = getattr(current_user, "nombre_rol", None)
            if nombre_rol not in roles:
                abort(403)
            if session.get("debe_cambiar_password"):
                return redirect(url_for("usuario.cambiar_password_obligatorio"))
            return f(*args, **kwargs)
        return decorated
    return decorator


def doble_factor_verificado(f):
    """Exige que el segundo factor esté verificado en esta sesión.

    Si el usuario está autenticado pero no ha completado el 2FA,
    redirige a la vista de verificación.
    """
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not session.get("2fa_verificado"):
            return redirect(url_for("auth.verificar_2fa"))
        if session.get("debe_cambiar_password"):
            return redirect(url_for("usuario.cambiar_password_obligatorio"))
        return f(*args, **kwargs)
    return decorated
