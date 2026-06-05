# Checklist de Seguridad — PhysioScan

Basado en la matriz §6.4 del Blueprint Técnico (OWASP Top 10 · ISO/IEC 27001:2022 · Ley 1581/2012).

Estado del sistema al 2026-06-04. `[x]` = implementado y verificado.

---

## OWASP Top 10

### A01 — Broken Access Control / IDOR

- [x] **RBAC** con `@rol_requerido(rol)` en todas las rutas sensibles (`app/comun/decoradores.py`)
- [x] **Verificación a nivel de objeto**: un deportista solo consulta sus propias sesiones; un entrenador solo accede a deportistas asignados (`listar_asignaciones_entrenador`)
- [x] Rutas `/admin/` exigen rol `administrador` — verificado en `admin_controlador.py`
- [x] `@login_required` de Flask-Login en toda ruta que requiere sesión autenticada
- [ ] **Pendiente**: mover verificaciones de objeto desde controladores a servicios (ver `docs/REFACTOR.md`)

### A02 — Cryptographic Failures

- [x] **Contraseñas**: Argon2id via `argon2-cffi` (`hash_password`, `verificar_password` en `seguridad_utils.py`)
- [x] **Códigos de recuperación**: Argon2id (`hash_codigo`, `verificar_codigo`)
- [x] **Secreto TOTP**: cifrado en reposo con Fernet AES-128-CBC (`cifrar_secreto`, `descifrar_secreto`)
- [x] **Tokens efímeros** (email, reset, 2FA): SHA-256 de `secrets.token_urlsafe(32)` — nunca texto plano en BD
- [x] **API key dispositivo**: Argon2id; texto plano mostrado **una sola vez** al crear el dispositivo
- [x] **HMAC-SHA256** en ingesta ESP32 para autenticidad del payload
- [x] **HSTS** habilitado en producción (`strict_transport_security=True`, 2 años) via Talisman
- [x] Sesiones con cookie `Secure` + `HttpOnly` + `SameSite=Lax` en producción
- [x] Fernet key y SECRET_KEY cargados desde `.env` — nunca hardcodeados

### A03 — Injection

- [x] **SQL Injection**: 100% consultas parametrizadas con `%s` (mysql-connector); prohibido concatenar SQL
  - Verificado: `grep -r "f\"SELECT\|'%s' %" app/datos/` → 0 resultados
- [x] **XSS**: autoescape activado en Jinja2 por defecto; sin `| safe` innecesario en templates
- [x] **CSP estricta**: `script-src 'self'`, `style-src 'self' 'unsafe-hashes'`, sin CDN externo — via Talisman
- [x] Sin `eval()`, `innerHTML` ni eventos inline en JavaScript propio

### A04 — Insecure Design

- [x] Modelo en 3 capas con separación estricta: Presentación → Negocio → Datos
- [x] Principio de mínimo privilegio: servicios reciben solo los datos que necesitan
- [x] Secretos nunca viajan a la capa de presentación (solo IDs y DTOs)
- [x] Registro devuelve `(id, token_claro, codigos_planos)` en memoria — no guardados en claro

### A05 — Security Misconfiguration

- [x] `Flask-Talisman` configurado con CSP, HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`
- [x] `DEBUG=False` en `ConfigProduccion` (`config.py`)
- [x] Handlers de error personalizados sin stack trace (`app/comun/errores.py`)
- [x] `MAX_CONTENT_LENGTH = 2 MB` en configuración de Flask
- [x] `form-action 'self'` en CSP — previene exfiltración de formularios
- [x] `frame-ancestors 'none'` — previene clickjacking

### A06 — Vulnerable and Outdated Components

- [x] Versiones fijadas en `requirements.txt`
- [x] `pip-audit` ejecutado: **0 vulnerabilidades en librerías de la aplicación** (2026-06-04)
- [x] Three.js r128 **autohospedado** en `static/js/vendor/` — sin CDN externo
- [x] Sin dependencias con CVE críticos conocidos a la fecha de cierre
- [ ] **Proceso**: ejecutar `pip-audit` en cada PR antes de merge a main

### A07 — Identification and Authentication Failures

- [x] Argon2id con parámetros por defecto (`time_cost=3`, `mem=64 MB`)
- [x] **2FA**: TOTP (RFC 6238) con ventana `valid_window=1` + OTP email de respaldo
- [x] **Bloqueo por intentos**: 5 fallos → cuenta bloqueada 15 min (`intentos_fallidos`, `bloqueado_hasta`)
- [x] **Anti-enumeración**: mismo mensaje y tiempo (`_DUMMY_HASH`) para usuario inexistente vs contraseña incorrecta
- [x] **Sesiones del lado servidor**: token hash SHA-256 revocable individualmente o en bloque
- [x] Restablecimiento de contraseña revoca **todas las sesiones** activas
- [x] Cookie de sesión `HttpOnly` + `Secure` (producción) + `SameSite=Lax`
- [x] `session_protection = "strong"` en Flask-Login
- [x] Rate-limit en `/auth/login` y `/auth/registro` via Flask-Limiter

### A08 — Software and Data Integrity Failures

- [x] **HMAC-SHA256** en todos los envíos del firmware ESP32: `HMAC(api_key, codigo+timestamp+body)`
- [x] **Anti-replay**: ventana de ±60 s en `ingesta_servicio.autenticar_dispositivo`
- [x] Validación de rangos de sensores antes de insertar en BD (ECG: 0–4095, GPS: ±90/±180)
- [x] CSRF via Flask-WTF `CSRFProtect` en todos los formularios que cambian estado
- [x] API de ingesta exenta de CSRF (`csrf.exempt(bp_api_ingesta)`) — protegida por HMAC

### A09 — Security Logging and Monitoring Failures

- [x] Tabla `auditoria` append-only registra: `LOGIN_OK`, `LOGIN_FAIL`, `2FA_OK`, `2FA_FAIL`, `CUENTA_BLOQUEADA`, `EMAIL_VERIFICADO`, `CONTRASENA_RESTABLECIDA_*`, `LOTE_GENERADO`, `LOTE_REEMITIDO`, `ADMIN_ROL_CAMBIADO`, `CODIGO_ARCHIVO_INVALIDO`, `REGISTRO`
- [x] `auditoria_servicio.registrar()` es silencioso (no lanza en producción) — no rompe flujos
- [x] Panel de bitácora en `/admin/auditoria` con filtros y paginación
- [x] Trigger MySQL `trg_usuario_auditoria_estado` registra cambios de estado de cuenta
- [ ] **Pendiente**: alertas automáticas a admin ante patrones de ataque (>N bloqueos/hora)

### A10 — Server-Side Request Forgery (SSRF)

- [x] La aplicación **no fetcha** URLs provistas por el usuario
- [x] Sin proxy ni redirección de recursos externos controlados por el usuario
- [x] CORS: no configurado (solo CORS implícito a `'self'` por CSP)

---

## Controles adicionales

### Fuerza bruta / DoS

- [x] `Flask-Limiter`: rate-limit global + por ruta (login: 10/min, ingesta: 120/min)
- [x] `MAX_CONTENT_LENGTH = 2 MB` en config
- [x] Lote de ingesta limitado a 500 muestras totales por request
- [x] Paginación en todas las listas (admin panel, bitácora, sesiones)

### CSRF

- [x] `Flask-WTF CSRFProtect` activo globalmente
- [x] Token CSRF en formularios: `{{ csrf_token() }}` en todos los `<form method="post">`
- [x] API de ingesta exenta explícitamente (`csrf.exempt(bp_api_ingesta)`)

### Enumeración de cuentas

- [x] Login: mensaje genérico "Credenciales inválidas" para email inexistente y contraseña incorrecta
- [x] Restablecimiento por correo: respuesta genérica independientemente de si el email existe
- [x] Mismo tiempo de respuesta via `_DUMMY_HASH` en ambos casos

### Privilegio de BD

- [x] Aplicación usa usuario MySQL con permisos DML únicamente (SELECT, INSERT, UPDATE, DELETE)
- [x] Migraciones con usuario separado con DDL
- [x] Documentado en `docs/INSTALL_DB.md`

### Ley 1581 de 2012 (Colombia — Protección de Datos Personales)

- [x] Aviso de tratamiento de datos en footer (`base.html`): "Datos personales tratados conforme a Ley 1581/2012"
- [x] Perfil deportivo (peso, altura, fecha nacimiento, FC) almacenado de forma cifrada en tránsito (TLS)
- [x] Sin venta ni transferencia de datos a terceros en el diseño actual
- [ ] **Pendiente**: política de privacidad completa como página separada antes de producción real

---

## Resultado pip-audit (2026-06-04)

```
No known vulnerabilities found
```

Paquetes auditados: todos los declarados en `requirements.txt` tras upgrade de pip a 26.1.

---

## Próximas acciones de seguridad

1. Implementar `tests/test_seguridad.py` con casos de IDOR (acceder sesión de otro deportista → 403)
2. Agregar `Content-Security-Policy-Report-Only` en desarrollo para detectar violaciones CSP
3. Configurar alertas de bloqueos masivos en panel admin
4. Publicar política de privacidad completa (Ley 1581) antes de puesta en producción
