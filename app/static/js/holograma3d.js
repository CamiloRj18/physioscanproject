/* PhysioScan — Holograma 3D "Constelación" · Three.js r128
   - Carga cuerpo.glb con GLTFLoader; material emissive cian + wireframe superpuesto
   - Anillos de escaneo (scan rings) que barren el cuerpo de abajo a arriba
   - Plataforma HUD en la base con grid de líneas y anillo exterior
   - Partículas de constelación flotantes en el entorno
   - Rotación lenta en Y; luz puntual cian pulsante
   - Fallback procedural: CylinderGeometry + SphereGeometry (NUNCA CapsuleGeometry, es r142+)
   - physioSetBPM(bpm) y physioSetIMU(pitch, roll) como hooks globales para el dashboard
   - Respeta prefers-reduced-motion
*/
(function () {
  "use strict";

  var canvas = document.getElementById("holograma-canvas");
  if (!canvas) return;

  // ── prefers-reduced-motion ─────────────────────────────────────────────────
  var reducedMotion = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;

  // ── Detección de WebGL ────────────────────────────────────────────────────
  function webglDisponible() {
    try {
      var probe = document.createElement("canvas");
      return !!(probe.getContext("webgl") || probe.getContext("experimental-webgl"));
    } catch (e) { return false; }
  }

  function mostrarFallback() {
    canvas.style.display = "none";
    var fb = document.getElementById("holograma-fallback");
    if (fb) fb.style.display = "flex";
  }

  if (typeof THREE === "undefined" || !webglDisponible()) {
    mostrarFallback();
    return;
  }

  // ── Escena ────────────────────────────────────────────────────────────────
  var scene  = new THREE.Scene();
  var w      = canvas.clientWidth  || 480;
  var h      = canvas.clientHeight || 600;
  var camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 50);
  camera.position.set(0, 0.5, 4.0);

  var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);

  // ── Iluminación ───────────────────────────────────────────────────────────
  scene.add(new THREE.AmbientLight(0x041425, 1.0));
  var puntual = new THREE.PointLight(0x79DBFF, 3.5, 16);
  puntual.position.set(2, 3, 2);
  scene.add(puntual);
  var rimLight = new THREE.PointLight(0x19AAFF, 1.2, 10);
  rimLight.position.set(-2, 0, -1);
  scene.add(rimLight);

  // ── Materiales ────────────────────────────────────────────────────────────
  var CYAN = 0x79DBFF;

  var matSolido = new THREE.MeshStandardMaterial({
    color: 0x020813, emissive: new THREE.Color(CYAN),
    emissiveIntensity: 0.55, metalness: 0.2, roughness: 0.7,
    transparent: true, opacity: 0.82,
  });

  var matWire = new THREE.MeshBasicMaterial({
    color: CYAN, wireframe: true, transparent: true, opacity: 0.18,
  });

  var matAnillo = new THREE.MeshBasicMaterial({
    color: 0xB4F8FF, transparent: true, opacity: 0.55, side: THREE.DoubleSide,
  });

  var matCardiaco = new THREE.MeshStandardMaterial({
    color: 0xFF7285, emissive: new THREE.Color(0xFF7285),
    emissiveIntensity: 0.6, transparent: true, opacity: 0.9,
  });

  // ── Estado para hooks ─────────────────────────────────────────────────────
  var grupoBody    = null;
  var grupoTorso   = null;
  var meshCardiaco = null;
  var pulsoBPM     = 0;
  var pulsoDelta   = 2.0;

  // ── Anillos de escaneo ─────────────────────────────────────────────────────
  var anillos = [];
  var SCAN_MIN_Y    = -1.55;
  var SCAN_MAX_Y    =  2.0;
  var SCAN_VEL      = reducedMotion ? 0 : 0.85;

  function crearAnillos() {
    for (var i = 0; i < 3; i++) {
      var geo = new THREE.RingGeometry(0.52, 0.58, 52);
      var mat = matAnillo.clone();
      mat.opacity = 0.25 + i * 0.08;
      var mesh = new THREE.Mesh(geo, mat);
      mesh.rotation.x = Math.PI / 2;
      var offsetY = SCAN_MIN_Y + (i / 3) * (SCAN_MAX_Y - SCAN_MIN_Y);
      mesh.position.y = offsetY;
      mesh.userData.fase = offsetY - SCAN_MIN_Y;
      scene.add(mesh);
      anillos.push(mesh);
    }
  }
  crearAnillos();

  // ── Plataforma HUD ─────────────────────────────────────────────────────────
  function crearPlataforma() {
    var matDisc = new THREE.MeshBasicMaterial({
      color: CYAN, transparent: true, opacity: 0.12, side: THREE.DoubleSide,
    });
    var geoDisc = new THREE.CircleGeometry(0.72, 52);
    var disc    = new THREE.Mesh(geoDisc, matDisc);
    disc.rotation.x = -Math.PI / 2;
    disc.position.y = -1.56;
    scene.add(disc);

    var matRing = matAnillo.clone();
    matRing.opacity = 0.45;
    var geoRing = new THREE.RingGeometry(0.70, 0.75, 52);
    var ring    = new THREE.Mesh(geoRing, matRing);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = -1.56;
    scene.add(ring);

    var geoRing2 = new THREE.RingGeometry(0.85, 0.88, 52);
    var matRing2 = matAnillo.clone();
    matRing2.opacity = 0.18;
    var ring2 = new THREE.Mesh(geoRing2, matRing2);
    ring2.rotation.x = -Math.PI / 2;
    ring2.position.y = -1.56;
    scene.add(ring2);

    var lineMat = new THREE.LineBasicMaterial({ color: CYAN, transparent: true, opacity: 0.12 });
    var STEP = 0.22;
    for (var i = -3; i <= 3; i++) {
      var s = i * STEP;
      var h1 = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-0.68, -1.55, s),
        new THREE.Vector3( 0.68, -1.55, s),
      ]);
      scene.add(new THREE.Line(h1, lineMat));
      var v1 = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(s, -1.55, -0.68),
        new THREE.Vector3(s, -1.55,  0.68),
      ]);
      scene.add(new THREE.Line(v1, lineMat));
    }
  }
  crearPlataforma();

  // ── Partículas de constelación flotantes ───────────────────────────────────
  function crearParticulasConstelacion() {
    var count     = 90;
    var positions = new Float32Array(count * 3);
    for (var i = 0; i < count; i++) {
      positions[i * 3]     = (Math.random() - 0.5) * 5;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 5.5;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 2.5 - 1;
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    var mat = new THREE.PointsMaterial({ color: CYAN, size: 0.022, transparent: true, opacity: 0.35 });
    scene.add(new THREE.Points(geo, mat));
  }
  crearParticulasConstelacion();

  // ── Función auxiliar: añade malla + wireframe a un grupo ──────────────────
  function addMesh(grupo, geo, mat, pos, rotZ) {
    var mesh = new THREE.Mesh(geo, mat.clone());
    if (pos)  mesh.position.set(pos[0], pos[1], pos[2]);
    if (rotZ) mesh.rotation.z = rotZ;
    mesh.add(new THREE.Mesh(geo, matWire));
    grupo.add(mesh);
    return mesh;
  }

  // ── Fallback procedural (r128: CylinderGeometry + SphereGeometry ONLY) ────
  function construirCuerpoFallback() {
    grupoBody  = new THREE.Group();
    grupoTorso = new THREE.Group();

    // Cabeza
    addMesh(grupoBody, new THREE.SphereGeometry(0.30, 14, 14), matSolido, [0, 1.52, 0]);
    // Cuello
    addMesh(grupoBody, new THREE.CylinderGeometry(0.09, 0.11, 0.18, 8), matSolido, [0, 1.17, 0]);

    // Torso (en grupoTorso para rotación IMU)
    var torsoGeo  = new THREE.CylinderGeometry(0.26, 0.30, 0.82, 10);
    var torsoMesh = new THREE.Mesh(torsoGeo, matSolido.clone());
    torsoMesh.add(new THREE.Mesh(torsoGeo, matWire));

    // Nodo cardiaco
    meshCardiaco = new THREE.Mesh(new THREE.SphereGeometry(0.095, 8, 8), matCardiaco);
    meshCardiaco.position.set(-0.09, 0.14, 0.20);
    torsoMesh.add(meshCardiaco);
    grupoTorso.add(torsoMesh);
    grupoTorso.position.set(0, 0.62, 0);
    grupoBody.add(grupoTorso);

    // Pelvis
    addMesh(grupoBody, new THREE.CylinderGeometry(0.28, 0.26, 0.28, 8), matSolido, [0, 0.15, 0]);

    // Brazos
    [[-0.40, 0.63, 0], [0.40, 0.63, 0]].forEach(function (p, i) {
      addMesh(grupoBody, new THREE.CylinderGeometry(0.070, 0.060, 0.68, 7), matSolido, p,
        i === 0 ? 0.14 : -0.14);
    });
    // Antebrazos
    [[-0.43, 0.16, 0], [0.43, 0.16, 0]].forEach(function (p, i) {
      addMesh(grupoBody, new THREE.CylinderGeometry(0.055, 0.045, 0.56, 7), matSolido, p,
        i === 0 ? 0.28 : -0.28);
    });
    // Muslos
    [[-0.17, -0.38, 0], [0.17, -0.38, 0]].forEach(function (p) {
      addMesh(grupoBody, new THREE.CylinderGeometry(0.13, 0.11, 0.68, 8), matSolido, p);
    });
    // Pantorrillas
    [[-0.17, -0.88, 0], [0.17, -0.88, 0]].forEach(function (p) {
      addMesh(grupoBody, new THREE.CylinderGeometry(0.09, 0.075, 0.62, 8), matSolido, p);
    });
    // Pies
    [[-0.17, -1.26, 0.05], [0.17, -1.26, 0.05]].forEach(function (p) {
      var pie = new THREE.Mesh(
        new THREE.CylinderGeometry(0.055, 0.07, 0.09, 7),
        matSolido.clone()
      );
      pie.position.set(p[0], p[1], p[2]);
      pie.rotation.x = 0.45;
      grupoBody.add(pie);
    });

    scene.add(grupoBody);
  }

  // ── Carga del GLB ─────────────────────────────────────────────────────────
  function cargarGLB() {
    if (typeof THREE.GLTFLoader === "undefined") {
      construirCuerpoFallback();
      return;
    }
    var loader = new THREE.GLTFLoader();
    var glbUrl = canvas.getAttribute("data-model") || "/static/models/cuerpo.glb";
    loader.load(
      glbUrl,
      function (gltf) {
        grupoBody = gltf.scene;
        grupoBody.traverse(function (child) {
          if (child.isMesh) {
            child.material = matSolido.clone();
            child.add(new THREE.Mesh(child.geometry, matWire));
            if (!grupoTorso) grupoTorso = child;
          }
        });
        var caja = new THREE.Box3().setFromObject(grupoBody);
        var cen  = caja.getCenter(new THREE.Vector3());
        var tam  = caja.getSize(new THREE.Vector3());
        grupoBody.position.sub(cen);
        grupoBody.scale.setScalar(2.2 / tam.y);
        scene.add(grupoBody);
      },
      undefined,
      function () { construirCuerpoFallback(); }
    );
  }
  cargarGLB();

  // ── Loop de animación ─────────────────────────────────────────────────────
  var tiempoAnterior = performance.now();
  var scanT          = 0;
  var animFrameId;

  function animar() {
    animFrameId = requestAnimationFrame(animar);
    var ahora = performance.now();
    var dt    = Math.min((ahora - tiempoAnterior) / 1000, 0.05);
    tiempoAnterior = ahora;

    if (!reducedMotion) {
      // Rotación lenta del cuerpo
      if (grupoBody) grupoBody.rotation.y += 0.0038;

      // Anillos de escaneo: suben en bucle
      scanT += dt * SCAN_VEL;
      var rango = SCAN_MAX_Y - SCAN_MIN_Y;
      anillos.forEach(function (anillo, i) {
        var fase = (scanT + i * (rango / anillos.length)) % rango;
        anillo.position.y = SCAN_MIN_Y + fase;
        var prog   = fase / rango;
        // Máxima opacidad en el centro del recorrido, casi invisible en los extremos
        var opBase = 0.5 - Math.abs(prog - 0.5) * 0.9;
        anillo.material.opacity = Math.max(0.02, opBase);
      });

      // Pulso del nodo cardiaco
      pulsoBPM += dt * pulsoDelta;
      if (meshCardiaco) {
        var intensidad = 0.4 + Math.sin(pulsoBPM) * 0.38;
        meshCardiaco.material.emissiveIntensity = Math.max(0.1, intensidad);
      }
      // Pulso suave de la luz puntual
      puntual.intensity = 3.0 + Math.sin(pulsoBPM * 0.5) * 0.5;
    }

    renderer.render(scene, camera);
  }
  animar();

  // ── Resize ────────────────────────────────────────────────────────────────
  function onResize() {
    var w2 = canvas.clientWidth;
    var h2 = canvas.clientHeight;
    if (w2 < 10 || h2 < 10) return;
    camera.aspect = w2 / h2;
    camera.updateProjectionMatrix();
    renderer.setSize(w2, h2);
  }
  window.addEventListener("resize", onResize);

  // ── Hook: physioSetBPM(bpm) ───────────────────────────────────────────────
  window.physioSetBPM = function (bpm) {
    var norm = Math.min(Math.max((bpm - 50) / 160, 0), 1);
    pulsoDelta = 1.5 + norm * 5.0;
    if (meshCardiaco) {
      meshCardiaco.material.emissive.setRGB(1, (114 - norm * 60) / 255, 133 / 255);
      meshCardiaco.material.emissiveIntensity = 0.4 + norm * 0.7;
    }
  };

  // ── Hook: physioSetIMU(pitch, roll) ──────────────────────────────────────
  window.physioSetIMU = function (pitch, roll) {
    var toRad = function (deg) { return deg * Math.PI / 180; };
    if (grupoTorso) {
      grupoTorso.rotation.x = toRad(pitch * 0.5);
      grupoTorso.rotation.z = toRad(roll  * 0.3);
    }
    if (grupoBody) grupoBody.rotation.x = toRad(pitch * 0.18);
  };

  // ── Limpieza cuando el canvas sale del DOM ────────────────────────────────
  if (typeof MutationObserver !== "undefined") {
    var obs = new MutationObserver(function () {
      if (!document.contains(canvas)) {
        cancelAnimationFrame(animFrameId);
        renderer.dispose();
        window.removeEventListener("resize", onResize);
        obs.disconnect();
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

})();
