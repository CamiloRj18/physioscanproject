/* PhysioScan — pobla la galería de íconos en ambos temas (CSP-safe, externo) */
(function () {
  var ICONS = [
    ['ic-heart', 'corazon'], ['ic-ecg', 'onda-ecg'], ['ic-gps', 'gps-pin'],
    ['ic-gyro', 'giroscopio'], ['ic-speed', 'velocimetro'], ['ic-thermo', 'termometro'],
    ['ic-user', 'usuario'], ['ic-users', 'usuarios-grupo'], ['ic-gear', 'engranaje'],
    ['ic-bell', 'campana'], ['ic-logout', 'logout'], ['ic-menu', 'menu-hamburger'],
    ['ic-arrow-left', 'flecha-izq'], ['ic-arrow-right', 'flecha-der'], ['ic-chevron-up', 'chevron-up'],
    ['ic-chevron-down', 'chevron-down'], ['ic-x', 'x-cerrar'], ['ic-search', 'buscar'],
    ['ic-check-circle', 'check-circle'], ['ic-alert-triangle', 'alert-triangle'], ['ic-x-circle', 'x-circle'],
    ['ic-info-circle', 'info-circle'], ['ic-lock', 'candado-cerrado'], ['ic-lock-open', 'candado-abierto'],
    ['ic-shield', 'escudo'], ['ic-eye', 'ojo'], ['ic-eye-off', 'ojo-tachado'],
    ['ic-grid', 'grid-panel'], ['ic-device', 'tablet-dispositivo'], ['ic-log', 'lista-bitacora'],
    ['ic-user-plus', 'user-plus'], ['ic-user-x', 'user-x'], ['ic-user-edit', 'user-edit'],
    ['ic-refresh', 'refresh'], ['ic-plus', 'plus'], ['ic-edit', 'edit-pencil'],
    ['ic-trash', 'trash'], ['ic-download', 'download'], ['ic-upload', 'upload'],
    ['ic-filter', 'filter'], ['ic-external', 'external-link'], ['ic-copy', 'copy'], ['ic-check', 'check-solo']
  ];
  var SVGNS = 'http://www.w3.org/2000/svg';
  function build(target) {
    var frag = document.createDocumentFragment();
    ICONS.forEach(function (it) {
      var tile = document.createElement('div');
      tile.className = 'ic-tile';
      var svg = document.createElementNS(SVGNS, 'svg');
      svg.setAttribute('class', 'icon icon-lg');
      svg.setAttribute('viewBox', '0 0 24 24');
      var use = document.createElementNS(SVGNS, 'use');
      use.setAttribute('href', '#' + it[0]);
      svg.appendChild(use);
      var name = document.createElement('span');
      name.className = 'ic-name';
      name.textContent = it[1];
      tile.appendChild(svg);
      tile.appendChild(name);
      frag.appendChild(tile);
    });
    target.appendChild(frag);
  }
  document.addEventListener('DOMContentLoaded', function () {
    var d = document.getElementById('grid-dark'), l = document.getElementById('grid-light');
    if (d) build(d);
    if (l) build(l);
    var c = document.getElementById('ic-count');
    if (c) c.textContent = ICONS.length;
  });
})();
