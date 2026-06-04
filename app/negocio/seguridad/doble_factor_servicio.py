"""Servicio de doble factor: TOTP (pyotp/RFC 6238) + OTP por correo.

El secreto TOTP se guarda cifrado con Fernet; el texto plano solo vive en memoria.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import pyotp

from app.comun.errores import AutenticacionError, ValidacionError
from app.comun.seguridad_utils import (
    cifrar_secreto,
    descifrar_secreto,
    generar_token_url,
    sha256_hex,
)
from app.datos import seguridad_repositorio as sr
from app.negocio.seguridad.auditoria_servicio import registrar as audit


# ── TOTP ─────────────────────────────────────────────────────────────────────

def generar_secreto_totp(fernet_key: str) -> tuple[str, bytes]:
    """Genera un secreto TOTP aleatorio.

    Returns:
        (secreto_claro, secreto_cifrado) — cifrado para guardar en BD.
    """
    secreto_claro   = pyotp.random_base32()
    secreto_cifrado = cifrar_secreto(secreto_claro, fernet_key)
    return secreto_claro, secreto_cifrado


def uri_totp(email: str, secreto_claro: str) -> str:
    """otpauth:// URI para el QR de Google Authenticator / Authy."""
    totp = pyotp.TOTP(secreto_claro)
    return totp.provisioning_uri(name=email, issuer_name="PhysioScan")


def activar_totp(id_usuario: int, secreto_cifrado: bytes) -> None:
    """Persiste el secreto cifrado en usuario_2fa (aún no confirmado)."""
    sr.guardar_2fa(id_usuario, "totp", secreto_cifrado)


def confirmar_totp(
    id_usuario: int, codigo: str, fernet_key: str, ip: str | None = None
) -> None:
    """Verifica el primer código TOTP tras escanear el QR y activa el 2FA."""
    datos = sr.obtener_2fa(id_usuario)
    if not datos or not datos.get("secreto_totp"):
        raise ValidacionError("No hay un secreto TOTP pendiente de confirmación.")

    secreto_claro = descifrar_secreto(datos["secreto_totp"], fernet_key)
    totp = pyotp.TOTP(secreto_claro)

    if not totp.verify(codigo.strip(), valid_window=1):
        audit("2FA_CONFIRM_FAIL", id_usuario, ip)
        raise AutenticacionError("El código TOTP no es válido.")

    sr.habilitar_2fa(id_usuario)
    audit("2FA_ACTIVADO", id_usuario, ip)


def verificar_totp(
    id_usuario: int, codigo: str, fernet_key: str, ip: str | None = None
) -> bool:
    """Verifica código TOTP en el flujo de login.

    Returns True si válido; lanza AutenticacionError si no.
    Ventana de ±1 paso (30 s) para compensar desincronización de reloj.
    """
    datos = sr.obtener_2fa(id_usuario)
    if not datos or not datos.get("habilitado") or not datos.get("secreto_totp"):
        raise AutenticacionError("2FA no configurado para este usuario.")

    secreto_claro = descifrar_secreto(datos["secreto_totp"], fernet_key)
    totp = pyotp.TOTP(secreto_claro)

    if not totp.verify(codigo.strip(), valid_window=1):
        audit("2FA_FAIL", id_usuario, ip)
        raise AutenticacionError("El código de verificación no es válido.")

    audit("2FA_OK", id_usuario, ip)
    return True


# ── OTP por correo ────────────────────────────────────────────────────────────

def generar_otp_email(id_usuario: int, ip: str | None = None) -> str:
    """Genera un OTP de 6 dígitos para 2FA por correo.

    Invalida OTPs previos del mismo tipo y devuelve el código en claro
    para que el controlador lo envíe por correo.
    """
    sr.invalidar_tokens_usuario(id_usuario, "2fa_email")

    codigo     = "".join(str(secrets.randbelow(10)) for _ in range(6))
    token_hash = sha256_hex(codigo)
    expira_en  = datetime.utcnow() + timedelta(minutes=5)
    sr.crear_token(id_usuario, token_hash, "2fa_email", expira_en, ip)
    return codigo


def verificar_otp_email(
    id_usuario: int, codigo: str, ip: str | None = None
) -> bool:
    """Verifica el OTP enviado por correo. Lanza AutenticacionError si inválido."""
    token_hash = sha256_hex(codigo.strip())
    registro   = sr.buscar_token_valido(token_hash, "2fa_email")

    if not registro or registro["id_usuario"] != id_usuario:
        audit("2FA_FAIL", id_usuario, ip)
        raise AutenticacionError("El código no es válido o ha expirado.")

    sr.marcar_token_usado(registro["id_token"])
    audit("2FA_OK", id_usuario, ip)
    return True
