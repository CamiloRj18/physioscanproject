"""Controlador API de ingesta: /api/v1 — recibe datos del chaleco ESP32.

Exento de CSRF (API de dispositivo autenticada por HMAC + api_key_hash).
"""
from __future__ import annotations

from flask import Blueprint, current_app, request

from app.comun.errores import AutenticacionError, ValidacionError
from app.comun.respuestas import error, no_autorizado, ok
from app.extensions import limiter
from app.negocio import ingesta_servicio as isrv

bp_api_ingesta = Blueprint("api_ingesta", __name__, url_prefix="/api/v1")

_LIMITE_INGESTA = "120 per minute"


def _autenticar_request() -> dict:
    """Extrae cabeceras y delega la autenticación HMAC en el servicio."""
    codigo    = request.headers.get("X-Device-Code", "").strip()
    api_key   = request.headers.get("X-Device-Key", "").strip()
    timestamp = request.headers.get("X-Timestamp", "").strip()
    signature = request.headers.get("X-Signature", "").strip()

    if not all([codigo, api_key, timestamp, signature]):
        raise AutenticacionError("Cabeceras de autenticación incompletas.")

    return isrv.autenticar_dispositivo(
        codigo, api_key, timestamp, signature,
        body_raw=request.get_data(),
    )


# ── POST /api/v1/sesiones/iniciar ────────────────────────────────────────────

@bp_api_ingesta.post("/sesiones/iniciar")
@limiter.limit(_LIMITE_INGESTA)
def iniciar_sesion():
    try:
        _autenticar_request()
        cuerpo = request.get_json(force=True, silent=True) or {}
        codigo = cuerpo.get("codigo_dispositivo", "").strip()
        if not codigo:
            return error("Falta codigo_dispositivo.", 422)
        resultado = isrv.iniciar_sesion(codigo)
        return ok(resultado)
    except AutenticacionError as exc:
        return no_autorizado(str(exc))
    except ValidacionError as exc:
        return error(str(exc), 422)
    except Exception as exc:
        current_app.logger.exception("iniciar_sesion: %s", exc)
        return error("Error interno.", 500)


# ── POST /api/v1/sesiones/<id>/lecturas ──────────────────────────────────────

@bp_api_ingesta.post("/sesiones/<int:id_sesion>/lecturas")
@limiter.limit(_LIMITE_INGESTA)
def registrar_lecturas(id_sesion: int):
    try:
        _autenticar_request()
        payload = request.get_json(force=True, silent=True) or {}
        resultado = isrv.registrar_lecturas(id_sesion, payload)
        return ok(resultado)
    except AutenticacionError as exc:
        return no_autorizado(str(exc))
    except ValidacionError as exc:
        return error(str(exc), 422)
    except Exception as exc:
        current_app.logger.exception("registrar_lecturas(sesion=%s): %s", id_sesion, exc)
        return error("Error interno.", 500)


# ── POST /api/v1/sesiones/<id>/finalizar ─────────────────────────────────────

@bp_api_ingesta.post("/sesiones/<int:id_sesion>/finalizar")
@limiter.limit(_LIMITE_INGESTA)
def finalizar_sesion(id_sesion: int):
    try:
        _autenticar_request()
        resultado = isrv.finalizar_sesion(id_sesion)
        return ok(resultado)
    except AutenticacionError as exc:
        return no_autorizado(str(exc))
    except ValidacionError as exc:
        return error(str(exc), 422)
    except Exception as exc:
        current_app.logger.exception("finalizar_sesion(sesion=%s): %s", id_sesion, exc)
        return error("Error interno.", 500)


# ── GET /api/v1/sesiones/<id>/tiempo-real ────────────────────────────────────

def _autorizar_sesion(sesion: dict, usuario) -> bool:
    """Verifica que el usuario autenticado puede acceder a la sesión."""
    nombre_rol = getattr(usuario, "nombre_rol", None)
    if nombre_rol == "administrador":
        return True
    try:
        from app.datos import deportista_repositorio as dr
        if nombre_rol == "deportista":
            dep = dr.buscar_por_id_usuario(usuario.id_usuario)
            return bool(dep and dep["id_deportista"] == sesion.get("id_deportista"))
        if nombre_rol == "entrenador":
            asig = dr.buscar_asignacion(usuario.id_usuario, sesion.get("id_deportista"))
            return asig is not None
    except Exception:
        pass
    return False


@bp_api_ingesta.get("/sesiones/<int:id_sesion>/tiempo-real")
def tiempo_real(id_sesion: int):
    """Datos en vivo de una sesión para el navegador (requiere login + autorización)."""
    from flask_login import current_user
    if not current_user.is_authenticated:
        return no_autorizado("Inicia sesión para acceder.")
    try:
        from app.datos import alerta_repositorio as ar
        from app.datos import lectura_repositorio as lr
        from app.datos import sesion_repositorio as sr

        sesion = sr.buscar_por_id(id_sesion)
        if not sesion:
            return error("Sesión no encontrada.", 404)

        if not _autorizar_sesion(sesion, current_user):
            return no_autorizado("Sin acceso a esta sesión.")

        ultima_ecg = lr.ultima_lectura_ecg(id_sesion)
        ultima_imu = lr.ultima_lectura_imu(id_sesion)
        recorrido  = lr.recorrido_gps_reciente(id_sesion, 50)
        alertas    = ar.listar_recientes(id_sesion, 10)

        adc = ultima_ecg["valor_adc"] if ultima_ecg else None
        bpm_raw = ultima_ecg.get("bpm") if ultima_ecg else None
        bpm = int(bpm_raw) if bpm_raw else (int(40 + (adc / 4095.0) * 160) if adc is not None else None)
        inc = float(ultima_imu["inclinacion_grados"]) if ultima_imu and ultima_imu.get("inclinacion_grados") else None

        return ok({
            "ultimo_bpm":  bpm,
            "inclinacion": inc,
            "recorrido":   [[float(p["latitud"]), float(p["longitud"])] for p in reversed(recorrido)],
            "alertas":     [
                {"tipo": a["tipo"], "severidad": a["severidad"], "mensaje": a["mensaje"]}
                for a in alertas
            ],
        })
    except Exception as exc:
        current_app.logger.exception("tiempo_real(sesion=%s): %s", id_sesion, exc)
        return error("Error interno.", 500)


# ── GET /api/v1/sesiones/<id>/datos-graficas ─────────────────────────────────

@bp_api_ingesta.get("/sesiones/<int:id_sesion>/datos-graficas")
def datos_graficas(id_sesion: int):
    """Series temporales para las gráficas del detalle de sesión (requiere login)."""
    from flask_login import current_user
    if not current_user.is_authenticated:
        return no_autorizado("Inicia sesión para acceder.")
    try:
        from app.datos import lectura_repositorio as lr
        from app.datos import sesion_repositorio as sr

        sesion = sr.buscar_por_id(id_sesion)
        if not sesion:
            return error("Sesión no encontrada.", 404)
        if not _autorizar_sesion(sesion, current_user):
            return no_autorizado("Sin acceso a esta sesión.")

        def _fmt_ts(v) -> str:
            return v.isoformat() if hasattr(v, "isoformat") else str(v)

        bpm_serie    = lr.serie_bpm(id_sesion, 300)
        inc_serie    = lr.serie_inclinacion(id_sesion, 300)
        vel_serie    = lr.serie_velocidad(id_sesion, 200)
        ruta         = lr.recorrido_gps(id_sesion)

        return ok({
            "bpm":        [{"t": _fmt_ts(r["capturado_en"]), "v": int(r["bpm_calc"])} for r in bpm_serie],
            "inclinacion":[{"t": _fmt_ts(r["capturado_en"]), "v": float(r["inclinacion_grados"])} for r in inc_serie],
            "velocidad":  [{"t": _fmt_ts(r["capturado_en"]), "v": float(r["velocidad_kmh"])} for r in vel_serie],
            "ruta":       [[float(r["latitud"]), float(r["longitud"])] for r in ruta],
        })
    except Exception as exc:
        current_app.logger.exception("datos_graficas(sesion=%s): %s", id_sesion, exc)
        return error("Error interno.", 500)
