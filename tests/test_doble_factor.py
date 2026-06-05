"""Tests: TOTP válido/inválido, sin 2FA, confirmación, OTP email."""
from __future__ import annotations

from unittest.mock import patch

import pyotp
import pytest

from app.comun.errores import AutenticacionError, ValidacionError
from app.comun.seguridad_utils import cifrar_secreto
from app.negocio.seguridad import doble_factor_servicio as svc


def _datos_2fa(secreto_claro: str, fernet_key: str, *, habilitado: bool = True) -> dict:
    return {
        "habilitado": habilitado,
        "secreto_totp": cifrar_secreto(secreto_claro, fernet_key),
    }


# ── TOTP ──────────────────────────────────────────────────────────────────────

@patch("app.negocio.seguridad.doble_factor_servicio.audit")
@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_verificar_totp_valido(mock_sr, mock_audit, fernet_key, totp_secreto):
    codigo = pyotp.TOTP(totp_secreto).now()
    mock_sr.obtener_2fa.return_value = _datos_2fa(totp_secreto, fernet_key)

    resultado = svc.verificar_totp(1, codigo, fernet_key)

    assert resultado is True
    mock_audit.assert_called_once_with("2FA_OK", 1, None)


@patch("app.negocio.seguridad.doble_factor_servicio.audit")
@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_verificar_totp_invalido(mock_sr, mock_audit, fernet_key, totp_secreto):
    mock_sr.obtener_2fa.return_value = _datos_2fa(totp_secreto, fernet_key)

    with pytest.raises(AutenticacionError, match="válido"):
        svc.verificar_totp(1, "000000", fernet_key)

    mock_audit.assert_called_once_with("2FA_FAIL", 1, None)


@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_verificar_totp_sin_2fa(mock_sr):
    mock_sr.obtener_2fa.return_value = None

    with pytest.raises(AutenticacionError, match="no configurado"):
        svc.verificar_totp(1, "123456", "unused_key")


@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_verificar_totp_no_habilitado(mock_sr, fernet_key, totp_secreto):
    mock_sr.obtener_2fa.return_value = _datos_2fa(totp_secreto, fernet_key, habilitado=False)

    with pytest.raises(AutenticacionError, match="no configurado"):
        svc.verificar_totp(1, "123456", fernet_key)


@patch("app.negocio.seguridad.doble_factor_servicio.audit")
@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_confirmar_totp_ok(mock_sr, mock_audit, fernet_key, totp_secreto):
    codigo = pyotp.TOTP(totp_secreto).now()
    mock_sr.obtener_2fa.return_value = {"secreto_totp": cifrar_secreto(totp_secreto, fernet_key)}

    svc.confirmar_totp(1, codigo, fernet_key)

    mock_sr.habilitar_2fa.assert_called_once_with(1)
    mock_audit.assert_called_once_with("2FA_ACTIVADO", 1, None)


@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_confirmar_totp_sin_secreto_pendiente(mock_sr):
    mock_sr.obtener_2fa.return_value = None

    with pytest.raises(ValidacionError, match="pendiente"):
        svc.confirmar_totp(1, "123456", "unused")


# ── OTP email ─────────────────────────────────────────────────────────────────

@patch("app.negocio.seguridad.doble_factor_servicio.audit")
@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_verificar_otp_email_valido(mock_sr, mock_audit):
    mock_sr.buscar_token_valido.return_value = {"id_token": 5, "id_usuario": 1}

    resultado = svc.verificar_otp_email(1, "847291")

    assert resultado is True
    mock_sr.marcar_token_usado.assert_called_once_with(5)
    mock_audit.assert_called_once_with("2FA_OK", 1, None)


@patch("app.negocio.seguridad.doble_factor_servicio.audit")
@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_verificar_otp_email_invalido(mock_sr, mock_audit):
    mock_sr.buscar_token_valido.return_value = None

    with pytest.raises(AutenticacionError, match="expirado"):
        svc.verificar_otp_email(1, "000000")

    mock_audit.assert_called_once_with("2FA_FAIL", 1, None)


@patch("app.negocio.seguridad.doble_factor_servicio.audit")
@patch("app.negocio.seguridad.doble_factor_servicio.sr")
def test_verificar_otp_email_usuario_distinto(mock_sr, mock_audit):
    """Token existe pero pertenece a otro usuario."""
    mock_sr.buscar_token_valido.return_value = {"id_token": 5, "id_usuario": 99}

    with pytest.raises(AutenticacionError):
        svc.verificar_otp_email(1, "847291")
