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
