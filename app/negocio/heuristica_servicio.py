"""Motor heurístico: evalúa umbrales y emite alertas en tiempo casi real."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.datos import alerta_repositorio as ar
from app.datos.base_repositorio import muchos


def _obtener_umbrales(id_deportista: int | None) -> list[dict[str, Any]]:
    """Carga umbrales globales + los del deportista (los personalizados tienen prioridad)."""
    return muchos(
        """
        SELECT * FROM umbral_heuristico
        WHERE activo = TRUE
          AND (id_deportista IS NULL OR id_deportista = %s)
        ORDER BY id_deportista DESC
        """,
        (id_deportista,),
    )


def _evaluar(valor: float, operador: str, umbral: float) -> bool:
    ops = {">": valor > umbral, ">=": valor >= umbral,
           "<": valor < umbral, "<=": valor <= umbral, "==": valor == umbral}
    return ops.get(operador, False)


def evaluar_lote(id_sesion: int, id_deportista: int | None,
                 ecg: list[dict], gps: list[dict], imu: list[dict]) -> list[dict]:
    """Evalúa el lote de muestras contra los umbrales y registra las alertas disparadas."""
    umbrales = _obtener_umbrales(id_deportista)
    alertas: list[dict] = []
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # --- ECG: electrodo suelto y FC estimada ---
    for m in ecg:
        if m.get("electrodo_suelto"):
            ar.registrar_alerta(
                id_sesion, "electrodo_suelto", "amarillo",
                "Electrodo suelto detectado.", ts,
            )
            alertas.append({"tipo": "electrodo_suelto", "severidad": "amarillo",
                             "mensaje": "Electrodo suelto detectado."})
            break

        # Proxy ADC→BPM (escala lineal simplificada)
        adc = m.get("valor_adc", 0)
        fc_estimada = 40 + (adc / 4095) * 160
        # Evalúa umbrales de % FCmáx (fc_porcentaje_max): necesitamos FCmáx del deportista.
        # Proxy: usamos fc_estimada como porcentaje de 200 BPM (FCmáx por defecto simplificada).
        for u in umbrales:
            if u["parametro"] not in ("fc_porcentaje_max", "fc_bpm"):
                continue
            porcentaje = (fc_estimada / 200.0) * 100.0
            if _evaluar(porcentaje, u["operador"], float(u["valor"])):
                ar.registrar_alerta(id_sesion, "sobreesfuerzo_cardiaco",
                                    u["severidad"], u["mensaje"], ts, fc_estimada)
                alertas.append({"tipo": "sobreesfuerzo_cardiaco",
                                 "severidad": u["severidad"], "mensaje": u["mensaje"]})

    # --- IMU: inclinación de caída ---
    for m in imu:
        inc = m.get("inclinacion_grados")
        if inc is None:
            continue
        for u in umbrales:
            if u["parametro"] not in ("inclinacion_grados", "inclinacion_caida"):
                continue
            if _evaluar(float(inc), u["operador"], float(u["valor"])):
                ar.registrar_alerta(id_sesion, "caida_postura",
                                    u["severidad"], u["mensaje"], ts, float(inc))
                alertas.append({"tipo": "caida_postura",
                                 "severidad": u["severidad"], "mensaje": u["mensaje"]})

    return alertas
