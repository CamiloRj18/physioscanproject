"""Pool de conexiones MySQL para PhysioScan.

Lee configuración exclusivamente de variables de entorno (nunca hardcodeadas).
Llamar a init_pool() en la application factory antes de atender peticiones.
"""

from __future__ import annotations

import os

import mysql.connector.pooling

_pool: mysql.connector.pooling.MySQLConnectionPool | None = None


def init_pool() -> None:
    """Inicializa el pool leyendo las variables de entorno DB_*.

    Idempotente: si el pool ya existe, no hace nada.
    """
    global _pool
    if _pool is not None:
        return

    dbconfig = {
        "host":     os.environ["DB_HOST"],
        "port":     int(os.environ.get("DB_PORT", "3306")),
        "database": os.environ["DB_NAME"],
        "user":     os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "charset":  "utf8mb4",
        "time_zone": "+00:00",
        "autocommit": False,
    }
    pool_size = int(os.environ.get("DB_POOL_SIZE", "5"))
    _pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="physioscan_pool",
        pool_size=pool_size,
        pool_reset_session=True,
        **dbconfig,
    )


def get_connection() -> mysql.connector.pooling.PooledMySQLConnection:
    """Devuelve una conexión del pool. Llama a init_pool() si todavía no existe."""
    if _pool is None:
        init_pool()
    return _pool.get_connection()  # type: ignore[union-attr]
