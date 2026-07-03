// Story page (Section 5.3): headline, AI summary, confidence indicator,
// timeline of which source lit up when, full source list with outbound
// links (Section 6.8 — always visible), and the 'connected history' panel
// surfacing linked past facts from the chain (the fact chain, surfaced).
import React from 'react';

function fmt(iso) {
  return iso ? new Date(iso).toLocaleString() : 'unknown time';
}

export default function StoryPage({ story, onBack }) {
  if (!story) return null;

  const members = story.members ?? [];
  const timeline = [...members].sort(
    (a, b) => new Date(a.occurred_at ?? a.when_occurred ?? 0) - new Date(b.occurred_at ?? b.when_occurred ?? 0),
  );
  const historical = members.filter((m) => m.linked_via === 'historical_chain');
  const sources = [...new Map(
    members
      .filter((m) => m.source_name)
      .map((m) => [m.source_name, m]),
  ).values()];
  const narrative = story.causal_narrative;

  return (
    <div className="story-page">
      <button className="back" onClick={onBack}>← Back to feed</button>
      <h2>{story.headline ?? 'Story forming — narrative pending'}</h2>
      <div className="card-meta">
        {story.confidence && (
          <span className={`badge confidence-${story.confidence}`}>confidence: {story.confidence}</span>
        )}
        <span className="badge src">{story.source_count ?? sources.length} sources</span>
        {(story.categories ?? []).map((cat) => (
          <span key={cat} className={`badge cat-${cat}`}>{cat}</span>
        ))}
      </div>
      {story.summary && <p className="summary">{story.summary}</p>}

      {narrative && (
        <>
          <div className="section-label">Causal analysis</div>
          <dl className="narrative">
            <dt>Cause</dt>
            <dd>{narrative.cause}</dd>
            <dt>Affected</dt>
            <dd><ul>{(narrative.affected ?? []).map((a) => <li key={a}>{a}</li>)}</ul></dd>
            <dt>Likely consequences</dt>
            <dd><ul>{(narrative.consequences ?? []).map((c) => <li key={c}>{c}</li>)}</ul></dd>
          </dl>
        </>
      )}

      <div className="section-label">Timeline — which source lit up when</div>
      <div className="timeline">
        {timeline.map((m, i) => (
          <div key={m.id ?? i} className="timeline-item">
            <div className="t-time">{fmt(m.occurred_at ?? m.when_occurred)}</div>
            <span className="t-source">{m.source_name ?? 'unknown source'}</span>
            {' — '}
            {m.title ?? m.what}
          </div>
        ))}
      </div>

      <div className="section-label">Sources</div>
      <div className="source-list">
        {sources.map((m) => (
          <div key={m.source_name}>
            {m.outbound_link
              ? <a href={m.outbound_link} target="_blank" rel="noreferrer">{m.source_name} ↗</a>
              : <span>{m.source_name}</span>}
            {m.source_leaning && m.source_leaning !== 'n/a' && (
              <span className="leaning">({m.source_leaning})</span>
            )}
          </div>
        ))}
      </div>

      <div className="section-label">Connected history</div>
      <div className="history-panel">
        {historical.length === 0 && (
          <div className="empty">
            No links into the historical fact chain yet — this story is built
            entirely from same-window correlation.
          </div>
        )}
        {historical.map((m, i) => (
          <div key={m.id ?? i} className="history-item">
            <div className="t-time" style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              {fmt(m.occurred_at ?? m.when_occurred)} · via historical chain
            </div>
            {m.title ?? `${m.who ?? ''} — ${m.what ?? ''}`}
          </div>
        ))}
      </div>
    </div>
  );
}
