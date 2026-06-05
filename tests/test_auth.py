"""Tests: registro, login, bloqueo por intentos, anti-enumeración, verificación email."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.comun.errores import AutenticacionError, BloqueadoError, ConflictoError, ValidacionError
from app.negocio import auth_servicio as svc

# ── Helpers ──────────────────────────────────────────────────────────────────

_ROL = {"id_rol": 4, "nombre": "usuario"}


def _usuario(**kwargs):
    base = {
        "id_usuario": 1,
        "primer_nombre": "Ana",
        "email": "ana@ejemplo.com",
        "email_verificado": True,
        "estado": "activo",
        "nombre_rol": "deportista",
        "bloqueado_hasta": None,
        "intentos_fallidos": 0,
    }
    base.update(kwargs)
    return base


# ── Registro ──────────────────────────────────────────────────────────────────

@patch("app.negocio.auth_servicio.audit")
@patch("app.negocio.auth_servicio.hash_codigo", return_value="hash_code")
@patch("app.negocio.auth_servicio.hash_nueva", return_value="hash_pwd")
@patch("app.negocio.auth_servicio.validar_politica")
@patch("app.negocio.auth_servicio.ur")
def test_registro_ok(mock_ur, mock_pol, mock_hash, mock_hc, mock_audit):
    mock_ur.buscar_por_email.return_value = None
    mock_ur.buscar_rol_por_nombre.return_value = _ROL
    mock_ur.crear_completo.return_value = (1, None)

    id_u, token, codigos = svc.registrar_usuario(
        "Ana", None, "Lopez", None, "ana@ejemplo.com", None, "Segura1234!"
    )

    assert id_u == 1
    assert token
    assert len(codigos) == 12
    mock_audit.assert_called_once()


@patch("app.negocio.auth_servicio.validar_politica")
@patch("app.negocio.auth_servicio.ur")
def test_registro_email_duplicado(mock_ur, mock_pol):
    mock_ur.buscar_por_email.return_value = _usuario()

    with pytest.raises(ConflictoError):
        svc.registrar_usuario(
            "Ana", None, "Lopez", None, "ana@ejemplo.com", None, "Segura1234!"
        )


def test_registro_email_invalido():
    with pytest.raises(ValidacionError, match="formato"):
        svc.registrar_usuario(
            "Ana", None, "Lopez", None, "no-es-email", None, "Segura1234!"
        )


@patch("app.negocio.auth_servicio.validar_politica",
       side_effect=ValidacionError("contraseña débil"))
@patch("app.negocio.auth_servicio.ur")
def test_registro_password_debil(mock_ur, mock_pol):
    mock_ur.buscar_por_email.return_value = None

    with pytest.raises(ValidacionError, match="débil"):
        svc.registrar_usuario(
            "Ana", None, "Lopez", None, "ana@ejemplo.com", None, "1234"
        )


# ── Autenticación ─────────────────────────────────────────────────────────────

@patch("app.negocio.auth_servicio.audit")
@patch("app.negocio.auth_servicio.verificar_password", return_value=True)
@patch("app.negocio.auth_servicio.sr")
@patch("app.negocio.auth_servicio.ur")
def test_autenticar_ok(mock_ur, mock_sr, mock_vp, mock_audit, usuario_activo):
    mock_ur.buscar_por_email.return_value = usuario_activo
    mock_sr.obtener_credencial.return_value = {"hash_contrasena": "hash"}

    resultado = svc.autenticar("ana@ejemplo.com", "clave", "1.2.3.4", "UA")

    assert resultado["id_usuario"] == 1
    mock_ur.actualizar_ultimo_acceso.assert_called_once_with(1)


@patch("app.negocio.auth_servicio.verificar_password", return_value=False)
@patch("app.negocio.auth_servicio.sr")
@patch("app.negocio.auth_servicio.ur")
def test_autenticar_anti_enumeracion(mock_ur, mock_sr, mock_vp):
    """Usuario inexistente recibe el mismo error que contraseña incorrecta."""
    mock_ur.buscar_por_email.return_value = None

    with pytest.raises(AutenticacionError, match="Credenciales inválidas"):
        svc.autenticar("noexiste@x.com", "clave", None, None)

    mock_vp.assert_called_once()  # consume tiempo con dummy hash


@patch("app.negocio.auth_servicio.ur")
def test_autenticar_bloqueo_activo(mock_ur):
    mock_ur.buscar_por_email.return_value = _usuario(
        bloqueado_hasta=datetime.utcnow() + timedelta(minutes=10)
    )

    with pytest.raises(BloqueadoError):
        svc.autenticar("ana@ejemplo.com", "clave", None, None)


@patch("app.negocio.auth_servicio.audit")
@patch("app.negocio.auth_servicio.verificar_password", return_value=False)
@patch("app.negocio.auth_servicio.sr")
@patch("app.negocio.auth_servicio.ur")
def test_autenticar_bloqueo_por_intentos(mock_ur, mock_sr, mock_vp, mock_audit):
    mock_ur.buscar_por_email.return_value = _usuario()
    mock_sr.obtener_credencial.return_value = {"hash_contrasena": "hash"}
    mock_ur.buscar_por_id.return_value = _usuario(intentos_fallidos=5)

    with pytest.raises(BloqueadoError):
        svc.autenticar("ana@ejemplo.com", "mala", None, None)

    mock_ur.bloquear.assert_called_once()
    mock_audit.assert_called()


@patch("app.negocio.auth_servicio.audit")
@patch("app.negocio.auth_servicio.verificar_password", return_value=True)
@patch("app.negocio.auth_servicio.sr")
@patch("app.negocio.auth_servicio.ur")
def test_autenticar_email_no_verificado(mock_ur, mock_sr, mock_vp, mock_audit):
    mock_ur.buscar_por_email.return_value = _usuario(email_verificado=False)
    mock_sr.obtener_credencial.return_value = {"hash_contrasena": "hash"}

    with pytest.raises(AutenticacionError, match="Verifica"):
        svc.autenticar("ana@ejemplo.com", "clave", None, None)


@patch("app.negocio.auth_servicio.audit")
@patch("app.negocio.auth_servicio.verificar_password", return_value=True)
@patch("app.negocio.auth_servicio.sr")
@patch("app.negocio.auth_servicio.ur")
def test_autenticar_cuenta_inactiva(mock_ur, mock_sr, mock_vp, mock_audit):
    mock_ur.buscar_por_email.return_value = _usuario(estado="suspendido")
    mock_sr.obtener_credencial.return_value = {"hash_contrasena": "hash"}

    with pytest.raises(AutenticacionError, match="activa"):
        svc.autenticar("ana@ejemplo.com", "clave", None, None)


# ── Verificación de email ─────────────────────────────────────────────────────

@patch("app.negocio.auth_servicio.audit")
@patch("app.negocio.auth_servicio.sr")
@patch("app.negocio.auth_servicio.ur")
def test_verificar_email_ok(mock_ur, mock_sr, mock_audit):
    token = "tokenclaro123"
    mock_sr.buscar_token_valido.return_value = {"id_token": 10, "id_usuario": 1}

    id_u = svc.verificar_email(token)

    assert id_u == 1
    mock_sr.marcar_token_usado.assert_called_once_with(10)
    mock_ur.marcar_email_verificado.assert_called_once_with(1)


@patch("app.negocio.auth_servicio.sr")
def test_verificar_email_expirado(mock_sr):
    mock_sr.buscar_token_valido.return_value = None

    with pytest.raises(AutenticacionError, match="expirado"):
        svc.verificar_email("tokeninvalido")
