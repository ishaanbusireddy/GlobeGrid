// v2 addendum §6.3 — node-link fact-chain graph explorer.
// Canonical entities as nodes, same-story co-occurrence as edges. Hand-
// rolled force simulation (repulsion + spring edges + damping) on canvas —
// no D3, staying buildless-consistent with the rest of the frontend.
import { api } from "../api/client.js";

export class GraphExplorer {
  constructor(overlayEl) {
    this.overlay = overlayEl;
    this.running = false;
  }

  async open() {
    this.overlay.classList.remove("hidden");
    this.overlay.innerHTML = `
      <div class="graph-page">
        <div class="close-row">
          <h3>Fact-chain graph — entities linked by shared stories</h3>
          <button class="close-btn">Close</button>
        </div>
        <canvas class="graph-canvas"></canvas>
        <p class="graph-hint">drag nodes · scroll to zoom · size = story count</p>
      </div>`;
    this.overlay.querySelector(".close-btn").addEventListener("click", () => this.close());
    this.canvas = this.overlay.querySelector(".graph-canvas");
    const box = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = Math.min(1100, box.width - 40);
    this.canvas.height = Math.max(420, window.innerHeight * 0.62);
    try {
      const data = await api.graph();
      this._simulate(data);
    } catch (err) {
      this.overlay.querySelector(".graph-page").innerHTML +=
        `<p>graph unavailable: ${err.message}</p>`;
    }
  }

  close() {
    this.running = false;
    this.overlay.classList.add("hidden");
    this.overlay.innerHTML = "";
  }

  _simulate({ nodes, edges }) {
    const W = this.canvas.width, H = this.canvas.height;
    const ctx = this.canvas.getContext("2d");
    if (!nodes.length) {
      ctx.fillStyle = "#8494b5";
      ctx.font = "14px system-ui";
      ctx.fillText("No canonical entities linked into stories yet — the graph grows"
        + " as the correlation engine runs.", 24, 40);
      return;
    }
    const byId = new Map();
    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * Math.PI * 2;
      byId.set(n.id, { ...n, x: W / 2 + Math.cos(angle) * H * 0.3,
                       y: H / 2 + Math.sin(angle) * H * 0.3, vx: 0, vy: 0 });
    });
    const links = edges
      .filter((e) => byId.has(e.a) && byId.has(e.b))
      .map((e) => ({ a: byId.get(e.a), b: byId.get(e.b), w: e.weight }));
    const sim = [...byId.values()];
    let zoom = 1, panX = 0, panY = 0, dragNode = null;

    const radius = (n) => 4 + Math.min(16, Math.sqrt(n.weight) * 3.2);

    const tick = () => {
      // repulsion (O(n²) fine at <=200 nodes) + springs + centering + damping
      for (let i = 0; i < sim.length; i++)
        for (let j = i + 1; j < sim.length; j++) {
          const a = sim[i], b = sim[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          const d2 = Math.max(64, dx * dx + dy * dy);
          const f = 2600 / d2;
          const d = Math.sqrt(d2);
          dx /= d; dy /= d;
          a.vx += dx * f; a.vy += dy * f;
          b.vx -= dx * f; b.vy -= dy * f;
        }
      for (const l of links) {
        const dx = l.b.x - l.a.x, dy = l.b.y - l.a.y;
        const d = Math.max(1, Math.hypot(dx, dy));
        const target = 90 - Math.min(40, l.w * 6);
        const f = (d - target) * 0.004;
        l.a.vx += (dx / d) * f; l.a.vy += (dy / d) * f;
        l.b.vx -= (dx / d) * f; l.b.vy -= (dy / d) * f;
      }
      for (const n of sim) {
        n.vx += (W / 2 - n.x) * 0.0012;
        n.vy += (H / 2 - n.y) * 0.0012;
        if (n !== dragNode) { n.x += n.vx *= 0.86; n.y += n.vy *= 0.86; }
      }
    };

    const draw = () => {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, W, H);
      ctx.setTransform(zoom, 0, 0, zoom, panX, panY);
      for (const l of links) {
        ctx.strokeStyle = `rgba(120,150,220,${Math.min(0.55, 0.12 + l.w * 0.1)})`;
        ctx.lineWidth = Math.min(3, 0.5 + l.w * 0.5);
        ctx.beginPath(); ctx.moveTo(l.a.x, l.a.y); ctx.lineTo(l.b.x, l.b.y); ctx.stroke();
      }
      ctx.font = "11px system-ui";
      for (const n of sim) {
        const r = radius(n);
        ctx.fillStyle = "rgba(77,163,255,0.25)";
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 3, 0, 7); ctx.fill();
        ctx.fillStyle = "#4da3ff";
        ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 7); ctx.fill();
        ctx.fillStyle = "#dbe4f5";
        ctx.fillText(n.name.slice(0, 26), n.x + r + 4, n.y + 3);
      }
    };

    const loop = () => {
      if (!this.running) return;
      tick(); draw();
      requestAnimationFrame(loop);
    };
    this.running = true;
    loop();

    const toWorld = (ev) => {
      const rect = this.canvas.getBoundingClientRect();
      return [(ev.clientX - rect.left - panX) / zoom,
              (ev.clientY - rect.top - panY) / zoom];
    };
    this.canvas.addEventListener("pointerdown", (ev) => {
      const [x, y] = toWorld(ev);
      dragNode = sim.find((n) => Math.hypot(n.x - x, n.y - y) < radius(n) + 5) || null;
      this.canvas.setPointerCapture(ev.pointerId);
    });
    this.canvas.addEventListener("pointermove", (ev) => {
      if (!dragNode) return;
      const [x, y] = toWorld(ev);
      dragNode.x = x; dragNode.y = y; dragNode.vx = dragNode.vy = 0;
    });
    this.canvas.addEventListener("pointerup", () => { dragNode = null; });
    this.canvas.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      zoom = Math.max(0.4, Math.min(3, zoom * (ev.deltaY < 0 ? 1.15 : 1 / 1.15)));
    }, { passive: false });
  }
}
