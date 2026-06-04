/* PhysioScan — Holograma 3D con Three.js r128
   - Carga cuerpo.glb con GLTFLoader; fallback procedural con
     CylinderGeometry + SphereGeometry (NUNCA CapsuleGeometry, es r142+)
   - Material: MeshStandardMaterial emissive cian + wireframe superpuesto
   - Rotación lenta en Y; luz puntual cian; fondo transparente
   - Hooks globales para modo dashboard: physioSetIMU(pitch, roll) y physioSetBPM(bpm)
   - Degradación: sin WebGL → muestra #holograma-fallback
*/
(function () {
  "use strict";

  var canvas = document.getElementById("holograma-canvas");
  if (!canvas) return;

  // ── Detección de WebGL ────────────────────────────────────────────────────
  function webglDisponible() {
    try {
      var probe = document.createElement("canvas");
      return !!(
        probe.getContext("webgl") ||
        probe.getContext("experimental-webgl")
      );
    } catch (e) {
      return false;
    }
  }

  function mostrarFallback() {
    canvas.style.display = "none";
    var fb = document.getElementById("holograma-fallback");
    if (fb) {
      fb.style.display = "flex";
    }
  }

  if (typeof THREE === "undefined" || !webglDisponible()) {
    mostrarFallback();
    return;
  }

  // ── Escena ────────────────────────────────────────────────────────────────
  var scene    = new THREE.Scene();
  var w        = canvas.clientWidth  || 480;
  var h        = canvas.clientHeight || 600;
  var camera   = new THREE.PerspectiveCamera(42, w / h, 0.1, 50);
  camera.position.set(0, 0.6, 3.8);

  var renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    alpha: true,
    antialias: true,
  });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.shadowMap.enabled = false;

  // ── Iluminación ───────────────────────────────────────────────────────────
  var ambient = new THREE.AmbientLight(0x041425, 1.2);
  scene.add(ambient);

  var puntual = new THREE.PointLight(0x79DBFF, 3.0, 14);
  puntual.position.set(2, 3, 2);
  scene.add(puntual);

  var rimLight = new THREE.PointLight(0x19AAFF, 1.0, 10);
  rimLight.position.set(-2, 0, -1);
  scene.add(rimLight);

  // ── Materiales ────────────────────────────────────────────────────────────
  var matSolido = new THREE.MeshStandardMaterial({
    color:             0x020813,
    emissive:          new THREE.Color(0x79DBFF),
    emissiveIntensity: 0.55,
    metalness:         0.2,
    roughness:         0.7,
    transparent:       true,
    opacity:           0.82,
  });

  var matWire = new THREE.MeshBasicMaterial({
    color:       0x79DBFF,
    wireframe:   true,
    transparent: true,
    opacity:     0.22,
  });

  var matCardiaco = new THREE.MeshStandardMaterial({
    color:             0xFF7285,
    emissive:          new THREE.Color(0xFF7285),
    emissiveIntensity: 0.5,
    transparent:       true,
    opacity:           0.9,
  });

  // ── Referencias para hooks ─────────────────────────────────────────────────
  var grupoBody     = null;
  var grupoTorso    = null;
  var meshCardiaco  = null;
  var pulsoBPM      = 0;
  var pulsoDelta    = 2.0;   // rad/s — varía con physioSetBPM

  // ── Función utilitaria: añadir malla + wireframe al grupo ─────────────────
  function addMesh(grupo, geo, mat, pos, rot) {
    var mesh = new THREE.Mesh(geo, mat.clone());
    if (pos) mesh.position.set(pos[0], pos[1], pos[2]);
    if (rot) {
      mesh.rotation.x = rot[0] || 0;
      mesh.rotation.z = rot[2] || 0;
    }
    var wire = new THREE.Mesh(geo, matWire);
    mesh.add(wire);
    grupo.add(mesh);
    return mesh;
  }

  // ── Fallback procedural (r128: CylinderGeometry + SphereGeometry ONLY) ────
  function construirCuerpo() {
    grupoBody  = new THREE.Group();
    grupoTorso = new THREE.Group();

    // Cabeza
    addMesh(grupoBody,
      new THREE.SphereGeometry(0.30, 14, 14),
      matSolido, [0, 1.52, 0]);

    // Cuello
    addMesh(grupoBody,
      new THREE.CylinderGeometry(0.09, 0.11, 0.18, 8),
      matSolido, [0, 1.17, 0]);

    // Torso (dentro del grupoTorso para rotación IMU)
    var torsoGeo  = new THREE.CylinderGeometry(0.26, 0.30, 0.82, 10);
    var torsoMesh = new THREE.Mesh(torsoGeo, matSolido.clone());
    torsoMesh.add(new THREE.Mesh(torsoGeo, matWire));

    // Nodo cardiaco (esfera pequeña en el pecho)
    meshCardiaco = new THREE.Mesh(
      new THREE.SphereGeometry(0.095, 8, 8),
      matCardiaco
    );
    meshCardiaco.position.set(-0.09, 0.14, 0.20);
    torsoMesh.add(meshCardiaco);

    grupoTorso.add(torsoMesh);
    grupoTorso.position.set(0, 0.62, 0);
    grupoBody.add(grupoTorso);

    // Pelvis
    addMesh(grupoBody,
      new THREE.CylinderGeometry(0.28, 0.26, 0.28, 8),
      matSolido, [0, 0.15, 0]);

    // Brazos
    [[-0.40, 0.63, 0, 0, 0.14], [0.40, 0.63, 0, 0, -0.14]].forEach(function (p) {
      addMesh(grupoBody,
        new THREE.CylinderGeometry(0.070, 0.060, 0.68, 7),
        matSolido, [p[0], p[1], p[2]], [0, 0, p[4]]);
    });

    // Antebrazos
    [[-0.43, 0.16, 0, 0, 0.28], [0.43, 0.16, 0, 0, -0.28]].forEach(function (p) {
      addMesh(grupoBody,
        new THREE.CylinderGeometry(0.055, 0.045, 0.56, 7),
        matSolido, [p[0], p[1], p[2]], [0, 0, p[4]]);
    });

    // Muslos
    [[-0.17, -0.38, 0], [0.17, -0.38, 0]].forEach(function (p) {
      addMesh(grupoBody,
        new THREE.CylinderGeometry(0.13, 0.11, 0.68, 8),
        matSolido, p);
    });

    // Pantorrillas
    [[-0.17, -0.88, 0], [0.17, -0.88, 0]].forEach(function (p) {
      addMesh(grupoBody,
        new THREE.CylinderGeometry(0.09, 0.075, 0.62, 8),
        matSolido, p);
    });

    // Pies (cilindro pequeño inclinado)
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

  // ── Intento de carga del modelo GLB ────────────────────────────────────────
  function cargarGLB() {
    if (typeof THREE.GLTFLoader === "undefined") {
      construirCuerpo();
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
            var wire = new THREE.Mesh(child.geometry, matWire);
            child.add(wire);
            // El primer mesh es el torso (heurística simple)
            if (!grupoTorso) {
              grupoTorso = child;
            }
          }
        });

        // Centrar y escalar
        var caja = new THREE.Box3().setFromObject(grupoBody);
        var cen  = caja.getCenter(new THREE.Vector3());
        var tam  = caja.getSize(new THREE.Vector3());
        grupoBody.position.sub(cen);
        var escala = 2.2 / tam.y;
        grupoBody.scale.setScalar(escala);
        scene.add(grupoBody);
      },
      undefined,
      function () {
        // GLB no disponible → fallback procedural
        construirCuerpo();
      }
    );
  }

  cargarGLB();

  // ── Loop de animación ─────────────────────────────────────────────────────
  var tiempoAnterior = performance.now();
  var animFrameId;

  function animar() {
    animFrameId = requestAnimationFrame(animar);
    var ahora = performance.now();
    var dt    = Math.min((ahora - tiempoAnterior) / 1000, 0.05);
    tiempoAnterior = ahora;

    if (grupoBody) {
      grupoBody.rotation.y += 0.004;
    }

    // Pulso del nodo cardiaco
    if (meshCardiaco) {
      pulsoBPM += dt * pulsoDelta;
      var intensidad = 0.4 + Math.sin(pulsoBPM) * 0.38;
      meshCardiaco.material.emissiveIntensity = Math.max(0.1, intensidad);
    }

    // Pulso leve de la luz puntual
    puntual.intensity = 2.8 + Math.sin(pulsoBPM * 0.5) * 0.4;

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

  // ── Hooks para el modo dashboard ──────────────────────────────────────────

  // physioSetIMU(pitch, roll): recibe grados desde el IMU del chaleco
  window.physioSetIMU = function (pitch, roll) {
    if (grupoTorso) {
      grupoTorso.rotation.x = THREE.MathUtils
        ? THREE.MathUtils.degToRad(pitch * 0.5)
        : (pitch * 0.5 * Math.PI) / 180;
      grupoTorso.rotation.z = THREE.MathUtils
        ? THREE.MathUtils.degToRad(roll * 0.3)
        : (roll * 0.3 * Math.PI) / 180;
    }
    if (grupoBody) {
      grupoBody.rotation.x = THREE.MathUtils
        ? THREE.MathUtils.degToRad(pitch * 0.18)
        : (pitch * 0.18 * Math.PI) / 180;
    }
  };

  // physioSetBPM(bpm): ajusta la velocidad y color del pulso cardiaco
  window.physioSetBPM = function (bpm) {
    // BPM normal 60-100; máximo útil ~200
    var norm = Math.min(Math.max((bpm - 50) / 160, 0), 1);
    pulsoDelta = 1.5 + norm * 5.0;  // rad/s; se traduce en latidos por segundo
    if (meshCardiaco) {
      // Más rojo (alerta) a mayor BPM
      var r = Math.round(255);
      var g = Math.round(114 - norm * 60);
      meshCardiaco.material.emissive.setRGB(r / 255, g / 255, 133 / 255);
      meshCardiaco.material.emissiveIntensity = 0.4 + norm * 0.7;
    }
  };

  // ── Limpieza cuando el canvas sale del DOM (SPA) ──────────────────────────
  if (typeof MutationObserver !== "undefined") {
    var observer = new MutationObserver(function () {
      if (!document.contains(canvas)) {
        cancelAnimationFrame(animFrameId);
        renderer.dispose();
        window.removeEventListener("resize", onResize);
        observer.disconnect();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // ── Scroll: revelar elementos con clase .fade-up ──────────────────────────
  if (typeof IntersectionObserver !== "undefined") {
    var ioOpts = { threshold: 0.15 };
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var delay = entry.target.getAttribute("data-delay") || 0;
          setTimeout(function () {
            entry.target.classList.add("visible");
          }, parseInt(delay, 10));
          io.unobserve(entry.target);
        }
      });
    }, ioOpts);
    document.querySelectorAll(".fade-up").forEach(function (el) {
      io.observe(el);
    });
  } else {
    // Sin IntersectionObserver — mostrar todo directamente
    document.querySelectorAll(".fade-up").forEach(function (el) {
      el.classList.add("visible");
    });
  }

})();
