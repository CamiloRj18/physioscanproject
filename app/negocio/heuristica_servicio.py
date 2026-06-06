"""Motor heurístico: evalúa umbrales y emite alertas en tiempo casi real."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.datos import alerta_repositorio as ar
from app.datos.base_repositorio import muchos, uno

_VENTANA_IDEMPOTENCIA_S = 30


def _obtener_umbrales(id_deportista: int | None) -> list[dict[str, Any]]:
    """Umbrales globales + personalizados del deportista (los personalizados van primero)."""
    return muchos(
        """
        SELECT * FROM umbral_heuristico
        WHERE activo = TRUE
          AND (id_deportista IS NULL OR id_deportista = %s)
        ORDER BY id_deportista DESC
        """,
        (id_deportista,),
    )


def _fcmax(id_deportista: int | None) -> float:
    """FC máxima: usa fc_max_estimada del deportista, o calcula 208-0.7*edad, o 200."""
    if id_deportista is None:
        return 200.0
    try:
        from app.datos import deportista_repositorio as dr
        dep = dr.buscar_por_id(id_deportista)
        if not dep:
            return 200.0
        if dep.get("fc_max_estimada"):
            return float(dep["fc_max_estimada"])
        if dep.get("fecha_nacimiento"):
            from datetime import date
            fecha_nac = dep["fecha_nacimiento"]
            if isinstance(fecha_nac, date):
                edad = (date.today() - fecha_nac).days // 365
                return max(100.0, 208.0 - 0.7 * edad)
    except Exception:
        pass
    return 200.0


def _es_duplicado(id_sesion: int, tipo: str) -> bool:
    """True si ya existe una alerta del mismo tipo en los últimos _VENTANA_IDEMPOTENCIA_S s."""
    ultima = ar.ultima_alerta_por_tipo(id_sesion, tipo)
    if not ultima:
        return False
    ts = ultima.get("capturado_en")
    if ts is None:
        return False
    try:
        if isinstance(ts, datetime):
            ts_dt = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        else:
            ts_dt = datetime.fromisoformat(str(ts)).replace(tzinfo=timezone.utc)
        ahora = datetime.now(timezone.utc)
        return (ahora - ts_dt).total_seconds() < _VENTANA_IDEMPOTENCIA_S
    except Exception:
        return False


def _evaluar_op(valor: float, operador: str, umbral: float) -> bool:
    ops = {
        ">":  valor >  umbral,
        ">=": valor >= umbral,
        "<":  valor <  umbral,
        "<=": valor <= umbral,
        "==": valor == umbral,
    }
    return ops.get(operador, False)


def evaluar_lote(id_sesion: int, id_deportista: int | None,
                 ecg: list[dict], gps: list[dict], imu: list[dict]) -> list[dict]:
    """Evalúa el lote de muestras contra umbrales y registra alertas (idempotente)."""
    umbrales = _obtener_umbrales(id_deportista)
    fc_max = _fcmax(id_deportista)
    alertas: list[dict] = []
    ts = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # ── ECG: electrodo suelto y %FCmáx ────────────────────────────────────────
    electrodo_revisado = False
    for m in ecg:
        if m.get("electrodo_suelto") and not electrodo_revisado:
            electrodo_revisado = True
            if not _es_duplicado(id_sesion, "electrodo_suelto"):
                ar.registrar_alerta(id_sesion, "electrodo_suelto", "amarillo",
                                    "Electrodo suelto detectado.", ts)
                alertas.append({"tipo": "electrodo_suelto", "severidad": "amarillo",
                                 "mensaje": "Electrodo suelto detectado."})

        bpm = float(m.get("bpm") or 0) or (40 + (float(m.get("valor_adc", 0)) / 4095.0) * 160)
        porcentaje = (bpm / fc_max) * 100.0

        for u in umbrales:
            if u["parametro"] not in ("fc_porcentaje_max", "fc_bpm"):
                continue
            if _evaluar_op(porcentaje, u["operador"], float(u["valor"])):
                tipo = "sobreesfuerzo_cardiaco"
                if not _es_duplicado(id_sesion, tipo):
                    ar.registrar_alerta(id_sesion, tipo, u["severidad"],
                                        u["mensaje"], ts, bpm)
                    alertas.append({"tipo": tipo, "severidad": u["severidad"],
                                     "mensaje": u["mensaje"]})
                break  # un solo disparo por muestra

    # ── IMU: inclinación de caída ──────────────────────────────────────────────
    for m in imu:
        inc = m.get("inclinacion_grados")
        if inc is None:
            continue
        for u in umbrales:
            if u["parametro"] not in ("inclinacion_grados", "inclinacion_caida"):
                continue
            if _evaluar_op(float(inc), u["operador"], float(u["valor"])):
                tipo = "caida_postura"
                if not _es_duplicado(id_sesion, tipo):
                    ar.registrar_alerta(id_sesion, tipo, u["severidad"],
                                        u["mensaje"], ts, float(inc))
                    alertas.append({"tipo": tipo, "severidad": u["severidad"],
                                     "mensaje": u["mensaje"]})
                break

    # ── ECG: recuperación cardíaca lenta (requiere contexto de lote previo) ───
    if len(ecg) >= 2:
        bpm_vals = [
            float(m.get("bpm") or 0) or (40 + (float(m.get("valor_adc", 0)) / 4095.0) * 160)
            for m in ecg
        ]
        delta_bpm = bpm_vals[-1] - bpm_vals[0]
        for u in umbrales:
            if u["parametro"] != "fc_recuperacion_bpm":
                continue
            # Umbral: si la reducción de BPM en el lote es menor que lo esperado
            if _evaluar_op(delta_bpm, u["operador"], float(u["valor"])):
                tipo = "fatiga"
                if not _es_duplicado(id_sesion, tipo):
                    ar.registrar_alerta(id_sesion, tipo, u["severidad"],
                                        u["mensaje"], ts, delta_bpm)
                    alertas.append({"tipo": tipo, "severidad": u["severidad"],
                                     "mensaje": u["mensaje"]})
                break

    return alertas


def evaluar(id_sesion: int, muestras_recientes: dict[str, list]) -> list[dict]:
    """Punto de entrada público. Carga id_deportista desde la sesión y delega."""
    sesion: dict | None = None
    try:
        from app.datos import sesion_repositorio as sr
        sesion = sr.buscar_por_id(id_sesion)
    except Exception:
        pass
    id_deportista = sesion.get("id_deportista") if sesion else None
    ecg = muestras_recientes.get("ecg", [])
    gps = muestras_recientes.get("gps", [])
    imu = muestras_recientes.get("imu", [])
    return evaluar_lote(id_sesion, id_deportista, ecg, gps, imu)
