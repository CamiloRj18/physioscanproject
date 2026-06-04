"""DTOs para usuario y rol. Sin lógica de negocio ni SQL."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Rol:
    id_rol: int
    nombre: str
    descripcion: Optional[str] = None


@dataclass
class Usuario:
    id_usuario: int
    primer_nombre: str
    primer_apellido: str
    email: str
    id_rol: int
    estado: str
    email_verificado: bool
    intentos_fallidos: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    codigo_usuario: Optional[str] = None
    segundo_nombre: Optional[str] = None
    segundo_apellido: Optional[str] = None
    telefono: Optional[str] = None
    bloqueado_hasta: Optional[datetime] = None
    ultimo_acceso: Optional[datetime] = None
