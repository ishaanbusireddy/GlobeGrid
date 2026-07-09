// Tier 2 — flat 2D map (v1 Section 11.1, overhauled in v4 §4): a literal
// flat version of the globe, not a lesser sibling. Every globe toggle has
// its identical counterpart here, reading the identical backend data:
// country borders (Natural Earth 50m/10m LOD, on by default), disputed
// boundaries (dashed, own toggle), alliance tint, marked locations,
// non-state actors, satellites, heatmap, clustered pins, and the
// Paradox-style population-tiered city labels (§4.3). East-west
// wraparound (§4.2): three horizontally-tiled copies rendered around the
// view with the pan snapped back by 360° at tile boundaries — no seam,
// and interactive layers hit-test in all three tiles.
import { BOUNDARIES_50M_ENC } from "../../data/boundaries50m.js";
import { DISPUTED_BOUNDARIES_ENC } from "../../data/disputedBoundaries.js";
import { decodeBoundaries } from "../../data/boundaryCodec.js";

const CATEGORY_COLORS = {
  geopolitics: "#4da3ff", finance: "#ffd166", technology: "#b26bff",   // v6.6.2 tech
  disaster: "#ff6b6b", conflict: "#ff8c42", military: "#4acc73", other: "#93a1b8",
  domestic: "#e6935c", health: "#35c88a",                              // v8.13
};
const MARKED_COLORS = {
  capital: "#8d9cbf", strategic_chokepoint: "#59e6f2", contested_territory: "#ff9e59",
  conflict_zone: "#ff6b6b", semiconductor_fab: "#99ff99", rare_earth_site: "#d9bf80",
  undersea_cable: "#80ccff", energy_pipeline: "#ffd966", lng_terminal: "#ffb3d9",
  other: "#b3b3b3",
  // v7.1 §5 — physical sensor layer (ground-truth fusion)
  sensor_firms: "#ff7043", sensor_opensky: "#4fc3f7",
  sensor_usgs: "#ffca28", sensor_acled: "#ef5350",
  sensor_ais: "#26c6da", sensor_nightlights: "#ab47bc",
};

export class Tier2Map {
  constructor(host, { onSelectEvent, onSelectLocation, onCountryClick, onSelectActor,
                      onSelectCity, wraparound = true, minConfidenceSolid = 0.6,
                      countryAt = null } = {}) {
    this.host = host;
    this.onSelectEvent = onSelectEvent || (() => {});
    this.onSelectLocation = onSelectLocation || (() => {});
    this.onCountryClick = onCountryClick || (() => {});
    this.onSelectActor = onSelectActor || (() => {});
    this.onSelectCity = onSelectCity || (() => {});   // v8.8 — city chip click
    this._cityScreens = [];                            // v8.8 — drawn city hit-boxes
    this.zoomSensitivity = 1;                          // v8.9 — mouse-wheel zoom sensitivity
    this.panSensitivity = 1;                           // v8.13 — drag/WASD pan (x+y together) sensitivity
    this.countryAt = countryAt;
    this.wraparound = wraparound;
    this.minConfSolid = minConfidenceSolid;
    this.canvas = document.createElement("canvas");
    host.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d");
    this.tip = document.createElement("div");
    this.tip.id = "map-tip";
    host.appendChild(this.tip);

    this.events = [];
    this.clusterCfg = { cluster_pin_threshold: 15, cluster_radius_km: 300 };
    this.zoom = 1; this.panX = 0; this.panY = 0;
    this.clusters = [];
    this.destroyed = false;

    // v4 parity layers
    this.showBorders = true;
    this.showDisputes = false;
    this.showHeatmap = false;
    this.markedLocations = [];
    this.actors = [];
    this.actorZones = [];   // v5 §11
    this.autonomousZones = [];   // v7.6 — always-on dotted borders (like territories)
    this.adminRings = [];        // v8 §3 — ADM1 province borders (flat rings, zoom-gated)
    this.admin2Rings = [];       // v8.1 — ADM2 district/county borders (deeper gate)
    this.admin3Rings = [];       // v8.2 — ADM3 sub-district borders (deepest gate)
    this.showAdmin = false;
    this.adminVis = [false, false, false];   // v8.8 — per-tier (div1/div2/div3) visibility
    this.satellites = [];
    this.cities = [];
    this.allianceRings = null;
    this.allianceColor = "#4da3ff";
    this.b50 = decodeBoundaries(BOUNDARIES_50M_ENC);
    this.b10 = null;         // lazily decoded on zoom-in (§2.3 LOD)
    this.disputed = decodeBoundaries(DISPUTED_BOUNDARIES_ENC);
    // v6.6.7 — append the Antarctic claim-sector meridians so they render as
    // disputed lines on the 2D map too (parity with the globe).
    for (const lon of [-150, -90, -20, 45, 136, 142, 160]) {
      const ring = [];
      for (let lat = -88; lat <= -63; lat += 1.2) ring.push(lon, lat);
      this.disputed.push({ a: "", b: "", n: "Antarctic sector", r: [ring] });
    }
    // v6.6.9 — Zaporizhzhia/Kherson front-line approximations + a Falklands
    // outline ring (owner: "add line borders for zaporizhzhia, kherson, and
    // falklands"), same data as the globe renderer.
    const extraDisputed = [
      [34.8, 47.55, 35.6, 47.35, 36.4, 47.4, 37.2, 47.5, 37.9, 47.7],
      [31.7, 46.4, 32.6, 46.55, 32.6, 46.65, 33.37, 46.75, 34.0, 46.85, 34.4, 47.0],
      [-61.3, -51.05, -59.3, -50.95, -57.6, -51.25, -58.0, -52.35,
       -59.8, -52.15, -61.0, -51.75, -61.3, -51.05],
    ];
    const extraNames = ["Zaporizhzhia front line", "Kherson front line", "Falkland Islands"];
    extraDisputed.forEach((ring, i) =>
      this.disputed.push({ a: "", b: "", n: extraNames[i], r: [ring] }));

    this._initInteraction();
    this._resizeObserver = new ResizeObserver(() => { this._resize(); this.draw(); });
    this._resizeObserver.observe(host);
    this._resize();
  }

  destroy() {
    this.destroyed = true;
    this._resizeObserver.disconnect();
    this.canvas.remove();
    this.tip.remove();
  }

  setData({ events = [], cluster_config }) {
    this.events = events.filter((e) => e.lat != null && e.lon != null);
    if (cluster_config) this.clusterCfg = cluster_config;
    this.draw();
  }

  // identical toggles to the globe (§4.1)
  setHeatmap(on) { this.showHeatmap = on; this.draw(); }
  setBorders(on) { this.showBorders = !!on; this.draw(); }
  setDisputes(on) { this.showDisputes = !!on; this.draw(); }
  setMarkedLocations(locs) {
    this.markedLocations = (locs || []).filter((l) => l.lat != null);
    this.draw();
  }
  setActors(actors) {
    this.actors = (actors || []).filter((a) => a.base_lat != null);
    this.draw();
  }
  setActorZones(zones) { this.actorZones = zones || []; this.draw(); }   // v5 §11
  // v7.6 — autonomous-region outlines as always-on DOTTED borders (owner: shown
  // like territories by default, but slightly dotted). Each zone → a flat ring.
  setAutonomousZones(zones) {
    this.autonomousZones = (zones || [])
      .filter((z) => Array.isArray(z.outline) && z.outline.length > 2)
      .map((z) => ({ name: z.name, ring: z.outline.flatMap(([lon, lat]) => [lon, lat]) }));
    this.draw();
  }
  // v8 §3 — real ADM1 (province) borders: a flat list of [lon,lat,…] rings,
  // drawn only when the layer is toggled on AND zoomed in (gate in draw()).
  setAdminBoundaries(rings) { this.adminRings = rings || []; this.draw(); }
  setAdmin2Boundaries(rings) { this.admin2Rings = rings || []; this.draw(); }   // v8.1
  setAdmin3Boundaries(rings) { this.admin3Rings = rings || []; this.draw(); }   // v8.2
  // v8.4 — real historical world borders overlaid for a past as_of epoch:
  // a flat list of [lon,lat,…] rings, drawn (ungated) in amber when set.
  setHistoricalBoundaries(rings) { this.histRings = rings || null; this.draw(); }   // v8.4
  setAdminVisible(on) { this.showAdmin = !!on; this.adminVis = [!!on, !!on, !!on]; this.draw(); }
  // v8.8 — per-tier visibility so div1/div2/div3 toggle independently.
  setAdminLayerVisible(level, on) {
    if (!this.adminVis) this.adminVis = [false, false, false];
    this.adminVis[level - 1] = !!on; this.draw();
  }
  setSatellites(sats) { this.satellites = sats || []; this.draw(); }
  setZoomSensitivity(s) { this.zoomSensitivity = Math.max(0.2, Math.min(4, +s || 1)); }   // v8.9
  setPanSensitivity(s) { this.panSensitivity = Math.max(0.2, Math.min(4, +s || 1)); }     // v8.13
  setCities(cities) { this.cities = cities || []; this.draw(); }
  // v6.1.1 — dynamic country labels, revealed by apparent on-screen size
  setCountryLabels(labels) { this.countryLabels = labels || []; this.draw(); }
  setCountryLabelsVisible(on) { this.countryLabelsOn = on !== false; this.draw(); }  // v6.2
  // v6.2 — theme-driven map colours (coastline + graticule), pushed by App
  // from the active theme's --map-land / --map-grid CSS variables.
  setThemeColors(landStroke, gridStroke) {
    if (landStroke) this.landStroke = landStroke;
    if (gridStroke) this.gridStroke = gridStroke;
    if (!this.destroyed) this.draw();
  }
  setAllianceOverlay(rings, colorRgb) {
    this.allianceRings = rings && rings.length ? rings : null;
    if (colorRgb) {
      this.allianceColor = `rgb(${colorRgb.map((c) => Math.round(c * 255)).join(",")})`;
    }
    this.draw();
  }

  // v6 §7/§8 — parity with the globe: any number of colored ring groups at
  // once (multi-select blocs, War Mode side coloring)
  setColoredRings(groups) {
    this.ringGroups = (groups || []).map((g) => ({
      rings: g.rings || [],
      color: `rgba(${(g.color || [0.4, 0.75, 1]).map((c) => Math.round(c * 255)).join(",")},${g.alpha != null ? g.alpha : 0.9})`,
    }));
    this.draw();
  }

  // v6 §26 — pulsing focus highlight; runs a small rAF loop only while active
  setHighlight(rings, colorRgb) {
    this.highlightRings = rings && rings.length ? rings : null;
    this.highlightColor = colorRgb || [1.0, 0.72, 0.18];   // v6.2 — orange/gold
    if (this.highlightRings && !this._pulseRaf) {
      const tick = () => {
        if (!this.highlightRings || this.destroyed) { this._pulseRaf = null; return; }
        this.draw();
        this._pulseRaf = requestAnimationFrame(tick);
      };
      this._pulseRaf = requestAnimationFrame(tick);
    }
    if (!this.highlightRings) this.draw();
  }

  // v6 §16 — thematic choropleth fill ({iso3: cssColor} or null)
  setChoropleth(colorsByIso3) { this.choropleth = colorsByIso3 || null; this.draw(); }
  // v8.3 — Hotspots heat: fill only active admin units. cells=[{rings,color}]
  setAdminHeat(cells) { this.adminHeat = cells || null; this.draw(); }

  setCityLights() {}   // no night-side lights on the flat map — API parity no-op
  setTerrain() {}

  // v6 §6 — events inside a screen-space rectangle (client px)
  eventsInRect(x0, y0, x1, y1) {
    const rect = this.canvas.getBoundingClientRect();
    const [loX, hiX] = [Math.min(x0, x1) - rect.left, Math.max(x0, x1) - rect.left];
    const [loY, hiY] = [Math.min(y0, y1) - rect.top, Math.max(y0, y1) - rect.top];
    const tiles = this._tiles();
    const out = [];
    for (const e of this.events) {
      const [px, py] = this._project(e.lat, e.lon);
      for (const off of tiles) {
        if (px + off >= loX && px + off <= hiX && py >= loY && py <= hiY) {
          out.push(e);
          break;
        }
      }
    }
    return out;
  }

  flyTo(lat, lon) {
    this.zoom = Math.max(this.zoom, 3);
    const [px, py] = this._project(lat, lon);
    this.panX += this.host.clientWidth / 2 - px;
    this.panY += this.host.clientHeight / 2 - py;
    this._snapPan();
    this.draw();
  }

  _resize() {
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.max(1, this.host.clientWidth * dpr);
    this.canvas.height = Math.max(1, this.host.clientHeight * dpr);
    this.canvas.style.width = this.host.clientWidth + "px";
    this.canvas.style.height = this.host.clientHeight + "px";
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  _scale() {
    const w = this.host.clientWidth, h = this.host.clientHeight;
    return Math.min(w / 360, h / 180) * this.zoom;
  }

  _project(lat, lon) {
    const w = this.host.clientWidth, h = this.host.clientHeight;
    const scale = this._scale();
    const cx = w / 2 + this.panX, cy = h / 2 + this.panY;
    return [cx + lon * scale, cy - lat * scale];
  }

  _unproject(x, y) {
    const w = this.host.clientWidth, h = this.host.clientHeight;
    const scale = this._scale();
    let lon = (x - (w / 2 + this.panX)) / scale;
    const lat = ((h / 2 + this.panY) - y) / scale;
    lon = ((lon + 540) % 360) - 180;   // wraparound tiles fold back (§4.2)
    return { lat, lon };
  }

  // v6.1.1 — screen(client) → lat/lon, parity with the globe for hover lookups
  screenToLatLon(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    const g = this._unproject(clientX - rect.left, clientY - rect.top);
    return (g.lat >= -90 && g.lat <= 90) ? g : null;
  }

  // §4.2 — the world repeats east-west; snap the coordinate space back by
  // 360° of longitude whenever the pan crosses a tile boundary
  _snapPan() {
    if (!this.wraparound) return;
    const world = 360 * this._scale();
    if (this.panX > world / 2) this.panX -= world;
    if (this.panX < -world / 2) this.panX += world;
  }

  // x-offsets (in px) of the world copies that intersect the viewport
  _tiles() {
    if (!this.wraparound) return [0];
    const world = 360 * this._scale();
    const w = this.host.clientWidth;
    // v5 §12 — defer/skip wraparound tiles: only include an east/west repeat
    // copy when it actually intersects the viewport, instead of eagerly
    // rendering all three copies on every draw regardless of view.
    const out = [0];
    // east copy visible if its left edge is on-screen
    if (this.panX + world / 2 < w) out.push(world);
    // west copy visible if its right edge is on-screen
    if (this.panX - world / 2 > 0) out.push(-world);
    return out;
  }

  // v5 §12 — the lon/lat rectangle currently visible (with margin), used to
  // cull off-screen geometry before drawing it
  _visibleBounds(w, h) {
    const a = this._unproject(-40, -40);
    const b = this._unproject(w + 40, h + 40);
    return {
      minLon: Math.min(a.lon, b.lon) - 5, maxLon: Math.max(a.lon, b.lon) + 5,
      minLat: Math.min(a.lat, b.lat) - 5, maxLat: Math.max(a.lat, b.lat) + 5,
    };
  }

  _bboxVisible(bb) {
    // wraparound: a country crossing the antimeridian (wide bbox) is always
    // considered potentially visible rather than risk culling it wrongly
    const vb = this._vb;
    if (!vb || !bb) return true;
    if (bb[2] - bb[0] > 180) return bb[3] >= vb.minLat && bb[1] <= vb.maxLat;
    return bb[3] >= vb.minLat && bb[1] <= vb.maxLat
        && bb[2] >= vb.minLon && bb[0] <= vb.maxLon;
  }

  _drawRings(rings, offset, stroke, width, dashed = false, pattern = [5, 4]) {
    const ctx = this.ctx;
    ctx.strokeStyle = stroke;
    ctx.lineWidth = width;
    if (dashed) ctx.setLineDash(pattern);
    for (const ring of rings) {
      ctx.beginPath();
      let started = false, prevX = 0;
      for (let i = 0; i + 1 < ring.length; i += 2) {
        const [x, y] = this._project(ring[i + 1], ring[i]);
        const xx = x + offset;
        // antimeridian-crossing segments would streak across the map
        if (started && Math.abs(xx - prevX) > 180 * this._scale()) started = false;
        if (!started) { ctx.moveTo(xx, y); started = true; }
        else ctx.lineTo(xx, y);
        prevX = xx;
      }
      ctx.stroke();
    }
    if (dashed) ctx.setLineDash([]);
  }

  _boundaries() {
    // §2.3 LOD: 10m once zoomed in enough that the accuracy is visible
    if (this.zoom >= 3.2) {
      if (this.b10) return this.b10;
      if (!this._b10Loading) {
        this._b10Loading = true;
        import("../../data/boundaries10m.js").then((m) => {
          this.b10 = decodeBoundaries(m.BOUNDARIES_10M_ENC);
          this._b10Loading = false;
          this.draw();
        }).catch(() => { this._b10Loading = false; });
      }
    }
    return this.b50;
  }

  // ----- v6 §18 — real tile-based boundary rendering -----
  // The v5 approach still projected every vertex of every visible country in
  // JS on every draw (the 10m dataset is hundreds of thousands of vertices —
  // that's the lag). This is the actual fix, not a tuning pass: geometry is
  // chunked ONCE per dataset into fixed-size lon/lat tiles, each tile's
  // segments baked into a native Path2D in lon/lat space. A draw then just
  // strokes the Path2Ds of the tiles intersecting the viewport under a canvas
  // affine transform — zero per-vertex JavaScript per frame.
  _tileGrid(data, sizeDeg) {
    const tiles = new Map();   // "tx:ty" -> Path2D
    const add = (tx, ty, x1, y1, x2, y2) => {
      const key = tx + ":" + ty;
      let p = tiles.get(key);
      if (!p) { p = new Path2D(); tiles.set(key, p); }
      p.moveTo(x1, y1); p.lineTo(x2, y2);
    };
    for (const c of data) {
      for (const ring of c.r) {
        for (let i = 0; i + 3 < ring.length; i += 2) {
          const x1 = ring[i], y1 = ring[i + 1], x2 = ring[i + 2], y2 = ring[i + 3];
          if (Math.abs(x2 - x1) > 180) continue;      // antimeridian wrap segment
          const tx = Math.floor(((x1 + x2) / 2 + 180) / sizeDeg);
          const ty = Math.floor((90 - (y1 + y2) / 2) / sizeDeg);
          add(tx, ty, x1, y1, x2, y2);
        }
      }
    }
    return tiles;
  }

  _tileSize() { return this._tileSizeDeg || 30; }
  setTileSize(deg) { this._tileSizeDeg = Math.max(1, Math.min(90, deg || 30)); }

  _tilesFor(data, which) {
    const cacheKey = "_tileCache_" + which;
    if (!this[cacheKey]) this[cacheKey] = this._tileGrid(data, this._tileSize());
    return this[cacheKey];
  }

  // stroke the boundary tiles intersecting the viewport under an affine
  // lon/lat -> screen transform (native path stroking, no JS projection)
  _strokeBoundaryTiles(data, which, off, stroke, width) {
    const ctx = this.ctx;
    const dpr = window.devicePixelRatio || 1;
    const scale = this._scale();
    const w = this.host.clientWidth, h = this.host.clientHeight;
    const grid = this._tilesFor(data, which);
    const size = this._tileSize();
    const vb = this._vb;
    const tx0 = Math.max(0, Math.floor((vb.minLon + 180) / size));
    const tx1 = Math.min(Math.ceil(360 / size) - 1, Math.floor((vb.maxLon + 180) / size));
    const ty0 = Math.max(0, Math.floor((90 - vb.maxLat) / size));
    const ty1 = Math.min(Math.ceil(180 / size) - 1, Math.floor((90 - vb.minLat) / size));
    ctx.save();
    ctx.setTransform(scale * dpr, 0, 0, -scale * dpr,
                     (w / 2 + this.panX + off) * dpr, (h / 2 + this.panY) * dpr);
    ctx.strokeStyle = stroke;
    ctx.lineWidth = width / scale;      // constant screen-space width
    for (let ty = ty0; ty <= ty1; ty++) {
      for (let tx = tx0; tx <= tx1; tx++) {
        const p = grid.get(tx + ":" + ty);
        if (p) ctx.stroke(p);
      }
    }
    ctx.restore();
    const drawn = (tx1 - tx0 + 1) * (ty1 - ty0 + 1);
    this._lastTileStats = { visible_tiles: drawn, total_tiles: grid.size };
  }

  // v6 §16 — choropleth fill: closed country rings as cached Path2D per
  // country, filled under the same affine transform
  _countryPaths(data, which) {
    const key = "_pathCache_" + which;
    if (!this[key]) {
      const m = new Map();
      for (const c of data) {
        const p = new Path2D();
        for (const ring of c.r) {
          let started = false;
          for (let i = 0; i + 1 < ring.length; i += 2) {
            if (i >= 2 && Math.abs(ring[i] - ring[i - 2]) > 180) { started = false; }
            if (!started) { p.moveTo(ring[i], ring[i + 1]); started = true; }
            else p.lineTo(ring[i], ring[i + 1]);
          }
          p.closePath();
        }
        m.set(c.i, { path: p, bbox: c.b });
      }
      this[key] = m;
    }
    return this[key];
  }

  _cluster() {
    const threshold = this.clusterCfg.cluster_pin_threshold;
    const cell = (this.clusterCfg.cluster_radius_km / 111.32) / Math.max(1, this.zoom / 2);
    const grid = new Map();
    for (const e of this.events) {
      const key = `${Math.round(e.lat / cell)}:${Math.round(e.lon / cell)}`;
      if (!grid.has(key)) grid.set(key, []);
      grid.get(key).push(e);
    }
    const clusters = [];
    for (const members of grid.values()) {
      if (members.length >= threshold && this.zoom < 4) {
        const lat = members.reduce((s, e) => s + e.lat, 0) / members.length;
        const lon = members.reduce((s, e) => s + e.lon, 0) / members.length;
        clusters.push({ cluster: true, lat, lon, members });
      } else {
        for (const e of members) clusters.push({ cluster: false, lat: e.lat, lon: e.lon, event: e });
      }
    }
    return clusters;
  }

  draw() {
    if (this.destroyed) return;
    const ctx = this.ctx;
    const w = this.host.clientWidth, h = this.host.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const tiles = this._tiles();
    const scale = this._scale();
    // v5 §12 — viewport culling: compute the visible lon/lat bounds once, so
    // off-screen country rings / cities / points are skipped instead of drawn
    // and clipped. A generous margin keeps things that are just off-edge.
    this._vb = this._visibleBounds(w, h);

    // graticule per tile — v6.2 theme-tinted
    ctx.strokeStyle = this.gridStroke || "rgba(64,97,158,0.18)";
    ctx.lineWidth = 1;
    for (const off of tiles) {
      for (let lon = -180; lon <= 180; lon += 30) {
        const [x1, y1] = this._project(85, lon), [, y2] = this._project(-85, lon);
        ctx.beginPath(); ctx.moveTo(x1 + off, y1); ctx.lineTo(x1 + off, y2); ctx.stroke();
      }
      for (let lat = -60; lat <= 60; lat += 30) {
        const [x1, y1] = this._project(lat, -180), [x2] = this._project(lat, 180);
        ctx.beginPath(); ctx.moveTo(x1 + off, y1); ctx.lineTo(x2 + off, y1); ctx.stroke();
      }
    }

    const boundaries = this._boundaries();
    const lodKey = boundaries === this.b10 ? "10m" : "50m";
    for (const off of tiles) {
      // v6 §16 — thematic choropleth fill FIRST (under every line layer)
      if (this.choropleth) {
        const paths = this._countryPaths(boundaries, lodKey);
        const dpr = window.devicePixelRatio || 1;
        this.ctx.save();
        this.ctx.setTransform(scale * dpr, 0, 0, -scale * dpr,
                              (w / 2 + this.panX + off) * dpr,
                              (h / 2 + this.panY) * dpr);
        for (const [iso3, { path, bbox }] of paths) {
          const color = this.choropleth[iso3];
          if (!color || !this._bboxVisible(bbox)) continue;
          this.ctx.fillStyle = color;
          this.ctx.fill(path);
        }
        this.ctx.restore();
      }
      // v8.3 — Hotspots heat fill (active admin units only), under the lines.
      // Uses the same lon/lat affine transform as the choropleth.
      if (this.adminHeat && this.adminHeat.length) {
        const dpr = window.devicePixelRatio || 1;
        this.ctx.save();
        this.ctx.setTransform(scale * dpr, 0, 0, -scale * dpr,
                              (w / 2 + this.panX + off) * dpr,
                              (h / 2 + this.panY) * dpr);
        for (const cell of this.adminHeat) {
          this.ctx.fillStyle = cell.color;
          for (const ring of cell.rings) {
            if (ring.length < 6) continue;
            this.ctx.beginPath();
            for (let i = 0; i < ring.length; i += 2) {
              if (i) this.ctx.lineTo(ring[i], ring[i + 1]);
              else this.ctx.moveTo(ring[i], ring[i + 1]);
            }
            this.ctx.closePath();
            this.ctx.fill();
          }
        }
        this.ctx.restore();
      }
      // country borders — v6 §18 tile-based rendering (see _strokeBoundaryTiles)
      // v8.9 — when an admin-division tier is actively drawn (zoomed in), fade
      // the national border so the differently-simplified admin outer ring
      // doesn't criss-cross it into an ugly double line.
      if (this.showBorders) {
        const adminOn = (this.adminVis[0] && this.zoom >= 2.5 && this.adminRings.length)
                     || (this.adminVis[1] && this.zoom >= 4.5 && this.admin2Rings.length)
                     || (this.adminVis[2] && this.zoom >= 7 && this.admin3Rings.length);
        const stroke = adminOn ? "rgba(122,146,190,0.16)"
                               : (this.landStroke || "rgba(122,146,190,0.5)");
        this._strokeBoundaryTiles(boundaries, lodKey, off, stroke, 1);
      }
      // alliance tint (§4.1 parity with the globe's bloc overlay)
      if (this.allianceRings) {
        this._drawRings(this.allianceRings, off, this.allianceColor, 1.6);
      }
      // v6 §7/§8 — multi-select bloc groups / War Mode side colors
      for (const g of (this.ringGroups || [])) {
        this._drawRings(g.rings, off, g.color, 1.6);
      }
      // v6 §26 — pulsing focus highlight
      if (this.highlightRings) {
        const pulse = 0.4 + 0.5 * Math.abs(Math.sin(performance.now() / 320));
        const [r, g, b] = this.highlightColor.map((c) => Math.round(c * 255));
        this._drawRings(this.highlightRings, off, `rgba(${r},${g},${b},${pulse})`, 2.2);
      }
      // disputed boundaries — dashed, own toggle (§5.3)
      if (this.showDisputes) {
        for (const d of this.disputed) {
          this._drawRings(d.r, off, "rgba(255,184,77,0.9)", 1.4, true);
        }
      }
      // v8 §3 — ADM1 province borders: solid soft-teal, only when toggled on
      // and zoomed in (a national outline still dominates at low zoom). Canvas
      // clips off-screen segments cheaply, so the whole set is drawn on demand.
      if (this.adminVis[0] && this.zoom >= 2.5 && this.adminRings.length) {
        this._drawRings(this.adminRings, off, "rgba(107,184,184,0.5)", 0.7);
      }
      // v8.1 — ADM2 (county/district) borders: fainter, only when zoomed deeper
      if (this.adminVis[1] && this.zoom >= 4.5 && this.admin2Rings.length) {
        this._drawRings(this.admin2Rings, off, "rgba(140,168,152,0.42)", 0.5);
      }
      // v8.2 — ADM3 (sub-district) borders: faintest, only at the tightest zoom
      if (this.adminVis[2] && this.zoom >= 7 && this.admin3Rings.length) {
        this._drawRings(this.admin3Rings, off, "rgba(158,152,174,0.4)", 0.45);
      }
      // v8.4 — historical world borders for a past as_of epoch: amber, ungated
      // (they replace the modern outline conceptually), drawn over the base map.
      if (this.histRings && this.histRings.length) {
        this._drawRings(this.histRings, off, "rgba(242,178,82,0.92)", 1.2);
      }
      // v7.6 — autonomous regions: always-on DOTTED borders (like territories)
      for (const z of this.autonomousZones) {
        this._drawRings([z.ring], off, "rgba(120,200,255,0.85)", 1.3, true, [2, 3]);
      }
      // v5 §11 / v6 §21 — NSA territory zones: shaped polygons with a
      // pulsing dotted rough-boundary style (never solid rectangles);
      // clickable → the actor's overview page
      const ZC = { established: "242,89,140", contested: "255,180,80",
                   reported: "150,150,170" };
      this._zonePolys = this._zonePolys || [];
      if (off === tiles[0]) this._zonePolys = [];
      const zt = performance.now() / 1000;
      for (const z of this.actorZones) {
        const ring = (z.geojson && z.geojson.coordinates && z.geojson.coordinates[0]) || [];
        if (ring.length < 3) continue;
        const col = ZC[z.confidence] || ZC.reported;
        const pulse = 0.55 + 0.35 * Math.sin(zt * 2.1 + ring.length);
        const poly = [];
        ctx.beginPath();
        ring.forEach(([lon, lat], i) => {
          const [x, y] = this._project(lat, lon);
          poly.push([x + off, y]);
          i ? ctx.lineTo(x + off, y) : ctx.moveTo(x + off, y);
        });
        ctx.closePath();
        // v6.1 — faint fill + a pulsing DOT-FIELD (techno stipple) instead of
        // an outlined polygon that reads as an "ugly rectangle"
        ctx.fillStyle = `rgba(${col},${(0.05 + 0.04 * pulse).toFixed(3)})`;
        ctx.fill();
        let mnx = Infinity, mny = Infinity, mxx = -Infinity, mxy = -Infinity;
        for (const p of poly) { mnx = Math.min(mnx, p[0]); mxx = Math.max(mxx, p[0]); mny = Math.min(mny, p[1]); mxy = Math.max(mxy, p[1]); }
        const gstep = 12;
        const inpoly = (x, y) => {
          let ins = false;
          for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
            const xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
            if (((yi > y) !== (yj > y)) &&
                (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-9) + xi)) ins = !ins;
          }
          return ins;
        };
        for (let gy = mny; gy <= mxy; gy += gstep) {
          for (let gx = mnx; gx <= mxx; gx += gstep) {
            const jx = gx + Math.sin((gx + gy) * 0.7) * gstep * 0.28;
            const jy = gy + Math.cos((gx - gy) * 0.7) * gstep * 0.28;
            if (!inpoly(jx, jy)) continue;
            const ph = 0.5 + 0.5 * Math.sin(zt * 3.0 + (jx + jy) * 0.02);
            ctx.beginPath();
            ctx.arc(jx, jy, 1.0 + 1.0 * ph, 0, 7);
            ctx.fillStyle = `rgba(${col},${(0.35 + 0.5 * ph).toFixed(3)})`;
            ctx.fill();
          }
        }
        this._zonePolys.push({ poly, zone: z });
      }
    }

    // heatmap
    if (this.showHeatmap) {
      for (const off of tiles) {
        for (const e of this.events) {
          const [x, y] = this._project(e.lat, e.lon);
          const r = 18 + (e.severity || 1) * 6;
          const grad = ctx.createRadialGradient(x + off, y, 0, x + off, y, r);
          grad.addColorStop(0, "rgba(255,120,40,0.16)");
          grad.addColorStop(1, "rgba(255,120,40,0)");
          ctx.fillStyle = grad;
          ctx.fillRect(x + off - r, y - r, r * 2, r * 2);
        }
      }
    }

    // v6.1.1 — dynamic country labels: reveal by apparent width (span° × px/°) + v6.2 toggle
    if (this.countryLabelsOn !== false && this.countryLabels && this.countryLabels.length) {
      const scale = this._scale();
      const placedC = [];
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (const l of this.countryLabels) {
        if (this._vb && (l.lat < this._vb.minLat - 5 || l.lat > this._vb.maxLat + 5)) continue;
        const apparentPx = (l.span || 4) * scale;
        if (apparentPx < 46) continue;
        const alpha = Math.min(0.82, 0.2 + (apparentPx - 46) / 30 * 0.62);
        const [x, y] = this._project(l.lat, l.lon);
        for (const off of tiles) {
          const xx = x + off;
          if (xx < 0 || xx > w || y < 0 || y > h) continue;
          let collide = false;
          for (const q of placedC) {
            if (Math.abs(q[0] - xx) < 60 && Math.abs(q[1] - y) < 15) { collide = true; break; }
          }
          if (collide) continue;
          placedC.push([xx, y]);
          const fs = Math.max(10, Math.min(16, apparentPx / 9));
          ctx.font = `600 ${fs}px system-ui`;
          ctx.lineWidth = 3;
          ctx.strokeStyle = `rgba(6,10,18,${(alpha * 0.7).toFixed(2)})`;
          ctx.fillStyle = `rgba(225,232,246,${alpha.toFixed(2)})`;
          ctx.strokeText(l.name, xx, y);
          ctx.fillText(l.name, xx, y);
        }
      }
    }

    // §4.3 city labels: population tier by zoom, density screen-bounded.
    // v8.8 — drawn as lightly-outlined clickable chips; screen boxes recorded.
    this._cityScreens = [];
    if (this.cities.length && this.zoom >= 1.2) {
      const minPop = this.zoom < 2.4 ? 5000000 : this.zoom < 4 ? 500000 : 50000;
      const placed = [];
      ctx.font = "10.5px system-ui";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      for (const c of this.cities) {
        if (placed.length >= 70) break;
        if (c.population < minPop) continue;
        // v5 §12 — cull cities outside the visible lat/lon window before
        // projecting/measuring text (this loop scans thousands of cities)
        if (this._vb && (c.lat < this._vb.minLat || c.lat > this._vb.maxLat)) continue;
        const [x, y] = this._project(c.lat, c.lon);
        for (const off of tiles) {
          const xx = x + off;
          if (xx < -20 || xx > w + 20 || y < 0 || y > h) continue;
          let collide = false;
          for (const q of placed) {
            if (Math.abs(q[0] - xx) < 86 && Math.abs(q[1] - y) < 13) { collide = true; break; }
          }
          if (collide) continue;
          placed.push([xx, y]);
          const big = c.population >= 5000000;
          const tw = ctx.measureText(c.name).width;
          const bx = xx + 3, bw = tw + 8, bh = 14;
          // lightly-outlined chip behind the label
          ctx.fillStyle = "rgba(18,26,42,0.4)";
          ctx.strokeStyle = big ? "rgba(150,175,215,0.5)" : "rgba(140,160,195,0.32)";
          ctx.lineWidth = 0.8;
          if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(bx, y - bh / 2, bw, bh, 4); ctx.fill(); ctx.stroke(); }
          else { ctx.fillRect(bx, y - bh / 2, bw, bh); ctx.strokeRect(bx, y - bh / 2, bw, bh); }
          ctx.fillStyle = "rgba(219,228,245,0.85)";
          ctx.beginPath(); ctx.arc(xx, y, 1.6, 0, 7); ctx.fill();
          ctx.fillStyle = big ? "rgba(233,240,252,0.92)" : "rgba(190,205,230,0.8)";
          ctx.fillText(c.name, bx + 4, y);
          if (c.id != null) this._cityScreens.push({ id: c.id, x: bx, y, w: bw, h: bh });
        }
      }
    }

    // marked locations (§4.1 parity)
    for (const off of tiles) {
      for (const l of this.markedLocations) {
        const [x, y] = this._project(l.lat, l.lon);
        ctx.fillStyle = MARKED_COLORS[l.category] || MARKED_COLORS.other;
        ctx.beginPath();
        const xx = x + off;
        ctx.moveTo(xx, y - 4); ctx.lineTo(xx + 4, y); ctx.lineTo(xx, y + 4);
        ctx.lineTo(xx - 4, y); ctx.closePath();
        ctx.fill();
      }
      // non-state actors (§5.4)
      for (const a of this.actors) {
        const [x, y] = this._project(a.base_lat, a.base_lon);
        ctx.strokeStyle = "rgba(242,89,140,0.9)";
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(x + off, y, 5, 0, 7); ctx.stroke();
        ctx.fillStyle = "rgba(242,89,140,0.5)";
        ctx.beginPath(); ctx.arc(x + off, y, 2, 0, 7); ctx.fill();
      }
      // satellites (§4.1 parity)
      for (const s of this.satellites) {
        const [x, y] = this._project(s.lat, s.lon);
        ctx.fillStyle = "rgba(166,242,255,0.9)";
        ctx.fillRect(x + off - 1.5, y - 1.5, 3, 3);
      }
    }

    // pins / clusters — rendered in every visible tile so markers never
    // vanish while crossing the Pacific (§4.2)
    this.clusters = this._cluster();
    for (const c of this.clusters) {
      const [x, y] = this._project(c.lat, c.lon);
      c.px = x; c.py = y;
      for (const off of tiles) {
        const xx = x + off;
        if (xx < -40 || xx > w + 40) continue;
        if (c.cluster) {
          ctx.fillStyle = "rgba(77,163,255,0.22)";
          ctx.beginPath(); ctx.arc(xx, y, 16, 0, 7); ctx.fill();
          ctx.fillStyle = "#4da3ff";
          ctx.beginPath(); ctx.arc(xx, y, 11, 0, 7); ctx.fill();
          ctx.fillStyle = "#081120";
          ctx.font = "bold 11px system-ui";
          ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.fillText(String(c.members.length), xx, y);
        } else {
          const color = CATEGORY_COLORS[c.event.category] || CATEGORY_COLORS.other;
          const r = 3 + (c.event.severity || 1) * 1.2;
          const lowConf = c.event.geocode_confidence != null
            && c.event.geocode_confidence < this.minConfSolid;
          ctx.globalAlpha = lowConf ? 0.45 : 1;   // §3.1 — approximate ≠ exact
          if (lowConf) ctx.setLineDash([3, 3]);
          ctx.fillStyle = color + "33";
          ctx.beginPath(); ctx.arc(xx, y, r + 4, 0, 7); ctx.fill();
          ctx.fillStyle = color;
          ctx.beginPath(); ctx.arc(xx, y, r, 0, 7);
          if (lowConf) {
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.4;
            ctx.stroke();
          } else {
            ctx.fill();
          }
          ctx.setLineDash([]);
          ctx.globalAlpha = 1;
        }
      }
    }
  }

  _hit(x, y) {
    const tiles = this._tiles();
    let best = null, bestDist = 16;
    const test = (px, py, item) => {
      for (const off of tiles) {
        const d = Math.hypot(px + off - x, py - y);
        if (d < bestDist) { bestDist = d; best = item; }
      }
    };
    for (const c of this.clusters) test(c.px, c.py, c);
    for (const l of this.markedLocations) {
      const [px, py] = this._project(l.lat, l.lon);
      test(px, py, { marked: true, loc: l });
    }
    for (const a of this.actors) {
      const [px, py] = this._project(a.base_lat, a.base_lon);
      test(px, py, { actor: true, a });
    }
    return best;
  }

  _initInteraction() {
    const el = this.canvas;
    let dragging = false, lastX = 0, lastY = 0, moved = 0;
    el.addEventListener("pointerdown", (ev) => {
      dragging = true; moved = 0; lastX = ev.offsetX; lastY = ev.offsetY;
      el.setPointerCapture(ev.pointerId);
    });
    el.addEventListener("pointermove", (ev) => {
      if (dragging) {
        const ps = this.panSensitivity || 1;                   // v8.13 — x+y pan sensitivity
        this.panX += (ev.offsetX - lastX) * ps; this.panY += (ev.offsetY - lastY) * ps;
        moved += Math.abs(ev.offsetX - lastX) + Math.abs(ev.offsetY - lastY);
        lastX = ev.offsetX; lastY = ev.offsetY;
        this._snapPan();   // §4.2 — the user never perceives the seam
        this.draw();
      } else {
        const hit = this._hit(ev.offsetX, ev.offsetY);
        if (hit && !hit.cluster) {
          this.tip.style.display = "block";
          this.tip.style.left = (ev.offsetX + 14) + "px";
          this.tip.style.top = (ev.offsetY + 8) + "px";
          if (hit.marked) {
            this.tip.textContent = `${hit.loc.name} — ${hit.loc.category.replace(/_/g, " ")}`;
          } else if (hit.actor) {
            this.tip.textContent = `${hit.a.name} — approximate operating area`;
          } else {
            const approx = hit.event.geocode_confidence != null
              && hit.event.geocode_confidence < this.minConfSolid
              ? " · ≈ approximate" : "";
            this.tip.textContent =
              `${hit.event.title} — ${hit.event.location_name || ""}${approx}`;
          }
        } else this.tip.style.display = "none";
      }
    });
    el.addEventListener("pointerup", (ev) => {
      dragging = false;
      if (moved > 6) return;
      const hit = this._hit(ev.offsetX, ev.offsetY);
      if (!hit) {
        // v6 §21 — a click inside an NSA zone opens the actor's page
        for (const { poly, zone } of (this._zonePolys || [])) {
          let inside = false;
          for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
            const [xi, yi] = poly[i], [xj, yj] = poly[j];
            if ((yi > ev.offsetY) !== (yj > ev.offsetY)
                && ev.offsetX < ((xj - xi) * (ev.offsetY - yi)) / (yj - yi) + xi) {
              inside = !inside;
            }
          }
          if (inside) {
            this.onSelectActor({ id: zone.nsa_id, name: zone.nsa_name });
            return;
          }
        }
        // v8.8 — a click on a city chip opens the city's page
        for (const s of this._cityScreens) {
          if (ev.offsetX >= s.x - 3 && ev.offsetX <= s.x + s.w + 3
              && Math.abs(ev.offsetY - s.y) <= s.h / 2 + 3) {
            this.onSelectCity(s.id); return;
          }
        }
        // §4.1 parity — empty click resolves to a country profile
        const geo = this._unproject(ev.offsetX, ev.offsetY);
        if (Math.abs(geo.lat) <= 90) this.onCountryClick(geo.lat, geo.lon);
        return;
      }
      if (hit.cluster) { // clicking a cluster expands it (Section 5.2)
        this.zoom = Math.min(40, this.zoom * 2);
        const [cx, cy] = [this.host.clientWidth / 2, this.host.clientHeight / 2];
        this.panX += (cx - hit.px) * 1.6; this.panY += (cy - hit.py) * 1.6;
        this._snapPan();
        this.draw();
      } else if (hit.marked) this.onSelectLocation(hit.loc);
      else if (hit.actor) this.onSelectActor(hit.a);
      else this.onSelectEvent(hit.event);
    });
    el.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      // v8.9 — step scales with user sensitivity; max zoom 40 for very close view
      const step = 0.2 * this.zoomSensitivity;
      const factor = ev.deltaY < 0 ? 1 + step : 1 / (1 + step);
      this.zoom = Math.max(0.8, Math.min(40, this.zoom * factor));
      this._snapPan();
      this.draw();
    }, { passive: false });

    // v6.1 — WASD panning on the 2D map (game-style): while a key is held a
    // rAF loop pans/zooms and redraws; releasing all keys stops the loop.
    this._keys = {};
    const typing = (t) => t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA"
      || t.tagName === "SELECT" || t.isContentEditable);
    const loop = () => {
      const k = this._keys, step = 14 * (1 / Math.max(0.6, this.zoom * 0.5)) * (this.panSensitivity || 1);
      let moved = false;
      // v6.6 — A/D horizontal direction inverted again for the 2D map only
      if (k.a) { this.panX += step; moved = true; }
      if (k.d) { this.panX -= step; moved = true; }
      if (k.w) { this.panY += step; moved = true; }
      if (k.s) { this.panY -= step; moved = true; }
      if (k.e || k["+"] || k["="]) { this.zoom = Math.min(40, this.zoom * 1.03); moved = true; }
      if (k.q || k["-"]) { this.zoom = Math.max(0.8, this.zoom / 1.03); moved = true; }
      if (moved) { this._snapPan(); this.draw(); }
      if (Object.values(this._keys).some(Boolean)) {
        this._keyRaf = requestAnimationFrame(loop);
      } else { this._keyRaf = null; }
    };
    window.addEventListener("keydown", (ev) => {
      if (typing(ev.target)) return;
      const key = ev.key.toLowerCase();
      if (!"wasdqe+-=".includes(key)) return;
      this._keys[key] = true;
      if (!this._keyRaf) this._keyRaf = requestAnimationFrame(loop);
    });
    window.addEventListener("keyup", (ev) => { this._keys[ev.key.toLowerCase()] = false; });
  }
}
