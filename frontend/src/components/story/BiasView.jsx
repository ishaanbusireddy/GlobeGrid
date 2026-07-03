// Bias / blindspot view (Section 5.7): how the same story is covered
// across outlets — side-by-side outlet name, leaning label (from the
// curated sources.leaning table seeded for the Section 4.1 outlets), and
// that outlet's headline for this story.
import React from 'react';

const LEANING_CLASS = { left: 'leaning-left', center: 'leaning-center', right: 'leaning-right' };

export default function BiasView({ members }) {
  const byOutlet = new Map();
  for (const m of members ?? []) {
    if (!m.source_name) continue;
    if (!byOutlet.has(m.source_name)) {
      byOutlet.set(m.source_name, {
        outlet: m.source_name,
        leaning: m.source_leaning ?? 'n/a',
        headline: m.title ?? m.what ?? '—',
        link: m.outbound_link,
      });
    }
  }
  const rows = [...byOutlet.values()];
  if (rows.length === 0) return null;

  return (
    <>
      <div className="section-label">Coverage by outlet — bias / blindspot view</div>
      <table className="bias-table">
        <thead>
          <tr><th>Outlet</th><th>Leaning</th><th>Their headline</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.outlet}>
              <td>{r.link ? <a href={r.link} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>{r.outlet}</a> : r.outlet}</td>
              <td><span className={`leaning-pill ${LEANING_CLASS[r.leaning] ?? 'leaning-na'}`}>{r.leaning}</span></td>
              <td>{r.headline}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
