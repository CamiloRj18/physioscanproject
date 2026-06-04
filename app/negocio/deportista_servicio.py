"""Servicio de deportista: creación, actualización de perfil, consulta."""
from __future__ import annotations

from typing import Any

from app.comun.errores import ConflictoError, ValidacionError
from app.datos import deportista_repositorio as dr
from app.datos import usuario_repositorio as ur
from app.negocio.seguridad.auditoria_servicio import registrar as audit


def completar_perfil(
    id_usuario: int,
    fecha_nacimiento: str | None,
    sexo: str | None,
    altura_cm: int | None,
    peso_kg: float | None,
    deporte: str | None,
    categoria: str | None,
    ip: str | None = None,
) -> int:
    """Crea el registro deportista y sube el rol a 'deportista'.

    Idempotente: si ya existe el deportista, sólo actualiza el perfil y el rol.
    Returns: id_deportista
    """
    existente = dr.buscar_por_id_usuario(id_usuario)
    if existente:
        id_deportista = existente["id_deportista"]
    else:
        id_deportista = dr.crear(id_usuario)

    dr.actualizar_perfil(
        id_deportista=id_deportista,
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo,
        altura_cm=altura_cm,
        peso_kg=peso_kg,
        deporte=deporte,
        categoria=categoria,
        fc_max_estimada=None,
        fc_reposo=None,
    )

    rol_deportista = ur.buscar_rol_por_nombre("deportista")
    if not rol_deportista:
        raise ValidacionError("Rol 'deportista' no configurado.")
    ur.actualizar_rol(id_usuario, rol_deportista["id_rol"])

    audit("PERFIL_DEPORTISTA_COMPLETADO", id_usuario, ip, detalle={"id_deportista": id_deportista})
    return id_deportista


def actualizar_perfil_basico(
    id_usuario: int,
    primer_nombre: str,
    segundo_nombre: str | None,
    primer_apellido: str,
    segundo_apellido: str | None,
    telefono: str | None,
    ip: str | None = None,
) -> None:
    """Actualiza datos personales del usuario sin tocar el rol."""
    ur.actualizar_datos_personales(
        id_usuario=id_usuario,
        primer_nombre=primer_nombre,
        segundo_nombre=segundo_nombre,
        primer_apellido=primer_apellido,
        segundo_apellido=segundo_apellido,
        telefono=telefono,
    )
    audit("PERFIL_BASICO_ACTUALIZADO", id_usuario, ip)


def actualizar_perfil_deportivo(
    id_usuario: int,
    fecha_nacimiento: str | None,
    sexo: str | None,
    altura_cm: int | None,
    peso_kg: float | None,
    deporte: str | None,
    categoria: str | None,
    fc_max_estimada: int | None,
    fc_reposo: int | None,
    ip: str | None = None,
) -> None:
    """Actualiza el perfil deportivo de un usuario que ya tiene registro deportista."""
    deportista = dr.buscar_por_id_usuario(id_usuario)
    if not deportista:
        raise ConflictoError("No se encontró perfil deportivo para este usuario.")
    dr.actualizar_perfil(
        id_deportista=deportista["id_deportista"],
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo,
        altura_cm=altura_cm,
        peso_kg=peso_kg,
        deporte=deporte,
        categoria=categoria,
        fc_max_estimada=fc_max_estimada,
        fc_reposo=fc_reposo,
    )
    audit("PERFIL_DEPORTIVO_ACTUALIZADO", id_usuario, ip)
