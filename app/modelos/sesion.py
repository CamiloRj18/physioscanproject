"""DTOs para sesión de entrenamiento y métricas derivadas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class SesionEntrenamiento:
    id_sesion: int
    id_deportista: int
    inicio: datetime
    estado: str
    id_dispositivo: Optional[int] = None
    titulo: Optional[str] = None
    notas: Optional[str] = None
    fin: Optional[datetime] = None


@dataclass
class MetricaSesion:
    id_sesion: int
    recalculado_en: datetime
    fc_promedio: Optional[int] = None
    fc_maxima: Optional[int] = None
    fc_minima: Optional[int] = None
    distancia_total_m: Optional[Decimal] = None
    velocidad_max_kmh: Optional[Decimal] = None
    velocidad_prom_kmh: Optional[Decimal] = None
    duracion_seg: Optional[int] = None
    inclinacion_max: Optional[Decimal] = None
    calorias_estimadas: Optional[Decimal] = None
