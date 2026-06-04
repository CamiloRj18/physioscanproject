"""Repositorio de alertas heurísticas."""
from __future__ import annotations

from typing import Any

from app.datos.base_repositorio import ejecutar, muchos


def registrar_alerta(id_sesion: int, tipo: str, severidad: str,
                     mensaje: str, capturado_en: str,
                     valor_referencia: float | None = None) -> int:
    return ejecutar(
        """
        INSERT INTO alerta (id_sesion, tipo, severidad, mensaje, valor_referencia, capturado_en)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (id_sesion, tipo, severidad, mensaje, valor_referencia, capturado_en),
    )


def listar_por_sesion(id_sesion: int) -> list[dict[str, Any]]:
    return muchos(
        """
        SELECT * FROM alerta
        WHERE id_sesion = %s
        ORDER BY capturado_en DESC
        """,
        (id_sesion,),
    )


def reconocer(id_alerta: int) -> None:
    ejecutar(
        "UPDATE alerta SET reconocida = TRUE WHERE id_alerta = %s",
        (id_alerta,),
    )
