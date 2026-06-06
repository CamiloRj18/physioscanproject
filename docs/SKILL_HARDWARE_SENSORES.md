# PHYSIOSCAN — Skill de Hardware y Sensores ESP32

## Pinout definitivo (100% validado)

```
MPU6050:  VCC→3V3  GND→GND  SDA→GPIO21  SCL→GPIO22
GPS:      VCC→3V3  GND→GND  TX→GPIO16   RX→GPIO17
AD8232:   3V3→3V3  GND→GND  OUTPUT→GPIO34  LO+→GPIO32  LO-→GPIO33
```

**Electrodos AD8232:**
- RA → clavícula derecha
- LA → clavícula izquierda
- RL → costado derecho (neutro)

## Librerías Arduino IDE instaladas

- ArduinoJson 6.x by Benoit Blanchon
- TinyGPSPlus by Mikal Hart
- MPU6050 by Electronic Cats
- ESP32 board package Espressif
  (URL: https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json)

## config.h del firmware

```cpp
#define WIFI_SSID    "nombre_red"
#define WIFI_PASS    "contraseña"
#define SERVER_URL   "http://192.168.X.X:5000"  // IP LAN del PC, NUNCA 127.0.0.1
#define DEVICE_CODE  "CHAL0001"
#define API_KEY      "api_key_del_dispositivo"
#define ID_SESION    1
```

## Formato JSON que envía el chaleco

```json
{
  "id_sesion": 1,
  "ecg": [{"adc": 2048, "bpm": 75, "lo": false, "t": "2026-06-05 10:00:00.000"}],
  "gps": [{"lat": 4.149, "lon": -74.884, "vel": 12.5, "sat": 8}],
  "imu": [{"ax": 0.1, "ay": 0.2, "az": 9.8,
           "gx": 0.01, "gy": 0.02, "gz": 0.03,
           "inc": 5.2, "t": "2026-06-05 10:00:00.000"}]
}
```

## Headers HMAC-SHA256

```
X-Device-Code: CHAL0001
X-Timestamp:   (unix timestamp como string)
X-Signature:   HMAC_SHA256(key=API_KEY, msg=codigo+timestamp+body_bytes)
```

Ventana anti-replay: ±60 segundos.

## Fases firmware pendientes

1. Integración simultánea 3 sensores (sin WiFi) — mostrar todo por Serial
2. WiFi.begin() + reconexión automática
3. Construcción JSON con ArduinoJson
4. HMAC-SHA256 con mbedTLS del ESP32
5. HTTP POST a /api/v1/ingesta → verificar HTTP 200
6. Firmware v1: ciclo 1s → leer sensores → JSON → HMAC → POST

## Sketch de integración simultánea (fase 1)

Para verificar que los 3 sensores funcionan al mismo tiempo:

```cpp
#include <Wire.h>
#include <MPU6050.h>
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>

MPU6050 mpu;
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);

#define ECG_PIN  34
#define LO_PLUS  32
#define LO_MINUS 33

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  mpu.initialize();
  gpsSerial.begin(9600, SERIAL_8N1, 16, 17);
  pinMode(LO_PLUS, INPUT);
  pinMode(LO_MINUS, INPUT);
  Serial.println("PhysioScan — Integración simultánea");
}

void loop() {
  // ECG
  bool lo = digitalRead(LO_PLUS) || digitalRead(LO_MINUS);
  int adc = analogRead(ECG_PIN);
  Serial.printf("ECG: %d | LO: %d\n", adc, lo);

  // GPS
  while (gpsSerial.available()) gps.encode(gpsSerial.read());
  if (gps.location.isValid()) {
    Serial.printf("GPS: lat=%.6f lon=%.6f sat=%d vel=%.2f\n",
      gps.location.lat(), gps.location.lng(),
      gps.satellites.value(), gps.speed.kmph());
  } else {
    Serial.println("GPS: buscando fix...");
  }

  // IMU
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  float inc = atan2((float)ay, (float)az) * 180.0 / PI;
  Serial.printf("IMU: AX=%d AY=%d AZ=%d GX=%d GY=%d GZ=%d INC=%.1f\n",
    ax, ay, az, gx, gy, gz, inc);

  delay(1000);
}
```

## Simulador sin hardware

```powershell
.\venv\Scripts\python.exe scripts\simular_chaleco.py
```

Requiere que el servidor Flask esté corriendo y que exista un dispositivo
registrado en la BD con su api_key.
