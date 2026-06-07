/*
 * PhysioScan — Firmware Chaleco Inteligente v1.1
 * Hardware: ESP32-WROOM-32
 * Sensores: MPU-6050 (IMU/I2C), NEO-7M (GPS/UART2), AD8232 (ECG/ADC)
 *
 * Pinout:
 *   MPU-6050 : SDA→GPIO21   SCL→GPIO22
 *   NEO-7M   : TX→GPIO16    RX→GPIO17
 *   AD8232   : OUTPUT→GPIO34  LO+→GPIO32  LO-→GPIO33
 *
 * Ciclo: setup→iniciarSesion() → 1 muestra/segundo → JSON → HMAC-SHA256
 *        → POST /api/v1/sesiones/{id}/lecturas
 */

#include <Wire.h>
#include <MPU6050.h>
#include <HardwareSerial.h>
#include <TinyGPSPlus.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>
#include <time.h>
#include "config.h"

// ── Pines AD8232 ──────────────────────────────────────────────────────────────
#define ECG_OUTPUT 34
#define LO_PLUS    32
#define LO_MINUS   33

// ── Objetos globales ──────────────────────────────────────────────────────────
MPU6050        mpu;
TinyGPSPlus    gps;
HardwareSerial gpsSerial(2);  // UART2: RX=GPIO16, TX=GPIO17

unsigned long ultimoCiclo   = 0;
const unsigned long INTERVALO_MS = 1000;
int idSesionActual = 0;  // se asigna en iniciarSesion()

// ─────────────────────────────────────────────────────────────────────────────
// Genera un timestamp ISO-8601 usando hora NTP real.
// Fallback a millis() si NTP no está disponible.
// ─────────────────────────────────────────────────────────────────────────────
String timestampActual() {
  struct tm timeinfo;
  if (getLocalTime(&timeinfo)) {
    char buf[28];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S.000", &timeinfo);
    return String(buf);
  }
  // fallback si NTP falla
  unsigned long ms  = millis();
  unsigned long seg = ms / 1000;
  char buf[28];
  snprintf(buf, sizeof(buf), "2026-06-07T%02lu:%02lu:%02lu.000",
           (seg / 3600) % 24, (seg / 60) % 60, seg % 60);
  return String(buf);
}

// ─────────────────────────────────────────────────────────────────────────────
// Reconecta WiFi si se perdió la conexión. Se llama antes de cada POST.
// ─────────────────────────────────────────────────────────────────────────────
void reconectarWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("[WiFi] Reconectando");
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 10000) {
    delay(400);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" OK — IP: " + WiFi.localIP().toString());
  } else {
    Serial.println(" FALLO");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Calcula HMAC-SHA256(key=API_KEY, msg=DEVICE_CODE+timestamp+body)
// Devuelve 64 caracteres hex
// ─────────────────────────────────────────────────────────────────────────────
String calcularHMAC(const String& xTimestamp, const String& body) {
  String msg = String(DEVICE_CODE) + xTimestamp + body;

  unsigned char hmacRaw[32];
  mbedtls_md_context_t ctx;
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);

  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, info, 1);
  mbedtls_md_hmac_starts(&ctx,
    (const unsigned char*)API_KEY, strlen(API_KEY));
  mbedtls_md_hmac_update(&ctx,
    (const unsigned char*)msg.c_str(), msg.length());
  mbedtls_md_hmac_finish(&ctx, hmacRaw);
  mbedtls_md_free(&ctx);

  char hexBuf[65];
  for (int i = 0; i < 32; i++) {
    snprintf(hexBuf + i * 2, 3, "%02x", hmacRaw[i]);
  }
  return String(hexBuf);
}

// ─────────────────────────────────────────────────────────────────────────────
// Llama a POST /api/v1/sesiones/iniciar y guarda el id_sesion en idSesionActual
// ─────────────────────────────────────────────────────────────────────────────
void iniciarSesion() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[SESION] Sin WiFi — sesión no iniciada");
    return;
  }

  String body       = "{\"codigo_dispositivo\":\"" + String(DEVICE_CODE) + "\"}";
  String xTimestamp = String((unsigned long)time(nullptr));
  String firma      = calcularHMAC(xTimestamp, body);

  HTTPClient http;
  http.setTimeout(20000);
  http.begin(String(SERVER_URL) + "/api/v1/sesiones/iniciar");
  http.addHeader("Content-Type",  "application/json");
  http.addHeader("X-Device-Code", DEVICE_CODE);
  http.addHeader("X-Device-Key",  API_KEY);
  http.addHeader("X-Timestamp",   xTimestamp);
  http.addHeader("X-Signature",   firma);

  int httpCode = http.POST(body);
  Serial.printf("[SESION] POST iniciar → HTTP %d\n", httpCode);

  if (httpCode == 200) {
    String respuesta = http.getString();
    StaticJsonDocument<256> resp;
    DeserializationError err = deserializeJson(resp, respuesta);
    if (!err) {
      idSesionActual = resp["datos"]["id_sesion"] | 0;
      Serial.println("[SESION] id_sesion=" + String(idSesionActual));
    } else {
      Serial.println("[SESION] Error JSON: " + String(err.c_str()));
    }
  } else {
    Serial.println("[SESION] Fallo — lecturas desactivadas");
  }

  http.end();
}

// ─────────────────────────────────────────────────────────────────────────────
// setup()
// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n[PhysioScan] Iniciando chaleco...");

  // I2C → MPU-6050
  Wire.begin(21, 22);
  mpu.initialize();
  Serial.println("[IMU] MPU-6050 " + String(mpu.testConnection() ? "OK" : "ERROR"));

  // UART2 → GPS NEO-7M
  gpsSerial.begin(9600, SERIAL_8N1, 16, 17);
  Serial.println("[GPS] Serial UART2 iniciado (9600 bps)");

  // Pines detección electrodo AD8232
  pinMode(LO_PLUS,  INPUT);
  pinMode(LO_MINUS, INPUT);
  Serial.println("[ECG] AD8232 configurado (OUTPUT=34, LO+=32, LO-=33)");

  // WiFi — conexión directa con credenciales de config.h
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("[WiFi] Conectando a " + String(WIFI_SSID));
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 30000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(" FALLO — reiniciando en 5 s");
    delay(5000);
    ESP.restart();
  }
  Serial.println(" OK — IP: " + WiFi.localIP().toString());

  // Sincronizar hora via NTP (UTC)
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("[NTP] Sincronizando hora");
  struct tm timeinfo;
  int intentos = 0;
  while (!getLocalTime(&timeinfo) && intentos < 20) {
    delay(500);
    Serial.print(".");
    intentos++;
  }
  if (getLocalTime(&timeinfo)) {
    Serial.println(" OK");
  } else {
    Serial.println(" FALLO (usando millis)");
  }

  iniciarSesion();

  Serial.println("[PhysioScan] Setup completo\n");
}

// ─────────────────────────────────────────────────────────────────────────────
// loop()
// ─────────────────────────────────────────────────────────────────────────────
void loop() {
  // Alimentar el parser GPS de forma no bloqueante en cada iteración
  while (gpsSerial.available()) {
    gps.encode(gpsSerial.read());
  }

  // Ejecutar ciclo completo cada INTERVALO_MS (1 segundo)
  if (millis() - ultimoCiclo < INTERVALO_MS) return;
  ultimoCiclo = millis();

  // ── 1. Lectura ECG ──────────────────────────────────────────────────────────
  int  adc = analogRead(ECG_OUTPUT);
  bool lo  = digitalRead(LO_PLUS) || digitalRead(LO_MINUS);
  Serial.printf("[ECG] adc=%d lo=%d\n", adc, (int)lo);

  // ── 2. Lectura IMU ──────────────────────────────────────────────────────────
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  float inc = atan2((float)ay, (float)az) * 180.0 / PI;
  Serial.printf("[IMU] ax=%d ay=%d az=%d inc=%.1f\n", ax, ay, az, inc);

  // ── 3. Log GPS ─────────────────────────────────────────────────────────────
  if (gps.location.isValid()) {
    Serial.printf("[GPS] lat=%.6f lon=%.6f sat=%u\n",
      gps.location.lat(), gps.location.lng(),
      (unsigned)gps.satellites.value());
  } else {
    Serial.println("[GPS] sin fix");
  }

  // Sin sesión activa no hay nada que enviar
  if (idSesionActual <= 0) return;

  // ── 4. Construir JSON ───────────────────────────────────────────────────────
  String ts = timestampActual();
  StaticJsonDocument<1024> doc;

  // Muestra ECG — t primero según contrato API
  JsonArray ecgArr      = doc.createNestedArray("ecg");
  JsonObject ecgMuestra = ecgArr.createNestedObject();
  ecgMuestra["t"]   = ts;
  ecgMuestra["adc"] = adc;
  ecgMuestra["lo"]  = lo;

  // Muestra IMU — t primero
  JsonArray imuArr      = doc.createNestedArray("imu");
  JsonObject imuMuestra = imuArr.createNestedObject();
  imuMuestra["t"]   = ts;
  imuMuestra["ax"]  = ax;
  imuMuestra["ay"]  = ay;
  imuMuestra["az"]  = az;
  imuMuestra["gx"]  = gx;
  imuMuestra["gy"]  = gy;
  imuMuestra["gz"]  = gz;
  imuMuestra["inc"] = inc;

  // Muestra GPS — solo si hay fix válido
  if (gps.location.isValid()) {
    JsonArray gpsArr      = doc.createNestedArray("gps");
    JsonObject gpsMuestra = gpsArr.createNestedObject();
    gpsMuestra["t"]   = ts;
    gpsMuestra["lat"] = gps.location.lat();
    gpsMuestra["lon"] = gps.location.lng();
    gpsMuestra["vel"] = gps.speed.kmph();
    gpsMuestra["sat"] = (int)gps.satellites.value();
  }

  String body;
  body.reserve(512);
  serializeJson(doc, body);

  // ── 5. HMAC-SHA256 ──────────────────────────────────────────────────────────
  String xTimestamp = String((unsigned long)time(nullptr));
  String firma      = calcularHMAC(xTimestamp, body);

  // ── 6. HTTP POST ────────────────────────────────────────────────────────────
  reconectarWiFi();

  if (WiFi.status() == WL_CONNECTED) {
    String url = String(SERVER_URL) + "/api/v1/sesiones/"
                 + String(idSesionActual) + "/lecturas";
    HTTPClient http;
    http.setTimeout(20000);
    http.begin(url);
    http.addHeader("Content-Type",  "application/json");
    http.addHeader("X-Device-Code", DEVICE_CODE);
    http.addHeader("X-Device-Key",  API_KEY);
    http.addHeader("X-Timestamp",   xTimestamp);
    http.addHeader("X-Signature",   firma);

    int httpCode = http.POST(body);
    http.end();

    if (httpCode > 0) {
      Serial.printf("[POST] HTTP %d\n", httpCode);
    } else {
      Serial.printf("[POST] Error: %d\n", httpCode);
    }
  } else {
    Serial.println("[POST] Error: sin WiFi");
  }
}
