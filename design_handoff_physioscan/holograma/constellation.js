/* ============================================================
   PhysioScan — constellation viewer
   Loads physioscan_constellation.glb (points + lines, no faces),
   renders with PointsMaterial / LineBasicMaterial only, adds
   horizontal scan rings travelling bottom→top and a HUD platform.
   ============================================================ */
(function () {
  const BG = 0x020813, CYAN = 0x79DBFF, ICE = 0xB4F8FF, RING = 0x19AAFF;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const app = document.getElementById('app');
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(BG, 1);
  app.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BG);
  scene.fog = new THREE.FogExp2(BG, 0.14);

  const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 100);
  camera.position.set(0, 0.15, 3.7);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.minDistance = 2.2; controls.maxDistance = 6.5;
  controls.target.set(0, 0.05, 0); controls.enablePan = false;

  // soft circular sprite for glowing nodes
  function dotTexture() {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const x = c.getContext('2d');
    const g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.25, 'rgba(180,248,255,1)');
    g.addColorStop(0.6, 'rgba(121,219,255,0.45)');
    g.addColorStop(1, 'rgba(121,219,255,0)');
    x.fillStyle = g; x.fillRect(0, 0, 64, 64);
    const t = new THREE.CanvasTexture(c); t.needsUpdate = true; return t;
  }
  const sprite = dotTexture();

  const human = new THREE.Group();
  scene.add(human);

  const loader = new THREE.GLTFLoader();
  loader.load('physioscan_constellation.glb', (gltf) => {
    let pts = 0, links = 0;
    gltf.scene.traverse((o) => {
      if (o.isPoints) {
        o.material = new THREE.PointsMaterial({
          color: ICE, size: 0.05, map: sprite, transparent: true,
          alphaTest: 0.02, depthWrite: false, sizeAttenuation: true,
          blending: THREE.AdditiveBlending,
        });
        pts = o.geometry.attributes.position.count;
        human.add(o.clone());
      } else if (o.isLineSegments) {
        o.material = new THREE.LineBasicMaterial({
          color: CYAN, transparent: true, opacity: 0.55, depthWrite: false,
          blending: THREE.AdditiveBlending,
        });
        links = o.geometry.attributes.position.count / 2;
        human.add(o.clone());
      } else if (o.isLineLoop || o.isLine) {
        o.material = new THREE.LineBasicMaterial({
          color: RING, transparent: true, opacity: 0.85, depthWrite: false,
          blending: THREE.AdditiveBlending,
        });
        human.add(o.clone());
      }
    });
    document.getElementById('r-pts').textContent = pts.toLocaleString();
    document.getElementById('r-edges').textContent = links.toLocaleString();
    const l = document.getElementById('loading');
    l.style.transition = 'opacity .6s ease'; l.style.opacity = '0';
    setTimeout(() => l.remove(), 650);
  }, undefined, (err) => {
    document.getElementById('loading').textContent = 'LOAD ERROR';
    console.error(err);
  });

  // ---- HUD platform (glowing disc + concentric rings) ----
  const platform = new THREE.Group();
  platform.position.y = -0.92;
  scene.add(platform);
  [0.46, 0.34, 0.22].forEach((r, i) => {
    const g = new THREE.RingGeometry(r - 0.004, r + 0.004, 96);
    const m = new THREE.MeshBasicMaterial({
      color: RING, transparent: true, opacity: 0.5 - i * 0.12,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const ring = new THREE.Mesh(g, m); ring.rotation.x = -Math.PI / 2;
    platform.add(ring);
  });
  const discGeo = new THREE.CircleGeometry(0.46, 96);
  const discMat = new THREE.MeshBasicMaterial({
    color: 0x0a3a5c, transparent: true, opacity: 0.18,
    side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
  });
  const disc = new THREE.Mesh(discGeo, discMat); disc.rotation.x = -Math.PI / 2;
  platform.add(disc);

  // ---- travelling scan rings (bottom → top, looping) ----
  const BODY_BOTTOM = -0.92, BODY_TOP = 0.92;
  const scanRings = [];
  function bodyRadiusAt(y) {
    // rough silhouette radius for nicer ring fit
    const t = (y - BODY_BOTTOM) / (BODY_TOP - BODY_BOTTOM);
    if (t > 0.78) return 0.16;            // head
    if (t > 0.62) return 0.26;            // shoulders/chest
    if (t > 0.40) return 0.22;            // torso
    if (t > 0.10) return 0.30;            // hips + arms span
    return 0.26;                          // legs
  }
  for (let i = 0; i < 3; i++) {
    const geo = new THREE.RingGeometry(0.001, 0.001, 96);
    const mat = new THREE.MeshBasicMaterial({
      color: RING, transparent: true, opacity: 0.0, side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const r = new THREE.Mesh(geo, mat); r.rotation.x = -Math.PI / 2;
    r.userData.phase = i / 3;
    human.add(r); scanRings.push(r);
  }
  function setRing(mesh, y) {
    const rad = bodyRadiusAt(y);
    mesh.geometry.dispose();
    mesh.geometry = new THREE.RingGeometry(rad - 0.012, rad + 0.012, 96);
    mesh.position.y = y;
  }

  // ---- bloom ----
  let composer = null, bloom = null;
  try {
    composer = new THREE.EffectComposer(renderer);
    composer.addPass(new THREE.RenderPass(scene, camera));
    bloom = new THREE.UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.9, 0.7, 0.05);
    composer.addPass(bloom);
  } catch (e) { composer = null; }

  addEventListener('resize', () => {
    camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
    if (composer) composer.setSize(innerWidth, innerHeight);
    if (bloom) bloom.setSize(innerWidth, innerHeight);
  });

  const clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    if (!reduce) {
      human.rotation.y += 0.005;
      // scan rings sweep upward
      scanRings.forEach((r) => {
        const p = (t * 0.28 + r.userData.phase) % 1;
        const y = BODY_BOTTOM + p * (BODY_TOP - BODY_BOTTOM);
        setRing(r, y);
        const fade = Math.sin(p * Math.PI);            // fade in/out at ends
        r.material.opacity = 0.65 * fade;
      });
      platform.children.forEach((c, i) => { if (c.geometry && c.geometry.type === 'RingGeometry') c.rotation.z = t * (0.15 + i * 0.05); });
    } else {
      // static: park one ring at chest height
      setRing(scanRings[0], 0.35); scanRings[0].material.opacity = 0.5;
    }
    controls.update();
    if (composer) composer.render(); else renderer.render(scene, camera);
  }
  animate();
})();
