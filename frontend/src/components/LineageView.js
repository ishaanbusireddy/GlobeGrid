// v3 §8 — butterfly-effect lineage view: pick one fact and render
// everything it ever fed into, growing forward through time. Simple
// recursive canvas layout (columns = lineage depth), same hand-rolled
// approach as the v2 graph explorer. Distinct from that explorer:
// co-occurrence there, single-thread ancestry here.
import { api } from "../api/client.js";

export class LineageView {
  constructor(overlayEl, { onOpenStory } = {}) {
    this.overlay = overlayEl;
    this.onOpenStory = onOpenStory || (() => {});
    this.overlay.addEventListener("click", (ev) => {
      if (ev.target === this.overlay) this.close();
    });
  }

  close() { this.overlay.classList.add("hidden"); this.overlay.innerHTML = ""; }

  async open(factId) {
    this.overlay.classList.remove("hidden");
    this.overlay.innerHTML = '<div class="graph-page"><p>tracing lineage…</p></div>';
    let data;
    try { data = await api.lineage(factId); }
    catch (err) {
      this.overlay.innerHTML =
        `<div class="graph-page"><p>lineage unavailable: ${err.message}</p></div>`;
      return;
    }
    const page = document.createElement("div");
    page.className = "graph-page";
    page.innerHTML = `
      <div class="close-row">
        <h3>Butterfly effect — everything this fact fed into</h3>
        <button class="close-btn">✕ close</button>
      </div>
      <canvas class="graph-canvas"></canvas>
      <p class="graph-hint">left = the origin fact · each column is one correlation hop
        forward in time · click a node's story link below</p>
      <div class="lineage-stories"></div>`;
    page.querySelector(".close-btn").addEventListener("click", () => this.close());
    this.overlay.innerHTML = "";
    this.overlay.appendChild(page);

    const canvas = page.querySelector(".graph-canvas");
    canvas.width = Math.min(1100, window.innerWidth - 120);
    canvas.height = Math.max(360, Math.min(640, 90 + data.nodes.length * 34));
    this._draw(canvas, data);

    const storiesEl = page.querySelector(".lineage-stories");
    const seen = new Set();
    for (const e of data.edges) {
      if (seen.has(e.via_story_id)) continue;
      seen.add(e.via_story_id);
      const chip = document.createElement("button");
      chip.className = "ap-chip";
      chip.textContent = "⌕ " + (e.headline || e.via_story_id).slice(0, 64);
      chip.addEventListener("click", () => this.onOpenStory(e.via_story_id));
      storiesEl.appendChild(chip);
    }
    if (!data.edges.length) {
      storiesEl.innerHTML = '<p class="cp-meta">This fact has not yet influenced any '
        + "future correlation — lineage grows as the historical chain links new events "
        + "back to it.</p>";
    }
  }

  _draw(canvas, { nodes, edges }) {
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const maxDepth = Math.max(1, ...nodes.map((n) => n.depth));
    const byDepth = new Map();
    for (const n of nodes) {
      (byDepth.get(n.depth) || byDepth.set(n.depth, []).get(n.depth)).push(n);
    }
    const pos = new Map();
    for (const [depth, list] of byDepth) {
      list.sort((a, b) => (a.when_occurred || "").localeCompare(b.when_occurred || ""));
      list.forEach((n, i) => {
        pos.set(n.id, {
          x: 90 + (depth / Math.max(1, maxDepth)) * (W - 220),
          y: 60 + ((i + 0.5) / list.length) * (H - 110),
        });
      });
    }
    ctx.clearRect(0, 0, W, H);
    // edges as gentle curves growing rightward
    for (const e of edges) {
      const a = pos.get(e.from), b = pos.get(e.to);
      if (!a || !b) continue;
      ctx.strokeStyle = "rgba(199,146,234,0.55)";
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.bezierCurveTo((a.x + b.x) / 2, a.y, (a.x + b.x) / 2, b.y, b.x, b.y);
      ctx.stroke();
    }
    ctx.font = "11px system-ui";
    for (const n of nodes) {
      const p = pos.get(n.id);
      if (!p) continue;
      const isRoot = n.depth === 0;
      ctx.fillStyle = isRoot ? "#ffd166" : "#c792ea";
      ctx.beginPath();
      ctx.arc(p.x, p.y, isRoot ? 9 : 6, 0, 7);
      ctx.fill();
      ctx.fillStyle = "#dbe4f5";
      const label = `${(n.who || "").slice(0, 24)} — ${(n.what || "").slice(0, 30)}`;
      ctx.fillText(label, p.x + 12, p.y - 2);
      ctx.fillStyle = "#8494b5";
      ctx.fillText((n.when_occurred || "").slice(0, 10), p.x + 12, p.y + 11);
    }
  }
}
