/* PhysioScan 3D hologram.
   Uses local three.min.js + GLTFLoader.js loaded by the template.
   Fallback uses CylinderGeometry and SphereGeometry only. */
(function () {
  'use strict';

  var canvas = document.getElementById('holograma-canvas');
  if (!canvas) return;

  var reducedMotion = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  function hasWebGL() {
    try {
      var probe = document.createElement('canvas');
      return !!(probe.getContext('webgl') || probe.getContext('experimental-webgl'));
    } catch (e) {
      return false;
    }
  }

  function showStaticFallback() {
    canvas.style.display = 'none';
    var fallback = document.getElementById('holograma-fallback');
    if (fallback) fallback.style.display = 'flex';
  }

  if (typeof THREE === 'undefined' || !hasWebGL()) {
    showStaticFallback();
    return;
  }

  var CYAN = 0x79DBFF;
  var ICE = 0xB4F8FF;
  var RING = 0x19AAFF;
  var BODY_BOTTOM = -0.92;
  var BODY_TOP = 0.92;

  var width = canvas.clientWidth || 480;
  var height = canvas.clientHeight || 600;

  var scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x020813, 0.10);

  var camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 50);
  camera.position.set(0, 0.15, 3.7);

  var renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    alpha: true,
    antialias: true
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(width, height);
  renderer.setClearColor(0x000000, 0);

  scene.add(new THREE.AmbientLight(0x041425, 1.0));
  var pulseLight = new THREE.PointLight(CYAN, 3.5, 16);
  pulseLight.position.set(2, 3, 2);
  scene.add(pulseLight);
  var rimLight = new THREE.PointLight(RING, 1.2, 10);
  rimLight.position.set(-2, 0, -1);
  scene.add(rimLight);

  function dotTexture() {
    var textureCanvas = document.createElement('canvas');
    textureCanvas.width = 64;
    textureCanvas.height = 64;
    var ctx = textureCanvas.getContext('2d');
    var gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(255,255,255,1)');
    gradient.addColorStop(0.25, 'rgba(180,248,255,1)');
    gradient.addColorStop(0.6, 'rgba(121,219,255,0.45)');
    gradient.addColorStop(1, 'rgba(121,219,255,0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    var texture = new THREE.CanvasTexture(textureCanvas);
    texture.needsUpdate = true;
    return texture;
  }

  var sprite = dotTexture();
  var pointsMaterial = new THREE.PointsMaterial({
    color: ICE,
    size: 0.05,
    map: sprite,
    transparent: true,
    alphaTest: 0.02,
    depthWrite: false,
    sizeAttenuation: true,
    blending: THREE.AdditiveBlending
  });
  var lineMaterial = new THREE.LineBasicMaterial({
    color: CYAN,
    transparent: true,
    opacity: 0.55,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  });
  var ringLineMaterial = new THREE.LineBasicMaterial({
    color: RING,
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  });
  var solidMaterial = new THREE.MeshStandardMaterial({
    color: 0x020813,
    emissive: new THREE.Color(CYAN),
    emissiveIntensity: 0.55,
    metalness: 0.2,
    roughness: 0.7,
    transparent: true,
    opacity: 0.82
  });
  var wireMaterial = new THREE.MeshBasicMaterial({
    color: CYAN,
    wireframe: true,
    transparent: true,
    opacity: 0.18
  });
  var heartMaterial = new THREE.MeshStandardMaterial({
    color: 0xFF7285,
    emissive: new THREE.Color(0xFF7285),
    emissiveIntensity: 0.6,
    transparent: true,
    opacity: 0.9
  });

  var human = null;
  var torso = null;
  var heart = null;
  var pulse = 0;
  var pulseSpeed = 2.0;
  var scanRings = [];

  function bodyRadiusAt(y) {
    var t = (y - BODY_BOTTOM) / (BODY_TOP - BODY_BOTTOM);
    if (t > 0.78) return 0.16;
    if (t > 0.62) return 0.26;
    if (t > 0.40) return 0.22;
    if (t > 0.10) return 0.30;
    return 0.26;
  }

  function setRing(mesh, y) {
    var radius = bodyRadiusAt(y);
    mesh.geometry.dispose();
    mesh.geometry = new THREE.RingGeometry(radius - 0.012, radius + 0.012, 96);
    mesh.position.y = y;
  }

  function makeScanRing(index) {
    var material = new THREE.MeshBasicMaterial({
      color: RING,
      transparent: true,
      opacity: 0,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    var ring = new THREE.Mesh(new THREE.RingGeometry(0.001, 0.001, 96), material);
    ring.rotation.x = -Math.PI / 2;
    ring.userData.phase = index / 3;
    scanRings.push(ring);
    return ring;
  }

  var platform = new THREE.Group();
  platform.position.y = BODY_BOTTOM;
  scene.add(platform);

  [0.46, 0.34, 0.22].forEach(function (radius, index) {
    var geometry = new THREE.RingGeometry(radius - 0.004, radius + 0.004, 96);
    var material = new THREE.MeshBasicMaterial({
      color: RING,
      transparent: true,
      opacity: 0.5 - index * 0.12,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    var ring = new THREE.Mesh(geometry, material);
    ring.rotation.x = -Math.PI / 2;
    platform.add(ring);
  });

  var platformDisc = new THREE.Mesh(
    new THREE.CircleGeometry(0.46, 96),
    new THREE.MeshBasicMaterial({
      color: 0x0a3a5c,
      transparent: true,
      opacity: 0.18,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  );
  platformDisc.rotation.x = -Math.PI / 2;
  platform.add(platformDisc);

  (function addBackgroundParticles() {
    var count = 90;
    var positions = new Float32Array(count * 3);
    for (var i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 5;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 5.5;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 2.5 - 1;
    }
    var geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    scene.add(new THREE.Points(geometry, new THREE.PointsMaterial({
      color: CYAN,
      size: 0.018,
      transparent: true,
      opacity: 0.3,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })));
  })();

  function addMesh(group, geometry, material, x, y, z, rotZ) {
    var mesh = new THREE.Mesh(geometry, material.clone());
    mesh.position.set(x || 0, y || 0, z || 0);
    if (rotZ) mesh.rotation.z = rotZ;
    mesh.add(new THREE.Mesh(geometry, wireMaterial));
    group.add(mesh);
    return mesh;
  }

  function finishHuman() {
    scanRings = [];
    for (var i = 0; i < 3; i++) human.add(makeScanRing(i));
    scene.add(human);
  }

  function buildProceduralFallback() {
    human = new THREE.Group();
    torso = new THREE.Group();

    addMesh(human, new THREE.SphereGeometry(0.30, 14, 14), solidMaterial, 0, 1.52, 0);
    addMesh(human, new THREE.CylinderGeometry(0.09, 0.11, 0.18, 8), solidMaterial, 0, 1.17, 0);

    var torsoGeometry = new THREE.CylinderGeometry(0.26, 0.30, 0.82, 10);
    var torsoMesh = new THREE.Mesh(torsoGeometry, solidMaterial.clone());
    torsoMesh.add(new THREE.Mesh(torsoGeometry, wireMaterial));
    heart = new THREE.Mesh(new THREE.SphereGeometry(0.095, 8, 8), heartMaterial);
    heart.position.set(-0.09, 0.14, 0.20);
    torsoMesh.add(heart);
    torso.add(torsoMesh);
    torso.position.set(0, 0.62, 0);
    human.add(torso);

    addMesh(human, new THREE.CylinderGeometry(0.28, 0.26, 0.28, 8), solidMaterial, 0, 0.15, 0);
    addMesh(human, new THREE.CylinderGeometry(0.070, 0.060, 0.68, 7), solidMaterial, -0.40, 0.63, 0, 0.14);
    addMesh(human, new THREE.CylinderGeometry(0.070, 0.060, 0.68, 7), solidMaterial, 0.40, 0.63, 0, -0.14);
    addMesh(human, new THREE.CylinderGeometry(0.055, 0.045, 0.56, 7), solidMaterial, -0.43, 0.16, 0, 0.28);
    addMesh(human, new THREE.CylinderGeometry(0.055, 0.045, 0.56, 7), solidMaterial, 0.43, 0.16, 0, -0.28);
    addMesh(human, new THREE.CylinderGeometry(0.13, 0.11, 0.68, 8), solidMaterial, -0.17, -0.38, 0);
    addMesh(human, new THREE.CylinderGeometry(0.13, 0.11, 0.68, 8), solidMaterial, 0.17, -0.38, 0);
    addMesh(human, new THREE.CylinderGeometry(0.09, 0.075, 0.62, 8), solidMaterial, -0.17, -0.88, 0);
    addMesh(human, new THREE.CylinderGeometry(0.09, 0.075, 0.62, 8), solidMaterial, 0.17, -0.88, 0);

    addMesh(human, new THREE.CylinderGeometry(0.055, 0.07, 0.09, 7), solidMaterial, -0.17, -1.26, 0.05).rotation.x = 0.45;
    addMesh(human, new THREE.CylinderGeometry(0.055, 0.07, 0.09, 7), solidMaterial, 0.17, -1.26, 0.05).rotation.x = 0.45;

    finishHuman();
  }

  function loadModel() {
    if (typeof THREE.GLTFLoader === 'undefined') {
      buildProceduralFallback();
      return;
    }

    var modelUrl = canvas.dataset.model || '/static/models/cuerpo.glb';
    var loader = new THREE.GLTFLoader();
    loader.load(modelUrl, function (gltf) {
      human = new THREE.Group();
      gltf.scene.traverse(function (object) {
        var clone;
        if (object.isPoints) {
          clone = object.clone();
          clone.material = pointsMaterial.clone();
          human.add(clone);
        } else if (object.isLineSegments) {
          clone = object.clone();
          clone.material = lineMaterial.clone();
          human.add(clone);
        } else if (object.isLineLoop || object.isLine) {
          clone = object.clone();
          clone.material = ringLineMaterial.clone();
          human.add(clone);
        } else if (object.isMesh) {
          clone = object.clone();
          clone.material = solidMaterial.clone();
          clone.add(new THREE.Mesh(clone.geometry, wireMaterial));
          if (!torso) torso = clone;
          human.add(clone);
        }
      });

      if (!human.children.length) {
        buildProceduralFallback();
        return;
      }

      var box = new THREE.Box3().setFromObject(human);
      var center = box.getCenter(new THREE.Vector3());
      var size = box.getSize(new THREE.Vector3());
      human.position.sub(center);
      if (size.y > 0) human.scale.setScalar(1.84 / size.y);
      finishHuman();
    }, undefined, function () {
      buildProceduralFallback();
    });
  }

  loadModel();

  var lastTime = performance.now();
  var elapsed = 0;
  var animationId = null;

  function animate() {
    animationId = requestAnimationFrame(animate);
    var now = performance.now();
    var dt = Math.min((now - lastTime) / 1000, 0.05);
    lastTime = now;
    elapsed += dt;

    if (!reducedMotion) {
      if (human) human.rotation.y += 0.005;
      scanRings.forEach(function (ring) {
        var p = (elapsed * 0.28 + ring.userData.phase) % 1;
        var y = BODY_BOTTOM + p * (BODY_TOP - BODY_BOTTOM);
        setRing(ring, y);
        ring.material.opacity = 0.65 * Math.sin(p * Math.PI);
      });
      platform.children.forEach(function (child, index) {
        if (child.geometry && child.geometry.type === 'RingGeometry') {
          child.rotation.z = elapsed * (0.15 + index * 0.05);
        }
      });
      pulse += dt * pulseSpeed;
      if (heart) {
        heart.material.emissiveIntensity = Math.max(0.1, 0.4 + Math.sin(pulse) * 0.38);
      }
      pulseLight.intensity = 3.0 + Math.sin(pulse * 0.5) * 0.5;
    } else if (scanRings[0]) {
      setRing(scanRings[0], 0.35);
      scanRings[0].material.opacity = 0.5;
    }

    renderer.render(scene, camera);
  }

  animate();

  function resize() {
    var nextWidth = canvas.clientWidth;
    var nextHeight = canvas.clientHeight;
    if (nextWidth < 10 || nextHeight < 10) return;
    camera.aspect = nextWidth / nextHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(nextWidth, nextHeight);
  }

  window.addEventListener('resize', resize);

  window.physioSetBPM = function (bpm) {
    var norm = Math.min(Math.max((Number(bpm) - 50) / 160, 0), 1);
    pulseSpeed = 1.5 + norm * 5.0;
    if (heart) {
      heart.material.emissive.setRGB(1, (114 - norm * 60) / 255, 133 / 255);
      heart.material.emissiveIntensity = 0.4 + norm * 0.7;
    }
  };

  window.physioSetIMU = function (pitch, roll) {
    var toRad = function (degrees) { return Number(degrees || 0) * Math.PI / 180; };
    if (torso) {
      torso.rotation.x = toRad(pitch) * 0.5;
      torso.rotation.z = toRad(roll) * 0.3;
    }
    if (human) human.rotation.x = toRad(pitch) * 0.18;
  };

  if (typeof MutationObserver !== 'undefined') {
    var observer = new MutationObserver(function () {
      if (!document.contains(canvas)) {
        cancelAnimationFrame(animationId);
        renderer.dispose();
        sprite.dispose();
        window.removeEventListener('resize', resize);
        observer.disconnect();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();
