// Tier 1 — full WebGL2 3D globe (three.js, Section 11.1): custom globe
// renderer with animated correlation threads between linked stories and
// particle-density pulse effects for event clusters. Performance budget
// (Section 11.3): 60fps sustained with up to 500 rendered events, under 4s
// to interactive.
//
// Everything is procedural (sphere + graticule + glow) — no texture assets,
// so first paint isn't blocked on any download.
import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

const GLOBE_RADIUS = 1;
const CATEGORY_COLORS = {
  geopolitics: new THREE.Color('#4da3ff'),
  finance: new THREE.Color('#ffc857'),
  disaster: new THREE.Color('#ff6b57'),
  conflict: new THREE.Color('#ff4d88'),
  other: new THREE.Color('#9aa7bd'),
};

function latLonToVec3(lat, lon, radius = GLOBE_RADIUS) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

function buildGraticule() {
  const group = new THREE.Group();
  const material = new THREE.LineBasicMaterial({ color: 0x1d2b47, transparent: true, opacity: 0.55 });
  for (let lat = -60; lat <= 60; lat += 30) {
    const pts = [];
    for (let lon = -180; lon <= 180; lon += 4) pts.push(latLonToVec3(lat, lon, GLOBE_RADIUS * 1.001));
    group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), material));
  }
  for (let lon = -180; lon < 180; lon += 30) {
    const pts = [];
    for (let lat = -90; lat <= 90; lat += 4) pts.push(latLonToVec3(lat, lon, GLOBE_RADIUS * 1.001));
    group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), material));
  }
  return group;
}

// Pulsing event points: per-point color/size/phase driven by one time uniform.
const POINT_VERTEX = `
  attribute float severity;
  attribute float phase;
  attribute vec3 pointColor;
  uniform float uTime;
  varying vec3 vColor;
  varying float vPulse;
  void main() {
    vColor = pointColor;
    vPulse = 0.6 + 0.4 * sin(uTime * 2.2 + phase);
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = (3.0 + severity * 2.4) * vPulse * (300.0 / -mvPosition.z) / 100.0;
    gl_Position = projectionMatrix * mvPosition;
  }
`;
const POINT_FRAGMENT = `
  varying vec3 vColor;
  varying float vPulse;
  void main() {
    float d = length(gl_PointCoord - vec2(0.5));
    if (d > 0.5) discard;
    float glow = smoothstep(0.5, 0.0, d);
    gl_FragColor = vec4(vColor, glow * vPulse);
  }
`;

// Correlation threads: a bright packet travels along each arc (per-vertex t
// attribute vs time uniform) — the "animated correlation threads" of 11.1.
const ARC_VERTEX = `
  attribute float t;
  varying float vT;
  void main() {
    vT = t;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const ARC_FRAGMENT = `
  uniform float uTime;
  uniform vec3 uColor;
  varying float vT;
  void main() {
    float packet = fract(vT - uTime * 0.25);
    float intensity = 0.18 + 0.82 * smoothstep(0.12, 0.0, packet);
    gl_FragColor = vec4(uColor, intensity);
  }
`;

function buildArc(a, b, color) {
  const start = latLonToVec3(a[1], a[0], GLOBE_RADIUS * 1.005);
  const end = latLonToVec3(b[1], b[0], GLOBE_RADIUS * 1.005);
  const mid = start.clone().add(end).multiplyScalar(0.5);
  const lift = 1 + start.distanceTo(end) * 0.45;
  mid.normalize().multiplyScalar(GLOBE_RADIUS * lift);
  const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
  const points = curve.getPoints(48);

  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const ts = new Float32Array(points.length);
  for (let i = 0; i < points.length; i++) ts[i] = i / (points.length - 1);
  geometry.setAttribute('t', new THREE.BufferAttribute(ts, 1));

  const material = new THREE.ShaderMaterial({
    vertexShader: ARC_VERTEX,
    fragmentShader: ARC_FRAGMENT,
    uniforms: { uTime: { value: 0 }, uColor: { value: color } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  return new THREE.Line(geometry, material);
}

export default function Tier1Globe({ events, stories, onSelectStory }) {
  const mountRef = useRef(null);
  const [fps, setFps] = useState(0);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    const mount = mountRef.current;
    const located = events.filter((e) => Array.isArray(e.location));

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, mount.clientWidth / mount.clientHeight, 0.1, 100);
    camera.position.set(0, 0.4, 3.1);

    const globeGroup = new THREE.Group();
    scene.add(globeGroup);

    globeGroup.add(new THREE.Mesh(
      new THREE.SphereGeometry(GLOBE_RADIUS, 48, 48),
      new THREE.MeshBasicMaterial({ color: 0x0d1424 }),
    ));
    globeGroup.add(buildGraticule());

    // Atmosphere glow: backside rim shader.
    globeGroup.add(new THREE.Mesh(
      new THREE.SphereGeometry(GLOBE_RADIUS * 1.06, 48, 48),
      new THREE.ShaderMaterial({
        vertexShader: `
          varying vec3 vNormal;
          void main() { vNormal = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: `
          varying vec3 vNormal;
          void main() { float rim = pow(0.72 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);
            gl_FragColor = vec4(0.25, 0.5, 1.0, 1.0) * rim; }`,
        side: THREE.BackSide, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false,
      }),
    ));

    // Event points.
    const n = located.length;
    const positions = new Float32Array(n * 3);
    const colors = new Float32Array(n * 3);
    const severities = new Float32Array(n);
    const phases = new Float32Array(n);
    located.forEach((event, i) => {
      const [lon, lat] = event.location;
      const v = latLonToVec3(lat, lon, GLOBE_RADIUS * 1.008);
      positions.set([v.x, v.y, v.z], i * 3);
      const c = CATEGORY_COLORS[event.category] ?? CATEGORY_COLORS.other;
      colors.set([c.r, c.g, c.b], i * 3);
      severities[i] = event.severity ?? 1;
      phases[i] = Math.random() * Math.PI * 2;
    });
    const pointsGeometry = new THREE.BufferGeometry();
    pointsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    pointsGeometry.setAttribute('pointColor', new THREE.BufferAttribute(colors, 3));
    pointsGeometry.setAttribute('severity', new THREE.BufferAttribute(severities, 1));
    pointsGeometry.setAttribute('phase', new THREE.BufferAttribute(phases, 1));
    const pointsMaterial = new THREE.ShaderMaterial({
      vertexShader: POINT_VERTEX, fragmentShader: POINT_FRAGMENT,
      uniforms: { uTime: { value: 0 } },
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    const pointsMesh = new THREE.Points(pointsGeometry, pointsMaterial);
    globeGroup.add(pointsMesh);

    // Correlation threads between each story's member events.
    const eventById = new Map(located.map((e) => [e.id, e]));
    const arcMaterialsUniforms = [];
    (stories ?? []).forEach((story) => {
      const members = (story.member_event_ids ?? [])
        .map((id) => eventById.get(id))
        .filter(Boolean);
      for (let i = 0; i + 1 < members.length; i++) {
        const color = (CATEGORY_COLORS[members[i].category] ?? CATEGORY_COLORS.other).clone().lerp(new THREE.Color('#ffffff'), 0.25);
        const arc = buildArc(members[i].location, members[i + 1].location, color);
        arcMaterialsUniforms.push(arc.material.uniforms);
        globeGroup.add(arc);
      }
    });

    // Drag-to-rotate + wheel zoom + slow idle auto-rotation.
    let dragging = false;
    let lastX = 0; let lastY = 0;
    let idleSince = performance.now();
    const onDown = (e) => { dragging = true; lastX = e.clientX; lastY = e.clientY; };
    const onUp = () => { dragging = false; idleSince = performance.now(); };
    const onMove = (e) => {
      if (dragging) {
        globeGroup.rotation.y += (e.clientX - lastX) * 0.005;
        globeGroup.rotation.x = Math.max(-1.2, Math.min(1.2, globeGroup.rotation.x + (e.clientY - lastY) * 0.005));
        lastX = e.clientX; lastY = e.clientY;
        idleSince = performance.now();
      } else {
        const rect = renderer.domElement.getBoundingClientRect();
        pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        pointerPx.x = e.clientX - rect.left;
        pointerPx.y = e.clientY - rect.top;
        hoverDirty = true;
      }
    };
    const onWheel = (e) => {
      e.preventDefault();
      camera.position.multiplyScalar(1 + Math.sign(e.deltaY) * 0.08);
      camera.position.clampLength(1.6, 6.5);
    };
    const onClick = () => {
      if (hovered != null && onSelectStory) {
        const event = located[hovered];
        const story = (stories ?? []).find((s) => (s.member_event_ids ?? []).includes(event.id));
        if (story) onSelectStory(story.id);
      }
    };
    renderer.domElement.addEventListener('pointerdown', onDown);
    window.addEventListener('pointerup', onUp);
    renderer.domElement.addEventListener('pointermove', onMove);
    renderer.domElement.addEventListener('wheel', onWheel, { passive: false });
    renderer.domElement.addEventListener('click', onClick);

    const raycaster = new THREE.Raycaster();
    raycaster.params.Points.threshold = 0.03;
    const pointer = new THREE.Vector2(-2, -2);
    const pointerPx = new THREE.Vector2();
    let hoverDirty = false;
    let hovered = null;

    const onResize = () => {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener('resize', onResize);

    const clock = new THREE.Clock();
    let frames = 0;
    let fpsWindowStart = performance.now();
    let disposed = false;

    function animate() {
      if (disposed) return;
      requestAnimationFrame(animate);
      const t = clock.getElapsedTime();
      pointsMaterial.uniforms.uTime.value = t;
      arcMaterialsUniforms.forEach((u) => { u.uTime.value = t; });

      if (!dragging && performance.now() - idleSince > 2500) globeGroup.rotation.y += 0.0009;

      if (hoverDirty) {
        hoverDirty = false;
        raycaster.setFromCamera(pointer, camera);
        const hits = raycaster.intersectObject(pointsMesh);
        hovered = hits.length ? hits[0].index : null;
        setTooltip(hovered != null
          ? { x: pointerPx.x, y: pointerPx.y, event: located[hovered] }
          : null);
      }

      renderer.render(scene, camera);

      frames += 1;
      const nowMs = performance.now();
      if (nowMs - fpsWindowStart >= 1000) {
        const measured = Math.round((frames * 1000) / (nowMs - fpsWindowStart));
        setFps(measured);
        window.__globeFps = measured; // exposed for automated perf verification
        frames = 0;
        fpsWindowStart = nowMs;
      }
    }
    animate();
    window.__globeReady = true;

    return () => {
      disposed = true;
      window.removeEventListener('resize', onResize);
      window.removeEventListener('pointerup', onUp);
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [events, stories, onSelectStory]);

  return (
    <div ref={mountRef} style={{ position: 'absolute', inset: 0 }}>
      <div className="fps-meter">{fps} fps · {events.filter((e) => e.location).length} events</div>
      {tooltip && (
        <div className="map-tooltip" style={{ left: tooltip.x + 14, top: tooltip.y + 14 }}>
          <strong>{tooltip.event.title}</strong>
          <div style={{ color: 'var(--text-dim)', marginTop: 2 }}>
            {tooltip.event.location_name} · severity {tooltip.event.severity}
          </div>
        </div>
      )}
    </div>
  );
}
