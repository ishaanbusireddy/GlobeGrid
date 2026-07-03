// Live feed (Section 5.1): story clusters (never raw articles), one card per
// correlated event, source-count badge, newest first.
import React from 'react';

function timeAgo(iso) {
  if (!iso) return '';
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
  if (seconds < 3600) return `${Math.max(1, Math.round(seconds / 60))}m ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
  return `${Math.round(seconds / 86400)}d ago`;
}

export default function LiveFeed({ stories, onSelectStory }) {
  const sorted = [...stories].sort(
    (a, b) => new Date(b.last_updated_at ?? 0) - new Date(a.last_updated_at ?? 0),
  );

  return (
    <div>
      <div className="feed-header">Live feed · {sorted.length} stories</div>
      {sorted.map((story) => (
        <div key={story.id} className="story-card" onClick={() => onSelectStory(story.id)}>
          <h3>{story.headline ?? 'Story forming — narrative pending'}</h3>
          {story.summary && <p>{story.summary}</p>}
          <div className="card-meta">
            <span className="badge src">{story.source_count} sources</span>
            {story.confidence && (
              <span className={`badge confidence-${story.confidence}`}>{story.confidence}</span>
            )}
            {(story.categories ?? []).map((cat) => (
              <span key={cat} className={`badge cat-${cat}`}>{cat}</span>
            ))}
            <span className="badge">{timeAgo(story.last_updated_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
