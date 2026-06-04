#!/usr/bin/env python3
"""Crea la base de datos physioscan ejecutando los 4 scripts SQL en orden.

Lee DB_HOST, DB_PORT y DB_ROOT_PASSWORD desde el archivo .env de la raíz.
Requiere XAMPP con MySQL activo en el puerto configurado.

Uso:
    python scripts/crear_bd.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

# .env está en la raíz del proyecto, un nivel arriba de scripts/
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_HOST          = os.environ.get("DB_HOST", "localhost")
DB_PORT          = int(os.environ.get("DB_PORT", "3306"))
DB_ROOT_PASSWORD = os.environ.get("DB_ROOT_PASSWORD", "")

SQL_FILES = [
    "database/01_schema.sql",
    "database/02_triggers.sql",
    "database/03_seed.sql",
    "database/04_vistas.sql",
]

_DELIMITER_RE = re.compile(r"^DELIMITER\s+(\S+)\s*$", re.IGNORECASE)


def split_statements(content: str) -> list[str]:
    """Divide SQL en sentencias individuales manejando DELIMITER para triggers.

    - Ignora líneas de comentario (--) y líneas vacías.
    - Cambia el delimitador activo al encontrar una directiva DELIMITER.
    - Acumula líneas hasta que el buffer termina con el delimitador activo.
    """
    delimiter = ";"
    buffer = ""
    statements: list[str] = []

    for line in content.splitlines(keepends=True):
        stripped = line.strip()

        # Ignorar líneas vacías y comentarios de línea completa
        if not stripped or stripped.startswith("--"):
            continue

        # Detectar directiva DELIMITER (cliente MySQL, no SQL)
        m = _DELIMITER_RE.match(stripped)
        if m:
            pending = buffer.strip()
            if pending:
                statements.append(pending)
            buffer = ""
            delimiter = m.group(1)
            continue

        buffer += line

        # Sentencia completa cuando el buffer acumulado termina con el delimitador
        if buffer.rstrip().endswith(delimiter):
            stmt = buffer.rstrip()[: -len(delimiter)].strip()
            if stmt:
                statements.append(stmt)
            buffer = ""

    # Procesar cualquier resto (archivo sin punto y coma final)
    remaining = buffer.strip()
    if remaining:
        statements.append(remaining)

    return statements


def run_sql_file(cursor: mysql.connector.cursor.MySQLCursor, filepath: Path) -> None:
    content = filepath.read_text(encoding="utf-8")
    for stmt in split_statements(content):
        cursor.execute(stmt)


def main() -> None:
    # Conectar como root sin seleccionar BD (el propio SQL la crea)
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user="root",
            password=DB_ROOT_PASSWORD,
            charset="utf8mb4",
            autocommit=True,
            connection_timeout=10,
        )
    except mysql.connector.Error as exc:
        print(f"ERROR al conectar a MySQL ({DB_HOST}:{DB_PORT}): {exc}")
        print("Verifica que XAMPP MySQL esté activo y que DB_ROOT_PASSWORD sea correcto en .env")
        sys.exit(1)

    try:
        cursor = conn.cursor()
        for rel_path in SQL_FILES:
            filepath = ROOT / rel_path
            try:
                run_sql_file(cursor, filepath)
                print(f"OK: {rel_path}")
            except mysql.connector.Error as exc:
                print(f"ERROR en {rel_path} — código {exc.errno}: {exc.msg}")
                if exc.errno == 1050:  # Table already exists
                    print("  → La BD ya existe. Ejecuta DROP DATABASE physioscan; en phpMyAdmin y vuelve a intentar.")
                elif exc.errno == 1007:  # DB already exists (sin IF NOT EXISTS)
                    print("  → La BD ya existe (sin IF NOT EXISTS). Revisa el SQL.")
                sys.exit(1)
        cursor.close()
    finally:
        conn.close()

    print("\n✓ Base de datos physioscan creada correctamente.")
    print("  Siguiente paso: crear el usuario app (ver docs/INSTALL_DB.md).")


if __name__ == "__main__":
    main()
