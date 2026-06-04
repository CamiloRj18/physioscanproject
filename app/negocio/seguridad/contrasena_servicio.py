"""Servicio de contraseñas: hash Argon2id, verificación, política, historial."""
from __future__ import annotations

from app.comun.errores import ValidacionError
from app.comun.seguridad_utils import (
    hash_password,
    password_necesita_rehash,
    verificar_password,
)
from app.comun.validadores import validar_contrasena


def hash_nueva(password: str) -> str:
    return hash_password(password)


def verificar(password: str, hash_almacenado: str) -> bool:
    return verificar_password(password, hash_almacenado)


def necesita_rehash(hash_almacenado: str) -> bool:
    return password_necesita_rehash(hash_almacenado)


def validar_politica(password: str) -> None:
    """Lanza ValidacionError si la contraseña no cumple la política."""
    error = validar_contrasena(password)
    if error:
        raise ValidacionError(error)


def en_historial(password: str, historial: list[dict]) -> bool:
    """True si la contraseña coincide con alguna entrada del historial."""
    for entrada in historial:
        if verificar_password(password, entrada["hash_contrasena"]):
            return True
    return False
