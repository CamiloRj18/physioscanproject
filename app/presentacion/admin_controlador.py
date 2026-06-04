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
"""
from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from app.comun.decoradores import rol_requerido
from app.comun.errores import ConflictoError, ValidacionError
from app.comun.validadores import validar_contrasena, validar_email
from app.datos import deportista_repositorio as dr
from app.datos import seguridad_repositorio as sr
from app.datos import usuario_repositorio as ur
from app.negocio.seguridad import recuperacion_archivo_servicio as ras
from app.negocio.seguridad.auditoria_servicio import registrar as audit
from app.negocio.seguridad.contrasena_servicio import hash_nueva, validar_politica

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")

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

        # Generar lote de recuperación inicial para el nuevo usuario
        try:
            _, contenido_txt, nombre_archivo = ras.generar_lote(id_nuevo, int(current_user.get_id()))
        except Exception as exc:
            current_app.logger.warning("Lote recuperación no generado para %s: %s", id_nuevo, exc)
            contenido_txt  = None
            nombre_archivo = None

        audit(
            "USUARIO_CREADO_ADMIN",
            int(current_user.get_id()),
            request.remote_addr,
            detalle={"id_nuevo": id_nuevo, "email": form["email"]},
        )

        flash(f"Usuario creado correctamente (id={id_nuevo}).", "success")

        if contenido_txt:
            resp = make_response(contenido_txt)
            resp.headers["Content-Type"]        = "text/plain; charset=utf-8"
            resp.headers["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
            resp.headers["Cache-Control"]       = "no-store"
            return resp

        return redirect(url_for("admin.usuario_detalle", id=id_nuevo))

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

    return render_template(
        "admin/usuario_detalle.html",
        usuario=usuario,
        lote_activo=lote_activo,
        deportista=deportista,
        asignaciones=asignaciones,
        entrenadores=entrenadores,
        deportistas_todos=deportistas_todos,
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
            _, contenido_txt, nombre_archivo = ras.generar_lote(id, generado_por=id_admin)
        except ValidacionError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.usuario_detalle", id=id))

        audit(
            "LOTE_REEMITIDO",
            id_admin,
            request.remote_addr,
            detalle={"id_usuario_objetivo": id, "lote_anterior": lote_actual["id_lote"] if lote_actual else None},
        )

        resp = make_response(contenido_txt)
        resp.headers["Content-Type"]        = "text/plain; charset=utf-8"
        resp.headers["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
        resp.headers["Cache-Control"]       = "no-store"
        return resp

    return render_template(
        "admin/reemitir_recuperacion.html",
        usuario=usuario,
        lote_actual=lote_actual,
    )


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
