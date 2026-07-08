// v7 §6 — the personal morning audio briefing: a ~3-minute SPOKEN digest of
// overnight movement on the stories YOU follow, narrated with the browser's
// built-in speech synthesis (no network, no key) while the globe auto-flies
// between the stories as it speaks. The ambient music ducks under the voice
// and swells back after. Interests are learned locally (localStorage) from
// what you actually open — nothing leaves the machine.

const INTEREST_KEY = "tdl_interests";
const DAY_KEY = "tdl_briefing_day";

export function trackInterest(story) {
  // called on every story open: learn category + named entities
  try {
    const w = JSON.parse(localStorage.getItem(INTEREST_KEY) || "{}");
    const bump = (k) => { if (k) w[k] = Math.min((w[k] || 0) + 1, 40); };
    bump("cat:" + (story.category || "other"));
    (String(story.headline || "").match(/[A-Z][a-z]{3,}/g) || [])
      .slice(0, 4).forEach((e) => bump("ent:" + e.toLowerCase()));
    localStorage.setItem(INTEREST_KEY, JSON.stringify(w));
  } catch { /* localStorage full/blocked — learning is best-effort */ }
}

function interestScore(story, watchTerms) {
  let w = {};
  try { w = JSON.parse(localStorage.getItem(INTEREST_KEY) || "{}"); } catch { }
  let sc = (story.confidence || 0.4);
  sc += (w["cat:" + (story.category || "other")] || 0) * 0.08;
  const hl = String(story.headline || "");
  for (const e of (hl.match(/[A-Z][a-z]{3,}/g) || []))
    sc += (w["ent:" + e.toLowerCase()] || 0) * 0.05;
  // v7.1 — the explicit watchlist gets a strong boost: "overnight movement on
  // the things YOU follow" is the point of the briefing.
  const low = hl.toLowerCase() + " " + String(story.summary || "").toLowerCase();
  for (const t of (watchTerms || []))
    if (t && low.includes(t.toLowerCase())) sc += 1.0;
  return sc;
}

function cleanForSpeech(text) {
  return String(text || "")
    .replace(/https?:\S+/g, "").replace(/[*_#`|>]/g, "")
    .replace(/\s+/g, " ").trim();
}

export function briefingAvailable() {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function shouldOfferToday() {
  const today = new Date().toISOString().slice(0, 10);
  return localStorage.getItem(DAY_KEY) !== today;
}

export function markOffered() {
  localStorage.setItem(DAY_KEY, new Date().toISOString().slice(0, 10));
}

// Speak `segments` [{text, lat?, lon?}] flying the map between them.
// Returns a controller with stop().
export function playBriefing(segments, { flyTo, duck, restore } = {}) {
  const synth = window.speechSynthesis;
  synth.cancel();
  let stopped = false;
  duck?.();
  const speakNext = (i) => {
    if (stopped || i >= segments.length) { restore?.(); return; }
    const seg = segments[i];
    if (seg.lat != null && seg.lon != null) flyTo?.(seg.lat, seg.lon);
    const u = new SpeechSynthesisUtterance(seg.text);
    u.rate = 1.02;
    u.onend = () => setTimeout(() => speakNext(i + 1), 350);
    u.onerror = () => speakNext(i + 1);
    synth.speak(u);
  };
  speakNext(0);
  return { stop: () => { stopped = true; synth.cancel(); restore?.(); } };
}

// Build the segment list from the live stories, interest-ranked. `watchTerms`
// are the user's explicit watchlist values (boosted hard).
export function buildSegments(stories, locate, watchTerms) {
  const ranked = [...(stories || [])].sort((a, z) =>
    interestScore(z, watchTerms) - interestScore(a, watchTerms)).slice(0, 6);
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning." : hour < 18 ? "Good afternoon." : "Good evening.";
  const segs = [{ text: `${greet} This is your GlobeGrid intelligence briefing — `
    + `${ranked.length} developments on your radar.` }];
  ranked.forEach((s, i) => {
    const loc = locate?.(s) || {};
    segs.push({
      text: `${i + 1}. ${cleanForSpeech(s.headline)}. `
        + cleanForSpeech((s.summary || "").split(/(?<=\.)\s/).slice(0, 2).join(" ")),
      lat: loc.lat, lon: loc.lon,
    });
  });
  segs.push({ text: "That completes your briefing. The full analysis is on the globe." });
  return segs;
}
