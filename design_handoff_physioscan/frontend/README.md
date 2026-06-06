# PhysioScan — Sistema Front-end (handoff para Claude Code)

> **Para Claude Code:** esta carpeta `frontend/` es el **sistema de diseño y las 6 pantallas**
> de PhysioScan, construidas como HTML/CSS/JS **plano y CSP-safe**. NO son código de
> producción para copiar tal cual: son la **fuente visual de verdad**. Tu tarea es
> **portarlas a la app Flask** (`app/templates` + `app/static`) respetando el modelo en
> capas de `docs/ARQUITECTURA.md` y rellenando los datos con Jinja2 desde los servicios.
> Lee primero `docs/ARQUITECTURA.md` y `CLAUDE.md`.

---

## 0. Por qué esto encaja "tal cual" en tu stack

Todo el sistema ya cumple las **restricciones absolutas** del proyecto, así que el porte es casi 1:1:

- **CSP `style-src 'self'`** → cero `style="..."` en el HTML. Todo el CSS vive en `frontend/css/*.css`. (Lo poco dinámico —partículas, contadores, barras— se setea con `element.style` desde JS, que **sí** permite la CSP.)
- **CSP `script-src 'self'`** → cero CDN. Todo el JS es local en `frontend/js/*.js`, sin dependencias.
- **Cero emojis** → toda la iconografía es SVG inline (`frontend/icons.svg`, 43 símbolos).
- **`prefers-reduced-motion`** → cada animación tiene su contraparte reducida en `animations.css` y en cada `page-*.css`. La versión animada es el default; la reducida desactiva el movimiento dejando el estado final.
- **Temas dark/light de primera clase** → `data-theme` en `<html>`, conmutado por `theme.js` (cargado en `<head>` sin `defer` para evitar el flash), preferencia en `localStorage['physioscan-theme']`.
- **Tipografías del brief** → `--font-title` Bahnschrift · `--font-body` Trebuchet MS · `--font-data` Cascadia Code (con fallbacks). Autohospeda las fuentes en `static/fonts/` y declara `@font-face` (no Google Fonts, por CSP).

---

## 1. Mapa de archivos → destino en Flask

```
frontend/                                   →  app/
├── css/
│   ├── tokens.css        (dark+light, data-theme)   →  static/css/tokens.css
│   ├── base.css          (reset, tipografía, foco)  →  static/css/base.css
│   ├── animations.css    (keyframes + reduced)      →  static/css/animations.css
│   ├── components.css    (botones, cards, inputs…)  →  static/css/componentes.css
│   ├── app.css           (navbar, sidebar, shell)   →  static/css/app.css
│   └── page-*.css        (estilos por pantalla)     →  static/css/page-*.css
├── js/
│   ├── theme.js          (toggle + anti-flash)      →  static/js/theme.js
│   ├── ui.js             (contadores, tabs, menús…) →  static/js/ui.js
│   ├── nav.js            (glass al scroll + drawer)  →  static/js/nav.js
│   ├── login.js          (partículas + tabs)        →  static/js/login.js
│   └── icons-page.js     (galería de íconos, demo)   →  (solo para la página de íconos)
├── icons.svg             (sprite de 43 símbolos)    →  templates/componentes/_sprite.svg.html
└── *.html  (6 pantallas de referencia)              →  se recrean como templates Jinja2
```

### El sprite de íconos (importante)
En estos prototipos el sprite está **inlineado** dentro de cada `.html` (al inicio de `<body>`)
porque el `<use href="archivo.svg#id">` externo no siempre resuelve en previsualizadores.
**En Flask hazlo bien:** guarda `icons.svg` como `templates/componentes/_sprite.svg.html` y haz
`{% include 'componentes/_sprite.svg.html' %}` justo después de `<body>` en `base.html`. Luego
referencia cada ícono con `<svg class="icon"><use href="#ic-heart"></use></svg>`.

---

## 2. Las 6 pantallas (qué es cada una y con qué datos se rellena)

| Archivo | Pantalla | Datos Jinja (desde servicios) |
|---|---|---|
| `NAVBAR.html` | Barra de navegación (logueado y anónimo) | rol del usuario → links contextuales; iniciales para el avatar; `codigo_usuario` |
| `LOGIN_REGISTRO.html` | Ingreso + registro (split con visual animado) | CSRF token de Flask-WTF; mensajes flash; validación de `validadores.py` |
| `DASHBOARD_DEPORTISTA.html` | Panel del atleta | `metricas_servicio` (BPM, distancia, inclinación, duración), `alerta` (semáforo), historial de `sesion_entrenamiento` |
| `ADMIN_PANEL.html` | Panel admin (sidebar) | KPIs agregados; tabla `usuario` con rol/estado; `codigos_usados/total` del `lote_recuperacion`; acciones (crear/editar/bloquear/reemitir) |
| `PERFIL_USUARIO.html` | Perfil (4 tabs) | datos de `usuario`/`deportista`; estado `usuario_2fa`; % de perfil; `lote_recuperacion` activo (X/12) |
| `SISTEMA_ICONOS.html` | Catálogo de íconos (referencia de diseño) | — (no es una ruta; es documentación visual) |

**Convenciones que respetan el blueprint:**
- El **código de usuario** se muestra como `10001CR` (5 dígitos + iniciales) — campo de solo lectura.
- Roles: `administrador` · `entrenador` · `deportista` → badges `.badge-rol`.
- Estados de cuenta → badges con punto pulsante: activo (`.badge-success`), pendiente (`.badge-warning`), bloqueado (`.badge-danger` + `.live-dot.danger`).
- Semáforo heurístico verde/amarillo/rojo → `.semaphore.verde|amarillo|rojo` (el rojo tiene glow pulsante de alarma).
- Archivo de recuperación → "X de 12 usados" + barra + 12 puntos; badge "Archivo activo" (0 usados) o "Solicita reemisión" (12 usados).
- Holograma 3D del cuerpo → usa el visor y el `.glb` del otro paquete (`PhysioScan Constellation.html` / `physioscan_constellation.glb`), Three.js r128 **autohospedado** en `static/js/vendor/`.

---

## 3. Patrón de `base.html` (Jinja2) recomendado

```html
<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}PhysioScan{% endblock %}</title>
  <!-- anti-flash: theme.js ANTES del CSS, sin defer -->
  <script src="{{ url_for('static', filename='js/theme.js') }}"></script>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/tokens.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/base.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/animations.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/componentes.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">
  {% block page_css %}{% endblock %}
</head>
<body>
  {% include 'componentes/_sprite.svg.html' %}
  {% include 'componentes/navbar.html' %}
  {% block content %}{% endblock %}
  <script src="{{ url_for('static', filename='js/ui.js') }}"></script>
  {% block page_js %}{% endblock %}
</body>
</html>
```

- Cada pantalla → un template que `{% extends 'base.html' %}` y rellena `content` + `page_css` + `page_js`.
- Los datos fijos del HTML (148 bpm, "Camilo Ramírez", "10001CR", filas de tabla) se reemplazan por variables Jinja: `{{ m.bpm }}`, `{{ u.nombre_completo }}`, `{{ u.codigo_usuario }}`, `{% for u in usuarios %}…{% endfor %}`.
- Protege todo formulario que cambia estado con el token CSRF de Flask-WTF.

---

## 4. Tokens (resumen — la fuente es `css/tokens.css`)

**Dark** (`:root`, default): `--bg-base #020813` · `--bg-raised #041425` · `--bg-surface #071C34` · `--bg-glass rgba(10,34,66,.52)` · `--accent #79DBFF` · `--accent-strong #B4F8FF` · `--text-primary #ECFBFF` · `--text-secondary #9784C8` · `--success #2FD69E` · `--danger #FF7285` · `--border-soft rgba(117,218,255,.14)` · `--border-strong rgba(117,218,255,.32)` · `--glow 0 0 24px rgba(121,219,255,.35)`.

**Light** (`[data-theme="light"]`): `--bg-base #F0F7FF` · `--bg-raised #E2F0FF` · `--bg-surface #FFFFFF` · `--accent #0077B6` · `--accent-strong #005A8E` · `--text-primary #041425` · `--text-secondary #2D5A8E` · `--success #0B7A4E` · `--danger #C0392B`. Todos los pares texto/fondo cumplen **WCAG AA (≥4.5:1)**.

**Escala / radios:** espaciado 8px (`--s-1..--s-8`); radios `--r-card 8px`, `--r-panel 12px`, `--r-pill 999px`.

---

## 5. Animaciones implementadas (todas con contraparte reducida)

Entrada de página (`.reveal`, `.stagger`), hover de cards (lift + glow), botón primario con **shimmer**, links con **subrayado animado**, **contadores 0→valor** (`data-count`), **barras de progreso** animadas (`.progress > i[data-val]`), **latido BPM** (`data-bpm`), **dot EN VIVO** (pulso radial), **semáforo rojo** con glow de alarma, **velocímetro** con aguja (`data-needle`), **partículas** flotantes (login), **skeleton loaders** (`data-skeleton-swap`), **tabs** con subrayado deslizante, **toggle switch** spring, **dropdown** slide-down, **drawer** móvil, **toasts** (`window.psToast`), **mini-ECG** y **ruta GPS** que se dibujan. Todo se apaga/estatiza bajo `prefers-reduced-motion: reduce`.

> Nota de captura: algunos previsualizadores que clonan el DOM muestran las animaciones de
> opacidad en su fotograma inicial (oculto). En un navegador real se ven perfectas. Si
> necesitas pantallazos, desactiva animaciones temporalmente con un `<style>` inyectado.

---

## 6. Prompt sugerido para Claude Code

Pega esto en Claude Code, dentro del repo, con esta carpeta copiada en la raíz:

> «Lee `docs/ARQUITECTURA.md`, `CLAUDE.md` y `design_handoff_physioscan/frontend/README.md`.
> Integra el sistema de diseño de `frontend/` en la app Flask **una pantalla a la vez**,
> respetando el modelo en capas (presentación → negocio → datos):
> 1) Copia `frontend/css/*` y `frontend/js/*` a `app/static/`, y `icons.svg` a
>    `app/templates/componentes/_sprite.svg.html`.
> 2) Crea `app/templates/base.html` con el patrón del README (theme.js anti-flash + sprite incluido).
> 3) Recrea `componentes/navbar.html` desde `NAVBAR.html`, con links según `current_user` y rol.
> 4) Porta `LOGIN_REGISTRO.html` → `auth/login.html` + `auth/registro.html`, con CSRF y mensajes flash.
> 5) Porta `DASHBOARD_DEPORTISTA.html` → `deportista/dashboard.html`, rellenando métricas desde `metricas_servicio` y alertas reales.
> 6) Porta `ADMIN_PANEL.html` → `admin/panel.html`, con la tabla de `usuario` y las acciones (crear, editar, bloquear, reemitir archivo).
> 7) Porta `PERFIL_USUARIO.html` → `perfil/index.html` con sus 4 tabs (datos, deportivo, seguridad/2FA, recuperación X/12).
> Mantén CSP `style-src 'self'` y `script-src 'self'`: sin estilos inline en HTML, sin CDN.
> No metas SQL ni reglas de negocio en los controladores; usa los servicios. Verifica cada
> pantalla en dark y light antes de pasar a la siguiente.»

---

## 7. Checklist de porte

- [ ] `static/css` y `static/js` poblados; rutas con `url_for('static', …)`.
- [ ] `_sprite.svg.html` incluido una vez en `base.html`; íconos con `<use href="#ic-…">`.
- [ ] `theme.js` en `<head>` sin `defer`; toggle en navbar; preferencia en `localStorage`.
- [ ] Fuentes Bahnschrift / Trebuchet MS / Cascadia Code autohospedadas con `@font-face`.
- [ ] Datos fijos reemplazados por Jinja desde los servicios (nada de SQL en plantillas/controladores).
- [ ] CSRF en formularios; mensajes flash mapeados a `window.psToast` o `.toast`.
- [ ] Dark y light revisados; contraste AA; foco visible; navegable por teclado.
- [ ] `prefers-reduced-motion` respetado (ya viene en el CSS; no lo rompas).
- [ ] Holograma 3D (otro paquete) con Three.js r128 autohospedado, no CDN.
