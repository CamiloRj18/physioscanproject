"""Servicio de recuperación por correo: token SHA-256 de un solo uso, 30 min.

Anti-enumeración: solicitar_reset nunca revela si el email existe.
El controlador siempre muestra el mismo mensaje genérico.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.comun.errores import AutenticacionError, ValidacionError
from app.comun.seguridad_utils import (
    generar_token_url,
    hash_password,
    sha256_hex,
    verificar_password,
)
from app.datos import seguridad_repositorio as sr
from app.datos import usuario_repositorio as ur
from app.negocio.seguridad.auditoria_servicio import registrar as audit
from app.negocio.seguridad.contrasena_servicio import en_historial, hash_nueva, validar_politica

# Hash dummy para igualar tiempos cuando el usuario no existe.
_DUMMY_HASH: str = hash_password("DummyAntiEnumResetPhysioScan!")


def solicitar_reset(email: str, ip: str | None = None) -> tuple[str, str, str] | None:
    """Genera token de reset y retorna (primer_nombre, email, token_claro) o None.

    Nunca lanza excepción visible al usuario.
    El controlador SIEMPRE muestra respuesta genérica.
    Retorna None si el email no existe o la cuenta no está activa;
    retorna la tupla si el correo se debe enviar.
    """
    email = email.lower().strip()
    usuario = ur.buscar_por_email(email)

    if not usuario or usuario.get("estado") not in ("activo",):
        # Tiempo constante: simula el hash que se haría en el camino exitoso
        verificar_password("dummy_check_for_timing", _DUMMY_HASH)
        return None

    id_usuario = usuario["id_usuario"]

    # Invalida tokens anteriores del mismo tipo para este usuario
    sr.invalidar_tokens_usuario(id_usuario, "reset_password")

    token_claro = generar_token_url(32)
    token_hash  = sha256_hex(token_claro)
    expira_en   = datetime.utcnow() + timedelta(minutes=30)

    sr.crear_token(id_usuario, token_hash, "reset_password", expira_en, ip)
    audit("RESET_SOLICITADO", id_usuario, ip, detalle={"email": email})

    return usuario["primer_nombre"], usuario["email"], token_claro


def validar_token(token_claro: str) -> dict[str, Any]:
    """Valida el token de reset y retorna la fila del usuario.

    Raises:
        AutenticacionError: si el token no existe, ya fue usado o expiró.
    """
    token_hash = sha256_hex(token_claro)
    registro   = sr.buscar_token_valido(token_hash, "reset_password")
    if not registro:
        raise AutenticacionError("El enlace de recuperación no es válido o ha expirado.")

    usuario = ur.buscar_por_id(registro["id_usuario"])
    if not usuario:
        raise AutenticacionError("El enlace de recuperación no es válido.")

    return {"token_fila": registro, "usuario": usuario}


def restablecer(token_claro: str, nueva_password: str, ip: str | None = None) -> None:
    """Restablece la contraseña usando el token de correo.

    Pasos:
      1. Valida token (hash + vigencia + no usado).
      2. Aplica política de contraseña.
      3. Verifica historial (no reuso de últimas 5).
      4. Actualiza hash en credencial.
      5. Agrega al historial.
      6. Marca token como usado.
      7. Revoca TODAS las sesiones del usuario.
      8. Audita.

    Raises:
        AutenticacionError: token inválido.
        ValidacionError: contraseña no cumple política o está en historial.
    """
    token_hash = sha256_hex(token_claro)
    registro   = sr.buscar_token_valido(token_hash, "reset_password")
    if not registro:
        raise AutenticacionError("El enlace de recuperación no es válido o ha expirado.")

    id_usuario = registro["id_usuario"]

    validar_politica(nueva_password)

    historial = sr.obtener_historial_contrasena(id_usuario, limite=5)
    if en_historial(nueva_password, historial):
        raise ValidacionError("No puedes usar una contraseña que ya utilizaste recientemente.")

    nuevo_hash = hash_nueva(nueva_password)

    sr.actualizar_credencial(id_usuario, nuevo_hash)
    sr.agregar_historial_contrasena(id_usuario, nuevo_hash)
    sr.marcar_token_usado(registro["id_token"])
    sr.revocar_todas_sesiones(id_usuario)

    audit("CONTRASENA_RESTABLECIDA_EMAIL", id_usuario, ip,
          detalle={"token_id": registro["id_token"]})
