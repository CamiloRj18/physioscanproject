"""Helpers de acceso a datos compartidos por todos los repositorios.

REGLA ABSOLUTA: solo consultas parametrizadas con %s.
Jamás concatenación de SQL ni interpolación de strings en queries.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from app.datos.conexion import get_connection


def ejecutar(sql: str, params: tuple = ()) -> int:
    """Ejecuta INSERT / UPDATE / DELETE en su propia conexión auto-commit.

    Devuelve lastrowid para INSERTs; rowcount para UPDATE/DELETE.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid if cur.lastrowid else cur.rowcount
    finally:
        cur.close()
        conn.close()


def uno(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    """Ejecuta SELECT y devuelve la primera fila como dict, o None si no hay resultados."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def muchos(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Ejecuta SELECT y devuelve todas las filas como lista de dicts."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@contextmanager
def transaccion():
    """Context manager para transacciones explícitas con múltiples queries.

    Yields (conn, cur) — usar cur.execute(sql, params_tuple) con %s.
    Hace commit al salir sin excepción; rollback automático si hay error.

    Ejemplo::

        with transaccion() as (conn, cur):
            cur.execute("INSERT INTO usuario (...) VALUES (%s, %s)", (a, b))
            cur.execute("INSERT INTO credencial (...) VALUES (%s)", (h,))
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
