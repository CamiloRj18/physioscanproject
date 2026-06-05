/* PhysioScan — Toggle dark/light mode
   Ejecutado en <head> (sin defer) para aplicar el tema antes del primer render
   y evitar el flash de modo incorrecto.
*/
(function () {
  "use strict";

  var STORAGE_KEY = "physioscan-theme";
  var DEFAULT     = "dark";

  function leerTema() {
    try { return localStorage.getItem(STORAGE_KEY) || DEFAULT; }
    catch (e) { return DEFAULT; }
  }

  function guardarTema(tema) {
    try { localStorage.setItem(STORAGE_KEY, tema); } catch (e) {}
  }

  function aplicarTema(tema) {
    var html = document.documentElement;
    html.setAttribute("data-theme", tema);

    if (document.body) {
      document.body.setAttribute("data-theme", tema);
    }

    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.setAttribute("aria-pressed", tema === "light" ? "true" : "false");
      btn.setAttribute("aria-label",
        tema === "light" ? "Activar modo oscuro" : "Activar modo claro");
    }
  }

  // Aplicar inmediatamente (antes del render del body)
  var temaActual = leerTema();
  document.documentElement.setAttribute("data-theme", temaActual);

  // Conectar el botón una vez que el DOM esté listo
  document.addEventListener("DOMContentLoaded", function () {
    aplicarTema(temaActual);

    var btn = document.getElementById("theme-toggle");
    if (!btn) return;

    btn.addEventListener("click", function () {
      temaActual = temaActual === "dark" ? "light" : "dark";
      aplicarTema(temaActual);
      guardarTema(temaActual);
    });
  });
})();
