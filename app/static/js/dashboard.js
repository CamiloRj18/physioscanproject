/**
 * PhysioScan — dashboard.js
 * Dibuja gráficas de sesión (BPM, inclinación, velocidad, ruta) con Canvas 2D nativo.
 * Consume el endpoint /api/v1/sesiones/{id}/datos-graficas (JSON).
 * Sin librerías externas. Respeta prefers-reduced-motion.
 */

(function () {
  'use strict';

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── Tokens de color ──────────────────────────────────────────────────────
  const COLORS = {
    grid:       'rgba(117, 218, 255, 0.10)',
    axisText:   '#9784C8',
    bpm:        '#79DBFF',
    bpmFill:    'rgba(121, 219, 255, 0.12)',
    inc:        '#FBBF24',
    incFill:    'rgba(251, 191, 36, 0.12)',
    vel:        '#2FD69E',
    velFill:    'rgba(47, 214, 158, 0.12)',
    route:      '#79DBFF',
    routeDot:   '#B4F8FF',
    bg:         '#041425',
  };

  // ── Helpers ──────────────────────────────────────────────────────────────
  function setDPR(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width  = rect.width  * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    return ctx;
  }

  function drawLineChart(canvas, series, opts) {
    if (!canvas) return;
    const ctx = setDPR(canvas);
    const W = canvas.getBoundingClientRect().width;
    const H = canvas.getBoundingClientRect().height;
    const pad = { top: 10, right: 10, bottom: 28, left: 40 };
    const iW = W - pad.left - pad.right;
    const iH = H - pad.top  - pad.bottom;

    ctx.clearRect(0, 0, W, H);

    if (!series || series.length === 0) {
      ctx.fillStyle = COLORS.axisText;
      ctx.font = '12px "Cascadia Code", Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Sin datos', W / 2, H / 2);
      return;
    }

    const vals = series.map(d => d.v);
    const minV = opts.minY !== undefined ? opts.minY : Math.min(...vals);
    const maxV = opts.maxY !== undefined ? opts.maxY : Math.max(...vals);
    const rangeV = maxV - minV || 1;

    function xOf(i) { return pad.left + (i / (series.length - 1 || 1)) * iW; }
    function yOf(v) { return pad.top  + (1 - (v - minV) / rangeV) * iH; }

    // Grid horizontal
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth   = 1;
    const ticks = 4;
    for (let i = 0; i <= ticks; i++) {
      const y = pad.top + (i / ticks) * iH;
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + iW, y); ctx.stroke();
      const label = Math.round(maxV - (i / ticks) * rangeV);
      ctx.fillStyle = COLORS.axisText;
      ctx.font = '10px "Cascadia Code", Consolas, monospace';
      ctx.textAlign = 'right';
      ctx.fillText(label, pad.left - 4, y + 4);
    }

    // Fill area
    ctx.beginPath();
    ctx.moveTo(xOf(0), yOf(series[0].v));
    for (let i = 1; i < series.length; i++) ctx.lineTo(xOf(i), yOf(series[i].v));
    ctx.lineTo(xOf(series.length - 1), pad.top + iH);
    ctx.lineTo(xOf(0), pad.top + iH);
    ctx.closePath();
    ctx.fillStyle = opts.fillColor;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.strokeStyle = opts.lineColor;
    ctx.lineWidth   = 2;
    ctx.lineJoin    = 'round';
    ctx.moveTo(xOf(0), yOf(series[0].v));
    for (let i = 1; i < series.length; i++) ctx.lineTo(xOf(i), yOf(series[i].v));
    ctx.stroke();

    // X labels (first, middle, last)
    const labelIdx = [0, Math.floor(series.length / 2), series.length - 1];
    ctx.fillStyle  = COLORS.axisText;
    ctx.font       = '9px "Cascadia Code", Consolas, monospace';
    ctx.textAlign  = 'center';
    labelIdx.forEach(i => {
      const t = series[i].t;
      const label = typeof t === 'string' ? t.slice(11, 19) : '';
      ctx.fillText(label, xOf(i), H - 8);
    });
  }

  function drawRoute(canvas, points) {
    if (!canvas) return;
    const ctx = setDPR(canvas);
    const W = canvas.getBoundingClientRect().width;
    const H = canvas.getBoundingClientRect().height;
    const pad = 20;

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, W, H);

    if (!points || points.length < 2) {
      ctx.fillStyle = COLORS.axisText;
      ctx.font = '12px "Cascadia Code", Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Sin recorrido GPS', W / 2, H / 2);
      return;
    }

    const lats = points.map(p => p[0]);
    const lons = points.map(p => p[1]);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);
    const minLon = Math.min(...lons), maxLon = Math.max(...lons);
    const ranLat = maxLat - minLat || 1e-5;
    const ranLon = maxLon - minLon || 1e-5;
    const scaleX = (W - pad * 2) / ranLon;
    const scaleY = (H - pad * 2) / ranLat;
    const scale  = Math.min(scaleX, scaleY);

    function ptX(lon) { return pad + (lon - minLon) * scale; }
    function ptY(lat) { return H - pad - (lat - minLat) * scale; }

    // Trace
    ctx.beginPath();
    ctx.strokeStyle = COLORS.route;
    ctx.lineWidth   = 2;
    ctx.lineJoin    = 'round';
    ctx.moveTo(ptX(points[0][1]), ptY(points[0][0]));
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(ptX(points[i][1]), ptY(points[i][0]));
    }
    ctx.stroke();

    // Start dot
    ctx.beginPath();
    ctx.arc(ptX(points[0][1]), ptY(points[0][0]), 5, 0, Math.PI * 2);
    ctx.fillStyle = COLORS.vel;
    ctx.fill();

    // End dot
    const last = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(ptX(last[1]), ptY(last[0]), 5, 0, Math.PI * 2);
    ctx.fillStyle = COLORS.routeDot;
    ctx.fill();
  }

  // ── Carga y renderizado ──────────────────────────────────────────────────
  function initCharts() {
    const panel = document.getElementById('charts-panel');
    if (!panel) return;
    const idSesion = panel.dataset.sesion;
    if (!idSesion) return;

    fetch('/api/v1/sesiones/' + idSesion + '/datos-graficas')
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(resp => {
        if (!resp.ok) return;
        const d = resp.datos;
        const cBpm = document.getElementById('chart-bpm');
        const cInc = document.getElementById('chart-inc');
        const cVel = document.getElementById('chart-vel');
        const cRuta = document.getElementById('chart-ruta');

        drawLineChart(cBpm,  d.bpm,        { lineColor: COLORS.bpm,  fillColor: COLORS.bpmFill,  minY: 40 });
        drawLineChart(cInc,  d.inclinacion, { lineColor: COLORS.inc,  fillColor: COLORS.incFill,  minY: 0  });
        drawLineChart(cVel,  d.velocidad,   { lineColor: COLORS.vel,  fillColor: COLORS.velFill,  minY: 0  });
        drawRoute(cRuta, d.ruta);
      })
      .catch(() => {});
  }

  // Redibuja al cambiar tamaño (debounced)
  let resizeTimer;
  window.addEventListener('resize', () => {
    if (reducedMotion) { initCharts(); return; }
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(initCharts, 200);
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCharts);
  } else {
    initCharts();
  }
})();
