"""Tests: alertas por umbral, electrodo suelto, idempotencia de ventana."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.negocio import heuristica_servicio as svc

# ── Umbrales de prueba ────────────────────────────────────────────────────────

_U_SOBREESFUERZO = {
    "parametro": "fc_porcentaje_max",
    "operador": ">=",
    "valor": "85",
    "severidad": "rojo",
    "mensaje": "Esfuerzo máximo superado.",
    "id_deportista": None,
}

_U_CAIDA = {
    "parametro": "inclinacion_grados",
    "operador": ">=",
    "valor": "45",
    "severidad": "rojo",
    "mensaje": "Postura peligrosa detectada.",
    "id_deportista": None,
}

_U_FATIGA = {
    "parametro": "fc_recuperacion_bpm",
    "operador": ">=",
    "valor": "5",
    "severidad": "amarillo",
    "mensaje": "Recuperación cardíaca lenta.",
    "id_deportista": None,
}


# ── Tests ─────────────────────────────────────────────────────────────────────

@patch("app.negocio.heuristica_servicio.ar")
@patch("app.negocio.heuristica_servicio.muchos", return_value=[])
def test_electrodo_suelto(mock_muchos, mock_ar):
    mock_ar.ultima_alerta_por_tipo.return_value = None

    ecg = [{"valor_adc": 100, "electrodo_suelto": True}]
    alertas = svc.evaluar_lote(1, None, ecg, [], [])

    tipos = [a["tipo"] for a in alertas]
    assert "electrodo_suelto" in tipos
    mock_ar.registrar_alerta.assert_called()


@patch("app.negocio.heuristica_servicio.ar")
@patch("app.negocio.heuristica_servicio.muchos", return_value=[_U_SOBREESFUERZO])
def test_sobreesfuerzo_cardiaco(mock_muchos, mock_ar):
    mock_ar.ultima_alerta_por_tipo.return_value = None
    # fc_max = 200 (id_deportista=None); 90% de 200 = 180 BPM
    ecg = [{"bpm": 180.0}]

    alertas = svc.evaluar_lote(1, None, ecg, [], [])

    tipos = [a["tipo"] for a in alertas]
    assert "sobreesfuerzo_cardiaco" in tipos
    assert alertas[0]["severidad"] == "rojo"


@patch("app.negocio.heuristica_servicio.ar")
@patch("app.negocio.heuristica_servicio.muchos", return_value=[_U_SOBREESFUERZO])
def test_no_alerta_fc_normal(mock_muchos, mock_ar):
    mock_ar.ultima_alerta_por_tipo.return_value = None
    # 60 BPM → 30% de FCmax → no sobrepasa 85%
    ecg = [{"bpm": 60.0}]

    alertas = svc.evaluar_lote(1, None, ecg, [], [])

    assert alertas == []
    mock_ar.registrar_alerta.assert_not_called()


@patch("app.negocio.heuristica_servicio.ar")
@patch("app.negocio.heuristica_servicio.muchos", return_value=[_U_CAIDA])
def test_caida_postura(mock_muchos, mock_ar):
    mock_ar.ultima_alerta_por_tipo.return_value = None
    imu = [{"inclinacion_grados": 60.0}]

    alertas = svc.evaluar_lote(1, None, [], [], imu)

    tipos = [a["tipo"] for a in alertas]
    assert "caida_postura" in tipos


@patch("app.negocio.heuristica_servicio.ar")
@patch("app.negocio.heuristica_servicio.muchos", return_value=[_U_FATIGA])
def test_fatiga_recuperacion_lenta(mock_muchos, mock_ar):
    mock_ar.ultima_alerta_por_tipo.return_value = None
    # delta_bpm = bpm[-1] - bpm[0] = 110 - 100 = +10, operador ">= 5" → dispara fatiga
    ecg = [{"bpm": 100.0}, {"bpm": 110.0}]

    alertas = svc.evaluar_lote(1, None, ecg, [], [])

    tipos = [a["tipo"] for a in alertas]
    assert "fatiga" in tipos


@patch("app.negocio.heuristica_servicio.ar")
@patch("app.negocio.heuristica_servicio.muchos", return_value=[_U_SOBREESFUERZO])
def test_idempotencia_ventana_30s(mock_muchos, mock_ar):
    """Alerta reciente dentro de la ventana de 30 s no se duplica."""
    ts_reciente = datetime.now(timezone.utc) - timedelta(seconds=10)
    mock_ar.ultima_alerta_por_tipo.return_value = {"capturado_en": ts_reciente}

    ecg = [{"bpm": 180.0}]
    alertas = svc.evaluar_lote(1, None, ecg, [], [])

    assert alertas == []
    mock_ar.registrar_alerta.assert_not_called()


@patch("app.negocio.heuristica_servicio.ar")
@patch("app.negocio.heuristica_servicio.muchos", return_value=[_U_SOBREESFUERZO])
def test_alerta_fuera_ventana_30s(mock_muchos, mock_ar):
    """Alerta anterior fuera de la ventana de 30 s sí se registra."""
    ts_viejo = datetime.now(timezone.utc) - timedelta(seconds=45)
    mock_ar.ultima_alerta_por_tipo.return_value = {"capturado_en": ts_viejo}

    ecg = [{"bpm": 180.0}]
    alertas = svc.evaluar_lote(1, None, ecg, [], [])

    tipos = [a["tipo"] for a in alertas]
    assert "sobreesfuerzo_cardiaco" in tipos
