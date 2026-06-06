"""Servicio de métricas: calcula y persiste metrica_sesion al cerrar una sesión."""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from app.datos import deportista_repositorio as deprep
from app.datos import lectura_repositorio as lr
from app.datos import sesion_repositorio as sr

# Sesiones de más de 5 h tienen timestamps incorrectos (datos de prueba, errores de hardware).
# No calcular calorías en ese caso para evitar valores absurdos.
_MAX_DURACION_SEG = 18_000


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos coordenadas (fórmula de Haversine)."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _calorias(fc_prom: float, duracion_seg: int,
              deportista: dict[str, Any] | None) -> float | None:
    """Estimación calórica. Usa fórmula Keytel (2005) si hay datos demográficos."""
    if not fc_prom or not duracion_seg or duracion_seg <= 0:
        return None
    if duracion_seg > _MAX_DURACION_SEG:
        return None
    dur_min = duracion_seg / 60.0
    if deportista:
        peso_kg = float(deportista.get("peso_kg") or 0)
        sexo = deportista.get("sexo")
        fecha_nac = deportista.get("fecha_nacimiento")
        edad: int | None = None
        if isinstance(fecha_nac, date):
            edad = (date.today() - fecha_nac).days // 365
        if peso_kg and edad:
            if sexo == "M":
                cal_min = (-55.0969 + 0.6309 * fc_prom + 0.1988 * peso_kg + 0.2017 * edad) / 4.184
            elif sexo == "F":
                cal_min = (-20.4022 + 0.4472 * fc_prom - 0.1263 * peso_kg + 0.074 * edad) / 4.184
            else:
                m = (-55.0969 + 0.6309 * fc_prom + 0.1988 * peso_kg + 0.2017 * edad) / 4.184
                f = (-20.4022 + 0.4472 * fc_prom - 0.1263 * peso_kg + 0.074 * edad) / 4.184
                cal_min = (m + f) / 2.0
            return round(max(0.0, cal_min * dur_min), 2)
        if peso_kg:
            # Sin edad: MET ~8 (trote), fórmula simplificada
            return round(8.0 * peso_kg * (duracion_seg / 3600.0), 2)
    # Sin datos demográficos: proxy solo HR+tiempo
    return round(max(0.0, dur_min * (fc_prom - 55.0) * 0.15), 2)


def calcular_metricas(id_sesion: int) -> dict[str, Any]:
    """Calcula todas las métricas de la sesión y las persiste en metrica_sesion.

    Returns el diccionario de métricas calculadas (vacío si la sesión no existe).
    """
    sesion = sr.buscar_por_id(id_sesion)
    if not sesion:
        return {}

    deportista: dict[str, Any] | None = None
    if sesion.get("id_deportista"):
        try:
            deportista = deprep.buscar_por_id(sesion["id_deportista"])
        except Exception:
            pass

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
    duracion_seg: int | None = None
    if inicio and fin:
        duracion_seg = int((fin - inicio).total_seconds())

    fc_prom: int | None = None
    fc_max: int | None = None
    fc_min: int | None = None
    if ecg_stats.get("total", 0):
        fc_prom = int(float(ecg_stats["fc_promedio"] or 0))
        fc_max  = int(float(ecg_stats["fc_maxima"]   or 0))
        fc_min  = int(float(ecg_stats["fc_minima"]   or 0))

    metrica: dict[str, Any] = {
        "fc_promedio":        fc_prom,
        "fc_maxima":          fc_max,
        "fc_minima":          fc_min,
        "distancia_total_m":  round(distancia_m, 2) if distancia_m else None,
        "velocidad_max_kmh":  float(gps_stats["velocidad_max_kmh"] or 0) or None,
        "velocidad_prom_kmh": float(gps_stats["velocidad_prom_kmh"] or 0) or None,
        "duracion_seg":       duracion_seg,
        "inclinacion_max":    float(imu_stats["inclinacion_max"] or 0) or None,
        "calorias_estimadas": _calorias(fc_prom, duracion_seg, deportista) if fc_prom else None,
    }

    sr.guardar_metrica(id_sesion, metrica)
    return metrica


# Alias para compatibilidad con ingesta_servicio
calcular_y_guardar = calcular_metricas
