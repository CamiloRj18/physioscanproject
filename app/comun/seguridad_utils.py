"""Utilidades criptográficas transversales.

Reglas:
- hash_password / hash_codigo usan Argon2id (argon2-cffi).
- Los secretos TOTP se cifran con Fernet (cryptography).
- SHA-256 solo para tokens efímeros de un solo uso (no contraseñas).
- comparacion_segura usa hmac.compare_digest para tiempo constante.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

# Hasher compartido con parámetros por defecto (Argon2id, time_cost=3, mem=64 MB)
_ph = PasswordHasher()


# ── Contraseñas ─────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Devuelve el hash Argon2id de la contraseña."""
    return _ph.hash(password)


def verificar_password(password: str, hash_almacenado: str) -> bool:
    """Verifica contraseña contra su hash Argon2id. Devuelve False si no coincide."""
    try:
        return _ph.verify(hash_almacenado, password)
    except (VerifyMismatchError, VerificationError):
        return False


def password_necesita_rehash(hash_almacenado: str) -> bool:
    """True si el hash fue generado con parámetros anteriores y conviene actualizarlo."""
    return _ph.check_needs_rehash(hash_almacenado)


# ── Códigos de recuperación ──────────────────────────────────────────────────

def hash_codigo(codigo: str) -> str:
    """Hash Argon2id de un código de recuperación (mismo algoritmo que contraseñas)."""
    return _ph.hash(codigo)


def verificar_codigo(codigo: str, hash_almacenado: str) -> bool:
    """Verifica un código de recuperación contra su hash Argon2id."""
    try:
        return _ph.verify(hash_almacenado, codigo)
    except (VerifyMismatchError, VerificationError):
        return False


# ── Tokens efímeros ──────────────────────────────────────────────────────────

def generar_token_url(nbytes: int = 32) -> str:
    """Token URL-safe de alta entropía para correos de restablecimiento.

    Solo el hash SHA-256 se persiste en BD; el token en claro viaja en el correo.
    """
    return secrets.token_urlsafe(nbytes)


def sha256_hex(token: str) -> str:
    """Digest SHA-256 en hexadecimal de un token en claro."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ── Cifrado simétrico (secreto TOTP) ────────────────────────────────────────

def cifrar_secreto(dato: str, fernet_key: str) -> bytes:
    """Cifra dato con Fernet. Devuelve bytes para almacenar en VARBINARY."""
    f = Fernet(_normalizar_key(fernet_key))
    return f.encrypt(dato.encode("utf-8"))


def descifrar_secreto(token: bytes, fernet_key: str) -> str:
    """Descifra token Fernet. Lanza ValueError si la clave es incorrecta o el token está corrupto."""
    try:
        f = Fernet(_normalizar_key(fernet_key))
        return f.decrypt(token).decode("utf-8")
    except (InvalidToken, Exception) as exc:
        raise ValueError("No se pudo descifrar el secreto TOTP.") from exc


def _normalizar_key(key: str | bytes) -> bytes:
    return key.encode("utf-8") if isinstance(key, str) else key


# ── Comparación en tiempo constante ─────────────────────────────────────────

def comparacion_segura(a: str, b: str) -> bool:
    """Compara dos strings en tiempo constante para evitar ataques de temporización."""
    return hmac.compare_digest(
        a.encode("utf-8") if isinstance(a, str) else a,
        b.encode("utf-8") if isinstance(b, str) else b,
    )
