"""Servicio de autenticación: registro, verificación email, login con bloqueo, logout.

Sin imports de Flask ni de mysql.connector. Recibe datos ya validados de formato
y devuelve dicts o lanza excepciones de dominio.
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta
from typing import Any

from app.comun.errores import (
    AutenticacionError,
    BloqueadoError,
    ConflictoError,
    ValidacionError,
)
from app.comun.seguridad_utils import (
    generar_token_url,
    hash_codigo,
    hash_password,
    sha256_hex,
    verificar_password,
)
from app.comun.validadores import validar_contrasena, validar_email
from app.datos import seguridad_repositorio as sr
from app.datos import usuario_repositorio as ur
from app.negocio.seguridad.auditoria_servicio import registrar as audit
from app.negocio.seguridad.contrasena_servicio import hash_nueva, validar_politica

# Hash dummy para anti-enumeración: consume tiempo Argon2id aunque el usuario no exista.
_DUMMY_HASH: str = hash_password("DummyAntiEnumPhysioScan2024!")


def registrar_usuario(
    primer_nombre: str,
    segundo_nombre: str | None,
    primer_apellido: str,
    segundo_apellido: str | None,
    email: str,
    telefono: str | None,
    password: str,
    ip: str | None = None,
) -> tuple[int, str, list[str]]:
    """Crea una cuenta nueva (rol deportista).

    Returns:
        (id_usuario, token_verificacion_claro, codigos_recuperacion_planos)

    El token y los códigos en claro existen únicamente en esta llamada.
    El sistema persiste solo sus hashes (Argon2id / SHA-256).
    """
    email = email.lower().strip()

    if not validar_email(email):
        raise ValidacionError("El correo no tiene un formato válido.")

    validar_politica(password)

    if ur.buscar_por_email(email):
        raise ConflictoError("El correo ya está registrado.")

    rol = ur.buscar_rol_por_nombre("deportista")
    if not rol:
        raise ValidacionError("Rol 'deportista' no configurado.")

    hash_pwd = hash_nueva(password)

    token_claro = generar_token_url(32)
    token_hash  = sha256_hex(token_claro)
    token_expira = datetime.utcnow() + timedelta(hours=24)

    codigos_planos  = _generar_codigos(12)
    hashes_codigos  = [hash_codigo(c) for c in codigos_planos]

    id_usuario, _ = ur.crear_completo(
        primer_nombre   = primer_nombre,
        segundo_nombre  = segundo_nombre,
        primer_apellido = primer_apellido,
        segundo_apellido= segundo_apellido,
        email           = email,
        telefono        = telefono,
        id_rol          = rol["id_rol"],
        hash_contrasena = hash_pwd,
        token_hash      = token_hash,
        token_expira    = token_expira,
        ip_solicitud    = ip,
        hashes_codigos  = hashes_codigos,
    )

    audit("REGISTRO", id_usuario, ip, detalle={"email": email})
    return id_usuario, token_claro, codigos_planos


def verificar_email(token_claro: str, ip: str | None = None) -> int:
    """Activa la cuenta mediante el token del enlace de verificación.

    Returns:
        id_usuario del usuario verificado.
    Raises:
        AutenticacionError si el token no existe, ya fue usado o expiró.
    """
    token_hash = sha256_hex(token_claro)
    registro   = sr.buscar_token_valido(token_hash, "verificacion_email")
    if not registro:
        raise AutenticacionError("El enlace de verificación no es válido o ha expirado.")

    sr.marcar_token_usado(registro["id_token"])
    ur.marcar_email_verificado(registro["id_usuario"])
    audit("EMAIL_VERIFICADO", registro["id_usuario"], ip)
    return registro["id_usuario"]


def autenticar(
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
    lockout_intentos: int = 5,
    lockout_minutos: int  = 15,
) -> dict[str, Any]:
    """Verifica credenciales y devuelve la fila del usuario (dict con nombre_rol).

    Anti-enumeración: ejecuta Argon2id aunque el usuario no exista.
    Raises:
        AutenticacionError — credenciales inválidas o cuenta no verificada/activa.
        BloqueadoError     — cuenta bloqueada temporalmente.
    """
    email   = email.lower().strip()
    usuario = ur.buscar_por_email(email)

    if usuario is None:
        verificar_password(password, _DUMMY_HASH)  # consume tiempo constante
        sr.registrar_intento(email, False, ip, user_agent)
        raise AutenticacionError("Credenciales inválidas.")

    # Bloqueo temporal activo
    bloqueado_hasta = usuario.get("bloqueado_hasta")
    if bloqueado_hasta and bloqueado_hasta > datetime.utcnow():
        raise BloqueadoError(
            "Cuenta bloqueada temporalmente. "
            f"Inténtalo de nuevo después de las {bloqueado_hasta.strftime('%H:%M')}."
        )

    credencial      = sr.obtener_credencial(usuario["id_usuario"])
    hash_almacenado = credencial["hash_contrasena"] if credencial else _DUMMY_HASH

    valida = verificar_password(password, hash_almacenado)
    sr.registrar_intento(email, valida, ip, user_agent)

    if not valida:
        ur.incrementar_intentos(usuario["id_usuario"])
        fila_actual = ur.buscar_por_id(usuario["id_usuario"])
        intentos    = fila_actual["intentos_fallidos"] if fila_actual else 0

        if intentos >= lockout_intentos:
            bloqueado_hasta = datetime.utcnow() + timedelta(minutes=lockout_minutos)
            ur.bloquear(usuario["id_usuario"], bloqueado_hasta)
            audit("CUENTA_BLOQUEADA", usuario["id_usuario"], ip, user_agent)
            raise BloqueadoError("Cuenta bloqueada por demasiados intentos fallidos.")

        raise AutenticacionError("Credenciales inválidas.")

    if not usuario.get("email_verificado"):
        raise AutenticacionError("Verifica tu correo antes de iniciar sesión.")

    if usuario.get("estado") != "activo":
        raise AutenticacionError("La cuenta no está activa. Contacta al administrador.")

    ur.actualizar_ultimo_acceso(usuario["id_usuario"])
    audit("LOGIN_OK", usuario["id_usuario"], ip, user_agent)
    return usuario


def crear_sesion_servidor(
    id_usuario: int,
    ip: str | None,
    user_agent: str | None,
    expira_horas: int = 24,
) -> str:
    """Crea una sesión del lado servidor (revocable). Devuelve el token en claro."""
    token_claro = generar_token_url(32)
    token_hash  = sha256_hex(token_claro)
    expira_en   = datetime.utcnow() + timedelta(hours=expira_horas)
    sr.crear_sesion(id_usuario, token_hash, ip, user_agent, expira_en)
    return token_claro


def revocar_sesion_servidor(token_claro: str) -> None:
    sr.revocar_sesion(sha256_hex(token_claro))


def revocar_todas_sesiones(id_usuario: int) -> None:
    sr.revocar_todas_sesiones(id_usuario)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _generar_codigos(n: int) -> list[str]:
    alfabet = string.ascii_uppercase + string.digits
    return [
        "-".join(
            "".join(secrets.choice(alfabet) for _ in range(4))
            for _ in range(3)
        )
        for _ in range(n)
    ]
