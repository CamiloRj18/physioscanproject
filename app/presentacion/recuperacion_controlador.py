"""Controlador de recuperación: reset por correo + por archivo de 12 códigos.

Rutas:
    GET      /recuperar/                        → landing (elige método)
    GET/POST /recuperar/correo                  → solicitar reset por correo
    GET/POST /recuperar/correo/<token>          → fijar nueva contraseña (token)
    GET/POST /recuperar/archivo                 → usar código del archivo de 12
"""
from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_mail import Message

from app.comun.errores import AutenticacionError, BloqueadoError, ValidacionError
from app.comun.validadores import validar_email
from app.extensions import limiter, mail
from app.negocio.seguridad import recuperacion_archivo_servicio as ras
from app.negocio.seguridad import recuperacion_email_servicio as res

bp_recuperacion = Blueprint("recuperacion", __name__, url_prefix="/recuperar")

_RATE_CORREO  = "5 per minute;20 per hour"
_RATE_ARCHIVO = "5 per minute;15 per hour"

_MAX_INTENTOS_ARCHIVO = 5


# ── Landing ──────────────────────────────────────────────────────────────────

@bp_recuperacion.get("/")
def inicio():
    return render_template("recuperacion/solicitar.html")


# ── Reset por correo ──────────────────────────────────────────────────────────

@bp_recuperacion.route("/correo", methods=["GET", "POST"])
@limiter.limit(_RATE_CORREO)
def correo_solicitar():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        if not validar_email(email):
            flash("El correo no tiene un formato válido.", "error")
            return render_template("recuperacion/correo.html")

        resultado = res.solicitar_reset(email, request.remote_addr)
        if resultado:
            nombre, email_dest, token = resultado
            _enviar_email_reset(email_dest, nombre, token)

        # Respuesta siempre genérica: anti-enumeración
        flash(
            "Si el correo está registrado y la cuenta está activa, "
            "recibirás un enlace de recuperación en los próximos minutos.",
            "info",
        )
        return redirect(url_for("recuperacion.correo_solicitar"))

    return render_template("recuperacion/correo.html")


@bp_recuperacion.route("/correo/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def correo_nueva(token: str):
    """Permite fijar la nueva contraseña usando el token del correo."""
    # Validar token antes de mostrar el formulario
    try:
        datos = res.validar_token(token)
    except AutenticacionError:
        flash("El enlace de recuperación no es válido o ha expirado.", "error")
        return redirect(url_for("recuperacion.correo_solicitar"))

    if request.method == "POST":
        nueva   = request.form.get("password", "")
        confirm = request.form.get("password2", "")

        if nueva != confirm:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("recuperacion/nueva_contrasena.html", token=token)

        try:
            res.restablecer(token, nueva, request.remote_addr)
            flash("Contraseña actualizada correctamente. Ya puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login"))
        except AutenticacionError as exc:
            flash(str(exc), "error")
            return redirect(url_for("recuperacion.correo_solicitar"))
        except ValidacionError as exc:
            flash(str(exc), "error")
            return render_template("recuperacion/nueva_contrasena.html", token=token)

    return render_template("recuperacion/nueva_contrasena.html", token=token)


# ── Recuperación por archivo de 12 códigos ────────────────────────────────────

@bp_recuperacion.route("/archivo", methods=["GET", "POST"])
@limiter.limit(_RATE_ARCHIVO)
def archivo_form():
    """Permite recuperar la cuenta usando un código del archivo de 12."""
    # Bloqueo por sesión tras demasiados intentos fallidos
    intentos = session.get("intentos_archivo", 0)
    if intentos >= _MAX_INTENTOS_ARCHIVO:
        return render_template(
            "recuperacion/por_archivo.html",
            bloqueado=True,
            max_intentos=_MAX_INTENTOS_ARCHIVO,
        )

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        codigo   = request.form.get("codigo", "").strip()
        nueva    = request.form.get("password", "")
        confirm  = request.form.get("password2", "")

        # Validación de formato en el controlador
        if not validar_email(email):
            flash("El correo no tiene un formato válido.", "error")
            return render_template("recuperacion/por_archivo.html", bloqueado=False)

        if not codigo:
            flash("El código es obligatorio.", "error")
            return render_template("recuperacion/por_archivo.html", bloqueado=False)

        if nueva != confirm:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("recuperacion/por_archivo.html", bloqueado=False)

        try:
            ras.recuperar_con_codigo(email, codigo, nueva, request.remote_addr)
            session.pop("intentos_archivo", None)
            flash("Contraseña actualizada correctamente. Ya puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login"))

        except AutenticacionError as exc:
            session["intentos_archivo"] = intentos + 1
            flash(str(exc), "error")
        except (ValidacionError, BloqueadoError) as exc:
            flash(str(exc), "error")

        return render_template("recuperacion/por_archivo.html", bloqueado=False)

    return render_template("recuperacion/por_archivo.html", bloqueado=False)


# ── Helpers privados ─────────────────────────────────────────────────────────

def _enviar_email_reset(email: str, nombre: str, token: str) -> None:
    url = url_for("recuperacion.correo_nueva", token=token, _external=True)
    msg = Message(
        subject    = "Recuperación de contraseña — PhysioScan",
        recipients = [email],
        body       = (
            f"Hola {nombre},\n\n"
            f"Recibiste este correo porque solicitaste restablecer tu contraseña.\n\n"
            f"Haz clic en el siguiente enlace para continuar:\n{url}\n\n"
            "El enlace es válido por 30 minutos y solo puede usarse una vez.\n\n"
            "Si no solicitaste este cambio, ignora este mensaje. Tu contraseña no cambiará.\n\n"
            "Equipo PhysioScan — UniEspinal"
        ),
    )
    try:
        mail.send(msg)
    except Exception as exc:
        current_app.logger.warning("Email reset no enviado a %s: %s", email, exc)
