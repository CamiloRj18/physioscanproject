"""Repositorio de usuario: CRUD parametrizado + mapeo fila → dict.

Todas las consultas incluyen JOIN con rol para exponer nombre_rol,
lo que permite que UsuarioProxy / @rol_requerido funcionen sin lógica SQL.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.datos.base_repositorio import ejecutar, transaccion, uno


_SQL_SELECT = """
    SELECT u.*, r.nombre AS nombre_rol
    FROM   usuario u
    JOIN   rol r ON r.id_rol = u.id_rol
"""


def buscar_por_email(email: str) -> dict[str, Any] | None:
    return uno(_SQL_SELECT + " WHERE u.email = %s", (email.lower().strip(),))


def buscar_por_id(id_usuario: int) -> dict[str, Any] | None:
    return uno(_SQL_SELECT + " WHERE u.id_usuario = %s", (id_usuario,))


def buscar_rol_por_nombre(nombre: str) -> dict[str, Any] | None:
    return uno("SELECT * FROM rol WHERE nombre = %s", (nombre,))


def crear_completo(
    primer_nombre: str,
    segundo_nombre: str | None,
    primer_apellido: str,
    segundo_apellido: str | None,
    email: str,
    telefono: str | None,
    id_rol: int,
    hash_contrasena: str,
    token_hash: str,
    token_expira: datetime,
    ip_solicitud: str | None,
    hashes_codigos: list[str],
) -> tuple[int, int]:
    """Crea usuario + credencial + historial + token verificación + lote + 12 códigos.

    Toda la operación ocurre en una única transacción.
    Returns: (id_usuario, id_lote)
    """
    with transaccion() as (conn, cur):
        cur.execute(
            """
            INSERT INTO usuario
                (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
                 email, telefono, id_rol, estado, email_verificado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendiente_verificacion', FALSE)
            """,
            (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
             email, telefono, id_rol),
        )
        id_usuario = cur.lastrowid

        cur.execute(
            "INSERT INTO credencial (id_usuario, hash_contrasena, algoritmo) VALUES (%s, %s, 'argon2id')",
            (id_usuario, hash_contrasena),
        )

        cur.execute(
            "INSERT INTO historial_contrasena (id_usuario, hash_contrasena) VALUES (%s, %s)",
            (id_usuario, hash_contrasena),
        )

        cur.execute(
            """
            INSERT INTO token_recuperacion (id_usuario, token_hash, tipo, expira_en, ip_solicitud)
            VALUES (%s, %s, 'verificacion_email', %s, %s)
            """,
            (id_usuario, token_hash, token_expira, ip_solicitud),
        )

        cur.execute(
            "INSERT INTO lote_recuperacion (id_usuario, numero_lote, total_codigos, activo) VALUES (%s, 1, 12, TRUE)",
            (id_usuario,),
        )
        id_lote = cur.lastrowid

        for orden, h in enumerate(hashes_codigos, 1):
            cur.execute(
                "INSERT INTO codigo_recuperacion_archivo (id_lote, orden, codigo_hash) VALUES (%s, %s, %s)",
                (id_lote, orden, h),
            )

    return id_usuario, id_lote


def actualizar_estado(id_usuario: int, estado: str) -> None:
    ejecutar("UPDATE usuario SET estado = %s WHERE id_usuario = %s", (estado, id_usuario))


def marcar_email_verificado(id_usuario: int) -> None:
    ejecutar(
        "UPDATE usuario SET email_verificado = TRUE, estado = 'activo' WHERE id_usuario = %s",
        (id_usuario,),
    )


def incrementar_intentos(id_usuario: int) -> None:
    ejecutar(
        "UPDATE usuario SET intentos_fallidos = intentos_fallidos + 1 WHERE id_usuario = %s",
        (id_usuario,),
    )


def reiniciar_intentos(id_usuario: int) -> None:
    ejecutar(
        "UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id_usuario = %s",
        (id_usuario,),
    )


def bloquear(id_usuario: int, bloqueado_hasta: datetime) -> None:
    ejecutar(
        "UPDATE usuario SET estado = 'bloqueado', bloqueado_hasta = %s WHERE id_usuario = %s",
        (bloqueado_hasta, id_usuario),
    )


def actualizar_ultimo_acceso(id_usuario: int) -> None:
    ejecutar(
        "UPDATE usuario SET ultimo_acceso = NOW(), intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id_usuario = %s",
        (id_usuario,),
    )
