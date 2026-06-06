/* ============================================================
   PhysioScan — procedural low-poly humanoid
   Male, anatomical position. Centered at origin, ~1.8u tall,
   facing +Z. Returns a single merged BufferGeometry.
   ============================================================ */
(function () {
  const V = THREE.Vector3;

  // tapered cylinder segment between two points (axis baked in)
  function limb(p0, p1, r0, r1, seg) {
    seg = seg || 8;
    const dir = new V().subVectors(p1, p0);
    const len = dir.length();
    const g = new THREE.CylinderGeometry(r1, r0, len, seg, 1, false);
    g.translate(0, len / 2, 0); // base (r0) at local origin, tip (r1) at +len
    const quat = new THREE.Quaternion()
      .setFromUnitVectors(new V(0, 1, 0), dir.clone().normalize());
    const m = new THREE.Matrix4().makeRotationFromQuaternion(quat);
    m.setPosition(p0.x, p0.y, p0.z);
    g.applyMatrix4(m);
    return g.toNonIndexed();
  }

  // rounded volume (scaled icosahedron) — for head/torso/joints/feet
  function blob(cx, cy, cz, rx, ry, rz, detail) {
    const g = new THREE.IcosahedronGeometry(1, detail == null ? 1 : detail);
    g.scale(rx, ry, rz);
    g.translate(cx, cy, cz);
    return g.toNonIndexed();
  }

  function p(x, y, z) { return new V(x, y, z); }

  function buildHumanGeometry() {
    const parts = [];

    /* ---- head + neck ---- */
    parts.push(blob(0, 0.80, 0, 0.115, 0.140, 0.118, 1));          // skull
    parts.push(blob(0, 0.70, 0.02, 0.078, 0.060, 0.078, 1));        // jaw/chin mass
    parts.push(limb(p(0, 0.615, 0), p(0, 0.70, 0), 0.052, 0.046, 8)); // neck

    /* ---- torso (chest → abdomen → pelvis) ---- */
    parts.push(blob(0, 0.500, 0.005, 0.190, 0.135, 0.115, 1));      // chest (broad)
    parts.push(blob(0, 0.330, 0.000, 0.158, 0.120, 0.100, 1));      // abdomen (less pinch)
    parts.push(blob(0, 0.150, 0.000, 0.150, 0.110, 0.105, 1));      // pelvis (narrower)

    /* ---- shoulders (wide, male) ---- */
    parts.push(blob(0.205, 0.560, 0, 0.078, 0.074, 0.076, 1));
    parts.push(blob(-0.205, 0.560, 0, 0.078, 0.074, 0.076, 1));

    /* ---- arms (anatomical: slightly abducted, ~12°) ---- */
    function arm(s) { // s = +1 right, -1 left
      const sh = p(0.215 * s, 0.560, 0);
      const el = p(0.285 * s, 0.270, 0.015);
      const wr = p(0.320 * s, 0.000, 0.030);
      parts.push(limb(sh, el, 0.058, 0.046, 8));   // upper arm
      parts.push(limb(el, wr, 0.046, 0.034, 8));   // forearm
      parts.push(blob(0.325 * s, -0.055, 0.032, 0.046, 0.060, 0.030, 1)); // hand
    }
    arm(1); arm(-1);

    /* ---- legs ---- */
    function leg(s) {
      const hip = p(0.090 * s, 0.060, 0);
      const knee = p(0.100 * s, -0.420, 0.010);
      const ankle = p(0.100 * s, -0.825, -0.020);
      parts.push(blob(0.092 * s, 0.060, 0, 0.080, 0.075, 0.080, 1)); // hip joint
      parts.push(limb(hip, knee, 0.090, 0.060, 8));   // thigh
      parts.push(blob(0.100 * s, -0.420, 0.010, 0.058, 0.058, 0.058, 1)); // knee
      parts.push(limb(knee, ankle, 0.062, 0.040, 8)); // calf
      parts.push(blob(0.100 * s, -0.870, 0.045, 0.050, 0.034, 0.105, 1)); // foot
    }
    leg(1); leg(-1);

    /* ---- merge ---- */
    let geo = THREE.BufferGeometryUtils.mergeBufferGeometries(parts, false);

    // normalize: exact height 1.8, centered at origin, facing +Z
    geo.computeBoundingBox();
    const bb = geo.boundingBox;
    const h = bb.max.y - bb.min.y;
    const s = 1.8 / h;
    geo.scale(s, s, s);
    geo.computeBoundingBox();
    const c = new V();
    geo.boundingBox.getCenter(c);
    geo.translate(-c.x, -c.y, -c.z);

    geo.computeVertexNormals();
    return geo;
  }

  window.buildHumanGeometry = buildHumanGeometry;
})();
