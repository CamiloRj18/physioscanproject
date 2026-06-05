"""Tests: generar lote, usar código, agotamiento de 12, reemisión admin."""
from __future__ import annotations

from unittest.mock import call, patch

import pytest

from app.comun.errores import AutenticacionError, BloqueadoError, ValidacionError
from app.negocio.seguridad import recuperacion_archivo_servicio as svc

# ── Helpers ──────────────────────────────────────────────────────────────────

_USUARIO = {
    "id_usuario": 1,
    "codigo_usuario": "ANA0001",
    "estado": "activo",
}

_LOTE = {"id_lote": 10, "codigos_usados": 0, "total_codigos": 12}

_CODIGO_BD = {"id_codigo": 20, "orden": 1, "codigo_hash": "hash_code"}


# ── Generación de lote ────────────────────────────────────────────────────────

@patch("app.negocio.seguridad.recuperacion_archivo_servicio.audit")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.hash_codigo", return_value="h")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.sr")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.ur")
def test_generar_lote_ok(mock_ur, mock_sr, mock_hc, mock_audit):
    mock_ur.buscar_por_id.return_value = _USUARIO
    mock_sr.obtener_numero_lote_maximo.return_value = 0
    mock_sr.crear_lote.return_value = 10
    mock_sr.crear_codigos_lote.return_value = None

    codigos, txt, nombre = svc.generar_lote(1)

    assert len(codigos) == 12
    assert "ANA0001" in nombre
    assert "PhysioScan" in txt
    mock_sr.desactivar_lotes_usuario.assert_called_once_with(1)
    mock_audit.assert_called_once()


@patch("app.negocio.seguridad.recuperacion_archivo_servicio.audit")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.hash_codigo", return_value="h")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.sr")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.ur")
def test_generar_lote_reemision_admin(mock_ur, mock_sr, mock_hc, mock_audit):
    mock_ur.buscar_por_id.return_value = _USUARIO
    mock_sr.obtener_numero_lote_maximo.return_value = 1
    mock_sr.crear_lote.return_value = 11
    mock_sr.crear_codigos_lote.return_value = None

    _, _, _ = svc.generar_lote(1, generado_por=99)

    audit_call = mock_audit.call_args
    assert audit_call[0][0] == "LOTE_REEMITIDO"


# ── Recuperación con código ───────────────────────────────────────────────────

@patch("app.negocio.seguridad.recuperacion_archivo_servicio.audit")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.en_historial", return_value=False)
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.hash_nueva", return_value="new_hash")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.verificar_codigo", return_value=True)
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.validar_politica")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.sr")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.ur")
def test_usar_codigo_ok(mock_ur, mock_sr, mock_pol, mock_vc, mock_hn, mock_eh, mock_audit):
    mock_ur.buscar_por_email.return_value = _USUARIO
    mock_sr.obtener_lote_activo.return_value = _LOTE
    mock_sr.obtener_codigos_lote.return_value = [_CODIGO_BD]
    mock_sr.obtener_historial_contrasena.return_value = []
    mock_sr.obtener_lote_por_id.return_value = {"codigos_usados": 1, "total_codigos": 12}

    svc.recuperar_con_codigo("ana@ejemplo.com", "ABCD-EFGH-IJKL", "NuevaClave1!", "1.2.3.4")

    mock_sr.marcar_codigo_usado.assert_called_once_with(20)
    mock_sr.revocar_todas_sesiones.assert_called_once_with(1)


@patch("app.negocio.seguridad.recuperacion_archivo_servicio.verificar_codigo", return_value=False)
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.validar_politica")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.audit")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.sr")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.ur")
def test_codigo_invalido(mock_ur, mock_sr, mock_audit, mock_pol, mock_vc):
    mock_ur.buscar_por_email.return_value = _USUARIO
    mock_sr.obtener_lote_activo.return_value = _LOTE
    mock_sr.obtener_codigos_lote.return_value = [_CODIGO_BD]

    with pytest.raises(AutenticacionError, match="Código inválido"):
        svc.recuperar_con_codigo("ana@ejemplo.com", "XXXX-XXXX-XXXX", "NuevaClave1!")


@patch("app.negocio.seguridad.recuperacion_archivo_servicio.sr")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.ur")
def test_sin_lote_activo(mock_ur, mock_sr):
    mock_ur.buscar_por_email.return_value = _USUARIO
    mock_sr.obtener_lote_activo.return_value = None

    with pytest.raises(ValidacionError, match="archivo de recuperación"):
        svc.recuperar_con_codigo("ana@ejemplo.com", "ABCD-EFGH-IJKL", "NuevaClave1!")


@patch("app.negocio.seguridad.recuperacion_archivo_servicio.audit")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.en_historial", return_value=False)
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.hash_nueva", return_value="new_hash")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.verificar_codigo", return_value=True)
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.validar_politica")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.sr")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.ur")
def test_agotamiento_12(mock_ur, mock_sr, mock_pol, mock_vc, mock_hn, mock_eh, mock_audit):
    """Al usar el código #12 el lote queda desactivado."""
    mock_ur.buscar_por_email.return_value = _USUARIO
    mock_sr.obtener_lote_activo.return_value = _LOTE
    mock_sr.obtener_codigos_lote.return_value = [_CODIGO_BD]
    mock_sr.obtener_historial_contrasena.return_value = []
    mock_sr.obtener_lote_por_id.return_value = {"codigos_usados": 12, "total_codigos": 12}

    svc.recuperar_con_codigo("ana@ejemplo.com", "ABCD-EFGH-IJKL", "NuevaClave1!")

    mock_sr.desactivar_lote.assert_called_once_with(10)

    audit_call_args = [c[0][0] for c in mock_audit.call_args_list]
    assert "CONTRASENA_RESTABLECIDA_ARCHIVO" in audit_call_args


@patch("app.negocio.seguridad.recuperacion_archivo_servicio.ur")
def test_cuenta_bloqueada(mock_ur):
    mock_ur.buscar_por_email.return_value = {**_USUARIO, "estado": "bloqueado"}

    with pytest.raises(BloqueadoError, match="bloqueada"):
        svc.recuperar_con_codigo("ana@ejemplo.com", "ABCD-EFGH-IJKL", "NuevaClave1!")


@patch("app.negocio.seguridad.recuperacion_archivo_servicio.audit")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.en_historial", return_value=True)
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.verificar_codigo", return_value=True)
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.validar_politica")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.sr")
@patch("app.negocio.seguridad.recuperacion_archivo_servicio.ur")
def test_password_reusada(mock_ur, mock_sr, mock_pol, mock_vc, mock_eh, mock_audit):
    mock_ur.buscar_por_email.return_value = _USUARIO
    mock_sr.obtener_lote_activo.return_value = _LOTE
    mock_sr.obtener_codigos_lote.return_value = [_CODIGO_BD]
    mock_sr.obtener_historial_contrasena.return_value = [{"hash_contrasena": "old_hash"}]

    with pytest.raises(ValidacionError, match="ya utilizaste"):
        svc.recuperar_con_codigo("ana@ejemplo.com", "ABCD-EFGH-IJKL", "NuevaClave1!")
