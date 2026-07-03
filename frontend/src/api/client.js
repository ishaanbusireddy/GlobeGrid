// REST client for the Section 8.1 endpoints. Origin-relative paths — the
// Vite dev server proxies /api to the backend (vite.config.js); in any
// packaged setup the API serves from the same origin.

async function get(path, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null),
  ).toString();
  const response = await fetch(`${path}${query ? `?${query}` : ''}`);
  if (!response.ok) throw new Error(`GET ${path} -> ${response.status}`);
  return response.json();
}

export const fetchStories = ({ since, limit, category } = {}) =>
  get('/api/stories', { since, limit, category });

export const fetchStory = (id) => get(`/api/stories/${id}`);

export const fetchEvents = ({ bbox, category, since, limit } = {}) =>
  get('/api/events', { bbox, category, since, limit });

export const fetchMapClusters = ({ bbox, category, since } = {}) =>
  get('/api/map/clusters', { bbox, category, since });

export const fetchInstability = (range = '72h') => get('/api/instability', { range });

export const fetchSourcesStatus = () => get('/api/sources/status');

export const translateText = (text, targetLanguage) =>
  fetch('/api/translate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, target_language: targetLanguage }),
  }).then((r) => {
    if (!r.ok) throw new Error(`POST /api/translate -> ${r.status}`);
    return r.json();
  });
