"""Repositorio de lecturas: INSERT por lotes (executemany) para ECG, GPS e IMU."""
from __future__ import annotations

from typing import Any

from app.datos.base_repositorio import muchos, transaccion, uno


def insertar_lote_ecg(id_sesion: int, lecturas: list[dict]) -> int:
    """Inserta múltiples lecturas ECG en una sola transacción.

    lecturas = [{"capturado_en": str, "valor_adc": int, "electrodo_suelto": bool}, ...]
    Devuelve cantidad de filas insertadas.
    """
    if not lecturas:
        return 0
    sql = """
        INSERT INTO lectura_ecg (id_sesion, capturado_en, valor_adc, electrodo_suelto)
        VALUES (%s, %s, %s, %s)
    """
    params = [
        (id_sesion, r["capturado_en"], r["valor_adc"], bool(r.get("electrodo_suelto", False)))
        for r in lecturas
    ]
    with transaccion() as (conn, cur):
        cur.executemany(sql, params)
        return cur.rowcount


def insertar_lote_gps(id_sesion: int, lecturas: list[dict]) -> int:
    """Inserta múltiples lecturas GPS. Devuelve cantidad insertada."""
    if not lecturas:
        return 0
    sql = """
        INSERT INTO lectura_gps (id_sesion, capturado_en, latitud, longitud,
                                 velocidad_kmh, satelites)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = [
        (
            id_sesion,
            r["capturado_en"],
            r["latitud"],
            r["longitud"],
            r.get("velocidad_kmh"),
            r.get("satelites"),
        )
        for r in lecturas
    ]
    with transaccion() as (conn, cur):
        cur.executemany(sql, params)
        return cur.rowcount


def insertar_lote_imu(id_sesion: int, lecturas: list[dict]) -> int:
    """Inserta múltiples lecturas IMU. Devuelve cantidad insertada."""
    if not lecturas:
        return 0
    sql = """
        INSERT INTO lectura_imu (id_sesion, capturado_en,
                                 accel_x, accel_y, accel_z,
                                 gyro_x, gyro_y, gyro_z,
                                 inclinacion_grados)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = [
        (
            id_sesion,
            r["capturado_en"],
            r["accel_x"],
            r["accel_y"],
            r["accel_z"],
            r["gyro_x"],
            r["gyro_y"],
            r["gyro_z"],
            r.get("inclinacion_grados"),
        )
        for r in lecturas
    ]
    with transaccion() as (conn, cur):
        cur.executemany(sql, params)
        return cur.rowcount


def ultima_lectura_ecg(id_sesion: int) -> dict[str, Any] | None:
    return uno(
        """
        SELECT * FROM lectura_ecg
        WHERE id_sesion = %s
        ORDER BY capturado_en DESC
        LIMIT 1
        """,
        (id_sesion,),
    )


def recorrido_gps(id_sesion: int) -> list[dict[str, Any]]:
    return muchos(
        """
        SELECT latitud, longitud, capturado_en
        FROM lectura_gps
        WHERE id_sesion = %s
        ORDER BY capturado_en
        """,
        (id_sesion,),
    )


def ultima_lectura_imu(id_sesion: int) -> dict[str, Any] | None:
    return uno(
        """
        SELECT * FROM lectura_imu
        WHERE id_sesion = %s
        ORDER BY capturado_en DESC
        LIMIT 1
        """,
        (id_sesion,),
    )


def estadisticas_ecg(id_sesion: int) -> dict[str, Any] | None:
    """Agregados de ECG: FC en BPM (usa columna bpm si existe, sino conversión ADC lineal)."""
    return uno(
        """
        SELECT
            AVG(CASE WHEN bpm IS NOT NULL THEN bpm
                     ELSE 40 + (valor_adc / 4095.0) * 160 END) AS fc_promedio,
            MAX(CASE WHEN bpm IS NOT NULL THEN bpm
                     ELSE 40 + (valor_adc / 4095.0) * 160 END) AS fc_maxima,
            MIN(CASE WHEN bpm IS NOT NULL THEN bpm
                     ELSE 40 + (valor_adc / 4095.0) * 160 END) AS fc_minima,
            COUNT(*) AS total
        FROM lectura_ecg
        WHERE id_sesion = %s
        """,
        (id_sesion,),
    )


def estadisticas_gps(id_sesion: int) -> dict[str, Any] | None:
    """Agregados de GPS: velocidades."""
    return uno(
        """
        SELECT
            MAX(velocidad_kmh) AS velocidad_max_kmh,
            AVG(velocidad_kmh) AS velocidad_prom_kmh,
            COUNT(*)           AS total
        FROM lectura_gps
        WHERE id_sesion = %s
        """,
        (id_sesion,),
    )


def estadisticas_imu(id_sesion: int) -> dict[str, Any] | None:
    """Agregados de IMU: inclinación máxima."""
    return uno(
        """
        SELECT
            MAX(inclinacion_grados) AS inclinacion_max,
            COUNT(*)                AS total
        FROM lectura_imu
        WHERE id_sesion = %s
        """,
        (id_sesion,),
    )


def serie_bpm(id_sesion: int, limite: int = 300) -> list[dict[str, Any]]:
    """Serie temporal BPM para gráfica (hasta `limite` muestras, orden cronológico)."""
    return muchos(
        """
        SELECT capturado_en,
               CAST(CASE WHEN bpm IS NOT NULL THEN bpm
                         ELSE 40 + (valor_adc / 4095.0) * 160 END AS UNSIGNED) AS bpm_calc
        FROM lectura_ecg
        WHERE id_sesion = %s
        ORDER BY capturado_en
        LIMIT %s
        """,
        (id_sesion, limite),
    )


def serie_inclinacion(id_sesion: int, limite: int = 300) -> list[dict[str, Any]]:
    """Serie temporal de inclinación IMU para gráfica."""
    return muchos(
        """
        SELECT capturado_en, inclinacion_grados
        FROM lectura_imu
        WHERE id_sesion = %s AND inclinacion_grados IS NOT NULL
        ORDER BY capturado_en
        LIMIT %s
        """,
        (id_sesion, limite),
    )


def serie_velocidad(id_sesion: int, limite: int = 200) -> list[dict[str, Any]]:
    """Serie temporal de velocidad GPS para gráfica."""
    return muchos(
        """
        SELECT capturado_en, velocidad_kmh
        FROM lectura_gps
        WHERE id_sesion = %s AND velocidad_kmh IS NOT NULL
        ORDER BY capturado_en
        LIMIT %s
        """,
        (id_sesion, limite),
    )


def recorrido_gps_reciente(id_sesion: int, limite: int = 50) -> list[dict[str, Any]]:
    """Últimas N posiciones GPS para el mini-mapa en vivo."""
    return muchos(
        """
        SELECT latitud, longitud
        FROM lectura_gps
        WHERE id_sesion = %s
        ORDER BY capturado_en DESC
        LIMIT %s
        """,
        (id_sesion, limite),
    )
