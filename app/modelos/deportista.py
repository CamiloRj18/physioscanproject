"""DTO para deportista (subtipo 1:1 de usuario)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Deportista:
    id_deportista: int
    creado_en: datetime
    id_usuario: Optional[int] = None
    documento: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[str] = None
    altura_cm: Optional[int] = None
    peso_kg: Optional[Decimal] = None
    deporte: Optional[str] = None
    categoria: Optional[str] = None
    fc_max_estimada: Optional[int] = None
    fc_reposo: Optional[int] = None
