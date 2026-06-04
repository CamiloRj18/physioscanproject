"""Simulador del chaleco PhysioScan.

Firma e inyecta lecturas ECG/GPS/IMU sintéticas al API local para demo y tests sin hardware.

Uso:
    python scripts/simular_chaleco.py [--url URL] [--code DEVICE_CODE] [--key API_KEY]
    python scripts/simular_chaleco.py           # usa .env o valores por defecto
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import random
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Configuración (env o argparse) ────────────────────────────────────────────
DEFAULT_URL  = os.environ.get("SIMULATE_SERVER_URL", "http://127.0.0.1:5000")
DEFAULT_CODE = os.environ.get("SIMULATE_DEVICE_CODE", "CHAL0001")
DEFAULT_KEY  = os.environ.get("SIMULATE_DEVICE_KEY",  "clave-demo-insegura")

LOTES       = 5     # número de lotes a enviar
INTERVALO_S = 1.0   # segundos entre lotes
ECG_POR_LOTE = 10
GPS_POR_LOTE = 1
IMU_POR_LOTE = 5


# ── Firma HMAC ────────────────────────────────────────────────────────────────

def firmar(api_key: str, device_code: str, timestamp: str, body: bytes) -> str:
    mensaje = (device_code + timestamp).encode() + body
    return hmac.new(api_key.encode(), mensaje, hashlib.sha256).hexdigest()


def cabeceras(api_key: str, device_code: str, body: bytes) -> dict:
    ts = str(int(time.time()))
    return {
        "Content-Type": "application/json",
        "X-Device-Code": device_code,
        "X-Device-Key":  api_key,
        "X-Timestamp":   ts,
        "X-Signature":   firmar(api_key, device_code, ts, body),
    }


# ── Generadores de lecturas sintéticas ───────────────────────────────────────

def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


def generar_ecg(n: int = ECG_POR_LOTE) -> list[dict]:
    """ADC sinusoidal 1200–2800 (simulación de pulso cardíaco ~60-80 BPM)."""
    muestras = []
    for i in range(n):
        t = time.time() + i * 0.01
        adc = int(2048 + 800 * math.sin(2 * math.pi * 1.2 * t) + random.gauss(0, 30))
        adc = max(0, min(4095, adc))
        muestras.append({"t": _iso(), "adc": adc, "lo": False})
    return muestras


def generar_gps(n: int = GPS_POR_LOTE) -> list[dict]:
    """Recorrido sintético: deriva ~7 m/muestra al norte desde un punto base."""
    lat_base = 4.1490 + random.uniform(-0.0001, 0.0001)
    lon_base = -74.8838 + random.uniform(-0.0001, 0.0001)
    muestras = []
    for i in range(n):
        muestras.append({
            "t":   _iso(),
            "lat": round(lat_base + i * 0.00006, 6),
            "lon": round(lon_base + i * 0.00003, 6),
            "vel": round(random.uniform(6.0, 12.0), 2),
            "sat": random.randint(7, 12),
        })
    return muestras


def generar_imu(n: int = IMU_POR_LOTE) -> list[dict]:
    """Acelerómetro y giroscopio con inclinación leve."""
    muestras = []
    for _ in range(n):
        muestras.append({
            "t":   _iso(),
            "ax":  random.randint(-200, 200),
            "ay":  random.randint(-100, 100),
            "az":  random.randint(16000, 16500),
            "gx":  random.randint(-50, 50),
            "gy":  random.randint(-50, 50),
            "gz":  random.randint(-10, 10),
            "inc": round(random.uniform(0.0, 15.0), 2),
        })
    return muestras


# ── Flujo principal ───────────────────────────────────────────────────────────

def post(url: str, payload: dict, api_key: str, device_code: str) -> dict:
    body = json.dumps(payload, separators=(",", ":")).encode()
    r = requests.post(url, data=body, headers=cabeceras(api_key, device_code, body), timeout=10)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(description="Simulador chaleco PhysioScan")
    parser.add_argument("--url",  default=DEFAULT_URL,  help="URL base del servidor Flask")
    parser.add_argument("--code", default=DEFAULT_CODE, help="Código del dispositivo (CHAL####)")
    parser.add_argument("--key",  default=DEFAULT_KEY,  help="API key del dispositivo")
    parser.add_argument("--lotes", type=int, default=LOTES, help="Número de lotes a enviar")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    print(f"[sim] Servidor: {base}")
    print(f"[sim] Dispositivo: {args.code}")

    # 1. Iniciar sesión
    print("[sim] POST /api/v1/sesiones/iniciar ...")
    resp = post(f"{base}/api/v1/sesiones/iniciar",
                {"codigo_dispositivo": args.code},
                args.key, args.code)
    if not resp.get("ok"):
        print(f"[sim] Error: {resp.get('error')}", file=sys.stderr)
        sys.exit(1)

    id_sesion = resp["datos"]["id_sesion"]
    inicio    = resp["datos"]["inicio"]
    print(f"[sim] Sesión iniciada: id={id_sesion}, inicio={inicio}")

    # 2. Enviar lotes
    total = {"ecg": 0, "gps": 0, "imu": 0}
    for i in range(1, args.lotes + 1):
        payload = {
            "ecg": generar_ecg(),
            "gps": generar_gps(),
            "imu": generar_imu(),
        }
        print(f"[sim] Lote {i}/{args.lotes} → POST /sesiones/{id_sesion}/lecturas ...")
        resp = post(f"{base}/api/v1/sesiones/{id_sesion}/lecturas",
                    payload, args.key, args.code)
        if resp.get("ok"):
            r = resp["datos"]["recibidas"]
            total["ecg"] += r.get("ecg", 0)
            total["gps"] += r.get("gps", 0)
            total["imu"] += r.get("imu", 0)
            alertas = resp["datos"].get("alertas", [])
            print(f"      recibidas: ecg={r.get('ecg',0)} gps={r.get('gps',0)} imu={r.get('imu',0)}"
                  f"  alertas={len(alertas)}")
            for a in alertas:
                print(f"      [alerta] {a.get('severidad','?')} — {a.get('mensaje','')}")
        else:
            print(f"      Error: {resp.get('error')}", file=sys.stderr)
        if i < args.lotes:
            time.sleep(INTERVALO_S)

    # 3. Finalizar sesión
    print(f"[sim] POST /sesiones/{id_sesion}/finalizar ...")
    resp = post(f"{base}/api/v1/sesiones/{id_sesion}/finalizar",
                {}, args.key, args.code)
    if resp.get("ok"):
        m = resp["datos"].get("metricas", {})
        print(f"[sim] Sesion finalizada. Metricas: {json.dumps(m, default=str, indent=2)}")
    else:
        print(f"[sim] Error al finalizar: {resp.get('error')}", file=sys.stderr)

    print(f"\n[sim] Total insertado: {total}")
    print("[sim] Verifica en MySQL:")
    print(f"  SELECT COUNT(*) FROM lectura_ecg  WHERE id_sesion={id_sesion};")
    print(f"  SELECT COUNT(*) FROM lectura_gps  WHERE id_sesion={id_sesion};")
    print(f"  SELECT COUNT(*) FROM lectura_imu  WHERE id_sesion={id_sesion};")
    print(f"  SELECT * FROM metrica_sesion WHERE id_sesion={id_sesion};")


if __name__ == "__main__":
    main()
