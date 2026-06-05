"""Tests: HMAC válido/inválido, timestamp viejo, rangos de sensores, lote grande."""
from __future__ import annotations

import hashlib
import hmac
import time
from unittest.mock import patch

import pytest

from app.comun.errores import AutenticacionError, ValidacionError
from app.negocio import ingesta_servicio as svc

# ── Helpers ──────────────────────────────────────────────────────────────────

_CODIGO = "CHAL0001"
_API_KEY = "testApiKey123Secret"
_BODY    = b'{"ecg":[]}'

_DISPOSITIVO_ACTIVO = {
    "id_dispositivo": 1,
    "codigo": _CODIGO,
    "api_key_hash": "argon2_hash_placeholder",
    "estado": "activo",
    "id_deportista": 5,
}


def _firma_valida(timestamp: str) -> str:
    mensaje = (_CODIGO + timestamp).encode() + _BODY
    return hmac.new(_API_KEY.encode(), mensaje, hashlib.sha256).hexdigest()


# ── autenticar_dispositivo ────────────────────────────────────────────────────

@patch("app.negocio.ingesta_servicio.verificar_password", return_value=True)
@patch("app.negocio.ingesta_servicio.dr")
def test_hmac_valido(mock_dr, mock_vp):
    ts = str(int(time.time()))
    mock_dr.buscar_por_codigo.return_value = _DISPOSITIVO_ACTIVO

    resultado = svc.autenticar_dispositivo(
        _CODIGO, _API_KEY, ts, _firma_valida(ts), _BODY
    )

    assert resultado["id_dispositivo"] == 1


@patch("app.negocio.ingesta_servicio.verificar_password", return_value=True)
@patch("app.negocio.ingesta_servicio.dr")
def test_hmac_invalido_firma(mock_dr, mock_vp):
    ts = str(int(time.time()))
    mock_dr.buscar_por_codigo.return_value = _DISPOSITIVO_ACTIVO

    with pytest.raises(AutenticacionError, match="Firma inválida"):
        svc.autenticar_dispositivo(
            _CODIGO, _API_KEY, ts, "firma_incorrecta_aaaa", _BODY
        )


@patch("app.negocio.ingesta_servicio.dr")
def test_timestamp_viejo(mock_dr):
    ts_viejo = str(int(time.time()) - 120)
    mock_dr.buscar_por_codigo.return_value = _DISPOSITIVO_ACTIVO

    with pytest.raises(AutenticacionError, match="anti-replay"):
        svc.autenticar_dispositivo(
            _CODIGO, _API_KEY, ts_viejo, "irrelevante", _BODY
        )


@patch("app.negocio.ingesta_servicio.dr")
def test_dispositivo_no_encontrado(mock_dr):
    mock_dr.buscar_por_codigo.return_value = None

    with pytest.raises(AutenticacionError, match="no autorizado"):
        svc.autenticar_dispositivo(
            "INEXISTENTE", _API_KEY, str(int(time.time())), "firma", _BODY
        )


@patch("app.negocio.ingesta_servicio.verificar_password", return_value=True)
@patch("app.negocio.ingesta_servicio.dr")
def test_dispositivo_inactivo(mock_dr, mock_vp):
    ts = str(int(time.time()))
    disp = {**_DISPOSITIVO_ACTIVO, "estado": "inactivo"}
    mock_dr.buscar_por_codigo.return_value = disp

    with pytest.raises(AutenticacionError, match="inactivo"):
        svc.autenticar_dispositivo(
            _CODIGO, _API_KEY, ts, _firma_valida(ts), _BODY
        )


# ── Validación de rangos ECG ──────────────────────────────────────────────────

def test_ecg_range_valido():
    lecturas = [{"adc": 2048, "t": "2026-06-04 00:00:00.000"}]
    resultado = svc._validar_ecg(lecturas)
    assert len(resultado) == 1
    assert resultado[0]["valor_adc"] == 2048


def test_ecg_range_fuera():
    lecturas = [{"adc": 5000}, {"adc": -1}, {"adc": 4095}]
    resultado = svc._validar_ecg(lecturas)
    assert len(resultado) == 1
    assert resultado[0]["valor_adc"] == 4095


def test_ecg_electrodo_suelto():
    lecturas = [{"adc": 100, "lo": True}]
    resultado = svc._validar_ecg(lecturas)
    assert resultado[0]["electrodo_suelto"] is True


# ── Validación GPS ─────────────────────────────────────────────────────────────

def test_gps_valido():
    lecturas = [{"lat": 4.71, "lon": -74.07, "vel": 12.5, "sat": 8}]
    resultado = svc._validar_gps(lecturas)
    assert len(resultado) == 1
    assert resultado[0]["latitud"] == pytest.approx(4.71)


def test_gps_fuera_rango():
    lecturas = [{"lat": 100.0, "lon": -74.07}]
    resultado = svc._validar_gps(lecturas)
    assert len(resultado) == 0


# ── Lote grande ───────────────────────────────────────────────────────────────

@patch("app.negocio.ingesta_servicio.sr")
def test_lote_grande_rechazado(mock_sr):
    mock_sr.buscar_por_id.return_value = {"estado": "en_curso", "id_deportista": 5}
    payload = {
        "ecg": [{"adc": 100}] * 300,
        "gps": [{"lat": 4.71, "lon": -74.07}] * 150,
        "imu": [{"ax": 0, "ay": 0, "az": 0, "gx": 0, "gy": 0, "gz": 0}] * 100,
    }

    with pytest.raises(ValidacionError, match="grande"):
        svc.registrar_lecturas(1, payload)


@patch("app.negocio.ingesta_servicio.lr")
@patch("app.negocio.ingesta_servicio.sr")
def test_registrar_lecturas_ok(mock_sr, mock_lr):
    mock_sr.buscar_por_id.return_value = {"estado": "en_curso", "id_deportista": 5}
    mock_lr.insertar_lote_ecg.return_value = 2
    mock_lr.insertar_lote_gps.return_value = 1
    mock_lr.insertar_lote_imu.return_value = 0
    payload = {
        "ecg": [{"adc": 1024}, {"adc": 2048}],
        "gps": [{"lat": 4.71, "lon": -74.07}],
        "imu": [],
    }

    resultado = svc.registrar_lecturas(1, payload)

    assert resultado["recibidas"]["ecg"] == 2
    assert resultado["recibidas"]["gps"] == 1
