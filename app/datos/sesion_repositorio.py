"""Repositorio de sesión de entrenamiento y métricas."""
from __future__ import annotations

from typing import Any

from app.datos.base_repositorio import ejecutar, muchos, transaccion, uno


def crear_sesion(id_deportista: int, id_dispositivo: int | None = None,
                 titulo: str | None = None) -> dict[str, Any]:
    """Crea una sesión en_curso y devuelve id_sesion + inicio."""
    with transaccion() as (conn, cur):
        cur.execute(
            """
            INSERT INTO sesion_entrenamiento (id_deportista, id_dispositivo, titulo)
            VALUES (%s, %s, %s)
            """,
            (id_deportista, id_dispositivo, titulo),
        )
        id_sesion = cur.lastrowid
        cur.execute(
            "SELECT id_sesion, inicio, estado FROM sesion_entrenamiento WHERE id_sesion = %s",
            (id_sesion,),
        )
        fila = cur.fetchone()
    return fila


def finalizar_sesion(id_sesion: int) -> None:
    ejecutar(
        """
        UPDATE sesion_entrenamiento
           SET estado = 'finalizada', fin = NOW()
         WHERE id_sesion = %s AND estado = 'en_curso'
        """,
        (id_sesion,),
    )


def buscar_por_id(id_sesion: int) -> dict[str, Any] | None:
    return uno(
        """
        SELECT se.*, d.id_deportista, disp.codigo_dispositivo
        FROM sesion_entrenamiento se
        JOIN deportista d ON d.id_deportista = se.id_deportista
        LEFT JOIN dispositivo disp ON disp.id_dispositivo = se.id_dispositivo
        WHERE se.id_sesion = %s
        """,
        (id_sesion,),
    )


def listar_por_deportista(id_deportista: int) -> list[dict[str, Any]]:
    return muchos(
        """
        SELECT se.id_sesion, se.titulo, se.inicio, se.fin, se.estado,
               disp.codigo_dispositivo
        FROM sesion_entrenamiento se
        LEFT JOIN dispositivo disp ON disp.id_dispositivo = se.id_dispositivo
        WHERE se.id_deportista = %s
        ORDER BY se.inicio DESC
        """,
        (id_deportista,),
    )


def guardar_metrica(id_sesion: int, m: dict[str, Any]) -> None:
    """INSERT OR UPDATE en metrica_sesion (ON DUPLICATE KEY UPDATE)."""
    ejecutar(
        """
        INSERT INTO metrica_sesion
            (id_sesion, fc_promedio, fc_maxima, fc_minima,
             distancia_total_m, velocidad_max_kmh, velocidad_prom_kmh,
             duracion_seg, inclinacion_max, calorias_estimadas, recalculado_en)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            fc_promedio        = VALUES(fc_promedio),
            fc_maxima          = VALUES(fc_maxima),
            fc_minima          = VALUES(fc_minima),
            distancia_total_m  = VALUES(distancia_total_m),
            velocidad_max_kmh  = VALUES(velocidad_max_kmh),
            velocidad_prom_kmh = VALUES(velocidad_prom_kmh),
            duracion_seg       = VALUES(duracion_seg),
            inclinacion_max    = VALUES(inclinacion_max),
            calorias_estimadas = VALUES(calorias_estimadas),
            recalculado_en     = NOW()
        """,
        (
            id_sesion,
            m.get("fc_promedio"),
            m.get("fc_maxima"),
            m.get("fc_minima"),
            m.get("distancia_total_m"),
            m.get("velocidad_max_kmh"),
            m.get("velocidad_prom_kmh"),
            m.get("duracion_seg"),
            m.get("inclinacion_max"),
            m.get("calorias_estimadas"),
        ),
    )


def obtener_metrica(id_sesion: int) -> dict[str, Any] | None:
    return uno(
        "SELECT * FROM metrica_sesion WHERE id_sesion = %s",
        (id_sesion,),
    )
