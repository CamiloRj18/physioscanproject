/* PhysioScan — Loader: oculta el overlay al terminar de cargar la página */
(function () {
  "use strict";

  function ocultarLoader() {
    var loader = document.getElementById("page-loader");
    if (loader) {
      loader.classList.add("loader--hidden");
    }
  }

  if (document.readyState === "complete") {
    setTimeout(ocultarLoader, 350);
  } else {
    window.addEventListener("load", function () {
      setTimeout(ocultarLoader, 350);
    });
  }
})();
