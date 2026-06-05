# PhysioScan

Servicio web de monitoreo deportivo con chaleco inteligente (ESP32 + sensores ECG/GPS/IMU).
Desarrollado por **Camilo Ramírez Jiménez** · UniEspinal · Metodología XP.

---

## Requisitos previos

| Herramienta | Versión mínima |
|---|---|
| Python | 3.9+ |
| XAMPP (MySQL) | 5.7 |
| pip | 26.1+ |

---

## Instalación

```bash
# 1. Clonar
git clone <repo-url>
cd physioscan

# 2. Entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 3. Dependencias
pip install -r requirements.txt
```

---

## Configuración de la base de datos

### Crear usuario y BD en phpMyAdmin o MySQL CLI

```sql
CREATE DATABASE physioscan CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'physio_app'@'localhost' IDENTIFIED BY 'tu_password_seguro';
GRANT SELECT, INSERT, UPDATE, DELETE ON physioscan.* TO 'physio_app'@'localhost';
```

### Ejecutar scripts DDL / seed

```bash
# Desde la raíz del proyecto (con MySQL activo en XAMPP)
venv\Scripts\python.exe scripts/crear_bd.py
```

Esto ejecuta en orden: `database/01_schema.sql`, `02_triggers.sql`, `03_seed.sql`.

> Si la BD ya existe con 3 roles, ejecutar manualmente en phpMyAdmin:
> `INSERT INTO rol (nombre, descripcion) VALUES ('usuario', 'Cuenta básica sin perfil deportivo');`

---

## Variables de entorno

Crea `.env` en la raíz del proyecto:

```ini
FLASK_ENV=desarrollo
SECRET_KEY=cambia_esto_por_una_clave_larga_y_aleatoria
FERNET_KEY=<generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

DB_HOST=localhost
DB_PORT=3306
DB_NAME=physioscan
DB_USER=physio_app
DB_PASSWORD=tu_password_seguro

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_app_password_gmail
MAIL_DEFAULT_SENDER=PhysioScan <tu_correo@gmail.com>
```

---

## Crear administrador inicial

```bash
venv\Scripts\python.exe -m flask --app app crear-admin
```

Solicita email y contraseña. Genera hash Argon2id, inserta en BD y genera el primer lote de 12 códigos de recuperación. **Guarda el archivo `.txt` que se muestra una sola vez.**

---

## Ejecutar en desarrollo

```bash
venv\Scripts\python.exe -m flask --app app run --debug
```

Accede a `http://127.0.0.1:5000`.

## Ejecutar en producción

```bash
# Con Waitress (Windows)
pip install waitress
waitress-serve --port=8000 "app:create_app('produccion')"

# Con Gunicorn (Linux)
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('produccion')"
```

Asegúrate de tener un proxy inverso (nginx) con certificado TLS delante.

---

## Firmware ESP32

### Configurar

```bash
cp firmware/config.h.example firmware/config.h
# Editar firmware/config.h:
#   SERVER_URL  → IP LAN del servidor (ej. http://192.168.1.20:5000)
#   DEVICE_CODE → código del dispositivo registrado en el panel admin
#   DEVICE_KEY  → API key mostrada al crear el dispositivo (texto plano, una sola vez)
```

### Compilar y flashear

Abrir `firmware/physioscan_chaleco.ino` en Arduino IDE con las librerías:
- `ArduinoJson`
- `TinyGPSPlus`
- `MPU6050` (Wire)
- `mbedtls` (incluida en ESP32 SDK)

### Simulador (sin hardware)

```bash
venv\Scripts\python.exe scripts/simular_chaleco.py \
    --url http://127.0.0.1:5000 \
    --codigo CHAL0001 \
    --key tu_api_key_en_claro
```

Inyecta lecturas ECG/GPS/IMU sintéticas firmadas con HMAC-SHA256 y valida que queden en BD.

---

## Tests

```bash
# Todos los tests (sin BD ni hardware)
venv\Scripts\python.exe -m pytest tests/ -v

# Con cobertura
venv\Scripts\python.exe -m pytest tests/ --cov=app/negocio --cov-report=term-missing
```

Los tests usan `unittest.mock` para aislar la capa de datos; no requieren MySQL activo.

### Archivos de tests

| Archivo | Qué cubre |
|---|---|
| `tests/test_auth.py` | Registro, login, bloqueo, anti-enumeración, verificación email |
| `tests/test_doble_factor.py` | TOTP válido/inválido, OTP email |
| `tests/test_recuperacion_archivo.py` | Generar lote, usar código, agotamiento, reemisión admin |
| `tests/test_ingesta.py` | HMAC, timestamp anti-replay, rangos de sensores, lote grande |
| `tests/test_heuristica.py` | Alertas por umbral, idempotencia de ventana 30 s |

---

## Documentación adicional

| Documento | Descripción |
|---|---|
| `docs/ARQUITECTURA.md` | Blueprint técnico completo (stack, BD, seguridad, sensores) |
| `docs/API.md` | Contrato de la API de ingesta (ESP32 → Flask) |
| `docs/INSTALL_DB.md` | Instrucciones detalladas de BD y permisos MySQL |
| `docs/REFACTOR.md` | Deuda técnica y plan de refactor por capas |
| `docs/SEGURIDAD_CHECKLIST.md` | Matriz OWASP/ISO 27001/Ley 1581 con estado de cada control |
| `docs/GUION_DEMO.md` | Guión paso a paso para la sustentación |

---

## Estructura del proyecto

```
physioscan/
├── app/
│   ├── presentacion/   # Controladores Flask (blueprints)
│   ├── negocio/        # Servicios de dominio (sin Flask, sin SQL)
│   ├── datos/          # Repositorios y pool MySQL
│   ├── comun/          # Utilidades transversales (crypto, validadores, decoradores)
│   ├── static/         # CSS, JS, modelos 3D
│   └── templates/      # Jinja2 (base.html + componentes)
├── database/           # DDL, triggers, seed
├── docs/               # Documentación técnica
├── firmware/           # Código Arduino (ESP32)
├── scripts/            # crear_bd.py, simular_chaleco.py
├── tests/              # pytest unit tests
├── .env                # Variables de entorno (NO commitear)
├── config.py           # Configuraciones desarrollo/produccion/pruebas
└── requirements.txt
```

---

## Licencia

Proyecto académico — UniEspinal 2026. Todos los derechos reservados.
