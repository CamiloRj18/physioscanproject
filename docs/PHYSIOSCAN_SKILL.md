# PHYSIOSCAN — Skill de Proyecto Completo

> **Uso:** Pega este archivo en la raíz del repo como `PHYSIOSCAN_SKILL.md` o en `.claude/skills/`.  
> Claude Code lo leerá para tener contexto completo del proyecto sin necesidad de reexplicar nada.

---

## 1. Identidad del proyecto

| Campo | Valor |
|---|---|
| Nombre | PhysioScan |
| Autor | Camilo Ramírez Jiménez |
| Institución | Institución Universitaria de El Espinal — UniEspinal |
| Docente | Juan David Díaz Valencia |
| Metodología | XP (Extreme Programming) |
| Deadline original | Sábado 6 de junio de 2026 |
| Repo | https://github.com/CamiloRj18/physioscanproject |

**Descripción:** Servicio web de monitoreo deportivo biométrico con chaleco inteligente ESP32. Captura frecuencia cardíaca (ECG AD8232), posición GPS (NEO-7M) e inclinación corporal (IMU MPU-6050) en tiempo real. Los datos se envían desde el chaleco al servidor Flask vía HTTPS/HMAC y se visualizan en dashboards por rol.

---

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | HTML5 · CSS3 · JavaScript vanilla · Three.js r128 (autohospedado) |
| Backend | Python 3 · Flask 3.1.x |
| Base de datos | MySQL 5.7 (XAMPP) · mysql-connector-python |
| Seguridad | Argon2id · Fernet · HMAC-SHA256 · TOTP (pyotp) · Flask-Talisman · Flask-WTF CSRF |
| Hardware | ESP32 · AD8232 (ECG) · NEO-7M (GPS) · MPU-6050 (IMU) |
| Íconos | Sprite SVG propio (43 símbolos, `_sprite.svg.html`) + Devicon SVG para stack tecnológico |
| Fuentes | Bahnschrift (títulos) · Trebuchet MS (cuerpo) · Cascadia Code (datos) |

---

## 3. Arquitectura en capas

```
app/
├── presentacion/    # Blueprints Flask, controladores HTTP, templates Jinja2
│   ├── auth_controlador.py          (login, registro, logout, 2FA, verificar email)
│   ├── admin_controlador.py         (CRUD usuarios, dispositivos, auditoría, roles)
│   ├── deportista_controlador.py    (sesiones, detalle, en_vivo)
│   ├── entrenador_controlador.py    (deportistas asignados, detalle)
│   ├── usuario_controlador.py       (perfil, cambio de rol a deportista)
│   ├── recuperacion_controlador.py  (reset por correo, reset por archivo de 12 códigos)
│   ├── publico_controlador.py       (home institucional con holograma)
│   ├── api_ingesta_controlador.py   (POST /api/v1/ingesta, GET /tiempo-real, GET /datos-graficas)
│   └── sesion_controlador.py        (crear/cerrar sesiones de entrenamiento)
├── negocio/         # Servicios puros, sin SQL ni HTTP
│   ├── auth_servicio.py
│   ├── metricas_servicio.py         (fórmula Keytel calorías, FCmax real)
│   ├── heuristica_servicio.py       (alertas idempotentes, ventana 30s)
│   ├── ingesta_servicio.py          (validación HMAC, rangos sensores)
│   └── seguridad/
│       ├── doble_factor_servicio.py (TOTP + OTP email)
│       └── recuperacion_archivo_servicio.py (lote 12 códigos)
├── datos/           # Repositorios SQL parametrizados
│   ├── base_repositorio.py          (pool mysql-connector, uno/muchos/ejecutar)
│   ├── usuario_repositorio.py
│   ├── sesion_repositorio.py
│   ├── lectura_repositorio.py       (ECG, GPS, IMU, series temporales)
│   ├── alerta_repositorio.py
│   ├── deportista_repositorio.py
│   └── dispositivo_repositorio.py
├── modelos/         # Dataclasses Python
├── comun/           # Decoradores, errores, seguridad_utils, extensiones Flask
├── static/
│   ├── css/         # tokens.css, base.css, animations.css, componentes.css, app.css, page-*.css, loader.css
│   ├── js/          # theme.js, ui.js, nav.js, login.js, loader.js, holograma3d.js, dashboard.js, tiempo_real.js
│   │   └── vendor/  # three.min.js r128, GLTFLoader.js r128
│   ├── models/      # cuerpo.glb (physioscan_constellation.glb)
│   └── img/stack/   # SVG Devicon: html5, css3, javascript, mysql, flask, python, arduino
└── templates/
    ├── base.html
    ├── componentes/ (_sprite.svg.html, navbar.html, footer.html)
    ├── publico/     (home.html)
    ├── auth/        (login.html, registro.html, verificar_2fa.html, verificar_otp.html)
    ├── admin/       (panel.html, usuarios.html, usuario_detalle.html, dispositivos.html, auditoria.html)
    ├── deportista/  (sesiones.html, sesion_detalle.html, en_vivo.html)
    ├── entrenador/  (deportistas.html, deportista_detalle.html)
    ├── usuario/     (perfil.html)
    └── recuperacion/(solicitar.html, verificar.html, nueva_contrasena.html, archivo.html)
```

---

## 4. Base de datos — decisiones clave

**Normalización:** 3FN/BCNF, 20+ tablas. Dos denormalizaciones documentadas: `metrica_sesion` (caché de cálculos) y `contador codigos_usados` en `lote_recuperacion`.

**IDs:**
- Todas las tablas: PK técnica `INT AUTO_INCREMENT` (`id_*`)
- Tabla `usuario`: además tiene `codigo_usuario CHAR(7)`, generado por trigger `BEFORE INSERT`
  - Formato: `LPAD(seq,5,'0') + inicial_primer_nombre + inicial_primer_apellido`
  - Ejemplo: `10001CR` (Camilo Ramírez)
  - Secuencia atómica con tabla `secuencia_codigo` y `LAST_INSERT_ID()`

**Cotejamiento:** `utf8mb4_general_ci` (MySQL 5.7, XAMPP — `utf8mb4_0900_ai_ci` no existe en 5.7)

**Scripts BD:**
```
database/
├── 01_schema.sql   # DDL completo
├── 02_triggers.sql # código_usuario, secuencias
├── 03_seed.sql     # roles (1=administrador, 2=entrenador, 3=deportista, 4=usuario), umbrales heurísticos
└── 04_vistas.sql   # vistas de reportes
```

**Roles:**

| id_rol | nombre | Descripción |
|---|---|---|
| 1 | administrador | Gestión total, reemisión archivos, cambio de roles |
| 2 | entrenador | Asignado por admin, ve deportistas asignados |
| 3 | deportista | Registrado desde perfil propio |
| 4 | usuario | Cuenta básica recién creada (rol por defecto al registrarse) |

---

## 5. Seguridad implementada

| Control | Implementación |
|---|---|
| Contraseñas | Argon2id (argon2-cffi) |
| Secreto TOTP | Fernet AES-128-CBC cifrado en BD |
| Tokens efímeros (email, verificación) | SHA-256, expiración configurable |
| 2FA | TOTP (pyotp) + OTP por correo (fallback) |
| Archivo recuperación | 12 códigos Argon2id, lote desactivado al agotar |
| Anti-replay | HMAC-SHA256 + timestamp ±60s en API del chaleco |
| CSRF | Flask-WTF en todos los formularios |
| Headers HTTP | Flask-Talisman (HSTS, CSP, X-Frame-Options, etc.) |
| CSP | `style-src 'self' 'unsafe-hashes'` · `script-src 'self'` · sin CDN |
| SQL Injection | 100% consultas parametrizadas, cero f-strings en SQL |
| Bloqueo | 5 intentos fallidos → bloqueo temporal |
| Anti-enumeración | Mismo mensaje para usuario inexistente y contraseña incorrecta |
| Sesiones servidor | Token opaco en BD, revocación total posible |
| Auditoría | Tabla `auditoria` con IP, user-agent, acción, timestamp |
| Ley 1581 | Aviso en footer, finalidad declarada |

---

## 6. API del chaleco ESP32

**Endpoint ingesta:** `POST /api/v1/ingesta`

**Autenticación:** HMAC-SHA256
```
firma = HMAC_SHA256(key=api_key, msg=codigo_dispositivo + timestamp + body)
Headers: X-Device-Code, X-Timestamp, X-Signature
```

**Formato JSON:**
```json
{
  "id_sesion": 42,
  "ecg": [{"adc": 2048, "bpm": 75, "lo": false, "t": "2026-06-04 10:00:00.000"}],
  "gps": [{"lat": 4.149, "lon": -74.884, "vel": 12.5, "sat": 8}],
  "imu": [{"ax": 0.1, "ay": 0.2, "az": 9.8, "gx": 0.01, "gy": 0.02, "gz": 0.03,
           "inc": 5.2, "t": "2026-06-04 10:00:00.000"}]
}
```

**Script simulador:** `scripts/simular_chaleco.py`
**Firmware:** `firmware/physioscan_chaleco.ino` + `firmware/config.h`

**Importante:** `SERVER_URL` en `config.h` debe ser la IP LAN del PC (ej: `192.168.1.100:5000`), nunca `127.0.0.1`.

---

## 7. Holograma 3D

- **Librería:** Three.js r128 autohospedado en `static/js/vendor/three.min.js`
- **GLTFLoader:** `static/js/vendor/GLTFLoader.js`
- **Modelo:** `static/models/cuerpo.glb` (physioscan_constellation.glb de Claude Design — estilo red de constelación, 301 nodos, 774 links)
- **Fallback:** geometría procedural con `CylinderGeometry + SphereGeometry` (NUNCA `CapsuleGeometry`, es r142+)
- **Material:** `PointsMaterial` (nodos #B4F8FF) + `LineBasicMaterial` (links #79DBFF), sin faces
- **Animación:** rotación lenta en Y, 3 anillos de escaneo sweeping bottom→top, plataforma HUD
- **Hooks globales:** `physioSetBPM(bpm)`, `physioSetIMU(pitch, roll)`

---

## 8. Sistema de diseño (Claude Design handoff)

**Fuente de verdad:** `design_handoff_physioscan/frontend/` (descomprimido en raíz del repo)

**Archivos CSS:**
```
tokens.css      → variables dark/light (data-theme en <html>)
base.css        → reset, tipografía, focus ring
animations.css  → keyframes + prefers-reduced-motion
componentes.css → botones, cards, inputs, badges, modales
app.css         → navbar, sidebar, shell
page-auth.css, page-admin.css, page-dashboard.css,
page-perfil.css, page-navbar.css, page-icons.css
loader.css      → corazón ECG draw-in + fade-out
```

**Archivos JS:**
```
theme.js    → toggle dark/light, localStorage, anti-flash (en <head> sin defer)
ui.js       → contadores 0→valor, tabs, toasts (psToast), skeleton, velocímetro, BPM pulse
nav.js      → glass navbar al scroll, drawer móvil
login.js    → partículas flotantes + tabs login/registro
loader.js   → fade-out en window.onload
```

**Íconos:** Sprite SVG `_sprite.svg.html` (43 símbolos), uso: `<svg class="icon"><use href="#ic-heart"></use></svg>`

**Temas:**
- Dark (default): `--bg-base #020813`, `--accent #79DBFF`, `--text-primary #ECFBFF`
- Light (ciudadano de primera clase): `--bg-base #F0F7FF`, `--accent #0077B6`, `--text-primary #041425`
- Toggle: botón `#theme-toggle` en navbar con SVG luna/sol

**Íconos Devicon** (stack tecnológico, de `devicon-master/icons/`):
```
app/static/img/stack/html5.svg, css3.svg, javascript.svg,
mysql.svg, flask.svg, python.svg, arduino.svg
```

---

## 9. Dashboards y tiempo real

**Polling tiempo real:** `GET /api/v1/sesiones/{id}/tiempo-real` cada 2s
**Series para gráficas:** `GET /api/v1/sesiones/{id}/datos-graficas`

**Métricas calculadas:**
- Calorías: fórmula Keytel (2005) con datos demográficos del deportista, degradación a MET si faltan datos
- FCmax real: `fc_max_estimada` del deportista, o `208 - 0.7 * edad`, o 200 como fallback
- Distancia: fórmula Haversine entre puntos GPS

**Alertas heurísticas (idempotentes, ventana 30s):**
- `sobreesfuerzo_cardiaco`: % FCmax >= umbral configurable
- `electrodo_suelto`: flag `lo=true` del AD8232
- `caida_postura`: inclinación >= 45° (configurable)
- `fatiga`: delta BPM positivo en lote (recuperación cardíaca lenta)

---

## 10. Sesiones de Claude Code completadas

| Sesión | Contenido | Commit |
|---|---|---|
| S1 BD | Schema, triggers, seed, vistas, pool MySQL, dataclasses | `feat(db)` |
| S2 App factory | `create_app`, config por entorno, seguridad, extensiones | `feat(core)` |
| S3 Auth+2FA | Registro, login, TOTP, OTP email, bloqueo, templates dark | `feat(auth)` |
| S4 Recuperación+Admin | Reset correo, archivo 12 códigos, admin CRUD, RBAC, auditoría | `feat(seguridad)` |
| S5 Sensores+API | `/api/v1` HMAC, ingesta por lotes, firmware ESP32, simulador | `feat(ingesta)` |
| S6 Métricas+Dashboards | Keytel, FCmax real, tiempo real, dashboards deportista/entrenador | `feat(analitica)` |
| S7 Home+Holograma | Three.js r128, figura procedural, home institucional, responsive | `feat(ui)` |
| S-Roles | Rol `usuario` (id=4) por defecto, perfil editable, cambio rol admin | `feat(roles)` |
| S-Visual | Holograma constelación, loader ECG, dark/light, logos stack, CSP fix | `feat(visual)` |
| S8 Pruebas+Docs | 48 pruebas pytest en verde sin BD, pip-audit limpio, README, GUION_DEMO | `test+docs` |
| S-Design | Integración handoff Claude Design + Devicon stack logos (pendiente) | — |

**Último commit conocido:** `55529c5` — `test+docs`

---

## 11. Configuración del entorno

**`.env` requerido:**
```env
SECRET_KEY=235a8b691435d08be0ea79f241cee06767fb963a9585704fdf1695ff302b4406
FERNET_KEY=rHckecWB3i-UUknX5EYPlhKQJOx5fTvGXtCNT3iReFg=
MAIL_USERNAME=physioscan.uniespinal@gmail.com
MAIL_PASSWORD=vgko alsz avge nhgq
DB_PASSWORD=PhysioScan2024#
DB_ROOT_PASSWORD=
```

**Arrancar en desarrollo:**
```powershell
.\venv\Scripts\activate
python run.py
# o
flask --app app run --debug
```

**Crear admin inicial:**
```powershell
flask --app app crear-admin
```

**Correr pruebas:**
```powershell
.\venv\Scripts\python.exe -m pytest tests/ -v
```

---

## 12. Bugs conocidos y fixes aplicados

| Bug | Fix |
|---|---|
| `from flask import BuildError` | → `from werkzeug.routing.exceptions import BuildError` |
| `utf8mb4_0900_ai_ci` no existe en MySQL 5.7 | → `utf8mb4_general_ci` |
| PowerShell: `&&` no funciona | → comandos separados con `;` |
| `venv\Scripts\activate` falla en PS | → `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` primero |
| Three.js CSP inline styles | → `style-src 'self' 'unsafe-hashes'` en `__init__.py` |
| Login redirige a home en vez de dashboard | → Fix en `_destino_post_login()`, caso rol `usuario` → `/usuario/perfil` |

---

## 13. Pendientes para la demo

1. **Manual:** Copiar `physioscan_constellation.glb` → `app/static/models/cuerpo.glb`
2. **Manual:** Conectar chaleco físico, configurar IP LAN en `firmware/config.h`
3. **Claude Code:** Ejecutar el prompt de integración del handoff Claude Design + Devicon
4. **Demo:** Seguir `docs/GUION_DEMO.md` (10 pasos, ~25 minutos)

---

## 14. Archivos de referencia importantes

```
docs/ARQUITECTURA.md           → blueprint técnico completo
docs/GUION_DEMO.md             → pasos para la sustentación
docs/SEGURIDAD_CHECKLIST.md    → matriz OWASP/ISO 27001/Ley 1581
docs/REFACTOR.md               → deuda técnica documentada
README.md                      → instalación completa
firmware/README_firmware.md    → instrucciones del chaleco
design_handoff_physioscan/
  frontend/README.md           → instrucciones de integración del diseño
```
