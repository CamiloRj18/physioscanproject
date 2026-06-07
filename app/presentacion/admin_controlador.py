"""Controlador de administración.

Rutas (todas protegidas con @rol_requerido("administrador")):

    GET      /admin/                              → panel resumen
    GET      /admin/usuarios                      → lista paginada con filtros
    GET/POST /admin/usuarios/crear                → crear usuario (cualquier rol)
    GET      /admin/usuarios/<id>                 → detalle + acciones
    POST     /admin/usuarios/<id>/estado          → activar / inactivar / bloquear
    GET/POST /admin/usuarios/<id>/reemitir        → reemitir archivo de 12 códigos
    POST     /admin/asignaciones/crear            → asignar entrenador ↔ deportista
    POST     /admin/asignaciones/<id>/eliminar    → eliminar asignación
    GET      /admin/auditoria                     → bitácora paginada con filtros
    POST     /admin/usuarios/<id>/resetear-password → genera password temporal y la envía
"""
from __future__ import annotations

import secrets
import string

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from flask_mail import Message

from app.extensions import mail

from app.comun.decoradores import rol_requerido
from app.comun.errores import ConflictoError, ValidacionError
from app.comun.seguridad_utils import hash_password, generar_token_url
from app.comun.validadores import validar_contrasena, validar_email
from app.datos import deportista_repositorio as dr
from app.datos import dispositivo_repositorio as dispr
from app.datos import seguridad_repositorio as sr
from app.datos import sesion_repositorio as sesionr
from app.datos import usuario_repositorio as ur
from app.negocio.seguridad import recuperacion_archivo_servicio as ras
from app.negocio.seguridad.auditoria_servicio import registrar as audit
from app.negocio.seguridad.contrasena_servicio import hash_nueva, validar_politica

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")


def _generar_password_temporal() -> str:
    mayus = string.ascii_uppercase
    minus = string.ascii_lowercase
    digitos = string.digits
    especiales = "!@#$%&*"
    alfab = mayus + minus + digitos + especiales
    chars = [
        secrets.choice(mayus),
        secrets.choice(minus),
        secrets.choice(digitos),
        secrets.choice(especiales),
    ] + [secrets.choice(alfab) for _ in range(8)]
    rand = secrets.SystemRandom()
    rand.shuffle(chars)
    return "".join(chars)


def _enviar_password_temporal(email: str, nombre: str, password_temp: str) -> None:
    msg = Message(
        subject="PhysioScan — Contraseña temporal restablecida",
        recipients=[email],
    )
    msg.body = (
        f"Hola {nombre},\n\n"
        "El administrador de PhysioScan restableció tu contraseña.\n\n"
        f"Tu contraseña temporal es:\n\n    {password_temp}\n\n"
        "Deberás cambiarla la próxima vez que inicies sesión.\n"
        "No compartas esta contraseña con nadie.\n\n"
        "— Equipo PhysioScan · UniEspinal"
    )
    mail.send(msg)


def _enviar_codigos_pdf(
    email: str, nombre: str, codigo_usuario: str, pdf_bytes: bytes
) -> None:
    msg = Message(
        subject="PhysioScan — Tu archivo de códigos de recuperación",
        recipients=[email],
    )
    msg.body = (
        f"Hola {nombre},\n\n"
        "Bienvenido/a a PhysioScan.\n\n"
        "Adjunto encontrarás tu archivo de 12 códigos de recuperación de contraseña.\n"
        "Cada código solo puede usarse UNA VEZ.\n"
        "Guarda este archivo en un lugar seguro.\n\n"
        "Si no solicitaste esta cuenta, ignora este correo.\n\n"
        "— Equipo PhysioScan · UniEspinal"
    )
    msg.attach(
        filename=f"physioscan_codigos_{codigo_usuario}.pdf",
        content_type="application/pdf",
        data=pdf_bytes,
    )
    mail.send(msg)

_POR_PAGINA = 20


# ── Panel resumen ─────────────────────────────────────────────────────────────

@bp_admin.get("/")
@rol_requerido("administrador")
def panel():
    total_usuarios    = ur.contar_total()
    total_deportistas = ur.contar_total(nombre_rol="deportista")
    total_entrenadores = ur.contar_total(nombre_rol="entrenador")
    total_bloqueados  = ur.contar_total(estado="bloqueado")
    return render_template(
        "admin/panel.html",
        stats={
            "usuarios":    total_usuarios,
            "deportistas": total_deportistas,
            "entrenadores": total_entrenadores,
            "bloqueados":  total_bloqueados,
        },
    )


# ── Lista de usuarios ─────────────────────────────────────────────────────────

@bp_admin.get("/usuarios")
@rol_requerido("administrador")
def usuarios():
    pagina    = max(1, request.args.get("p", 1, type=int))
    rol_f     = request.args.get("rol", "").strip() or None
    estado_f  = request.args.get("estado", "").strip() or None
    busqueda  = request.args.get("q", "").strip() or None

    filas  = ur.listar_paginado(pagina, _POR_PAGINA, rol_f, estado_f, busqueda)
    total  = ur.contar_total(rol_f, estado_f, busqueda)
    paginas = max(1, (total + _POR_PAGINA - 1) // _POR_PAGINA)
    roles   = ur.listar_roles()

    return render_template(
        "admin/usuarios.html",
        usuarios=filas,
        pagina=pagina,
        paginas=paginas,
        total=total,
        roles=roles,
        filtros={"rol": rol_f or "", "estado": estado_f or "", "q": busqueda or ""},
    )


# ── Crear usuario ─────────────────────────────────────────────────────────────

@bp_admin.route("/usuarios/crear", methods=["GET", "POST"])
@rol_requerido("administrador")
def crear_usuario():
    roles = ur.listar_roles()

    if request.method == "POST":
        form = {
            "primer_nombre":    request.form.get("primer_nombre", "").strip(),
            "segundo_nombre":   request.form.get("segundo_nombre", "").strip() or None,
            "primer_apellido":  request.form.get("primer_apellido", "").strip(),
            "segundo_apellido": request.form.get("segundo_apellido", "").strip() or None,
            "email":            request.form.get("email", "").strip().lower(),
            "telefono":         request.form.get("telefono", "").strip() or None,
            "id_rol":           request.form.get("id_rol", "", type=int),
            "password":         request.form.get("password", ""),
        }

        error = None
        if not form["primer_nombre"]:
            error = "El primer nombre es obligatorio."
        elif not form["primer_apellido"]:
            error = "El primer apellido es obligatorio."
        elif not validar_email(form["email"]):
            error = "El correo no tiene un formato válido."
        elif not form["id_rol"]:
            error = "Selecciona un rol."
        elif not form["password"]:
            error = "La contraseña es obligatoria."
        else:
            error = validar_contrasena(form["password"])

        if error:
            flash(error, "error")
            return render_template("admin/crear_usuario.html", roles=roles, form=form)

        if ur.buscar_por_email(form["email"]):
            flash("El correo ya está registrado.", "error")
            return render_template("admin/crear_usuario.html", roles=roles, form=form)

        try:
            validar_politica(form["password"])
        except ValidacionError as exc:
            flash(str(exc), "error")
            return render_template("admin/crear_usuario.html", roles=roles, form=form)

        nuevo_hash = hash_nueva(form["password"])
        id_nuevo   = ur.crear_con_rol(
            primer_nombre    = form["primer_nombre"],
            segundo_nombre   = form["segundo_nombre"],
            primer_apellido  = form["primer_apellido"],
            segundo_apellido = form["segundo_apellido"],
            email            = form["email"],
            telefono         = form["telefono"],
            id_rol           = form["id_rol"],
            hash_contrasena  = nuevo_hash,
        )

        fila_nueva = ur.buscar_por_id(id_nuevo)
        codigo_usuario_nuevo = fila_nueva["codigo_usuario"] if fila_nueva else str(id_nuevo)
        email_enviado = False
        try:
            _, _, _, pdf_bytes = ras.generar_lote(id_nuevo, int(current_user.get_id()))
            _enviar_codigos_pdf(form["email"], form["primer_nombre"], codigo_usuario_nuevo, pdf_bytes)
            email_enviado = True
        except Exception as exc:
            current_app.logger.warning("Lote/PDF códigos no enviado para usuario %s: %s", id_nuevo, exc)

        audit(
            "USUARIO_CREADO_ADMIN",
            int(current_user.get_id()),
            request.remote_addr,
            detalle={"id_nuevo": id_nuevo, "email": form["email"]},
        )

        if email_enviado:
            flash(
                f'Usuario {form["primer_nombre"]} {form["primer_apellido"]} creado correctamente. '
                f'El archivo de códigos de recuperación fue enviado a {form["email"]}.',
                "success",
            )
        else:
            flash(
                f'Usuario creado. ADVERTENCIA: No se pudo enviar el archivo de códigos '
                f'al correo {form["email"]}. Genera el archivo manualmente desde '
                "el detalle del usuario.",
                "warning",
            )

        return redirect(url_for("admin.usuarios"))

    return render_template("admin/crear_usuario.html", roles=roles, form={})


# ── Detalle de usuario ────────────────────────────────────────────────────────

@bp_admin.get("/usuarios/<int:id>")
@rol_requerido("administrador")
def usuario_detalle(id: int):
    usuario = ur.buscar_por_id(id)
    if not usuario:
        abort(404)

    lote_activo      = sr.obtener_lote_activo(id)
    deportista       = dr.buscar_por_id_usuario(id)
    asignaciones     = []
    entrenadores     = []
    deportistas_todos = []

    if deportista:
        # Buscar asignaciones si es deportista
        asignaciones = dr.listar_asignaciones_entrenador(id) if usuario["nombre_rol"] == "entrenador" else []
        entrenadores = ur.buscar_todos_por_rol("entrenador")
        deportistas_todos = dr.listar_todos()

    if usuario["nombre_rol"] == "entrenador":
        asignaciones     = dr.listar_asignaciones_entrenador(id)
        deportistas_todos = dr.listar_todos()

    roles = ur.listar_roles()

    return render_template(
        "admin/usuario_detalle.html",
        usuario=usuario,
        lote_activo=lote_activo,
        deportista=deportista,
        asignaciones=asignaciones,
        entrenadores=entrenadores,
        deportistas_todos=deportistas_todos,
        roles=roles,
    )


# ── Cambio de estado ──────────────────────────────────────────────────────────

@bp_admin.post("/usuarios/<int:id>/estado")
@rol_requerido("administrador")
def cambiar_estado(id: int):
    usuario = ur.buscar_por_id(id)
    if not usuario:
        abort(404)

    nuevo_estado = request.form.get("estado", "").strip()
    if nuevo_estado not in ("activo", "inactivo", "bloqueado"):
        flash("Estado no válido.", "error")
        return redirect(url_for("admin.usuario_detalle", id=id))

    ur.actualizar_estado(id, nuevo_estado)

    if nuevo_estado in ("activo",):
        ur.reiniciar_intentos(id)

    audit(
        f"ADMIN_ESTADO_{nuevo_estado.upper()}",
        int(current_user.get_id()),
        request.remote_addr,
        detalle={"id_objetivo": id, "nuevo_estado": nuevo_estado},
    )
    flash(f"Estado de cuenta actualizado a '{nuevo_estado}'.", "success")
    return redirect(url_for("admin.usuario_detalle", id=id))


# ── Cambio de rol ────────────────────────────────────────────────────────────

@bp_admin.post("/usuarios/<int:id>/rol")
@rol_requerido("administrador")
def cambiar_rol(id: int):
    usuario = ur.buscar_por_id(id)
    if not usuario:
        abort(404)

    nombre_rol = request.form.get("nombre_rol", "").strip()
    rol = ur.buscar_rol_por_nombre(nombre_rol)
    if not rol:
        flash("Rol no válido.", "error")
        return redirect(url_for("admin.usuario_detalle", id=id))

    ur.actualizar_rol(id, rol["id_rol"])
    audit(
        "ADMIN_ROL_CAMBIADO",
        int(current_user.get_id()),
        request.remote_addr,
        detalle={"id_objetivo": id, "nuevo_rol": nombre_rol},
    )
    flash(f"Rol actualizado a '{nombre_rol}'.", "success")
    return redirect(url_for("admin.usuario_detalle", id=id))


# ── Reemisión del archivo de 12 códigos ──────────────────────────────────────

@bp_admin.route("/usuarios/<int:id>/reemitir", methods=["GET", "POST"])
@rol_requerido("administrador")
def reemitir_recuperacion(id: int):
    """Reemite el archivo de 12 códigos para un usuario.

    GET  → muestra aviso de que se invalidará el lote anterior + botón confirmar.
    POST → genera nuevo lote, descarga el archivo, audita LOTE_REEMITIDO.
    """
    usuario = ur.buscar_por_id(id)
    if not usuario:
        abort(404)

    lote_actual = sr.obtener_lote_activo(id)

    if request.method == "POST":
        id_admin = int(current_user.get_id())
        try:
            _, _, _, pdf_bytes = ras.generar_lote(id, generado_por=id_admin)
        except ValidacionError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.usuario_detalle", id=id))

        audit(
            "LOTE_REEMITIDO",
            id_admin,
            request.remote_addr,
            detalle={"id_usuario_objetivo": id, "lote_anterior": lote_actual["id_lote"] if lote_actual else None},
        )

        try:
            _enviar_codigos_pdf(
                usuario["email"],
                usuario["primer_nombre"],
                usuario["codigo_usuario"],
                pdf_bytes,
            )
            flash("Archivo reemitido y enviado al correo del usuario.", "success")
        except Exception as exc:
            current_app.logger.error("Error reemitiendo PDF: %s", exc)
            flash(
                "Lote generado pero no se pudo enviar el correo. "
                "Verifica la configuración de correo.",
                "warning",
            )

        return redirect(url_for("admin.usuario_detalle", id=id))

    return render_template(
        "admin/reemitir_recuperacion.html",
        usuario=usuario,
        lote_actual=lote_actual,
    )


# ── Restablecer contraseña de usuario ────────────────────────────────────────

@bp_admin.post("/usuarios/<int:id>/resetear-password")
@rol_requerido("administrador")
def resetear_password(id: int):
    usuario = ur.buscar_por_id(id)
    if not usuario:
        abort(404)

    password_temp = _generar_password_temporal()
    nuevo_hash    = hash_nueva(password_temp)

    sr.actualizar_credencial(id, nuevo_hash)
    sr.agregar_historial_contrasena(id, nuevo_hash)
    sr.marcar_requiere_cambio(id)
    sr.revocar_todas_sesiones(id)

    audit(
        "ADMIN_PASSWORD_RESETEADO",
        int(current_user.get_id()),
        request.remote_addr,
        detalle={"id_objetivo": id},
    )

    try:
        _enviar_password_temporal(usuario["email"], usuario["primer_nombre"], password_temp)
        flash("Contraseña restablecida y enviada al correo del usuario.", "success")
    except Exception as exc:
        current_app.logger.error("No se pudo enviar correo de contraseña temporal: %s", exc)
        flash("Contraseña restablecida pero no se pudo enviar el correo. Verifica la config de correo.", "warning")

    return redirect(url_for("admin.usuario_detalle", id=id))


# ── Asignaciones entrenador ↔ deportista ──────────────────────────────────────

@bp_admin.post("/asignaciones/crear")
@rol_requerido("administrador")
def crear_asignacion():
    id_entrenador = request.form.get("id_entrenador", type=int)
    id_deportista = request.form.get("id_deportista", type=int)
    id_usuario_redir = request.form.get("id_usuario_redir", type=int)

    if not id_entrenador or not id_deportista:
        flash("Faltan datos para la asignación.", "error")
        return redirect(request.referrer or url_for("admin.usuarios"))

    deportista = dr.buscar_por_id(id_deportista)
    if not deportista:
        flash("Deportista no encontrado.", "error")
        return redirect(url_for("admin.usuarios"))

    entrenador = ur.buscar_por_id(id_entrenador)
    if not entrenador or entrenador["nombre_rol"] != "entrenador":
        flash("El usuario seleccionado no es entrenador.", "error")
        return redirect(url_for("admin.usuarios"))

    dr.crear_asignacion(id_entrenador, id_deportista)
    audit(
        "ASIGNACION_CREADA",
        int(current_user.get_id()),
        request.remote_addr,
        detalle={"id_entrenador": id_entrenador, "id_deportista": id_deportista},
    )
    flash("Asignación creada correctamente.", "success")

    redir_id = id_usuario_redir or id_entrenador
    return redirect(url_for("admin.usuario_detalle", id=redir_id))


@bp_admin.post("/asignaciones/<int:id_asignacion>/eliminar")
@rol_requerido("administrador")
def eliminar_asignacion(id_asignacion: int):
    id_usuario_redir = request.form.get("id_usuario_redir", type=int)
    dr.eliminar_asignacion(id_asignacion)
    audit(
        "ASIGNACION_ELIMINADA",
        int(current_user.get_id()),
        request.remote_addr,
        detalle={"id_asignacion": id_asignacion},
    )
    flash("Asignación eliminada.", "success")
    if id_usuario_redir:
        return redirect(url_for("admin.usuario_detalle", id=id_usuario_redir))
    return redirect(url_for("admin.usuarios"))


# ── Gestión de dispositivos ───────────────────────────────────────────────────

@bp_admin.get("/dispositivos")
@rol_requerido("administrador")
def dispositivos():
    lista = dispr.listar_todos()
    return render_template("admin/dispositivos.html", dispositivos=lista)


@bp_admin.route("/dispositivos/crear", methods=["GET", "POST"])
@rol_requerido("administrador")
def crear_dispositivo():
    deportistas = dr.listar_todos()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        mac    = request.form.get("mac", "").strip() or None

        if not nombre:
            flash("El nombre del dispositivo es obligatorio.", "error")
            return render_template("admin/crear_dispositivo.html", deportistas=deportistas)

        if mac and dispr.buscar_por_mac(mac):
            flash(f"Ya existe un dispositivo registrado con la MAC {mac}.", "error")
            return render_template("admin/crear_dispositivo.html", deportistas=deportistas)

        # Genera API key en claro — se muestra UNA sola vez
        api_key = generar_token_url(32)
        api_key_hash = hash_password(api_key)

        resultado = dispr.registrar(nombre, api_key_hash, mac)
        id_disp   = resultado["id_dispositivo"]
        codigo    = resultado["codigo_dispositivo"]

        # Registrar sensores por defecto (NEO-7M=GPS, AD8232=ECG, MPU-6050=IMU)
        # Los id_tipo_sensor corresponden al orden del seed: ECG=1, GPS=2, IMU=3
        sensores_defecto = [
            {"id_tipo_sensor": 1, "modelo": "AD8232",  "config_pines": "OUTPUT=34,LO+=35,LO-=32"},
            {"id_tipo_sensor": 2, "modelo": "NEO-7M",  "config_pines": "TX=16(RX2),RX=17(TX2)"},
            {"id_tipo_sensor": 3, "modelo": "MPU-6050", "config_pines": "SDA=21,SCL=22"},
        ]
        dispr.registrar_sensores(id_disp, sensores_defecto)

        id_deportista = request.form.get("id_deportista", type=int)
        if id_deportista:
            dispr.asignar_deportista(id_disp, id_deportista)

        audit(
            "DISPOSITIVO_CREADO",
            int(current_user.get_id()),
            request.remote_addr,
            detalle={"id_dispositivo": id_disp, "codigo": codigo},
        )

        # Renderiza la pantalla de API key (mostrada una sola vez)
        return render_template(
            "admin/dispositivo_api_key.html",
            codigo=codigo,
            api_key=api_key,
            id_dispositivo=id_disp,
        )

    return render_template("admin/crear_dispositivo.html", deportistas=deportistas)


@bp_admin.get("/dispositivos/<int:id>")
@rol_requerido("administrador")
def dispositivo_detalle(id: int):
    disp = dispr.buscar_por_id(id)
    if not disp:
        abort(404)
    sensores    = dispr.listar_sensores(id)
    deportistas = dr.listar_todos()
    return render_template(
        "admin/dispositivo_detalle.html",
        disp=disp,
        sensores=sensores,
        deportistas=deportistas,
    )


@bp_admin.post("/dispositivos/<int:id>/asignar")
@rol_requerido("administrador")
def asignar_dispositivo(id: int):
    disp = dispr.buscar_por_id(id)
    if not disp:
        abort(404)

    id_deportista = request.form.get("id_deportista", type=int) or None
    dispr.asignar_deportista(id, id_deportista)
    audit(
        "DISPOSITIVO_ASIGNADO",
        int(current_user.get_id()),
        request.remote_addr,
        detalle={"id_dispositivo": id, "id_deportista": id_deportista},
    )
    flash("Dispositivo asignado correctamente.", "success")
    return redirect(url_for("admin.dispositivo_detalle", id=id))


# ── Crear sesión de entrenamiento ────────────────────────────────────────────

@bp_admin.route("/sesiones/crear", methods=["GET", "POST"])
@rol_requerido("administrador")
def crear_sesion():
    deportistas = dr.listar_todos()
    dispositivos = [d for d in dispr.listar_todos() if d.get("estado") == "activo"]

    if request.method == "POST":
        id_deportista = request.form.get("id_deportista", type=int)
        id_dispositivo = request.form.get("id_dispositivo", type=int) or None
        titulo = request.form.get("titulo", "").strip() or None

        if not id_deportista:
            flash("Selecciona un deportista.", "error")
            return render_template(
                "admin/crear_sesion.html",
                deportistas=deportistas,
                dispositivos=dispositivos,
            )

        if sesionr.sesion_en_curso(id_deportista):
            flash("El deportista ya tiene una sesión en curso. Finalizala antes de crear una nueva.", "error")
            return render_template(
                "admin/crear_sesion.html",
                deportistas=deportistas,
                dispositivos=dispositivos,
            )

        sesion = sesionr.crear_sesion(id_deportista, id_dispositivo, titulo)
        audit(
            "SESION_CREADA",
            int(current_user.get_id()),
            request.remote_addr,
            detalle={"id_sesion": sesion["id_sesion"], "id_deportista": id_deportista},
        )
        return render_template("admin/sesion_creada.html", sesion=sesion)

    return render_template(
        "admin/crear_sesion.html",
        deportistas=deportistas,
        dispositivos=dispositivos,
    )


# ── Bitácora de auditoría ─────────────────────────────────────────────────────

@bp_admin.get("/auditoria")
@rol_requerido("administrador")
def auditoria():
    pagina      = max(1, request.args.get("p", 1, type=int))
    id_usuario  = request.args.get("usuario", type=int)
    accion_f    = request.args.get("accion", "").strip() or None

    filas   = sr.listar_auditoria(pagina, _POR_PAGINA, id_usuario, accion_f)
    total   = sr.contar_auditoria(id_usuario, accion_f)
    paginas = max(1, (total + _POR_PAGINA - 1) // _POR_PAGINA)

    return render_template(
        "admin/auditoria.html",
        eventos=filas,
        pagina=pagina,
        paginas=paginas,
        total=total,
        filtros={"usuario": id_usuario or "", "accion": accion_f or ""},
    )
