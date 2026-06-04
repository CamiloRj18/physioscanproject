"""Instancias de extensiones Flask.

Se crean aquí sin init_app; la inicialización ocurre en create_app() de app/__init__.py.
También define UsuarioProxy (adapta el DTO Usuario a flask-login) y el user_loader.
"""
from __future__ import annotations

from flask_login import LoginManager, UserMixin
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_talisman import Talisman

login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()
talisman = Talisman()


class UsuarioProxy(UserMixin):
    """Adapta el DTO Usuario a la interfaz de flask-login.

    Mantiene app/modelos/usuario.py libre de dependencias de Flask.
    Los campos extra del JOIN (p. ej. nombre_rol) se exponen a través de _extra.
    """

    def __init__(self, fila: dict) -> None:
        from app.modelos.usuario import Usuario
        campos    = set(Usuario.__dataclass_fields__)
        self._u   = Usuario(**{k: v for k, v in fila.items() if k in campos})
        self._extra: dict = {k: v for k, v in fila.items() if k not in campos}

    def get_id(self) -> str:
        return str(self._u.id_usuario)

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self._u.estado == "activo"

    def __getattr__(self, name: str):
        extra = self.__dict__.get("_extra", {})
        if name in extra:
            return extra[name]
        u = self.__dict__.get("_u")
        if u is not None:
            return getattr(u, name)
        raise AttributeError(name)


@login_manager.user_loader
def _cargar_usuario(id_str: str):
    """Recarga el usuario (con nombre_rol) desde BD en cada petición autenticada."""
    try:
        from app.datos.base_repositorio import uno
        fila = uno(
            """
            SELECT u.*, r.nombre AS nombre_rol
            FROM   usuario u
            JOIN   rol r ON r.id_rol = u.id_rol
            WHERE  u.id_usuario = %s
            """,
            (int(id_str),),
        )
        return UsuarioProxy(fila) if fila else None
    except Exception:
        return None
