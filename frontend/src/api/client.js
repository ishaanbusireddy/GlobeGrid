// REST client for the Section 8.1 contract + v2 addendum routes.
const BASE = "";

// v6.1 — every request carries a client-side timeout so a slow/stuck
// provider call can never leave the UI spinning forever ("responses stall
// and just don't go through"). Callers may pass their own AbortSignal (the
// analyst Stop button) which composes with the timeout.
const DEFAULT_TIMEOUT_MS = 25000;

function withTimeout(ms, externalSignal) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(new Error("timeout")), ms);
  if (externalSignal) {
    if (externalSignal.aborted) ctrl.abort(externalSignal.reason);
    else externalSignal.addEventListener("abort",
      () => ctrl.abort(externalSignal.reason), { once: true });
  }
  return { signal: ctrl.signal, done: () => clearTimeout(timer) };
}

async function get(path, { timeout = DEFAULT_TIMEOUT_MS, signal } = {}) {
  const t = withTimeout(timeout, signal);
  try {
    const resp = await fetch(BASE + path,
      { headers: { Accept: "application/json" }, signal: t.signal });
    if (!resp.ok) throw new Error(`${path} -> HTTP ${resp.status}`);
    return await resp.json();
  } finally { t.done(); }
}

async function post(path, body, { timeout = DEFAULT_TIMEOUT_MS, signal } = {}) {
  const t = withTimeout(timeout, signal);
  try {
    const resp = await fetch(BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: t.signal,
    });
    return await resp.json();
  } finally { t.done(); }
}

export const api = {
  stories: ({ since, limit, category, as_of, watchlist, conflict_id,
              min_relevance, region, story_type } = {}) => {
    const q = new URLSearchParams();
    if (since) q.set("since", since);
    if (limit) q.set("limit", limit);
    if (category) q.set("category", category);
    if (as_of) q.set("as_of", as_of);
    if (watchlist) q.set("watchlist", watchlist);
    if (conflict_id) q.set("conflict_id", conflict_id);
    if (min_relevance != null) q.set("min_relevance", min_relevance);
    if (region) q.set("region", region);
    if (story_type) q.set("story_type", story_type);
    return get(`/api/stories?${q}`);
  },
  story: (id) => get(`/api/stories/${id}`),
  events: ({ bbox, category, since, as_of } = {}) => {
    const q = new URLSearchParams();
    if (bbox) q.set("bbox", bbox);
    if (category) q.set("category", category);
    if (since) q.set("since", since);
    if (as_of) q.set("as_of", as_of);
    return get(`/api/events?${q}`);
  },
  mapEvents: ({ category, since, as_of, min_relevance, conflict_id } = {}) => {
    const q = new URLSearchParams();
    if (category) q.set("category", category);
    if (since) q.set("since", since);
    if (as_of) q.set("as_of", as_of);
    if (min_relevance != null) q.set("min_relevance", min_relevance);
    if (conflict_id) q.set("conflict_id", conflict_id);
    return get(`/api/map/events?${q}`);
  },
  instability: (range = "72h", asOf = null) => {
    const q = new URLSearchParams({ range });
    if (asOf) q.set("as_of", asOf);
    return get(`/api/instability?${q}`);
  },
  sourcesStatus: () => get("/api/sources/status"),
  sourceStories: (sid) => get(`/api/sources/${encodeURIComponent(sid)}/stories`),
  config: () => get("/api/config"),
  search: (term) => get(`/api/search?q=${encodeURIComponent(term)}`),
  graph: () => get("/api/graph"),
  predictions: () => get("/api/predictions"),
  briefings: (generate = false, period = "day") => {
    const q = new URLSearchParams();
    if (generate) q.set("generate", "1");
    if (period && period !== "day") q.set("period", period);
    return get(`/api/briefings?${q}`, { timeout: 60000 });
  },
  watchlist: () => get("/api/watchlist"),
  watchlistAdd: (kind, value) => post("/api/watchlist", { kind, value }),
  watchlistDelete: (id) => post("/api/watchlist/delete", { id }),
  // --- v7 ---
  counterfactual: (perturbation, force) =>
    post("/api/counterfactual", { perturbation, force }, { timeout: 90000 }),
  counterfactualRecent: () => get("/api/counterfactual/recent"),
  counterfactualExpand: (perturbation, branch) =>
    post("/api/counterfactual/expand", { perturbation, branch }, { timeout: 90000 }),
  sensors: () => get("/api/sensors"),
  forecastScorecard: () => get("/api/forecasting/scorecard"),
  runBacktest: () => post("/api/forecasting/backtest", {}, { timeout: 60000 }),
  situationRoom: (cid, force) =>
    get(`/api/situation-room/${cid}${force ? "?force=1" : ""}`, { timeout: 180000 }),
  // --- v3 ---
  storyFeedback: (id, vote) => post(`/api/stories/${id}/feedback`, { vote }),
  lineage: (factId) => get(`/api/lineage/${factId}`),
  provenance: () => get("/api/provenance"),
  countries: (q_) => get(`/api/countries${q_ ? "?q=" + encodeURIComponent(q_) : ""}`),
  country: (iso3) => get(`/api/countries/${iso3}`),
  alliances: () => get("/api/alliances"),
  alliance: (id) => get(`/api/alliance/${encodeURIComponent(id)}`),   // v6.6.2 rich bloc panel
  conflicts: () => get("/api/conflicts"),
  confirmConflictTag: (storyId, confirm) =>
    post("/api/conflicts/confirm_tag", { story_id: storyId, confirm }),
  actors: () => get("/api/actors"),
  orgs: () => get("/api/orgs"),
  markedLocations: () => get("/api/marked-locations"),
  relations: () => get("/api/relations"),
  satellites: () => get("/api/satellites"),
  // v6.1 — analyst can run several LLM+web-search steps; give it a longer
  // ceiling and let the caller pass a Stop signal (AbortController).
  analystAsk: (question, sessionId, focusedEntity, screen, signal) =>
    post("/api/analyst/ask", { question, session_id: sessionId,
                               focused_entity: focusedEntity, screen },
         { timeout: 60000, signal }),   // v6 §29 — screen-aware context
  analystHistory: (sessionId) =>
    get(`/api/analyst/history${sessionId ? "?session_id=" + sessionId : ""}`),
  analystClear: (sessionId) =>
    post("/api/analyst/clear", { session_id: sessionId || null }),
  // --- v4 ---
  cities: (minPop, limit) =>
    get(`/api/cities?min_population=${minPop || 500000}&limit=${limit || 4000}`),
  borderDisputes: () => get("/api/border-disputes"),
  disputedZones: () => get("/api/disputed-zones"),   // v6.6.2 disputed territories
  countryStat: (iso3, metric) => get(`/api/country-stat?iso3=${encodeURIComponent(iso3)}&metric=${encodeURIComponent(metric)}`),   // v6.6.5
  parties: () => get("/api/parties"),
  party: (id) => get(`/api/parties/${id}`),
  person: (id) => get(`/api/persons/${id}`),
  wikiDirectory: () => get("/api/wiki/directory"),
  background: (etype, eid) => get(`/api/background/${etype}/${eid}`),
  storiesDirectory: (type) =>
    get(`/api/stories-directory${type ? "?type=" + encodeURIComponent(type) : ""}`),
  lineageChains: () => get("/api/chains"),                               // v7.4.1 chains tab
  storyTrace: (id) => get(`/api/stories/${id}/trace`),
  deepSummary: (id, expand) => post(`/api/stories/${id}/deep_summary`, expand ? { expand: true } : {}, { timeout: 60000 }),
  annotations: (targetType, targetId) => {
    const q = new URLSearchParams();
    if (targetType) q.set("target_type", targetType);
    if (targetId) q.set("target_id", targetId);
    return get(`/api/annotations?${q}`);
  },
  annotationSave: (targetType, targetId, noteText, id) =>
    post("/api/annotations", { target_type: targetType, target_id: targetId,
                               note_text: noteText, id }),
  annotationDelete: (id) => post("/api/annotations/delete", { id }),
  bookmarks: () => get("/api/bookmarks"),
  bookmarkToggle: (targetType, targetId) =>
    post("/api/bookmarks", { target_type: targetType, target_id: targetId }),
  credits: () => get("/api/credits"),
  keysStatus: () => get("/api/settings/keys"),
  keySave: (name, value) => post("/api/settings/keys", { name, value }),
  completeness: () => get("/api/completeness"),
  // --- v5 ---
  nsaZones: () => get("/api/nsa-zones"),
  regionSummary: (region) => get(`/api/region/${encodeURIComponent(region)}`),
  // --- v6 ---
  warMode: (cid) => get(`/api/conflicts/${cid}/war_mode`),               // §8
  conflictFeed: (cid) => get(`/api/conflicts/${cid}/feed`),              // v7.5 war-mode stories+events
  orderOfBattle: (cid) =>                                                 // v6.1.1
    get(`/api/conflicts/${cid}/order_of_battle`, { timeout: 55000 }),
  mapModes: () => get("/api/mapmodes"),                                  // §16
  mapMode: (mode) => get(`/api/mapmodes/${encodeURIComponent(mode)}`),   // §16
  threadDetail: (id) => get(`/api/threads/${id}`),                       // §27
  un: () => get("/api/un"),                                              // v6.1 UN panel
  unFeed: () => get("/api/un/feed"),                                     // v7.4.1 UN news feed
  recognitionSubjects: () => get("/api/recognition"),                    // v7.4.1 recognition map
  recognition: (subject) => get(`/api/recognition/${encodeURIComponent(subject)}`),
  autonomousZones: () => get("/api/autonomous-zones"),                   // v7.4.1 autonomous regions
  autonomousZone: (zid) => get(`/api/autonomous-zones/${encodeURIComponent(zid)}`),
  partyDossier: (name, country) => get(`/api/party-dossier?name=${encodeURIComponent(name)}${country ? "&country=" + encodeURIComponent(country) : ""}`),  // v7.4.2
  leaderProfile: (name) =>                                              // v6.6 / v6.6.6 non-blocking
    get(`/api/leader-profile?name=${encodeURIComponent(name)}`, { timeout: 20000 }),
  leaderPortrait: (name) =>                                             // v6.2
    get(`/api/leader-portrait?name=${encodeURIComponent(name)}`, { timeout: 10000 }),
  translateContent: (language, items) =>                                 // §11
    post("/api/translate/content", { language, items }, { timeout: 60000 }),
};
