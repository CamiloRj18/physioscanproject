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


# ── Admin: listado paginado y filtros ────────────────────────────────────────

def listar_paginado(
    pagina: int = 1,
    por_pagina: int = 20,
    nombre_rol: str | None = None,
    estado: str | None = None,
    busqueda: str | None = None,
) -> list[dict[str, Any]]:
    condiciones: list[str] = []
    params: list[Any] = []
    if nombre_rol:
        condiciones.append("r.nombre = %s")
        params.append(nombre_rol)
    if estado:
        condiciones.append("u.estado = %s")
        params.append(estado)
    if busqueda:
        condiciones.append("(u.email LIKE %s OR u.primer_nombre LIKE %s OR u.primer_apellido LIKE %s)")
        params += [f"%{busqueda}%", f"%{busqueda}%", f"%{busqueda}%"]
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    offset = (pagina - 1) * por_pagina
    params += [por_pagina, offset]
    from app.datos.base_repositorio import muchos
    return muchos(
        f"{_SQL_SELECT} {where} ORDER BY u.fecha_creacion DESC LIMIT %s OFFSET %s",
        tuple(params),
    )


def contar_total(
    nombre_rol: str | None = None,
    estado: str | None = None,
    busqueda: str | None = None,
) -> int:
    condiciones: list[str] = []
    params: list[Any] = []
    if nombre_rol:
        condiciones.append("r.nombre = %s")
        params.append(nombre_rol)
    if estado:
        condiciones.append("u.estado = %s")
        params.append(estado)
    if busqueda:
        condiciones.append("(u.email LIKE %s OR u.primer_nombre LIKE %s OR u.primer_apellido LIKE %s)")
        params += [f"%{busqueda}%", f"%{busqueda}%", f"%{busqueda}%"]
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    from app.datos.base_repositorio import uno as _uno
    fila = _uno(
        f"""
        SELECT COUNT(*) AS total
        FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
        {where}
        """,
        tuple(params),
    )
    return int(fila["total"]) if fila else 0


def buscar_todos_por_rol(nombre_rol: str) -> list[dict[str, Any]]:
    from app.datos.base_repositorio import muchos
    return muchos(
        _SQL_SELECT + " WHERE r.nombre = %s ORDER BY u.primer_apellido, u.primer_nombre",
        (nombre_rol,),
    )


def listar_roles() -> list[dict[str, Any]]:
    from app.datos.base_repositorio import muchos
    return muchos("SELECT * FROM rol ORDER BY id_rol", ())


def crear_con_rol(
    primer_nombre: str,
    segundo_nombre: str | None,
    primer_apellido: str,
    segundo_apellido: str | None,
    email: str,
    telefono: str | None,
    id_rol: int,
    hash_contrasena: str,
) -> int:
    from app.datos.base_repositorio import transaccion
    with transaccion() as (conn, cur):
        cur.execute(
            """
            INSERT INTO usuario
                (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
                 email, telefono, id_rol, estado, email_verificado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'activo', TRUE)
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
    return id_usuario


def actualizar_datos_basicos(
    id_usuario: int,
    primer_nombre: str,
    segundo_nombre: str | None,
    primer_apellido: str,
    segundo_apellido: str | None,
    telefono: str | None,
    id_rol: int,
) -> None:
    ejecutar(
        """
        UPDATE usuario
        SET primer_nombre=%s, segundo_nombre=%s, primer_apellido=%s, segundo_apellido=%s,
            telefono=%s, id_rol=%s
        WHERE id_usuario=%s
        """,
        (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
         telefono, id_rol, id_usuario),
    )


def actualizar_datos_personales(
    id_usuario: int,
    primer_nombre: str,
    segundo_nombre: str | None,
    primer_apellido: str,
    segundo_apellido: str | None,
    telefono: str | None,
) -> None:
    ejecutar(
        """
        UPDATE usuario
        SET primer_nombre=%s, segundo_nombre=%s, primer_apellido=%s, segundo_apellido=%s,
            telefono=%s
        WHERE id_usuario=%s
        """,
        (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
         telefono, id_usuario),
    )


def actualizar_rol(id_usuario: int, id_rol: int) -> None:
    ejecutar(
        "UPDATE usuario SET id_rol=%s WHERE id_usuario=%s",
        (id_rol, id_usuario),
    )
