/**
 * PhysioScan — tiempo_real.js
 * Polling cada 2 s al endpoint /api/v1/sesiones/{id}/tiempo-real.
 * Actualiza: BPM, inclinación, semáforo de alertas, mapa GPS (Leaflet).
 * Respeta prefers-reduced-motion.
 */

(function () {
  'use strict';

  const POLL_MS = 2000;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const COLORS = {
    route:      '#79DBFF',
    routeStart: '#2FD69E',
    routeEnd:   '#B4F8FF',
  };

  // ── Referencias DOM ──────────────────────────────────────────────────────
  const panel    = document.getElementById('live-panel');
  if (!panel) return;
  const idSesion = panel.dataset.sesion;
  if (!idSesion) return;

  const elBpm      = document.getElementById('live-bpm-value');
  const elInc      = document.getElementById('live-inc-value');
  const elIncBar   = document.getElementById('live-inc-bar');
  const elSemaforo = document.getElementById('live-semaforo');
  const elAlerts   = document.getElementById('live-alerts-list');
  const elStatus   = document.getElementById('live-status');

  // ── Mapa Leaflet ─────────────────────────────────────────────────────────
  let _map      = null;
  let _polyline = null;
  let _startDot = null;
  let _curDot   = null;
  let _mapReady = false;

  function initLeafletMap() {
    if (_mapReady) return true;
    const container = document.getElementById('live-map');
    if (!container || typeof L === 'undefined') return false;

    _map = L.map(container, { zoomControl: true, attributionControl: true })
             .setView([4.15, -74.5], 13);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(_map);

    _polyline = L.polyline([], {
      color: COLORS.route, weight: 3, opacity: 0.9,
    }).addTo(_map);

    _mapReady = true;
    return true;
  }

  function drawMap(puntos) {
    if (!_mapReady && !initLeafletMap()) return;
    if (!puntos || puntos.length === 0) return;

    const latlngs = puntos.map(p => [p[0], p[1]]);
    _polyline.setLatLngs(latlngs);

    // Punto de inicio (verde)
    if (!_startDot) {
      _startDot = L.circleMarker(latlngs[0], {
        radius: 6, color: COLORS.routeStart, fillColor: COLORS.routeStart,
        fillOpacity: 1, weight: 2,
      }).bindTooltip('Inicio').addTo(_map);
    }

    // Posición actual (cian pulsante)
    const last = latlngs[latlngs.length - 1];
    if (!_curDot) {
      _curDot = L.circleMarker(last, {
        radius: 9, color: '#fff', weight: 2,
        fillColor: COLORS.routeEnd, fillOpacity: 1,
      }).addTo(_map);
    } else {
      _curDot.setLatLng(last);
    }

    if (!reducedMotion) _map.setView(last, Math.max(_map.getZoom(), 16));
  }

  // ── Semáforo ─────────────────────────────────────────────────────────────
  function severidadActual(alertas) {
    if (!alertas || alertas.length === 0) return 'verde';
    if (alertas.some(a => a.severidad === 'rojo'))     return 'rojo';
    if (alertas.some(a => a.severidad === 'amarillo')) return 'amarillo';
    return 'verde';
  }

  function actualizarSemaforo(sev) {
    if (!elSemaforo) return;
    elSemaforo.className = 'semaphore ' + sev;        // FIX: clase CSS correcta
    const textos = { verde: 'Normal', amarillo: 'Precaución', rojo: 'Alerta' };
    const dotEl  = elSemaforo.querySelector('.s-dot'); // FIX: selector correcto en HTML
    const txtEl  = elSemaforo.querySelector('.semaforo__text');
    if (txtEl) txtEl.textContent = textos[sev] || sev;
    if (dotEl) dotEl.setAttribute('aria-label', 'Estado: ' + (textos[sev] || sev));
  }

  // ── Alertas ───────────────────────────────────────────────────────────────
  const TIPO_LABELS = {
    sobreesfuerzo_cardiaco: 'Sobreesfuerzo cardíaco',
    electrodo_suelto:       'Electrodo suelto',
    caida_postura:          'Caída / postura',
    fatiga:                 'Fatiga',
  };

  function alertIcon(sev) {
    const fill = { rojo: '#FF7285', amarillo: '#FBBF24', verde: '#2FD69E' }[sev] || '#9784C8';
    return `<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="${fill}" stroke-width="2" aria-hidden="true">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>`;
  }

  function actualizarAlertas(alertas) {
    if (!elAlerts) return;
    if (!alertas || alertas.length === 0) {
      elAlerts.innerHTML = '<li class="alert-item alert-item--verde"><span class="alert-item__text">Sin alertas activas</span></li>';
      return;
    }
    elAlerts.innerHTML = alertas.slice(0, 6).map(a => {
      const label = TIPO_LABELS[a.tipo] || a.tipo;
      return `<li class="alert-item alert-item--${a.severidad}">
        ${alertIcon(a.severidad)}
        <span class="alert-item__text">
          <span class="alert-item__tipo">${label}</span><br>
          ${a.mensaje}
        </span>
      </li>`;
    }).join('');
  }

  // ── BPM ──────────────────────────────────────────────────────────────────
  let prevBpm = null;

  function actualizarBpm(bpm) {
    if (!elBpm) return;
    const v = bpm !== null && bpm !== undefined ? bpm : '---';
    elBpm.textContent = v;

    elBpm.classList.remove('live-bpm__value--alto', 'live-bpm__value--critico');
    if (typeof bpm === 'number') {
      if (bpm >= 180)      elBpm.classList.add('live-bpm__value--critico');
      else if (bpm >= 150) elBpm.classList.add('live-bpm__value--alto');
    }

    if (!reducedMotion && prevBpm !== null && bpm !== null && bpm !== prevBpm) {
      elBpm.style.transition = 'color 300ms ease, transform 150ms ease';
      elBpm.style.transform  = 'scale(1.08)';
      setTimeout(() => { elBpm.style.transform = 'scale(1)'; }, 150);
    }
    prevBpm = bpm;
  }

  // ── Inclinación ──────────────────────────────────────────────────────────
  function actualizarInclinacion(inc) {
    if (elInc) elInc.textContent = inc !== null && inc !== undefined ? inc.toFixed(1) + '°' : '---';
    if (elIncBar) {
      const pct = Math.min(100, Math.max(0, (Math.abs(inc || 0) / 90) * 100));
      if (!reducedMotion) elIncBar.style.transition = 'width 300ms ease';
      elIncBar.style.width = pct + '%';
    }
  }

  // ── Polling ───────────────────────────────────────────────────────────────
  let consecutive_errors = 0;

  function poll() {
    fetch('/api/v1/sesiones/' + idSesion + '/tiempo-real')
      .then(r => {
        if (r.status === 410) { stopPolling(); return null; }
        return r.ok ? r.json() : Promise.reject(r.status);
      })
      .then(resp => {
        if (!resp) return;
        consecutive_errors = 0;
        if (elStatus) elStatus.textContent = 'Conectado';

        const d = resp.datos || {};
        actualizarBpm(d.ultimo_bpm);
        actualizarInclinacion(d.inclinacion);
        actualizarAlertas(d.alertas);
        actualizarSemaforo(severidadActual(d.alertas));
        if (d.recorrido) {
          panel.dataset.lastRoute = JSON.stringify(d.recorrido);
          drawMap(d.recorrido);
        }
      })
      .catch(() => {
        consecutive_errors++;
        if (elStatus) elStatus.textContent = 'Sin conexión…';
        if (consecutive_errors >= 10) stopPolling();
      });
  }

  let timer = setInterval(poll, POLL_MS);
  initLeafletMap();
  poll();

  function stopPolling() {
    clearInterval(timer);
    if (elStatus) elStatus.textContent = 'Sesión finalizada';
    const dotEl = document.querySelector('.live-indicator__dot');
    if (dotEl) dotEl.style.background = '#9784C8';
  }

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (_map) _map.invalidateSize();
      const lastRoute = panel.dataset.lastRoute;
      if (lastRoute) {
        try { drawMap(JSON.parse(lastRoute)); } catch (_) {}
      }
    }, 200);
  });
})();
