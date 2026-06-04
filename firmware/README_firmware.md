# Firmware PhysioScan — ESP32

Firmware del chaleco inteligente. Muestrea AD8232 (ECG), NEO-7M (GPS) y MPU-6050 (IMU)
y envía lotes JSON firmados con HMAC-SHA256 a la API Flask de PhysioScan.

## Hardware requerido

| Componente | Modelo | Bus | Pines ESP32 |
|---|---|---|---|
| Microcontrolador | ESP32-WROOM-32 | — | — |
| ECG | AD8232 | ADC | OUTPUT→GPIO34, LO+→GPIO35, LO−→GPIO32 |
| GPS | NEO-7M | UART2 | TX→GPIO16(RX2), RX→GPIO17(TX2) |
| IMU | MPU-6050 GY-521 | I2C | SDA→GPIO21, SCL→GPIO22 |
| Alimentación | — | — | 3.3 V **únicamente** para sensores. GND común. |

> **Advertencia:** No conectes los sensores a 5 V — se dañan.

## Instalación del entorno

### 1. Arduino IDE 2.x

Descarga desde `https://www.arduino.cc/en/software`

### 2. Soporte ESP32

1. **Archivo → Preferencias** → *URLs adicionales para gestor de tarjetas*:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
2. **Herramientas → Placa → Gestor de tarjetas** → busca `esp32` → instala
   **"esp32 by Espressif Systems"** (versión 2.x).
3. Selecciona placa: **ESP32 Dev Module**.

### 3. Librerías requeridas

Instala desde **Herramientas → Administrar bibliotecas**:

| Librería | Autor | Versión probada |
|---|---|---|
| `TinyGPSPlus` | Mikal Hart | >= 1.0.3 |
| `MPU6050` | Electronic Cats | >= 1.3.0 |

La librería `mbedtls` (para HMAC-SHA256) viene incluida en el SDK de ESP32.

### 4. Configurar credenciales

```bash
cp firmware/physioscan_chaleco/config.h.example firmware/physioscan_chaleco/config.h
```

Edita `config.h`:

| Variable | Cómo obtenerla |
|---|---|
| `WIFI_SSID` / `WIFI_PASS` | Datos de tu red Wi-Fi |
| `SERVER_URL` | IP LAN del PC (`ipconfig`/`ip addr`). **Nunca `127.0.0.1`** |
| `DEVICE_CODE` | Generado en Admin → Dispositivos → Crear (ej. `CHAL0001`) |
| `DEVICE_KEY` | API key mostrada en el panel al crear el dispositivo (una sola vez) |
| `EPOCH_OFFSET` | `python -c "import time; print(int(time.time()))"` |

### 5. Cargar el firmware

1. Conecta el ESP32 por USB.
2. **Herramientas → Puerto** → selecciona el puerto COM correcto.
3. Haz clic en **Subir** (→).
4. **Herramientas → Monitor Serie** a 115 200 baudios.
5. Verifica: `[WiFi] IP: 192.168.x.x` y `[Sesión] iniciada id=N`.

## Probar sin hardware (simulador)

```bash
python scripts/simular_chaleco.py
```

Verifica en MySQL:
```sql
SELECT COUNT(*) FROM lectura_ecg;
SELECT COUNT(*) FROM lectura_gps;
SELECT COUNT(*) FROM lectura_imu;
SELECT * FROM metrica_sesion;
```
