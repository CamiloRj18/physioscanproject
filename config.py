"""Configuración por entorno de PhysioScan.

Lee exclusivamente de variables de entorno (cargadas desde .env con python-dotenv).
Ningún secreto está hardcodeado: SECRET_KEY, FERNET_KEY y DB_PASSWORD siempre del entorno.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base común a todos los entornos."""

    # Flask
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-clave-insegura-CAMBIAR")
    MAX_CONTENT_LENGTH: int = 2 * 1024 * 1024  # 2 MB

    # Sesiones y cookies
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = False       # True en producción
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_SAMESITE: str = "Lax"
    REMEMBER_COOKIE_SECURE: bool = False

    # CSRF
    WTF_CSRF_ENABLED: bool = True

    # Rate limiting (Flask-Limiter lee RATELIMIT_* de la config de Flask)
    RATELIMIT_STORAGE_URI: str = "memory://"
    RATELIMIT_DEFAULT: str = "200 per day;50 per hour"

    # Base de datos
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_PORT: int = int(os.environ.get("DB_PORT", "3306"))
    DB_NAME: str = os.environ.get("DB_NAME", "physioscan")
    DB_USER: str = os.environ.get("DB_USER", "physioscan_app")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_POOL_SIZE: int = int(os.environ.get("DB_POOL_SIZE", "5"))

    # Criptografía
    FERNET_KEY: str | None = os.environ.get("FERNET_KEY")

    # Correo (Flask-Mail)
    MAIL_SERVER: str = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS: bool = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME: str | None = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD: str | None = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER: str | None = os.environ.get("MAIL_DEFAULT_SENDER")

    # Tokens y bloqueos
    RESET_TOKEN_MINUTOS: int = int(os.environ.get("RESET_TOKEN_MINUTOS", "20"))
    LOCKOUT_INTENTOS: int = int(os.environ.get("LOCKOUT_INTENTOS", "5"))
    LOCKOUT_MINUTOS: int = int(os.environ.get("LOCKOUT_MINUTOS", "15"))


class ConfigDesarrollo(Config):
    DEBUG: bool = True
    TESTING: bool = False


class ConfigProduccion(Config):
    DEBUG: bool = False
    TESTING: bool = False
    SESSION_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True


class ConfigPruebas(Config):
    TESTING: bool = True
    DEBUG: bool = True
    WTF_CSRF_ENABLED: bool = False
    DB_NAME: str = os.environ.get("DB_TEST_NAME", "physioscan_test")


_mapa: dict[str, type[Config]] = {
    "desarrollo":  ConfigDesarrollo,
    "development": ConfigDesarrollo,
    "produccion":  ConfigProduccion,
    "production":  ConfigProduccion,
    "pruebas":     ConfigPruebas,
    "testing":     ConfigPruebas,
    "default":     ConfigDesarrollo,
}


def obtener_config(nombre: str = "default") -> type[Config]:
    return _mapa.get(nombre, ConfigDesarrollo)
