"""Repositorio de dispositivo: alta, consulta, asignación y sensores."""
from __future__ import annotations

from typing import Any

from app.datos.base_repositorio import ejecutar, muchos, transaccion, uno


def buscar_por_codigo(codigo_dispositivo: str) -> dict[str, Any] | None:
    return uno(
        """
        SELECT d.*, dep.id_deportista AS dep_id,
               u.primer_nombre, u.primer_apellido, u.codigo_usuario
        FROM dispositivo d
        LEFT JOIN deportista dep ON dep.id_deportista = d.id_deportista
        LEFT JOIN usuario u ON u.id_usuario = dep.id_usuario
        WHERE d.codigo_dispositivo = %s
        """,
        (codigo_dispositivo,),
    )


def buscar_por_id(id_dispositivo: int) -> dict[str, Any] | None:
    return uno(
        """
        SELECT d.*,
               u.primer_nombre, u.primer_apellido, u.codigo_usuario
        FROM dispositivo d
        LEFT JOIN deportista dep ON dep.id_deportista = d.id_deportista
        LEFT JOIN usuario u ON u.id_usuario = dep.id_usuario
        WHERE d.id_dispositivo = %s
        """,
        (id_dispositivo,),
    )


def listar_todos() -> list[dict[str, Any]]:
    return muchos(
        """
        SELECT d.id_dispositivo, d.codigo_dispositivo, d.nombre, d.mac,
               d.estado, d.firmware_version, d.creado_en, d.id_deportista,
               u.primer_nombre, u.primer_apellido, u.codigo_usuario
        FROM dispositivo d
        LEFT JOIN deportista dep ON dep.id_deportista = d.id_deportista
        LEFT JOIN usuario u ON u.id_usuario = dep.id_usuario
        ORDER BY d.creado_en DESC
        """,
        (),
    )


def registrar(nombre: str, api_key_hash: str, mac: str | None = None) -> dict[str, Any]:
    """Inserta un dispositivo. El trigger genera codigo_dispositivo.

    Devuelve dict con id_dispositivo y codigo_dispositivo generado.
    """
    with transaccion() as (conn, cur):
        cur.execute(
            """
            INSERT INTO dispositivo (nombre, api_key_hash, mac)
            VALUES (%s, %s, %s)
            """,
            (nombre, api_key_hash, mac),
        )
        id_disp = cur.lastrowid
        cur.execute(
            "SELECT codigo_dispositivo FROM dispositivo WHERE id_dispositivo = %s",
            (id_disp,),
        )
        fila = cur.fetchone()
    return {"id_dispositivo": id_disp, "codigo_dispositivo": fila["codigo_dispositivo"]}


def asignar_deportista(id_dispositivo: int, id_deportista: int | None) -> None:
    ejecutar(
        "UPDATE dispositivo SET id_deportista = %s WHERE id_dispositivo = %s",
        (id_deportista, id_dispositivo),
    )


def registrar_sensores(id_dispositivo: int, sensores: list[dict]) -> None:
    """Inserta los sensores de un dispositivo (reemplaza los existentes).

    sensores = [{"id_tipo_sensor": int, "modelo": str, "config_pines": str}, ...]
    """
    ejecutar(
        "DELETE FROM sensor WHERE id_dispositivo = %s",
        (id_dispositivo,),
    )
    with transaccion() as (conn, cur):
        for s in sensores:
            cur.execute(
                """
                INSERT INTO sensor (id_dispositivo, id_tipo_sensor, modelo, config_pines)
                VALUES (%s, %s, %s, %s)
                """,
                (id_dispositivo, s["id_tipo_sensor"], s["modelo"], s.get("config_pines")),
            )


def listar_sensores(id_dispositivo: int) -> list[dict[str, Any]]:
    return muchos(
        """
        SELECT s.*, ts.codigo AS tipo_codigo, ts.nombre AS tipo_nombre
        FROM sensor s
        JOIN tipo_sensor ts ON ts.id_tipo_sensor = s.id_tipo_sensor
        WHERE s.id_dispositivo = %s
        ORDER BY ts.codigo
        """,
        (id_dispositivo,),
    )


def buscar_por_id_deportista(id_deportista: int) -> dict[str, Any] | None:
    """Devuelve el dispositivo activo asignado al deportista, o None."""
    return uno(
        """
        SELECT id_dispositivo, codigo_dispositivo, nombre, estado
        FROM dispositivo
        WHERE id_deportista = %s AND estado = 'activo'
        LIMIT 1
        """,
        (id_deportista,),
    )


def actualizar_estado(id_dispositivo: int, estado: str) -> None:
    ejecutar(
        "UPDATE dispositivo SET estado = %s WHERE id_dispositivo = %s",
        (estado, id_dispositivo),
    )
