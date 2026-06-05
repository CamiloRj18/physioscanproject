"""Servicio del archivo de 12 códigos de recuperación.

Cada código se genera con secrets (formato XXXX-XXXX-XXXX),
se hashea con Argon2id y se persiste. El texto plano solo existe
en memoria durante la llamada a generar_lote(); el sistema no puede
volver a mostrarlo.
"""
from __future__ import annotations

import io
import secrets
import string
from datetime import date, datetime

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
) -> tuple[list[str], str, str, bytes]:
    """Genera un nuevo lote de 12 códigos de recuperación de archivo.

    Desactiva el lote anterior (si existe) y crea uno nuevo.
    Los textos planos solo existen en memoria durante esta llamada.

    Args:
        id_usuario:   Usuario al que pertenece el lote.
        generado_por: id_usuario del admin que reemite; None si es el registro inicial.

    Returns:
        (codigos_planos, contenido_txt, nombre_archivo, pdf_bytes)
        - codigos_planos: lista de 12 strings (texto claro, one-time).
        - contenido_txt:  texto del archivo descargable.
        - nombre_archivo: nombre base (sin extensión) para Content-Disposition.
        - pdf_bytes:       PDF en memoria listo para enviar al navegador.
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

    contenido_txt  = _construir_txt(codigo_usuario, numero_nuevo, codigos_planos, generado_por)
    nombre_archivo = f"physioscan_recuperacion_{codigo_usuario}"

    nombre_usuario = ""
    if usuario:
        nombre_usuario = f"{usuario.get('primer_nombre', '')} {usuario.get('primer_apellido', '')}".strip()

    pdf_bytes = _generar_pdf(codigos_planos, codigo_usuario, nombre_usuario)

    return codigos_planos, contenido_txt, nombre_archivo, pdf_bytes


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


def _pagina_oscura(canvas, doc):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#020813"))
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


def _generar_pdf(codigos: list[str], codigo_usuario: str, nombre_usuario: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    getSampleStyleSheet()
    elements = []

    titulo_style = ParagraphStyle(
        "titulo", fontSize=24, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#79DBFF"), spaceAfter=6, alignment=TA_CENTER,
    )
    elements.append(Paragraph("PhysioScan", titulo_style))

    subtitulo_style = ParagraphStyle(
        "subtitulo", fontSize=13, fontName="Helvetica",
        textColor=colors.HexColor("#9784C8"), spaceAfter=4, alignment=TA_CENTER,
    )
    elements.append(Paragraph("Archivo de Códigos de Recuperación", subtitulo_style))
    elements.append(Spacer(1, 0.3 * cm))

    info_style = ParagraphStyle(
        "info", fontSize=10, fontName="Helvetica",
        textColor=colors.HexColor("#ECFBFF"), spaceAfter=2, alignment=TA_CENTER,
    )
    if nombre_usuario:
        elements.append(Paragraph(f"Usuario: {nombre_usuario}", info_style))
    elements.append(Paragraph(f"Código: {codigo_usuario}", info_style))
    elements.append(Paragraph(f"Generado: {date.today().strftime('%d/%m/%Y')}", info_style))
    elements.append(Spacer(1, 0.5 * cm))

    warn_style = ParagraphStyle(
        "warn", fontSize=9, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#FF7285"), spaceAfter=4, alignment=TA_CENTER,
        borderColor=colors.HexColor("#FF7285"), borderWidth=1, borderPadding=8,
        backColor=colors.HexColor("#1a0a0d"),
    )
    elements.append(Paragraph(
        "IMPORTANTE: Cada código solo puede usarse UNA VEZ. "
        "Guarda este archivo en un lugar seguro. "
        "Al agotar los 12 códigos, solicita reemisión al administrador.",
        warn_style,
    ))
    elements.append(Spacer(1, 0.5 * cm))

    data = []
    for i in range(0, 12, 2):
        data.append([
            f"{i + 1}.  {codigos[i]}",
            f"{i + 2}.  {codigos[i + 1]}" if i + 1 < len(codigos) else "",
        ])

    tabla = Table(data, colWidths=[8 * cm, 8 * cm], rowHeights=1.1 * cm)
    tabla.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Courier-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 11),
        ("TEXTCOLOR",   (0, 0), (-1, -1), colors.HexColor("#79DBFF")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.HexColor("#041425"), colors.HexColor("#071C34")]),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#79DBFF")),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(tabla)
    elements.append(Spacer(1, 0.5 * cm))

    footer_style = ParagraphStyle(
        "footer", fontSize=8, fontName="Helvetica",
        textColor=colors.HexColor("#9784C8"), alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        "PhysioScan · Institución Universitaria de El Espinal — UniEspinal · "
        "Tratamiento de datos conforme a la Ley 1581 de 2012",
        footer_style,
    ))

    doc.build(elements, onFirstPage=_pagina_oscura, onLaterPages=_pagina_oscura)
    buffer.seek(0)
    return buffer.read()


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
