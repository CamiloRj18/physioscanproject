"""Application factory de PhysioScan.

Uso:
    flask --app app run          # desarrollo
    flask --app app crear-admin  # crear admin inicial
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask

# CSP estricta: sin unsafe-inline, sin unsafe-eval, sin CDN externo
_CSP: dict[str, str] = {
    "default-src":     "'self'",
    "script-src":      "'self'",
    "style-src":       "'self'",
    "img-src":         "'self' data:",
    "font-src":        "'self'",
    "object-src":      "'none'",
    "base-uri":        "'self'",
    "form-action":     "'self'",
    "frame-ancestors": "'none'",
}


def create_app(config_name: str | None = None) -> Flask:
    """Crea y configura la aplicación Flask.

    Args:
        config_name: 'desarrollo' | 'produccion' | 'pruebas' | None (lee FLASK_ENV).
    """
    load_dotenv()

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "desarrollo")

    app = Flask(__name__)

    from config import obtener_config
    app.config.from_object(obtener_config(config_name))

    _init_extensiones(app)
    _init_pool(app)
    _registrar_blueprints(app)

    from app.comun.errores import registrar_handlers
    registrar_handlers(app)

    @app.context_processor
    def _inject_globals():
        from datetime import datetime
        return {"now": datetime.utcnow()}

    from app.cli import registrar_comandos
    registrar_comandos(app)

    return app


# ── Internos ────────────────────────────────────────────────────────────────

def _init_extensiones(app: Flask) -> None:
    from app.extensions import login_manager, csrf, limiter, mail, talisman

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"
    login_manager.init_app(app)

    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    es_prod = not app.debug and not app.testing
    talisman.init_app(
        app,
        content_security_policy=_CSP,
        force_https=es_prod,
        force_https_permanent=False,
        strict_transport_security=es_prod,
        strict_transport_security_max_age=63072000,        # 2 años
        strict_transport_security_include_subdomains=True,
        frame_options="DENY",
        x_content_type_options=True,
        referrer_policy="strict-origin-when-cross-origin",
        session_cookie_secure=es_prod,
        session_cookie_samesite="Lax",
    )


def _init_pool(app: Flask) -> None:
    with app.app_context():
        try:
            from app.datos.conexion import init_pool
            init_pool()
        except Exception as exc:
            app.logger.warning(
                "Pool BD no disponible al arrancar (%s) — "
                "las rutas que accedan a BD fallarán hasta que MySQL esté activo.",
                exc,
            )


def _registrar_blueprints(app: Flask) -> None:
    from app.presentacion.publico_controlador      import bp_publico
    from app.presentacion.auth_controlador         import bp_auth
    from app.presentacion.recuperacion_controlador import bp_recuperacion
    from app.presentacion.deportista_controlador   import bp_deportista
    from app.presentacion.entrenador_controlador   import bp_entrenador
    from app.presentacion.admin_controlador        import bp_admin
    from app.presentacion.sesion_controlador       import bp_sesion
    from app.presentacion.api_ingesta_controlador  import bp_api_ingesta
    from app.extensions import csrf

    app.register_blueprint(bp_publico)
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_recuperacion)
    app.register_blueprint(bp_deportista)
    app.register_blueprint(bp_entrenador)
    app.register_blueprint(bp_admin)
    app.register_blueprint(bp_sesion)
    app.register_blueprint(bp_api_ingesta)

    csrf.exempt(bp_api_ingesta)
