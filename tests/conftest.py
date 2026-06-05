"""Fixtures compartidas: clave Fernet, secreto TOTP, usuario de prueba."""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet


@pytest.fixture(scope="session")
def fernet_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture(scope="session")
def totp_secreto() -> str:
    import pyotp
    return pyotp.random_base32()


@pytest.fixture
def usuario_activo() -> dict:
    return {
        "id_usuario": 1,
        "primer_nombre": "Ana",
        "email": "ana@ejemplo.com",
        "email_verificado": True,
        "estado": "activo",
        "nombre_rol": "deportista",
        "bloqueado_hasta": None,
        "intentos_fallidos": 0,
        "codigo_usuario": "ANA0001",
    }
