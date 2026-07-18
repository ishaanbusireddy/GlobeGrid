// v8.16 — the live tracking windows: Military, Trade & Resources, Markets,
// Prediction Markets and the Diplomatic Window. Every window states its data
// layering honestly: LIVE (extracted events, sensors, real prediction-market
// odds) vs CURATED (year+source-labelled statistics). Opened from the header
// trackers button; each window is its own pane page.
import { api } from "../../api/client.js";
import { formatDateTime } from "../../data/timefmt.js";

const esc = (s) => String(s == null ? "" : s).replace(/</g, "&lt;");
const num = (n) => (n == null ? "—" : Number(n).toLocaleString("en-US"));
const usdB = (n) => (n == null ? "—" : "$" + (n >= 1000 ? (n / 1000).toFixed(2) + "T" : Math.round(n) + "B"));

export function renderTrackers(el, ctx) {
  el.innerHTML = `
    <h1>Tracking Windows</h1>
    <p class="cp-meta">Live, focused monitors over the same event chain the map runs on —
       plus curated statistical context (every curated figure carries its year + source).</p>
    <div class="tracker-grid">
      <button class="tracker-card" data-w="military"><b>Military Tracker</b>
        <span>Live Military & Conflict Events with coordinates, physical-sensor tracks, standing force posture</span></button>
      <button class="tracker-card" data-w="trade"><b>Trade & Resources</b>
        <span>Exports/imports, partners, chokepoints, resources & industry by country + live trade news</span></button>
      <button class="tracker-card" data-w="markets"><b>Markets</b>
        <span>Live market & finance events off the wire + the hourly market briefing</span></button>
      <button class="tracker-card" data-w="pred"><b>Prediction Markets</b>
        <span>Real-money geopolitics odds from Polymarket & Kalshi, refreshed live</span></button>
      <button class="tracker-card" data-w="diplomacy"><b>Diplomatic Window</b>
        <span>Any two countries: current stance, background briefs, and their shared live coverage</span></button>
    </div>`;
  el.querySelectorAll(".tracker-card").forEach((b) =>
    b.addEventListener("click", () => openTracker(ctx, b.dataset.w)));
}

// v8.18 — one place that opens a tracking window by key, reused by the hub
// cards AND the header dropdown (owner: "split the tracker windows into their
// own buttons" → a dropdown of the 5 windows, one click each).
export const TRACKER_WINDOWS = [
  ["military", "Military Tracker"],
  ["trade", "Trade & Resources"],
  ["markets", "Markets"],
  ["pred", "Prediction Markets"],
  ["diplomacy", "Diplomatic Window"],
];
export function openTracker(ctx, w) {
  if (w === "military") ctx.pane.push({ key: "trk:mil", title: "military tracker", render: (e2) => renderMilitary(e2, ctx) });
  else if (w === "trade") ctx.pane.push({ key: "trk:trade", title: "trade & resources", render: (e2) => renderTrade(e2, ctx) });
  else if (w === "markets") ctx.pane.push({ key: "trk:mkt", title: "markets", render: (e2) => renderMarketsLive(e2, ctx) });
  else if (w === "pred") ctx.pane.push({ key: "trk:pred", title: "prediction markets", render: (e2) => renderPredMarkets(e2, ctx) });
  else if (w === "diplomacy") ctx.pane.push({ key: "trk:dip", title: "diplomatic window", render: (e2) => renderDiplomacy(e2, ctx) });
}

export async function renderMilitary(el, ctx) {
  el.innerHTML = `<h1>Military Tracker</h1><p class="cp-meta">loading…</p>`;
  const d = await api.military(120).catch(() => null);
  if (!d) { el.innerHTML = "<h1>Military Tracker</h1><p>Unavailable right now.</p>"; return; }
  const evRow = (e, sensor) => `
    <button class="ap-chip trk-evt" data-lat="${e.lat}" data-lon="${e.lon}">
      <span class="chip cat-${esc(e.category || "conflict")}">${sensor ? "" + esc(e.source_type) : esc(e.development_type || e.category)}</span>
      <span class="trk-evt-t">${esc(e.title)}</span>
      <span class="cp-meta">${e.lat != null ? e.lat.toFixed(2) + ", " + e.lon.toFixed(2) : ""} · ${esc(formatDateTime(e.occurred_at))}</span>
    </button>`;
  el.innerHTML = `
    <h1>Military Tracker</h1>
    <p class="cp-meta">${esc(d.layers_note)}</p>
    <section><h4>Live Military & Conflict Events <span class="cp-meta">(extracted from the wire, precise coordinates)</span></h4>
      ${d.events.length ? d.events.map((e) => evRow(e, false)).join("") : "<p class='cp-meta'>No live military events in the chain right now — they stream in as sources report.</p>"}
    </section>
    <section><h4>Physical-sensor Tracks <span class="cp-meta">(air traffic / shipping / thermal / seismic — key-gated feeds say so)</span></h4>
      ${d.sensors.length ? d.sensors.map((e) => evRow(e, true)).join("") : "<p class='cp-meta'>No sensor tracks in-window (AIS/FIRMS/OpenSky keys or live reach required).</p>"}
    </section>
    <section><h4>Standing Force Posture <span class="cp-meta">(curated context, mid-2026 — not live tracks)</span></h4>
      ${d.posture.map((p) => `
        <button class="ap-chip trk-evt" data-lat="${p.lat}" data-lon="${p.lon}">
          <b>${esc(p.actor)}</b> <span class="trk-evt-t">${esc(p.what)}</span>
          <span class="cp-meta">${esc(p.where)} — ${esc(p.note)}</span>
        </button>`).join("")}
    </section>`;
  el.querySelectorAll(".trk-evt").forEach((b) => b.addEventListener("click", () => {
    const lat = parseFloat(b.dataset.lat), lon = parseFloat(b.dataset.lon);
    if (!Number.isNaN(lat)) ctx.flyToBounds && ctx.flyToBounds(null, lat, lon);
  }));
}

export async function renderTrade(el, ctx, iso3) {
  el.innerHTML = `<h1>Trade & Resources</h1><p class="cp-meta">loading…</p>`;
  const world = await api.tradeWorld().catch(() => null);
  const opts = (world?.countries_covered || []).map((c) =>
    `<option value="${c}"${c === iso3 ? " selected" : ""}>${c}</option>`).join("");
  let country = null;
  if (iso3) country = await api.tradeCountry(iso3).catch(() => null);
  const w = world?.world || {};
  el.innerHTML = `
    <h1>Trade & Resources</h1>
    <section><h4>World Trade</h4>
      <div class="stat-grid">
        <div class="stat-cell"><span>World exports</span><b>${usdB(w.world_exports_usd_b)}</b></div>
        <div class="stat-cell"><span>Year</span><b>${esc(w.year || "")}</b></div>
      </div>
      <p class="cp-meta">${esc(w.src || "")}</p>
      ${(w.chokepoints || []).length ? `<h4>Chokepoints</h4>` + w.chokepoints.map((c) =>
        `<div class="src-row"><b>${esc(c.name)}</b> — ${esc(c.share)} <span class="cp-meta">${esc(c.note || "")}</span></div>`).join("") : ""}
    </section>
    <section><h4>Country profile</h4>
      <select id="trk-trade-c"><option value="">— pick a country —</option>${opts}</select>
      <div id="trk-trade-body"></div>
    </section>`;
  const body = el.querySelector("#trk-trade-body");
  if (country) {
    const t = country.trade, r = country.resources;
    body.innerHTML = `
      ${t ? `<div class="stat-grid">
        <div class="stat-cell"><span>Exports (${esc(t.year)})</span><b>${usdB(t.exports_usd_b)}</b></div>
        <div class="stat-cell"><span>Imports (${esc(t.year)})</span><b>${usdB(t.imports_usd_b)}</b></div>
      </div>
      <p><b>Top exports:</b> ${esc((t.top_exports || []).join(", "))}</p>
      <p><b>Top imports:</b> ${esc((t.top_imports || []).join(", "))}</p>
      <p><b>Main partners:</b> ${esc((t.partners || []).join(", "))}</p>
      <p class="cp-meta">${esc(t.src || "")}</p>` : `<p class="cp-meta">${esc(country.note)}</p>`}
      ${r ? `<h4>Resources & Industry</h4>
        <p><b>Key resources:</b> ${esc((r.resources || []).join(", "))}</p>
        ${r.production ? `<p><b>Headline production:</b> ${esc(r.production)}</p>` : ""}
        ${r.industry ? `<p><b>Industrial base:</b> ${esc(r.industry)}</p>` : ""}
        <p class="cp-meta">${esc(r.src || "")}</p>` : ""}
      ${(country.live_trade_news || []).length ? `<h4>Live Trade Coverage</h4>` +
        country.live_trade_news.map((s) => `<button class="ap-chip trk-story" data-id="${esc(s.id)}">${esc(s.headline)}</button>`).join("") : ""}`;
    body.querySelectorAll(".trk-story").forEach((b) =>
      b.addEventListener("click", () => ctx.openStory && ctx.openStory(b.dataset.id)));
  }
  el.querySelector("#trk-trade-c").addEventListener("change", (ev) => {
    if (ev.target.value) renderTrade(el, ctx, ev.target.value);
  });
}

export async function renderMarketsLive(el, ctx) {
  el.innerHTML = `<h1>Markets</h1><p class="cp-meta">loading…</p>`;
  const d = await api.marketsLive().catch(() => null);
  if (!d) { el.innerHTML = "<h1>Markets</h1><p>Unavailable right now.</p>"; return; }
  el.innerHTML = `
    <h1>Markets</h1>
    <p class="cp-meta">${esc(d.note)}</p>
    ${d.market_briefing ? `<section><h4>Market briefing</h4>
      <div class="briefing-text">${esc(d.market_briefing.content).replace(/\n/g, "<br>")}</div>
      <p class="cp-meta">generated ${esc(formatDateTime(d.market_briefing.generated_at))}</p></section>` : ""}
    <section><h4>Live market & finance events</h4>
      ${d.events.length ? d.events.map((e) => `
        <div class="src-row"><b>${esc(e.title)}</b>
        <span class="cp-meta">${esc(e.source_name)} · ${esc(formatDateTime(e.occurred_at))}</span></div>`).join("")
        : "<p class='cp-meta'>No market events in-window yet — they stream in from the finance wires (an Alpha Vantage key adds the market data source).</p>"}
    </section>`;
}

export async function renderPredMarkets(el, ctx, q) {
  el.innerHTML = `<h1>Prediction Markets</h1><p class="cp-meta">loading live odds…</p>`;
  const d = await api.predMarkets(q).catch(() => null);
  if (!d) { el.innerHTML = "<h1>Prediction Markets</h1><p>Unavailable right now.</p>"; return; }
  el.innerHTML = `
    <h1>Prediction Markets</h1>
    <p class="cp-meta">${esc(d.note)}</p>
    <div class="feed-tools"><input id="trk-pred-q" placeholder="filter markets… (e.g. ukraine, taiwan)" value="${esc(q || "")}">
      <button id="trk-pred-r" class="ap-chip">↻ refresh</button></div>
    <section id="trk-pred-list">
      ${(d.markets || []).length ? d.markets.map((m) => `
        <a class="src-row pred-row" href="${esc(m.url)}" target="_blank" rel="noopener">
          <span class="pred-odds">${m.yes_price != null ? Math.round(m.yes_price * 100) + "%" : "—"}</span>
          <b>${esc(m.title)}</b>
          <span class="cp-meta">${esc(m.source)} · 24h vol ${num(Math.round(m.volume_24h || 0))}</span>
        </a>`).join("") : (d.live ? "<p class='cp-meta'>No geopolitics markets matched the filter.</p>" : "")}
    </section>`;
  const rerun = () => renderPredMarkets(el, ctx, el.querySelector("#trk-pred-q").value.trim());
  el.querySelector("#trk-pred-r").addEventListener("click", rerun);
  el.querySelector("#trk-pred-q").addEventListener("keydown", (ev) => { if (ev.key === "Enter") rerun(); });
}

export async function renderDiplomacy(el, ctx, a, b) {
  const countries = await api.countries().catch(() => ({ countries: [] }));
  const list = (countries.countries || []).filter((c) => c.id && c.id.length === 3);
  const opts = (sel) => list.map((c) =>
    `<option value="${c.id}"${c.id === sel ? " selected" : ""}>${esc(c.name)}</option>`).join("");
  el.innerHTML = `
    <h1>Diplomatic Window</h1>
    <p class="cp-meta">Pick any two countries for their current stance, background briefs, and shared live coverage.</p>
    <div class="feed-tools">
      <select id="dip-a"><option value="">country A</option>${opts(a)}</select>
      <span>×</span>
      <select id="dip-b"><option value="">country B</option>${opts(b)}</select>
    </div>
    <div id="dip-body">${a && b ? "<p class='cp-meta'>loading…</p>" : ""}</div>`;
  const rerun = () => {
    const va = el.querySelector("#dip-a").value, vb = el.querySelector("#dip-b").value;
    if (va && vb && va !== vb) renderDiplomacy(el, ctx, va, vb);
  };
  el.querySelector("#dip-a").addEventListener("change", rerun);
  el.querySelector("#dip-b").addEventListener("change", rerun);
  if (!(a && b)) return;
  const d = await api.diplomacy(a, b).catch(() => null);
  const body = el.querySelector("#dip-body");
  if (!d) { body.innerHTML = "<p>Unavailable right now.</p>"; return; }
  const stanceColor = { allies: "#7bd88f", partners: "#a8d8a8", rivals: "#ff6b6b" }[d.stance] || "var(--text-dim)";
  body.innerHTML = `
    <section><h4>Current stance</h4>
      <p style="font-size:16px"><b>${esc(d.a.name)}</b> ↔ <b>${esc(d.b.name)}</b> —
      <b style="color:${stanceColor}">${esc(d.stance)}</b></p>
    </section>
    <section><h4>${esc(d.a.name)} — background</h4><p>${esc(d.a.brief) || "<i>no curated brief</i>"}</p></section>
    <section><h4>${esc(d.b.name)} — background</h4><p>${esc(d.b.brief) || "<i>no curated brief</i>"}</p></section>
    <section><h4>Shared Live Coverage <span class="cp-meta">— stories naming both</span></h4>
      ${(d.shared_coverage || []).length ? d.shared_coverage.map((s) =>
        `<button class="ap-chip dip-story" data-id="${esc(s.id)}">${esc(s.headline)}
         <span class="cp-meta">${esc(formatDateTime(s.last_updated_at))}</span></button>`).join("")
        : "<p class='cp-meta'>No tracked stories name both countries yet — this fills as coverage accumulates.</p>"}
      <p class="cp-meta">${esc(d.note)}</p>
    </section>
    <div class="feed-tools">
      <button class="ap-chip" id="dip-open-a">open ${esc(d.a.name)}</button>
      <button class="ap-chip" id="dip-open-b">open ${esc(d.b.name)}</button>
    </div>`;
  body.querySelectorAll(".dip-story").forEach((btn) =>
    btn.addEventListener("click", () => ctx.openStory && ctx.openStory(btn.dataset.id)));
  body.querySelector("#dip-open-a").addEventListener("click", () => ctx.openEntity("country", a));
  body.querySelector("#dip-open-b").addEventListener("click", () => ctx.openEntity("country", b));
}

// v8.16 — the War Mode public-sentiment strip: this conflict's live
// prediction-market odds, injected into the war feed panel by App.js.
export async function predMarketStrip(el, conflictName) {
  const d = await api.predMarkets(conflictName).catch(() => null);
  if (!d) { el.innerHTML = ""; return; }
  if (!(d.markets || []).length) {
    // v8.18 — be honest: show the "no conflict-specific markets" note instead of
    // silently blanking (which read as broken), never unrelated bets.
    el.innerHTML = d.note
      ? `<h4>Public Sentiment — Live Odds</h4><p class="cp-meta">${esc(d.note)}</p>`
      : "";
    return;
  }
  el.innerHTML = `<h4>Public Sentiment — Live Odds</h4>` + d.markets.slice(0, 4).map((m) => `
    <a class="src-row pred-row" href="${esc(m.url)}" target="_blank" rel="noopener">
      <span class="pred-odds">${m.yes_price != null ? Math.round(m.yes_price * 100) + "%" : "—"}</span>
      <span>${esc(m.title)}</span>
      <span class="cp-meta">${esc(m.source)}</span>
    </a>`).join("");
}
