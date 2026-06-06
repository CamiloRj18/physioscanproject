/* PhysioScan — navbar: glass al scroll + drawer móvil */
(function () {
  var nav = document.getElementById('nav');
  if (nav) {
    var onScroll = function () { nav.classList.toggle('scrolled', window.scrollY > 8); };
    onScroll(); window.addEventListener('scroll', onScroll, { passive: true });
  }
  var drawer = document.getElementById('drawer');
  var scrim = document.getElementById('drawerScrim');
  function set(open) {
    if (!drawer) return;
    drawer.classList.toggle('open', open);
    if (scrim) scrim.classList.toggle('open', open);
  }
  document.querySelectorAll('[data-drawer]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var act = btn.getAttribute('data-drawer');
      set(act === 'toggle' ? !drawer.classList.contains('open') : act === 'open');
    });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
})();
