/*
 * physioscan_chaleco.ino — Firmware ESP32-WROOM-32
 * Sensores: AD8232 (ECG/ADC·GPIO34), NEO-7M (GPS/UART2·GPIO16/17), MPU-6050 (IMU/I2C·GPIO21/22)
 * Envío: JSON por lotes cada 1 s vía HTTP POST con cabeceras HMAC-SHA256.
 * Instrucciones: copiar config.h.example → config.h, completar y cargar.
 */

#include <WiFi.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <MPU6050.h>
#include <HardwareSerial.h>
#include <TinyGPSPlus.h>
#include <mbedtls/md.h>
#include "config.h"

// ─── Pines ────────────────────────────────────────────────────────────────────
#define ECG_OUTPUT 34
#define LO_PLUS    35
#define LO_MINUS   32
#define GPS_RX2    16
#define GPS_TX2    17
#define IMU_SDA    21
#define IMU_SCL    22

// ─── Objetos de sensor ────────────────────────────────────────────────────────
MPU6050          mpu;
TinyGPSPlus      gps;
HardwareSerial   gpsSerial(2);

// ─── Estado global ────────────────────────────────────────────────────────────
long             idSesion    = -1;
unsigned long    ultimoEnvio = 0;
const unsigned long INTERVALO_MS = 1000;

// ─── Buffers de lote ─────────────────────────────────────────────────────────
String bufEcg = "";
String bufGps = "";
String bufImu = "";
int    cntEcg = 0, cntGps = 0, cntImu = 0;

// ─── HMAC-SHA256 ─────────────────────────────────────────────────────────────
String hmacSha256(const String& key, const String& msg) {
  byte result[32];
  const byte* k = (const byte*)key.c_str();
  const byte* m = (const byte*)msg.c_str();
  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
  mbedtls_md_hmac_starts(&ctx, k, key.length());
  mbedtls_md_hmac_update(&ctx, m, msg.length());
  mbedtls_md_hmac_finish(&ctx, result);
  mbedtls_md_free(&ctx);
  String hex = "";
  for (int i = 0; i < 32; i++) {
    char buf[3];
    sprintf(buf, "%02x", result[i]);
    hex += buf;
  }
  return hex;
}

// ─── Cabeceras de autenticación ───────────────────────────────────────────────
void agregarCabeceras(HTTPClient& http, const String& body) {
  String ts = String(millis() / 1000 + EPOCH_OFFSET);
  String firma = hmacSha256(String(API_KEY),
                             String(DEVICE_CODE) + ts + body);
  http.addHeader("Content-Type",  "application/json");
  http.addHeader("X-Device-Code", DEVICE_CODE);
  http.addHeader("X-Device-Key",  API_KEY);
  http.addHeader("X-Timestamp",   ts);
  http.addHeader("X-Signature",   firma);
}

// ─── POST genérico ────────────────────────────────────────────────────────────
int httpPost(const String& url, const String& body) {
  HTTPClient http;
  http.begin(url);
  agregarCabeceras(http, body);
  int code = http.POST(body);
  if (code > 0) Serial.printf("[HTTP] POST %s → %d\n", url.c_str(), code);
  else           Serial.printf("[HTTP] Error: %s\n", http.errorToString(code).c_str());
  http.end();
  return code;
}

// ─── Iniciar sesión ───────────────────────────────────────────────────────────
long iniciarSesion() {
  String body = "{\"codigo_dispositivo\":\"" + String(DEVICE_CODE) + "\"}";
  String url  = String(SERVER_URL) + "/api/v1/sesiones/iniciar";
  HTTPClient http;
  http.begin(url);
  agregarCabeceras(http, body);
  int code = http.POST(body);
  long id  = -1;
  if (code == 200) {
    String resp = http.getString();
    // Parseo mínimo: buscar "id_sesion":NNN
    int idx = resp.indexOf("\"id_sesion\":");
    if (idx >= 0) {
      id = resp.substring(idx + 12).toInt();
      Serial.printf("[Sesión] iniciada id=%ld\n", id);
    }
  } else {
    Serial.printf("[Sesión] error HTTP %d\n", code);
  }
  http.end();
  return id;
}

// ─── Timestamp ISO-8601 ───────────────────────────────────────────────────────
String isoNow() {
  unsigned long ms = millis();
  // Usa EPOCH_OFFSET (segundos desde 1970-01-01 al arrancar) + ms transcurridos
  unsigned long epoch = EPOCH_OFFSET + ms / 1000;
  unsigned long msFrac = ms % 1000;
  // Descomposición simplificada (sin DST)
  unsigned long s = epoch % 60; epoch /= 60;
  unsigned long m = epoch % 60; epoch /= 60;
  unsigned long h = epoch % 24; epoch /= 24;
  // Fecha aproximada (suficiente para la BD, no corrige años bisiestos)
  unsigned long y = 1970; unsigned long dias = epoch;
  while (true) {
    unsigned long yd = (y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)) ? 366 : 365;
    if (dias < yd) break; dias -= yd; y++;
  }
  char buf[32];
  snprintf(buf, sizeof(buf), "%04lu-%02lu-%02luT%02lu:%02lu:%02lu.%03lu",
           y, (unsigned long)1, dias + 1, h, m, s, msFrac);
  return String(buf);
}

// ─── Muestreo ECG ────────────────────────────────────────────────────────────
void muestrarEcg() {
  bool lo = digitalRead(LO_PLUS) || digitalRead(LO_MINUS);
  int  adc = lo ? 0 : analogRead(ECG_OUTPUT);
  if (cntEcg > 0) bufEcg += ",";
  bufEcg += "{\"t\":\"" + isoNow() + "\",\"adc\":" + String(adc)
           + ",\"lo\":" + (lo ? "true" : "false") + "}";
  cntEcg++;
}

// ─── Muestreo IMU ─────────────────────────────────────────────────────────────
void muestrarImu() {
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  float inc = atan2((float)ay, (float)az) * 180.0 / PI;
  if (cntImu > 0) bufImu += ",";
  bufImu += "{\"t\":\"" + isoNow() + "\","
           "\"ax\":" + String(ax) + ",\"ay\":" + String(ay) + ",\"az\":" + String(az) + ","
           "\"gx\":" + String(gx) + ",\"gy\":" + String(gy) + ",\"gz\":" + String(gz) + ","
           "\"inc\":" + String(inc, 2) + "}";
  cntImu++;
}

// ─── Muestreo GPS (no bloqueante) ────────────────────────────────────────────
void actualizarGps() {
  while (gpsSerial.available()) gps.encode(gpsSerial.read());
  if (gps.location.isValid() && gps.location.isUpdated()) {
    if (cntGps > 0) bufGps += ",";
    bufGps += "{\"t\":\"" + isoNow() + "\","
             "\"lat\":" + String(gps.location.lat(), 6) + ","
             "\"lon\":" + String(gps.location.lng(), 6) + ","
             "\"vel\":" + String(gps.speed.kmph(), 2) + ","
             "\"sat\":" + String(gps.satellites.value()) + "}";
    cntGps++;
  }
}

// ─── Enviar lote ─────────────────────────────────────────────────────────────
void enviarLote() {
  if (idSesion < 0) return;
  String body = "{\"ecg\":[" + bufEcg + "],\"gps\":[" + bufGps + "],\"imu\":[" + bufImu + "]}";
  String url  = String(SERVER_URL) + "/api/v1/sesiones/" + String(idSesion) + "/lecturas";
  httpPost(url, body);
  bufEcg = ""; bufGps = ""; bufImu = "";
  cntEcg = 0;  cntGps = 0;  cntImu = 0;
}

// ─── Setup ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  // ECG
  pinMode(LO_PLUS,  INPUT);
  pinMode(LO_MINUS, INPUT);

  // IMU I2C
  Wire.begin(IMU_SDA, IMU_SCL);
  mpu.initialize();
  if (!mpu.testConnection()) Serial.println("[IMU] MPU-6050 no responde");
  else                        Serial.println("[IMU] MPU-6050 OK");

  // GPS UART2
  gpsSerial.begin(9600, SERIAL_8N1, GPS_RX2, GPS_TX2);
  Serial.println("[GPS] NEO-7M en UART2");

  // WiFi — reset por GPIO0 (BOOT): mantener presionado 3 s al arrancar borra credenciales
  WiFiManager wifiManager;
  pinMode(0, INPUT_PULLUP);
  delay(100);
  if (digitalRead(0) == LOW) {
    Serial.println("[WiFi] Reset de credenciales WiFi...");
    wifiManager.resetSettings();
    ESP.restart();
  }

  wifiManager.setConfigPortalTimeout(180);
  wifiManager.setAPCallback([](WiFiManager* wm) {
    Serial.println("[WiFi] Sin credenciales guardadas.");
    Serial.println("[WiFi] Conéctate a 'PhysioScan-Setup' (pass: physioscan123)");
    Serial.println("[WiFi] Luego abre 192.168.4.1 en tu navegador");
  });
  if (!wifiManager.autoConnect("PhysioScan-Setup", "physioscan123")) {
    Serial.println("[WiFi] Timeout — reiniciando...");
    ESP.restart();
  }
  Serial.println("[WiFi] Conectado! IP: " + WiFi.localIP().toString());

  // Iniciar sesión en el servidor
  idSesion = iniciarSesion();
}

// ─── Loop ─────────────────────────────────────────────────────────────────────
void loop() {
  muestrarEcg();
  muestrarImu();
  actualizarGps();

  if (millis() - ultimoEnvio >= INTERVALO_MS) {
    ultimoEnvio = millis();
    enviarLote();
  }

  delay(10);  // ~100 Hz ECG e IMU
}
