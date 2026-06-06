# PHYSIOSCAN — Skill de Diseño y CSS

## Sistema de temas

**Dark (default):** data-theme="dark" en `<html>`
**Light:** data-theme="light" — mismo nivel de calidad que dark

```css
/* DARK */
--bg-base: #020813    --accent: #79DBFF    --text-primary: #ECFBFF
--bg-raised: #041425  --accent-strong: #B4F8FF  --text-secondary: #9784C8
--bg-surface: #071C34 --bg-glass: rgba(10,34,66,.52)
--success: #2FD69E    --danger: #FF7285    --warning: #FFC861
--border-soft: rgba(117,218,255,.14)  --border-strong: rgba(117,218,255,.32)
--glow: 0 0 24px rgba(121,219,255,.35)

/* LIGHT */
--bg-base: #F0F7FF    --accent: #0077B6    --text-primary: #041425
--bg-raised: #E2F0FF  --accent-strong: #005A8E  --text-secondary: #2D5A8E
--bg-surface: #FFFFFF --bg-glass: rgba(200,230,255,.70)
--glow: 0 0 20px rgba(0,119,182,.20)
--tint-accent: rgba(0,119,182,.10)
```

## Tipografías (del sistema, sin CDN)

```css
--font-title: Bahnschrift, "Segoe UI", system-ui, sans-serif
--font-body:  "Trebuchet MS", system-ui, sans-serif
--font-data:  "Cascadia Code", Consolas, "Courier New", monospace
```

## Archivos CSS en orden de carga (base.html)

```html
<link rel="stylesheet" href=".../css/tokens.css">
<link rel="stylesheet" href=".../css/base.css">
<link rel="stylesheet" href=".../css/animations.css">
<link rel="stylesheet" href=".../css/componentes.css">
<link rel="stylesheet" href=".../css/app.css">
<link rel="stylesheet" href=".../css/loader.css">
{% block page_css %}{% endblock %}
```

## Archivos JS en orden (base.html)

```html
<!-- En <head> SIN defer (anti-flash de tema) -->
<script src=".../js/theme.js"></script>

<!-- Al final del body -->
<script src=".../js/ui.js" defer></script>
<script src=".../js/nav.js" defer></script>
<script src=".../js/loader.js" defer></script>
{% block page_js %}{% endblock %}
```

## Íconos SVG

**Sprite:** `{% include 'componentes/_sprite.svg.html' %}` justo después de `<body>`

**Uso:**
```html
<svg class="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true">
  <use href="#ic-heart"></use>
</svg>
```

**Tamaños:**
```css
.icon    { width: 20px; height: 20px; }
.icon-sm { width: 16px; height: 16px; }
.icon-lg { width: 24px; height: 24px; }
```

## Componentes CSS principales

```css
/* Botones */
.btn           → base
.btn-primary   → fondo cian
.btn-secondary → ghost cian
.btn-ghost     → solo borde
.btn--sm       → tamaño pequeño

/* Cards */
.card          → card con borde y fondo surface
.reveal        → fade-up al hacer scroll (IntersectionObserver en ui.js)

/* Layout admin */
.shell         → grid sidebar + main
.sidebar       → panel izquierdo sticky
.main          → área de contenido
.main-head     → header sticky con blur
.main-body     → contenido con padding

/* Badges */
.badge         → pill genérico
.badge--activo    → verde
.badge--inactivo  → gris
.badge--bloqueado → rojo

/* Tabla */
.table-wrap    → contenedor con overflow
table.data     → tabla estilizada

/* Formularios */
.field         → input con float label
.field-select  → select estilizado con flecha SVG
.field-label   → label sobre select
.form-grid     → grid 2 columnas para formularios
.form-actions  → fila de botones al final del form
```

## Holograma 3D — reglas

```javascript
// CORRECTO en Three.js r128:
new THREE.CylinderGeometry(...)
new THREE.SphereGeometry(...)

// INCORRECTO — no existe en r128:
new THREE.CapsuleGeometry(...)  // ← NUNCA USAR, es r142+

// Cargar modelo desde el canvas:
const canvas = document.getElementById('holograma-canvas');
const modelUrl = canvas.dataset.model; // data-model="{{ url_for(...) }}"
```

## Loader del corazón

- Se muestra SOLO en la primera carga por sesión (sessionStorage)
- No interrumpe la navegación entre páginas
- Se controla en `static/js/loader.js`
- HTML en `base.html` antes del navbar
- CSS en `static/css/loader.css`

## Reglas de diseño absolutas

```
✓ Cero emojis — solo SVG inline o <use> del sprite
✓ Cero style="" en HTML — todo en archivos CSS externos
✓ Cero CDN — todo autohospedado en static/
✓ cursor: pointer en TODO elemento clickeable
✓ Hover con transition 150-200ms ease
✓ Focus visible para accesibilidad de teclado
✓ @media (prefers-reduced-motion: reduce) en animaciones
✓ WCAG AA: contraste mínimo 4.5:1
✓ Responsive: funcional en 375px, 768px, 1024px, 1440px
```
