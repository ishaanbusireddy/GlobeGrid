// Tier 1 — full 3D globe (v1 Section 11.1 + v2 addendum Section 5).
//
// Self-contained WebGL2 renderer, zero dependencies. v2 layers, gated by
// quality tier (standard / high / ultra — §5.1):
//   all tiers:  day/night terminator + city lights (real UTC subsolar
//               point), burst animation on live event/story WS messages,
//               heatmap density overlay toggle, fly-to camera tween,
//               idle tour mode, uncorrelated-vs-correlated pin states
//   high+:      starfield, atmosphere fresnel halo, particle trails on
//               correlation threads, ghost trail (fading 24-72h history)
//   ultra:      bloom post-processing (bright-pass + separable gaussian
//               blur, additively composited)
import { COASTLINES } from "../../data/worldCoastline.js";
import { CITY_LIGHTS } from "../../data/cityLights.js";
// v4 §2.3 — Natural Earth boundary LOD: 50m for the full-globe view, 10m
// decoded lazily on first zoom-in (accurate coastlines where they matter)
import { BOUNDARIES_50M_ENC } from "../../data/boundaries50m.js";
import { DISPUTED_BOUNDARIES_ENC } from "../../data/disputedBoundaries.js";
import { decodeBoundaries } from "../../data/boundaryCodec.js";

const CATEGORY_COLORS = {
  geopolitics: [0.30, 0.64, 1.00],
  finance: [1.00, 0.82, 0.40],
  disaster: [1.00, 0.42, 0.42],
  conflict: [1.00, 0.55, 0.26],
  military: [0.29, 0.80, 0.45],   // v6.1 — military developments, green
  other: [0.58, 0.63, 0.72],
};

// ---------- shaders ----------

// Coastlines/graticule sit on a shell slightly larger than the sphere, so
// depth-testing alone can't stop far-hemisphere lines poking past the
// silhouette (the "see-through globe" bug). The vertex shader computes
// whether each point faces the camera (rotated normal's view-space Z) and
// the fragment shader discards anything on the back hemisphere — a hard
// guarantee independent of tessellation or depth precision.
const VERT_LINE = `#version 300 es
layout(location=0) in vec3 pos;
uniform mat4 mvp;
uniform mat4 model;
out float vFacing;
void main() {
  vFacing = (mat3(model) * normalize(pos)).z;
  gl_Position = mvp * vec4(pos, 1.0);
}`;

const FRAG_LINE = `#version 300 es
precision mediump float;
in float vFacing;
uniform vec4 color;
out vec4 frag;
void main() {
  if (vFacing < -0.02) discard;          // back hemisphere — never show through
  float edge = smoothstep(-0.02, 0.10, vFacing);  // fade in at the limb
  frag = vec4(color.rgb, color.a * edge);
}`;

const VERT_SPHERE = `#version 300 es
layout(location=0) in vec3 pos;
uniform mat4 mvp;
uniform mat4 model;
out vec3 vNormal;
out vec3 vPos;
void main() {
  vNormal = mat3(model) * pos;
  vPos = pos;
  gl_Position = mvp * vec4(pos, 1.0);
}`;

// Day/night terminator (§5.1): sun direction from real UTC subsolar point.
// Heatmap overlay (optional, toggled) sampled from an equirect texture.
const FRAG_SPHERE = `#version 300 es
precision highp float;
in vec3 vNormal;
in vec3 vPos;
uniform vec3 sunDir;
uniform sampler2D heatTex;
uniform sampler2D biomeTex;  // v6 §19 — baked biome/elevation texture
uniform float useHeat;
uniform float terrain;   // v5 §8 — 0..1 terrain-detail strength (LOD-gated)
uniform float biomeReady;
uniform vec3 uOcean;     // v6.2 — theme-driven ocean tint (multiplies base blue)
uniform vec3 uRim;       // v6.2 — theme-driven atmosphere/limb colour
out vec4 frag;
void main() {
  vec3 n = normalize(vPos);
  float day = smoothstep(-0.12, 0.18, dot(n, sunDir));
  vec3 nightCol = vec3(0.028, 0.042, 0.078) * uOcean;
  vec3 dayCol = vec3(0.070, 0.108, 0.180) * uOcean;
  float rim = pow(1.0 - abs(normalize(vNormal).z), 2.5);
  vec3 col = mix(nightCol, dayCol, day) + uRim * rim * 0.45;
  // v6 §19 — real biome/elevation texture (baked from vendored Natural Earth
  // land + latitude-banded biome palette, scripts/build_biome_texture.py),
  // properly sampled in the globe's equirect UV space — replaces the v5
  // procedural noise. The FACING term is the v4 §2.1-family occlusion fix
  // applied to the terrain pass: shading only ever applies to the hemisphere
  // actually facing the camera, so terrain can never read through the globe
  // at the silhouette.
  if (terrain > 0.01 && biomeReady > 0.5) {
    float facing = smoothstep(0.0, 0.18, normalize(vNormal).z);
    // v6.1.1 fix — the biome texture's origin is lon=-180 at x=0, i.e.
    // u = (lon+180)/360 = atan2(z,-x)/2pi (see the screenToLatLon inverse).
    // The old "+ 0.5" was copy-pasted from the heatmap UV (different origin)
    // and shifted terrain 180deg, so North-America-shaped land rendered over
    // Asia. REPEAT wrap handles the negative half.
    float u = atan(n.z, -n.x) / 6.2831853;
    float v = 1.0 - (asin(clamp(n.y, -1.0, 1.0)) / 3.14159265 + 0.5);
    vec3 biome = texture(biomeTex, vec2(u, v)).rgb;
    col = mix(col, biome * (0.30 + 0.80 * day)
                   + vec3(0.16, 0.38, 0.80) * rim * 0.25,
              terrain * facing);
  }
  if (useHeat > 0.5) {
    float u = atan(n.z, -n.x) / 6.2831853 + 0.5;
    float v = 1.0 - (asin(clamp(n.y, -1.0, 1.0)) / 3.14159265 + 0.5);
    float h = texture(heatTex, vec2(u, v)).r;
    col += vec3(1.0, 0.45, 0.15) * h * 0.85;
  }
  frag = vec4(col, 1.0);
}`;

const VERT_POINT = `#version 300 es
layout(location=0) in vec3 pos;
layout(location=1) in vec3 color;
layout(location=2) in float size;
layout(location=3) in float phase;
layout(location=4) in float bright;
uniform mat4 mvp;
uniform float time;
uniform float dpr;
out vec3 vColor;
out float vPulse;
void main() {
  gl_Position = mvp * vec4(pos, 1.0);
  float pulse = (0.75 + 0.25 * sin(time * 2.2 + phase * 6.2831)) * bright;
  vPulse = pulse;
  vColor = color;
  // v5 §16 — clamp point size so extreme zoom-in can't balloon the sprite
  // into a low-res blur ("glitched PS2 texture"). The SDF fragment shader
  // keeps the edge crisp at whatever size survives this clamp.
  float ps = size * (0.55 + 0.45 * bright) * dpr * (140.0 / gl_Position.w) * 0.055;
  gl_PointSize = clamp(ps, 2.0, 64.0 * dpr);
}`;

// v5 §16 — resolution-independent signed-distance-field beacon: the glow
// falloff is computed in normalized sprite space and anti-aliased with
// fwidth() (screen-space derivative), so the edge is pixel-crisp at ANY
// gl_PointSize instead of relying on a fixed-resolution texture that
// pixelates when scaled up. highp for clean distance math.
const FRAG_POINT = `#version 300 es
precision highp float;
in vec3 vColor;
in float vPulse;
out vec4 frag;
void main() {
  vec2 d = gl_PointCoord - 0.5;
  float r = length(d) * 2.0;              // 0 at center, 1 at sprite edge
  // solid core: SDF edge anti-aliased by the pixel-space derivative of r,
  // so it stays a crisp disc whether the sprite is 4px or 64px
  float aa = fwidth(r) * 1.5 + 1e-4;
  float core = 1.0 - smoothstep(0.42 - aa, 0.42 + aa, r);
  // screen-space glow falloff (decoupled from world/camera distance, §16):
  // a smooth radial halo out to the sprite edge, independent of zoom
  float halo = pow(1.0 - clamp(r, 0.0, 1.0), 2.2) * 0.55;
  float a = (core + halo * (1.0 - core)) * vPulse;
  if (a < 0.003) discard;
  frag = vec4(vColor + core * 0.15, a);
}`;

// City lights: alpha rises on the night side only (§5.1).
const VERT_CITY = `#version 300 es
layout(location=0) in vec3 pos;
layout(location=1) in float bright;
uniform mat4 mvp;
uniform mat4 model;
uniform vec3 sunDir;
uniform float dpr;
out float vAlpha;
void main() {
  gl_Position = mvp * vec4(pos, 1.0);
  vec3 n = normalize(pos);
  float night = 1.0 - smoothstep(-0.16, 0.06, dot(n, sunDir));
  // camera-facing test — hide far-hemisphere lights so they don't bleed
  // through the globe (same guarantee as the coastlines)
  float facing = (mat3(model) * n).z;
  vAlpha = night * bright * smoothstep(-0.02, 0.12, facing);
  gl_PointSize = (1.0 + bright * 3.0) * dpr * (140.0 / gl_Position.w) * 0.02;
}`;

const FRAG_CITY = `#version 300 es
precision mediump float;
in float vAlpha;
out vec4 frag;
void main() {
  vec2 d = gl_PointCoord - 0.5;
  float r = length(d) * 2.0;
  if (r > 1.0) discard;
  frag = vec4(1.0, 0.85, 0.55, smoothstep(1.0, 0.0, r) * vAlpha * 0.85);
}`;

const VERT_ARC = `#version 300 es
layout(location=0) in vec3 pos;
layout(location=1) in float t;
uniform mat4 mvp;
out float vT;
void main() { vT = t; gl_Position = mvp * vec4(pos, 1.0); }`;

const FRAG_ARC = `#version 300 es
precision mediump float;
in float vT;
uniform float time;
out vec4 frag;
void main() {
  float head = fract(time * 0.25);
  float d = abs(vT - head);
  d = min(d, 1.0 - d);
  float travel = smoothstep(0.18, 0.0, d);
  frag = vec4(0.62, 0.55, 0.95, 0.16 + travel * 0.85);
}`;

// Particle trails (§5.1, high+): additive sprites flowing along the arcs.
const VERT_TRAIL = `#version 300 es
layout(location=0) in vec3 pos;
layout(location=1) in float t;
uniform mat4 mvp;
uniform float time;
uniform float dpr;
out float vA;
void main() {
  gl_Position = mvp * vec4(pos, 1.0);
  float head = fract(time * 0.25);
  float d = head - t;
  d = d < 0.0 ? d + 1.0 : d;
  vA = smoothstep(0.22, 0.0, d) * 0.55;  // age-based fade behind the head
  gl_PointSize = (1.4 + vA * 4.0) * dpr * (140.0 / gl_Position.w) * 0.05;
}`;

const FRAG_TRAIL = `#version 300 es
precision mediump float;
in float vA;
out vec4 frag;
void main() {
  vec2 d = gl_PointCoord - 0.5;
  float r = length(d) * 2.0;
  if (r > 1.0) discard;
  frag = vec4(0.72, 0.62, 1.0, smoothstep(1.0, 0.0, r) * vA * 0.9);
}`;

// Atmosphere fresnel halo (§5.1, high+): enlarged shell, front faces culled.
const FRAG_HALO = `#version 300 es
precision mediump float;
in vec3 vNormal;
in vec3 vPos;
out vec4 frag;
void main() {
  // tighter power + lower alpha = a clean thin atmosphere rim at the
  // silhouette rather than a broad flat blue wash across the disc
  float f = pow(1.0 - abs(normalize(vNormal).z), 4.5);
  frag = vec4(0.30, 0.55, 1.0, f * 0.42);
}`;

// Burst animation (§5.1): radial scale+fade rings on live WS messages.
const VERT_BURST = `#version 300 es
layout(location=0) in vec3 pos;
layout(location=1) in float start;
layout(location=2) in vec3 color;
uniform mat4 mvp;
uniform float time;
uniform float dpr;
out vec3 vColor;
out float vAge;
void main() {
  gl_Position = mvp * vec4(pos, 1.0);
  vAge = clamp((time - start) / 1.6, 0.0, 1.0);
  vColor = color;
  gl_PointSize = (6.0 + vAge * 90.0) * dpr * (140.0 / gl_Position.w) * 0.055;
}`;

const FRAG_BURST = `#version 300 es
precision mediump float;
in vec3 vColor;
in float vAge;
out vec4 frag;
void main() {
  vec2 d = gl_PointCoord - 0.5;
  float r = length(d) * 2.0;
  if (r > 1.0 || vAge >= 1.0) discard;
  float ring = smoothstep(0.25, 0.0, abs(r - vAge * 0.9));
  frag = vec4(vColor, ring * (1.0 - vAge));
}`;

// Volumetric light pillars (ultra): a camera-facing billboard quad rising
// radially from each significant event. The base is anchored to the
// surface point; the quad tapers and fades toward the tip; back-hemisphere
// beams are discarded. With the bloom pass these read as glowing beacons.
const VERT_BEAM = `#version 300 es
layout(location=0) in vec3 base;
layout(location=1) in vec3 axis;
layout(location=2) in vec3 color;
layout(location=3) in float side;
layout(location=4) in float t;
layout(location=5) in float height;
uniform mat4 mvp;
uniform mat4 model;
uniform vec3 camPosModel;
uniform float halfWidth;
out vec3 vColor;
out float vT;
out float vFacing;
void main() {
  vFacing = (mat3(model) * axis).z;
  vec3 viewDir = normalize(camPosModel - base);
  vec3 sideDir = normalize(cross(axis, viewDir));
  vec3 p = base + axis * (t * height) + sideDir * (side * halfWidth * (1.0 - t * 0.7));
  vColor = color;
  vT = t;
  gl_Position = mvp * vec4(p, 1.0);
}`;

const FRAG_BEAM = `#version 300 es
precision mediump float;
in vec3 vColor;
in float vT;
in float vFacing;
uniform float pulse;
out vec4 frag;
void main() {
  if (vFacing < -0.05) discard;
  float fade = (1.0 - vT) * (1.0 - vT);
  float a = fade * 0.55 * pulse * smoothstep(-0.05, 0.15, vFacing);
  frag = vec4(vColor, a);
}`;

// Bloom (§5.1, ultra): bright-pass + separable gaussian blur, additive.
const VERT_QUAD = `#version 300 es
layout(location=0) in vec2 pos;
out vec2 vUv;
void main() { vUv = pos * 0.5 + 0.5; gl_Position = vec4(pos, 0.0, 1.0); }`;

const FRAG_BRIGHT = `#version 300 es
precision mediump float;
in vec2 vUv;
uniform sampler2D tex;
out vec4 frag;
void main() {
  vec3 c = texture(tex, vUv).rgb;
  float lum = dot(c, vec3(0.299, 0.587, 0.114));
  frag = vec4(c * smoothstep(0.32, 0.6, lum), 1.0);
}`;

const FRAG_BLUR = `#version 300 es
precision mediump float;
in vec2 vUv;
uniform sampler2D tex;
uniform vec2 dir;
out vec4 frag;
void main() {
  vec3 sum = texture(tex, vUv).rgb * 0.227;
  vec2 o1 = dir * 1.3846, o2 = dir * 3.2307;
  sum += (texture(tex, vUv + o1).rgb + texture(tex, vUv - o1).rgb) * 0.316;
  sum += (texture(tex, vUv + o2).rgb + texture(tex, vUv - o2).rgb) * 0.070;
  frag = vec4(sum, 1.0);
}`;

const FRAG_COMPOSITE = `#version 300 es
precision mediump float;
in vec2 vUv;
uniform sampler2D tex;
out vec4 frag;
void main() { frag = vec4(texture(tex, vUv).rgb, 1.0); }`;

// ---------- math ----------

function mat4Multiply(a, b) {
  const out = new Float32Array(16);
  for (let c = 0; c < 4; c++)
    for (let r = 0; r < 4; r++) {
      let s = 0;
      for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
      out[c * 4 + r] = s;
    }
  return out;
}
function mat4Perspective(fovY, aspect, near, far) {
  const f = 1 / Math.tan(fovY / 2);
  const out = new Float32Array(16);
  out[0] = f / aspect; out[5] = f;
  out[10] = (far + near) / (near - far); out[11] = -1;
  out[14] = (2 * far * near) / (near - far);
  return out;
}
function mat4RotY(a) {
  const c = Math.cos(a), s = Math.sin(a);
  return new Float32Array([c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]);
}
function mat4RotX(a) {
  const c = Math.cos(a), s = Math.sin(a);
  return new Float32Array([1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]);
}
function mat4Translate(x, y, z) {
  return new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1]);
}
const easeInOut = (t) => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

export function latLonToVec3(lat, lon, radius = 1) {
  const phi = (90 - lat) * Math.PI / 180;
  const theta = (lon + 180) * Math.PI / 180;
  return [
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  ];
}

// Subsolar point from real UTC (§5.1 day/night terminator).
function sunDirection(date = new Date()) {
  const dayOfYear = (Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())
    - Date.UTC(date.getUTCFullYear(), 0, 0)) / 86400000;
  const decl = -23.44 * Math.cos((2 * Math.PI / 365) * (dayOfYear + 10));
  const utcHours = date.getUTCHours() + date.getUTCMinutes() / 60;
  const subsolarLon = (12 - utcHours) * 15;
  return latLonToVec3(decl, subsolarLon, 1);
}

function compile(gl, vsSrc, fsSrc) {
  const mk = (type, src) => {
    const sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS))
      throw new Error(gl.getShaderInfoLog(sh));
    return sh;
  };
  const prog = gl.createProgram();
  gl.attachShader(prog, mk(gl.VERTEX_SHADER, vsSrc));
  gl.attachShader(prog, mk(gl.FRAGMENT_SHADER, fsSrc));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS))
    throw new Error(gl.getProgramInfoLog(prog));
  return prog;
}

// ---------- renderer ----------

export class Tier1Globe {
  constructor(host, { onSelectEvent, onSelectLocation, onCountryClick, onSelectActor,
                      onSelectCluster,
                      quality = "high", idleTourSeconds = 45,
                      clusterScreenDistancePx = 40,       // v4 §2.2
                      facingOcclusion = true,             // v4 §2.1
                      minConfidenceSolid = 0.6,           // v4 §3.1
                      lodCalibration = 1 } = {}) {        // v4 §15.4
    this.host = host;
    this.onSelectEvent = onSelectEvent || (() => {});
    this.onSelectLocation = onSelectLocation || (() => {});   // v3 §17 markers
    this.onCountryClick = onCountryClick || (() => {});       // v3 §13.3
    this.onSelectActor = onSelectActor || (() => {});         // v4 §5.4 NSA layer
    this.onSelectCluster = onSelectCluster || (() => {});     // v5 §9 dense-cluster list
    this.quality = quality;                    // standard | high | ultra
    this.idleTourSeconds = idleTourSeconds;
    this.clusterPx = clusterScreenDistancePx * lodCalibration;
    this.facingOcclusion = facingOcclusion;
    this.minConfSolid = minConfidenceSolid;
    this.canvas = document.createElement("canvas");
    host.appendChild(this.canvas);
    // v4 §2.2/§4.3 — 2D overlay for cluster counts + zoom-tiered city
    // labels (text over WebGL, pointer-transparent)
    this.overlay = document.createElement("canvas");
    this.overlay.className = "globe-overlay";
    this.overlay.style.cssText =
      "position:absolute;inset:0;width:100%;height:100%;pointer-events:none";
    host.appendChild(this.overlay);
    this.octx = this.overlay.getContext("2d");
    this.tip = document.createElement("div");
    this.tip.id = "map-tip";
    host.appendChild(this.tip);
    this.hoverId = null;
    const gl = this.canvas.getContext("webgl2", { antialias: true, alpha: true });
    if (!gl) throw new Error("WebGL2 unavailable");
    this.gl = gl;

    this.progLine = compile(gl, VERT_LINE, FRAG_LINE);
    this.progSphere = compile(gl, VERT_SPHERE, FRAG_SPHERE);
    this.progHalo = compile(gl, VERT_SPHERE, FRAG_HALO);
    this.progPoint = compile(gl, VERT_POINT, FRAG_POINT);
    this.progCity = compile(gl, VERT_CITY, FRAG_CITY);
    this.progArc = compile(gl, VERT_ARC, FRAG_ARC);
    this.progTrail = compile(gl, VERT_TRAIL, FRAG_TRAIL);
    this.progBurst = compile(gl, VERT_BURST, FRAG_BURST);
    if (this.quality === "ultra") {
      this.progBright = compile(gl, VERT_QUAD, FRAG_BRIGHT);
      this.progBlur = compile(gl, VERT_QUAD, FRAG_BLUR);
      this.progComposite = compile(gl, VERT_QUAD, FRAG_COMPOSITE);
      this.progBeam = compile(gl, VERT_BEAM, FRAG_BEAM);
    }

    this.yaw = 0.6; this.pitch = 0.25; this.dist = 3.1;
    this.velYaw = 0; this.velPitch = 0;
    // v6 §13 — the globe never moves on its own outside the idle tour;
    // starting with autoRotate=true was the "random panning" bug.
    this.autoRotate = false;
    this.tween = null;             // fly-to state
    this.lastInteraction = performance.now();
    this.tourIndex = 0;
    this.events = [];              // display list (clusters collapsed, v4 §2.2)
    this.rawEvents = [];
    this.clusters = [];
    this._lastClusterDist = 0;
    this.bursts = [];
    this.showHeatmap = false;
    this.showBorders = true;       // v4 §5.4 — borders on by default, always
    this.showDisputes = false;     // v4 §5.3 — separate toggle, off by default
    this.actors = [];              // v4 §5.4 NSA layer
    this.cities = [];              // v4 §4.3 label data (GeoNames)
    this.destroyed = false;
    this._boundaryLod = null;      // '50m' | '10m'
    this._b10m = null;             // lazily-decoded 10m dataset

    this._buildStaticGeometry();
    this._buildOverlayTextures();
    if (this.quality === "ultra") this._buildBloomTargets();
    this._initInteraction();
    this._resize();
    this._resizeObserver = new ResizeObserver(() => this._resize());
    this._resizeObserver.observe(host);
    this._t0 = performance.now();
    requestAnimationFrame((t) => this._frame(t));
  }

  destroy() {
    this.destroyed = true;
    this._resizeObserver.disconnect();
    this.canvas.remove();
    this.overlay.remove();
    this.tip.remove();
  }

  // --- v4 §2.3 boundary LOD + §5.3 disputed lines + §5.4 NSA layer ---

  _linesFromRings(countries, radius) {
    const verts = [];
    for (const c of countries) {
      for (const ring of c.r) {
        for (let i = 0; i + 3 < ring.length; i += 2) {
          verts.push(...latLonToVec3(ring[i + 1], ring[i], radius),
                     ...latLonToVec3(ring[i + 3], ring[i + 2], radius));
        }
      }
    }
    return new Float32Array(verts);
  }

  _ensureBoundaryLod(wanted) {
    if (this._boundaryLod === wanted) return;
    const gl = this.gl;
    if (wanted === "10m" && !this._b10m) {
      if (this._b10mLoading) return;   // decode in progress — keep 50m
      this._b10mLoading = true;
      import("../../data/boundaries10m.js").then((mod) => {
        this._b10m = decodeBoundaries(mod.BOUNDARIES_10M_ENC);
        this._b10mLoading = false;
        this._boundaryLod = null;      // force rebuild next frame
      }).catch(() => { this._b10mLoading = false; });
      return;
    }
    const data = wanted === "10m" ? this._b10m
      : decodeBoundaries(BOUNDARIES_50M_ENC);
    if (!data) return;
    const verts = this._linesFromRings(data, 1.0008);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.borderBuf);
    gl.bufferData(gl.ARRAY_BUFFER, verts, gl.DYNAMIC_DRAW);
    this.borderCount = verts.length / 3;
    this._boundaryLod = wanted;
  }

  _buildDisputed() {
    // dashed look: keep every other segment pair so the line reads as
    // deliberately provisional (§5.3 — a disputed line must not render
    // like a settled one)
    const gl = this.gl;
    const verts = [];
    const lines = decodeBoundaries(DISPUTED_BOUNDARIES_ENC);
    for (const c of lines) {
      for (const ring of c.r) {
        for (let i = 0; i + 3 < ring.length; i += 2) {
          if ((i >> 1) % 2 === 0) {
            verts.push(...latLonToVec3(ring[i + 1], ring[i], 1.0012),
                       ...latLonToVec3(ring[i + 3], ring[i + 2], 1.0012));
          }
        }
      }
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, this.disputeBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
    this.disputeCount = verts.length / 3;
  }

  setBorders(on) { this.showBorders = !!on; }

  setDisputes(on) {
    this.showDisputes = !!on;
    if (on && !this.disputeCount) this._buildDisputed();
  }

  setActors(actors) {
    const gl = this.gl;
    this.actors = (actors || []).filter((a) => a.base_lat != null);
    const pts = new Float32Array(this.actors.length * 9);
    this.actors.forEach((a, i) => {
      const [x, y, z] = latLonToVec3(a.base_lat, a.base_lon, 1.005);
      pts.set([x, y, z, 0.95, 0.35, 0.55, 6.0, 0.0, 0.85], i * 9);
    });
    gl.bindBuffer(gl.ARRAY_BUFFER, this.actorBuf);
    gl.bufferData(gl.ARRAY_BUFFER, pts, gl.DYNAMIC_DRAW);
    this.actorCount = this.actors.length;
  }

  // v5 §11 — rough NSA territory zones, drawn as translucent filled polygons
  // on the 2D overlay (facing-culled), under the same NSA toggle as markers
  setActorZones(zones) { this.actorZones = zones || []; }

  setCities(cities) { this.cities = cities || []; }
  // v6.1.1 — dynamic country labels: {name, lat, lon, span} where span is the
  // country's bbox size in degrees. Visibility is gated on APPARENT on-screen
  // size, so big countries (Russia/USA) show from far out and small ones
  // (Bhutan/Luxembourg) only reveal as you zoom into them.
  setCountryLabels(labels) { this.countryLabels = labels || []; }
  setCountryLabelsVisible(on) { this.countryLabelsOn = on !== false; }   // v6.2 toggle

  // v6.2 — theme-driven globe colouring: the App reads --globe-ocean and
  // --globe-rim from the active theme's CSS and pushes RGB triples (0..1)
  // here so every theme retints the sphere itself, not just the panels.
  setThemeColors(oceanRgb, rimRgb) {
    if (oceanRgb) this.oceanTint = oceanRgb;
    if (rimRgb) this.rimTint = rimRgb;
  }

  // --- public controls (App / command palette / bookmarks) ---

  getCamera() { return { yaw: this.yaw, pitch: this.pitch, dist: this.dist }; }

  setCamera({ yaw, pitch, dist }) {
    this.yaw = yaw; this.pitch = pitch; this.dist = dist;
    this.tween = null;
    this._touch();
  }

  flyTo(lat, lon, dist = 2.2, durationMs = 1200) {
    // solve yaw/pitch that bring (lat,lon) to face the camera (+z)
    const [x, y, z] = latLonToVec3(lat, lon, 1);
    let targetYaw = Math.atan2(-x, z);
    const targetPitch = Math.max(-1.35, Math.min(1.35, Math.atan2(y, Math.hypot(x, z))));
    // shortest angular path
    const twoPi = Math.PI * 2;
    while (targetYaw - this.yaw > Math.PI) targetYaw -= twoPi;
    while (targetYaw - this.yaw < -Math.PI) targetYaw += twoPi;
    this.tween = {
      from: { yaw: this.yaw, pitch: this.pitch, dist: this.dist },
      to: { yaw: targetYaw, pitch: targetPitch, dist },
      start: performance.now(), duration: durationMs,
    };
  }

  setHeatmap(on) { this.showHeatmap = on; }
  setTerrain(on) { this.terrainOn = !!on; }   // v5 §8 (LOD-gated in the draw)

  burst(lat, lon, category = "other") {
    if (lat == null || lon == null) return;
    const time = (performance.now() - this._t0) / 1000;
    this.bursts.push({ pos: latLonToVec3(lat, lon, 1.01),
                       color: CATEGORY_COLORS[category] || CATEGORY_COLORS.other,
                       start: time });
    this.bursts = this.bursts.filter((b) => time - b.start < 1.8);
    this._uploadBursts();
  }

  // --- geometry ---

  _staticBuffer(data) {
    const gl = this.gl;
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    return buf;
  }

  _buildStaticGeometry() {
    const gl = this.gl;
    // sphere mesh (surface + rim + terminator + overlay sampling).
    // Fine tessellation at radius ~1.0 so the surface barely dips below the
    // coastline shell (radius 1.001), keeping depth occlusion tight; the
    // shader-side back-hemisphere discard on lines/lights is the real
    // guarantee against see-through, this just keeps the two consistent.
    const verts = [], idx = [];
    const LAT = 90, LON = 180, R = 0.999;
    for (let i = 0; i <= LAT; i++) {
      const lat = 90 - (180 * i) / LAT;
      for (let j = 0; j <= LON; j++) {
        verts.push(...latLonToVec3(lat, -180 + (360 * j) / LON, R));
      }
    }
    for (let i = 0; i < LAT; i++)
      for (let j = 0; j < LON; j++) {
        const a = i * (LON + 1) + j, b = a + LON + 1;
        idx.push(a, b, a + 1, b, b + 1, a + 1);
      }
    this.sphereBuf = this._staticBuffer(new Float32Array(verts));
    this.sphereIdx = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.sphereIdx);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(idx), gl.STATIC_DRAW);
    this.sphereIdxCount = idx.length;
    // halo shell (same topology, radius 1.045)
    const haloVerts = verts.map((v) => v * (1.045 / R));
    this.haloBuf = this._staticBuffer(new Float32Array(haloVerts));

    // graticule — hugs the sphere (radius 1.0005), back half shader-culled
    const grat = [];
    for (let lat = -60; lat <= 60; lat += 30)
      for (let lon = -180; lon < 180; lon += 3)
        grat.push(...latLonToVec3(lat, lon, 1.0005), ...latLonToVec3(lat, lon + 3, 1.0005));
    for (let lon = -180; lon < 180; lon += 30)
      for (let lat = -87; lat < 87; lat += 3)
        grat.push(...latLonToVec3(lat, lon, 1.0005), ...latLonToVec3(lat + 3, lon, 1.0005));
    this.gratBuf = this._staticBuffer(new Float32Array(grat));
    this.gratCount = grat.length / 3;

    // coastlines
    const coast = [];
    for (const line of COASTLINES) {
      for (let i = 0; i + 3 < line.length; i += 2) {
        coast.push(...latLonToVec3(line[i + 1], line[i], 1.001),
                   ...latLonToVec3(line[i + 3], line[i + 2], 1.001));
      }
    }
    this.coastBuf = this._staticBuffer(new Float32Array(coast));
    this.coastCount = coast.length / 3;

    // city lights (§5.1) — [lon, lat, brightness] triplets
    const cities = new Float32Array((CITY_LIGHTS.length / 3) * 4);
    for (let i = 0, o = 0; i < CITY_LIGHTS.length; i += 3, o += 4) {
      const [x, y, z] = latLonToVec3(CITY_LIGHTS[i + 1], CITY_LIGHTS[i], 1.0015);
      cities[o] = x; cities[o + 1] = y; cities[o + 2] = z;
      cities[o + 3] = CITY_LIGHTS[i + 2];
    }
    this.cityBuf = this._staticBuffer(cities);
    this.cityCount = CITY_LIGHTS.length / 3;

    // starfield (high+)
    if (this.quality !== "standard") {
      const stars = new Float32Array(900 * 8);
      for (let i = 0; i < 900; i++) {
        const u = Math.random() * 2 - 1, a = Math.random() * Math.PI * 2;
        // kept within the tightened far plane (see _mvp) to avoid clipping
        const r = Math.sqrt(1 - u * u), R2 = 11;
        stars.set([R2 * r * Math.cos(a), R2 * u, R2 * r * Math.sin(a),
                   0.75, 0.8, 0.95, 1.1 + Math.random() * 1.6, Math.random()], i * 8);
      }
      this.starBuf = this._staticBuffer(stars);
      this.starCount = 900;
    }

    this.pointBuf = gl.createBuffer();
    this.pointCount = 0;
    this.arcBuf = gl.createBuffer();
    this.arcCount = 0;
    this.trailBuf = gl.createBuffer();
    this.trailCount = 0;
    this.burstBuf = gl.createBuffer();
    this.burstCount = 0;
    this.beamBuf = gl.createBuffer();
    this.beamCount = 0;
    this.markedBuf = gl.createBuffer();
    this.markedCount = 0;
    this.markedLocations = [];
    this.satBuf = gl.createBuffer();
    this.satCount = 0;
    // v4: country borders (LOD), disputed lines, NSA markers
    this.borderBuf = gl.createBuffer();
    this.borderCount = 0;
    this.disputeBuf = gl.createBuffer();
    this.disputeCount = 0;
    this.actorBuf = gl.createBuffer();
    this.actorCount = 0;
    this._ensureBoundaryLod("50m");
    this.allianceBuf = gl.createBuffer();
    this.allianceCount = 0;
    this.allianceColor = [0.4, 0.75, 1.0];
    // fullscreen quad for post passes
    this.quadBuf = this._staticBuffer(new Float32Array([-1, -1, 3, -1, -1, 3]));
  }

  // --- v3 §17: persistent marked-location layer (fixed style, not the
  // pulsing live-event treatment — the two must never be confused) ---
  setMarkedLocations(locations) {
    const gl = this.gl;
    this.markedLocations = (locations || []).filter((l) => l.lat != null);
    const CAT_COLORS = {
      capital: [0.55, 0.62, 0.75], strategic_chokepoint: [0.35, 0.9, 0.95],
      contested_territory: [1.0, 0.62, 0.35], conflict_zone: [1.0, 0.42, 0.42],
      semiconductor_fab: [0.6, 1.0, 0.6], rare_earth_site: [0.85, 0.75, 0.5],
      undersea_cable: [0.5, 0.8, 1.0], energy_pipeline: [1.0, 0.85, 0.4],
      lng_terminal: [1.0, 0.7, 0.85], other: [0.7, 0.7, 0.7],
    };
    const pts = new Float32Array(this.markedLocations.length * 9);
    this.markedLocations.forEach((l, i) => {
      const [x, y, z] = latLonToVec3(l.lat, l.lon, 1.004);
      const c = CAT_COLORS[l.category] || CAT_COLORS.other;
      const size = l.category === "capital" ? 3.2 : 5.5;
      pts.set([x, y, z, ...c, size, 0.0, 0.9], i * 9);  // phase 0 = steady
    });
    gl.bindBuffer(gl.ARRAY_BUFFER, this.markedBuf);
    gl.bufferData(gl.ARRAY_BUFFER, pts, gl.DYNAMIC_DRAW);
    this.markedCount = this.markedLocations.length;
  }

  // --- v3 §10.2: satellites at their real altitude above the surface ---
  setSatellites(positions) {
    const gl = this.gl;
    const pts = new Float32Array(positions.length * 9);
    positions.forEach((s, i) => {
      const r = 1 + Math.min(0.5, (s.altKm || 400) / 6371 * 3); // exaggerated alt
      const [x, y, z] = latLonToVec3(s.lat, s.lon, r);
      pts.set([x, y, z, 0.65, 0.95, 1.0, 2.6, 0.0, 1.0], i * 9);
    });
    gl.bindBuffer(gl.ARRAY_BUFFER, this.satBuf);
    gl.bufferData(gl.ARRAY_BUFFER, pts, gl.DYNAMIC_DRAW);
    this.satCount = positions.length;
  }

  // --- v3 §14: alliance-bloc boundary tint (colored member outlines) ---
  _ringsToBuffer(rings, radius) {
    const gl = this.gl;
    const verts = [];
    for (const ring of rings) {
      for (let i = 0; i + 3 < ring.length; i += 2) {
        verts.push(...latLonToVec3(ring[i + 1], ring[i], radius),
                   ...latLonToVec3(ring[i + 3], ring[i + 2], radius));
      }
    }
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.DYNAMIC_DRAW);
    return { buf, count: verts.length / 3 };
  }

  // v6 §7/§8 — generic multi-color boundary-ring overlay groups: any number
  // of colored ring sets drawn simultaneously. Backs the multi-select bloc
  // overlay (several alliances at once), War Mode's one-color-per-side party
  // rendering, and the single-alliance API below.
  setColoredRings(groups) {
    const gl = this.gl;
    for (const g of (this.ringGroups || [])) gl.deleteBuffer(g.buf);
    this.ringGroups = [];
    for (const g of (groups || [])) {
      if (!g.rings || !g.rings.length) continue;
      const { buf, count } = this._ringsToBuffer(g.rings, 1.0035);
      this.ringGroups.push({ buf, count, color: g.color || [0.4, 0.75, 1.0],
                             alpha: g.alpha != null ? g.alpha : 0.9 });
    }
  }

  setAllianceOverlay(memberRings, colorRgb) {
    this.setColoredRings(memberRings && memberRings.length
      ? [{ rings: memberRings, color: colorRgb }] : []);
  }

  // v6 §26 — pulsing highlight on the focused country/region's borders,
  // separate slot from the bloc/war overlays so both can show at once.
  // Cleared (null) when the corresponding panel closes.
  setHighlight(rings, colorRgb) {
    const gl = this.gl;
    if (this.highlightGroup) { gl.deleteBuffer(this.highlightGroup.buf); }
    this.highlightGroup = null;
    if (rings && rings.length) {
      const { buf, count } = this._ringsToBuffer(rings, 1.0042);
      // v6.2 — selected-entity outline is orange/gold (owner: not greenish)
      this.highlightGroup = { buf, count, color: colorRgb || [1.0, 0.72, 0.18] };
    }
  }

  // v6 §16 — thematic choropleth: {iso3: cssColor} fill map painted onto the
  // overlay canvas from the same boundary rings as the base map (shapes stay
  // consistent across modes). null clears the mode.
  setChoropleth(colorsByIso3) {
    this.choropleth = colorsByIso3 || null;
    if (this.choropleth && !this._b50mData) {
      this._b50mData = decodeBoundaries(BOUNDARIES_50M_ENC);
    }
  }

  setCityLights(on) { this.cityLightsOn = !!on; }   // v6 §24

  // v6 §6 — every event inside a screen-space rectangle (client px),
  // front-facing only; powers the drag-to-select box
  eventsInRect(x0, y0, x1, y1) {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const [lo_x, hi_x] = [Math.min(x0, x1), Math.max(x0, x1)];
    const [lo_y, hi_y] = [Math.min(y0, y1), Math.max(y0, y1)];
    const { mvp, model } = this._mvp();
    const out = [];
    // rawEvents, not the display list — clusters collapse members out of
    // this.events, and a selection box must catch every event inside it
    for (const e of (this.rawEvents || [])) {
      if (e.lat == null || e.lon == null) continue;
      const [x, y, z] = latLonToVec3(e.lat, e.lon, 1.006);
      if (this._facing(model, x, y, z) < 0.02) continue;
      const p = this._project(mvp, x, y, z);
      if (!p) continue;
      const cx = rect.left + p[0] / dpr, cy = rect.top + p[1] / dpr;
      if (cx >= lo_x && cx <= hi_x && cy >= lo_y && cy <= hi_y) out.push(e);
    }
    return out;
  }

  // --- v3 §13.3: screen point -> lat/lon via ray-sphere intersection ---
  screenToLatLon(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    const ndcX = ((clientX - rect.left) / rect.width) * 2 - 1;
    const ndcY = 1 - ((clientY - rect.top) / rect.height) * 2;
    const aspect = this.canvas.width / Math.max(1, this.canvas.height);
    const tanF = Math.tan(0.35); // fovY 0.7 / 2
    // view-space ray from camera at (0,0,dist)
    const d = [ndcX * tanF * aspect, ndcY * tanF, -1];
    const o = [0, 0, this.dist];
    const dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
    const od = o[0] * d[0] + o[1] * d[1] + o[2] * d[2];
    const oo = o[0] * o[0] + o[1] * o[1] + o[2] * o[2];
    const disc = od * od - dd * (oo - 1);
    if (disc < 0) return null;                 // clicked off the globe
    const t = (-od - Math.sqrt(disc)) / dd;
    let p = [o[0] + t * d[0], o[1] + t * d[1], o[2] + t * d[2]];
    // undo model rotation: model = Rx(pitch)*Ry(yaw); q = Ry(-yaw)*Rx(-pitch)*p
    const cp = Math.cos(-this.pitch), sp = Math.sin(-this.pitch);
    p = [p[0], cp * p[1] - sp * p[2], sp * p[1] + cp * p[2]];
    const cy = Math.cos(-this.yaw), sy = Math.sin(-this.yaw);
    p = [cy * p[0] + sy * p[2], p[1], -sy * p[0] + cy * p[2]];
    const lat = Math.asin(Math.max(-1, Math.min(1, p[1]))) * 180 / Math.PI;
    const lon = Math.atan2(p[2], -p[0]) * 180 / Math.PI - 180;
    return { lat, lon: ((lon + 540) % 360) - 180 };
  }

  // --- v3 §9.1: WebXR immersive session (interior-surface mode) ---
  async enterXR() {
    if (!navigator.xr) throw new Error("WebXR unavailable");
    const gl = this.gl;
    await gl.makeXRCompatible();
    const session = await navigator.xr.requestSession("immersive-vr");
    const layer = new XRWebGLLayer(session, gl);
    await session.updateRenderState({ baseLayer: layer });
    const refSpace = await session.requestReferenceSpace("local");
    this.xrSession = session;
    const XR_SCALE = 6.0;   // user stands inside a 6-unit sphere interior
    const onFrame = (t, frame) => {
      if (!this.xrSession) return;
      session.requestAnimationFrame(onFrame);
      const pose = frame.getViewerPose(refSpace);
      if (!pose) return;
      gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
      gl.clearColor(0, 0, 0, 1);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      const time = (performance.now() - this._t0) / 1000;
      this.sunDir = new Float32Array(sunDirection());
      for (const view of pose.views) {
        const vp = layer.getViewport(view);
        gl.viewport(vp.x, vp.y, vp.width, vp.height);
        // scale model up so the viewer is inside the sphere
        const scale = new Float32Array([XR_SCALE, 0, 0, 0, 0, XR_SCALE, 0, 0,
                                        0, 0, XR_SCALE, 0, 0, 0, 0, 1]);
        const model = mat4Multiply(
          mat4Multiply(mat4RotX(this.pitch), mat4RotY(this.yaw)), scale);
        const mvp = mat4Multiply(view.projectionMatrix,
                                 mat4Multiply(view.transform.inverse.matrix, model));
        this.xrInside = true;
        this._drawScene(time, mvp, model);
        this.xrInside = false;
      }
    };
    session.requestAnimationFrame(onFrame);
    session.addEventListener("end", () => { this.xrSession = null; });
  }

  _buildBeams() {
    const gl = this.gl;
    // interleaved per-vertex: base(3) axis(3) color(3) side(1) t(1) height(1)
    const STRIDE = 12;
    const beacons = this.rawEvents.filter((e) => (e.severity || 1) >= 3);
    const data = new Float32Array(beacons.length * 6 * STRIDE);
    let o = 0;
    for (const e of beacons) {
      const axis = latLonToVec3(e._rlat ?? e.lat, e._rlon ?? e.lon, 1);
      const base = [axis[0] * 1.006, axis[1] * 1.006, axis[2] * 1.006];
      const color = CATEGORY_COLORS[e.category] || CATEGORY_COLORS.other;
      const height = 0.06 + (e.severity - 2) * 0.05;   // taller = more severe
      // two triangles: (bL, bR, tR) (bL, tR, tL); side ∈ {-1,+1}, t ∈ {0,1}
      const verts = [[-1, 0], [1, 0], [1, 1], [-1, 0], [1, 1], [-1, 1]];
      for (const [side, t] of verts) {
        data.set([...base, ...axis, ...color, side, t, height], o);
        o += STRIDE;
      }
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, this.beamBuf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
    this.beamCount = beacons.length * 6;
  }

  _buildOverlayTextures() {
    const gl = this.gl;
    this.heatCanvas = document.createElement("canvas");
    this.heatCanvas.width = 256; this.heatCanvas.height = 128;
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE,
                  new Uint8Array([0, 0, 0, 0]));
    this.heatTex = tex;
    // v6 §19 — baked biome/elevation texture, loaded async from the vendored
    // data URL (scripts/build_biome_texture.py); terrain shading stays off
    // until it's ready (biomeReady uniform)
    this.biomeTex = gl.createTexture();
    this.biomeReady = false;
    gl.bindTexture(gl.TEXTURE_2D, this.biomeTex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE,
                  new Uint8Array([20, 40, 70, 255]));
    import("../../data/biomeTexture.js").then(({ BIOME_TEXTURE_DATAURL }) => {
      const img = new Image();
      img.onload = () => {
        if (!this.gl) return;
        this.gl.bindTexture(this.gl.TEXTURE_2D, this.biomeTex);
        this.gl.texImage2D(this.gl.TEXTURE_2D, 0, this.gl.RGBA, this.gl.RGBA,
                           this.gl.UNSIGNED_BYTE, img);
        this.biomeReady = true;
      };
      img.src = BIOME_TEXTURE_DATAURL;
    }).catch(() => {});
  }

  _uploadCanvasTex(tex, canvas) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
  }

  _splat(ctx, w, h, events, radius, alphaScale) {
    for (const e of events) {
      const x = ((e.lon + 180) / 360) * w;
      const y = ((90 - e.lat) / 180) * h;
      const r = radius * (0.6 + (e.severity || 1) * 0.18);
      const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
      grad.addColorStop(0, `rgba(255,255,255,${0.35 * alphaScale})`);
      grad.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = grad;
      ctx.fillRect(x - r, y - r, r * 2, r * 2);
    }
  }

  _refreshOverlays() {
    // heatmap: rebuilt from current events on every data change (§5.1).
    // splat sizes shrink as event count grows so dense datasets read as a
    // gradient rather than saturating the whole texture. Only drawn when
    // the heatmap toggle is on. (The old always-on "ghost trail" overlay
    // was removed — it produced flat blocky purple patches.)
    const density = Math.max(1, Math.sqrt(this.rawEvents.length / 60));
    const hc = this.heatCanvas.getContext("2d");
    hc.clearRect(0, 0, 256, 128);
    this._splat(hc, 256, 128, this.rawEvents, 9 / density, 0.7);
    this._uploadCanvasTex(this.heatTex, this.heatCanvas);
  }

  _buildBloomTargets() {
    const gl = this.gl;
    const mkTarget = (w, h) => {
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      const fbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      return { tex, fbo, w, h };
    };
    this._mkTarget = mkTarget;
    this.bloomTargets = null;   // sized lazily in _resize
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  setData({ events = [], links = [] }) {
    const gl = this.gl;
    this.rawEvents = events.filter((e) => e.lat != null && e.lon != null);
    this._recluster();

    // Ultra: volumetric light pillars rising from significant events
    // (severity >= 3). Billboarded quads along the surface normal, alpha
    // fading to the tip; the bloom pass turns them into glowing beacons.
    if (this.quality === "ultra") this._buildBeams();

    // great-circle correlation threads + trail particles along them
    const SEG = 36;
    const arcVerts = [], trailVerts = [];
    for (const link of links) {
      const a = latLonToVec3(link.from[0], link.from[1], 1);
      const b = latLonToVec3(link.to[0], link.to[1], 1);
      const dot = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]));
      const omega = Math.acos(dot);
      if (omega < 1e-4) continue;
      const lift = 0.04 + 0.22 * (omega / Math.PI);
      let prev = null;
      for (let s = 0; s <= SEG; s++) {
        const t = s / SEG;
        const sa = Math.sin((1 - t) * omega) / Math.sin(omega);
        const sb = Math.sin(t * omega) / Math.sin(omega);
        const r = 1.004 + Math.sin(Math.PI * t) * lift;
        const p = [(sa * a[0] + sb * b[0]) * r, (sa * a[1] + sb * b[1]) * r,
                   (sa * a[2] + sb * b[2]) * r];
        if (s % 2 === 0) trailVerts.push(p[0], p[1], p[2], t);
        if (prev) arcVerts.push(prev[0], prev[1], prev[2], prev[3], p[0], p[1], p[2], t);
        prev = [p[0], p[1], p[2], t];
      }
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, this.arcBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(arcVerts), gl.DYNAMIC_DRAW);
    this.arcCount = arcVerts.length / 4;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.trailBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(trailVerts), gl.DYNAMIC_DRAW);
    this.trailCount = trailVerts.length / 4;

    this._refreshOverlays();
  }

  // --- v4 §2.2 zoom-dependent clustering with progressive declustering ---
  // Not a hard zoom-level cutoff: points cluster while their screen-space
  // separation is under cluster_screen_distance_px and split as the camera
  // closes in, recomputed continuously as dist changes.

  _clusterAngleDeg() {
    // px per radian of surface arc at screen center ≈ globeRadiusPx
    const h = this.canvas.height || 1;
    const globeRadiusPx = (h / 2) / (Math.tan(0.35) * Math.max(1.05, this.dist));
    const dpr = window.devicePixelRatio || 1;
    return (this.clusterPx * dpr / Math.max(1, globeRadiusPx)) * 180 / Math.PI;
  }

  _recluster() {
    const cellDeg = Math.max(0.15, this._clusterAngleDeg());
    this._lastClusterDist = this.dist;
    const grid = new Map();
    for (const e of this.rawEvents) {
      const key = `${Math.round(e.lat / cellDeg)}:` +
        `${Math.round(e.lon * Math.cos(e.lat * Math.PI / 180) / cellDeg)}`;
      (grid.get(key) || grid.set(key, []).get(key)).push(e);
    }
    this.events = [];
    this.clusters = [];
    const pending = [];
    for (const group of grid.values()) {
      if (group.length >= 3 && cellDeg > 0.8) {
        pending.push(group);
      } else {
        // coincident-point spreading for singles (kept from v3): stacked
        // same-city events fan out so each stays individually clickable
        if (group.length === 1) {
          group[0]._rlat = group[0].lat; group[0]._rlon = group[0].lon;
        } else {
          const ring = 0.9 + Math.min(1.6, group.length * 0.12);
          group.forEach((e, k) => {
            const ang = (k / group.length) * Math.PI * 2;
            const latScale = 1 / Math.max(0.3, Math.cos(e.lat * Math.PI / 180));
            e._rlat = e.lat + Math.sin(ang) * ring;
            e._rlon = e.lon + Math.cos(ang) * ring * latScale;
          });
        }
        this.events.push(...group);
      }
    }
    // merge adjacent-cell clusters that would overlap on screen, then
    // finalize (dominant category, max severity, centroid)
    const merged = [];
    for (const group of pending) {
      const lat = group.reduce((s, e) => s + e.lat, 0) / group.length;
      const lon = group.reduce((s, e) => s + e.lon, 0) / group.length;
      const near = merged.find((m) =>
        Math.abs(m.lat - lat) < cellDeg &&
        Math.abs(m.lon - lon) * Math.cos(lat * Math.PI / 180) < cellDeg);
      if (near) {
        near.members.push(...group);
        near.lat = near.members.reduce((s, e) => s + e.lat, 0) / near.members.length;
        near.lon = near.members.reduce((s, e) => s + e.lon, 0) / near.members.length;
      } else {
        merged.push({ lat, lon, members: [...group] });
      }
    }
    for (const m of merged) {
      const catCount = {};
      let sev = 1;
      for (const e of m.members) {
        catCount[e.category] = (catCount[e.category] || 0) + 1;
        sev = Math.max(sev, e.severity || 1);
      }
      this.clusters.push({
        _cluster: true, lat: m.lat, lon: m.lon, _rlat: m.lat, _rlon: m.lon,
        members: m.members, count: m.members.length, severity: sev,
        category: Object.keys(catCount).sort((a, b) => catCount[b] - catCount[a])[0],
      });
    }
    this._uploadPoints();
  }

  _uploadPoints() {
    // Clusters are NOT giant glow sprites (that read as the blobs the v2
    // feedback killed) — they draw as crisp counted circles on the 2D
    // overlay; only individual events go in the GL point buffer.
    const gl = this.gl;
    const pts = new Float32Array(this.events.length * 9);
    this.events.forEach((e, i) => {
      const [x, y, z] = latLonToVec3(e._rlat, e._rlon, 1.006);
      const color = CATEGORY_COLORS[e.category] || CATEGORY_COLORS.other;
      // §2: uncorrelated events render dimmer until promoted into a story;
      // v4 §3.1: low-confidence geocodes render dimmer still — the map
      // never implies more precision than the resolution actually has
      let bright = e.story_id ? 1.0 : 0.45;
      if (e.geocode_confidence != null && e.geocode_confidence < this.minConfSolid) {
        bright *= 0.55;
      }
      pts.set([x, y, z, ...color, 5 + (e.severity || 1) * 2.4, Math.random(), bright],
              i * 9);
    });
    gl.bindBuffer(gl.ARRAY_BUFFER, this.pointBuf);
    gl.bufferData(gl.ARRAY_BUFFER, pts, gl.DYNAMIC_DRAW);
    this.pointCount = this.events.length;
  }

  _clusterRadiusPx(count) {
    const dpr = window.devicePixelRatio || 1;
    return (11 + Math.min(9, count * 0.35)) * dpr;
  }

  _uploadBursts() {
    const gl = this.gl;
    const data = new Float32Array(this.bursts.length * 7);
    this.bursts.forEach((b, i) => {
      data.set([...b.pos, b.start, ...b.color], i * 7);
    });
    gl.bindBuffer(gl.ARRAY_BUFFER, this.burstBuf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
    this.burstCount = this.bursts.length;
  }

  // --- interaction ---

  _touch() { this.lastInteraction = performance.now(); this.autoRotate = false; }

  _initInteraction() {
    const el = this.canvas;
    el.style.cursor = "grab";
    let dragging = false, lastX = 0, lastY = 0, moved = 0;
    el.addEventListener("pointerdown", (ev) => {
      dragging = true; moved = 0; lastX = ev.clientX; lastY = ev.clientY;
      this._touch(); this.tween = null;
      el.setPointerCapture(ev.pointerId);
    });
    el.addEventListener("pointermove", (ev) => {
      if (!dragging) {
        this._updateHover(ev.clientX, ev.clientY);  // tooltip + cursor
        return;
      }
      const dx = ev.clientX - lastX, dy = ev.clientY - lastY;
      moved += Math.abs(dx) + Math.abs(dy);
      lastX = ev.clientX; lastY = ev.clientY;
      this.velYaw = dx * 0.005; this.velPitch = dy * 0.005;
      this.yaw += this.velYaw;
      this.pitch = Math.max(-1.35, Math.min(1.35, this.pitch + this.velPitch));
    });
    el.addEventListener("pointerdown", () => { this.tip.style.display = "none"; });
    el.addEventListener("pointerleave", () => {
      this.tip.style.display = "none"; this.hoverId = null;
    });
    el.addEventListener("pointerup", (ev) => {
      dragging = false;
      if (moved < 6) this._pick(ev.clientX, ev.clientY);
      this._updateHover(ev.clientX, ev.clientY);
      this._touch();
    });
    el.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      this.dist = Math.max(1.45, Math.min(5.5, this.dist + ev.deltaY * 0.0018));
      this._touch(); this.tween = null;
    }, { passive: false });

    // v6.1 — WASD navigation (game-style): A/D spin the globe (yaw), W/S tilt
    // (pitch), Q/E or +/- zoom. Held keys apply continuously in _updateCamera.
    // Ignored while typing in an input so it never eats text.
    this.keys = {};
    const isTyping = (t) => t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA"
      || t.tagName === "SELECT" || t.isContentEditable);
    window.addEventListener("keydown", (ev) => {
      if (isTyping(ev.target)) return;
      const k = ev.key.toLowerCase();
      if ("wasdqe".includes(k) || k === "+" || k === "-" || k === "=") {
        this.keys[k] = true; this._touch(); this.tween = null;
      }
    });
    window.addEventListener("keyup", (ev) => {
      this.keys[ev.key.toLowerCase()] = false;
    });
  }

  // v6.1 — apply currently-held WASD/QE keys to the camera each frame
  _applyKeys(dt) {
    if (!this.keys) return false;
    const yawStep = 1.4 * dt, pitchStep = 1.1 * dt, zoomStep = 1.6 * dt;
    let moved = false;
    // v6.2 — A/D direction inverted (owner request)
    if (this.keys.a) { this.yaw += yawStep; moved = true; }
    if (this.keys.d) { this.yaw -= yawStep; moved = true; }
    if (this.keys.w) { this.pitch = Math.min(1.35, this.pitch + pitchStep); moved = true; }
    if (this.keys.s) { this.pitch = Math.max(-1.35, this.pitch - pitchStep); moved = true; }
    if (this.keys.q || this.keys["-"]) {
      this.dist = Math.min(5.5, this.dist + zoomStep); moved = true; }
    if (this.keys.e || this.keys["+"] || this.keys["="]) {
      this.dist = Math.max(1.45, this.dist - zoomStep); moved = true; }
    if (moved) this.lastInteraction = performance.now();
    return moved;
  }

  _mvp() {
    const aspect = this.canvas.width / Math.max(1, this.canvas.height);
    // near/far tightened to the scene's actual depth range (camera dist is
    // 1.45-5.5, nothing sits farther than ~1.3 units off-surface). A
    // standard depth buffer concentrates precision near the near plane, so
    // the old 0.1-100 range (ratio 1000:1) crushed precision right where
    // the globe lives, causing z-fighting between the coastline shell and
    // the sphere surface — worst at the silhouette, where front/back
    // points are closest in depth, which read as "seeing through the
    // globe" to far-side geometry. 0.12-14 (ratio ~117:1) fixes this
    // without clipping anything (starfield radius was pulled in to match).
    const proj = mat4Perspective(0.7, aspect, 0.12, 14);
    const model = mat4Multiply(mat4RotX(this.pitch), mat4RotY(this.yaw));
    const view = mat4Translate(0, 0, -this.dist);
    return { mvp: mat4Multiply(proj, mat4Multiply(view, model)), model };
  }

  // v4 §2.1 — correct occlusion: the same facing computation the vertex
  // shader already uses for rendering (vFacing = (mat3(model)·n̂).z), NOT
  // the old NDC-depth threshold (cz/cw > 0.997) that let far-side orbs
  // stay clickable through the globe. Any candidate facing away from the
  // camera is rejected outright.
  _facing(model, x, y, z) {
    const len = Math.hypot(x, y, z) || 1;
    const nx = x / len, ny = y / len, nz = z / len;
    return model[2] * nx + model[6] * ny + model[10] * nz;
  }

  _project(mvp, x, y, z) {
    const cw = mvp[3] * x + mvp[7] * y + mvp[11] * z + mvp[15];
    if (cw <= 0) return null;
    return [
      ((mvp[0] * x + mvp[4] * y + mvp[8] * z + mvp[12]) / cw * 0.5 + 0.5)
        * this.canvas.width,
      (1 - ((mvp[1] * x + mvp[5] * y + mvp[9] * z + mvp[13]) / cw * 0.5 + 0.5))
        * this.canvas.height,
      cw,
    ];
  }

  // v4 §2.2 — the clickable hit area is the SOLID DOT actually drawn (the
  // point-sprite core, ~22.5% of gl_PointSize), not the pretty diffuse
  // glow around it — with a small usability floor so tiny dots stay
  // tappable. Glow radius and hit radius are decoupled by construction.
  _coreRadiusPx(sizeAttr, bright, cw) {
    const dpr = window.devicePixelRatio || 1;
    const pointSize = sizeAttr * (0.55 + 0.45 * bright) * dpr * (140.0 / cw) * 0.055;
    return Math.max(8 * dpr, pointSize * 0.225 * 1.3);
  }

  _hitTest(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    const px = (clientX - rect.left) * (this.canvas.width / rect.width);
    const py = (clientY - rect.top) * (this.canvas.height / rect.height);
    const { mvp, model } = this._mvp();
    let best = null, bestScore = Infinity;
    const consider = (item, lat, lon, sizeAttr, bright) => {
      const [x, y, z] = latLonToVec3(lat, lon, 1.006);
      if (this.facingOcclusion && this._facing(model, x, y, z) < 0) return;
      const p = this._project(mvp, x, y, z);
      if (!p) return;
      const d = Math.hypot(p[0] - px, p[1] - py);
      const hitRadius = this._coreRadiusPx(sizeAttr, bright, p[2]);
      if (d < hitRadius && d < bestScore) { bestScore = d; best = item; }
    };
    for (const c of this.clusters) {
      const [x, y, z] = latLonToVec3(c.lat, c.lon, 1.006);
      if (this.facingOcclusion && this._facing(model, x, y, z) < 0) continue;
      const p = this._project(mvp, x, y, z);
      if (!p) continue;
      const d = Math.hypot(p[0] - px, p[1] - py);
      if (d < this._clusterRadiusPx(c.count) && d < bestScore) {
        bestScore = d; best = c;
      }
    }
    for (const e of this.events) {
      consider(e, e._rlat ?? e.lat, e._rlon ?? e.lon,
               5 + (e.severity || 1) * 2.4, e.story_id ? 1.0 : 0.45);
    }
    return best;
  }

  _hitTestPointList(clientX, clientY, list, latKey, lonKey, radius) {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const px = (clientX - rect.left) * (this.canvas.width / rect.width);
    const py = (clientY - rect.top) * (this.canvas.height / rect.height);
    const { mvp, model } = this._mvp();
    let best = null, bestD = 12 * dpr;
    for (const l of list) {
      const [x, y, z] = latLonToVec3(l[latKey], l[lonKey], radius);
      if (this.facingOcclusion && this._facing(model, x, y, z) < 0) continue; // §2.1
      const p = this._project(mvp, x, y, z);
      if (!p) continue;
      const d = Math.hypot(p[0] - px, p[1] - py);
      if (d < bestD) { bestD = d; best = l; }
    }
    return best;
  }

  _hitTestMarked(clientX, clientY) {
    return this._hitTestPointList(clientX, clientY, this.markedLocations,
                                  "lat", "lon", 1.004);
  }

  _hitTestActors(clientX, clientY) {
    return this._hitTestPointList(clientX, clientY, this.actors,
                                  "base_lat", "base_lon", 1.005);
  }

  _pick(clientX, clientY) {
    const hit = this._hitTest(clientX, clientY);
    if (hit && hit._cluster) {
      // v5 §9 — zoom-only declustering has a hard ceiling: 75 events on one
      // city never separate even at max zoom. When a cluster is large or we're
      // already zoomed in, open its member list in the sliding pane (the
      // reliable path); otherwise zoom toward it to split (the nice-to-have).
      const nearMaxZoom = this.dist < 1.9;
      if (hit.count > 12 || nearMaxZoom) {
        this.onSelectCluster(hit);
      } else {
        this.flyTo(hit.lat, hit.lon, Math.max(1.5, this.dist * 0.55), 900);
      }
      return;
    }
    if (hit) { this.onSelectEvent(hit); return; }
    const actor = this.actorCount ? this._hitTestActors(clientX, clientY) : null;
    if (actor) { this.onSelectActor(actor); return; }
    const marked = this._hitTestMarked(clientX, clientY);
    if (marked) { this.onSelectLocation(marked); return; }
    // v6 §21 — clicking inside an NSA zone opens that actor's overview page
    const zone = this._hitTestZones(clientX, clientY);
    if (zone) { this.onSelectActor({ id: zone.nsa_id, name: zone.nsa_name }); return; }
    // v3 §13.3 — empty globe click resolves to a country (point-in-polygon
    // happens App-side against the vendored boundaries)
    const geo = this.screenToLatLon(clientX, clientY);
    if (geo) this.onCountryClick(geo.lat, geo.lon);
  }

  _hitTestZones(clientX, clientY) {
    // point-in-polygon over the zone outlines as drawn this frame
    if (!this._zoneScreenPolys || !this._zoneScreenPolys.length) return null;
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const px = (clientX - rect.left) * dpr, py = (clientY - rect.top) * dpr;
    for (const { pts, zone } of this._zoneScreenPolys) {
      let inside = false;
      for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        const [xi, yi] = pts[i], [xj, yj] = pts[j];
        if ((yi > py) !== (yj > py)
            && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside;
      }
      if (inside) return zone;
    }
    return null;
  }

  _updateHover(clientX, clientY) {
    const hit = this._hitTest(clientX, clientY);
    this.hoverId = hit ? hit.id : null;
    if (hit && hit._cluster) {
      this.canvas.style.cursor = "pointer";
      const rect = this.canvas.getBoundingClientRect();
      this.tip.style.display = "block";
      this.tip.style.left = (clientX - rect.left + 14) + "px";
      this.tip.style.top = (clientY - rect.top + 8) + "px";
      this.tip.innerHTML = `<b>${hit.count} events</b><br>` +
        `<span style="color:var(--text-dim)">click to zoom in and split</span>`;
      return;
    }
    if (!hit && this.actorCount) {
      const actor = this._hitTestActors(clientX, clientY);
      if (actor) {
        this.canvas.style.cursor = "pointer";
        const rect = this.canvas.getBoundingClientRect();
        this.tip.style.display = "block";
        this.tip.style.left = (clientX - rect.left + 14) + "px";
        this.tip.style.top = (clientY - rect.top + 8) + "px";
        this.tip.innerHTML = `<b>${(actor.name || "").replace(/</g, "&lt;")}</b><br>` +
          `<span style="color:var(--text-dim)">${actor.actor_type || "non-state actor"}` +
          ` · approximate operating area</span>`;
        return;
      }
    }
    if (!hit) {
      const marked = this._hitTestMarked(clientX, clientY);
      if (marked) {
        this.canvas.style.cursor = "pointer";
        const rect = this.canvas.getBoundingClientRect();
        this.tip.style.display = "block";
        this.tip.style.left = (clientX - rect.left + 14) + "px";
        this.tip.style.top = (clientY - rect.top + 8) + "px";
        this.tip.innerHTML = `<b>${(marked.name || "").replace(/</g, "&lt;")}</b><br>` +
          `<span style="color:var(--text-dim)">${marked.category.replace(/_/g, " ")}` +
          `${marked.description ? " · " + marked.description.replace(/</g, "&lt;").slice(0, 90) : ""}</span>`;
        return;
      }
    }
    this.canvas.style.cursor = hit ? "pointer" : "grab";
    if (hit) {
      const rect = this.canvas.getBoundingClientRect();
      this.tip.style.display = "block";
      this.tip.style.left = (clientX - rect.left + 14) + "px";
      this.tip.style.top = (clientY - rect.top + 8) + "px";
      const when = (hit.occurred_at || "").replace("T", " ").replace("Z", "");
      // v4 §3.1 — low-confidence geocodes say so instead of implying precision
      const approx = hit.geocode_confidence != null
        && hit.geocode_confidence < this.minConfSolid
        ? " · ≈ approximate location" : "";
      this.tip.innerHTML =
        `<b>${(hit.title || "").replace(/</g, "&lt;")}</b><br>` +
        `<span style="color:var(--text-dim)">${hit.location_name || "—"}${approx} · ` +
        `sev ${hit.severity} · ${when}${hit.story_id ? " · click to open" : ""}</span>`;
    } else {
      this.tip.style.display = "none";
    }
  }

  _resize() {
    const dpr = window.devicePixelRatio || 1;
    const w = this.host.clientWidth, h = this.host.clientHeight;
    this.canvas.width = Math.max(1, w * dpr);
    this.canvas.height = Math.max(1, h * dpr);
    this.canvas.style.width = w + "px";
    this.canvas.style.height = h + "px";
    this.overlay.width = this.canvas.width;
    this.overlay.height = this.canvas.height;
    if (this.quality === "ultra" && this._mkTarget) {
      const bw = Math.max(2, this.canvas.width >> 1), bh = Math.max(2, this.canvas.height >> 1);
      this.bloomTargets = {
        scene: this._mkTarget(this.canvas.width, this.canvas.height),
        a: this._mkTarget(bw, bh),
        b: this._mkTarget(bw, bh),
      };
      this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, null);
    }
  }

  // --- per-frame updates ---

  _updateCamera(now) {
    // v6.1 — WASD/QE held-key camera control (frame-rate independent via dt).
    // A key press cancels any running fly-to tween so control feels immediate.
    const dt = Math.min(0.05, (now - (this._lastCamNow || now)) / 1000);
    this._lastCamNow = now;
    if (this.keys && this._applyKeys(dt)) this.tween = null;
    if (this.tween) {
      const t = Math.min(1, (now - this.tween.start) / this.tween.duration);
      const k = easeInOut(t);
      this.yaw = this.tween.from.yaw + (this.tween.to.yaw - this.tween.from.yaw) * k;
      this.pitch = this.tween.from.pitch + (this.tween.to.pitch - this.tween.from.pitch) * k;
      this.dist = this.tween.from.dist + (this.tween.to.dist - this.tween.from.dist) * k;
      if (t >= 1) this.tween = null;
      return;
    }
    const idleMs = now - this.lastInteraction;
    // v6 §13 — autonomous motion is allowed ONLY via the idle-tour feature
    // (v2 §5.1), which must be explicitly enabled (idle_tour_seconds > 0)
    // and only after that much real inactivity. No other code path may
    // pan, rotate, or reset the camera on its own.
    const tourEnabled = this.idleTourSeconds > 0;
    if (tourEnabled && idleMs > this.idleTourSeconds * 1000 && this.rawEvents.length) {
      // §5.1 idle tour: hop between the most severe recent regions
      if (!this._nextTourAt || now >= this._nextTourAt) {
        const ranked = [...this.rawEvents].sort((a, b) =>
          (b.severity || 1) - (a.severity || 1) ||
          (b.occurred_at || "").localeCompare(a.occurred_at || ""));
        const target = ranked[this.tourIndex % Math.min(ranked.length, 8)];
        this.tourIndex += 1;
        this._nextTourAt = now + 9000;
        if (target) this.flyTo(target.lat, target.lon, 2.4, 2600);
      }
    } else if (tourEnabled && idleMs > this.idleTourSeconds * 1000) {
      // idle-tour window reached but no events yet: gentle rotate as the
      // tour's degenerate form — still gated on the same opt-in setting
      this.autoRotate = true;
    } else {
      this.autoRotate = false;
    }
    if (this.autoRotate) this.yaw += 0.0016;
    else {
      this.yaw += this.velYaw *= 0.94;
      this.pitch = Math.max(-1.35, Math.min(1.35, this.pitch + (this.velPitch *= 0.94)));
    }
  }

  // --- render ---

  _drawScene(time, mvp, model) {
    const gl = this.gl;
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    // starfield (high+)
    if (this.starBuf) {
      gl.useProgram(this.progPoint);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progPoint, "mvp"), false, mvp);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "time"), time * 0.12);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "dpr"), window.devicePixelRatio || 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.starBuf);
      this._pointAttribs(false);
      gl.depthMask(false);
      gl.drawArrays(gl.POINTS, 0, this.starCount);
      gl.depthMask(true);
    }

    // sphere with day/night + overlays
    gl.useProgram(this.progSphere);
    gl.uniformMatrix4fv(gl.getUniformLocation(this.progSphere, "mvp"), false, mvp);
    gl.uniformMatrix4fv(gl.getUniformLocation(this.progSphere, "model"), false, model);
    gl.uniform3fv(gl.getUniformLocation(this.progSphere, "sunDir"), this.sunDir);
    gl.uniform1f(gl.getUniformLocation(this.progSphere, "useHeat"), this.showHeatmap ? 1 : 0);
    // v5 §8 — terrain detail fades in only when enabled AND zoomed in (LOD:
    // real detail where the camera is, flat political coloring far away)
    const terr = this.terrainOn
      ? Math.max(0, Math.min(1, (2.6 - this.dist) / 1.0)) : 0;
    gl.uniform1f(gl.getUniformLocation(this.progSphere, "terrain"), terr);
    gl.uniform1f(gl.getUniformLocation(this.progSphere, "biomeReady"),
                 this.biomeReady ? 1 : 0);
    // v6.2 — theme-driven globe tint (default neutral = current teal look)
    const oc = this.oceanTint || [1, 1, 1];
    const rc = this.rimTint || [0.16, 0.38, 0.80];
    gl.uniform3f(gl.getUniformLocation(this.progSphere, "uOcean"), oc[0], oc[1], oc[2]);
    gl.uniform3f(gl.getUniformLocation(this.progSphere, "uRim"), rc[0], rc[1], rc[2]);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.heatTex);
    gl.uniform1i(gl.getUniformLocation(this.progSphere, "heatTex"), 0);
    gl.activeTexture(gl.TEXTURE1);                        // v6 §19
    gl.bindTexture(gl.TEXTURE_2D, this.biomeTex);
    gl.uniform1i(gl.getUniformLocation(this.progSphere, "biomeTex"), 1);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.sphereBuf);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
    gl.disableVertexAttribArray(1); gl.disableVertexAttribArray(2);
    gl.disableVertexAttribArray(3); gl.disableVertexAttribArray(4);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.sphereIdx);
    gl.drawElements(gl.TRIANGLES, this.sphereIdxCount, gl.UNSIGNED_INT, 0);

    // atmosphere fresnel halo (high+)
    if (this.quality !== "standard") {
      gl.useProgram(this.progHalo);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progHalo, "mvp"), false, mvp);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progHalo, "model"), false, model);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.haloBuf);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
      gl.enable(gl.CULL_FACE);
      gl.cullFace(gl.FRONT);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
      gl.depthMask(false);
      gl.drawElements(gl.TRIANGLES, this.sphereIdxCount, gl.UNSIGNED_INT, 0);
      gl.depthMask(true);
      gl.disable(gl.CULL_FACE);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }

    // graticule + coastlines
    gl.useProgram(this.progLine);
    const mvpLoc = gl.getUniformLocation(this.progLine, "mvp");
    const colLoc = gl.getUniformLocation(this.progLine, "color");
    gl.uniformMatrix4fv(mvpLoc, false, mvp);
    gl.uniformMatrix4fv(gl.getUniformLocation(this.progLine, "model"), false, model);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.gratBuf);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
    gl.uniform4f(colLoc, 0.25, 0.38, 0.62, 0.16);
    gl.drawArrays(gl.LINES, 0, this.gratCount);
    // v6 §7 — border/coastline resolution match: when country borders are on
    // (default), the 50m/10m boundary rings already trace every coastline at
    // the higher resolution, so drawing the coarse 110m coastline underneath
    // just paints a visible seam next to it. One layer at one resolution.
    if (!this.showBorders || !this.borderCount) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.coastBuf);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
      gl.uniform4f(colLoc, 0.42, 0.62, 0.9, 0.55);
      gl.drawArrays(gl.LINES, 0, this.coastCount);
    }

    // v4 §2.3/§5.4 — country borders (Natural Earth 50m/10m LOD), visible
    // by default with an explicit settings toggle to turn them off
    if (this.showBorders && this.borderCount) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.borderBuf);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
      gl.uniform4f(colLoc, 0.5, 0.6, 0.78, 0.34);
      gl.drawArrays(gl.LINES, 0, this.borderCount);
    }

    // v4 §5.3 — disputed boundaries: own toggle, visually distinct
    // (dashed, amber) so a disputed line never reads as settled
    if (this.showDisputes && this.disputeCount) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.disputeBuf);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
      gl.uniform4f(colLoc, 1.0, 0.72, 0.3, 0.85);
      gl.drawArrays(gl.LINES, 0, this.disputeCount);
    }

    // v3 §14 / v6 §7 §8 — colored boundary-ring overlays: any number of
    // groups at once (multi-select blocs, War Mode side coloring)
    for (const g of (this.ringGroups || [])) {
      gl.bindBuffer(gl.ARRAY_BUFFER, g.buf);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
      gl.uniform4f(colLoc, ...g.color, g.alpha);
      gl.drawArrays(gl.LINES, 0, g.count);
    }
    // v6 §26 — pulsing focus highlight (current-style animated border)
    if (this.highlightGroup) {
      const pulse = 0.45 + 0.45 * Math.sin(time * 3.2);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.highlightGroup.buf);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
      gl.uniform4f(colLoc, ...this.highlightGroup.color, 0.35 + pulse * 0.6);
      gl.drawArrays(gl.LINES, 0, this.highlightGroup.count);
    }

    // city lights on the night side (v6 §24 — user-toggleable, on by default)
    if (this.cityLightsOn !== false) {
      gl.useProgram(this.progCity);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progCity, "mvp"), false, mvp);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progCity, "model"), false, model);
      gl.uniform3fv(gl.getUniformLocation(this.progCity, "sunDir"), this.sunDir);
      gl.uniform1f(gl.getUniformLocation(this.progCity, "dpr"), window.devicePixelRatio || 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.cityBuf);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 16, 0);
      gl.enableVertexAttribArray(1);
      gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 16, 12);
      gl.disableVertexAttribArray(2); gl.disableVertexAttribArray(3);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
      gl.depthMask(false);
      gl.drawArrays(gl.POINTS, 0, this.cityCount);
      gl.depthMask(true);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }

    // correlation threads
    if (this.arcCount) {
      gl.useProgram(this.progArc);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progArc, "mvp"), false, mvp);
      gl.uniform1f(gl.getUniformLocation(this.progArc, "time"), time);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.arcBuf);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 16, 0);
      gl.enableVertexAttribArray(1);
      gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 16, 12);
      gl.depthMask(false);
      gl.drawArrays(gl.LINES, 0, this.arcCount);
      gl.depthMask(true);
    }

    // particle trails along threads (high+)
    if (this.trailCount && this.quality !== "standard") {
      gl.useProgram(this.progTrail);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progTrail, "mvp"), false, mvp);
      gl.uniform1f(gl.getUniformLocation(this.progTrail, "time"), time);
      gl.uniform1f(gl.getUniformLocation(this.progTrail, "dpr"), window.devicePixelRatio || 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.trailBuf);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 16, 0);
      gl.enableVertexAttribArray(1);
      gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 16, 12);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
      gl.depthMask(false);
      gl.drawArrays(gl.POINTS, 0, this.trailCount);
      gl.depthMask(true);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }

    // volumetric light pillars from significant events (ultra)
    if (this.beamCount && this.progBeam) {
      gl.useProgram(this.progBeam);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progBeam, "mvp"), false, mvp);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progBeam, "model"), false, model);
      // camera position in model space = R^T · (0,0,dist); R is pure rotation
      gl.uniform3f(gl.getUniformLocation(this.progBeam, "camPosModel"),
                   model[2] * this.dist, model[6] * this.dist, model[10] * this.dist);
      gl.uniform1f(gl.getUniformLocation(this.progBeam, "halfWidth"), 0.012);
      gl.uniform1f(gl.getUniformLocation(this.progBeam, "pulse"),
                   0.8 + 0.2 * Math.sin(time * 1.6));
      gl.bindBuffer(gl.ARRAY_BUFFER, this.beamBuf);
      for (let loc = 0; loc <= 5; loc++) gl.enableVertexAttribArray(loc);
      const S = 48;
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, S, 0);
      gl.vertexAttribPointer(1, 3, gl.FLOAT, false, S, 12);
      gl.vertexAttribPointer(2, 3, gl.FLOAT, false, S, 24);
      gl.vertexAttribPointer(3, 1, gl.FLOAT, false, S, 36);
      gl.vertexAttribPointer(4, 1, gl.FLOAT, false, S, 40);
      gl.vertexAttribPointer(5, 1, gl.FLOAT, false, S, 44);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
      gl.depthMask(false);
      gl.drawArrays(gl.TRIANGLES, 0, this.beamCount);
      gl.depthMask(true);
      for (let loc = 2; loc <= 5; loc++) gl.disableVertexAttribArray(loc);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }

    // v3 §17 — marked locations (fixed markers, no pulse: phase attr = 0)
    if (this.markedCount) {
      gl.useProgram(this.progPoint);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progPoint, "mvp"), false, mvp);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "time"), 0);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "dpr"), window.devicePixelRatio || 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.markedBuf);
      this._pointAttribs(true);
      gl.depthMask(false);
      gl.drawArrays(gl.POINTS, 0, this.markedCount);
      gl.depthMask(true);
    }

    // v4 §5.4 — non-state actor markers (own toggle, approximate centroids)
    if (this.actorCount) {
      gl.useProgram(this.progPoint);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progPoint, "mvp"), false, mvp);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "time"), time * 0.4);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "dpr"), window.devicePixelRatio || 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.actorBuf);
      this._pointAttribs(true);
      gl.depthMask(false);
      gl.drawArrays(gl.POINTS, 0, this.actorCount);
      gl.depthMask(true);
    }

    // v3 §10.2 — satellites at altitude (visually distinct from ground pins)
    if (this.satCount) {
      gl.useProgram(this.progPoint);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progPoint, "mvp"), false, mvp);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "time"), 0);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "dpr"), window.devicePixelRatio || 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.satBuf);
      this._pointAttribs(true);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
      gl.depthMask(false);
      gl.drawArrays(gl.POINTS, 0, this.satCount);
      gl.depthMask(true);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }

    // event particles
    if (this.pointCount) {
      gl.useProgram(this.progPoint);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progPoint, "mvp"), false, mvp);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "time"), time);
      gl.uniform1f(gl.getUniformLocation(this.progPoint, "dpr"), window.devicePixelRatio || 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.pointBuf);
      this._pointAttribs(true);
      gl.depthMask(false);
      gl.drawArrays(gl.POINTS, 0, this.pointCount);
      gl.depthMask(true);
    }

    // live bursts (§5.1)
    if (this.burstCount) {
      gl.useProgram(this.progBurst);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.progBurst, "mvp"), false, mvp);
      gl.uniform1f(gl.getUniformLocation(this.progBurst, "time"), time);
      gl.uniform1f(gl.getUniformLocation(this.progBurst, "dpr"), window.devicePixelRatio || 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.burstBuf);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 28, 0);
      gl.enableVertexAttribArray(1);
      gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 28, 12);
      gl.enableVertexAttribArray(2);
      gl.vertexAttribPointer(2, 3, gl.FLOAT, false, 28, 16);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
      gl.depthMask(false);
      gl.drawArrays(gl.POINTS, 0, this.burstCount);
      gl.depthMask(true);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }
  }

  _pointAttribs(withBright) {
    const gl = this.gl;
    const stride = withBright ? 36 : 32;
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, stride, 0);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 3, gl.FLOAT, false, stride, 12);
    gl.enableVertexAttribArray(2);
    gl.vertexAttribPointer(2, 1, gl.FLOAT, false, stride, 24);
    gl.enableVertexAttribArray(3);
    gl.vertexAttribPointer(3, 1, gl.FLOAT, false, stride, 28);
    if (withBright) {
      gl.enableVertexAttribArray(4);
      gl.vertexAttribPointer(4, 1, gl.FLOAT, false, stride, 32);
    } else {
      gl.disableVertexAttribArray(4);
      gl.vertexAttrib1f(4, 1.0);
    }
  }

  _postQuad(prog, srcTex, target, extra) {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, target ? target.fbo : null);
    gl.viewport(0, 0, target ? target.w : this.canvas.width,
                target ? target.h : this.canvas.height);
    gl.useProgram(prog);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, srcTex);
    gl.uniform1i(gl.getUniformLocation(prog, "tex"), 0);
    if (extra) extra(prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    for (const i of [1, 2, 3, 4]) gl.disableVertexAttribArray(i);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  _frame(tNow) {
    if (this.destroyed) return;
    const gl = this.gl;
    const time = (tNow - this._t0) / 1000;
    this.sunDir = new Float32Array(sunDirection());
    this._updateCamera(tNow);
    const { mvp, model } = this._mvp();

    // v4 §2.2 — continuous declustering: recompute clusters when the
    // camera distance moves enough to change screen-space separation
    if (this.rawEvents.length &&
        Math.abs(this.dist - this._lastClusterDist) / (this._lastClusterDist || 1) > 0.06) {
      this._recluster();
    }
    // v4 §2.3 — boundary LOD: accurate 10m lines up close, 50m for the
    // full-globe view where sub-km accuracy is invisible
    this._ensureBoundaryLod(this.dist < 2.05 ? "10m" : "50m");

    const bloom = this.quality === "ultra" && this.bloomTargets;
    if (bloom) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, this.bloomTargets.scene.fbo);
    } else {
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    }
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    this._drawScene(time, mvp, model);

    if (bloom) {
      const { scene, a, b } = this.bloomTargets;
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.BLEND);
      this._postQuad(this.progBright, scene.tex, a);
      this._postQuad(this.progBlur, a.tex, b, (p) =>
        gl.uniform2f(gl.getUniformLocation(p, "dir"), 1.6 / a.w, 0));
      this._postQuad(this.progBlur, b.tex, a, (p) =>
        gl.uniform2f(gl.getUniformLocation(p, "dir"), 0, 1.6 / a.h));
      // composite: scene + additive blurred highlights
      this._postQuad(this.progComposite, scene.tex, null);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE);
      this._postQuad(this.progComposite, a.tex, null);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }

    this._drawOverlay(mvp, model);
    requestAnimationFrame((t) => this._frame(t));
  }

  // v4 §2.2 cluster counts + §4.3 population-tiered city labels, drawn on
  // the 2D overlay canvas (text over WebGL, pointer-transparent)
  // project one lon/lat-flat or pair ring to screen; null when mostly backfacing
  _projectRing(ring, model, mvp, radius, pairs) {
    const pts = [];
    let facing = 0;
    const n = pairs ? ring.length : ring.length / 2;
    for (let i = 0; i < n; i++) {
      const lon = pairs ? ring[i][0] : ring[i * 2];
      const lat = pairs ? ring[i][1] : ring[i * 2 + 1];
      const [x, y, zz] = latLonToVec3(lat, lon, radius);
      if (this._facing(model, x, y, zz) > 0) facing++;
      const p = this._project(mvp, x, y, zz);
      if (!p) return null;
      pts.push(p);
    }
    return facing >= n * 0.6 ? pts : null;
  }

  _drawOverlay(mvp, model) {
    const ctx = this.octx;
    const dpr = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);
    const nowT = performance.now() / 1000;

    // v6 §16 — thematic choropleth: fill each country's boundary rings with
    // its metric color, projected in screen space over the same boundary
    // data the base map uses (shapes stay consistent across modes)
    if (this.choropleth && this._b50mData) {
      for (const c of this._b50mData) {
        const color = this.choropleth[c.i];
        if (!color) continue;
        ctx.fillStyle = color;
        for (const ring of c.r) {
          if (ring.length < 8) continue;
          const pts = this._projectRing(ring, model, mvp, 1.002, false);
          if (!pts) continue;
          ctx.beginPath();
          pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
          ctx.closePath();
          ctx.fill();
        }
      }
    }

    // v5 §11 / v6 §21 — NSA territory zones: actual shaped polygons rendered
    // as a PULSING dotted rough-boundary (never solid rectangles). Drawn only
    // when a majority of the ring faces the camera, so a zone on the far
    // side doesn't smear across the silhouette. Clickable (→ actor page).
    const ZONE_COL = { established: "242,89,140", contested: "255,180,80",
                       reported: "150,150,170" };
    this._zoneScreenPolys = [];
    for (const z of (this.actorZones || [])) {
      const ring = (z.geojson && z.geojson.coordinates && z.geojson.coordinates[0]) || [];
      if (ring.length < 3) continue;
      const pts = this._projectRing(ring, model, mvp, 1.004, true);
      if (!pts) continue;
      const col = ZONE_COL[z.confidence] || ZONE_COL.reported;
      const pulse = 0.55 + 0.35 * Math.sin(nowT * 2.1 + (z.nsa_id || "").length);
      // v6.1 — render the zone as a techno DOT-FIELD (pulsing stipple) filling
      // its shape, not an outlined polygon that reads as an "ugly rectangle".
      // A very faint fill keeps the silhouette; the dots carry the look.
      ctx.beginPath();
      pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
      ctx.closePath();
      ctx.fillStyle = `rgba(${col},${(0.05 + 0.04 * pulse).toFixed(3)})`;
      ctx.fill();
      // bbox of the screen polygon → sample a jittered grid → keep inside points
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const p of pts) {
        minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]);
        minY = Math.min(minY, p[1]); maxY = Math.max(maxY, p[1]);
      }
      const step = 13 * dpr;   // dot spacing in device px
      const pip = (x, y) => {
        let inside = false;
        for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
          const xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
          if (((yi > y) !== (yj > y)) &&
              (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-9) + xi)) inside = !inside;
        }
        return inside;
      };
      for (let gy = minY; gy <= maxY; gy += step) {
        for (let gx = minX; gx <= maxX; gx += step) {
          const jx = gx + Math.sin((gx + gy) * 0.7) * step * 0.28;
          const jy = gy + Math.cos((gx - gy) * 0.7) * step * 0.28;
          if (!pip(jx, jy)) continue;
          // per-dot phase → shimmering "scan" pulse across the field
          const ph = 0.5 + 0.5 * Math.sin(nowT * 3.0 + (jx + jy) * 0.02);
          ctx.beginPath();
          ctx.arc(jx, jy, (1.1 + 1.0 * ph) * dpr, 0, 7);
          ctx.fillStyle = `rgba(${col},${(0.35 + 0.5 * ph).toFixed(3)})`;
          ctx.fill();
        }
      }
      this._zoneScreenPolys.push({ pts, zone: z });
    }

    const HEX = { geopolitics: "#4da3ff", finance: "#ffd166", disaster: "#ff6b6b",
                  conflict: "#ff8c42", military: "#4acc73", other: "#93a1b8" };
    for (const c of this.clusters) {
      const [x, y, z] = latLonToVec3(c.lat, c.lon, 1.006);
      if (this._facing(model, x, y, z) < 0.02) continue;
      const p = this._project(mvp, x, y, z);
      if (!p) continue;
      const r = this._clusterRadiusPx(c.count);
      const color = HEX[c.category] || HEX.other;
      ctx.beginPath();
      ctx.arc(p[0], p[1], r, 0, 7);
      ctx.fillStyle = "rgba(10,14,23,0.72)";
      ctx.fill();
      ctx.lineWidth = 1.6 * dpr;
      ctx.strokeStyle = color;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(p[0], p[1], r * 0.55, 0, 7);
      ctx.fillStyle = color + "33";
      ctx.fill();
      ctx.font = `bold ${11 * dpr}px system-ui`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#e8eefb";
      ctx.fillText(String(c.count), p[0], p[1]);
    }

    // v6.1.1 — dynamic country labels, gated on apparent screen size + v6.2 toggle
    if (this.countryLabelsOn !== false && this.countryLabels && this.countryLabels.length) {
      const placed = [];
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (const l of this.countryLabels) {
        const [x, y, z] = latLonToVec3(l.lat, l.lon, 1.002);
        if (this._facing(model, x, y, z) < 0.15) continue;
        const p = this._project(mvp, x, y, z);
        if (!p) continue;
        // apparent width: project a second point ~span° east and measure px
        const [x2, y2, z2] = latLonToVec3(l.lat, l.lon + (l.span || 4), 1.002);
        const p2 = this._project(mvp, x2, y2, z2);
        if (!p2) continue;
        const apparentPx = Math.hypot(p2[0] - p[0], p2[1] - p[1]);
        // v6.2 — small island nations (span < ~4°) are near-invisible dots on
        // the map: give them an always-on marker so they actually EXIST, and
        // a label once you zoom in a bit. Without this Mauritius/Comoros/etc.
        // were unfindable.
        const isSmall = (l.span || 0) < 4;
        if (isSmall && apparentPx < 34 * dpr) {
          if (p[0] >= 0 && p[0] <= this.overlay.width && p[1] >= 0 && p[1] <= this.overlay.height && this.dist < 3.1) {
            ctx.beginPath();
            ctx.arc(p[0], p[1], 2.2 * dpr, 0, 7);
            ctx.fillStyle = "rgba(180,200,235,0.55)";
            ctx.fill();
            if (this.dist < 2.2) {   // show the name when zoomed toward it
              ctx.font = `600 ${10 * dpr}px system-ui`;
              ctx.fillStyle = "rgba(210,222,240,0.7)";
              ctx.strokeStyle = "rgba(6,10,18,0.6)"; ctx.lineWidth = 3 * dpr;
              ctx.strokeText(l.name, p[0], p[1] - 8 * dpr);
              ctx.fillText(l.name, p[0], p[1] - 8 * dpr);
            }
          }
          continue;
        }
        // reveal once the country spans ~46px on screen; fade over the next 30
        if (apparentPx < 46 * dpr) continue;
        const alpha = Math.min(0.82, 0.2 + (apparentPx - 46 * dpr) / (30 * dpr) * 0.62);
        if (p[0] < 0 || p[0] > this.overlay.width || p[1] < 0 || p[1] > this.overlay.height) continue;
        let collide = false;
        for (const q of placed) {
          if (Math.abs(q[0] - p[0]) < 70 * dpr && Math.abs(q[1] - p[1]) < 16 * dpr) { collide = true; break; }
        }
        if (collide) continue;
        placed.push(p);
        const fs = Math.max(10, Math.min(16, apparentPx / 9)) * dpr;
        ctx.font = `600 ${fs}px system-ui`;
        ctx.fillStyle = `rgba(225,232,246,${alpha.toFixed(2)})`;
        ctx.strokeStyle = `rgba(6,10,18,${(alpha * 0.7).toFixed(2)})`;
        ctx.lineWidth = 3 * dpr;
        ctx.strokeText(l.name, p[0], p[1]);
        ctx.fillText(l.name, p[0], p[1]);
      }
    }

    if (this.cities.length && this.dist < 3.4) {
      // §4.3 — population tier widens as the camera closes in, and label
      // density is screen-space bounded so dense regions don't flood
      const minPop = this.dist > 2.4 ? 5000000 : this.dist > 1.8 ? 500000 : 50000;
      const placed = [];
      const maxLabels = 46;
      ctx.font = `${10.5 * dpr}px system-ui`;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      for (const c of this.cities) {            // already sorted by population
        if (placed.length >= maxLabels) break;
        if (c.population < minPop) continue;
        const [x, y, z] = latLonToVec3(c.lat, c.lon, 1.002);
        if (this._facing(model, x, y, z) < 0.12) continue;
        const p = this._project(mvp, x, y, z);
        if (!p || p[0] < 0 || p[0] > this.overlay.width
            || p[1] < 0 || p[1] > this.overlay.height) continue;
        let collide = false;
        for (const q of placed) {
          if (Math.abs(q[0] - p[0]) < 90 * dpr && Math.abs(q[1] - p[1]) < 14 * dpr) {
            collide = true; break;
          }
        }
        if (collide) continue;
        placed.push(p);
        ctx.fillStyle = "rgba(219,228,245,0.28)";
        ctx.beginPath();
        ctx.arc(p[0], p[1], 1.6 * dpr, 0, 7);
        ctx.fill();
        ctx.fillStyle = c.population >= 5000000
          ? "rgba(219,228,245,0.75)" : "rgba(160,178,208,0.6)";
        ctx.fillText(c.name, p[0] + 4 * dpr, p[1]);
      }
    }
  }
}
