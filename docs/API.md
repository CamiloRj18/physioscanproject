# Contrato API de Ingesta — PhysioScan

## Autenticación de dispositivo

Cabeceras obligatorias en cada petición:

| Cabecera | Valor |
|---|---|
| `X-Device-Code` | Código del dispositivo, p.ej. `CHAL0001` |
| `X-Device-Key` | API key en claro (se compara con `dispositivo.api_key_hash`) |
| `X-Timestamp` | Epoch Unix en segundos; se rechaza si desfase > 60 s (anti-replay) |
| `X-Signature` | `HMAC_SHA256(secreto, codigo + timestamp + body)` |

## Endpoints

### POST /api/v1/sesiones/iniciar

```json
{ "codigo_dispositivo": "CHAL0001" }
```
Respuesta `200`:
```json
{ "id_sesion": 123, "inicio": "2026-06-04T10:00:00" }
```

### POST /api/v1/sesiones/{id_sesion}/lecturas

```json
{
  "ecg": [ { "t": "2026-06-04T10:00:01.020", "adc": 2480, "lo": false } ],
  "gps": [ { "t": "2026-06-04T10:00:01.000", "lat": 4.1490, "lon": -74.8838, "vel": 7.8, "sat": 9 } ],
  "imu": [ { "t": "2026-06-04T10:00:01.010", "ax": 120, "ay": -30, "az": 16380, "gx": 5, "gy": -2, "gz": 1, "inc": 11.3 } ]
}
```
Respuesta `200`:
```json
{ "recibidas": { "ecg": 1, "gps": 1, "imu": 1 }, "alertas": [] }
```

### POST /api/v1/sesiones/{id_sesion}/finalizar

Respuesta `200`:
```json
{ "id_sesion": 123, "metricas": { "fc_promedio": 142, "distancia_total_m": 1820 } }
```

### GET /api/v1/sesiones/{id_sesion}/tiempo-real

Requiere login de usuario (deportista / entrenador asignado).
```json
{ "ultimo_bpm": 168, "inclinacion": 11.3, "recorrido": [[4.149, -74.883]], "alertas": [] }
```
