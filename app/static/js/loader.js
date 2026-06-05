(function () {
  var loader = document.getElementById('page-loader');
  if (!loader) return;
  // Solo mostrar en la primera carga de la sesión
  if (sessionStorage.getItem('ps_loaded')) {
    loader.remove();
    return;
  }
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var heart = loader.querySelector('.loader-heart__path');
  if (heart && !reduce) {
    try {
      var L = heart.getTotalLength();
      heart.style.strokeDasharray = L;
      heart.style.strokeDashoffset = L;
      heart.getBoundingClientRect();
      heart.style.transition = 'stroke-dashoffset 1.8s ease';
      requestAnimationFrame(function() {
        requestAnimationFrame(function() { heart.style.strokeDashoffset = '0'; });
      });
    } catch(e) {}
  }
  function finish() {
    sessionStorage.setItem('ps_loaded', '1');
    loader.style.transition = reduce ? 'none' : 'opacity 0.5s ease';
    loader.style.opacity = '0';
    setTimeout(function() { if (loader.parentNode) loader.parentNode.removeChild(loader); }, reduce ? 0 : 550);
  }
  if (document.readyState === 'complete') { setTimeout(finish, 1800); }
  else { window.addEventListener('load', function() { setTimeout(finish, 1800); }); }
})();
