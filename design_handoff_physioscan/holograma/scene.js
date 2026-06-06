/* ============================================================
   PhysioScan — scene wiring
   Three.js r128. Holographic HUD render of the procedural
   low-poly humanoid from body-model.js. Also exports the
   geometry as a ready-to-use .glb on demand.
   ============================================================ */
(function () {
  const BG = 0x020813;
  const CYAN = 0x79DBFF;

  // ---- renderer ----
  const app = document.getElementById('app');
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(BG, 1);
  app.appendChild(renderer.domElement);

  // ---- scene + camera ----
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BG);
  scene.fog = new THREE.FogExp2(BG, 0.16);

  const camera = new THREE.PerspectiveCamera(
    38, window.innerWidth / window.innerHeight, 0.1, 100
  );
  camera.position.set(0, 0.15, 3.6);

  // ---- controls ----
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.8;
  controls.minDistance = 2.2;
  controls.maxDistance = 6.0;
  controls.target.set(0, 0.05, 0);
  controls.enablePan = false;

  // ---- lights ----
  scene.add(new THREE.AmbientLight(0x16324a, 1.0));
  const key = new THREE.DirectionalLight(CYAN, 0.9);
  key.position.set(1.5, 2.0, 2.5);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x2a9bd6, 0.7);
  rim.position.set(-2.0, 0.5, -2.0);
  scene.add(rim);
  const fill = new THREE.PointLight(CYAN, 0.5, 12);
  fill.position.set(0, 0.2, 3);
  scene.add(fill);

  // ---- geometry + materials ----
  const geometry = window.buildHumanGeometry();

  const bodyMat = new THREE.MeshStandardMaterial({
    color: 0x020813,
    emissive: CYAN,
    emissiveIntensity: 0.4,
    metalness: 0.1,
    roughness: 0.55,
    transparent: true,
    opacity: 0.92,
  });

  const wireMat = new THREE.MeshBasicMaterial({
    color: CYAN,
    wireframe: true,
    transparent: true,
    opacity: 0.6,
    depthWrite: false,
  });

  const bodyMesh = new THREE.Mesh(geometry, bodyMat);
  const wireMesh = new THREE.Mesh(geometry, wireMat);

  const human = new THREE.Group();
  human.add(bodyMesh);
  human.add(wireMesh);
  scene.add(human);

  // ground reflection-ish grid plane for HUD feel
  const grid = new THREE.GridHelper(6, 24, CYAN, 0x0a2a3a);
  grid.material.transparent = true;
  grid.material.opacity = 0.12;
  grid.position.y = -0.98;
  scene.add(grid);

  // pedestal ring
  const ringGeo = new THREE.RingGeometry(0.55, 0.62, 64);
  const ringMat = new THREE.MeshBasicMaterial({
    color: CYAN, transparent: true, opacity: 0.35, side: THREE.DoubleSide,
  });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = -0.96;
  scene.add(ring);

  // ---- triangle readout ----
  const triCount = (geometry.attributes.position.count / 3) | 0;
  const triEl = document.getElementById('r-tris');
  if (triEl) triEl.textContent = triCount.toLocaleString() + ' tris';

  // ---- post-processing (bloom) ----
  let composer = null, bloomPass = null;
  try {
    composer = new THREE.EffectComposer(renderer);
    composer.addPass(new THREE.RenderPass(scene, camera));
    bloomPass = new THREE.UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight),
      0.85,  // strength
      0.6,   // radius
      0.12   // threshold
    );
    composer.addPass(bloomPass);
  } catch (e) {
    composer = null; // graceful fallback to plain render
  }

  // ---- spin toggle ----
  let spinning = true;
  const btnRotate = document.getElementById('btn-rotate');
  if (btnRotate) {
    btnRotate.addEventListener('click', () => {
      spinning = !spinning;
      btnRotate.textContent = spinning ? 'PAUSE\u00A0SPIN' : 'RESUME\u00A0SPIN';
    });
  }

  // ---- GLB export ----
  const btnExport = document.getElementById('btn-export');
  if (btnExport) {
    btnExport.addEventListener('click', () => {
      const exporter = new THREE.GLTFExporter();
      // export a clean mesh: geometry + simple standard material, no rig
      const exportMesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
        color: 0x020813, emissive: CYAN, emissiveIntensity: 0.4,
        metalness: 0.1, roughness: 0.55,
      }));
      exportMesh.name = 'PhysioScan_Body';
      const oldTxt = btnExport.textContent;
      btnExport.textContent = 'BUILDING…';
      exporter.parse(exportMesh, (glb) => {
        const blob = new Blob([glb], { type: 'model/gltf-binary' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'physioscan_body.glb';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        btnExport.textContent = oldTxt;
      }, { binary: true });
    });
  }

  // ---- resize ----
  window.addEventListener('resize', () => {
    const w = window.innerWidth, h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    if (composer) composer.setSize(w, h);
    if (bloomPass) bloomPass.setSize(w, h);
  });

  // ---- animate ----
  const clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    if (spinning) human.rotation.y += 0.006;
    // subtle hologram float + flicker
    human.position.y = Math.sin(t * 1.1) * 0.01;
    wireMat.opacity = 0.55 + Math.sin(t * 6.0) * 0.05;
    ring.rotation.z += 0.004;
    controls.update();
    if (composer) composer.render();
    else renderer.render(scene, camera);
  }
  animate();

  // ---- hide loader ----
  const loader = document.getElementById('loading');
  if (loader) {
    loader.style.transition = 'opacity .6s ease';
    loader.style.opacity = '0';
    setTimeout(() => loader.remove(), 650);
  }
})();
