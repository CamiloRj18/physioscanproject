"""Servicio de métricas: calcula y persiste metrica_sesion al cerrar una sesión."""
from __future__ import annotations

import math
from typing import Any

from app.datos import lectura_repositorio as lr
from app.datos import sesion_repositorio as sr


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos coordenadas usando la fórmula de Haversine."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calcular_y_guardar(id_sesion: int) -> dict[str, Any]:
    """Calcula todas las métricas de la sesión y las persiste en metrica_sesion."""
    sesion = sr.buscar_por_id(id_sesion)
    if not sesion:
        return {}

    ecg_stats = lr.estadisticas_ecg(id_sesion) or {}
    gps_stats = lr.estadisticas_gps(id_sesion) or {}
    imu_stats = lr.estadisticas_imu(id_sesion) or {}

    recorrido = lr.recorrido_gps(id_sesion)
    distancia_m = 0.0
    for i in range(1, len(recorrido)):
        distancia_m += _haversine_m(
            float(recorrido[i - 1]["latitud"]),
            float(recorrido[i - 1]["longitud"]),
            float(recorrido[i]["latitud"]),
            float(recorrido[i]["longitud"]),
        )

    inicio = sesion.get("inicio")
    fin = sesion.get("fin")
    duracion_seg = None
    if inicio and fin:
        duracion_seg = int((fin - inicio).total_seconds())

    fc_prom = None
    fc_max = None
    fc_min = None
    if ecg_stats.get("total", 0):
        adc_prom = float(ecg_stats["adc_promedio"] or 0)
        adc_max  = float(ecg_stats["adc_maximo"] or 0)
        adc_min  = float(ecg_stats["adc_minimo"] or 0)
        # Conversión simplificada ADC→BPM (proxy: escala 0-4095 → 40-200 BPM)
        fc_prom = int(40 + (adc_prom / 4095) * 160)
        fc_max  = int(40 + (adc_max  / 4095) * 160)
        fc_min  = int(40 + (adc_min  / 4095) * 160)

    metrica = {
        "fc_promedio":        fc_prom,
        "fc_maxima":          fc_max,
        "fc_minima":          fc_min,
        "distancia_total_m":  round(distancia_m, 2) if distancia_m else None,
        "velocidad_max_kmh":  float(gps_stats["velocidad_max_kmh"] or 0) or None,
        "velocidad_prom_kmh": float(gps_stats["velocidad_prom_kmh"] or 0) or None,
        "duracion_seg":       duracion_seg,
        "inclinacion_max":    float(imu_stats["inclinacion_max"] or 0) or None,
        "calorias_estimadas": None,
    }

    sr.guardar_metrica(id_sesion, metrica)
    return metrica
