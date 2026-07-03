// System-status panel (Section 5.10): health of every registered source —
// a dead source is surfaced here, never silently dropped.
import React, { useEffect, useState } from 'react';
import provider from '../../data/dataProvider.js';

export default function SourceStatusPanel() {
  const [sources, setSources] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () => provider.getSourcesStatus().then((s) => alive && setSources(s)).catch(() => {});
    load();
    const timer = setInterval(load, 30000);
    return () => { alive = false; clearInterval(timer); };
  }, []);

  const unhealthy = sources.filter((s) => s.health_status !== 'ok').length;

  return (
    <div className="status-panel">
      <div
        className="feed-header"
        style={{ padding: 0, cursor: 'pointer' }}
        onClick={() => setOpen(!open)}
      >
        System status · {sources.length - unhealthy}/{sources.length} sources healthy {open ? '▾' : '▸'}
      </div>
      {open && sources.map((s) => (
        <div key={s.id} className="status-row" title={s.last_error ?? ''}>
          <span className={`dot ${s.health_status}`} />
          <span>{s.name}</span>
          <span style={{ color: 'var(--text-dim)', marginLeft: 'auto' }}>{s.health_status}</span>
        </div>
      ))}
    </div>
  );
}
