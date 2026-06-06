"""Servicio de ingesta: autenticación HMAC, validación de rangos, escritura por lotes."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any

from app.comun.errores import AutenticacionError, ValidacionError
from app.comun.seguridad_utils import verificar_password
from app.datos import dispositivo_repositorio as dr
from app.datos import lectura_repositorio as lr
from app.datos import sesion_repositorio as sr

_MAX_DESFASE_S = 60
_MAX_LOTE = 500


# ── Autenticación ─────────────────────────────────────────────────────────────

def autenticar_dispositivo(
    codigo: str,
    api_key: str,
    timestamp: str,
    signature: str,
    body_raw: bytes,
) -> dict[str, Any]:
    """Verifica la identidad del dispositivo.

    1. Busca el dispositivo por código.
    2. Verifica desfase temporal <= 60 s (anti-replay).
    3. Comprueba api_key contra api_key_hash (Argon2id).
    4. Valida HMAC-SHA256(api_key, codigo + timestamp + body).
    Lanza AutenticacionError en cualquier fallo (mensaje genérico para no enumerar).
    """
    dispositivo = dr.buscar_por_codigo(codigo)
    if not dispositivo:
        raise AutenticacionError("Dispositivo no autorizado.")

    try:
        ts_int = int(timestamp)
    except (ValueError, TypeError):
        raise AutenticacionError("Timestamp inválido.")

    if abs(time.time() - ts_int) > _MAX_DESFASE_S:
        raise AutenticacionError("Timestamp fuera de ventana (anti-replay).")

    argon2_ok = verificar_password(api_key, dispositivo["api_key_hash"])
    if not argon2_ok:
        raise AutenticacionError("Dispositivo no autorizado.")

    mensaje = (codigo + timestamp).encode() + body_raw
    firma_esperada = hmac.new(api_key.encode(), mensaje, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma_esperada, signature):
        raise AutenticacionError("Firma inválida.")

    if dispositivo["estado"] != "activo":
        raise AutenticacionError("Dispositivo inactivo.")

    return dispositivo


# ── Sesión ────────────────────────────────────────────────────────────────────

def iniciar_sesion(codigo_dispositivo: str) -> dict[str, Any]:
    """Crea una sesión de entrenamiento para el deportista asignado al dispositivo."""
    dispositivo = dr.buscar_por_codigo(codigo_dispositivo)
    if not dispositivo:
        raise ValidacionError("Dispositivo no encontrado.")

    id_deportista = dispositivo.get("id_deportista") or dispositivo.get("dep_id")
    if not id_deportista:
        raise ValidacionError("El dispositivo no tiene un deportista asignado.")

    fila = sr.crear_sesion(id_deportista, dispositivo["id_dispositivo"])
    return {
        "id_sesion": fila["id_sesion"],
        "inicio": fila["inicio"].isoformat() if isinstance(fila["inicio"], datetime) else str(fila["inicio"]),
    }


# ── Lecturas ──────────────────────────────────────────────────────────────────

def _validar_ecg(lecturas: list[dict]) -> list[dict]:
    validas = []
    for m in lecturas:
        try:
            adc = int(m["adc"])
        except (KeyError, ValueError, TypeError):
            continue
        if not (0 <= adc <= 4095):
            continue
        validas.append({
            "capturado_en":    m.get("t", datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]),
            "valor_adc":       adc,
            "electrodo_suelto": bool(m.get("lo", False)),
        })
    return validas


def _validar_gps(lecturas: list[dict]) -> list[dict]:
    validas = []
    for m in lecturas:
        try:
            lat = float(m["lat"])
            lon = float(m["lon"])
        except (KeyError, ValueError, TypeError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        validas.append({
            "capturado_en": m.get("t", datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]),
            "latitud":      lat,
            "longitud":     lon,
            "velocidad_kmh": float(m["vel"]) if "vel" in m else None,
            "satelites":    int(m["sat"]) if "sat" in m else None,
        })
    return validas


def _validar_imu(lecturas: list[dict]) -> list[dict]:
    validas = []
    for m in lecturas:
        try:
            ax, ay, az = int(m["ax"]), int(m["ay"]), int(m["az"])
            gx, gy, gz = int(m["gx"]), int(m["gy"]), int(m["gz"])
        except (KeyError, ValueError, TypeError):
            continue
        validas.append({
            "capturado_en":      m.get("t", datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]),
            "accel_x": ax, "accel_y": ay, "accel_z": az,
            "gyro_x":  gx, "gyro_y":  gy, "gyro_z":  gz,
            "inclinacion_grados": float(m["inc"]) if "inc" in m else None,
        })
    return validas


def registrar_lecturas(id_sesion: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Valida y persiste un lote de lecturas. Llama al motor heurístico.

    payload = {"ecg": [...], "gps": [...], "imu": [...]}
    Devuelve {"recibidas": {"ecg": N, ...}, "alertas": [...]}
    """
    sesion = sr.buscar_por_id(id_sesion)
    if not sesion:
        raise ValidacionError("Sesión no encontrada.")
    if sesion["estado"] != "en_curso":
        raise ValidacionError("La sesión no está en curso.")

    ecg_raw = payload.get("ecg", [])
    gps_raw = payload.get("gps", [])
    imu_raw = payload.get("imu", [])

    total = len(ecg_raw) + len(gps_raw) + len(imu_raw)
    if total > _MAX_LOTE:
        raise ValidacionError(f"Lote demasiado grande ({total} > {_MAX_LOTE}).")

    ecg_ok = _validar_ecg(ecg_raw)
    gps_ok = _validar_gps(gps_raw)
    imu_ok = _validar_imu(imu_raw)

    n_ecg = lr.insertar_lote_ecg(id_sesion, ecg_ok)
    n_gps = lr.insertar_lote_gps(id_sesion, gps_ok)
    n_imu = lr.insertar_lote_imu(id_sesion, imu_ok)

    id_deportista = sesion.get("id_deportista")
    alertas: list[dict] = []
    try:
        from app.negocio import heuristica_servicio as hs
        alertas = hs.evaluar_lote(id_sesion, id_deportista, ecg_ok, gps_ok, imu_ok)
    except Exception:
        pass

    return {
        "recibidas": {"ecg": n_ecg, "gps": n_gps, "imu": n_imu},
        "alertas": alertas,
    }


# ── Finalizar ─────────────────────────────────────────────────────────────────

def finalizar_sesion(id_sesion: int) -> dict[str, Any]:
    """Marca la sesión finalizada y calcula métricas."""
    sesion = sr.buscar_por_id(id_sesion)
    if not sesion:
        raise ValidacionError("Sesión no encontrada.")

    sr.finalizar_sesion(id_sesion)

    metrica: dict[str, Any] = {}
    try:
        from app.negocio import metricas_servicio as ms
        metrica = ms.calcular_y_guardar(id_sesion)
    except Exception:
        pass

    return {"id_sesion": id_sesion, "metricas": metrica}
