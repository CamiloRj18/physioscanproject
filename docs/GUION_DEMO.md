# Guión de Demostración — PhysioScan

Sustentación académica · UniEspinal 2026
Autor: Camilo Ramírez Jiménez

Tiempo estimado: 20–25 minutos.

---

## Preparación previa (5 min antes)

1. XAMPP activo con MySQL corriendo.
2. Servidor Flask en desarrollo: `venv\Scripts\python.exe -m flask --app app run --debug`
3. Abrir navegador en `http://127.0.0.1:5000`
4. Tener a mano:
   - Email de admin: el configurado con `flask crear-admin`
   - Contraseña de admin y sus códigos de recuperación
   - Código del dispositivo simulado (ej. `CHAL0001`) y su API key en texto plano
5. Terminal secundaria lista para ejecutar el simulador

---

## Paso 1 — Home institucional y holograma 3D (2 min)

**URL:** `http://127.0.0.1:5000/`

1. Mostrar el **loader** de corazón + ECG al cargar la página.
2. Señalar el **holograma 3D** en la sección hero: anillos de escaneo, plataforma HUD, partículas.
3. Activar el **modo claro** con el botón luna/sol del navbar. Volver a modo oscuro.
4. Hacer scroll hacia abajo mostrando las secciones de fade-up:
   - Visión / Misión
   - Objetivos
   - Paleta de colores (design system)
   - Tipografías
   - Stack tecnológico con logos oficiales

**Mensaje:** "Esta es la home institucional. El holograma carga un modelo GLB si está disponible, o genera la constelación proceduralmente como fallback."

---

## Paso 2 — Registro y verificación de correo (3 min)

**URL:** `/auth/registro`

1. Registrar un nuevo usuario:
   - Nombre: `Demo Deportista`
   - Email: `demo@ejemplo.com`
   - Contraseña válida (mínimo 12 caracteres, mayúsculas, dígitos, símbolo)
2. Sistema muestra los **12 códigos de recuperación** — descargar el archivo `.txt`.
3. Ir a la bandeja de correo (o mostrar el log de Flask si hay MAIL_SERVER de test) para verificar el token.
4. Si no hay SMTP de test: demostrar desde phpMyAdmin la tabla `token_recuperacion` y construir el enlace manualmente.
5. Verificar el correo → cuenta activa.

**Puntos a destacar:**
- El archivo de 12 códigos se muestra **una sola vez** (Argon2id hash en BD).
- El token de verificación es SHA-256 en BD; el texto plano solo viaja por correo.

---

## Paso 3 — Login con 2FA (2 min)

**URL:** `/auth/login`

1. Iniciar sesión con las credenciales del admin.
2. El sistema solicita el **código TOTP** (abrir Google Authenticator o Authy).
3. Ingresar el código de 6 dígitos → acceso al panel de admin.

**Puntos a destacar:**
- Argon2id para verificar la contraseña.
- `valid_window=1` en TOTP (±30 s de tolerancia de reloj).
- La sesión servidor usa un token SHA-256 revocable.

---

## Paso 4 — Panel de administrador (3 min)

**URL:** `/admin/panel`

1. Mostrar el **panel con métricas**: usuarios, sesiones, dispositivos.
2. Ir a **Usuarios** → crear un usuario deportista manualmente.
3. En el detalle del usuario, cambiar su **rol** a `deportista` desde el select.
4. Mostrar la **bitácora de auditoría** (`/admin/auditoria`): acciones registradas con IP y timestamp.
5. Ir a **Dispositivos** → mostrar el dispositivo `CHAL0001` con estado activo.

**Puntos a destacar:**
- Todas las acciones del admin se registran en `auditoria` (RGPD / Ley 1581).
- RBAC: `@rol_requerido("administrador")` protege cada ruta.

---

## Paso 5 — Sesión simulada con el chaleco (4 min)

**Terminal:** ejecutar el simulador

```bash
venv\Scripts\python.exe scripts/simular_chaleco.py \
    --url http://127.0.0.1:5000 \
    --codigo CHAL0001 \
    --key TU_API_KEY_EN_CLARO
```

1. El simulador inicia una sesión (`POST /api/v1/sesiones/iniciar`).
2. Envía 5 lotes de lecturas ECG/GPS/IMU firmadas con HMAC-SHA256.
3. Mostrar en la terminal la respuesta JSON con `recibidas` y `alertas`.
4. Finalizar la sesión (`POST /api/v1/sesiones/finalizar`).

**Puntos a destacar:**
- Cabecera `X-Signature: HMAC-SHA256(api_key, codigo+timestamp+body)`.
- Anti-replay: timestamp con desfase > 60 s es rechazado (mostrar el error).
- Validación de rangos: ADC fuera de 0–4095 se descarta silenciosamente.

---

## Paso 6 — Dashboard deportista en tiempo real (3 min)

1. Iniciar sesión con la cuenta del deportista (`demo@ejemplo.com`).
2. Ir a **Mis sesiones** (`/deportista/sesiones`).
3. Abrir la sesión recién creada → ver el **detalle**: BPM, distancia GPS, alertas.
4. (Opcional) Si el simulador sigue corriendo: ir a **En vivo** (`/deportista/en-vivo/<id>`) y mostrar el polling cada 2 s.

**Puntos a destacar:**
- Gráfica Canvas 2D nativa (sin Chart.js, sin CDN).
- Mini-mapa de recorrido GPS con proyección lat/lon → píxeles.
- Semáforo animado (verde/amarillo/rojo) según alertas heurísticas.

---

## Paso 7 — Alertas heurísticas (2 min)

1. Mostrar en el simulador un lote con BPM alto (≥ 85% de FC máx) o inclinación > 45°.
2. La respuesta JSON incluye `"alertas": [{"tipo": "sobreesfuerzo_cardiaco", "severidad": "rojo"}]`.
3. Refrescar el dashboard en vivo → semáforo cambia a rojo.
4. En phpMyAdmin mostrar la tabla `alerta` con el registro recién creado.

**Puntos a destacar:**
- Idempotencia: la misma alerta dentro de 30 s no se duplica.
- FCmax calculada dinámicamente: `208 - 0.7 * edad` o `deportista.fc_max_estimada`.

---

## Paso 8 — Recuperación de contraseña con archivo (2 min)

**URL:** `/recuperar/archivo`

1. Cerrar sesión.
2. Ir a "Recuperar con archivo de recuperación".
3. Ingresar el email y uno de los 12 códigos del archivo descargado en el Paso 2.
4. Ingresar una nueva contraseña válida y diferente.
5. Sistema restablece la contraseña, **revoca todas las sesiones** activas y redirige al login.

**Puntos a destacar:**
- Comparación Argon2id en tiempo constante (no enumera cuál código es inválido).
- Al usar el código #12 el lote se desactiva; solo el admin puede reemitir.

---

## Paso 9 — Reemisión de archivo desde admin (1 min)

1. Iniciar sesión como admin.
2. Ir al detalle del usuario → **Reemitir archivo de recuperación**.
3. Se genera un nuevo lote con `numero_lote = anterior + 1`, generado_por = id_admin.
4. Auditoría registra `LOTE_REEMITIDO`.

---

## Paso 10 — Tests y seguridad (2 min)

**Terminal:**

```bash
venv\Scripts\python.exe -m pytest tests/ -v
```

1. Mostrar las **48 pruebas en verde** en ~1 segundo (sin BD activa).
2. Mostrar:

```bash
venv\Scripts\python.exe -m pip_audit
# → No known vulnerabilities found
```

3. Señalar `docs/SEGURIDAD_CHECKLIST.md` con la matriz OWASP completa.

---

## Cierre (1 min)

Resaltar las decisiones de diseño más importantes:

| Decisión | Por qué |
|---|---|
| Argon2id para contraseñas y códigos | Resistente a GPU/ASIC, parámetros configurables |
| Fernet para secreto TOTP | Cifrado reversible en reposo; el servicio puede descifrar al autenticar |
| HMAC-SHA256 en ingesta | Autenticidad del payload sin TLS obligatorio en LAN de prueba |
| 12 códigos de recuperación | Independencia del correo; trazabilidad de uso |
| Three.js autohospedado | CSP estricta sin `unsafe-inline`; sin dependencia de CDN externo |
| Capas presentación→negocio→datos | Testeable, mantenible, sin SQL en controladores |

---

*Fin del guión. Tiempo total estimado: 20–25 minutos.*
