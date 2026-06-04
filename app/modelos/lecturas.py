"""DTOs para las tres familias de lecturas del chaleco (ECG, GPS, IMU)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class LecturaEcg:
    id_lectura: int
    id_sesion: int
    capturado_en: datetime
    valor_adc: int
    bpm: Optional[int] = None
    electrodo_suelto: bool = False


@dataclass
class LecturaGps:
    id_lectura: int
    id_sesion: int
    capturado_en: datetime
    latitud: Decimal
    longitud: Decimal
    velocidad_kmh: Optional[Decimal] = None
    altitud_m: Optional[Decimal] = None
    satelites: Optional[int] = None
    hdop: Optional[Decimal] = None


@dataclass
class LecturaImu:
    id_lectura: int
    id_sesion: int
    capturado_en: datetime
    accel_x: int
    accel_y: int
    accel_z: int
    gyro_x: int
    gyro_y: int
    gyro_z: int
    inclinacion_grados: Optional[Decimal] = None
