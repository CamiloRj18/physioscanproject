# PHYSIOSCAN — Skill Completa de Continuación
> Autor: Camilo Ramírez Jiménez · UniEspinal · Espinal, Tolima
> Docente: Juan David Díaz Valencia
> Repo: https://github.com/CamiloRj18/physioscanproject

---

## 1. Qué es PhysioScan

Servicio web Flask de monitoreo deportivo biométrico con chaleco inteligente ESP32.
Captura ECG (AD8232), GPS (NEO-7M) e inclinación corporal (MPU-6050) en tiempo real.
Los datos se envían desde el chaleco al servidor vía HTTPS/HMAC y se visualizan
en dashboards por rol. Proyecto académico, deadline domingo 8 de junio de 2026.

---

## 2. Stack

| Capa | Tecnología |
|---|---|
| Frontend | HTML5 · CSS3 · JS vanilla · Three.js r128 autohospedado |
| Backend | Python 3.14 · Flask 3.1.x |
| Base de datos | MySQL 5.7 (XAMPP) · mysql-connector-python |
| Seguridad | Argon2id · Fernet · HMAC-SHA256 · TOTP pyotp · Flask-Talisman · Flask-WTF |
| PDF | reportlab |
| Correo | Flask-Mail |
| Hardware | ESP32 · AD8232 · NEO-7M · MPU-6050 |

---

## 3. Estructura del proyecto

```
C:\physioscan\
├── app/
│   ├── presentacion/    # Blueprints Flask
│   │   ├── auth_controlador.py
│   │   ├── admin_controlador.py
│   │   ├── deportista_controlador.py
│   │   ├── entrenador_controlador.py
│   │   ├── usuario_controlador.py
│   │   ├── recuperacion_controlador.py
│   │   ├── publico_controlador.py
│   │   ├── api_ingesta_controlador.py
│   │   └── sesion_controlador.py
│   ├── negocio/         # Servicios puros sin SQL ni HTTP
│   │   ├── auth_servicio.py
│   │   ├── metricas_servicio.py
│   │   ├── heuristica_servicio.py
│   │   ├── ingesta_servicio.py
│   │   └── seguridad/
│   │       ├── doble_factor_servicio.py
│   │       └── recuperacion_archivo_servicio.py  ← genera PDF + envía correo
│   ├── datos/           # Repositorios SQL parametrizados
│   ├── modelos/         # Dataclasses
│   ├── comun/           # Decoradores, errores, extensiones
│   ├── static/
│   │   ├── css/         # tokens.css, base.css, animations.css, componentes.css,
│   │   │                # app.css, loader.css, page-*.css
│   │   ├── js/          # theme.js, ui.js, nav.js, login.js, loader.js,
│   │   │                # holograma3d.js, dashboard.js, tiempo_real.js
│   │   │   └── vendor/  # three.min.js r128, GLTFLoader.js r128
│   │   ├── models/      # cuerpo.glb (holograma constelación)
│   │   └── img/stack/   # SVG Devicon: html5, css3, javascript, mysql, flask, python
│   └── templates/
│       ├── base.html
│       ├── componentes/ # navbar.html, footer.html, _sprite.svg.html
│       ├── publico/     # home.html
│       ├── auth/        # login.html, registro.html, verificar_2fa.html
│       ├── admin/       # panel.html, usuarios.html, dispositivos.html, auditoria.html
│       ├── deportista/  # sesiones.html, sesion_detalle.html, en_vivo.html
│       ├── entrenador/  # deportistas.html, deportista_detalle.html
│       ├── usuario/     # perfil.html
│       └── recuperacion/
├── database/            # 01_schema.sql 02_triggers.sql 03_seed.sql 04_vistas.sql
├── firmware/            # physioscan_chaleco.ino, config.h.example
├── scripts/             # crear_bd.py, simular_chaleco.py
├── tests/               # 48 pruebas pytest en verde sin BD
├── design_handoff_physioscan/
│   └── frontend/        # CSS/JS/HTML del handoff de Claude Design
│       ├── css/         # tokens.css, base.css, animations.css, app.css, components.css
│       ├── js/          # theme.js, ui.js, nav.js, login.js
│       └── icons.svg    # 43 íconos SVG
├── devicon-master/      # Logos SVG de tecnologías (Devicon)
├── docs/                # ARQUITECTURA.md, GUION_DEMO.md, SEGURIDAD_CHECKLIST.md
├── .env
├── requirements.txt
├── run.py
└── PHYSIOSCAN_SKILL.md  # este archivo
```

---

## 4. Base de datos — decisiones clave

**Normalización:** 3FN/BCNF, 20+ tablas.
**Cotejamiento:** utf8mb4_general_ci (MySQL 5.7, NO usar utf8mb4_0900_ai_ci).

**IDs:**
- Todas las tablas: PK INT AUTO_INCREMENT
- Tabla usuario: además tiene codigo_usuario CHAR(7) generado por trigger BEFORE INSERT
  - Formato: LPAD(seq,5,'0') + inicial_primer_nombre + inicial_primer_apellido
  - Ejemplo: 10001CR (Camilo Ramírez)

**Roles (tabla rol, 4 registros en BD):**

| id_rol | nombre | Cómo se asigna |
|---|---|---|
| 1 | administrador | CLI flask crear-admin |
| 2 | entrenador | Admin desde panel |
| 3 | deportista | Usuario completa perfil deportivo |
| 4 | usuario | Por defecto al registrarse |

**IMPORTANTE:** El rol 4 'usuario' DEBE existir en la BD.
Si no existe: INSERT IGNORE INTO rol (id_rol, nombre, descripcion) VALUES (4, 'usuario', 'Cuenta básica');

---

## 5. Configuración .env

```env
SECRET_KEY=235a8b691435d08be0ea79f241cee06767fb963a9585704fdf1695ff302b4406
FERNET_KEY=rHckecWB3i-UUknX5EYPlhKQJOx5fTvGXtCNT3iReFg=
MAIL_USERNAME=physioscan.uniespinal@gmail.com
MAIL_PASSWORD=vgko alsz avge nhgq
DB_PASSWORD=PhysioScan2024#
DB_ROOT_PASSWORD=
```

**Arrancar:**
```powershell
.\venv\Scripts\activate
python run.py
```

**Crear admin:**
```powershell
flask --app app crear-admin
```

**Pruebas:**
```powershell
.\venv\Scripts\python.exe -m pytest tests/ -v
```

---

## 6. Seguridad

- Contraseñas: Argon2id
- Secreto TOTP: Fernet cifrado en BD
- 2FA: TOTP + OTP por correo
- Archivo recuperación: 12 códigos Argon2id, enviados por correo en PDF al usuario
- API chaleco: HMAC-SHA256 + timestamp anti-replay 60s
- CSRF: Flask-WTF en todos los formularios (usar csrf_token() en templates, NO form.hidden_tag())
- CSP: style-src 'self' 'unsafe-hashes' · script-src 'self'
- El proyecto NO usa WTForms — usa request.form directamente
- Los templates usan dict['campo'] no objeto.campo para datos de MySQL

---

## 7. Bugs conocidos y fixes aplicados

| Bug | Fix |
|---|---|
| from flask import BuildError | → from werkzeug.routing.exceptions import BuildError |
| utf8mb4_0900_ai_ci no existe | → utf8mb4_general_ci |
| form.hidden_tag() en templates | → input csrf_token() directo |
| 'dict object' has no attribute X | → usar dict['campo'] en templates |
| Login redirige mal | → _destino_post_login() con try/except BuildError |
| Rol 'usuario' no configurado | → INSERT rol id=4 en BD |
| Three.js CSP inline styles | → style-src 'unsafe-hashes' |
| PowerShell && no funciona | → comandos separados con ; |

---

## 8. Sistema de diseño

**Tema:** dark por defecto (data-theme="dark" en html), light también funcional.
**Toggle:** botón #theme-toggle en navbar, guarda en localStorage.
**Anti-flash:** theme.js en head SIN defer.

**Tokens dark:**
```css
--bg-base: #020813  --accent: #79DBFF  --text-primary: #ECFBFF
--bg-raised: #041425  --accent-strong: #B4F8FF  --text-secondary: #9784C8
```

**Tokens light:**
```css
--bg-base: #F0F7FF  --accent: #0077B6  --text-primary: #041425
```

**Íconos:** Sprite SVG en templates/componentes/_sprite.svg.html
Uso: `<svg class="icon"><use href="#ic-heart"></use></svg>`
REGLA: Cero emojis en todo el proyecto.

**Holograma 3D:**
- Three.js r128 autohospedado en static/js/vendor/
- Modelo: static/models/cuerpo.glb (constelación 301 nodos, 774 links)
- NUNCA usar CapsuleGeometry (es r142+, no existe en r128)
- Fallback: CylinderGeometry + SphereGeometry

---

## 9. API del chaleco ESP32

**Endpoint:** POST /api/v1/ingesta

**Headers HMAC:**
```
X-Device-Code: CHAL0001
X-Timestamp: (unix timestamp string)
X-Signature: HMAC_SHA256(key=api_key, msg=codigo+timestamp+body)
```

**JSON:**
```json
{
  "id_sesion": 1,
  "ecg": [{"adc": 2048, "bpm": 75, "lo": false, "t": "2026-06-05 10:00:00.000"}],
  "gps": [{"lat": 4.149, "lon": -74.884, "vel": 12.5, "sat": 8}],
  "imu": [{"ax": 0.1, "ay": 0.2, "az": 9.8, "gx": 0.01, "gy": 0.02, "gz": 0.03,
           "inc": 5.2, "t": "2026-06-05 10:00:00.000"}]
}
```

**SERVER_URL en config.h:** IP LAN del PC (ej: 192.168.1.100:5000), NUNCA 127.0.0.1

---

## 10. Pinout definitivo del chaleco (validado)

```
MPU6050:  VCC→3V3, GND→GND, SDA→GPIO21, SCL→GPIO22
GPS:      VCC→3V3, GND→GND, TX→GPIO16,  RX→GPIO17
AD8232:   3V3→3V3, GND→GND, OUTPUT→GPIO34, LO+→GPIO32, LO-→GPIO33
```

**Electrodos AD8232:** RA→clavícula derecha, LA→clavícula izquierda, RL→costado derecho

**Librerías Arduino IDE instaladas:**
- ArduinoJson 6.x by Benoit Blanchon
- TinyGPSPlus by Mikal Hart
- MPU6050 by Electronic Cats
- ESP32 board package Espressif

**Fases del firmware pendientes:**
1. Integración simultánea de 3 sensores (sin WiFi)
2. WiFi.begin() + reconexión automática
3. Construcción JSON con ArduinoJson
4. HMAC-SHA256 con mbedTLS del ESP32
5. HTTP POST a Flask
6. Firmware v1 producción: ciclo 1s → leer → JSON → HMAC → POST

---

## 11. Flujo de códigos de recuperación (CORRECTO)

1. Usuario se registra → se genera lote de 12 códigos Argon2id
2. Se genera PDF tema CLARO (fondo blanco, para imprimir) con reportlab
3. El PDF se envía por correo al email del usuario
4. El admin NO ve los códigos nunca
5. Al agotar los 12 → admin reemite desde /admin/usuarios/<id> → PDF va por correo al usuario
6. Esto aplica tanto para registro propio como para creación por admin

---

## 12. Sesiones de Claude Code completadas

| Sesión | Contenido |
|---|---|
| S1 | BD completa, triggers, seed, pool MySQL |
| S2 | App factory, config, seguridad, extensiones |
| S3 | Auth + 2FA TOTP + OTP email + bloqueo |
| S4 | Recuperación + Admin CRUD + RBAC + auditoría |
| S5 | API ingesta HMAC + firmware ESP32 + simulador |
| S6 | Métricas Keytel + heurística + dashboards tiempo real |
| S7 | Home + holograma Three.js r128 |
| S-Roles | Rol usuario (id=4), perfil editable, cambio rol admin |
| S-Visual | Holograma constelación GLB, loader ECG, dark/light |
| S8 | 48 pruebas pytest, pip-audit, README, GUION_DEMO |
| S-Design | Integración handoff Claude Design + Devicon |
| S-Fixes | dict attrs templates, rutas post-login, CSS footer/dropdowns |
| S-PDF | PDF códigos recuperación tema claro, envío por correo (PENDIENTE COMMIT) |

**Último commit conocido:** fix(css): toggle icon, holograma light, footer, dropdowns, swatch hover

---

## 13. Pendientes para la demo

1. Verificar que el prompt de PDF/correo terminó correctamente en Claude Code
2. Conectar chaleco: soldar sensores a protoboard con ESP32 centrado
3. Configurar IP LAN en firmware/config.h
4. Crear sesión de entrenamiento desde admin → asignar al deportista
5. Correr python scripts/simular_chaleco.py para probar sin hardware
6. Seguir docs/GUION_DEMO.md (10 pasos, ~25 minutos)

---

## 14. Rutas del sistema

| Ruta | Quién accede |
|---|---|
| / | Todos |
| /auth/login | Anónimo |
| /auth/registro | Anónimo |
| /usuario/perfil | Todos logueados |
| /deportista/sesiones | rol deportista |
| /entrenador/deportistas | rol entrenador |
| /admin/ | rol administrador |
| /admin/usuarios | rol administrador |
| /admin/dispositivos | rol administrador |
| /recuperacion/solicitar | Anónimo |
| /recuperacion/archivo | Anónimo |
| /api/v1/ingesta | Dispositivo ESP32 (HMAC) |
| /api/v1/sesiones/<id>/tiempo-real | Usuario logueado |

---

## 15. Cómo continuar en otra cuenta de Claude

Al empezar una nueva conversación pega esto:

"Soy Camilo Ramírez Jiménez, estudiante de UniEspinal.
Tengo un proyecto Flask llamado PhysioScan en C:\physioscan.
Lee el archivo PHYSIOSCAN_SKILL.md en la raíz del proyecto
para entender el contexto completo antes de ayudarme."

Si Claude Code no encuentra el skill en la raíz, está también en:
C:\Users\CAMI\Downloads\PHYSIOSCAN_SKILL_COMPLETA.md

---

*Generado el 5 de junio de 2026 — PhysioScan v1.0*
*"Del hardware al software, del sensor al dashboard." — Camilo R.*
