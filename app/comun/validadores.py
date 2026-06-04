"""Validadores de formato. Validan FORMA, no semántica de negocio.

Devuelven bool (email, lat/lon, rango) o str | None (contraseña: mensaje de error o None).
"""
from __future__ import annotations

import re

from email_validator import EmailNotValidError, validate_email


def validar_email(email: str) -> bool:
    """True si el email tiene formato válido (sin verificar entregabilidad)."""
    try:
        validate_email(email.strip(), check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def validar_contrasena(password: str) -> str | None:
    """Valida la política de contraseña. Devuelve mensaje de error o None si es válida.

    Política:
    - Mínimo 12 caracteres.
    - Al menos 1 letra mayúscula.
    - Al menos 1 letra minúscula.
    - Al menos 1 dígito.
    """
    if len(password) < 12:
        return "La contraseña debe tener al menos 12 caracteres."
    if not re.search(r"[A-Z]", password):
        return "La contraseña debe contener al menos una letra mayúscula."
    if not re.search(r"[a-z]", password):
        return "La contraseña debe contener al menos una letra minúscula."
    if not re.search(r"\d", password):
        return "La contraseña debe contener al menos un dígito."
    return None


def validar_lat_lon(lat: float, lon: float) -> bool:
    """True si latitud está en [-90, 90] y longitud en [-180, 180]."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def validar_rango(valor: float, minimo: float, maximo: float) -> bool:
    """True si valor está en el rango [minimo, maximo] (extremos incluidos)."""
    return minimo <= valor <= maximo
