// GlobeGrid — frontend orchestrator (v1 Stage 7 + v2 + v3 + v4).
// v4 wiring: the shared left-docked SlidePane serves story pages, country
// profiles, wiki pages, directories, compare view and settings (§6/§17);
// clustering/boundary-LOD/city-label options flow from /api/config into
// both renderers (§2/§4); continent + relevance filters share one state
// across feed and map (§9); breaking-story alerts (§25); snapshot export
// (§23); volume slider + music presets incl. data sonification (§12);
// API-key onboarding (§14); and the §16 focusedEntity lifecycle fix —
// cleared on pane close and empty clicks, timestamped for staleness.
import { api } from "./api/client.js";
import { FeedSocket } from "./api/socket.js";
import { initTierControl } from "./components/map/TierDetector.js";
import { Tier1Globe } from "./components/map/Tier1Globe.js";
import { Tier2Map } from "./components/map/Tier2Map.js";
import { Tier3List } from "./components/map/Tier3List.js";
import { LiveFeed } from "./components/feed/LiveFeed.js";
import { InstabilityChart } from "./components/feed/InstabilityChart.js";
import { StoryPage } from "./components/story/StoryPage.js";
import { StatusPanel } from "./components/status/StatusPanel.js";
import { SoundEngine, PRESETS } from "./components/SoundEngine.js";
import { TimeScrubber } from "./components/TimeScrubber.js";
import { CommandPalette } from "./components/CommandPalette.js";
import { GraphExplorer } from "./components/GraphExplorer.js";
import { AnalystPanel } from "./components/AnalystPanel.js";
import { LineageView } from "./components/LineageView.js";
import { propagateAll } from "./components/Satellites.js";
// --- v4 ---
import { SlidePane } from "./components/panes/SlidePane.js";
import * as Wiki from "./components/panes/WikiPages.js";
import { Alerts } from "./components/Alerts.js";
import { exportSnapshot } from "./components/Snapshot.js";
import { BOUNDARIES_50M_ENC } from "./data/boundaries50m.js";
import { decodeBoundaries, countryAtPoint } from "./data/boundaryCodec.js";
import { LANGUAGE_INFO, RELIGION_INFO, familyColor } from "./data/families.js";
import { TIMEZONES, getTimeZone, setTimeZone } from "./data/timefmt.js";  // v6.2 header tz
import { LANGUAGES, applyLanguage } from "./i18n.js";   // v5 §2
import { renderWhatIf } from "./components/panes/WhatIf.js";   // v7 §2
import { renderSituationRoom } from "./components/panes/SituationRoom.js";  // v7 §3
import * as morning from "./components/MorningBriefing.js";   // v7 §6
// v7 — backend translation scrapped (owner will architect a replacement);
// the language picker remains and drives dir/RTL + the wordmark only.

// v5 §14 — apply a color theme by swapping the body class (CSS-variable
// theme). Themes are mutually exclusive; colorblind_safe subsumes the old
// standalone colorblind toggle.
const THEME_CLASSES = ["theme-high_contrast", "theme-colorblind_safe",
                       "theme-amber_terminal",
                       // v6 §23
                       "theme-crimson_edge", "theme-cold_war", "theme-nightfall",
                       "theme-neon_grid", "theme-gunmetal", "theme-desert_ops",
                       "theme-crimson_gold", "theme-forest_floor", "theme-new_order", "theme-fire_rises",
                       "theme-royal_gold", "theme-synthwave"];
// v6.6 — cycle to the next theme (Ctrl/Cmd+T where the browser allows it,
// plain T always — Chrome reserves Ctrl+T for new-tab and won't yield it)
function cycleTheme() {
  const list = (state.clientConfig.themes || {}).available || ["dark_teal_default"];
  const cur = localStorage.getItem("tdl_theme") || "dark_teal_default";
  const i = list.indexOf(cur);
  applyTheme(list[(i + 1) % list.length]);
}
document.addEventListener("keydown", (ev) => {
  if (ev.target && /INPUT|TEXTAREA|SELECT/.test(ev.target.tagName)) return;
  if ((ev.key === "t" || ev.key === "T") && (ev.ctrlKey || ev.metaKey || !ev.altKey)) {
    if (ev.ctrlKey || ev.metaKey) ev.preventDefault();
    if (!ev.ctrlKey && !ev.metaKey && ev.key === "T") return; // shift+T free for later
    if (!ev.ctrlKey && !ev.metaKey && ev.key !== "t") return;
    cycleTheme();
  }
});

// v6.6.2 — single-key navigation shortcuts (owner-requested):
//   F = toggle live feed   L = next language   C = last/random country
//   G = globe mode         M = 2D map mode
// Plain unmodified keypresses only, and never while typing in a field.
document.addEventListener("keydown", (ev) => {
  if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
  if (ev.target && /INPUT|TEXTAREA|SELECT/.test(ev.target.tagName)) return;
  const k = ev.key.toLowerCase();
  if (k === "f") { setFeedVisible(feedPanelEl.style.display === "none"); }
  else if (k === "l") { cycleLanguage(); }
  else if (k === "c") { openLastOrRandomCountry(); }
  else if (k === "g") { switchToTier(1); }
  else if (k === "m") { switchToTier(2); }
  else if (ev.key === "?") { showHelp(); }   // v7.4.1 — open the full guide
});

function cycleLanguage() {   // v6.6.2 — advance to the next interface language
  const cur = localStorage.getItem("tdl_lang") || "en";
  const i = LANGUAGES.findIndex((l) => l.code === cur);
  const next = LANGUAGES[(i + 1) % LANGUAGES.length];
  setSiteLanguage(next.code);
  if (els.langBtn) els.langBtn.value = next.code;
}
function openLastOrRandomCountry() {   // v6.6.2 — last opened, or a random one
  let id = state.lastCountryId;
  if (!id) {
    const pool = BOUNDARIES_50M.filter((b) => b.i && b.i.length === 3);
    id = pool.length ? pool[Math.floor(Math.random() * pool.length)].i : "USA";
  }
  openEntity("country", id);
}
function switchToTier(tier) {   // v6.6.2 — G/M mode switch, persisted like the picker
  if (state.tier === tier) return;
  if (els.tierSelect) els.tierSelect.value = String(tier);
  try { localStorage.setItem("tdl_tier_override", String(tier)); } catch { /* ignore */ }
  mountRenderer(tier);
}

// v6.6.4 — selectable font style for the whole UI (and the map labels, which
// read the same family off the body). Persisted, applied on load.
const FONT_CLASSES = ["font-serif", "font-mono", "font-condensed", "font-rounded"];
function applyFont(font) {
  document.body.classList.remove(...FONT_CLASSES);
  if (font && font !== "sans") document.body.classList.add("font-" + font);
  localStorage.setItem("tdl_font", font || "sans");
  // let the renderer pick up the new family for its canvas labels
  const fam = getComputedStyle(document.body).fontFamily;
  state.renderer?.setLabelFont?.(fam);
}

function applyTheme(theme) {
  // v6.6.4 — strip EVERY theme-* class, not a hardcoded list. The old
  // THEME_CLASSES list went stale (missing theme-ember), so switching away
  // from the orange 'ember' theme never removed it — the theme got "stuck".
  for (const c of [...document.body.classList]) {
    if (c.startsWith("theme-")) document.body.classList.remove(c);
  }
  document.body.classList.remove("colorblind");
  document.body.classList.toggle("light-theme", theme === "light");
  if (theme && theme !== "dark_teal_default") {
    document.body.classList.add("theme-" + theme);
  }
  localStorage.setItem("tdl_theme", theme || "dark_teal_default");
  applyThemeToRenderer();   // v6.2 — retint globe/map to match
}

// v6.2 — themes now reach the globe + 2D map, not just the panels ("i want
// every part of the UI to be affected, even the globe and map coloring"). The
// active theme's --accent (already CSS-swapped per theme) is read from the
// computed style and turned into: an ocean tint (hue of the accent, softened
// so the sphere stays legible), an atmosphere/limb colour, and map coastline/
// graticule strokes. One accent read drives all of them, so every theme —
// including the new crimson+gold — visibly recolours the world, no per-theme
// shader table to maintain.
function hexToRgb01(hex) {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec((hex || "").trim());
  if (!m) return null;
  return [parseInt(m[1], 16) / 255, parseInt(m[2], 16) / 255, parseInt(m[3], 16) / 255];
}
function applyThemeToRenderer() {
  const r = state.renderer;
  if (!r || !r.setThemeColors) return;
  const cs = getComputedStyle(document.body);
  const accent = hexToRgb01(cs.getPropertyValue("--accent")) || [0.16, 0.38, 0.80];
  if (state.tier === 1) {
    // normalise the accent's brightness so the ocean multiplier keeps the
    // base sphere luminance but takes the accent's hue, then soften toward
    // neutral so the globe stays legible under any theme
    const avg = Math.max(0.001, (accent[0] + accent[1] + accent[2]) / 3);
    const mix = 0.55;   // 0 = neutral teal, 1 = full accent hue
    const ocean = accent.map((c) => 1 - mix + mix * (c / avg));
    const rim = accent.map((c) => 0.12 + 0.72 * c);   // atmosphere = accent glow
    r.setThemeColors(ocean, rim);
  } else {
    // 2D map coastline + graticule as translucent accent strokes
    const [ar, ag, ab] = accent.map((c) => Math.round(c * 255));
    r.setThemeColors(`rgba(${ar},${ag},${ab},0.5)`, `rgba(${ar},${ag},${ab},0.16)`);
  }
}

// v4 §2.3 — point-in-polygon now runs over Natural Earth 50m (bbox
// prefiltered), replacing the coarse 110m set that misplaced clicks
const BOUNDARIES_50M = decodeBoundaries(BOUNDARIES_50M_ENC);
function countryAt(lat, lon) { return countryAtPoint(BOUNDARIES_50M, lat, lon); }

// v6.1.1 — dynamic country label anchors, computed once from the largest ring
// of each country (rings are flat [lon,lat,...]). The label sits at that
// ring's bbox centre and carries its span in degrees; the renderer reveals it
// by apparent on-screen size, so big countries show from far and small ones
// only when zoomed in.
const COUNTRY_LABELS = BOUNDARIES_50M.map((c) => {
  let best = null, bestLen = 0;
  for (const ring of c.r) {
    if (ring.length > bestLen) { bestLen = ring.length; best = ring; }
  }
  if (!best || best.length < 6) return null;
  let mnLon = Infinity, mnLat = Infinity, mxLon = -Infinity, mxLat = -Infinity;
  for (let k = 0; k < best.length; k += 2) {
    const lon = best[k], lat = best[k + 1];
    mnLon = Math.min(mnLon, lon); mxLon = Math.max(mxLon, lon);
    mnLat = Math.min(mnLat, lat); mxLat = Math.max(mxLat, lat);
  }
  return { iso3: c.i, name: c.n, lat: (mnLat + mxLat) / 2, lon: (mnLon + mxLon) / 2,
           span: Math.max(mxLon - mnLon, mxLat - mnLat) };
}).filter(Boolean);
const ISO3_NAME = {};
for (const c of BOUNDARIES_50M) ISO3_NAME[c.i] = c.n;

const CATEGORIES = ["", "geopolitics", "finance", "technology", "disaster", "conflict", "military", "other"];
const CONTINENTS = ["", "Africa", "America", "Asia", "Europe", "Oceania", "Middle East"];
const MAP_REFRESH_MS = 45000;
const STORY_REFRESH_MS = 12000;   // v6.3 — feed safety-net poll (always streaming, faster)
const QUALITY_KEY = "tdl_quality";
const CALIB_KEY = "tdl_lod_calibration";
const RELEVANCE_KEY = "tdl_relevance_filter";

const els = {};
for (const id of ["marked-toggle", "sat-toggle", "sensors-toggle", "blocs-btn", "bloc-panel", "xr-btn", "conflict-tabs",
                  "conflicts-btn", "un-btn", "modes-btn", "modes-bar", "mode-legend",
                  "lang-btn", "brand-translit", "feed-header",
                  "lineage-overlay", "map-host", "feed-list", "tier-select",
                  "quality-select", "sound-toggle", "volume-slider", "preset-select",
                  "heatmap-toggle", "borders-toggle", "disputes-toggle", "actors-toggle",
                  "names-toggle", "spin-toggle", "tz-header",
                  "palette-btn", "briefing-btn", "graph-btn", "watchlist-btn", "whatif-btn", "audio-briefing-btn",
                  "bookmarks-btn", "stories-btn", "settings-btn", "snapshot-btn", "help-btn",
                  "watchlist-panel", "conn-badge", "map-filters", "graph-overlay",
                  "briefing-overlay", "status-drawer", "status-toggle",
                  "instability-value", "instability-spark", "instability-widget",
                  "scrubber-host", "feed-tools", "slide-pane", "alerts-host"]) {
  els[id.replace(/-(\w)/g, (_, c) => c.toUpperCase())] = document.getElementById(id);
}

const state = {
  renderer: null,
  tier: null,
  category: "",
  region: "",             // v4 §9.2 continent filter — one state, all views
  relevanceOn: localStorage.getItem(RELEVANCE_KEY) !== "0",   // v4 §9.1 default on
  asOf: null,
  watchlistOnly: false,
  syntheticMode: false,
  syntheticData: null,
  mapData: { events: [], links: [] },
  clientConfig: {
    graphics: { quality_tier: "high", idle_tour_seconds: 0, ambient_sound_default: false },
    globe: { hit_test_use_facing_occlusion: true, cluster_screen_distance_px: 40 },
    geocoding: { min_confidence_for_solid_marker: 0.6 },
    map2d: { wraparound_enabled: true },
    relevance: { global_relevance_default_filter: true, global_relevance_floor: 0.3 },
    audio: { master_gain_default: 0.4, preset: "ambient_default" },
    panes: { transition_duration_ms: 300 },
    alerts: { in_app_breaking_alert_severity_floor: 4 },
    onboarding: { require_ai_key_before_first_run: true },
    attribution: [],
  },
  conflictId: null,
  conflicts: [],
  markedOn: false,
  markedLocations: [],
  actorsOn: false,        // v4 §5.4
  actors: [],
  actorZones: [],         // v5 §11
  bordersOn: true,        // v4 §5.4 — default on
  disputesOn: false,      // v4 §5.3
  satOn: false,
  satellites: [],
  satTimer: null,
  cities: [],             // v4 §4.3
  // v4 §16 — focus context is timestamped and cleared on close/empty-click
  focusedEntity: null,
  // --- v6 ---
  warMode: null,          // §8 — active war-mode payload or null
  warTab: "",             // §8 — Military/Civilian/Diplomatic/Economic sub-filter
  lang: localStorage.getItem("tdl_lang") || "en",   // §11 site-wide language
  mapMode: null,          // §16 — active thematic mode id
  cityLights: localStorage.getItem("tdl_citylights") !== "0",   // §24
};

function setFocus(type, name) {
  state.focusedEntity = type ? { type, name, set_at: Date.now() } : null;
}

// ---------- the shared pane (§6/§17/§18) + navigation context ----------

const pane = new SlidePane(els.slidePane, {
  durationMs: state.clientConfig.panes.transition_duration_ms,
  resizable: (state.clientConfig.panels || {}).resizable !== false,   // v5 §10
  minWidth: (state.clientConfig.panels || {}).min_width_px || 280,
  maxWidth: (state.clientConfig.panels || {}).max_width_px || 900,
  persist: (state.clientConfig.panels || {}).persist_across_restarts !== false, // §21
  onNavigate: (entry) => {
    // §16.2 — closing the pane (entry=null) clears the analyst focus;
    // v6 §26 — it also clears the pulsing map highlight
    // v6.6.4 — alignment mode auto-disables when we leave a country panel
    // (owner: "auto disable alignment mode if navigated to another page").
    if (!entry || entry.targetType !== "country") {
      if (state.alignmentIso) { applyAlignmentOverlay(null); state.alignmentIso = null; }
      // v7.4.1 — recognition overlay also auto-clears when leaving a country panel
      if (state.recognitionIso) { state.renderer?.setColoredRings?.(null); state.recognitionIso = null; }
    }
    if (!entry) {
      // v7.4 — fully closing the war-mode pane exits war mode (owner: "War
      // mode should exit when the associated war panel is closed fully").
      if (state.warMode) exitWarMode();
      setFocus(null); state.renderer?.setHighlight?.(null); return;
    }
    if (entry.focus) setFocus(entry.focus.type, entry.focus.name);
  },
});

const ctx = {
  openStory: (id) => openStory(id),
  // v7.4 — open a conflict by ENTERING WAR MODE (fetches it by id), so a
  // conflict chip on an NSA / country / bloc panel always opens even when the
  // conflict isn't in the pre-loaded state.conflicts list (owner: "Conflicts
  // dont link properly from certain pages such as NSA panels"). selectConflict
  // silently no-op'd on an unloaded id.
  openConflict: (id) => { pane.close(); enterWarMode(id); },
  openEntity: (type, id, opts) => openEntity(type, id, opts),
  openCompare: (a, b) => pane.push({
    key: `cmp:${a}:${b}`, title: "compare",
    render: (el) => Wiki.renderCompare(el, a, b, ctx),
  }),
  openDirectory: (type) => pane.push({
    key: `dir:${type || "all"}`, title: "stories directory",
    render: (el) => Wiki.renderStoriesDirectory(el, ctx, type),
  }, { replace: pane.top() && String(pane.top().key).startsWith("dir:") }),
  openRegion: (region) => {                // v5 §20 / v6 §26
    api.regionSummary(region).then((d) =>
      highlightCountries((d.countries || []).map((c) => c.id))).catch(() => {});
    return pane.push({
      key: `region:${region}`, title: region,
      render: (el) => Wiki.renderRegion(el, region, ctx),
    });
  },
  setColorblind: (on) => {
    document.body.classList.toggle("colorblind", on);
    localStorage.setItem("tdl_colorblind", on ? "1" : "0");
  },
  setTheme: (theme) => applyTheme(theme),           // v5 §14
  setFont: (font) => applyFont(font),               // v6.6.4 font style
  font: () => localStorage.getItem("tdl_font") || "sans",
  languages: () => LANGUAGES,                         // v5 §2
  setLanguage: (code) => setSiteLanguage(code),       // v6 §11 — site-wide
  themes: () => (state.clientConfig.themes || {}).available
      || ["dark_teal_default", "high_contrast", "colorblind_safe", "amber_terminal"],
  setCityLights: (on) => {                            // v6 §24
    state.cityLights = !!on;
    localStorage.setItem("tdl_citylights", on ? "1" : "0");
    state.renderer?.setCityLights?.(on);
  },
  cityLights: () => state.cityLights,
  setAlertsEnabled: (on) => {                         // v6.6.2 breaking-alert toggle
    alerts.enabled = !!on;
    localStorage.setItem("tdl_alerts_enabled", on ? "1" : "0");
  },
  alertsEnabled: () => alerts.enabled,
  onTimeSettingsChanged: () => refreshStories().catch(() => {}),  // v6.1.1 tz re-render
  onAiKeySaved: async () => {                                      // v6.2 instant ping
    try { state.clientConfig = { ...state.clientConfig, ...(await api.config()) }; }
    catch { /* keep old config */ }
    refreshStories().catch(() => {});
    // the background warm-up needs a few seconds to produce; re-pull then
    setTimeout(() => refreshStories().catch(() => {}), 6000);
    setTimeout(() => refreshStories().catch(() => {}), 15000);
  },
  enterWarMode: (cid) => enterWarMode(cid),           // v6 §8
  openLeader: (name) => pane.push({                    // v6.6 — leader profile
    title: name, key: "leader:" + name,
    render: (el) => Wiki.renderLeader(el, name, ctx),
  }),
  // v6.6.2 — alignment overlay is now a toggle: clicking the same country's
  // button again turns it off; navigating to a different country re-targets.
  // Returns the new on/off state so the button label can reflect it.
  showAlignments: (iso3, alignments) => {
    if (state.alignmentIso === iso3) {          // same country → toggle off
      applyAlignmentOverlay(null);
      state.alignmentIso = null;
      return false;
    }
    applyAlignmentOverlay(alignments);
    state.alignmentIso = iso3;
    return true;
  },
  alignmentActive: () => state.alignmentIso || null,
  // v7.4.1 — recognition map mode: color who recognizes a partially-recognized
  // state (green) vs who doesn't (red), the subject itself gold. Toggle.
  showRecognition: async (iso3) => {
    if (state.recognitionIso === iso3) {
      state.renderer?.setColoredRings?.(null);
      state.recognitionIso = null;
      return false;
    }
    try {
      const v = await api.recognition(iso3);
      const ringsFor = (isos) => {
        const r = [];
        for (const i of isos) {
          const c = BOUNDARIES_50M.find((b) => b.i === i);
          if (c) r.push(...c.r);
        }
        return r;
      };
      const groups = [];
      const rec = ringsFor(v.recognizers || []);
      const non = ringsFor(v.non_recognizers || []);
      const subj = ringsFor([iso3]);
      if (rec.length) groups.push({ color: [0.15, 0.8, 0.35], rings: rec });
      if (non.length) groups.push({ color: [0.9, 0.3, 0.25], rings: non });
      if (subj.length) groups.push({ color: [1.0, 0.78, 0.2], rings: subj });
      state.renderer?.setColoredRings?.(groups.length ? groups : null);
      state.recognitionIso = iso3;
      alerts.toast?.(`Recognition of ${v.name}: green = recognizes (${v.recognizer_count}), red = does not`);
      return true;
    } catch { return false; }
  },
  recognitionActive: () => state.recognitionIso || null,
  openThread: (id) => pane.push({                     // v6 §27
    key: `thread:${id}`, title: "story thread",
    render: (el) => Wiki.renderThread(el, id, ctx),
  }),
  openUN: () => pane.push({                            // v6.1 UN panel
    key: "un", title: "United Nations",
    render: (el) => Wiki.renderUN(el, ctx),
  }),
  openDisputedZones: () => pane.push({                 // v6.6.2 disputed territories
    key: "disputed", title: "Disputed territories",
    render: (el) => Wiki.renderDisputedZones(el, ctx),
  }),
  openDisputedZone: (zid) => pane.push({
    key: "disputed:" + zid, title: "disputed territory",
    render: (el) => Wiki.renderDisputedZone(el, zid, ctx),
  }),
  openAutonomousZones: () => pane.push({                 // v7.4.1 autonomous regions
    key: "autonomous", title: "Autonomous regions",
    render: (el) => Wiki.renderAutonomousZones(el, ctx),
  }),
  openAutonomousZone: (zid) => pane.push({
    key: "autonomous:" + zid, title: "autonomous region",
    render: (el) => Wiki.renderAutonomousZone(el, zid, ctx),
  }),
  openEntityByName: (type, name) => {                    // v7.4.1 resolve name→iso3
    const c = BOUNDARIES_50M.find((b) => b.n && b.n.toLowerCase() === (name || "").toLowerCase());
    if (c && c.i) openEntity(type, c.i);
  },
  openPartyDossier: (name, iso) => pane.push({           // v7.4.2 party dossier by name
    key: `party-dossier:${name}`, title: name.slice(0, 40),
    render: (el) => Wiki.renderPartyDossier(el, name, iso, ctx),
  }),
  openCountryStat: (iso3, metric, name) => pane.push({   // v6.6.5 stat detail
    key: `stat:${iso3}:${metric}`, title: metric,
    render: (el) => Wiki.renderCountryStat(el, iso3, metric, name, ctx),
  }),
  openAntarctica: () => pane.push({                      // v6.6.6 Antarctica page
    key: "antarctica", title: "Antarctica",
    render: (el) => Wiki.renderAntarctica(el, ctx),
  }),
};
pane.openEntity = (type, id, opts) => openEntity(type, id, opts);

const ENTITY_RENDER = {
  country: (el, id) => Wiki.renderCountry(el, id, ctx),
  party: (el, id) => Wiki.renderParty(el, id, ctx),
  person: (el, id) => Wiki.renderPerson(el, id, ctx),
  non_state_actor: (el, id) => Wiki.renderActor(el, id, ctx),
  org: (el, id) => Wiki.renderOrg(el, id, ctx),
  alliance: (el, id) => Wiki.renderAlliance(el, id, ctx),
};

// v6.6.2 — paint the diplomatic-alignment overlay (allies green / partners
// light-green / rivals red). Passing null clears it.
function applyAlignmentOverlay(alignments) {
  if (!alignments) { state.renderer?.setColoredRings?.(null); return; }
  const tone = { strong: [0.15, 0.85, 0.3], partner: [0.55, 0.9, 0.55],
                 rival: [0.95, 0.25, 0.2] };
  const groups = [];
  for (const [kind, isos] of Object.entries(alignments || {})) {
    const rings = [];
    for (const iso of isos) {
      const c = BOUNDARIES_50M.find((b) => b.i === iso);
      if (c) rings.push(...c.r);
    }
    if (rings.length) groups.push({ color: tone[kind] || [0.7, 0.7, 0.7], rings });
  }
  state.renderer?.setColoredRings?.(groups.length ? groups : null);
}

// v6 §26 — pulse the focused country/region borders on the map; cleared by
// the pane's onNavigate(null) when the panel closes
function highlightCountries(iso3List) {
  const rings = [];
  for (const c of BOUNDARIES_50M) {
    if (iso3List.includes(c.i)) rings.push(...c.r);
  }
  state.renderer?.setHighlight?.(rings.length ? rings : null);
}

async function openEntity(type, id, { replace = false } = {}) {
  const render = ENTITY_RENDER[type];
  if (!render) return;
  // v6.6.6 — navigating to any entity leaves War Mode (owner: "exit war mode
  // automatically when navigating away from it"). The war coloring, edge glow
  // and feed all restore before the new page opens.
  if (state.warMode) exitWarMode();
  if (type === "country") { highlightCountries([id]); state.lastCountryId = id; }   // v6 §26 / v6.6.2 C-shortcut
  await pane.push({
    key: `${type}:${id}`,
    title: type.replace(/_/g, " "),
    targetType: type,
    targetId: id,
    sequence: { type, id },        // §6.2 prev/next arrows
    focus: { type, name: id },     // refined after load for countries
    render: async (el) => {
      await render(el, id);
      const h1 = el.querySelector("h1, h2");
      if (h1) {
        // first text node only — skip the iso3 / thin-coverage badge spans
        const name = (h1.childNodes[0]?.textContent || h1.textContent).trim();
        setFocus(type, name);
        pane.host.querySelector(".pane-title").textContent = name.slice(0, 48);
      }
    },
  }, { replace });
}

// v5 §9 — a dense cluster that zoom can't split opens its member events as a
// scrollable list in the shared sliding pane (same pane, list template).
function openClusterList(cluster) {
  const members = (cluster.members || []).slice()
    .sort((a, b) => (b.severity || 0) - (a.severity || 0)
      || (b.occurred_at || "").localeCompare(a.occurred_at || ""));
  pane.push({
    key: `cluster:${cluster.lat.toFixed(2)}:${cluster.lon.toFixed(2)}:${members.length}`,
    title: `${members.length} events here`,
    render: (el) => {
      el.innerHTML = `<h1>${members.length} events in this cluster</h1>
        <p class="cp-meta">Too many overlapping points to separate by zoom — browse them
          all here. Sorted by severity, then recency.</p>
        <button class="full-summary-btn pan-cluster">⌖ Pan to this area</button>
        <div class="cluster-list"></div>`;
      // v7.4.1 — a panel-level Pan-to-Event control (owner: "pan event button
      // should be available from within the event panel as well"). Flies to the
      // cluster centroid; individual rows keep their own per-event pan buttons.
      const panCluster = el.querySelector(".pan-cluster");
      if (cluster.lat != null && cluster.lon != null) {
        panCluster.addEventListener("click", () =>
          state.renderer?.flyTo?.(cluster.lat, cluster.lon,
            state.tier === 1 ? 2.0 : undefined, 900));
      } else { panCluster.remove(); }
      const list = el.querySelector(".cluster-list");
      for (const ev of members) {
        const row = document.createElement("div");
        row.className = "story-card cluster-row";
        const cat = ev.category || "other";
        row.innerHTML = `<div class="card-meta">
            <span class="chip cat-${cat}">${cat}</span>
            <span class="cp-meta">sev ${ev.severity || "?"}</span>
            ${ev.development_type ? `<span class="chip">${ev.development_type}</span>` : ""}
            <span class="cp-meta" style="margin-left:auto">${(ev.occurred_at || "").slice(0, 16).replace("T", " ")}</span>
          </div><h3></h3><p class="cp-meta"></p>
          <button class="ap-chip pan-to-event">⌖ Pan to Event</button>`;
        row.querySelector("h3").textContent = ev.title || "(untitled event)";
        row.querySelector("p").textContent = ev.location_name || "";
        // v6.6.7 — Pan to Event: fly the map to wherever the event was placed
        const panBtn = row.querySelector(".pan-to-event");
        if (ev.lat != null && ev.lon != null) {
          panBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            state.renderer?.flyTo?.(ev.lat, ev.lon, state.tier === 1 ? 2.0 : undefined, 900);
          });
        } else { panBtn.remove(); }
        // v7.4.2 — EVERY row is clickable (owner: "why from cluster lists are
        // some stories not clickable but listed?"). A correlated event opens its
        // story; a not-yet-correlated event flies the map to it (and says so).
        row.style.cursor = "pointer";
        if (ev.story_id) {
          row.addEventListener("click", () => openStory(ev.story_id));
        } else {
          row.querySelector("p").textContent += " · standalone event — click to locate";
          row.addEventListener("click", () => {
            if (ev.lat != null && ev.lon != null) {
              state.renderer?.flyTo?.(ev.lat, ev.lon, state.tier === 1 ? 2.0 : undefined, 900);
            }
          });
        }
        list.appendChild(row);
      }
    },
  });
}

// v7.4.1 — click a source in the health drawer to browse the stories + events
// it fed (owner: "in the sources tab you should be able to click on a source
// and see the stories sourced from that source").
function openSourceStories(src) {
  pane.push({
    key: `source:${src.id}`,
    title: src.name.slice(0, 40),
    render: async (el) => {
      el.innerHTML = `<h1>${src.name}</h1>
        <p class="cp-meta">${src.type || ""}${src.reliability_tier ? " · " + src.reliability_tier + " reliability" : ""} — stories and events sourced from this outlet.</p>
        <div class="src-stories"><p class="cp-meta">loading…</p></div>`;
      const box = el.querySelector(".src-stories");
      try {
        const data = await api.sourceStories(src.id);
        box.innerHTML = "";
        if (!(data.stories || []).length && !(data.uncorrelated_events || []).length) {
          box.innerHTML = `<p class="cp-meta">No stored stories or events from this source yet.</p>`;
          return;
        }
        for (const s of data.stories || []) {
          const row = document.createElement("div");
          row.className = "story-card";
          row.style.cursor = "pointer";
          row.innerHTML = `<h3></h3>
            <div class="card-meta"><span class="badge-src">${s.n_events || 0} ev</span>
            <span class="cp-meta" style="margin-left:auto">${(s.last_occurred || s.first_seen_at || "").slice(0, 10)}</span></div>`;
          row.querySelector("h3").textContent = s.headline || "(untitled story)";
          row.addEventListener("click", () => openStory(s.id));
          box.appendChild(row);
        }
        if ((data.uncorrelated_events || []).length) {
          const h = document.createElement("h4");
          h.textContent = "Recent events (not yet in a story)";
          h.style.marginTop = "14px";
          box.appendChild(h);
          for (const e of data.uncorrelated_events) {
            const row = document.createElement("div");
            row.className = "story-card cluster-row";
            const cat = e.category || "other";
            row.innerHTML = `<div class="card-meta"><span class="chip cat-${cat}">${cat}</span>
              <span class="cp-meta" style="margin-left:auto">${(e.occurred_at || "").slice(0, 10)}</span></div><h3></h3><p class="cp-meta"></p>`;
            row.querySelector("h3").textContent = e.title || "(untitled event)";
            row.querySelector("p").textContent = e.location_name || "";
            box.appendChild(row);
          }
        }
      } catch (err) {
        box.innerHTML = `<p class="cp-meta">Couldn't load: ${err.message}</p>`;
      }
    },
  });
}

// v5 §1 — History / archive view: the permanent fact chain already stores
// everything, so this is a browsing UI over it (paginated, date + category
// filtered), not new storage. Opens in the shared sliding pane.
function openHistory() {
  pane.push({
    key: "history",
    title: "history / archive",
    render: async (el) => {
      el.innerHTML = `<h1>History</h1>
        <p class="cp-meta">The full permanent fact chain — browse past stories by date and category.</p>
        <div class="hist-controls">
          <label>from <input type="date" class="h-from"></label>
          <label>to <input type="date" class="h-to"></label>
          <select class="h-cat"><option value="">all categories</option>
            <option>geopolitics</option><option>finance</option><option>technology</option>
            <option>disaster</option><option>conflict</option><option>military</option><option>other</option></select>
        </div>
        <div class="hist-list"></div>
        <div class="hist-more"><button class="h-more">load more</button></div>`;
      const listEl = el.querySelector(".hist-list");
      let offset = 0;
      const load = async (reset) => {
        if (reset) { offset = 0; listEl.innerHTML = ""; }
        const from = el.querySelector(".h-from").value;
        const to = el.querySelector(".h-to").value;
        const data = await api.stories({
          limit: 30, offset, sort: "oldest",
          category: el.querySelector(".h-cat").value || undefined,
          from: from ? from + "T00:00:00Z" : undefined,
          to: to ? to + "T23:59:59Z" : undefined,
        }).catch(() => ({ stories: [] }));
        for (const s of data.stories || []) {
          const row = document.createElement("div");
          row.className = "story-card";
          row.style.cursor = "pointer";
          row.innerHTML = `<div class="card-meta">
              <span class="chip cat-${s.category || "other"}">${s.category || "other"}</span>
              <span class="cp-meta" style="margin-left:auto">${(s.first_seen_at || "").slice(0, 10)}</span>
            </div><h3></h3>`;
          row.querySelector("h3").textContent = s.headline || "(untitled)";
          row.addEventListener("click", () => openStory(s.id));
          listEl.appendChild(row);
        }
        offset += (data.stories || []).length;
        el.querySelector(".hist-more").style.display =
          (data.stories || []).length < 30 ? "none" : "block";
      };
      el.querySelectorAll(".hist-controls input, .hist-controls select").forEach((c) =>
        c.addEventListener("change", () => load(true)));
      el.querySelector(".h-more").addEventListener("click", () => load(false));
      await load(true);
    },
  });
}

// ---------- shell components ----------

const lineageView = new LineageView(els.lineageOverlay, {
  onOpenStory: (id) => openStory(id),
});
const storyPage = new StoryPage(pane, {
  onOpenStory: (id) => openStory(id),
  onWatch: () => watchlist.refresh(),
  onOpenLineage: (factId) => lineageView.open(factId),
  onPanTo: (lat, lon) => state.renderer?.flyTo?.(lat, lon, state.tier === 1 ? 2.0 : undefined, 900),
  onOpenEntity: (type, id) => {                       // v7.4.1 impacted chips
    // territories are country rows (status='territory') so they open as a
    // country page; zones (marked_locations) fall back to the disputed directory
    if (type === "territory") openEntity("country", id);
    else if (type === "zone") ctx.openDisputedZones && ctx.openDisputedZones();
    else openEntity(type, id);
  },
});
const feed = new LiveFeed(els.feedList, { onOpenStory: (id) => openStory(id),
  onOpenConflict: (cid) => enterWarMode(cid) });   // v6.6.2 conflict chip → War Mode
const instChart = new InstabilityChart(els.instabilityValue, els.instabilitySpark);
const statusPanel = new StatusPanel(els.statusDrawer, els.statusToggle,
  (src) => openSourceStories(src));   // v7.4.1 — click a source → its stories
const graphExplorer = new GraphExplorer(els.graphOverlay);
// v6.1 — music plays from the start by default (owner request). A saved
// preference still wins; armAutoplay() (below) works around the browser
// autoplay policy by resuming on the first user gesture.
const sound = new SoundEngine(true);
const alerts = new Alerts(els.alertsHost, {
  severityFloor: 4,
  onOpenStory: (id) => openStory(id),
});

function setConn(mode) {
  els.connBadge.className = `conn-${mode}`;
  els.connBadge.textContent =
    mode === "live" ? "live" : mode === "polling" ? "polling (15s)"
    : mode === "capsule" ? "time capsule" : "offline";
}

// ---------- story deep links (§5.3) ----------

function openStory(id, { push = true } = {}) {
  if (push) history.pushState({ storyId: id }, "", `/story/${id}`);
  // v7 §6 — learn interests locally from what the user actually opens
  const st = feed?.snapshot?.().find((x) => x.id === id);
  if (st) morning.trackInterest(st);
  // v7.4.4 — the synthetic/demo path was deleted; every story is a real
  // backend story now.
  storyPage.open(id);
}
window.addEventListener("popstate", (ev) => {
  if (ev.state && ev.state.storyId) openStory(ev.state.storyId, { push: false });
  else pane.close();
});

function onSelectEvent(event) {
  if (event.story_id) openStory(event.story_id);
}

// ---------- tier + quality management (§5) ----------

function currentQuality() {
  return localStorage.getItem(QUALITY_KEY) || state.clientConfig.graphics.quality_tier;
}

function mountRenderer(tier) {
  if (state.renderer) { state.renderer.destroy(); state.renderer = null; }
  els.mapHost.innerHTML = "";
  const g4 = state.clientConfig.globe || {};
  const opts = {
    onSelectEvent,
    quality: currentQuality(),
    idleTourSeconds: state.clientConfig.graphics.idle_tour_seconds,
    clusterScreenDistancePx: g4.cluster_screen_distance_px || 40,   // §2.2
    facingOcclusion: g4.hit_test_use_facing_occlusion !== false,    // §2.1
    minConfidenceSolid:
      (state.clientConfig.geocoding || {}).min_confidence_for_solid_marker ?? 0.6,
    lodCalibration: parseFloat(localStorage.getItem(CALIB_KEY) || "1"),  // §15.4
    wraparound: (state.clientConfig.map2d || {}).wraparound_enabled !== false, // §4.2
    countryAt,
    onSelectLocation: (loc) => {
      setFocus("location", loc.name);
      if (loc.country_id) openEntity("country", loc.country_id);
      else if (loc.conflict_id) selectConflict(loc.conflict_id, { forceOn: true });
    },
    onSelectActor: (a) => {           // v4 §5.4
      setFocus("non_state_actor", a.name);
      openEntity("non_state_actor", a.id);
    },
    onSelectCluster: (cluster) => openClusterList(cluster),   // v5 §9
    onSelectDisputed: (z) => ctx.openDisputedZone(z.id),      // v6.6.4 disputed marker
    onCountryClick: (lat, lon) => {
      let c = countryAt(lat, lon);
      // v6.2 — small island nations (Mauritius, Comoros, Malta, Seychelles…)
      // have tiny polygons that a click almost never lands exactly on, so they
      // felt like they "don't exist". If the direct hit misses, snap to the
      // nearest small-country centroid within ~2.5° and open that.
      if (!c) {
        let best = null, bestD = 2.5;
        for (const l of COUNTRY_LABELS) {
          if (l.span > 6) continue;   // only snap to genuinely small states
          const d = Math.hypot(l.lat - lat, (l.lon - lon)
            * Math.cos(lat * Math.PI / 180));
          if (d < bestD) { bestD = d; best = l; }
        }
        if (best) c = { i: best.iso3, n: best.name };
      }
      if (c) {
        setFocus("country", c.n);
        openEntity("country", c.i);
      } else if (lat < -60) {
        // v6.6.6 — Antarctica has no country polygon; clicking it used to be
        // blank. Open a dedicated Antarctica page (Treaty + the 7 claims).
        setFocus("region", "Antarctica");
        ctx.openAntarctica();
      } else {
        setFocus(null);               // §16.2 — empty-space click clears focus
      }
    },
  };
  try {
    if (tier === 1) state.renderer = new Tier1Globe(els.mapHost, opts);
    else if (tier === 2) state.renderer = new Tier2Map(els.mapHost, opts);
    else state.renderer = new Tier3List(els.mapHost, opts);
    state.tier = tier;
  } catch (err) {
    console.warn(`tier ${tier} failed (${err.message}), degrading`);
    mountRenderer(tier === 1 ? 2 : 3);
    return;
  }
  state.renderer.setHeatmap?.(els.heatmapToggle.classList.contains("active"));
  state.renderer.setBorders?.(state.bordersOn);
  if (state.spinOn) state.renderer.setAutoSpin?.(true);   // v6.6.6 re-apply auto-spin
  state.renderer.setDisputes?.(state.disputesOn);
  if (state.disputesOn && state.disputedZones)   // v6.6.4 re-apply clickable markers
    state.renderer.setDisputedZones?.(state.disputedZones);
  if (state.markedOn) state.renderer.setMarkedLocations?.(state.markedLocations);
  if (state.actorsOn) {
    state.renderer.setActors?.(state.actors);
    state.renderer.setActorZones?.(state.actorZones);   // v5 §11
  }
  if (state.cities.length) state.renderer.setCities?.(state.cities);
  state.renderer.setCountryLabels?.(COUNTRY_LABELS);   // v6.1.1 dynamic labels
  if (state.renderer && state.renderer.onSelectRegion !== undefined)
    state.renderer.onSelectRegion = (region) => ctx.openRegion(region);  // v6.6
  applyBlocOverlay();
  // v6 §31 — WebXR isn't functional yet: keep the button hidden until the
  // config flips ui.vr_button_visible (the underlying spec stays intact)
  const vrVisible = (state.clientConfig.ui || {}).vr_button_visible === true;
  els.xrBtn.classList.toggle("hidden",
    !(vrVisible && state.tier === 1 && window.__xrSupported));
  // v6.1.1 — terrain button hidden unless ui.terrain_button_visible (the biome
  // texture drops most interior land, so it read as misplaced blobs)
  // v6.2 — country labels honor the names toggle
  state.renderer?.setCountryLabelsVisible?.(state.namesOn !== false);
  applyThemeToRenderer();   // v6.2 — retint globe/map for the active theme
  state.renderer?.setCityLights?.(state.cityLights);   // v6 §24
  pushMapData();
  if (tier === 1) calibrateOnce();
}

// v4 §15.4 — one-time first-launch calibration: measure real frame time
// on this machine and scale the cluster/label density threshold to match
function calibrateOnce() {
  if (localStorage.getItem(CALIB_KEY)) return;
  const samples = [];
  let last = performance.now();
  const probe = (t) => {
    samples.push(t - last);
    last = t;
    if (samples.length < 40) { requestAnimationFrame(probe); return; }
    const avg = samples.slice(10).reduce((s, x) => s + x, 0) / (samples.length - 10);
    const factor = avg > 40 ? 1.8 : avg > 24 ? 1.3 : 1;
    localStorage.setItem(CALIB_KEY, String(factor));
    if (factor > 1 && state.renderer) state.renderer.clusterPx =
      (state.clientConfig.globe.cluster_screen_distance_px || 40) * factor;
  };
  requestAnimationFrame(probe);
}

function relevanceFloor() {
  return state.relevanceOn
    ? (state.clientConfig.relevance || {}).global_relevance_floor ?? 0.3 : null;
}

function pushMapData() {
  if (!state.renderer) return;
  const { events, links } = state.mapData;
  let filtered = state.category
    ? events.filter((e) => e.category === state.category) : events;
  if (state.region) {   // §9.2 — continent filter applied map-side via PIP
    filtered = filtered.filter((e) => {
      const c = countryAt(e.lat, e.lon);
      return c && countryRegionMatches(c.i, state.region);
    });
  }
  const storyIds = new Set(filtered.map((e) => e.story_id).filter(Boolean));
  state.renderer.setData({
    events: filtered,
    links: (links || []).filter((l) => storyIds.has(l.story_id)),
    cluster_config: state.mapData.cluster_config,
  });
}

let regionByIso = new Map();
function countryRegionMatches(iso3, region) {
  const r = regionByIso.get(iso3) || "";
  if (region === "America") return r.includes("America") || r.includes("Caribbean");
  if (region === "Middle East") return r.includes("Middle East") || r.includes("Western Asia");
  return r.includes(region);
}

// ---------- filters (§6.4 + v4 §9) ----------

for (const cat of CATEGORIES) {
  const chip = document.createElement("button");
  chip.className = "filter-chip" + (cat === "" ? " active" : "");
  chip.dataset.cat = cat;
  chip.textContent = cat || "all";
  chip.addEventListener("click", () => {
    state.category = cat;
    document.querySelectorAll(".filter-chip[data-cat]").forEach((c) =>
      c.classList.toggle("active", c === chip));
    pushMapData();
    refreshStories().catch(() => {});
  });
  els.mapFilters.appendChild(chip);
}
// §9.2 continent filter — one shared state across feed, map and directory
const contSel = document.createElement("select");
contSel.className = "filter-chip";
contSel.title = "continent filter (feed + map + stories, one state)";
for (const c of CONTINENTS) {
  const o = document.createElement("option");
  o.value = c; o.textContent = c || "🌐 all regions";
  contSel.appendChild(o);
}
contSel.addEventListener("change", () => {
  state.region = contSel.value;
  pushMapData();
  refreshStories().catch(() => {});
});
els.mapFilters.appendChild(contSel);
// §9.1 relevance-floor toggle, default ON per the product's purpose
const relChip = document.createElement("button");
relChip.className = "filter-chip" + (state.relevanceOn ? " active" : "");
relChip.textContent = "global only";
relChip.title = "hide low-relevance local coverage (v4 §9.1)";
relChip.addEventListener("click", () => {
  state.relevanceOn = !state.relevanceOn;
  localStorage.setItem(RELEVANCE_KEY, state.relevanceOn ? "1" : "0");
  relChip.classList.toggle("active", state.relevanceOn);
  refreshMap().catch(() => {});
  refreshStories().catch(() => {});
});
els.mapFilters.appendChild(relChip);

const exportChip = document.createElement("a");
exportChip.className = "filter-chip";
exportChip.textContent = "⤓ csv";
exportChip.title = "export current events as CSV";
els.mapFilters.appendChild(exportChip);
function updateExportLink() {
  const q = new URLSearchParams({ format: "csv" });
  if (state.category) q.set("category", state.category);
  if (state.asOf) q.set("as_of", state.asOf);
  exportChip.href = `/api/events?${q}`;
}

// ---------- data loading ----------

async function refreshStories() {
  // v7.4.2 — War Mode no longer filters the live feed (owner: "war mode
  // SHOULDN'T filter the live feed itself at all"). The live feed is always the
  // full global feed; a conflict's own stories/events/analysis live in the
  // dedicated War Mode panel instead. So conflict_id / war_tab are gone here.
  const data = await api.stories({ limit: 60, category: state.category || undefined,
                                   as_of: state.asOf || undefined,
                                   watchlist: state.watchlistOnly ? "1" : undefined,
                                   min_relevance: relevanceFloor() ?? undefined,
                                   region: state.region || undefined,
                                   sort: state.feedSort || undefined,          // v5 §1
                                   development_type: state.devType || undefined });
  // v7 — feed renders in English (translation scrapped; owner will
  // architect a replacement).
  const stories = data.stories || [];
  feed.setStories(stories);
  feed.currentIds = stories;
}

async function refreshMap() {
  state.mapData = await api.mapEvents({ as_of: state.asOf || undefined,
                                        min_relevance: relevanceFloor() ?? undefined });
  pushMapData();
  updateExportLink();
}

async function refreshInstability() {
  const data = await api.instability("72h", state.asOf);
  instChart.update(data);
  if (!state.asOf && data.latest) {
    sound.setInstability(data.latest.score);
    analyst.setInstability(data.latest.score);
    state.lastInstability = data.latest.score;
  }
}

// ---------- time capsule (§4) ----------

let liveSuspended = false;
const scrubber = new TimeScrubber(els.scrubberHost, {
  onAsOfChange: (asOf) => {
    state.asOf = asOf;
    liveSuspended = asOf !== null;
    setConn(asOf ? "capsule" : "live");
    Promise.all([refreshStories(), refreshMap(), refreshInstability()]).catch(() => {});
  },
});

// ---------- live wiring ----------

async function loadReal() {
  // v7.4.3/v7.4.4 — the backend is the source of truth. If /api/config answers,
  // the backend is REACHABLE and the app is LIVE. The bundled demo dataset was
  // DELETED in v7.4.4 (owner: "delete the synthetic data, I don't need it"), so
  // there is no fake-data path left at all; a config failure just shows an
  // honest "backend not reachable" offline screen. A hiccup in one feed fetch
  // must not swap the whole app off the live backend.
  const cfgData = await api.config();   // throws → real "API unavailable" → offline screen
  if (cfgData) state.clientConfig = { ...state.clientConfig, ...cfgData };
  // v7 — patch-version badge next to the wordmark (owner: "so I know I'm
  // running the right patch"); sourced from the backend's APP_VERSION.
  if (cfgData && cfgData.app_version) {
    const v = document.getElementById("brand-version");
    if (v) v.textContent = "v" + cfgData.app_version;
  }
  if (!localStorage.getItem(QUALITY_KEY)) {
    els.qualitySelect.value = state.clientConfig.graphics.quality_tier;
  }
  document.documentElement.style.setProperty("--pane-ms",
    ((state.clientConfig.panes || {}).transition_duration_ms ?? 300) + "ms");
  alerts.severityFloor =
    (state.clientConfig.alerts || {}).in_app_breaking_alert_severity_floor ?? 4;
  sound.volume = localStorage.getItem("tdl_sound_vol") !== null
    ? sound.volume : (state.clientConfig.audio || {}).master_gain_default ?? 0.4;
  els.volumeSlider.value = String(Math.round(sound.volume * 100));

  // v7.4.3 — config succeeded, so the backend is live. A failure in any single
  // feed/map/instability fetch must NOT throw out of loadReal (that would drop
  // the whole app into the bundled demo dataset). Each is best-effort; the
  // safety-net pollers below keep retrying, and a real error surfaces in the
  // console + an empty-but-live feed, never fake [SYNTHETIC] stories.
  await refreshStories().catch((e) => {
    console.error("live feed fetch failed (staying live, will retry):", e);
    els.feedList.innerHTML = `<p class="cp-meta">Connecting to the live feed…</p>`;
  });
  await refreshMap().catch((e) => console.error("map fetch failed:", e));
  await refreshInstability().catch((e) => console.error("instability fetch failed:", e));
  setConn("live");
  loadCities().catch(() => {});
  checkOnboarding().catch(() => {});
  loadCompleteness().catch(() => {});

  const socket = new FeedSocket({
    onStateChange: (mode) => { if (!liveSuspended) setConn(mode); },
    onMessage: async (msg) => {
      if (liveSuspended) return;
      if (msg.type === "event_created") {
        const p = msg.payload;
        sound.onLiveEvent(p);            // §12.3 data sonification
        sound.noteSeverity(p.severity);
        if (p.location) {
          state.mapData.events.unshift({ id: p.id, title: p.title,
            lat: p.location.lat, lon: p.location.lon,
            location_name: p.location_name, category: p.category,
            severity: p.severity, occurred_at: p.occurred_at,
            geocode_confidence: p.geocode_confidence,
            global_relevance_score: p.global_relevance_score, story_id: null });
          pushMapData();
          state.renderer?.burst?.(p.location.lat, p.location.lon, p.category);
        }
      } else if (msg.type === "event_relocated") {
        // v6.6.6 — the backend LLM re-placed an event; move its pin in place.
        const p = msg.payload;
        const ev = state.mapData.events.find((e) => e.id === p.id);
        if (ev) {
          ev.lat = p.lat; ev.lon = p.lon;
          if (p.location_name) ev.location_name = p.location_name;
          pushMapData();
        }
      } else if (msg.type === "story_created" || msg.type === "story_updated") {
        try {
          const full = await api.stories({ limit: 30 });
          const card = (full.stories || []).find((s) => s.id === msg.payload.id);
          feed.upsert(card || msg.payload);
        } catch { feed.upsert(msg.payload); }
        if (msg.type === "story_created") {
          sound.blip();
          const ev = state.mapData.events.find((e) => e.story_id === msg.payload.id);
          if (ev) state.renderer?.burst?.(ev.lat, ev.lon, ev.category);
          // §25 — in-app breaking alert above the severity floor
          const sev = ev ? ev.severity
            : Math.max(0, ...state.mapData.events
                .filter((e) => e.story_id === msg.payload.id)
                .map((e) => e.severity || 0));
          alerts.maybeAlert(msg.payload, sev);
        }
        refreshMap().catch(() => {});
      } else if (msg.type === "instability_updated") {
        refreshInstability().catch(() => {});
      }
    },
  });
  socket.start();
  // v6.2 — SAFETY-NET story polling. The WS only falls back to polling after
  // 60s of being *down*; if it connects fine but a story push is missed (or
  // the correlation engine emits between pushes), the feed would otherwise
  // never refresh after the initial load — the "feed sometimes doesn't come
  // in" bug. A steady full refresh guarantees events keep streaming in.
  setInterval(() => {
    if (!liveSuspended) refreshStories().catch(() => {});
  }, STORY_REFRESH_MS);
  setInterval(() => { if (!liveSuspended) refreshMap().catch(() => {}); }, MAP_REFRESH_MS);
  setInterval(() => { if (!liveSuspended) refreshInstability().catch(() => {}); },
              MAP_REFRESH_MS * 5);
}

// v4 §4.3 — city label data (GeoNames, population-sorted) for both renderers
async function loadCities() {
  const data = await api.cities(50000, 4000);
  state.cities = data.cities || [];
  state.renderer?.setCities?.(state.cities);
}

// v4 §14, v5.1 §18 — first-run onboarding: surface the key setup, don't
// block serving. Gate on ai_available (any configured provider in the
// llm_provider fallback chain — Groq by default, free, no card) rather than
// Claude specifically, since Claude is now an optional upgrade.
async function checkOnboarding() {
  if (localStorage.getItem("tdl_onboarded") === "1") return;
  if (!(state.clientConfig.onboarding || {}).require_ai_key_before_first_run) return;
  const ks = await api.keysStatus().catch(() => null);
  if (!ks) return;
  if (ks.ai_available) {
    localStorage.setItem("tdl_onboarded", "1");
    return;
  }
  const banner = document.createElement("div");
  banner.className = "onboard-banner";
  // v6.5 — Ollama-first: local AI is the primary provider (free forever, no
  // rate limits); a Groq key stays available as the cloud alternative.
  banner.innerHTML = `<span>⚙ <b>First run:</b> install <b>Ollama</b> (ollama.com) and run
      <code>ollama pull llama3.1</code> to switch on the AI features locally — free,
      unlimited, private. (Or add a free Groq key in Settings instead.)</span>
    <button class="ob-open">open settings</button><button class="ob-skip">later</button>`;
  banner.querySelector(".ob-open").addEventListener("click", () => {
    banner.remove();
    openSettings();
  });
  banner.querySelector(".ob-skip").addEventListener("click", () => {
    banner.remove();
    localStorage.setItem("tdl_onboarded", "1");
  });
  document.getElementById("map-panel").appendChild(banner);
}

// v4 §5.1 — surfaced (never silent) completeness check result
async function loadCompleteness() {
  const c = await api.completeness().catch(() => null);
  if (c && (c.problems || []).length) {
    console.warn("entity completeness gaps:", c.problems);
  }
}

// v7.4.4 — the bundled synthetic/demo dataset was DELETED at the owner's
// request ("could you actually delete the synthetic data? I don't need it").
// There is no longer any fake-data fallback: if the backend can't be reached
// the app stays honestly empty and says so, and keeps polling. It will NEVER
// again paint `[SYNTHETIC]` rows that could be mistaken for live coverage.
async function loadSynthetic() {
  state.syntheticMode = false;
  state.syntheticData = null;
  setConn("offline");
  try {
    if (!document.getElementById("synthetic-warning-banner")) {
      const warn = document.createElement("div");
      warn.id = "synthetic-warning-banner";
      warn.style.cssText = "position:absolute;top:8px;left:50%;transform:translateX(-50%);"
        + "z-index:9999;background:#b45309;color:#fff;padding:8px 16px;border-radius:6px;"
        + "font-size:13px;box-shadow:0 2px 10px rgba(0,0,0,.5);max-width:90%;text-align:center;";
      warn.innerHTML = "⚠ Backend not reachable — the live feed is offline. "
        + "Start the server (<code>python run.py</code>) and reload.";
      document.getElementById("map-panel").appendChild(warn);
    }
  } catch { /* non-fatal */ }
  state.mapData = { events: [], links: [] };
  pushMapData();
  feed.setStories([], { force: true });
  els.feedList.innerHTML = `<p class="cp-meta">Backend not reachable — no live feed. `
    + `Start <code>python run.py</code> and reload.</p>`;
  instChart.update({ latest: null, history: [] });
}

// ---------- topbar controls ----------

els.qualitySelect.value = currentQuality();
els.qualitySelect.addEventListener("change", () => {
  localStorage.setItem(QUALITY_KEY, els.qualitySelect.value);
  mountRenderer(state.tier);
});

function paintSoundBtn() {
  els.soundToggle.textContent = sound.isEnabled() ? "🔊" : "🔇";
  els.soundToggle.classList.toggle("active", sound.isEnabled());
}
els.soundToggle.addEventListener("click", () => { sound.toggle(); paintSoundBtn(); });
paintSoundBtn();
// v6.1 — start the music without the user having to touch the volume/toggle
sound.armAutoplay();

// v6.1 — a friendly "what is this / how do I use it" popup, hidden behind the
// header "?" button and shown once automatically on the very first visit.
const HELP_SEEN_KEY = "tdl_help_seen";
// v7.4.1 — the "?" guide rebuilt as a full, tabbed manual to EVERY part of the
// system (owner: "make the startup guide a total detailed guide of every single
// thing … the first page should be a general overview and one tab should have
// all the keyboard shortcuts"). First tab = overview; last tabs = shortcuts + AI
// setup. Self-contained; no network.
const HELP_TABS = [
  ["Overview", `
    <h2>🌍 Welcome to GlobeGrid</h2>
    <p>GlobeGrid is a live <b>global-events intelligence system</b> on a 3-D world map.
       It continuously ingests news (hundreds of RSS wires), USGS earthquakes, market
       data, Reddit and physical sensors; extracts the <b>who / what / where / when</b> of
       every event into a permanent <b>fact chain</b>; correlates related events across
       the world <i>and across decades</i>; and explains <i>what happened and why</i> with
       AI-written causal storylines — every fact linked to its source.</p>
    <p>Use the tabs above to learn every part of the system. The short version:</p>
    <ul>
      <li><b>The globe</b> shows live events as glowing dots — click one to read the story.</li>
      <li><b>The live feed</b> (right) streams correlated stories as they form.</li>
      <li><b>Click any country</b> for a full profile; the <b>Conflicts</b> button opens War Mode.</li>
      <li>The <b>Modes</b> bar (bottom) paints thematic maps — HDI, GDP, alignments, recognition, and more.</li>
      <li>The glowing <b>orb</b> (bottom-right) is the AI analyst — ask it anything about world events.</li>
      <li>Turn on the AI in one step — see the <b>AI setup</b> tab.</li>
    </ul>
    <p class="help-foot">Tip: press <kbd>?</kbd> or click the header <b>?</b> any time to reopen this guide.</p>`],
  ["Map & globe", `
    <h3>The world map</h3>
    <ul>
      <li><b>Rotate</b> by dragging; <b>zoom</b> with the scroll wheel or <kbd>Q</kbd>/<kbd>E</kbd>;
          pan/tilt with <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd>.</li>
      <li>Three tiers auto-select for your device: a <b>WebGL2 globe</b> (best), a
          <b>2-D canvas map</b> (<kbd>M</kbd>), and a plain <b>list</b> on low-power hardware.
          Press <kbd>G</kbd> for the globe, <kbd>M</kbd> for the 2-D map.</li>
      <li><b>Event dots</b> are colored by category and sized by severity. Dense areas
          cluster into a counted circle — zoom in to split them, or click to browse them all.</li>
      <li><b>⟳ spin</b> toggles a slow auto-rotation; <b>names</b> toggles country labels.</li>
      <li><b>Shift-drag</b> box-selects a region and lists every event inside it.</li>
      <li><b>Pan to Event</b> buttons (on story pages and event panels) fly the camera to the spot.</li>
      <li>The <b>📡 sensor</b> toggle overlays physical ground truth (fires, flights, quakes, ships, blackouts).</li>
    </ul>`],
  ["Feed & stories", `
    <h3>Live feed &amp; story pages</h3>
    <ul>
      <li>The <b>live feed</b> streams correlated <b>stories</b> (clusters of related events),
          newest first, each showing its source and event counts. Close it with <kbd>F</kbd> or the ✕.</li>
      <li>Filter by <b>category</b> chips; <b>sort</b> newest / oldest / most-active.</li>
      <li>Click a card to open the <b>story page</b>: a one-line takeaway, bulleted deep
          summary (AI), the full event timeline, every source link, a <b>bias view</b>, and
          <b>connected history</b> reaching back decades.</li>
      <li><b>full summary</b> expands the analysis; <b>⌖ pan to event</b> flies the map there.</li>
      <li>A <b>📡 corroboration</b> badge means physical sensors agree with the reporting.</li>
      <li>The <b>history / archive</b> view browses the entire permanent fact chain by date &amp; category.</li>
      <li>Historical landmark events (1945→present) are seeded into the chain and marked <i>(historical)</i>.</li>
    </ul>`],
  ["Countries & world", `
    <h3>Countries, leaders &amp; institutions</h3>
    <ul>
      <li><b>Click a country</b> for its profile: flag, paramount leader (with portrait),
          legislature seat-arc, currency, population/GDP/HDI (clickable for breakdowns),
          languages + <b>other languages</b>, alliances, conflicts, and a deep-background dossier.</li>
      <li><b>Leader / party</b> names open rich profile pages (ideology, career, policies).</li>
      <li>The <b>🇺🇳 UN</b> button opens the United Nations panel — Security Council,
          resolutions with recorded votes, every principal organ as a tab, and a <b>live UN news feed</b>.</li>
      <li><b>Bloc / alliance</b> chips (NATO, EU, BRICS, ASEAN…) open full panels like the UN page.</li>
      <li><b>Disputed territories</b> and <b>Antarctica</b> claims render on the map and open breakdowns.</li>
      <li><b>Compare</b> two countries side by side; <b>bookmark</b> ★ anything for later.</li>
    </ul>`],
  ["Conflicts & War Mode", `
    <h3>Conflicts &amp; War Mode</h3>
    <ul>
      <li>The <b>Conflicts</b> button opens a directory of active wars and insurgencies.</li>
      <li>Pick one to enter <b>War Mode</b>: side-colored countries, belligerents vs backers,
          an approximate front line, and a feed filtered to that conflict
          (military / civilian / diplomatic / economic tabs).</li>
      <li>In a conflict panel, the <b>🎙 Situation Room</b> puts four AI analysts
          (realist, economist, humanitarian, military) into a threaded argument over the war.</li>
      <li>The <b>🎧 audio briefing</b> button narrates a detailed spoken rundown of the conflict.</li>
      <li><b>Order of battle</b> gives an AI-structured breakdown of forces, offensives and tactics.</li>
      <li>Opening any entity auto-exits War Mode and restores your feed.</li>
    </ul>`],
  ["AI tools", `
    <h3>The AI toolset</h3>
    <ul>
      <li><b>Analyst orb</b> (bottom-right): a conversational geopolitics assistant. It reads
          the same fact chain, is aware of the panel you have open, cites clickable stories,
          and can navigate the map for you. Clear the chat with 🗑.</li>
      <li><b>🔮 Counterfactual</b> (header): perturb the world ("What if the Strait of Hormuz
          closes?") for an AI branching consequence tree — each branch scored, probability-weighted,
          and expandable with <b>↳ deepen</b>.</li>
      <li><b>🎯 Forecasting scorecard</b>: a public "how right were we?" Brier backtest —
          a category only shows live forecasts once it earns calibration.</li>
      <li><b>🎧 Morning briefing</b>: a ~3-minute personalized spoken digest while the globe
          auto-flies between story locations.</li>
      <li>Daily / weekly / monthly <b>briefings</b> and a <b>market briefing</b> summarize the world.</li>
    </ul>
    <p class="help-foot">All AI features degrade gracefully when no AI provider is running —
       the maps, data and feed always work. Turn AI on in the <b>AI setup</b> tab.</p>`],
  ["Map modes", `
    <h3>Thematic map modes (bottom bar)</h3>
    <p>The <b>Modes</b> bar recolors the whole map from authoritative data — never AI-guessed:</p>
    <ul>
      <li><b>Data choropleths</b>: population, area, density, GDP, GDP per capita, HDI.</li>
      <li><b>Categorical</b>: dominant religion, language family (with hover tooltips).</li>
      <li><b>Nuclear arsenals</b>: the nine nuclear states by estimated warhead count.</li>
      <li><b>Alignments</b>: from a chosen country's view — allies green, partners light-green, rivals red.
          Every country has this button now.</li>
      <li><b>Recognition</b>: for a partially-recognized state (Kosovo, Taiwan, Palestine, Israel,
          Western Sahara…), who recognizes it and who doesn't.</li>
      <li><b>Disputed</b>: every contested zone as a clickable marker with its own breakdown.</li>
      <li><b>Blocs</b>: overlay one or several alliances at once, each its own color.</li>
    </ul>`],
  ["Audio", `
    <h3>Sound &amp; music</h3>
    <ul>
      <li>GlobeGrid has a generative music engine with <b>19 diverse presets</b> — from
          <i>ambient</i>, <i>arctic calm</i>, <i>oceanic deep</i> and <i>zen garden</i> to
          <i>neon night</i>, <i>pulse grid</i>, <i>iron march</i> and <i>thunderhead</i>.</li>
      <li>Pick a track in <b>Settings</b>; the <b>volume slider</b> is in the header.</li>
      <li><b>Data sonification</b> turns live event arrivals into sound — the feed becomes audible.</li>
      <li>New stories ping softly; mass-update alerts use a gentle chime.</li>
    </ul>`],
  ["⌨ Shortcuts", `
    <h3>Keyboard shortcuts</h3>
    <table class="help-keys">
      <tr><td><kbd>drag</kbd></td><td>rotate the globe</td></tr>
      <tr><td><kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd></td><td>pan / tilt the camera</td></tr>
      <tr><td><kbd>Q</kbd> / <kbd>E</kbd></td><td>zoom out / in</td></tr>
      <tr><td>scroll</td><td>zoom</td></tr>
      <tr><td><kbd>shift</kbd> + drag</td><td>box-select a region → grouped events</td></tr>
      <tr><td><kbd>F</kbd></td><td>toggle the live feed</td></tr>
      <tr><td><kbd>G</kbd></td><td>globe (3-D) view</td></tr>
      <tr><td><kbd>M</kbd></td><td>2-D map view</td></tr>
      <tr><td><kbd>L</kbd></td><td>next interface language</td></tr>
      <tr><td><kbd>C</kbd></td><td>open last / random country</td></tr>
      <tr><td><kbd>t</kbd> or <kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>T</kbd></td><td>cycle color themes</td></tr>
      <tr><td><kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>K</kbd></td><td>command palette (jump anywhere)</td></tr>
      <tr><td><kbd>?</kbd></td><td>open this guide</td></tr>
      <tr><td><kbd>Esc</kbd></td><td>close one layer at a time (palette → modes → drawers → panels → War Mode)</td></tr>
    </table>
    <p class="help-foot">Single-key shortcuts only fire when you're not typing in a field.</p>`],
  ["AI setup", `
    <h3>Switch on the AI (one-time)</h3>
    <p>GlobeGrid's AI (analyst, causal storylines, summaries, briefings) runs on
       <b>Ollama</b> — a free local AI server on your own machine. No account, no key,
       no rate limits, fully private:</p>
    <ol class="help-setup">
      <li>Install Ollama from <b>ollama.com</b> (Windows/Mac/Linux — one installer).</li>
      <li>In a terminal run <code>ollama pull llama3.1</code> (~4.9&nbsp;GB, one time).</li>
      <li>Done — Ollama runs in the background and GlobeGrid finds it automatically.
          Verify at <a href="/api/diagnostics" target="_blank">/api/diagnostics</a> (all rows ✅).</li>
    </ol>
    <p class="help-foot">Slow on an older PC? Use the smaller model
       <code>ollama pull llama3.2:3b</code> and set <code>llm_provider.ollama_model</code>
       in <code>backend/config.yaml</code>. Prefer the cloud? Add a free <b>Groq</b> key in
       Settings — it's the automatic fallback whenever Ollama isn't running.</p>`],
];

function showHelp() {
  let ov = document.getElementById("help-overlay");
  if (!ov) {
    ov = document.createElement("div");
    ov.id = "help-overlay";
    const tabsBar = HELP_TABS.map((t, i) =>
      `<button class="help-tab${i === 0 ? " active" : ""}" data-i="${i}">${t[0]}</button>`).join("");
    ov.innerHTML = `
      <div class="help-card">
        <button class="help-close" title="close">✕</button>
        <div class="help-tabs">${tabsBar}</div>
        <div class="help-body">${HELP_TABS[0][1]}</div>
      </div>`;
    document.body.appendChild(ov);
    const body = ov.querySelector(".help-body");
    ov.querySelectorAll(".help-tab").forEach((b) =>
      b.addEventListener("click", () => {
        ov.querySelectorAll(".help-tab").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        body.innerHTML = HELP_TABS[+b.dataset.i][1];
        body.scrollTop = 0;
      }));
    const close = () => ov.classList.add("hidden");
    ov.querySelector(".help-close").addEventListener("click", close);
    ov.addEventListener("click", (e) => { if (e.target === ov) close(); });
  }
  ov.classList.remove("hidden");
}
els.helpBtn.addEventListener("click", showHelp);
if (!localStorage.getItem(HELP_SEEN_KEY)) {
  localStorage.setItem(HELP_SEEN_KEY, "1");
  setTimeout(showHelp, 900);   // let the globe paint first
}
// §12.1 — the volume slider the gain bug made necessary
els.volumeSlider.value = String(Math.round(sound.volume * 100));
els.volumeSlider.addEventListener("input", () => {
  sound.setVolume(parseInt(els.volumeSlider.value, 10) / 100);
});
// §12.2/§12.3 — preset picker
// v6 §17 — explicit scope narrowing: only presets in audio.presets_active
// appear in the picker; everything else stays unbuilt/hidden until the
// hard-rock/metal proof of concept is validated
const activePresets = () =>
  (state.clientConfig.audio || {}).presets_active
  // v6.6.7 — the fallback (used before /api/config resolves) MUST include the
  // v6.6.5 tracks; otherwise the picker is built from this stale list and the
  // new tracks never appear ("audio tracks still don't show").
  || ["ambient_default", "nocturne_calm", "arctic_calm", "modal_drift",
      "storm_front", "data_sonification", "crystalline_chimes", "deep_glacier",
      "aurora_drift", "oceanic_deep", "desert_mirage", "neon_night", "monastery",
      "signal_static", "pulse_grid", "stargaze", "iron_march", "zen_garden",
      "thunderhead"];
for (const [name, p] of Object.entries(PRESETS)) {
  if (!activePresets().includes(name)) continue;
  const o = document.createElement("option");
  o.value = name; o.textContent = "♪ " + p.label;
  els.presetSelect.appendChild(o);
}
els.presetSelect.value = sound.presetName;
els.presetSelect.addEventListener("change", () => sound.setPreset(els.presetSelect.value));

els.heatmapToggle.addEventListener("click", () => {
  const on = !els.heatmapToggle.classList.contains("active");
  els.heatmapToggle.classList.toggle("active", on);
  state.renderer?.setHeatmap?.(on);
});
// v4 §5.4 — three orthogonal switches: borders / disputes / NSAs
els.bordersToggle.addEventListener("click", () => {
  state.bordersOn = !state.bordersOn;
  els.bordersToggle.classList.toggle("active", state.bordersOn);
  state.renderer?.setBorders?.(state.bordersOn);
});
els.disputesToggle.addEventListener("click", () => {
  state.disputesOn = !state.disputesOn;
  els.disputesToggle.classList.toggle("active", state.disputesOn);
  state.renderer?.setDisputes?.(state.disputesOn);
  // v6.6.4 — push the disputed zones onto the map as clickable amber markers,
  // AND open the directory. Clicking a marker OR a directory row opens the
  // per-zone context breakdown.
  if (state.disputesOn) {
    api.disputedZones().then((d) => {
      state.disputedZones = d.zones || [];
      state.renderer?.setDisputedZones?.(state.disputedZones);
    }).catch(() => {});
    ctx.openDisputedZones();
  } else {
    state.renderer?.setDisputedZones?.([]);
  }
});
// v6.2 — timezone picker in the header (was buried in Settings and hard to find)
for (const g of TIMEZONES) {
  const og = document.createElement("optgroup");
  og.label = g.group;
  for (const [val, label] of g.zones) {
    const o = document.createElement("option");
    o.value = val; o.textContent = label;
    og.appendChild(o);
  }
  els.tzHeader.appendChild(og);
}
els.tzHeader.value = getTimeZone();
els.tzHeader.addEventListener("change", () => {
  setTimeZone(els.tzHeader.value);
  refreshStories().catch(() => {});
});

// v6.2 — country-name label toggle (terrain removed entirely)
state.namesOn = localStorage.getItem("tdl_names") !== "0";
els.namesToggle.classList.toggle("active", state.namesOn);
els.namesToggle.addEventListener("click", () => {
  state.namesOn = !state.namesOn;
  localStorage.setItem("tdl_names", state.namesOn ? "1" : "0");
  els.namesToggle.classList.toggle("active", state.namesOn);
  state.renderer?.setCountryLabelsVisible?.(state.namesOn);
});
// v6.6.6 — explicit auto-spin toggle (the globe no longer spins on its own when
// idle; this is the deliberate way to make it rotate). Persisted.
state.spinOn = localStorage.getItem("tdl_spin") === "1";
if (els.spinToggle) {
  els.spinToggle.classList.toggle("active", state.spinOn);
  state.renderer?.setAutoSpin?.(state.spinOn);
  els.spinToggle.addEventListener("click", () => {
    state.spinOn = !state.spinOn;
    localStorage.setItem("tdl_spin", state.spinOn ? "1" : "0");
    els.spinToggle.classList.toggle("active", state.spinOn);
    state.renderer?.setAutoSpin?.(state.spinOn);
  });
}
els.actorsToggle.addEventListener("click", async () => {
  state.actorsOn = !state.actorsOn;
  els.actorsToggle.classList.toggle("active", state.actorsOn);
  if (state.actorsOn && !state.actors.length) {
    const data = await api.actors().catch(() => ({ actors: [] }));
    state.actors = data.actors || [];
  }
  if (state.actorsOn && !state.actorZones.length) {   // v5 §11 — same toggle
    const z = await api.nsaZones().catch(() => ({ zones: [] }));
    state.actorZones = z.zones || [];
  }
  state.renderer?.setActors?.(state.actorsOn ? state.actors : []);
  state.renderer?.setActorZones?.(state.actorsOn ? state.actorZones : []);
});

const palette = new CommandPalette({
  onOpenStory: (id) => openStory(id),
  onFlyTo: (lat, lon) => state.renderer?.flyTo?.(lat, lon),
  getCamera: () => state.renderer?.getCamera?.(),
  setCamera: (cam) => state.renderer?.setCamera?.(cam),
  getRegions: () => {
    const seen = new Map();
    for (const e of state.mapData.events) {
      if (e.location_name && !seen.has(e.location_name))
        seen.set(e.location_name, { name: e.location_name, lat: e.lat, lon: e.lon });
    }
    return [...seen.values()];
  },
});
els.paletteBtn.addEventListener("click", () => palette.toggle());
els.graphBtn.addEventListener("click", () => graphExplorer.open());

// v4 pane-hosted directories & pages
els.storiesBtn.addEventListener("click", () => ctx.openDirectory(null));
els.bookmarksBtn.addEventListener("click", () => pane.push({
  key: "bookmarks", title: "bookmarks",
  render: (el) => Wiki.renderBookmarks(el, ctx),
}));
function openSettings() {
  pane.push({ key: "settings", title: "settings",
              render: (el) => Wiki.renderSettings(el, ctx) });
}
els.settingsBtn.addEventListener("click", openSettings);
els.snapshotBtn.addEventListener("click", async () => {
  try {
    const cards = [...els.feedList.querySelectorAll(".story-card h3")]
      .slice(0, 3).map((h) => ({ headline: h.textContent }));
    await exportSnapshot({ mapHost: els.mapHost, stories: cards,
                           instability: state.lastInstability });
  } catch (err) { els.snapshotBtn.title = `snapshot failed: ${err.message}`; }
});

// §22 — credits reachable from the status drawer footer
statusPanel.onCredits = () => pane.push({
  key: "credits", title: "sources & credits",
  render: (el) => Wiki.renderCredits(el, ctx),
});
document.addEventListener("click", (ev) => {
  if (ev.target && ev.target.classList &&
      ev.target.classList.contains("credits-link")) {
    statusPanel.onCredits();
  }
});

// v6.1 — daily / weekly / monthly briefings, switchable in the overlay.
// v6.6.2 — a right-aligned Market briefing tab (global markets + tentative
// story-driven forecasts).
const BRIEFING_LABELS = { day: "Daily", week: "Weekly", month: "Monthly", market: "📈 Market" };
async function showBriefing(period = "day") {
  els.briefingOverlay.classList.remove("hidden");
  els.briefingOverlay.innerHTML =
    `<div class="story-page"><p>loading ${BRIEFING_LABELS[period].toLowerCase()} briefing…</p></div>`;
  const data = await api.briefings(true, period).catch((e) => ({ error: e.message }));
  const b = data.briefing;
  const page = document.createElement("div");
  page.className = "story-page";
  page.innerHTML = `
    <div class="close-row">
      <div class="briefing-tabs">
        ${["day", "week", "month"].map((p) =>
          `<button class="brief-tab ${p === period ? "active" : ""}" data-p="${p}">${BRIEFING_LABELS[p]}</button>`).join("")}
        <button class="brief-tab brief-tab-market ${period === "market" ? "active" : ""}" data-p="market">${BRIEFING_LABELS.market}</button>
      </div>
      <button class="close-btn">✕ close</button></div>
    <h3>${BRIEFING_LABELS[period]} briefing${b ? " — " + b.briefing_date : ""}</h3>
    <div class="briefing-body"></div>`;
  page.querySelector(".briefing-body").textContent =
    b ? b.content : (data.error || `No ${BRIEFING_LABELS[period].toLowerCase()} briefing yet`
      + " — it generates once enough stories exist over that window.");
  page.querySelectorAll(".brief-tab").forEach((t) =>
    t.addEventListener("click", () => showBriefing(t.dataset.p)));
  page.querySelector(".close-btn").addEventListener("click", () => {
    els.briefingOverlay.classList.add("hidden");
    els.briefingOverlay.innerHTML = "";
  });
  els.briefingOverlay.innerHTML = "";
  els.briefingOverlay.appendChild(page);
}
els.briefingBtn.addEventListener("click", () => showBriefing("day"));
els.briefingOverlay.addEventListener("click", (ev) => {
  if (ev.target === els.briefingOverlay) {
    els.briefingOverlay.classList.add("hidden");
    els.briefingOverlay.innerHTML = "";
  }
});

// ---------- watchlist (§6.2) ----------

const watchlist = {
  async refresh() {
    const data = await api.watchlist().catch(() => ({ items: [] }));
    const panel = els.watchlistPanel;
    panel.innerHTML = `
      <h3>Watchlist</h3>
      <label class="wl-only"><input type="checkbox" ${state.watchlistOnly ? "checked" : ""}>
        feed: watchlist only</label>
      <div class="wl-items"></div>
      <div class="wl-add">
        <select><option>entity</option><option>region</option><option>category</option></select>
        <input placeholder="value… (e.g. Ukraine)">
        <button>add</button>
      </div>`;
    panel.querySelector(".wl-only input").addEventListener("change", (ev) => {
      state.watchlistOnly = ev.target.checked;
      refreshStories().catch(() => {});
    });
    const itemsEl = panel.querySelector(".wl-items");
    for (const it of data.items) {
      const row = document.createElement("div");
      row.className = "src-row";
      row.innerHTML = `<span class="chip">${it.kind}</span> <b></b>
        <button class="cp-del" style="margin-left:auto">✕</button>`;
      row.querySelector("b").textContent = it.value;
      row.querySelector("button").addEventListener("click", async () => {
        await api.watchlistDelete(it.id);
        watchlist.refresh();
        refreshStories().catch(() => {});
      });
      itemsEl.appendChild(row);
    }
    if (!data.items.length) itemsEl.innerHTML = '<p class="cp-meta">nothing pinned yet</p>';
    const addBtn = panel.querySelector(".wl-add button");
    addBtn.addEventListener("click", async () => {
      const kind = panel.querySelector(".wl-add select").value;
      const value = panel.querySelector(".wl-add input").value.trim();
      if (!value) return;
      await api.watchlistAdd(kind, value);
      watchlist.refresh();
      refreshStories().catch(() => {});
    });
  },
};
els.watchlistBtn.addEventListener("click", () => {
  els.watchlistPanel.classList.toggle("hidden");
  if (!els.watchlistPanel.classList.contains("hidden")) watchlist.refresh();
});

// v5 §1 — feed sort controls
const sortSel = document.createElement("select");
sortSel.className = "filter-chip";
sortSel.title = "sort the feed";
sortSel.innerHTML = `<option value="">newest first</option>`
  + `<option value="oldest">oldest first</option>`
  + `<option value="active">most active</option>`;
sortSel.addEventListener("change", () => {
  state.feedSort = sortSel.value;
  refreshStories().catch(() => {});
});
els.feedTools.appendChild(sortSel);

// v5 §3 / v6.6.2 — the conflict/military development filter is War-Mode-only
// now (owner: "remove all developments vs military vs conflict from the base
// live feed … that's only for war mode"). War Mode's own sub-filter tabs
// (Military/Civilian/Diplomatic/Economic) drive that split via state.warTab,
// so the base feed no longer shows this dropdown. state.devType stays unset.

// v5 §1 — History / archive view (paginated, date+category filterable)
const histBtn = document.createElement("button");
histBtn.className = "filter-chip";
histBtn.textContent = "🕑 history";
histBtn.title = "browse the full fact-chain archive by date";
histBtn.addEventListener("click", () => openHistory());
els.feedTools.appendChild(histBtn);

const storiesCsv = document.createElement("a");
storiesCsv.className = "filter-chip";
storiesCsv.textContent = "⤓ csv";
storiesCsv.href = "/api/stories?format=csv";
storiesCsv.title = "export stories as CSV";
els.feedTools.appendChild(storiesCsv);

// ========== v3 wiring (with the §16 focus fix) ==========

function selectConflict(conflictId, { forceOn = false } = {}) {
  state.conflictId = (!forceOn && state.conflictId === conflictId) ? null : conflictId;
  const active = state.conflicts.find((c) => c.id === state.conflictId);
  // v4 §16.2 — when nothing is selected the focus CLEARS (the old code
  // kept the previous stale value here, which was the confirmed bug)
  setFocus(active ? "conflict" : null, active ? active.name : undefined);
  renderConflictTabs();
  refreshStories().catch(() => {});
}

function renderConflictTabs() {
  // v6 §9 — the redundant all-conflicts listing above the feed is REMOVED;
  // browsing conflicts now lives in the top-level Conflicts tab (War Mode
  // entry). What remains here is only the war-mode sub-filter row, or a
  // small "filtered ✕" chip when a conflict filter is active outside it.
  els.conflictTabs.innerHTML = "";
  if (state.warMode) { renderWarTabs(); return; }
  if (!state.conflictId) return;
  const active = state.conflicts.find((c) => c.id === state.conflictId);
  const chip = document.createElement("button");
  chip.className = "conflict-tab active";
  chip.innerHTML = `${(active ? active.name : "conflict").replace(/</g, "&lt;")} ✕`;
  chip.title = "clear the conflict filter";
  chip.addEventListener("click", () => {
    state.conflictId = null;
    setFocus(null);
    renderConflictTabs();
    refreshStories().catch(() => {});
  });
  els.conflictTabs.appendChild(chip);
}

async function loadConflicts() {
  try {
    const data = await api.conflicts();
    state.conflicts = data.conflicts || [];
    renderConflictTabs();
  } catch { /* entity layer not ready */ }
}

// v7.1 §5 — the marked-locations and sensor overlays share ONE pin buffer, so
// they can be shown together; each toggle just unions its array in.
function applyMapMarkers() {
  const pins = [];
  if (state.markedOn) pins.push(...(state.markedLocations || []));
  if (state.sensorsOn) pins.push(...(state.sensors || []));
  state.renderer?.setMarkedLocations?.(pins);
}
els.markedToggle.addEventListener("click", async () => {
  state.markedOn = !state.markedOn;
  els.markedToggle.classList.toggle("active", state.markedOn);
  if (state.markedOn && !state.markedLocations.length) {
    const data = await api.markedLocations().catch(() => ({ locations: [] }));
    state.markedLocations = data.locations || [];
  }
  applyMapMarkers();
});

// v7.1 §5 — physical-sensor ground-truth overlay (thermal/air/seismic/ACLED)
els.sensorsToggle.addEventListener("click", async () => {
  state.sensorsOn = !state.sensorsOn;
  els.sensorsToggle.classList.toggle("active", state.sensorsOn);
  if (state.sensorsOn && !(state.sensors || []).length) {
    const data = await api.sensors().catch(() => ({ sensors: [] }));
    state.sensors = data.sensors || [];
    if (!state.sensors.length) {
      els.sensorsToggle.title = "no sensor events yet — FIRMS/OpenSky/ACLED "
        + "need API keys; USGS seismic is keyless (network permitting)";
    }
  }
  applyMapMarkers();
});

els.satToggle.addEventListener("click", async () => {
  state.satOn = !state.satOn;
  els.satToggle.classList.toggle("active", state.satOn);
  if (state.satOn) {
    const data = await api.satellites().catch(() => ({ satellites: [] }));
    state.satellites = data.satellites || [];
    if (!state.satellites.length) {
      els.satToggle.title = "no TLE data yet — the daily CelesTrak fetch hasn't succeeded";
    }
    const tick = () => {
      if (!state.satOn) return;
      state.renderer?.setSatellites?.(propagateAll(state.satellites));
      state.satTimer = setTimeout(tick, 1000);
    };
    tick();
  } else {
    clearTimeout(state.satTimer);
    state.renderer?.setSatellites?.([]);
  }
});

// v6.1.1 — multiple blocs can be shown at once, each in a distinct color.
let alliancesCache = [];
const activeBlocs = new Set();
// a palette cycled per active bloc so overlapping alliances stay tellable
// apart, with a per-type fallback tint
const BLOC_PALETTE = [
  [1.0, 0.45, 0.35], [0.5, 0.85, 1.0], [0.55, 1.0, 0.65], [1.0, 0.85, 0.4],
  [0.8, 0.6, 1.0], [1.0, 0.6, 0.85], [0.5, 1.0, 0.9], [1.0, 0.72, 0.4],
];
function applyBlocOverlay() {
  const groups = [];
  let idx = 0;
  for (const aid of activeBlocs) {
    const alliance = alliancesCache.find((a) => a.id === aid);
    if (!alliance) continue;
    const members = new Set(alliance.members || []);
    const rings = [];
    for (const c of BOUNDARIES_50M) if (members.has(c.i)) rings.push(...c.r);
    if (rings.length) groups.push({ rings, color: BLOC_PALETTE[idx % BLOC_PALETTE.length] });
    idx++;
  }
  // prefer the multi-group API; fall back to single overlay if unavailable
  if (state.renderer?.setColoredRings) state.renderer.setColoredRings(groups);
  else state.renderer?.setAllianceOverlay?.(groups[0]?.rings || [], groups[0]?.color);
  els.blocsBtn.textContent = activeBlocs.size ? `blocs (${activeBlocs.size}) ▾` : "blocs ▾";
}
function blocColorHex(idx) {
  const c = BLOC_PALETTE[idx % BLOC_PALETTE.length];
  return `rgb(${c.map((x) => Math.round(x * 255)).join(",")})`;
}
async function loadAlliances() {
  try {
    const data = await api.alliances();
    alliancesCache = data.alliances || [];
    // v6.6.2 — each row has BOTH a checkbox (map overlay) and a clickable name
    // that OPENS the full bloc panel. Previously the name was inert, so "NATO
    // won't open" — there was no click-through to renderAlliance at all.
    els.blocPanel.innerHTML = alliancesCache.map((a) =>
      `<div class="bloc-row"><input type="checkbox" value="${a.id}" title="show on map">
        <button class="bloc-open" data-id="${a.id}">${a.name}</button>
        <span class="cp-meta">${a.type || ""}</span></div>`).join("")
      + `<button class="bloc-clear">clear all</button>`;
    els.blocPanel.querySelectorAll(".bloc-open").forEach((b) =>
      b.addEventListener("click", (ev) => {
        ev.stopPropagation();
        els.blocPanel.classList.add("hidden");
        openEntity("alliance", b.dataset.id);
      }));
    els.blocPanel.querySelectorAll("input[type=checkbox]").forEach((cb) =>
      cb.addEventListener("change", () => {
        cb.checked ? activeBlocs.add(cb.value) : activeBlocs.delete(cb.value);
        // recolor the checkbox row to match its overlay color
        [...activeBlocs].forEach((id, i) => {
          const box = els.blocPanel.querySelector(`input[value="${id}"]`);
          if (box) box.parentElement.style.borderLeft = `3px solid ${blocColorHex(i)}`;
        });
        els.blocPanel.querySelectorAll("input:not(:checked)").forEach((b) =>
          (b.parentElement.style.borderLeft = "3px solid transparent"));
        applyBlocOverlay();
      }));
    els.blocPanel.querySelector(".bloc-clear").addEventListener("click", () => {
      activeBlocs.clear();
      els.blocPanel.querySelectorAll("input[type=checkbox]").forEach((b) => {
        b.checked = false; b.parentElement.style.borderLeft = "3px solid transparent";
      });
      applyBlocOverlay();
    });
  } catch { /* entity layer not ready */ }
}
els.blocsBtn.addEventListener("click", (ev) => {
  ev.stopPropagation();
  els.blocPanel.classList.toggle("hidden");
});
document.addEventListener("click", (ev) => {
  if (!els.blocPanel.contains(ev.target) && ev.target !== els.blocsBtn)
    els.blocPanel.classList.add("hidden");
});

async function loadRegions() {
  try {
    const data = await api.countries();
    regionByIso = new Map((data.countries || []).map((c) => [c.id, c.region || ""]));
  } catch { /* entity layer not ready */ }
}

window.__xrSupported = false;
if (navigator.xr && navigator.xr.isSessionSupported) {
  navigator.xr.isSessionSupported("immersive-vr").then((ok) => {
    window.__xrSupported = !!ok;
    els.xrBtn.classList.toggle("hidden", !(ok && state.tier === 1));
  }).catch(() => {});
}
els.xrBtn.addEventListener("click", async () => {
  try { await state.renderer?.enterXR?.(); }
  catch (err) { els.xrBtn.title = `VR unavailable: ${err.message}`; }
});

// v3 §10.1 timelapse export (MediaRecorder/webm — deviation noted in CLAUDE.md)
const tlBtn = document.createElement("button");
tlBtn.className = "ts-play";
tlBtn.textContent = "⏺";
tlBtn.title = "export the last 24h as a video timelapse";
els.scrubberHost.querySelector("#time-scrubber").appendChild(tlBtn);
tlBtn.addEventListener("click", async () => {
  const canvas = els.mapHost.querySelector("canvas");
  if (!canvas || !window.MediaRecorder) { tlBtn.title = "capture unsupported here"; return; }
  tlBtn.textContent = "⏺…";
  tlBtn.disabled = true;
  const stream = canvas.captureStream(30);
  const rec = new MediaRecorder(stream, { mimeType: "video/webm" });
  const chunks = [];
  rec.ondataavailable = (ev) => ev.data.size && chunks.push(ev.data);
  const done = new Promise((res) => { rec.onstop = res; });
  rec.start();
  const STEPS = 48;
  for (let i = 0; i <= STEPS; i++) {
    const frac = i / STEPS;
    const value = Math.round(1000 * (1 - (1 - frac) * (24 / (7 * 24))));
    scrubber.range.value = String(value);
    scrubber.range.dispatchEvent(new Event("input"));
    await new Promise((r) => setTimeout(r, 220));
  }
  rec.stop();
  await done;
  scrubber.reset();
  const blob = new Blob(chunks, { type: "video/webm" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `globegrid-last24h-${new Date().toISOString().slice(0, 10)}.webm`;
  a.click();
  URL.revokeObjectURL(a.href);
  tlBtn.textContent = "⏺";
  tlBtn.disabled = false;
});

// --- §24 analyst orb + autonomous navigation (focus is timestamped; the
// backend now always tries the question text first — v4 §16.2) ---
const analyst = new AnalystPanel({
  onOpenStory: (id) => openStory(id),
  onOpenSound: () => sound.analystOpen(),     // v6.6.4 open/close cues
  onCloseSound: () => sound.analystClose(),
  getFocusedEntity: () => state.focusedEntity,
  // v6 §29 — screen-aware: whatever panel/page is open right now
  getScreen: () => {
    // v7 Part 6 — the analyst must comment on the panel the user is LOOKING AT
    // right now (the top of the pane stack), not a previously-focused entity.
    const t = pane.top();
    let topPanel = null;
    if (t) {
      const [kind, ...rest] = String(t.key).split(":");
      topPanel = { kind, id: rest.join(":") || null,
                   title: t.title || null, current: true };
    }
    return {
      pane: t ? String(t.key) : null,
      top_panel: topPanel,
      war_mode: state.warMode ? state.warMode.conflict.name : null,
      map_mode: state.mapMode, tier: state.tier,
      conflict_filter: state.conflictId,
    };
  },
  onOpenThread: (id) => ctx.openThread(id),
  autoNavDefault: true,
  onNavigate: (nav) => {
    if (!nav) return;
    if (nav.type === "country") openEntity("country", nav.id);
    else if (nav.type === "leader" && nav.name) ctx.openLeader(nav.name);   // v6.6.7
    // v6 §13 — an analyst answer that opens a conflict enters War Mode
    // directly and frames the conflict zone, not just a generic tab
    else if (nav.type === "conflict") enterWarMode(nav.id);
    else if (nav.type === "region") ctx.openRegion(nav.id);   // v5 §20
    else if (nav.type === "non_state_actor") openEntity("non_state_actor", nav.id);
    else if (nav.type === "location") {
      const loc = state.markedLocations.find((l) => l.id === nav.id);
      if (loc) state.renderer?.flyTo?.(loc.lat, loc.lon);
    } else if (nav.type === "alliance") {
      // v7.4 — asking the analyst about NATO now OPENS NATO's panel (owner:
      // "if i ask about NATO, the Analyst doesnt open NATO"), and also lights
      // its members on the map.
      openEntity("alliance", nav.id);
      activeBlocs.add(nav.id);
      const cb = els.blocPanel.querySelector(`input[value="${nav.id}"]`);
      if (cb) cb.checked = true;
      applyBlocOverlay();
    } else if (nav.type === "non_state_actor" || nav.type === "party"
               || nav.type === "person" || nav.type === "organization") {
      openEntity(nav.type, nav.id);   // v7.4 — generic entity open
    }
  },
});

setInterval(() => {
  const cam = state.renderer?.getCamera?.();
  if (cam) sound.setCameraYaw(cam.yaw);
  const byRegion = new Map();
  for (const e of state.mapData.events || []) {
    if (!e.location_name) continue;
    const r = byRegion.get(e.location_name) || { name: e.location_name,
                                                 lon: e.lon, weight: 0 };
    r.weight += 1;
    byRegion.set(e.location_name, r);
  }
  sound.setRegions([...byRegion.values()].sort((a, b) => b.weight - a.weight));
}, 3000);

loadConflicts();
loadAlliances();
loadRegions();

// ---------- boot ----------

// v5 §14/§2 — restore saved theme + language on boot
applyTheme(localStorage.getItem("tdl_theme")
  || (localStorage.getItem("tdl_colorblind") === "1" ? "colorblind_safe" : "dark_teal_default"));
applyFont(localStorage.getItem("tdl_font") || "sans");   // v6.6.4
applyLanguage(localStorage.getItem("tdl_lang") || "en");

// debug/verification handle (harmless in production; used by headless checks)
window.__gg = { state, ctx, pane, openStory, sound, analyst };

const initialTier = initTierControl(els.tierSelect, (tier) => mountRenderer(tier));
mountRenderer(initialTier);
paintSoundBtn();
els.instabilityWidget.addEventListener("click", () => refreshInstability().catch(() => {}));

loadReal().catch((err) => {
  console.warn("API unavailable — showing offline screen (no demo data):", err.message);
  loadSynthetic().catch((e2) => {
    els.feedList.innerHTML = `<p>no data available: ${e2.message}</p>`;
  });
}).then(() => {
  const match = location.pathname.match(/^\/story\/([0-9a-f]+)$/);
  if (match) openStory(match[1], { push: false });
});


// ========== v6 wiring ==========

// ---------- §8/§9 — Conflicts tab + War Mode ----------

const SIDE_COLORS = { a: [1.0, 0.42, 0.34], b: [0.36, 0.66, 1.0],
                      none: [0.72, 0.72, 0.78] };

els.unBtn.addEventListener("click", () => ctx.openUN());
// v7 §6 — the spoken personal briefing with globe autopilot
let briefingCtl = null;
async function playAudioBriefing() {
  if (!morning.briefingAvailable()) {
    alerts?.show?.({ headline: "This browser has no speech synthesis — the audio briefing needs Chrome/Edge/Safari." });
    return;
  }
  if (briefingCtl) { briefingCtl.stop(); briefingCtl = null;
    els.audioBriefingBtn.classList.remove("active"); return; }
  const stories = feed?.snapshot?.() || [];
  if (!stories.length) return;
  // v7.1 §6 — the explicit watchlist drives the briefing ranking ("overnight
  // movement on the things YOU follow"), on top of the learned interest model
  const wl = await api.watchlist().catch(() => ({ items: [] }));
  const watchTerms = (wl.items || []).map((it) => it.value).filter(Boolean);
  const segs = morning.buildSegments(stories,
    (s) => (s.lat != null ? { lat: s.lat, lon: s.lon } : null), watchTerms);
  const prevVol = sound.volume;
  els.audioBriefingBtn.classList.add("active");
  briefingCtl = morning.playBriefing(segs, {
    flyTo: (lat, lon) => state.renderer?.flyTo?.(lat, lon, state.tier === 1 ? 1.9 : undefined, 1200),
    duck: () => sound.setVolume(Math.min(prevVol, 0.12)),
    restore: () => { sound.setVolume(prevVol); briefingCtl = null;
                     els.audioBriefingBtn.classList.remove("active"); },
  });
  morning.markOffered();
}
els.audioBriefingBtn.addEventListener("click", playAudioBriefing);
// gentle once-a-day nudge: pulse the button instead of interrupting
if (morning.briefingAvailable() && morning.shouldOfferToday()) {
  els.audioBriefingBtn.classList.add("pulse-offer");
  els.audioBriefingBtn.addEventListener("click",
    () => els.audioBriefingBtn.classList.remove("pulse-offer"), { once: true });
}

// v7 §4 — the public forecast-accuracy dashboard
// v7.3 — forecast-accuracy scorecard removed (owner: "delete the forecast
// accuracy part … its dumb").
els.whatifBtn.addEventListener("click", () => {
  pane.push({ key: "whatif", title: "what-if",
              render: (el) => renderWhatIf(el, ctx) });
});
els.conflictsBtn.addEventListener("click", () => {
  pane.push({
    key: "conflicts", title: "conflicts",
    render: async (el) => {
      const data = await api.conflicts().catch(() => ({ conflicts: [] }));
      state.conflicts = data.conflicts || [];
      // v6.6.5 — two tabs at the top: full Conflicts vs Insurgencies (low-
      // intensity / separatist struggles that haven't become full-scale wars)
      el.innerHTML = `<h1>Conflicts</h1>
        <div class="conflict-tabs" style="margin-bottom:10px">
          <button class="conflict-tab cdir-tab active" data-k="ongoing">⚔ Ongoing</button>
          <button class="conflict-tab cdir-tab" data-k="frozen">❄ Frozen</button>
          <button class="conflict-tab cdir-tab" data-k="resolved">🏳 Resolved</button>
          <button class="conflict-tab cdir-tab" data-k="insurgencies">🔥 Insurgencies</button>
        </div>
        <p class="cp-meta cdir-note"></p>
        <div class="conflict-dir"></div>`;
      const NOTE = {
        ongoing: "Active and ceasefire wars. Opening one enters War Mode — a dedicated conflict panel; the live feed stays untouched.",
        frozen: "Unresolved standoffs with no active large-scale fighting. These CAN enter War Mode.",
        resolved: "Historical, ended conflicts. Opening one shows a read-only analysis — it does NOT enter War Mode.",
        insurgencies: "Low-intensity / separatist struggles. Opening one enters War Mode.",
      };
      const noteEl = el.querySelector(".cdir-note");
      const list = el.querySelector(".conflict-dir");
      const ONGOING = new Set(["active", "ceasefire"]);
      const renderCat = (kind) => {
        list.innerHTML = "";
        noteEl.textContent = NOTE[kind] || "";
        const items = state.conflicts.filter((c) => {
          if (c.is_insurgency) return kind === "insurgencies";
          const st = (c.status || "").toLowerCase();
          if (kind === "insurgencies") return false;
          if (kind === "frozen") return st === "frozen";
          if (kind === "resolved") return st === "resolved" || st === "ended";
          return ONGOING.has(st) || (!st);   // ongoing (default bucket)
        });
        for (const c of items) {
          const sides = { a: [], b: [], none: [] };
          for (const pt of (c.parties || [])) {
            (sides[pt.side || "none"] = sides[pt.side || "none"] || []).push(
              pt.country_name || pt.actor_name);
          }
          const row = document.createElement("div");
          row.className = "story-card dir-card";
          row.innerHTML = `<div class="card-meta">
              <span class="chip">${c.status}</span>
              <span class="cp-meta">${c.region || ""}</span>
              <span class="cp-meta" style="margin-left:auto">${c.story_count || 0} stories</span>
            </div><h3></h3>
            <p class="cp-meta war-sides"></p>`;
          row.querySelector("h3").textContent = c.name;
          row.querySelector(".war-sides").textContent =
            [sides.a.length ? sides.a.join(", ") : null,
             sides.b.length ? sides.b.join(", ") : null]
              .filter(Boolean).join("  ⚔  ");
          // v7 Part 6 — the curated explainer, right in the directory, so
          // someone who has never heard of this conflict learns it in place
          const kb = (c.knowledge || {}).brief;
          if (kb) {
            const p = document.createElement("p");
            p.className = "knowledge-text cdir-brief";
            const short = kb.length > 300 ? kb.slice(0, 297) + "…" : kb;
            p.textContent = short;
            if (kb.length > 300) {
              const more = document.createElement("button");
              more.className = "ap-chip";
              more.textContent = "full background";
              more.addEventListener("click", (ev) => {
                ev.stopPropagation();
                p.textContent = kb;
              });
              p.appendChild(document.createTextNode(" "));
              p.appendChild(more);
            }
            row.appendChild(p);
          }
          // v7.1 §3 — reach the Situation Room straight from the directory,
          // without first entering War Mode
          const sr = document.createElement("button");
          sr.className = "ap-chip cdir-sitroom";
          sr.textContent = "🎙 situation room";
          sr.title = "Four AI analysts argue this conflict from the same sources";
          sr.addEventListener("click", (ev) => {
            ev.stopPropagation();
            pane.push({ key: `sitroom:${c.id}`, title: "situation room",
                        render: (el) => renderSituationRoom(el, c.id, ctx) });
          });
          row.appendChild(sr);
          row.addEventListener("click", () => enterWarMode(c.id));
          list.appendChild(row);
        }
        if (!items.length) list.innerHTML =
          `<p class="cp-meta">no ${kind === "insurgencies" ? "insurgencies" : "conflicts"} registered yet</p>`;
      };
      el.querySelectorAll(".cdir-tab").forEach((t) =>
        t.addEventListener("click", () => {
          el.querySelectorAll(".cdir-tab").forEach((x) => x.classList.toggle("active", x === t));
          renderCat(t.dataset.k);
        }));
      renderCat("ongoing");
    },
  });
});

// v7.3 — detailed spoken briefing of the CURRENT conflict, driven by the
// browser's speech synthesis (no key). Narrates status, overview, the sides
// and who backs them, the live tracked developments, and — when a provider is
// up — the AI order-of-battle. Toggling again stops it.
const conflictBriefing = {
  speaking: false,
  _clean(t) {
    return String(t || "").replace(/https?:\S+/g, "").replace(/[*_#`|>]/g, "")
      .replace(/\s+/g, " ").trim();
  },
  async _segments(data) {
    const c = data.conflict || {};
    const sn = data.side_names || {};
    const segs = [`Conflict briefing: ${c.name}.`];
    const days = c.started_at
      ? Math.floor((Date.now() - new Date(c.started_at).getTime()) / 86400000) : null;
    segs.push(`Status: ${c.status || "ongoing"}${c.region ? ", in " + c.region : ""}`
      + `${days != null ? `, now in its ${days.toLocaleString()}th day` : ""}.`);
    if (c.summary) segs.push(this._clean(c.summary));
    // sides + who is on them
    for (const k of ["a", "b"]) {
      const side = (data.parties || []).filter((p) => (p.side || "") === k);
      if (!side.length) continue;
      const belligs = side.filter((p) => p.role === "belligerent")
        .map((p) => p.country_name || p.actor_name).filter(Boolean);
      const backers = side.filter((p) => p.role === "backer")
        .map((p) => p.country_name || p.actor_name).filter(Boolean);
      let line = `${sn[k] || "One side"}: ${belligs.join(", ") || "the belligerents"}`;
      if (backers.length) line += `, backed by ${backers.join(", ")}`;
      segs.push(line + ".");
    }
    // recent tracked developments from the war feed
    const recent = (feed.snapshot() || []).slice(0, 5)
      .map((s) => this._clean(s.headline)).filter(Boolean);
    if (recent.length) {
      segs.push("Recent tracked developments:");
      recent.forEach((h, i) => segs.push(`${i + 1}. ${h}.`));
    }
    // AI order of battle for real depth (degrades cleanly with no provider)
    try {
      const ob = await api.orderOfBattle(c.id);
      for (const key of ["order_of_battle", "offensives", "tactics_evolution",
                         "global_ramifications"]) {
        const v = ob && ob[key];
        if (v) segs.push(this._clean(Array.isArray(v) ? v.join(". ") : v));
      }
    } catch { /* no provider / offline — the briefing still covers the basics */ }
    segs.push("That concludes the conflict briefing.");
    return segs;
  },
  async toggle(data) {
    if (!("speechSynthesis" in window)) return;
    if (this.speaking) { this.stop(); return; }
    this.speaking = true;
    const segs = await this._segments(data);
    if (!this.speaking) return;   // stopped while fetching
    let i = 0;
    const next = () => {
      if (!this.speaking || i >= segs.length) { this.speaking = false; return; }
      const u = new SpeechSynthesisUtterance(segs[i++]);
      u.rate = 1.02;
      u.onend = () => setTimeout(next, 220);
      u.onerror = () => next();
      window.speechSynthesis.speak(u);
    };
    next();
  },
  stop() { this.speaking = false; try { window.speechSynthesis.cancel(); } catch {} },
};

// v7.4.2 — a read-only historical analysis pane for RESOLVED/ENDED conflicts.
// Viewing an old war must NOT trigger War Mode (owner: "old conflicts viewing
// should NOT trigger war mode … frozen can trigger war mode"). Same rich
// conflict panel (overview, sides, order of battle, coverage) minus the live
// war layout, map recoloring, feed changes and edge glow.
async function openResolvedConflict(conflictId, data) {
  pane.push({
    key: `conflict-view:${conflictId}`, title: "conflict (historical)",
    actions: [
      { icon: "🎙", title: "Situation Room — four AI analysts", onClick: () =>
          pane.push({ key: `sitroom:${conflictId}`, title: "situation room",
            render: (el) => renderSituationRoom(el, conflictId, ctx) }) },
      { icon: "🎧", title: "Audio briefing", onClick: () => conflictBriefing.toggle(data) },
    ],
    render: (el) => Wiki.renderWarMode(el, data, ctx),
  });
}

async function enterWarMode(conflictId) {
  if ((state.clientConfig.war_mode || {}).enabled === false) {
    selectConflict(conflictId, { forceOn: true });
    return;
  }
  let data;
  try { data = await api.warMode(conflictId); }
  catch { selectConflict(conflictId, { forceOn: true }); return; }
  // v7.4.2 — resolved/ended conflicts open READ-ONLY (no War Mode). Frozen and
  // active/ceasefire conflicts DO enter War Mode.
  const status = ((data.conflict || {}).status || "").toLowerCase();
  if (status === "resolved" || status === "ended") {
    openResolvedConflict(conflictId, data);
    return;
  }
  // v7.4.2 — War Mode CLOSES the live feed and shows a conflict-only panel
  // instead of filtering the feed. Nothing to snapshot/restore anymore.
  setFeedVisible(false);
  state.warMode = data;
  state.warTab = "";
  state.conflictId = conflictId;
  setFocus("conflict", data.conflict.name);

  // map: frame/zoom straight to the conflict zone (§8, §13)
  const f = data.frame;
  if (f && state.renderer?.flyTo) {
    const span = Math.max(f.max_lat - f.min_lat, f.max_lon - f.min_lon, 4);
    if (state.tier === 1) {
      const dist = Math.max(1.55, Math.min(2.6, 1.35 + span / 38));
      state.renderer.flyTo(f.center_lat, f.center_lon, dist, 1100);
    } else {
      state.renderer.flyTo(f.center_lat, f.center_lon);
    }
  }

  // parties: one consistent color per side, painted on their borders
  const groups = [];
  for (const side of ["a", "b"]) {
    const isos = (data.parties || [])
      .filter((pt) => pt.side === side && pt.country_id)
      .map((pt) => pt.country_id);
    const rings = [];
    for (const c of BOUNDARIES_50M) if (isos.includes(c.i)) rings.push(...c.r);
    if (rings.length) groups.push({ rings, color: SIDE_COLORS[side] });
  }
  state.renderer?.setColoredRings?.(groups);

  // subfactions: conflict-scoped internal-control areas that never render in
  // global mode (side a → established/pink, side b → contested/amber)
  const warZones = (data.subfactions || []).filter((sf) => sf.zone_geojson)
    .map((sf) => ({ nsa_id: null, nsa_name: sf.name,
                    confidence: sf.side === "a" ? "established"
                      : sf.side === "b" ? "contested" : "reported",
                    geojson: sf.zone_geojson }));
  state.renderer?.setActorZones?.([
    ...(state.actorsOn ? state.actorZones : []), ...warZones]);

  // left panel: wiki-infobox conflict overview on the shared pane shell (§8).
  // v7.3 — two small icon actions next to the fullscreen toggle: the Situation
  // Room (four-analyst debate) and a detailed spoken conflict briefing.
  pane.push({
    key: `war:${conflictId}`, title: "war mode",
    focus: { type: "conflict", name: data.conflict.name },
    actions: [
      { icon: "🎙", title: "Situation Room — four AI analysts argue this conflict",
        onClick: () => pane.push({ key: `sitroom:${conflictId}`, title: "situation room",
          render: (el) => renderSituationRoom(el, conflictId, ctx) }) },
      { icon: "🎧", title: "Audio briefing — a detailed spoken rundown of this conflict",
        onClick: () => conflictBriefing.toggle(data) },
    ],
    render: (el) => Wiki.renderWarMode(el, data, ctx),
  });

  document.body.classList.add("war-active");   // v6.6.6 — themed edge glow
}

function exitWarMode() {
  conflictBriefing.stop();   // v7.3 — silence any running conflict briefing
  document.body.classList.remove("war-active");   // v6.6.6 — clear edge glow
  if (!state.warMode) return;
  state.warMode = null;
  state.warTab = "";
  state.conflictId = null;
  setFocus(null);
  state.renderer?.setColoredRings?.([]);
  state.renderer?.setActorZones?.(state.actorsOn ? state.actorZones : []);
  // v7.4.2 — War Mode closed the live feed on entry; reopen it and refresh the
  // full global feed (it was never filtered, so there's no snapshot to restore).
  setFeedVisible(true);
  refreshStories().catch(() => {});
}
window.__gg.exitWarMode = exitWarMode;
window.__gg.enterWarMode = enterWarMode;   // v6.6.6 — exposed for scripting/tests

// §8 — right-panel sub-filters: Military / Civilian / Diplomatic / Economic
function renderWarTabs() {
  els.conflictTabs.innerHTML = "";
  const name = document.createElement("span");
  name.className = "war-name";
  name.textContent = "⚔ " + (state.warMode.conflict.name || "");
  els.conflictTabs.appendChild(name);
  for (const [id, label] of [["", "all"], ["military", "⚔ military"],
                             ["civilian", "🏥 civilian"],
                             ["diplomatic", "🕊 diplomatic"],
                             ["economic", "📈 economic"]]) {
    const tab = document.createElement("button");
    tab.className = "conflict-tab" + (state.warTab === id ? " active" : "");
    tab.textContent = label;
    tab.addEventListener("click", () => {
      state.warTab = id;
      renderWarTabs();
      refreshStories().catch(() => {});
    });
    els.conflictTabs.appendChild(tab);
  }
  const exit = document.createElement("button");
  exit.className = "conflict-tab war-exit";
  exit.textContent = "✕ exit war mode";
  exit.addEventListener("click", exitWarMode);
  els.conflictTabs.appendChild(exit);
}

// ---------- §11 — site-wide language + transliterated wordmark ----------

// phonetically accurate transliterations of "GlobeGrid" — a fixed,
// human-reviewed lookup per script (brand names get a consistent spelling,
// never a fresh machine guess)
const WORDMARK_TRANSLIT = {
  ru: "ГлобГрид", uk: "ГлобГрід", be: "ГлобГрыд", sr: "ГлобГрид",
  mk: "ГлобГрид", bg: "ГлобГрид",
  ar: "غلوبغريد", fa: "گلوب‌گرید", ur: "گلوب گرڈ", he: "גלובגריד",
  hi: "ग्लोबग्रिड", ka: "გლობგრიდი", hy: "ԳլոբԳրիդ",
  el: "ΓκλομπΓκριντ", th: "โกลบกริด",
  ja: "グローブグリッド", ko: "글로브그리드",
  "zh-Hans": "环球格网", "zh-Hant": "環球格網",
  my: "ဂလုဘ်ဂရစ်", km: "គ្លូបគ្រីដ", lo: "ໂກລບກຣິດ", am: "ግሎብግሪድ",
};

function setSiteLanguage(code) {
  state.lang = code;
  applyLanguage(code);   // v5 §2 — dir/lang attributes + persistence
  // §11 — script-matched wordmark next to the Latin brand
  const t = (state.clientConfig.ui || {}).wordmark_transliteration !== false
    ? WORDMARK_TRANSLIT[code] : null;
  els.brandTranslit.textContent = t || "";
  if (els.langBtn.value !== code) els.langBtn.value = code;
}

for (const l of LANGUAGES) {
  const o = document.createElement("option");
  o.value = l.code;
  o.textContent = l.code === "en" ? "English (American)" : l.name;
  els.langBtn.appendChild(o);
}
els.langBtn.value = state.lang;
els.langBtn.addEventListener("change", () => setSiteLanguage(els.langBtn.value));
if (state.lang !== "en") setSiteLanguage(state.lang);

// v6.6 — live feed panel is closable (X button / Esc last); a slim edge tab
// restores it so it's never unreachable
const feedPanelEl = document.getElementById("feed-panel");
const feedCloseBtn = document.getElementById("feed-close");
let feedReopenTab = null;
function setFeedVisible(on) {
  feedPanelEl.style.display = on ? "" : "none";
  // v6.6.7 — keep the analyst orb aligned: sit just LEFT of the live-feed panel
  // when it's open, flush to the right edge when it's closed. The CSS transition
  // on #analyst-orb makes the move smooth.
  const w = feedPanelEl.offsetWidth || 360;
  document.documentElement.style.setProperty("--orb-right", on ? (w + 20) + "px" : "22px");
  if (!on && !feedReopenTab) {
    feedReopenTab = document.createElement("button");
    feedReopenTab.id = "feed-reopen";
    feedReopenTab.textContent = "◀ live feed";
    feedReopenTab.addEventListener("click", () => setFeedVisible(true));
    document.body.appendChild(feedReopenTab);
  }
  if (feedReopenTab) feedReopenTab.style.display = on ? "none" : "";
}
if (feedCloseBtn) feedCloseBtn.addEventListener("click", () => setFeedVisible(false));

// ---------- §12 — ESC closes panels one at a time (a real stack) ----------

// One keydown handler querying the stack — topmost/rightmost first. The
// per-panel listeners this replaces are disabled via data flags below.
document.addEventListener("keydown", (ev) => {
  if (ev.key !== "Escape") return;
  if (ev.target && /INPUT|TEXTAREA|SELECT/.test(ev.target.tagName)) return;
  const closers = [
    [() => !palette.el.classList.contains("hidden"), () => palette.hide?.() || palette.toggle()],
    [() => !els.modesBar.classList.contains("hidden"), () => toggleModesBar(false)],
    [() => !els.statusDrawer.classList.contains("hidden"), () => statusPanel.close()],
    [() => !els.graphOverlay.classList.contains("hidden"),
     () => els.graphOverlay.classList.add("hidden")],
    [() => !els.briefingOverlay.classList.contains("hidden"),
     () => els.briefingOverlay.classList.add("hidden")],
    [() => !els.lineageOverlay.classList.contains("hidden"),
     () => els.lineageOverlay.classList.add("hidden")],
    [() => !els.watchlistPanel.classList.contains("hidden"),
     () => els.watchlistPanel.classList.add("hidden")],
    [() => !analyst.panel.classList.contains("hidden"), () => analyst.hide()],
    [() => pane.top(), () => pane.back()],
    [() => state.warMode, () => exitWarMode()],
    [() => feedPanelEl.style.display !== "none" && !!feedReopenTab, () => setFeedVisible(false)],
  ];
  for (const [check, close] of closers) {
    if (check()) { close(); ev.stopPropagation(); return; }
  }
}, { capture: true });

// ---------- §6 — drag-to-select rectangle (screen-axis-aligned) ----------

// Shift+drag draws an upright selection box (PDX-style — always parallel to
// the window edges, never rotated with the globe); on release every event
// inside opens in the left pane, grouped by location.
(() => {
  const box = document.createElement("div");
  box.id = "rect-select";
  box.style.display = "none";
  els.mapHost.appendChild(box);
  let start = null;
  els.mapHost.addEventListener("pointerdown", (ev) => {
    if (!ev.shiftKey) return;
    start = { x: ev.clientX, y: ev.clientY };
    box.style.display = "block";
    ev.preventDefault(); ev.stopPropagation();
  }, { capture: true });
  window.addEventListener("pointermove", (ev) => {
    if (!start) return;
    const host = els.mapHost.getBoundingClientRect();
    box.style.left = (Math.min(start.x, ev.clientX) - host.left) + "px";
    box.style.top = (Math.min(start.y, ev.clientY) - host.top) + "px";
    box.style.width = Math.abs(ev.clientX - start.x) + "px";
    box.style.height = Math.abs(ev.clientY - start.y) + "px";
  });
  window.addEventListener("pointerup", (ev) => {
    if (!start) return;
    box.style.display = "none";
    const dragged = Math.abs(ev.clientX - start.x) + Math.abs(ev.clientY - start.y);
    // a real drag must never fall through to the renderer's own click
    // resolution (which would open whatever country sits under the cursor)
    if (dragged > 10) { ev.stopPropagation(); ev.preventDefault(); }
    const events = state.renderer?.eventsInRect?.(start.x, start.y,
                                                  ev.clientX, ev.clientY) || [];
    start = null;
    if (dragged <= 10 || !events.length) return;
    // grouped by location, reusing the cluster list-content template (v5 §9)
    const byLoc = new Map();
    for (const e of events) {
      const key = e.location_name || "unknown location";
      if (!byLoc.has(key)) byLoc.set(key, []);
      byLoc.get(key).push(e);
    }
    pane.push({
      key: `rect:${Date.now()}`,
      title: `${events.length} selected events`,
      render: (el) => {
        el.innerHTML = `<h1>${events.length} events in selection</h1>`;
        for (const [loc, evs] of [...byLoc.entries()]
            .sort((a, b) => b[1].length - a[1].length)) {
          const sec = document.createElement("section");
          sec.innerHTML = `<h4>${loc.replace(/</g, "&lt;")} · ${evs.length}</h4>`;
          for (const e of evs) {
            const row = document.createElement("div");
            row.className = "cluster-row";
            row.innerHTML = `<span class="chip cat-${e.category || "other"}">${e.category || "other"}</span> <span></span>`;
            row.querySelector("span:last-child").textContent = e.title || "";
            if (e.story_id) {
              row.style.cursor = "pointer";
              row.addEventListener("click", () => openStory(e.story_id));
            }
            sec.appendChild(row);
          }
          el.appendChild(sec);
        }
      },
    });
  }, { capture: true });
})();

// ---------- §16 — thematic map modes (EU5-style rollout icon bar) ----------

let mapModesCache = null;
const MODE_CAT_PALETTE = ["#4da3ff", "#ffd166", "#ff6b6b", "#7bd88f", "#c792ea",
                          "#f78c6c", "#89ddff", "#e6a1c4", "#b5bd68"];

function toggleModesBar(show) {
  els.modesBar.classList.toggle("hidden", show === false);
  els.modesBtn.classList.toggle("active", show !== false);
}

els.modesBtn.addEventListener("click", async () => {
  if (!els.modesBar.classList.contains("hidden")) { toggleModesBar(false); return; }
  if (!mapModesCache) {
    const data = await api.mapModes().catch(() => ({ modes: [] }));
    mapModesCache = data.modes || [];
    els.modesBar.innerHTML = "";
    const off = document.createElement("button");
    off.className = "mode-chip";
    off.textContent = "✕ off";
    off.addEventListener("click", () => applyMapMode(null));
    els.modesBar.appendChild(off);
    for (const m of mapModesCache) {
      const b = document.createElement("button");
      b.className = "mode-chip";
      b.dataset.mode = m.id;
      b.innerHTML = `<span class="mode-ico">${m.icon}</span> ${m.label}`;
      b.title = `${m.label} — source: ${m.source}`;
      b.addEventListener("click", () => applyMapMode(m.id));
      els.modesBar.appendChild(b);
    }
  }
  toggleModesBar(true);
});

function _rampColor(t) {
  // v6.1 — deep-blue → magenta → amber → yellow sequential ramp at higher
  // opacity (owner: "more clear map mode shading that is more visible"). A
  // 3-stop ramp separates the low/mid/high bands far more than the old
  // teal→amber two-stop, and 0.72 alpha reads clearly over the base map.
  let r, g, b;
  if (t < 0.5) {           // deep blue → magenta
    const u = t / 0.5;
    r = Math.round(40 + 180 * u); g = Math.round(50 + 20 * u); b = Math.round(150 + 40 * u);
  } else {                 // magenta → amber → yellow
    const u = (t - 0.5) / 0.5;
    r = Math.round(220 + 30 * u); g = Math.round(70 + 150 * u); b = Math.round(190 - 170 * u);
  }
  return `rgba(${r},${g},${b},0.72)`;
}

async function applyMapMode(mode) {
  state.mapMode = mode;
  els.modesBar.querySelectorAll(".mode-chip").forEach((c) =>
    c.classList.toggle("active", c.dataset.mode === mode));
  if (!mode) {
    state.renderer?.setChoropleth?.(null);
    els.modeLegend.classList.add("hidden");
    state.modeValues = null;   // v6.1.1 — stop the hover tooltip
    return;
  }
  const d = await api.mapMode(mode).catch(() => null);
  if (!d) return;
  const colors = {};
  let legendHtml = `<b>${d.label}</b>`;
  if (d.kind === "numeric") {
    const lo = d.log_scale ? Math.log10(Math.max(1e-9, d.min)) : d.min;
    const hi = d.log_scale ? Math.log10(Math.max(1e-9, d.max)) : d.max;
    for (const [iso3, v] of Object.entries(d.values)) {
      const x = d.log_scale ? Math.log10(Math.max(1e-9, v)) : v;
      colors[iso3] = _rampColor(Math.max(0, Math.min(1, (x - lo) / (hi - lo || 1))));
    }
    legendHtml += ` <span class="ramp"></span>
      <span>${Number(d.min).toLocaleString()} – ${Number(d.max).toLocaleString()}</span>`;
  } else {
    // v6.1.1 — language/religion modes colour by FAMILY (related families sit
    // near each other on the hue wheel) so the map groups at a glance; other
    // categorical modes keep the arbitrary distinct palette.
    const isLang = /lang/i.test(mode), isRel = /relig/i.test(mode);
    const infoFor = isLang ? (v) => LANGUAGE_INFO[v]
      : isRel ? (v) => RELIGION_INFO[v] : null;
    const catColor = {};
    (d.categories || []).forEach((c, i) => {
      catColor[c] = MODE_CAT_PALETTE[i % MODE_CAT_PALETTE.length];
    });
    const colorFor = (v) => infoFor
      ? familyColor(infoFor(v), 0.72) : (catColor[v] + "b0");
    for (const [iso3, v] of Object.entries(d.values)) colors[iso3] = colorFor(v);
    if (infoFor) {
      // legend groups by FAMILY (no per-value key needed — hover names it)
      const fam = {};
      for (const c of (d.categories || [])) {
        const inf = infoFor(c);
        const f = inf ? inf.family : "other";
        (fam[f] = fam[f] || { color: colorFor(c), items: [] }).items.push(c);
      }
      legendHtml += " " + Object.entries(fam).map(([f, o]) =>
        `<span class="cat"><i style="background:${o.color}"></i>${f}</span>`).join(" ")
        + ` <span class="src">hover a country for details</span>`;
    } else {
      legendHtml += " " + (d.categories || []).map((c) =>
        `<span class="cat"><i style="background:${catColor[c]}"></i>${c}</span>`).join(" ");
    }
    // area-level modes: sub-national polygons override their country fill
    if (d.areas) {
      const areaZones = d.areas.filter((a) => a.zone_geojson).map((a) => ({
        nsa_id: null, nsa_name: `${a.name} — ${a.value}`,
        confidence: "reported", geojson: a.zone_geojson,
        _color: catColor[a.value],
      }));
      state.renderer?.setActorZones?.([
        ...(state.actorsOn ? state.actorZones : []), ...areaZones]);
    }
  }
  if (!/relig|lang/i.test(mode))
    legendHtml += ` <span class="src" title="data source">${d.source}</span>`;
  // v6.1.1 — remember the per-country value + a human label for the hover tooltip
  state.modeValues = d.values || null;
  state.modeLabel = d.label;
  state.modeUnit = d.kind === "numeric"
    ? (v) => Number(v).toLocaleString() : (v) => v;
  state.renderer?.setChoropleth?.(colors);
  els.modeLegend.innerHTML = legendHtml;
  els.modeLegend.classList.remove("hidden");
}

// v6.1.1 — hover tooltip for map modes: name the country + its value
// (language / religion / metric) under the cursor, so no colour key is needed.
let _modeTip = null;
function ensureModeTip() {
  if (_modeTip) return _modeTip;
  _modeTip = document.createElement("div");
  _modeTip.id = "mode-tip";
  _modeTip.className = "hidden";
  document.body.appendChild(_modeTip);
  return _modeTip;
}
els.mapHost.addEventListener("pointermove", (ev) => {
  if (!state.mapMode || !state.modeValues || !state.renderer?.screenToLatLon) {
    if (_modeTip) _modeTip.classList.add("hidden");
    return;
  }
  const geo = state.renderer.screenToLatLon(ev.clientX, ev.clientY);
  // countryAt returns the boundary object ({i, n, ...}); take its iso3
  const hit = geo ? countryAt(geo.lat, geo.lon) : null;
  const iso3 = hit && hit.i;
  const tip = ensureModeTip();
  if (!iso3 || !(iso3 in state.modeValues)) { tip.classList.add("hidden"); return; }
  const val = state.modeValues[iso3];
  const shown = state.modeUnit ? state.modeUnit(val) : val;
  tip.innerHTML = `<b>${(ISO3_NAME[iso3] || iso3).replace(/</g, "&lt;")}</b>`
    + `<span>${state.modeLabel}: ${String(shown).replace(/</g, "&lt;")}</span>`;
  tip.style.left = (ev.clientX + 14) + "px";
  tip.style.top = (ev.clientY + 14) + "px";
  tip.classList.remove("hidden");
});
els.mapHost.addEventListener("pointerleave", () => {
  if (_modeTip) _modeTip.classList.add("hidden");
});

// ---------- §13 — feed click moves the camera to the event ----------

// opening a story from anywhere also flies the camera to that story's most
// recent located event (mapEvents rows carry story_id + coordinates)
const _openStoryOrig = openStory;
openStory = function (id, opts) {
  const hit = (state.mapData.events || []).find(
    (e) => e.story_id === id && e.lat != null);
  if (hit) {
    if (state.tier === 1) {
      state.renderer?.flyTo?.(hit.lat, hit.lon,
        Math.min(2.4, state.renderer.dist || 2.4));
    } else {
      state.renderer?.flyTo?.(hit.lat, hit.lon);
    }
  }
  return _openStoryOrig(id, opts);
};
window.__gg.openStory = openStory;
