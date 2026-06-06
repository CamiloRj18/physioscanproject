(function () {
  var loader = document.getElementById('page-loader');
  if (!loader) return;

  // Solo mostrar en la primera carga de la sesión
  if (sessionStorage.getItem('ps_loaded')) {
    loader.remove();
    return;
  }

  var stage  = loader.querySelector('.page-loader-stage');   // FIX: era inexistente
  var heart  = stage && stage.querySelector('.ecg-heart');   // FIX: era '.loader-heart__path'
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // FIX: disparar animaciones CSS (beat, cursor, onda ECG slide)
  if (stage) stage.classList.add('play');

  // Draw-in del trazo del corazón vía CSSOM transition (CSP-safe; no inline HTML style).
  // El corazón es visible por defecto, cualquier fallo lo deja sólido.
  if (heart && !reduce) {
    try {
      var len = heart.getTotalLength();
      heart.style.strokeDasharray  = len;
      heart.style.strokeDashoffset = len;
      heart.getBoundingClientRect();                          // force reflow
      heart.style.transition = 'stroke-dashoffset 2s ease';
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { heart.style.strokeDashoffset = '0'; });
      });
      // Limpiar dash tras el draw-in → trazo sólido garantizado
      setTimeout(function () {
        heart.style.transition       = 'none';
        heart.style.strokeDasharray  = 'none';
        heart.style.strokeDashoffset = '0';
      }, 2250);
    } catch (e) {
      if (heart) heart.style.strokeDasharray = 'none';
    }
  }

  // FIX: mínimo visible 3800ms (suficiente para ver draw-in + beat + onda)
  var MIN_MS = 3800;
  var start  = Date.now();

  function finish() {
    var wait = Math.max(0, MIN_MS - (Date.now() - start));
    setTimeout(function () {
      sessionStorage.setItem('ps_loaded', '1');
      loader.classList.add('done');                           // FIX: clase en vez de inline style
      setTimeout(function () {
        if (loader && loader.parentNode) loader.parentNode.removeChild(loader);
      }, reduce ? 0 : 750);
    }, wait);
  }

  if (document.readyState === 'complete') finish();
  else window.addEventListener('load', finish);
})();
