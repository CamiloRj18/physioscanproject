/* ============================================================
   PhysioScan — ui.js  (vanilla, sin dependencias)
   Microinteracciones: contadores, dropdowns, tabs, mostrar/ocultar
   contraseña, medidor de fortaleza, sidebar móvil, toasts,
   barras de progreso animadas, latido BPM, velocímetro.
   Respeta prefers-reduced-motion.
   ============================================================ */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- contadores 0 → valor ---------- */
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var dec = (el.getAttribute('data-count').split('.')[1] || '').length;
    if (reduce) { el.textContent = target.toFixed(dec); return; }
    var dur = 800, t0 = null;
    function frame(t) {
      if (!t0) t0 = t;
      var p = Math.min((t - t0) / dur, 1);
      var e = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * e).toFixed(dec);
      if (p < 1) requestAnimationFrame(frame); else el.textContent = target.toFixed(dec);
    }
    requestAnimationFrame(frame);
  }

  /* ---------- barras de progreso (fill al entrar) ---------- */
  function fillBars(scope) {
    (scope || document).querySelectorAll('.progress > i[data-val]').forEach(function (b) {
      var v = b.getAttribute('data-val');
      requestAnimationFrame(function () { b.style.setProperty('--val', v); });
    });
  }

  /* ---------- latido sincronizado con BPM ---------- */
  function syncBeats() {
    document.querySelectorAll('[data-bpm]').forEach(function (el) {
      var bpm = parseFloat(el.getAttribute('data-bpm')) || 70;
      var dur = (60 / bpm).toFixed(3) + 's';
      el.style.animation = reduce ? 'none' : 'ps-beat ' + dur + ' ease-in-out infinite';
    });
  }

  /* ---------- velocímetro / aguja (rota a un ángulo) ---------- */
  function setGauges() {
    document.querySelectorAll('[data-needle]').forEach(function (n) {
      var deg = parseFloat(n.getAttribute('data-needle')) || 0;
      n.style.transition = reduce ? 'none' : 'transform .9s cubic-bezier(.34,1.4,.5,1)';
      requestAnimationFrame(function () { n.style.transform = 'rotate(' + deg + 'deg)'; });
    });
  }

  /* ---------- dropdown ---------- */
  function wireMenus() {
    document.querySelectorAll('[data-menu-trigger]').forEach(function (trg) {
      var panel = document.getElementById(trg.getAttribute('data-menu-trigger'));
      if (!panel) return;
      panel.classList.add('hidden');
      trg.addEventListener('click', function (e) {
        e.stopPropagation();
        panel.classList.toggle('hidden');
      });
    });
    document.addEventListener('click', function () {
      document.querySelectorAll('[data-menu-trigger]').forEach(function (trg) {
        var panel = document.getElementById(trg.getAttribute('data-menu-trigger'));
        if (panel) panel.classList.add('hidden');
      });
    });
  }

  /* ---------- tabs ---------- */
  function wireTabs() {
    document.querySelectorAll('[data-tabs]').forEach(function (group) {
      var tabs = group.querySelectorAll('[data-tab]');
      tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
          tabs.forEach(function (t) { t.classList.remove('active'); });
          tab.classList.add('active');
          var name = tab.getAttribute('data-tab');
          document.querySelectorAll('[data-panel]').forEach(function (p) {
            if (p.getAttribute('data-panel') === name) {
              p.classList.remove('hidden'); p.classList.add('reveal-in');
              p.style.animation = ''; void p.offsetWidth;
            } else { p.classList.add('hidden'); }
          });
        });
      });
    });
  }

  /* ---------- mostrar / ocultar contraseña ---------- */
  function wirePwToggles() {
    document.querySelectorAll('[data-pw-toggle]').forEach(function (btn) {
      var input = document.getElementById(btn.getAttribute('data-pw-toggle'));
      if (!input) return;
      btn.addEventListener('click', function () {
        var show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        btn.classList.toggle('on', show);
        btn.style.transform = show ? 'rotateY(180deg)' : 'none';
      });
    });
  }

  /* ---------- medidor de fortaleza ---------- */
  function wireStrength() {
    document.querySelectorAll('[data-strength-for]').forEach(function (meter) {
      var input = document.getElementById(meter.getAttribute('data-strength-for'));
      if (!input) return;
      input.addEventListener('input', function () {
        var v = input.value, s = 0;
        if (v.length >= 8) s++;
        if (/[A-Z]/.test(v) && /[a-z]/.test(v)) s++;
        if (/\d/.test(v)) s++;
        if (/[^A-Za-z0-9]/.test(v)) s++;
        meter.setAttribute('data-level', v ? s : 0);
      });
    });
  }

  /* ---------- sidebar / menú móvil ---------- */
  function wireToggles() {
    document.querySelectorAll('[data-toggle-target]').forEach(function (btn) {
      var el = document.getElementById(btn.getAttribute('data-toggle-target'));
      if (!el) return;
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        el.classList.toggle('open');
        btn.classList.toggle('on');
      });
    });
  }

  /* ---------- colapsables (slide-down) ---------- */
  function wireCollapse() {
    document.querySelectorAll('[data-collapse]').forEach(function (btn) {
      var el = document.getElementById(btn.getAttribute('data-collapse'));
      if (!el) return;
      el.classList.add('hidden');
      btn.addEventListener('click', function () {
        el.classList.toggle('hidden');
        if (!el.classList.contains('hidden')) { el.classList.add('reveal-in'); void el.offsetWidth; }
        btn.classList.toggle('on');
      });
    });
  }

  /* ---------- toast helper (global) ---------- */
  window.psToast = function (msg, kind) {
    var zone = document.querySelector('.toast-zone');
    if (!zone) { zone = document.createElement('div'); zone.className = 'toast-zone'; document.body.appendChild(zone); }
    var t = document.createElement('div');
    t.className = 'toast ' + (kind || 'info');
    t.innerHTML = '<span class="toast-msg"></span>';
    t.querySelector('.toast-msg').textContent = msg;
    zone.appendChild(t);
    setTimeout(function () { t.style.transition = 'opacity .3s, transform .3s'; t.style.opacity = '0'; t.style.transform = 'translateY(-12px)'; setTimeout(function () { t.remove(); }, 320); }, 3200);
  };

  /* ---------- skeleton → contenido (demo) ---------- */
  function demoSkeletons() {
    var holders = document.querySelectorAll('[data-skeleton-swap]');
    if (!holders.length) return;
    setTimeout(function () {
      holders.forEach(function (h) {
        var real = document.getElementById(h.getAttribute('data-skeleton-swap'));
        h.classList.add('hidden');
        if (real) { real.classList.remove('hidden'); real.classList.add('reveal-in');
          real.querySelectorAll('[data-count]').forEach(countUp);
          fillBars(real);
        }
      });
    }, 1100);
  }

  /* ---------- flash dismiss ---------- */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-dismiss]');
    if (btn) { var el = btn.closest('.flash'); if (el) el.remove(); }
  });

  /* ---------- init ---------- */
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-count]').forEach(function (el) {
      if (!el.closest('[id]') || !document.querySelector('[data-skeleton-swap="' + (el.closest('[id]') || {}).id + '"]')) countUp(el);
    });
    fillBars();
    syncBeats();
    setGauges();
    wireMenus();
    wireTabs();
    wirePwToggles();
    wireStrength();
    wireToggles();
    wireCollapse();
    demoSkeletons();
  });
})();
