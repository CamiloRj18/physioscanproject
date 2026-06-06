/* PhysioScan — login: partículas flotantes + cambio de tab por enlace */
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // partículas (CSSOM, CSP-safe)
  var box = document.getElementById('particles');
  if (box && !reduce) {
    var N = 16;
    for (var i = 0; i < N; i++) {
      var p = document.createElement('i');
      p.style.left = (Math.random() * 100).toFixed(2) + '%';
      p.style.top = (Math.random() * 100).toFixed(2) + '%';
      var sc = (0.5 + Math.random() * 1.4).toFixed(2);
      p.style.transform = 'scale(' + sc + ')';
      p.style.animationDuration = (5 + Math.random() * 6).toFixed(1) + 's';
      p.style.animationDelay = (-Math.random() * 7).toFixed(1) + 's';
      p.style.opacity = (0.25 + Math.random() * 0.5).toFixed(2);
      box.appendChild(p);
    }
  }

  // enlaces "crea una" / "ingresa aquí" cambian de pestaña
  document.querySelectorAll('[data-go]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var target = a.getAttribute('data-go');
      var tab = document.querySelector('.tab[data-tab="' + target + '"]');
      if (tab) tab.click();
    });
  });
})();
