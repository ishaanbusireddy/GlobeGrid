// Instability index trend line (Section 5.6): latest composite score plus
// the rolling history, rendered on the homepage. Data from
// GET /api/instability; live updates via instability_updated WS messages.
import React from 'react';

export default function InstabilityTrend({ latest, history }) {
  if (!latest) {
    return (
      <div className="trend-panel">
        <div className="trend-head"><span>GLOBAL INSTABILITY INDEX</span></div>
        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>no readings yet</span>
      </div>
    );
  }

  const width = 330;
  const height = 40;
  const points = history.length > 1 ? history : [latest, latest];
  const scores = points.map((p) => Number(p.score));
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const span = Math.max(max - min, 1);
  const path = scores
    .map((s, i) => {
      const x = (i / (scores.length - 1)) * width;
      const y = height - ((s - min) / span) * (height - 6) - 3;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  const score = Number(latest.score);
  const color = score >= 66 ? 'var(--low)' : score >= 33 ? 'var(--medium)' : 'var(--high)';

  return (
    <div className="trend-panel">
      <div className="trend-head">
        <span>GLOBAL INSTABILITY INDEX</span>
        <span className="score-now" style={{ color }}>{score.toFixed(1)}</span>
      </div>
      <svg width={width} height={height} style={{ display: 'block', maxWidth: '100%' }}>
        <path d={path} fill="none" stroke={color} strokeWidth="1.5" />
      </svg>
    </div>
  );
}
