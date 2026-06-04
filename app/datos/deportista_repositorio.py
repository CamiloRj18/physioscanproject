"""Repositorio de deportista: CRUD + asignaciones entrenador."""
from __future__ import annotations

from typing import Any

from app.datos.base_repositorio import ejecutar, muchos, transaccion, uno


def buscar_por_id(id_deportista: int) -> dict[str, Any] | None:
    return uno(
        """
        SELECT d.*, u.primer_nombre, u.primer_apellido, u.email, u.codigo_usuario
        FROM deportista d
        LEFT JOIN usuario u ON u.id_usuario = d.id_usuario
        WHERE d.id_deportista = %s
        """,
        (id_deportista,),
    )


def buscar_por_id_usuario(id_usuario: int) -> dict[str, Any] | None:
    return uno(
        "SELECT * FROM deportista WHERE id_usuario = %s",
        (id_usuario,),
    )


def crear(id_usuario: int) -> int:
    return ejecutar(
        "INSERT INTO deportista (id_usuario) VALUES (%s)",
        (id_usuario,),
    )


def actualizar_perfil(
    id_deportista: int,
    fecha_nacimiento: str | None,
    sexo: str | None,
    altura_cm: int | None,
    peso_kg: float | None,
    deporte: str | None,
    categoria: str | None,
    fc_max_estimada: int | None,
    fc_reposo: int | None,
) -> None:
    ejecutar(
        """
        UPDATE deportista
        SET fecha_nacimiento=%s, sexo=%s, altura_cm=%s, peso_kg=%s,
            deporte=%s, categoria=%s, fc_max_estimada=%s, fc_reposo=%s
        WHERE id_deportista=%s
        """,
        (fecha_nacimiento, sexo, altura_cm, peso_kg,
         deporte, categoria, fc_max_estimada, fc_reposo, id_deportista),
    )


def listar_todos() -> list[dict[str, Any]]:
    return muchos(
        """
        SELECT d.*, u.primer_nombre, u.primer_apellido, u.email, u.codigo_usuario, u.estado
        FROM deportista d
        LEFT JOIN usuario u ON u.id_usuario = d.id_usuario
        ORDER BY u.primer_apellido, u.primer_nombre
        """,
        (),
    )


# ── Asignaciones entrenador ↔ deportista ─────────────────────────────────────

def listar_asignaciones_entrenador(id_entrenador: int) -> list[dict[str, Any]]:
    return muchos(
        """
        SELECT ae.*, d.id_deportista,
               u.primer_nombre, u.primer_apellido, u.email, u.codigo_usuario
        FROM asignacion_entrenador ae
        JOIN deportista d ON d.id_deportista = ae.id_deportista
        LEFT JOIN usuario u ON u.id_usuario = d.id_usuario
        WHERE ae.id_entrenador = %s AND ae.activo = TRUE
        ORDER BY u.primer_apellido, u.primer_nombre
        """,
        (id_entrenador,),
    )


def buscar_asignacion(id_entrenador: int, id_deportista: int) -> dict[str, Any] | None:
    return uno(
        """
        SELECT * FROM asignacion_entrenador
        WHERE id_entrenador = %s AND id_deportista = %s AND activo = TRUE
        """,
        (id_entrenador, id_deportista),
    )


def crear_asignacion(id_entrenador: int, id_deportista: int) -> int:
    return ejecutar(
        """
        INSERT INTO asignacion_entrenador (id_entrenador, id_deportista, activo)
        VALUES (%s, %s, TRUE)
        ON DUPLICATE KEY UPDATE activo = TRUE, fecha_asignacion = NOW()
        """,
        (id_entrenador, id_deportista),
    )


def eliminar_asignacion(id_asignacion: int) -> None:
    ejecutar(
        "UPDATE asignacion_entrenador SET activo = FALSE WHERE id_asignacion = %s",
        (id_asignacion,),
    )


def listar_todas_asignaciones() -> list[dict[str, Any]]:
    return muchos(
        """
        SELECT ae.*,
               ue.primer_nombre AS entrenador_nombre, ue.primer_apellido AS entrenador_apellido,
               ue.email AS entrenador_email,
               ud.primer_nombre AS deportista_nombre, ud.primer_apellido AS deportista_apellido,
               ud.email AS deportista_email
        FROM asignacion_entrenador ae
        JOIN usuario ue ON ue.id_usuario = ae.id_entrenador
        JOIN deportista d ON d.id_deportista = ae.id_deportista
        LEFT JOIN usuario ud ON ud.id_usuario = d.id_usuario
        WHERE ae.activo = TRUE
        ORDER BY ue.primer_apellido, ud.primer_apellido
        """,
        (),
    )
