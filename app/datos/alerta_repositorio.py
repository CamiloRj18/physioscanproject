"""Repositorio de alertas heurísticas."""
from __future__ import annotations

from typing import Any

from app.datos.base_repositorio import ejecutar, muchos, uno


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


def listar_recientes(id_sesion: int, limite: int = 20) -> list[dict[str, Any]]:
    """Últimas N alertas no reconocidas de la sesión."""
    return muchos(
        """
        SELECT tipo, severidad, mensaje, capturado_en
        FROM alerta
        WHERE id_sesion = %s AND reconocida = FALSE
        ORDER BY capturado_en DESC
        LIMIT %s
        """,
        (id_sesion, limite),
    )


def ultima_alerta_por_tipo(id_sesion: int, tipo: str) -> dict[str, Any] | None:
    """Última alerta del tipo dado en la sesión (para control de idempotencia)."""
    return uno(
        """
        SELECT capturado_en FROM alerta
        WHERE id_sesion = %s AND tipo = %s
        ORDER BY capturado_en DESC
        LIMIT 1
        """,
        (id_sesion, tipo),
    )


def severidad_actual(id_sesion: int) -> str | None:
    """Severidad más grave entre alertas no reconocidas de la sesión."""
    row = uno(
        """
        SELECT CASE
            WHEN SUM(CASE WHEN severidad = 'rojo'     AND reconocida = FALSE THEN 1 ELSE 0 END) > 0 THEN 'rojo'
            WHEN SUM(CASE WHEN severidad = 'amarillo' AND reconocida = FALSE THEN 1 ELSE 0 END) > 0 THEN 'amarillo'
            WHEN SUM(CASE WHEN severidad = 'verde'    AND reconocida = FALSE THEN 1 ELSE 0 END) > 0 THEN 'verde'
            ELSE NULL
        END AS severidad
        FROM alerta
        WHERE id_sesion = %s
        """,
        (id_sesion,),
    )
    return row["severidad"] if row else None


def reconocer(id_alerta: int) -> None:
    ejecutar(
        "UPDATE alerta SET reconocida = TRUE WHERE id_alerta = %s",
        (id_alerta,),
    )
