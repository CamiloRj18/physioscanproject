# Contrato API de Ingesta — PhysioScan v1

Todos los endpoints viven bajo `/api/v1`. Las respuestas siempre tienen la estructura:
```json
{ "ok": true|false, "datos": <objeto>, "error": null|"mensaje" }
```

---

## Autenticación de dispositivo

Cada petición del chaleco debe incluir estas 4 cabeceras:

| Cabecera | Descripción |
|---|---|
| `X-Device-Code` | Código del dispositivo, p.ej. `CHAL0001` |
| `X-Device-Key` | API key en claro (se compara contra `api_key_hash` Argon2id) |
| `X-Timestamp` | Epoch Unix en segundos (entero). Se rechaza si el desfase con el servidor supera 60 s (anti-replay) |
| `X-Signature` | `HMAC-SHA256(api_key, device_code + timestamp + body_bytes)` en hexadecimal |

**Cálculo de la firma (Python):**
```python
import hashlib, hmac, time
ts   = str(int(time.time()))
body = b'{"codigo_dispositivo":"CHAL0001"}'
sig  = hmac.new(api_key.encode(), (device_code + ts).encode() + body, hashlib.sha256).hexdigest()
```

**Errores de autenticación:**
| Código | Causa |
|---|---|
| `401` | Cabeceras incompletas, dispositivo no encontrado, api_key incorrecta o firma inválida |
| `403` | Dispositivo inactivo o en mantenimiento |

---

## Endpoints

### POST `/api/v1/sesiones/iniciar`

Crea una sesión de entrenamiento para el deportista asignado al dispositivo.

**Body:**
```json
{ "codigo_dispositivo": "CHAL0001" }
```

**Respuesta 200:**
```json
{
  "ok": true,
  "datos": { "id_sesion": 123, "inicio": "2026-06-04T10:00:00" },
  "error": null
}
```

**Errores:**
| Código | Causa |
|---|---|
| `401` | Autenticación fallida |
| `422` | `codigo_dispositivo` ausente o dispositivo sin deportista asignado |

---

### POST `/api/v1/sesiones/{id_sesion}/lecturas`

Envía un lote de muestras (hasta 500 lecturas totales por petición).

**Body:**
```json
{
  "ecg": [
    { "t": "2026-06-04T10:00:01.020", "adc": 2480, "lo": false },
    { "t": "2026-06-04T10:00:01.030", "adc": 2510, "lo": false }
  ],
  "gps": [
    { "t": "2026-06-04T10:00:01.000", "lat": 4.1490, "lon": -74.8838, "vel": 7.8, "sat": 9 }
  ],
  "imu": [
    { "t": "2026-06-04T10:00:01.010", "ax": 120, "ay": -30, "az": 16380,
      "gx": 5, "gy": -2, "gz": 1, "inc": 11.3 }
  ]
}
```

Campos de cada tipo:

| Tipo | Campo | Tipo | Rango / formato |
|---|---|---|---|
| ECG | `t` | ISO-8601 | — |
| ECG | `adc` | int | 0–4095 |
| ECG | `lo` | bool | electrodo suelto |
| GPS | `t` | ISO-8601 | — |
| GPS | `lat` | float | −90…90 |
| GPS | `lon` | float | −180…180 |
| GPS | `vel` | float? | km/h |
| GPS | `sat` | int? | satélites |
| IMU | `t` | ISO-8601 | — |
| IMU | `ax/ay/az` | int | crudo int16 MPU-6050 |
| IMU | `gx/gy/gz` | int | crudo int16 MPU-6050 |
| IMU | `inc` | float? | grados de inclinación |

Lecturas que no pasen validación de rango se descartan silenciosamente.

**Respuesta 200:**
```json
{
  "ok": true,
  "datos": {
    "recibidas": { "ecg": 50, "gps": 1, "imu": 25 },
    "alertas": [
      { "tipo": "sobreesfuerzo_cardiaco", "severidad": "rojo",
        "mensaje": "Frecuencia cardíaca por encima del 90% de FCmáx: sobreesfuerzo" }
    ]
  },
  "error": null
}
```

**Errores:**
| Código | Causa |
|---|---|
| `401` | Autenticación fallida |
| `422` | Sesión no encontrada, no está en_curso, o lote > 500 lecturas |

---

### POST `/api/v1/sesiones/{id_sesion}/finalizar`

Marca la sesión como finalizada y calcula métricas (Haversine, FC media/máx/mín, etc.).

**Body:** vacío `{}`.

**Respuesta 200:**
```json
{
  "ok": true,
  "datos": {
    "id_sesion": 123,
    "metricas": {
      "fc_promedio": 142,
      "fc_maxima": 178,
      "fc_minima": 98,
      "distancia_total_m": 1820.5,
      "velocidad_max_kmh": 14.2,
      "velocidad_prom_kmh": 9.8,
      "duracion_seg": 900,
      "inclinacion_max": 18.4,
      "calorias_estimadas": null
    }
  },
  "error": null
}
```

---

### GET `/api/v1/sesiones/{id_sesion}/tiempo-real`

Endpoint para el **navegador** (requiere login de usuario — no de dispositivo).
Devuelve el último estado de la sesión para el holograma 3D y el dashboard.

**Respuesta 200:**
```json
{
  "ok": true,
  "datos": {
    "ultimo_bpm": 168,
    "inclinacion": 11.3,
    "recorrido": [[4.149, -74.883], [4.149106, -74.882971]],
    "alertas": [
      { "tipo": "electrodo_suelto", "severidad": "amarillo",
        "mensaje": "Electrodo suelto detectado." }
    ]
  },
  "error": null
}
```

**Errores:**
| Código | Causa |
|---|---|
| `401` | Usuario no autenticado |

---

## Rate limiting

Todos los endpoints de dispositivo: **120 requests/minuto** por IP.

---

## Variables de entorno del simulador

| Variable | Por defecto | Descripción |
|---|---|---|
| `SIMULATE_SERVER_URL` | `http://127.0.0.1:5000` | URL base de Flask |
| `SIMULATE_DEVICE_CODE` | `CHAL0001` | Código del dispositivo |
| `SIMULATE_DEVICE_KEY` | `clave-demo-insegura` | API key en claro |
