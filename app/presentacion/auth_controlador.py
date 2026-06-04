"""Controlador de autenticación: registro, login, 2FA, logout.

Rutas:
    GET/POST /auth/registro
    GET      /auth/verificar-correo?token=…
    GET      /auth/codigos-recuperacion          (una sola vez, post-registro)
    GET/POST /auth/login
    GET/POST /auth/verificar-2fa
    GET/POST /auth/logout
    GET/POST /auth/2fa/activar
"""
from __future__ import annotations

import base64
import io

import qrcode
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message
from werkzeug.routing.exceptions import BuildError

from app.comun.errores import AutenticacionError, BloqueadoError, ConflictoError, ValidacionError
from app.comun.validadores import validar_contrasena, validar_email
from app.datos import seguridad_repositorio as sr
from app.datos import usuario_repositorio as ur
from app.extensions import limiter, mail
from app.negocio import auth_servicio
from app.negocio.seguridad import doble_factor_servicio

bp_auth = Blueprint("auth", __name__, url_prefix="/auth")

_RATE_REGISTRO = "3 per minute;10 per hour"
_RATE_LOGIN    = "10 per minute;30 per hour"
_RATE_2FA      = "5 per minute"


# ── Registro ────────────────────────────────────────────────────────────────

@bp_auth.route("/registro", methods=["GET", "POST"])
@limiter.limit(_RATE_REGISTRO)
def registro():
    if current_user.is_authenticated:
        return redirect(_destino_post_login())

    form = {}
    if request.method == "POST":
        form = {
            "primer_nombre":    request.form.get("primer_nombre", "").strip(),
            "segundo_nombre":   request.form.get("segundo_nombre", "").strip() or None,
            "primer_apellido":  request.form.get("primer_apellido", "").strip(),
            "segundo_apellido": request.form.get("segundo_apellido", "").strip() or None,
            "email":            request.form.get("email", "").strip(),
            "telefono":         request.form.get("telefono", "").strip() or None,
            "password":         request.form.get("password", ""),
            "password2":        request.form.get("password2", ""),
        }

        # Validación de formato (controlador)
        if not form["primer_nombre"]:
            flash("El primer nombre es obligatorio.", "error")
        elif not form["primer_apellido"]:
            flash("El primer apellido es obligatorio.", "error")
        elif not validar_email(form["email"]):
            flash("El correo no tiene un formato válido.", "error")
        elif form["password"] != form["password2"]:
            flash("Las contraseñas no coinciden.", "error")
        elif validar_contrasena(form["password"]):
            flash(validar_contrasena(form["password"]), "error")
        else:
            try:
                id_usuario, token_v, codigos = auth_servicio.registrar_usuario(
                    primer_nombre    = form["primer_nombre"],
                    segundo_nombre   = form["segundo_nombre"],
                    primer_apellido  = form["primer_apellido"],
                    segundo_apellido = form["segundo_apellido"],
                    email            = form["email"],
                    telefono         = form["telefono"],
                    password         = form["password"],
                    ip               = request.remote_addr,
                )
            except (ConflictoError, ValidacionError) as exc:
                flash(str(exc), "error")
                return render_template("auth/registro.html", form=form)

            _enviar_email_verificacion(form["email"], form["primer_nombre"], token_v)

            fila = ur.buscar_por_id(id_usuario)
            codigo_usuario = fila["codigo_usuario"] if fila else "???????"

            session["codigos_registro"] = {
                "codigos":       codigos,
                "email":         form["email"],
                "codigo_usuario": codigo_usuario,
            }
            return redirect(url_for("auth.codigos_recuperacion"))

    return render_template("auth/registro.html", form=form)


# ── Códigos de recuperación (una sola vez) ───────────────────────────────────

@bp_auth.get("/codigos-recuperacion")
def codigos_recuperacion():
    datos = session.pop("codigos_registro", None)
    if not datos:
        flash("Los códigos de recuperación ya fueron mostrados o la sesión expiró.", "info")
        return redirect(url_for("auth.login"))
    return render_template(
        "auth/codigos_recuperacion.html",
        codigos=datos["codigos"],
        email=datos["email"],
        codigo_usuario=datos["codigo_usuario"],
    )


# ── Verificación de correo ───────────────────────────────────────────────────

@bp_auth.get("/verificar-correo")
@limiter.limit("10 per hour")
def verificar_correo():
    token = request.args.get("token", "")
    if not token:
        flash("Enlace de verificación inválido.", "error")
        return redirect(url_for("auth.login"))

    try:
        auth_servicio.verificar_email(token, request.remote_addr)
        flash("¡Correo verificado! Ya puedes iniciar sesión.", "success")
    except AutenticacionError as exc:
        flash(str(exc), "error")

    return redirect(url_for("auth.login"))


# ── Login ───────────────────────────────────────────────────────────────────

@bp_auth.route("/login", methods=["GET", "POST"])
@limiter.limit(_RATE_LOGIN)
def login():
    if current_user.is_authenticated and session.get("2fa_verificado"):
        return redirect(_destino_post_login())

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        try:
            usuario = auth_servicio.autenticar(
                email            = email,
                password         = password,
                ip               = request.remote_addr,
                user_agent       = request.user_agent.string,
                lockout_intentos = current_app.config["LOCKOUT_INTENTOS"],
                lockout_minutos  = current_app.config["LOCKOUT_MINUTOS"],
            )
        except (AutenticacionError, BloqueadoError) as exc:
            flash(str(exc), "error")
            return render_template("auth/login.html", email=email)

        from app.extensions import UsuarioProxy
        proxy = UsuarioProxy(usuario)

        datos_2fa = sr.obtener_2fa(usuario["id_usuario"])
        if datos_2fa and datos_2fa.get("habilitado"):
            session["pre_2fa_id"]     = usuario["id_usuario"]
            session["pre_2fa_metodo"] = datos_2fa["metodo"]

            if datos_2fa["metodo"] == "email":
                otp = doble_factor_servicio.generar_otp_email(
                    usuario["id_usuario"], request.remote_addr
                )
                _enviar_otp_email(usuario["email"], usuario["primer_nombre"], otp)

            return redirect(url_for("auth.verificar_2fa"))

        # Sin 2FA: login directo
        login_user(proxy, remember=False)
        session["2fa_verificado"] = True
        token_srv = auth_servicio.crear_sesion_servidor(
            usuario["id_usuario"], request.remote_addr, request.user_agent.string
        )
        session["_sesion_srv"] = token_srv
        return redirect(_destino_post_login())

    return render_template("auth/login.html")


# ── Verificar 2FA ───────────────────────────────────────────────────────────

@bp_auth.route("/verificar-2fa", methods=["GET", "POST"])
@limiter.limit(_RATE_2FA)
def verificar_2fa():
    id_usuario = session.get("pre_2fa_id")
    if not id_usuario:
        return redirect(url_for("auth.login"))

    metodo = session.get("pre_2fa_metodo", "totp")

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip().replace(" ", "").replace("-", "")

        try:
            if metodo == "totp":
                doble_factor_servicio.verificar_totp(
                    id_usuario, codigo, current_app.config["FERNET_KEY"],
                    request.remote_addr,
                )
            else:
                doble_factor_servicio.verificar_otp_email(
                    id_usuario, codigo, request.remote_addr
                )
        except AutenticacionError as exc:
            flash(str(exc), "error")
            return render_template("auth/verificar_2fa.html", metodo=metodo)

        fila = ur.buscar_por_id(id_usuario)
        if not fila:
            flash("Error al cargar el usuario.", "error")
            return redirect(url_for("auth.login"))

        from app.extensions import UsuarioProxy
        proxy = UsuarioProxy(fila)
        login_user(proxy, remember=False)
        session["2fa_verificado"] = True
        session.pop("pre_2fa_id", None)
        session.pop("pre_2fa_metodo", None)

        token_srv = auth_servicio.crear_sesion_servidor(
            id_usuario, request.remote_addr, request.user_agent.string
        )
        session["_sesion_srv"] = token_srv
        return redirect(_destino_post_login())

    return render_template("auth/verificar_2fa.html", metodo=metodo)


# ── Logout ──────────────────────────────────────────────────────────────────

@bp_auth.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    token_srv = session.get("_sesion_srv")
    if token_srv:
        try:
            auth_servicio.revocar_sesion_servidor(token_srv)
        except Exception:
            pass

    logout_user()
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("publico.home"))


# ── Activar 2FA ─────────────────────────────────────────────────────────────

@bp_auth.route("/2fa/activar", methods=["GET", "POST"])
@login_required
def activar_2fa():
    if not session.get("2fa_verificado"):
        return redirect(url_for("auth.verificar_2fa"))

    id_usuario  = int(current_user.get_id())
    fernet_key  = current_app.config["FERNET_KEY"]

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip().replace(" ", "")
        try:
            doble_factor_servicio.confirmar_totp(
                id_usuario, codigo, fernet_key, request.remote_addr
            )
            flash("Autenticación en dos pasos activada.", "success")
            return redirect(_destino_post_login())
        except (AutenticacionError, ValidacionError) as exc:
            flash(str(exc), "error")
            # Regresa al GET para regenerar QR con el mismo secreto pendiente

    secreto_claro, secreto_cifrado = doble_factor_servicio.generar_secreto_totp(fernet_key)
    uri = doble_factor_servicio.uri_totp(current_user.email, secreto_claro)
    doble_factor_servicio.activar_totp(id_usuario, secreto_cifrado)

    return render_template(
        "auth/activar_2fa.html",
        qr_data_url   = _qr_data_url(uri),
        secreto_claro = secreto_claro,
    )


# ── Helpers privados ─────────────────────────────────────────────────────────

def _destino_post_login() -> str:
    destino = request.args.get("next", "")
    if destino and destino.startswith("/") and not destino.startswith("//"):
        return destino
    if current_user.is_authenticated:
        rol = getattr(current_user, "nombre_rol", None)
        try:
            if rol == "administrador":
                return url_for("admin.panel")
            if rol == "entrenador":
                return url_for("entrenador.deportistas")
            if rol == "deportista":
                return url_for("deportista.sesiones")
            if rol == "usuario":
                return url_for("usuario.perfil")
        except BuildError:
            pass
    return url_for("publico.home")


def _enviar_email_verificacion(email: str, nombre: str, token: str) -> None:
    url = url_for("auth.verificar_correo", token=token, _external=True)
    msg = Message(
        subject    = "Verifica tu correo — PhysioScan",
        recipients = [email],
        body       = (
            f"Hola {nombre},\n\n"
            f"Confirma tu dirección de correo haciendo clic en:\n{url}\n\n"
            "El enlace es válido por 24 horas.\n\n"
            "Si no creaste esta cuenta, ignora este mensaje.\n\n"
            "Equipo PhysioScan — UniEspinal"
        ),
    )
    try:
        mail.send(msg)
    except Exception as exc:
        current_app.logger.warning("Email verificación no enviado a %s: %s", email, exc)


def _enviar_otp_email(email: str, nombre: str, codigo: str) -> None:
    msg = Message(
        subject    = "Código de verificación — PhysioScan",
        recipients = [email],
        body       = (
            f"Hola {nombre},\n\n"
            f"Tu código de acceso es:\n\n    {codigo}\n\n"
            "Válido por 5 minutos. No lo compartas.\n\n"
            "Equipo PhysioScan — UniEspinal"
        ),
    )
    try:
        mail.send(msg)
    except Exception as exc:
        current_app.logger.warning("OTP email no enviado a %s: %s", email, exc)


def _qr_data_url(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
