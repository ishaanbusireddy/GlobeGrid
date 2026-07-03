// Phase 4 data provider: serves the Section 12 synthetic dataset through the
// same interface the live API provider exposes in Phase 5, so swapping the
// data source never touches rendering code.
import syntheticDataset from './syntheticDataset.js';

const membersByStory = new Map();
for (const m of syntheticDataset.story_members) {
  if (!membersByStory.has(m.story_id)) membersByStory.set(m.story_id, []);
  membersByStory.get(m.story_id).push(m);
}
const eventById = new Map(syntheticDataset.events.map((e) => [e.id, e]));

export default {
  name: 'synthetic',

  async getStories() {
    return syntheticDataset.stories;
  },

  async getStory(id) {
    const story = syntheticDataset.stories.find((s) => s.id === id);
    if (!story) return null;
    const members = (membersByStory.get(id) ?? []).map((m) => {
      const event = eventById.get(m.event_id);
      return event && {
        kind: 'event',
        id: event.id,
        title: event.title,
        description: event.description,
        category: event.category,
        severity: event.severity,
        occurred_at: event.occurred_at,
        linked_via: m.linked_via,
        linked_at: m.linked_at,
        source_name: event.source_name,
        source_leaning: event.source_leaning,
        outbound_link: event.outbound_link,
      };
    }).filter(Boolean);
    return { ...story, members };
  },

  async getEvents() {
    return syntheticDataset.events;
  },

  async getInstability() {
    const history = syntheticDataset.instability_scores;
    return { latest: history[history.length - 1] ?? null, history };
  },

  async getSourcesStatus() {
    return [{
      id: 'synthetic', name: 'Synthetic Generator', type: 'rss', leaning: 'n/a',
      poll_interval_seconds: 86400, health_status: 'ok', last_fetched_at: null, last_error: null,
    }];
  },

  subscribe() {
    return () => {}; // static dataset — nothing to push
  },

  connectionState() {
    return 'synthetic';
  },
};
