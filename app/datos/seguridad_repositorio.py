"""Repositorio de seguridad: credencial, 2FA, tokens, sesiones, auditoría."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.datos.base_repositorio import ejecutar, muchos, uno


# ── Credencial ──────────────────────────────────────────────────────────────

def obtener_credencial(id_usuario: int) -> dict[str, Any] | None:
    return uno("SELECT * FROM credencial WHERE id_usuario = %s", (id_usuario,))


def actualizar_credencial(id_usuario: int, hash_contrasena: str) -> None:
    ejecutar(
        "UPDATE credencial SET hash_contrasena = %s, fecha_cambio = NOW() WHERE id_usuario = %s",
        (hash_contrasena, id_usuario),
    )


# ── Historial de contraseñas ─────────────────────────────────────────────────

def agregar_historial_contrasena(id_usuario: int, hash_contrasena: str) -> None:
    ejecutar(
        "INSERT INTO historial_contrasena (id_usuario, hash_contrasena) VALUES (%s, %s)",
        (id_usuario, hash_contrasena),
    )


def obtener_historial_contrasena(id_usuario: int, limite: int = 5) -> list[dict]:
    return muchos(
        """
        SELECT hash_contrasena FROM historial_contrasena
        WHERE id_usuario = %s ORDER BY creado_en DESC LIMIT %s
        """,
        (id_usuario, limite),
    )


# ── 2FA ──────────────────────────────────────────────────────────────────────

def obtener_2fa(id_usuario: int) -> dict[str, Any] | None:
    return uno("SELECT * FROM usuario_2fa WHERE id_usuario = %s", (id_usuario,))


def guardar_2fa(id_usuario: int, metodo: str, secreto_totp: bytes | None) -> None:
    existente = obtener_2fa(id_usuario)
    if existente:
        ejecutar(
            "UPDATE usuario_2fa SET metodo = %s, secreto_totp = %s WHERE id_usuario = %s",
            (metodo, secreto_totp, id_usuario),
        )
    else:
        ejecutar(
            """
            INSERT INTO usuario_2fa (id_usuario, metodo, secreto_totp, habilitado, confirmado)
            VALUES (%s, %s, %s, FALSE, FALSE)
            """,
            (id_usuario, metodo, secreto_totp),
        )


def habilitar_2fa(id_usuario: int) -> None:
    ejecutar(
        """
        UPDATE usuario_2fa
        SET habilitado = TRUE, confirmado = TRUE, fecha_activacion = NOW()
        WHERE id_usuario = %s
        """,
        (id_usuario,),
    )


# ── Tokens de recuperación ───────────────────────────────────────────────────

def crear_token(
    id_usuario: int, token_hash: str, tipo: str, expira_en: datetime, ip: str | None
) -> None:
    ejecutar(
        """
        INSERT INTO token_recuperacion (id_usuario, token_hash, tipo, expira_en, ip_solicitud)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (id_usuario, token_hash, tipo, expira_en, ip),
    )


def buscar_token_valido(token_hash: str, tipo: str) -> dict[str, Any] | None:
    return uno(
        """
        SELECT * FROM token_recuperacion
        WHERE token_hash = %s AND tipo = %s AND usado = FALSE AND expira_en > NOW()
        """,
        (token_hash, tipo),
    )


def marcar_token_usado(id_token: int) -> None:
    ejecutar(
        "UPDATE token_recuperacion SET usado = TRUE, usado_en = NOW() WHERE id_token = %s",
        (id_token,),
    )


def invalidar_tokens_usuario(id_usuario: int, tipo: str) -> None:
    ejecutar(
        """
        UPDATE token_recuperacion SET usado = TRUE, usado_en = NOW()
        WHERE id_usuario = %s AND tipo = %s AND usado = FALSE
        """,
        (id_usuario, tipo),
    )


# ── Sesiones de usuario (lado servidor, revocables) ──────────────────────────

def crear_sesion(
    id_usuario: int,
    token_hash: str,
    ip: str | None,
    user_agent: str | None,
    expira_en: datetime,
) -> int:
    return ejecutar(
        """
        INSERT INTO sesion_usuario (id_usuario, token_hash, ip, user_agent, expira_en)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (id_usuario, token_hash, ip, user_agent, expira_en),
    )


def buscar_sesion_valida(token_hash: str) -> dict[str, Any] | None:
    return uno(
        """
        SELECT * FROM sesion_usuario
        WHERE token_hash = %s AND revocado = FALSE AND expira_en > NOW()
        """,
        (token_hash,),
    )


def revocar_sesion(token_hash: str) -> None:
    ejecutar(
        "UPDATE sesion_usuario SET revocado = TRUE WHERE token_hash = %s",
        (token_hash,),
    )


def revocar_todas_sesiones(id_usuario: int) -> None:
    ejecutar(
        "UPDATE sesion_usuario SET revocado = TRUE WHERE id_usuario = %s AND revocado = FALSE",
        (id_usuario,),
    )


# ── Intentos de login ────────────────────────────────────────────────────────

def registrar_intento(
    identificador: str, exito: bool, ip: str | None, user_agent: str | None
) -> None:
    ejecutar(
        "INSERT INTO intento_login (identificador, exito, ip, user_agent) VALUES (%s, %s, %s, %s)",
        (identificador, exito, ip, user_agent),
    )


# ── Lote de recuperación de archivo ─────────────────────────────────────────

def obtener_lote_activo(id_usuario: int) -> dict[str, Any] | None:
    return uno(
        "SELECT * FROM lote_recuperacion WHERE id_usuario = %s AND activo = TRUE",
        (id_usuario,),
    )


def obtener_numero_lote_maximo(id_usuario: int) -> int:
    fila = uno(
        "SELECT MAX(numero_lote) AS max_lote FROM lote_recuperacion WHERE id_usuario = %s",
        (id_usuario,),
    )
    return int(fila["max_lote"]) if fila and fila.get("max_lote") is not None else 0


def desactivar_lotes_usuario(id_usuario: int) -> None:
    ejecutar(
        "UPDATE lote_recuperacion SET activo = FALSE WHERE id_usuario = %s AND activo = TRUE",
        (id_usuario,),
    )


def crear_lote(id_usuario: int, numero_lote: int, generado_por: int | None) -> int:
    return ejecutar(
        """
        INSERT INTO lote_recuperacion
            (id_usuario, numero_lote, total_codigos, codigos_usados, activo, generado_por)
        VALUES (%s, %s, 12, 0, TRUE, %s)
        """,
        (id_usuario, numero_lote, generado_por),
    )


def crear_codigos_lote(id_lote: int, hashes: list[str]) -> None:
    for orden, h in enumerate(hashes, 1):
        ejecutar(
            "INSERT INTO codigo_recuperacion_archivo (id_lote, orden, codigo_hash) VALUES (%s, %s, %s)",
            (id_lote, orden, h),
        )


def obtener_codigos_lote(id_lote: int) -> list[dict]:
    return muchos(
        """
        SELECT * FROM codigo_recuperacion_archivo
        WHERE id_lote = %s AND usado = FALSE ORDER BY orden
        """,
        (id_lote,),
    )


def marcar_codigo_usado(id_codigo: int) -> None:
    ejecutar(
        "UPDATE codigo_recuperacion_archivo SET usado = TRUE, usado_en = NOW() WHERE id_codigo = %s",
        (id_codigo,),
    )


def incrementar_codigos_usados(id_lote: int) -> None:
    ejecutar(
        "UPDATE lote_recuperacion SET codigos_usados = codigos_usados + 1 WHERE id_lote = %s",
        (id_lote,),
    )


def desactivar_lote(id_lote: int) -> None:
    ejecutar("UPDATE lote_recuperacion SET activo = FALSE WHERE id_lote = %s", (id_lote,))


def obtener_lote_por_id(id_lote: int) -> dict[str, Any] | None:
    return uno("SELECT * FROM lote_recuperacion WHERE id_lote = %s", (id_lote,))


# ── Auditoría con paginación/filtros ─────────────────────────────────────────

def listar_auditoria(
    pagina: int = 1,
    por_pagina: int = 30,
    id_usuario: int | None = None,
    accion: str | None = None,
) -> list[dict]:
    condiciones: list[str] = []
    params: list[Any] = []
    if id_usuario is not None:
        condiciones.append("a.id_usuario = %s")
        params.append(id_usuario)
    if accion:
        condiciones.append("a.accion LIKE %s")
        params.append(f"%{accion}%")
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    offset = (pagina - 1) * por_pagina
    params += [por_pagina, offset]
    return muchos(
        f"""
        SELECT a.*, u.email, u.primer_nombre, u.primer_apellido
        FROM auditoria a
        LEFT JOIN usuario u ON u.id_usuario = a.id_usuario
        {where}
        ORDER BY a.creado_en DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params),
    )


def contar_auditoria(id_usuario: int | None = None, accion: str | None = None) -> int:
    condiciones: list[str] = []
    params: list[Any] = []
    if id_usuario is not None:
        condiciones.append("id_usuario = %s")
        params.append(id_usuario)
    if accion:
        condiciones.append("accion LIKE %s")
        params.append(f"%{accion}%")
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    fila = uno(f"SELECT COUNT(*) AS total FROM auditoria {where}", tuple(params))
    return int(fila["total"]) if fila else 0


# ── Auditoría ────────────────────────────────────────────────────────────────

def registrar_auditoria(
    id_usuario: int | None,
    accion: str,
    entidad: str | None,
    id_entidad: str | None,
    ip: str | None,
    user_agent: str | None,
    detalle: dict | None,
) -> None:
    detalle_json = json.dumps(detalle, ensure_ascii=False) if detalle else None
    ejecutar(
        """
        INSERT INTO auditoria (id_usuario, accion, entidad, id_entidad, ip, user_agent, detalle)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (id_usuario, accion, entidad, id_entidad, ip, user_agent, detalle_json),
    )
