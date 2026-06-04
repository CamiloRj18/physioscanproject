"""Servicio del archivo de 12 códigos de recuperación.

Cada código se genera con secrets (formato XXXX-XXXX-XXXX),
se hashea con Argon2id y se persiste. El texto plano solo existe
en memoria durante la llamada a generar_lote(); el sistema no puede
volver a mostrarlo.
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime

from app.comun.errores import AutenticacionError, BloqueadoError, ValidacionError
from app.comun.seguridad_utils import hash_codigo, verificar_codigo
from app.datos import seguridad_repositorio as sr
from app.datos import usuario_repositorio as ur
from app.negocio.seguridad.auditoria_servicio import registrar as audit
from app.negocio.seguridad.contrasena_servicio import en_historial, hash_nueva, validar_politica

_ALFABETO = string.ascii_uppercase + string.digits
_TOTAL    = 12


def generar_lote(
    id_usuario: int,
    generado_por: int | None = None,
) -> tuple[list[str], str, str]:
    """Genera un nuevo lote de 12 códigos de recuperación de archivo.

    Desactiva el lote anterior (si existe) y crea uno nuevo.
    Los textos planos solo existen en memoria durante esta llamada.

    Args:
        id_usuario:   Usuario al que pertenece el lote.
        generado_por: id_usuario del admin que reemite; None si es el registro inicial.

    Returns:
        (codigos_planos, contenido_txt, nombre_archivo)
        - codigos_planos: lista de 12 strings (texto claro, one-time).
        - contenido_txt:  texto del archivo descargable.
        - nombre_archivo: nombre sugerido para Content-Disposition.
    """
    usuario = ur.buscar_por_id(id_usuario)
    if not usuario:
        raise ValidacionError("Usuario no encontrado.")

    codigo_usuario = usuario.get("codigo_usuario") or str(id_usuario)

    # Calcular número del nuevo lote
    numero_anterior = sr.obtener_numero_lote_maximo(id_usuario)
    numero_nuevo    = numero_anterior + 1

    # Desactivar lotes anteriores
    sr.desactivar_lotes_usuario(id_usuario)

    # Generar 12 códigos en texto claro
    codigos_planos  = [_generar_codigo() for _ in range(_TOTAL)]
    hashes_codigos  = [hash_codigo(c) for c in codigos_planos]

    # Persistir lote + códigos (hashes solamente)
    id_lote = sr.crear_lote(id_usuario, numero_nuevo, generado_por)
    sr.crear_codigos_lote(id_lote, hashes_codigos)

    accion = "LOTE_REEMITIDO" if generado_por else "LOTE_GENERADO"
    audit(
        accion,
        id_usuario,
        detalle={
            "id_lote":     id_lote,
            "numero_lote": numero_nuevo,
            "generado_por": generado_por,
        },
    )

    contenido_txt = _construir_txt(codigo_usuario, numero_nuevo, codigos_planos, generado_por)
    nombre_archivo = f"physioscan_recuperacion_{codigo_usuario}.txt"

    return codigos_planos, contenido_txt, nombre_archivo


def recuperar_con_codigo(
    email: str,
    codigo_str: str,
    nueva_password: str,
    ip: str | None = None,
) -> None:
    """Recupera la cuenta usando un código del archivo de 12.

    Flujo:
      1. Busca usuario por email.
      2. Obtiene lote activo.
      3. Normaliza el código ingresado.
      4. Compara con hashes Argon2id (tiempo constante).
      5. Si coincide: marca usado, incrementa contador, desactiva lote si es el #12.
      6. Aplica política + historial a la nueva contraseña.
      7. Revoca todas las sesiones.
      8. Audita.

    Raises:
        AutenticacionError: email/código inválido.
        ValidacionError:    sin lote activo, política de contraseña, reuso.
        BloqueadoError:     cuenta bloqueada.
    """
    email    = email.lower().strip()
    usuario  = ur.buscar_por_email(email)

    if not usuario:
        raise AutenticacionError("Datos inválidos.")

    if usuario.get("estado") == "bloqueado":
        raise BloqueadoError("La cuenta está bloqueada. Contacta al administrador.")

    if usuario.get("estado") not in ("activo",):
        raise AutenticacionError("La cuenta no está activa. Contacta al administrador.")

    id_usuario = usuario["id_usuario"]
    lote       = sr.obtener_lote_activo(id_usuario)

    if not lote:
        raise ValidacionError(
            "No tienes un archivo de recuperación activo. "
            "Solicita al administrador que reemita tu archivo de recuperación."
        )

    codigos_disponibles = sr.obtener_codigos_lote(lote["id_lote"])
    if not codigos_disponibles:
        # Todos usados pero lote aún marcado activo (inconsistencia defensiva)
        sr.desactivar_lote(lote["id_lote"])
        raise ValidacionError(
            "Todos los códigos han sido utilizados. "
            "Solicita al administrador un nuevo archivo de recuperación."
        )

    codigo_normalizado = _normalizar_codigo(codigo_str)
    codigo_encontrado  = _buscar_coincidencia(codigo_normalizado, codigos_disponibles)

    if not codigo_encontrado:
        audit("CODIGO_ARCHIVO_INVALIDO", id_usuario, ip, detalle={
            "id_lote": lote["id_lote"],
        })
        raise AutenticacionError("Código inválido o ya utilizado.")

    # Validar nueva contraseña antes de aplicar cambios
    validar_politica(nueva_password)
    historial = sr.obtener_historial_contrasena(id_usuario, limite=5)
    if en_historial(nueva_password, historial):
        raise ValidacionError("No puedes usar una contraseña que ya utilizaste recientemente.")

    # Marcar código como usado e incrementar contador
    sr.marcar_codigo_usado(codigo_encontrado["id_codigo"])
    sr.incrementar_codigos_usados(lote["id_lote"])

    # Comprobar si era el último código → desactivar lote
    lote_actualizado = sr.obtener_lote_por_id(lote["id_lote"])
    lote_agotado     = False
    if lote_actualizado:
        usados = lote_actualizado["codigos_usados"]
        total  = lote_actualizado["total_codigos"]
        if usados >= total:
            sr.desactivar_lote(lote["id_lote"])
            lote_agotado = True

    # Actualizar contraseña
    nuevo_hash = hash_nueva(nueva_password)
    sr.actualizar_credencial(id_usuario, nuevo_hash)
    sr.agregar_historial_contrasena(id_usuario, nuevo_hash)

    # Revocar todas las sesiones activas
    sr.revocar_todas_sesiones(id_usuario)

    audit("CONTRASENA_RESTABLECIDA_ARCHIVO", id_usuario, ip, detalle={
        "orden_codigo": codigo_encontrado["orden"],
        "id_lote":      lote["id_lote"],
        "lote_agotado": lote_agotado,
    })


# ── Helpers privados ─────────────────────────────────────────────────────────

def _generar_codigo() -> str:
    return "-".join(
        "".join(secrets.choice(_ALFABETO) for _ in range(4))
        for _ in range(3)
    )


def _normalizar_codigo(codigo: str) -> str:
    """Elimina separadores y reconstruye el formato XXXX-XXXX-XXXX."""
    limpio = "".join(c.upper() for c in codigo if c.isalnum())
    if len(limpio) == 12:
        return f"{limpio[:4]}-{limpio[4:8]}-{limpio[8:12]}"
    return codigo.strip().upper()


def _buscar_coincidencia(codigo_normalizado: str, codigos: list[dict]) -> dict | None:
    """Busca el código en la lista comparando contra hashes Argon2id."""
    for c in codigos:
        if verificar_codigo(codigo_normalizado, c["codigo_hash"]):
            return c
    return None


def _construir_txt(
    codigo_usuario: str,
    numero_lote: int,
    codigos: list[str],
    generado_por: int | None,
) -> str:
    ahora     = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    separador = "─" * 48
    quien     = "Sistema (registro)" if generado_por is None else f"Admin (id={generado_por})"

    lineas_codigos = "\n".join(
        f" {str(i+1).rjust(2)}. {c}" for i, c in enumerate(codigos)
    )

    return (
        f"PhysioScan — Archivo de Recuperación\n"
        f"{separador}\n"
        f"Usuario:     {codigo_usuario}\n"
        f"Lote:        #{numero_lote}\n"
        f"Generado:    {ahora}\n"
        f"Emitido por: {quien}\n"
        f"{separador}\n"
        f"INSTRUCCIONES:\n"
        f"  · Cada código sirve solo UNA vez.\n"
        f"  · Úsalos en /recuperar/archivo si pierdes acceso a tu correo.\n"
        f"  · Al agotar los 12, solicita reemisión al administrador.\n"
        f"  · El sistema NO puede regenerar estos códigos.\n"
        f"{separador}\n"
        f"Códigos de recuperación:\n"
        f"{lineas_codigos}\n"
        f"{separador}\n"
        f"Estos códigos son CONFIDENCIALES. No los compartas.\n"
        f"PhysioScan — UniEspinal\n"
    )
