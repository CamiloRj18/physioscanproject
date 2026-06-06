/* ============================================================
   PhysioScan — theme.js
   Cárgalo en <head> SIN defer para evitar el flash de tema.
   Aplica data-theme antes del primer pintado.
   ============================================================ */
(function () {
  var KEY = 'physioscan-theme';
  var stored;
  try { stored = localStorage.getItem(KEY); } catch (e) {}
  var theme = (stored === 'light' || stored === 'dark') ? stored : 'dark';
  document.documentElement.setAttribute('data-theme', theme);

  function setTheme(next) {
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
    document.querySelectorAll('[data-theme-toggle]').forEach(syncBtn);
  }
  function current() { return document.documentElement.getAttribute('data-theme'); }
  function syncBtn(btn) {
    var isLight = current() === 'light';
    btn.setAttribute('aria-pressed', isLight ? 'true' : 'false');
    btn.setAttribute('aria-label', isLight ? 'Cambiar a modo oscuro' : 'Cambiar a modo claro');
    var lbl = btn.querySelector('[data-theme-label]');
    if (lbl) lbl.textContent = isLight ? 'Oscuro' : 'Claro';
  }

  window.PhysioTheme = { set: setTheme, toggle: function () { setTheme(current() === 'light' ? 'dark' : 'light'); }, current: current };
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      syncBtn(btn);
      btn.addEventListener('click', function () { window.PhysioTheme.toggle(); });
    });
  });
})();
