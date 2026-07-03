// Tier 3 — Light list/card view (Section 11.1). Fully implemented in Phase 6;
// this minimal version already satisfies "content loads instantly" so the
// tier switcher is functional from Phase 4 onward.
import React from 'react';

export default function Tier3List({ events, stories, onSelectStory }) {
  const storyByEvent = new Map();
  (stories ?? []).forEach((s) => (s.member_event_ids ?? []).forEach((id) => storyByEvent.set(id, s.id)));

  const sorted = [...(events ?? [])].sort(
    (a, b) => new Date(b.occurred_at ?? 0) - new Date(a.occurred_at ?? 0),
  );

  return (
    <div className="tier3-list">
      {sorted.map((e) => (
        <div
          key={e.id}
          className="event-row"
          style={{ cursor: storyByEvent.has(e.id) ? 'pointer' : 'default' }}
          onClick={() => storyByEvent.has(e.id) && onSelectStory(storyByEvent.get(e.id))}
        >
          <span className={`badge cat-${e.category}`}>{e.category}</span>
          <span>{e.title}</span>
          <span className="place">{e.location_name}</span>
        </div>
      ))}
    </div>
  );
}
