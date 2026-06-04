"""Servicio de auditoría: registro append-only de eventos de seguridad."""
from __future__ import annotations

from app.datos.seguridad_repositorio import registrar_auditoria


def registrar(
    accion: str,
    id_usuario: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    detalle: dict | None = None,
    entidad: str | None = None,
    id_entidad: str | None = None,
) -> None:
    """Registra un evento en la bitácora de auditoría.

    No lanza excepciones: una falla de auditoría no debe interrumpir el flujo principal.
    """
    try:
        registrar_auditoria(id_usuario, accion, entidad, id_entidad, ip, user_agent, detalle)
    except Exception:
        pass
