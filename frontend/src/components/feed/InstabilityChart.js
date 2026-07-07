// Section 5.6 — instability index widget: current 0-100 score plus a
// sparkline trend from GET /api/instability history.
export class InstabilityChart {
  constructor(valueEl, sparkCanvas) {
    this.valueEl = valueEl;
    this.canvas = sparkCanvas;
  }

  update({ latest, history, anomalies }) {
    const score = latest ? Math.round(latest.score) : null;
    this.valueEl.textContent = score === null ? "–" : String(score);
    this.valueEl.style.color =
      score === null ? "var(--text-dim)"
        : score >= 66 ? "var(--down)"
        : score >= 33 ? "var(--degraded)" : "var(--ok)";
    this._spark(history || [], anomalies || []);
  }

  _spark(history, anomalies) {
    const ctx = this.canvas.getContext("2d");
    const w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (history.length < 2) return;
    const scores = history.map((p) => p.score);
    const min = Math.min(...scores), max = Math.max(...scores);
    const span = Math.max(1, max - min);
    const xy = (i, score) => [(i / (history.length - 1)) * (w - 2) + 1,
                              h - 3 - ((score - min) / span) * (h - 6)];
    ctx.beginPath();
    history.forEach((p, i) => {
      const [x, y] = xy(i, p.score);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#ffd166";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    // v3 §6 — anomaly markers on the trend line
    for (const a of anomalies) {
      let best = 0, bestDiff = Infinity;
      history.forEach((p, i) => {
        const diff = Math.abs(new Date(p.computed_at) - new Date(a.detected_at));
        if (diff < bestDiff) { bestDiff = diff; best = i; }
      });
      const [x, y] = xy(best, history[best].score);
      ctx.fillStyle = a.method === "cusum" ? "#c792ea" : "#ff6b6b";
      ctx.beginPath();
      ctx.moveTo(x, y - 6); ctx.lineTo(x - 4, y + 2); ctx.lineTo(x + 4, y + 2);
      ctx.closePath();
      ctx.fill();
    }
  }
}
