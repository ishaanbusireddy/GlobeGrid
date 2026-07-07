// v4 §6 — wiki-style content templates rendered into the shared SlidePane:
// redesigned country profile (§6.1), party/person/NSA/org/alliance pages
// (§6.2), credits (§22), bookmarks directory (§21), compare view (§24),
// API-key settings (§14), and the stories directory (§8.2). Every page
// keeps the project-wide rule: nothing renders without a resolvable
// source, and AI-synthesized vs background vs tracked coverage stay
// clearly attributed by origin (§7.2).
import { api } from "../../api/client.js";
import { TIMEZONES, getTimeZone, setTimeZone, getDateFormat, setDateFormat }
  from "../../data/timefmt.js";   // v6.1.1

const esc = (s) => String(s == null ? "" : s).replace(/</g, "&lt;");

// v5 §7 — render a REAL flag image (Wikimedia SVG, cached locally), never a
// Unicode flag emoji. flagImg() is the header/large form; flagInline() the
// small inline form used in member lists. Both fall back to a neutral
// placeholder box (still not an emoji) if the image fails to load.
export function flagImg(country, cls = "wiki-flag-img") {
  const url = country && country.flag_image_url;
  const name = esc(country && country.name);
  if (!url) return `<div class="wiki-flag-empty" title="flag pending sync">▧</div>`;
  return `<img class="${cls}" src="${esc(url)}" alt="Flag of ${name}"
    loading="lazy" onerror="this.classList.add('flag-broken')">`;
}

export function flagInline(country) {
  const url = country && country.flag_image_url;
  if (!url) return "▧";
  return `<img class="flag-inline" src="${esc(url)}" alt=""
    loading="lazy" onerror="this.style.display='none'">`;
}

const STATUS_LABEL = {
  un_member: "UN member", observer_state: "UN observer state",
  de_facto: "de facto state (limited recognition)",
  disputed_territory: "disputed territory",
};

function freshness(ts) {   // §15.3 — visible 'last updated', always
  return `<p class="freshness">last updated: ${esc((ts || "").slice(0, 16).replace("T", " ")) || "seed data (never synced)"}</p>`;
}

function backgroundSection(items) {   // §7.2 — attributed by origin
  if (!items || !items.length) {
    return `<section><h4>Background</h4><p class="cp-meta">No background synthesis cached
      yet — Wikipedia summaries refresh on the weekly reference cadence.</p></section>`;
  }
  return `<section><h4>Background <span class="cp-meta">(reference sources, not tracked coverage)</span></h4>` +
    items.map((b) => `<div class="bg-box"><span class="chip">${esc(b.origin)}</span>
      <span class="bg-extract">${esc(b.extract)}</span>
      ${b.url ? `<a href="${esc(b.url)}" target="_blank" rel="noopener">source ↗</a>` : ""}
      <span class="cp-meta"> fetched ${esc((b.fetched_at || "").slice(0, 10))}</span></div>`).join("") +
    `</section>`;
}

function storyChips(stories, ctx) {
  if (!stories || !stories.length) {
    return '<span class="cp-meta">no tracked coverage yet</span>';
  }
  return stories.map((s) =>
    `<button class="ap-chip story-link" data-id="${esc(s.id)}">⌕ ${esc(s.headline).slice(0, 64)}</button>`
  ).join(" ");
}

function wireStoryChips(el, ctx) {
  el.querySelectorAll(".story-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openStory(b.dataset.id)));
}

function thinBadge(coverage) {   // §15.1 — honest thin-coverage indicator
  if (!coverage || !coverage.thin) return "";
  return `<span class="thin-badge" title="fewer than ${coverage.floor} tracked stories back
 this profile — treat synthesized fields with corresponding caution">⚠ thin coverage</span>`;
}

// ---------- §6.1 country profile (left-docked, formal header block) ----------

// v6.1/v6.3 — parliamentary seat-arc (semicircle of dots) + legend, drawn from
// the per-party seat composition. v6.3: seats fill COLUMN-FIRST (left-to-right
// by angle across all rows) so each party occupies a clean angular wedge like a
// real chamber diagram, instead of horizontal bands per row. Bicameral bodies
// (e.g. US House + Senate) render BOTH chambers. A wrong count never crashes it.
function oneChamber(cham, fallbackLabel) {
  const parties = ((cham && cham.parties) || [])
    .map((p) => Array.isArray(p) ? { name: p[0], seats: p[1], color: p[2] } : p);
  if (!parties.length) return "";
  const colors = [];
  for (const p of parties) for (let i = 0; i < p.seats; i++) colors.push(p.color);
  const n = colors.length || (cham.total || 1);
  const rows = Math.max(2, Math.min(14, Math.ceil(Math.sqrt(n / 2.5))));
  const radii = [], weights = [];
  for (let i = 0; i < rows; i++) {
    const r = 1 + (rows === 1 ? 0 : i / (rows - 1));   // inner..outer 1..2
    radii.push(r); weights.push(r);
  }
  const wsum = weights.reduce((a, b) => a + b, 0);
  const rowCounts = []; let assigned = 0;
  for (let i = 0; i < rows; i++) {
    const c = Math.round(n * weights[i] / wsum); rowCounts.push(c); assigned += c;
  }
  rowCounts[rows - 1] += n - assigned;
  const W = 320, H = 170, cx = W / 2, cy = H - 10, maxR = Math.min(cx - 10, cy - 10);
  // collect every seat with its angular fraction t (0 = far left, 1 = far
  // right), then sort left-to-right so party colours assign COLUMN-FIRST
  const seats = [];
  for (let i = 0; i < rows; i++) {
    const rr = (radii[i] / 2) * maxR, cnt = Math.max(0, rowCounts[i]);
    for (let j = 0; j < cnt; j++) {
      const t = cnt === 1 ? 0.5 : j / (cnt - 1);
      const ang = Math.PI - t * Math.PI;
      seats.push({ x: cx + rr * Math.cos(ang), y: cy - rr * Math.sin(ang), t });
    }
  }
  seats.sort((a, b) => a.t - b.t);   // left (t=0) → right (t=1): fill by column
  const dots = seats.map((s, idx) =>
    `<circle cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" r="3.3" fill="${colors[idx] || "#888"}"><title>${esc(seatOwner(parties, idx))}</title></circle>`);
  const legend = parties.map((p) =>
    `<span class="seat-legend"><i style="background:${p.color}"></i>${esc(p.name)} <b>${p.seats}</b></span>`).join(" ");
  const label = cham.chamber || fallbackLabel || "Legislature";
  return `<div class="parliament">
      <svg viewBox="0 0 ${W} ${H}" class="parliament-svg" preserveAspectRatio="xMidYMax meet">${dots.join("")}</svg>
      <div class="parliament-total">${esc(label)} · ${cham.total} seats${cham.note ? ` <span class="cp-meta">(${esc(cham.note)})</span>` : ""}</div>
      <div class="seat-legend-row">${legend}</div>
    </div>`;
}

function parliamentGraphic(leg) {
  const lower = leg && leg.seats;
  if (!lower || !((lower.parties || []).length)) return "";
  // the lower/only chamber's display name prefers the DB column
  const lowerCham = { ...lower, chamber: leg.chamber_name || lower.chamber };
  let html = oneChamber(lowerCham, "Legislature");
  // v6.3 — bicameral: render the upper house too (e.g. US Senate)
  if (lower.upper && (lower.upper.parties || []).length) {
    html += oneChamber(lower.upper, "Upper house");
  }
  return html;
}

function seatOwner(parties, idx) {
  let acc = 0;
  for (const p of parties) { acc += p.seats; if (idx < acc) return `${p.name} — ${p.seats} seats`; }
  return "";
}

export async function renderCountry(el, iso3, ctx) {
  const p = await api.country(iso3);
  const hs = (p.leadership || []).find((l) => l.role === "head_of_state");
  const hg = (p.leadership || []).find((l) => l.role === "head_of_government");
  // v6.1 — feature the PARAMOUNT leader the server identified (Xi for China,
  // Putin for Russia), not blindly the prime minister. Fall back sensibly.
  const paramount = (p.leadership || []).find((l) => l.role === p.paramount_role)
    || hs || hg;
  const leader = paramount;
  const leaderTitle = p.paramount_title
    || (leader ? leader.role.replace(/_/g, " ") : "");
  const rulingParty = (leader && leader.party) || "—";
  // safe portrait: a wrong/stale URL swaps to the 👤 placeholder rather than
  // showing a broken-image icon, so vendored + synced photos both degrade well
  const photo = (leader && leader.image_url)
    ? `<img class="leader-photo" src="${esc(leader.image_url)}" alt="${esc(leader.name)}"
        onerror="this.outerHTML='<div class=\\'leader-photo leader-photo-empty\\'>👤</div>'">`
    : `<div class="leader-photo leader-photo-empty" data-leader="${leader ? esc(leader.name) : ""}" title="fetching portrait…">👤</div>`;

  const leadership = (p.leadership || []).map((l) => {
    const src = l.last_refreshed_at ? `synced ${l.last_refreshed_at.slice(0, 10)}` : "seed data";
    const isLead = l.role === p.paramount_role;   // v6.1 — mark who actually leads
    return `<div class="src-row"><span class="leaning">${esc(l.role.replace(/_/g, " "))}</span>
      <b>${esc(l.name)}</b>${isLead ? ' <span class="chip" style="font-size:10px">★ leads</span>' : ""}${l.party ? " · " + esc(l.party) : ""}
      <span class="cp-meta" style="margin-left:auto">${src}</span></div>`;
  }).join("") || '<p class="cp-meta">no leadership data yet (fills in from Wikidata)</p>';

  const memberships = (p.memberships || []).map((m) =>
    `<span class="chip">${esc(m.name)}</span>`).join(" ") ||
    '<span class="cp-meta">none registered</span>';

  const parties = (p.parties || []).map((pt) =>
    `<button class="ap-chip party-link" data-id="${esc(pt.id)}">${esc(pt.name)}</button>`
  ).join(" ") || '<span class="cp-meta">no registered parties</span>';

  const agenda = p.agenda ? `
    <div class="narrative-box"><b>Geopolitical agenda</b>${esc(p.agenda.geopolitical_agenda) || "—"}</div>
    <div class="narrative-box"><b>Economic agenda</b>${esc(p.agenda.economic_agenda) || "—"}</div>
    <div class="narrative-box" style="grid-column:1/-1"><b>Stances</b>${esc(p.agenda.stance_summary) || "—"}</div>`
    : '<div class="narrative-box" style="grid-column:1/-1">No AI synthesis yet — agendas generate'
      + " from this country's tagged coverage once stories accumulate"
      + ((window.__gg && window.__gg.state && window.__gg.state.clientConfig
          && window.__gg.state.clientConfig.ai_available)
          ? "." : " (add a free Groq key in Settings to enable AI synthesis).")
      + "</div>";

  const relations = (p.relations || []).map((r) => {
    const other = r.country_a_id === p.id
      ? { id: r.country_b_id, name: r.country_b_name }
      : { id: r.country_a_id, name: r.country_a_name };
    return `<div class="src-row"><span class="rel-badge rel-${esc(r.status)}">${esc(r.status)}</span>
      <button class="ap-chip country-link" data-id="${esc(other.id)}">${esc(other.name)}</button>
      <button class="ap-chip compare-link" data-id="${esc(other.id)}" title="side-by-side compare">⇔</button>
      <span class="cp-meta">${esc((r.synthesis || "").slice(0, 90))}</span></div>`;
  }).join("") || '<p class="cp-meta">no synthesized relations yet</p>';

  const disputes = (p.border_disputes || []).map((d) =>
    `<div class="src-row"><span class="chip dispute-${esc(d.status)}">${esc(d.status)}</span>
     <b>${esc(d.territory_name)}</b>
     <span class="cp-meta">${esc(d.claimant_a_name)}${d.claimant_b_name ? " / " + esc(d.claimant_b_name) : ""}</span></div>`
  ).join("") || '<p class="cp-meta">no registered border disputes</p>';

  const sanctions = (p.sanctions_targeting || []).map((s) =>
    `<div class="src-row">⛔ <span>${esc(s.reason)}</span>
     <span class="cp-meta" style="margin-left:auto">${esc(s.imposed_at || "")}</span></div>`
  ).join("") || '<p class="cp-meta">no active sanctions tracked against this country</p>';

  const treaties = (p.treaties || []).map((t) =>
    `<div class="src-row"><span class="chip">${esc(t.treaty_type.replace(/_/g, " "))}</span>
     <span>${esc(t.name)}</span>
     <span class="cp-meta" style="margin-left:auto">${t.ratified ? "ratified" : "signed"} · ${esc(t.status)}</span></div>`
  ).join("") || '<p class="cp-meta">none registered</p>';

  const persons = (p.notable_persons || []).map((n_) =>
    `<div class="src-row"><b>${esc(n_.name)}</b><span class="cp-meta">${esc(n_.role_title)}</span></div>`
  ).join("") || '<p class="cp-meta">none registered</p>';

  const elections = (p.elections || []).map((e) =>
    `<div class="src-row"><span class="chip">${esc(e.election_type)}</span>
     <span>${esc(e.scheduled_date || "?")}</span>
     <span class="conf conf-${e.status === "upcoming" ? "medium" : "low"}">${esc(e.status)}</span>
     ${e.result_summary ? `<span class="cp-meta">${esc(e.result_summary)}</span>` : ""}</div>`
  ).join("") || '<p class="cp-meta">no tracked elections</p>';

  const conflicts = (p.conflicts || []).map((c) =>
    `<button class="ap-chip conflict-link" data-id="${esc(c.id)}">${esc(c.name)} (${esc(c.role)})</button>`
  ).join(" ") || '<span class="cp-meta">not a registered conflict party</span>';

  const trade = p.trade && p.trade.gdp_usd
    ? `GDP $${(p.trade.gdp_usd / 1e9).toFixed(0)}B (World Bank, ${esc(p.trade.as_of_date)})`
    : "GDP pending (monthly World Bank sync)";
  const pop = p.population ? `pop. ${(p.population / 1e6).toFixed(1)}M` : "";

  // v6 §15 — profile depth: authoritative stats (World Bank / UNDP / Pew)
  const langs = Array.isArray(p.languages) ? p.languages.join(", ") : "";
  const fmtB = (v) => v >= 1e12 ? "$" + (v / 1e12).toFixed(2) + "T"
    : v >= 1e9 ? "$" + (v / 1e9).toFixed(1) + "B" : "$" + (v / 1e6).toFixed(0) + "M";
  const statCells = [
    p.population != null && ["Population", (p.population / 1e6).toFixed(2) + "M"],
    p.gdp_usd != null && ["GDP (nominal)", fmtB(p.gdp_usd)],
    p.gdp_per_capita_usd != null && ["GDP per capita",
      "$" + Math.round(p.gdp_per_capita_usd).toLocaleString()],
    p.hdi != null && ["HDI", Number(p.hdi).toFixed(3)],
    p.area_km2 != null && ["Area", Math.round(p.area_km2).toLocaleString() + " km²"],
    langs && ["Languages", langs],
    p.dominant_religion && ["Dominant religion", p.dominant_religion],
    p.currency_code && ["Currency",   // v6.1 — every country's currency
      `${p.currency_name} (${p.currency_code}${p.currency_symbol ? " " + p.currency_symbol : ""})`],
  ].filter(Boolean).map(([k, v]) =>
    `<div class="stat-cell"><span class="stat-k">${esc(k)}</span><span class="stat-v">${esc(String(v))}</span></div>`).join("");
  // v6 §14 — territory <-> sovereign linkage, both directions
  const sovereignLink = p.sovereign
    ? `<p class="cp-meta">Territory of <button class="ap-chip country-link" data-id="${esc(p.sovereign.id)}">${flagInline(p.sovereign)} ${esc(p.sovereign.name)}</button></p>` : "";
  const territories = (p.territories || []).length
    ? `<section><h4>Territories</h4>${p.territories.map((t) =>
        `<button class="ap-chip country-link" data-id="${esc(t.id)}">${flagInline(t)} ${esc(t.name)}</button>`).join(" ")}</section>` : "";
  const pastConflicts = (p.past_conflicts || []).map((c) =>
    `<button class="ap-chip conflict-link" data-id="${esc(c.id)}">${esc(c.name)} (resolved)</button>`).join(" ");

  el.innerHTML = `
    <div class="wiki-header">
      <div class="wiki-flag">${flagImg(p)}</div>
      ${photo}
      <div class="wiki-head-meta">
        <h1>${esc(p.name)} <span class="cp-meta">${esc(p.id)}</span> ${thinBadge(p.coverage)}</h1>
        ${p.official_name ? `<p class="official-name">${esc(p.official_name)}</p>` : ""}
        <p class="wiki-status status-${esc(p.status)}">${STATUS_LABEL[p.status] || esc(p.status)}</p>
        ${sovereignLink}
        <p class="cp-meta">${leader ? "<b>" + esc(leader.name) + "</b>" + (leaderTitle ? " · " + esc(leaderTitle) : "") + " · " : ""}ruling: ${esc(rulingParty)}</p>
        <p class="cp-meta">${esc(p.capital || "—")} · ${esc(p.region || "—")}${p.government_type ? " · " + esc(p.government_type) : ""}</p>
        <p class="cp-meta">${trade}${pop ? " · " + pop : ""}</p>
      </div>
    </div>
    ${statCells ? `<section><h4>Key statistics</h4><div class="stat-grid">${statCells}</div></section>` : ""}
    ${territories}
    ${freshness(p.last_updated_at)}
    ${backgroundSection(p.background)}
    <section><h4>Leadership</h4>${leadership}</section>
    <section><h4>Member of</h4>${memberships}</section>
    ${(p.legislature && p.legislature.seats)
      ? `<section><h4>Legislature</h4>${parliamentGraphic(p.legislature)}</section>`
      : (p.legislature && p.legislature.composition_summary
          ? `<section><h4>Legislature</h4><p>${esc(p.legislature.chamber_name || "")}</p><p class="cp-meta">${esc(p.legislature.composition_summary)}</p></section>`
          : "")}
    <section><h4>Political parties</h4>${parties}</section>
    <section><h4>Agendas & stances <span class="cp-meta">(AI-synthesized, source-linked)</span></h4>
      <div class="narrative-grid">${agenda}</div>
      ${p.agenda && p.agenda.source_story_ids
        ? `<p class="cp-meta">synthesized from ${p.agenda.source_story_ids.length} tracked stories · ${esc(p.agenda.generated_at || "")}</p>` : ""}
    </section>
    <section><h4>Bilateral relations</h4>${relations}</section>
    <section><h4>Border disputes</h4>${disputes}</section>
    <section><h4>Conflicts</h4>${conflicts}</section>
    ${pastConflicts ? `<section><h4>Past conflicts</h4>${pastConflicts}</section>` : ""}
    <section><h4>Sanctions targeting</h4>${sanctions}</section>
    <section><h4>Treaties</h4>${treaties}</section>
    <section><h4>Notable persons</h4>${persons}</section>
    <section><h4>Elections</h4>${elections}</section>
    <section><h4>Recent tracked coverage ${thinBadge(p.coverage)}</h4>${storyChips(p.recent_stories)}</section>`;

  wireStoryChips(el, ctx);
  // v6.2 — if the featured leader has no photo yet, fetch it on demand from
  // Wikipedia (reliable lead image) and swap it in, so e.g. Xi Jinping shows
  // next to the China flag immediately instead of waiting on a weekly sync.
  const ph = el.querySelector(".leader-photo-empty[data-leader]");
  if (ph && ph.dataset.leader) {
    api.leaderPortrait(ph.dataset.leader).then((r) => {
      if (r && r.image_url && ph.isConnected) {
        const img = new Image();
        img.className = "leader-photo";
        img.alt = ph.dataset.leader;
        img.src = r.image_url;
        img.onerror = () => { /* keep placeholder */ };
        img.onload = () => ph.replaceWith(img);
      }
    }).catch(() => {});
  }
  el.querySelectorAll(".party-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("party", b.dataset.id)));
  el.querySelectorAll(".country-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.id)));
  el.querySelectorAll(".conflict-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openConflict(b.dataset.id)));
  el.querySelectorAll(".compare-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openCompare(iso3, b.dataset.id)));
}

// ---------- §6.2 other wiki pages ----------

export async function renderParty(el, id, ctx) {
  const p = await api.party(id);
  const leaders = (p.leaders || []).map((l) =>
    `<div class="src-row"><b>${esc(l.name)}</b>
     <span class="cp-meta">${esc(l.role.replace(/_/g, " "))} · since ${esc(l.since_date || "?")}</span></div>`
  ).join("") || '<p class="cp-meta">no tracked officeholders</p>';
  el.innerHTML = `
    <div class="wiki-header"><div class="wiki-flag">🏛</div>
      <div class="wiki-head-meta"><h1>${esc(p.name)}</h1>
        <p class="cp-meta">${esc(p.country_name || "")} · founded ${esc(p.founded_date || "?")}</p>
        <p class="cp-meta">ideology: ${esc((p.ideology_tags || "").replace(/;/g, " · "))}</p>
      </div></div>
    ${freshness(p.last_updated_at)}
    ${backgroundSection(p.background)}
    ${p.founding_history ? `<section><h4>Founding history <span class="cp-meta">(AI-synthesized, source-linked)</span></h4><p>${esc(p.founding_history)}</p></section>` : ""}
    ${partyElectoralSection(p.electoral_history)}
    ${partyCoalitionSection(p.coalition_partners)}
    <section><h4>Officeholders in tracked leadership</h4>${leaders}</section>
    <section><h4>Recent tracked coverage</h4>${storyChips(p.recent_stories)}</section>`;
  wireStoryChips(el, ctx);
}

// v6 §5 — leader & party profile depth helpers
function partyElectoralSection(raw) {
  let rows = [];
  try { rows = JSON.parse(raw || "[]"); } catch { /* seed-format only */ }
  if (!rows.length) return "";
  return `<section><h4>Electoral history</h4>${rows.map((r) =>
    `<div class="src-row"><span class="chip">${esc(r.election || "")}</span>
     <span>${esc(r.result || "")}</span></div>`).join("")}</section>`;
}

function partyCoalitionSection(raw) {
  let rows = [];
  try { rows = JSON.parse(raw || "[]"); } catch { /* seed-format only */ }
  if (!rows.length) return "";
  return `<section><h4>Coalition partners</h4><p class="cp-meta">${rows.map(esc).join(" · ")}</p></section>`;
}

export async function renderPerson(el, id, ctx) {
  const p = await api.person(id);
  const aff = [p.country_name, p.org_name, p.nsa_name].filter(Boolean).join(" · ");
  // v6 §5 — Wikimedia-sourced portrait when available, placeholder otherwise
  const portrait = p.portrait_image_url
    ? `<img class="leader-photo" src="${esc(p.portrait_image_url)}" alt="${esc(p.name)}"
         onerror="this.outerHTML='<div class=\'wiki-flag\'>👤</div>'">`
    : `<div class="wiki-flag">👤</div>`;
  el.innerHTML = `
    <div class="wiki-header">${portrait}
      <div class="wiki-head-meta"><h1>${esc(p.name)}</h1>
        <p class="cp-meta">${esc(p.role_title || "")}${aff ? " · " + esc(aff) : ""}</p>
      </div></div>
    ${backgroundSection(p.background)}
    <section><h4>Bio</h4><p>${esc(p.bio_summary || "—")}</p></section>
    ${partyElectoralSection(p.electoral_history)}
    <section><h4>Recent tracked coverage</h4>${storyChips(p.recent_stories)}</section>`;
  wireStoryChips(el, ctx);
}

export async function renderActor(el, id, ctx) {
  const data = await api.actors();
  const a = (data.actors || []).find((x) => x.id === id);
  if (!a) { el.innerHTML = "<p>actor not registered</p>"; return; }
  const conflicts = (a.conflicts || []).map((c) =>
    `<button class="ap-chip conflict-link" data-id="${esc(c.id)}">${esc(c.name)} (${esc(c.role)})</button>`
  ).join(" ") || '<span class="cp-meta">none registered</span>';
  const bg = await api.background("non_state_actor", id).catch(() => ({ background: [] }));
  el.innerHTML = `
    <div class="wiki-header"><div class="wiki-flag">◈</div>
      <div class="wiki-head-meta"><h1>${esc(a.name)}</h1>
        <p class="cp-meta">${esc(a.actor_type)} · ${esc(a.primary_region || "")}
          · active since ${esc(a.active_since || "?")}</p>
        ${a.affiliated_state_name ? `<p class="cp-meta">reported backing: ${esc(a.affiliated_state_name)}</p>` : ""}
      </div></div>
    ${freshness(a.last_updated_at)}
    ${backgroundSection(bg.background)}
    <section><h4>Description <span class="cp-meta">(tracked synthesis)</span></h4>
      <p>${esc(a.description_synthesis || "—")}</p></section>
    <section><h4>Party to conflicts</h4>${conflicts}</section>`;
  el.querySelectorAll(".conflict-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openConflict(b.dataset.id)));
}

export async function renderOrg(el, id, ctx) {
  const data = await api.orgs();
  const o = (data.organizations || []).find((x) => x.id === id);
  if (!o) { el.innerHTML = "<p>organization not registered</p>"; return; }
  const bg = await api.background("org", id).catch(() => ({ background: [] }));
  el.innerHTML = `
    <div class="wiki-header"><div class="wiki-flag">🏢</div>
      <div class="wiki-head-meta"><h1>${esc(o.name)}</h1>
        <p class="cp-meta">${esc(o.org_type)} · HQ ${esc(o.hq_location || "?")} · founded ${esc(o.founded_date || "?")}</p>
      </div></div>
    ${freshness(o.last_updated_at)}
    ${backgroundSection(bg.background)}
    <section><h4>Mandate</h4><p>${esc(o.mandate_summary || "—")}</p></section>
    ${o.posture_synthesis ? `<section><h4>Current posture <span class="cp-meta">(AI-synthesized)</span></h4>
      <p>${esc(o.posture_synthesis)}</p></section>` : ""}`;
}

export async function renderAlliance(el, id, ctx) {
  const data = await api.alliances();
  const a = (data.alliances || []).find((x) => x.id === id);
  if (!a) { el.innerHTML = "<p>alliance not registered</p>"; return; }
  const countries = await api.countries().catch(() => ({ countries: [] }));
  const byId = new Map((countries.countries || []).map((c) => [c.id, c]));
  const members = (a.members || []).map((iso3) => {
    const c = byId.get(iso3);
    return `<button class="ap-chip country-link" data-id="${esc(iso3)}">
      ${c ? flagInline(c) + " " + esc(c.name) : esc(iso3)}</button>`;
  }).join(" ");
  el.innerHTML = `
    <div class="wiki-header"><div class="wiki-flag">⬡</div>
      <div class="wiki-head-meta"><h1>${esc(a.name)}</h1>
        <p class="cp-meta">${esc(a.type)} alliance · founded ${esc(a.founded_date || "?")}
          · ${(a.members || []).length} members</p>
      </div></div>
    ${freshness(a.last_updated_at)}
    <section><h4>About</h4><p>${esc(a.description || "—")}</p></section>
    <section><h4>Members <span class="cp-meta">(complete roster — Wikidata-synced)</span></h4>
      <div class="member-grid">${members}</div></section>`;
  el.querySelectorAll(".country-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.id)));
}

// ---------- §24 compare view ----------

export async function renderCompare(el, aId, bId, ctx) {
  const [a, b, rels] = await Promise.all([
    api.country(aId), api.country(bId),
    api.relations().catch(() => ({ relations: [] }))]);
  const rel = (rels.relations || []).find((r) =>
    (r.country_a_id === aId && r.country_b_id === bId) ||
    (r.country_a_id === bId && r.country_b_id === aId));
  const col = (p) => `
    <div class="cmp-col">
      <div class="wiki-header"><div class="wiki-flag">${flagImg(p)}</div>
        <div class="wiki-head-meta"><h2>${esc(p.name)}</h2>
          <p class="cp-meta">${STATUS_LABEL[p.status] || ""} · ${esc(p.region || "")}</p></div></div>
      <section><h4>Leadership</h4>${(p.leadership || []).map((l) =>
        `<div class="src-row"><span class="leaning">${esc(l.role.replace(/_/g, " "))}</span><b>${esc(l.name)}</b></div>`).join("") || "—"}</section>
      <section><h4>Agenda</h4><p class="cp-meta">${esc((p.agenda && p.agenda.geopolitical_agenda) || "no synthesis yet")}</p></section>
      <section><h4>Blocs</h4>${(p.memberships || []).map((m) => `<span class="chip">${esc(m.name)}</span>`).join(" ") || "—"}</section>
      <section><h4>Economy</h4><p class="cp-meta">${p.trade && p.trade.gdp_usd ? "GDP $" + (p.trade.gdp_usd / 1e9).toFixed(0) + "B" : "pending"}
        ${p.population ? " · pop. " + (p.population / 1e6).toFixed(1) + "M" : ""}</p></section>
      <section><h4>Coverage</h4>${storyChips(p.recent_stories)}</section>
    </div>`;
  el.innerHTML = `
    <h1 class="cmp-title">${esc(a.name)} ⇔ ${esc(b.name)}</h1>
    ${rel ? `<div class="cmp-relation rel-badge rel-${esc(rel.status)}">bilateral status: ${esc(rel.status)}
       ${rel.synthesis ? `<span class="cmp-rel-text">${esc(rel.synthesis)}</span>` : ""}</div>`
      : '<div class="cmp-relation cp-meta">no synthesized bilateral relation tracked yet</div>'}
    <div class="cmp-grid">${col(a)}${col(b)}</div>`;
  wireStoryChips(el, ctx);
}

// ---------- §22 sources & credits ----------

export async function renderCredits(el, ctx) {
  const data = await api.credits();
  const groups = Object.entries(data.source_groups || {}).map(([type, g]) => `
    <section><h4>${esc(g.provider)} <span class="cp-meta">(${esc(type)})</span></h4>
      <p class="cp-meta">${esc(g.attribution || "")}</p>
      ${g.sources.map((s) => `<div class="src-row"><b>${esc(s.name)}</b>
        ${s.kind === "official" ? '<span class="chip chip-official">official</span>' : ""}
        <a style="margin-left:auto" href="${esc(s.url)}" target="_blank" rel="noopener">↗</a></div>`).join("")}
    </section>`).join("");
  const providers = (data.data_providers || []).map((p) =>
    `<div class="src-row"><b>${esc(p.name)}</b><span class="cp-meta">${esc(p.attribution)}</span>
     <a style="margin-left:auto" href="${esc(p.url)}" target="_blank" rel="noopener">↗</a></div>`).join("");
  el.innerHTML = `
    <h1>Sources & credits</h1>
    <p class="cp-meta">Attribution has been a hard requirement since v1 §6.8 — every story links
      its sources; this page credits the providers themselves.</p>
    <section><h4>Data providers</h4>${providers}</section>
    ${groups}
    <p class="cp-meta">${esc(data.license || "")}</p>`;
}

// ---------- §21 bookmarks directory ----------

const BOOKMARK_OPEN = {
  story: (ctx, id) => ctx.openStory(id),
  country: (ctx, id) => ctx.openEntity("country", id),
  conflict: (ctx, id) => ctx.openConflict(id),
  non_state_actor: (ctx, id) => ctx.openEntity("non_state_actor", id),
  alliance: (ctx, id) => ctx.openEntity("alliance", id),
  notable_person: (ctx, id) => ctx.openEntity("person", id),
  party: (ctx, id) => ctx.openEntity("party", id),
  org: (ctx, id) => ctx.openEntity("org", id),
};

export async function renderBookmarks(el, ctx) {
  const data = await api.bookmarks();
  el.innerHTML = `<h1>Bookmarks</h1>
    <p class="cp-meta">Your reading list — distinct from watchlists, which monitor ongoing coverage.</p>
    <div class="bm-list"></div>`;
  const list = el.querySelector(".bm-list");
  for (const b of data.bookmarks || []) {
    const row = document.createElement("div");
    row.className = "src-row bm-row";
    row.innerHTML = `<span class="chip">${esc(b.target_type.replace(/_/g, " "))}</span>
      <button class="ap-chip bm-open"></button>
      <span class="cp-meta" style="margin-left:auto">${esc((b.bookmarked_at || "").slice(0, 10))}</span>
      <button class="cp-del">✕</button>`;
    row.querySelector(".bm-open").textContent = b.label || b.target_id;
    row.querySelector(".bm-open").addEventListener("click", () =>
      (BOOKMARK_OPEN[b.target_type] || (() => {}))(ctx, b.target_id));
    row.querySelector(".cp-del").addEventListener("click", async () => {
      await api.bookmarkToggle(b.target_type, b.target_id);
      row.remove();
    });
    list.appendChild(row);
  }
  if (!(data.bookmarks || []).length) {
    list.innerHTML = '<p class="cp-meta">Nothing saved yet — use the ☆ in the pane header'
      + " on any story, country, or wiki page.</p>";
  }
}

// ---------- §8.2 stories directory ----------

const TYPE_META = {
  acute_event: ["⚡", "Acute events", "tight clusters of recent correlated events"],
  ongoing_conflict: ["⚔", "Ongoing conflicts", "long-running, continuously updated"],
  alliance_development: ["⬡", "Alliance developments", "bloc membership & posture over time"],
  recurring_pattern: ["🔁", "Recurring patterns", "history rhyming — lineage & shared root causes"],
  diplomatic_push: ["🕊", "Diplomatic pushes", "sustained national agendas"],
  economic_push: ["📈", "Economic pushes", "trade, sanctions & economic agendas"],
};

// v5 §20 — region summary page: every country in the region + aggregated
// current activity, rendered in the same sliding pane
export async function renderRegion(el, region, ctx) {
  const d = await api.regionSummary(region);
  const countries = (d.countries || []).map((c) =>
    `<button class="ap-chip country-link" data-id="${esc(c.id)}">
      ${flagInline(c)} ${esc(c.name)}</button>`).join(" ");
  const conflicts = (d.conflicts || []).map((c) =>
    `<button class="ap-chip conflict-link" data-id="${esc(c.id)}">⚔ ${esc(c.name)} (${esc(c.status)})</button>`
  ).join(" ") || '<span class="cp-meta">no tracked conflicts with a party in this region</span>';
  el.innerHTML = `
    <h1>${esc(d.region)} <span class="cp-meta">region</span></h1>
    <p class="cp-meta">${(d.countries || []).length} countries · aggregated current activity across the region.</p>
    <section><h4>Countries</h4><div class="member-grid">${countries}</div></section>
    <section><h4>Active conflicts in the region</h4>${conflicts}</section>
    <section><h4>Recent tracked coverage</h4>${storyChips(d.recent_stories)}</section>`;
  wireStoryChips(el, ctx);
  el.querySelectorAll(".country-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.id)));
  el.querySelectorAll(".conflict-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openConflict(b.dataset.id)));
}

// ---------- v6 §8 — War Mode wiki-infobox overview ----------

export function renderWarMode(el, data, ctx) {
  const c = data.conflict;
  // v6.1 — real side names (Russia / Ukraine), not "Side A/B"
  const sn = data.side_names || {};
  const sideName = { a: sn.a || "Side A", b: sn.b || "Side B",
                     none: "Unaligned / mediators" };
  const sideClass = { a: "war-side-a", b: "war-side-b", none: "war-side-none" };
  const bySide = { a: [], b: [], none: [] };
  for (const pt of (data.parties || [])) {
    bySide[pt.side || "none"].push(pt);
  }
  const partyChip = (pt) => pt.country_id
    ? `<button class="ap-chip country-link" data-id="${esc(pt.country_id)}">${flagInline({ id: pt.country_id, name: pt.country_name, flag_image_url: pt.flag_image_url })} ${esc(pt.country_name)}</button>`
    : `<button class="ap-chip actor-link" data-id="${esc(pt.actor_id)}">◈ ${esc(pt.actor_name)}</button>`;
  // v6.1 — within each side, list BELLIGERENTS first, then BACKERS/supporters
  const sideBlock = (k) => {
    const belligs = bySide[k].filter((p) => p.role === "belligerent");
    const backers = bySide[k].filter((p) => p.role === "backer");
    const others = bySide[k].filter((p) => p.role !== "belligerent" && p.role !== "backer");
    let inner = "";
    if (belligs.length) inner += `<div class="war-line"><span class="war-role">Belligerents</span> ${belligs.map(partyChip).join(" ")}</div>`;
    if (backers.length) inner += `<div class="war-line"><span class="war-role">Backers / supporters</span> ${backers.map(partyChip).join(" ")}</div>`;
    if (others.length) inner += `<div class="war-line"><span class="war-role">Other</span> ${others.map(partyChip).join(" ")}</div>`;
    return `<div class="war-side ${sideClass[k]}"><h4>${esc(sideName[k])}</h4>${inner}</div>`;
  };
  const sidesHtml = ["a", "b", "none"].filter((k) => bySide[k].length).map(sideBlock).join("");
  const subf = (data.subfactions || []).map((sf) =>
    `<div class="src-row"><span class="chip ${sideClass[sf.side || "none"]}">${esc(sf.side ? "side " + sf.side : "unaligned")}</span>
       <span>${esc(sf.name)}</span></div>`).join("")
    || '<p class="cp-meta">no sub-national factions registered</p>';
  const days = c.started_at
    ? Math.floor((Date.now() - new Date(c.started_at).getTime()) / 86400000) : null;
  el.innerHTML = `
    <div class="war-infobox">
      <h1>⚔ ${esc(c.name)}</h1>
      <div class="stat-grid">
        <div class="stat-cell"><span class="stat-k">Status</span><span class="stat-v">${esc(c.status)}</span></div>
        <div class="stat-cell"><span class="stat-k">Began</span><span class="stat-v">${esc(c.started_at || "?")}</span></div>
        ${days != null ? `<div class="stat-cell"><span class="stat-k">Duration</span><span class="stat-v">${days.toLocaleString()} days</span></div>` : ""}
        <div class="stat-cell"><span class="stat-k">Region</span><span class="stat-v">${esc(c.region || "—")}</span></div>
        <div class="stat-cell"><span class="stat-k">Tracked stories</span><span class="stat-v">${data.story_count || 0}</span></div>
      </div>
      <section><h4>Overview</h4><p>${esc(c.summary || "—")}</p></section>
      <section><h4>Belligerents</h4>${sidesHtml}</section>
      <section><h4>Sub-national factions <span class="cp-meta">(War Mode only — never on the global map)</span></h4>${subf}</section>
      <section class="oob-section"><h4>Order of battle & tactical history
        <span class="cp-meta">(AI-generated)</span></h4>
        <div class="oob-body"><button class="oob-load">↻ generate order of battle</button></div>
      </section>
      <section><h4>Latest tracked coverage</h4>${storyChips(data.recent_stories)}</section>
      <p class="cp-meta">The right-panel feed is restricted to this conflict —
        use its Military / Civilian / Diplomatic / Economic tabs to sub-filter.</p>
    </div>`;
  // v6.1.1 — lazy-load the AI order of battle (kept off the fast war-mode entry)
  const oobBody = el.querySelector(".oob-body");
  const loadOob = async () => {
    oobBody.innerHTML = '<p class="cp-meta">generating order of battle & tactics…</p>';
    try {
      const r = await api.orderOfBattle(data.conflict.id);
      const o = r.order_of_battle;
      if (!o) { oobBody.innerHTML = `<p class="cp-meta">${esc(r.note || "unavailable")}</p>`; return; }
      oobBody.innerHTML = `
        <div class="narrative-box"><b>Order of battle</b>${esc(o.order_of_battle || "—")}</div>
        <div class="narrative-box"><b>Major offensives & phases</b><ul>${
          (o.offensives || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
        <div class="narrative-box"><b>Evolution of tactics</b>${esc(o.tactics_evolution || "—")}</div>
        <div class="narrative-box" style="grid-column:1/-1"><b>Global ramifications</b>${esc(o.global_ramifications || "—")}</div>`;
      oobBody.classList.add("narrative-grid");
    } catch (e) {
      oobBody.innerHTML = `<p class="cp-meta">order of battle unavailable: ${esc(e.message)}</p>`;
    }
  };
  el.querySelector(".oob-load").addEventListener("click", loadOob);
  wireStoryChips(el, ctx);
  el.querySelectorAll(".country-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.id)));
  el.querySelectorAll(".actor-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("non_state_actor", b.dataset.id)));
}

// ---------- v6.1 — United Nations panel ----------

// hemicycle vote graphic coloured yes(green)/no(red)/abstain(grey), sized to
// the recorded tally — a real parliamentary-style diagram of the vote
function voteArc(tally) {
  const order = [["yes", "#3fb950"], ["abstain", "#8b949e"], ["no", "#e5534b"]];
  const dots = [];
  for (const [k, c] of order) for (let i = 0; i < (tally[k] || 0); i++) dots.push(c);
  const n = dots.length || 1;
  const rows = Math.max(2, Math.min(16, Math.ceil(Math.sqrt(n / 2.2))));
  const radii = [], weights = [];
  for (let i = 0; i < rows; i++) { const r = 1 + i / (rows - 1); radii.push(r); weights.push(r); }
  const wsum = weights.reduce((a, b) => a + b, 0);
  const rc = []; let asg = 0;
  for (let i = 0; i < rows; i++) { const c = Math.round(n * weights[i] / wsum); rc.push(c); asg += c; }
  rc[rows - 1] += n - asg;
  const W = 340, H = 180, cx = W / 2, cy = H - 10, maxR = Math.min(cx - 8, cy - 8);
  const c = []; let idx = 0;
  for (let i = 0; i < rows; i++) {
    const rr = (radii[i] / 2) * maxR, cnt = Math.max(0, rc[i]);
    for (let j = 0; j < cnt; j++) {
      const t = cnt === 1 ? 0.5 : j / (cnt - 1), ang = Math.PI - t * Math.PI;
      c.push(`<circle cx="${(cx + rr * Math.cos(ang)).toFixed(1)}" cy="${(cy - rr * Math.sin(ang)).toFixed(1)}" r="3.1" fill="${dots[idx] || "#888"}"/>`);
      idx++;
    }
  }
  return `<svg viewBox="0 0 ${W} ${H}" class="parliament-svg" preserveAspectRatio="xMidYMax meet">${c.join("")}</svg>`;
}

const VOTE_CLASS = { yes: "vote-yes", no: "vote-no", abstain: "vote-abstain" };

export async function renderUN(el, ctx) {
  const d = await api.un();
  const sc = d.security_council || {};
  const memberChip = (m) => `<button class="ap-chip country-link" data-id="${esc(m.id)}">${flagInline(m)} ${esc(m.name)}${m.term ? ` <i class="cp-meta">${esc(m.term)}</i>` : ""}</button>`;
  const resolutions = (d.resolutions || []).map((r) => {
    const nv = (r.notable_votes || []).map((v) =>
      `<button class="ap-chip country-link ${VOTE_CLASS[v.vote] || ""}" data-id="${esc(v.id)}" title="${esc(v.vote)}">${flagInline(v)} ${esc(v.name)} · ${esc(v.vote)}</button>`).join(" ");
    return `<div class="un-res">
        <div class="un-res-head"><b>${esc(r.title)}</b> <span class="cp-meta">${esc(r.id)} · ${esc(r.body)} · ${esc(r.date)}</span></div>
        <p>${esc(r.summary)}</p>
        ${voteArc(r.tally)}
        <div class="vote-tally">
          <span class="vote-yes">✔ ${r.tally.yes} for</span>
          <span class="vote-no">✘ ${r.tally.no} against</span>
          <span class="vote-abstain">◦ ${r.tally.abstain} abstain</span>
          <span class="cp-meta">— ${esc(r.result)}</span>
        </div>
        <div class="un-notable"><span class="cp-meta">Notable positions:</span> ${nv}</div>
      </div>`;
  }).join("");
  el.innerHTML = `
    <div class="wiki-header"><div class="wiki-head-meta">
      <h1>🇺🇳 United Nations</h1>
      <p class="cp-meta">Security Council, recent resolutions and how members voted.</p>
    </div></div>
    <section><h4>Security Council — Permanent members (P5, veto power)</h4>
      ${sc.permanent ? sc.permanent.map(memberChip).join(" ") : ""}</section>
    <section><h4>Security Council — Elected members</h4>
      ${sc.elected ? sc.elected.map(memberChip).join(" ") : ""}</section>
    <section><h4>Other principal organs</h4>
      ${(d.other_councils || []).map((c) => `<div class="src-row"><b>${esc(c.name)}</b> <span class="cp-meta">${esc(c.note)}</span></div>`).join("")}</section>
    <section><h4>Notable resolutions & recorded votes</h4>${resolutions}</section>`;
  el.querySelectorAll(".country-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.id)));
}

// ---------- v6 §27 — story thread page ----------

export async function renderThread(el, id, ctx) {
  const t = await api.threadDetail(id);
  el.innerHTML = `<h1>${esc(t.name)}</h1>
    <p class="cp-meta">macro-trend thread · ${(t.members || []).length} tracked stories
      · since ${esc((t.first_seen_at || "").slice(0, 10))}</p>
    ${t.description ? `<section><h4>Overview <span class="cp-meta">(AI-synthesized)</span></h4><p>${esc(t.description)}</p></section>` : ""}
    <section><h4>Stories in this thread</h4><div class="thread-list"></div></section>`;
  const list = el.querySelector(".thread-list");
  for (const m of (t.members || [])) {
    const row = document.createElement("div");
    row.className = "story-card";
    row.style.cursor = "pointer";
    row.innerHTML = `<div class="card-meta">
        <span class="chip">${esc((m.story_type || "acute_event").replace(/_/g, " "))}</span>
        <span class="conf conf-${esc(m.confidence || "low")}">${esc(m.confidence || "low")}</span>
        <span class="cp-meta" style="margin-left:auto">${esc((m.last_updated_at || "").slice(0, 10))}</span>
      </div><h3></h3>`;
    row.querySelector("h3").textContent = m.headline || "(untitled)";
    row.addEventListener("click", () => ctx.openStory(m.id));
    list.appendChild(row);
  }
}

export async function renderStoriesDirectory(el, ctx, activeType) {
  const data = await api.storiesDirectory(activeType || undefined);
  const tabs = ["", ...Object.keys(TYPE_META)].map((t) => {
    const label = t ? TYPE_META[t][0] + " " + TYPE_META[t][1] : "all";
    return `<button class="conflict-tab dir-tab ${((activeType || "") === t) ? "active" : ""}"
      data-type="${t}">${label}</button>`;
  }).join("");
  el.innerHTML = `<h1>Stories</h1>
    <p class="cp-meta">The browsing surface for slower-moving story shapes — the live feed stays
      chronological; this is where threads, wars, alliances, patterns and agendas live (§8, v6 §27).</p>
    <div class="dir-threads"></div>
    <div class="dir-tabs">${tabs}</div><div class="dir-list"></div>`;
  // v6 §27 — Story Threads lead the directory: the macro-trend grouping
  // ABOVE individual stories, each with its member stories still visible
  const threadsHost = el.querySelector(".dir-threads");
  for (const t of (data.threads || [])) {
    const card = document.createElement("div");
    card.className = "story-card dir-card thread-card";
    card.innerHTML = `<div class="card-meta">
        <span class="chip">🧵 thread</span>
        <span class="cp-meta">${t.story_count || 0} stories</span>
        <span class="cp-meta" style="margin-left:auto">${esc((t.last_updated_at || "").slice(0, 10))}</span>
      </div><h3></h3><p class="cp-meta dir-sub"></p><div class="thread-members"></div>`;
    card.querySelector("h3").textContent = t.name;
    card.querySelector(".dir-sub").textContent = t.description || "";
    const mHost = card.querySelector(".thread-members");
    for (const m of (t.members || []).slice(0, 4)) {
      const chip = document.createElement("button");
      chip.className = "ap-chip";
      chip.textContent = "⌕ " + (m.headline || m.id).slice(0, 52);
      chip.addEventListener("click", (ev) => { ev.stopPropagation(); ctx.openStory(m.id); });
      mHost.appendChild(chip);
    }
    card.addEventListener("click", () => ctx.openThread(t.id));
    threadsHost.appendChild(card);
  }
  if ((data.threads || []).length) {
    const hdr = document.createElement("h4");
    hdr.textContent = "Individual entries";
    hdr.className = "dir-divider";
    threadsHost.appendChild(hdr);
  }
  el.querySelectorAll(".dir-tab").forEach((b) =>
    b.addEventListener("click", () => ctx.openDirectory(b.dataset.type || null)));
  const list = el.querySelector(".dir-list");
  for (const e of data.entries || []) {
    const meta = TYPE_META[e.story_type] || ["•", e.story_type, ""];
    const row = document.createElement("div");
    row.className = "story-card dir-card";
    row.innerHTML = `<div class="card-meta"><span class="chip">${meta[0]} ${esc(e.story_type.replace(/_/g, " "))}</span>
        ${e.status ? `<span class="chip">${esc(e.status)}</span>` : ""}
        ${e.story_count != null ? `<span class="cp-meta">${e.story_count} stories</span>` : ""}
        ${e.member_count != null ? `<span class="cp-meta">${e.member_count} members</span>` : ""}
        <span class="cp-meta" style="margin-left:auto">${esc((e.updated_at || "").slice(0, 10))}</span></div>
      <h3></h3><p class="cp-meta dir-sub"></p>`;
    row.querySelector("h3").textContent = e.title || "";
    row.querySelector(".dir-sub").textContent = e.subtitle || "";
    row.addEventListener("click", () => {
      if (e.ref_type === "story") ctx.openStory(e.ref_id);
      else if (e.ref_type === "conflict") ctx.openConflict(e.ref_id);
      else if (e.ref_type === "alliance") ctx.openEntity("alliance", e.ref_id);
      else if (e.ref_type === "country") ctx.openEntity("country", e.ref_id);
      else if (e.ref_type === "second_order" && e.story_a_id) ctx.openStory(e.story_a_id);
    });
    list.appendChild(row);
  }
  if (!(data.entries || []).length) {
    list.innerHTML = '<p class="cp-meta">nothing here yet — entries appear as coverage accumulates</p>';
  }
}

// ---------- §14 API key onboarding / settings ----------

export async function renderSettings(el, ctx) {
  const data = await api.keysStatus();
  // v6.5 — Ollama (local AI) is the PRIMARY provider: show its live status
  // first, with exact setup steps when it isn't ready. Key rows follow as the
  // cloud alternative.
  const ol = data.ollama || {};
  let olStatus;
  if (ol.reachable && ol.model_pulled) {
    olStatus = `<span class="conf-high">✅ running</span> — model <b>${esc(ol.model)}</b> ready
      at <code>${esc(ol.host)}</code>. All AI features are live, free and private.`;
  } else if (ol.reachable) {
    olStatus = `<span class="conf-medium">⚠ server running, model missing</span> — run
      <code>ollama pull ${esc(ol.model)}</code> in a terminal (one time).
      Installed: ${esc((ol.installed_models || []).join(", ") || "none")}`;
  } else {
    olStatus = `<span class="conf-low">❌ not detected</span> — install from
      <a href="https://ollama.com" target="_blank" rel="noopener">ollama.com</a>, then run
      <code>ollama pull ${esc(ol.model || "llama3.1")}</code>. GlobeGrid finds it
      automatically; no key needed. (Or add a Groq key below instead.)`;
  }
  el.innerHTML = `<h1>Settings — AI &amp; API keys</h1>
    <section><h4>🖥 Local AI — Ollama (primary)</h4>
      <p class="ollama-status">${olStatus}</p>
      <p class="cp-meta">Verify everything end-to-end on the
        <a href="/api/diagnostics" target="_blank">diagnostics page</a>.</p>
    </section>
    <h4>☁ Cloud keys (optional fallback)</h4>
    <p class="cp-meta">Keys are written straight to <code>${esc(data.env_path)}</code> — no manual
      file editing. Each save runs a live test call so you know the key actually works (§14).</p>
    <div class="keys-list"></div>
    <section><h4>Display</h4>
      <label class="settings-row">Color theme
        <select id="theme-select"></select></label>
      <label class="settings-row">Interface language
        <select id="lang-select"></select></label>
      <label class="settings-row">Night-side city lights
        <input type="checkbox" id="citylights-toggle"></label>
      <label class="settings-row">Timezone
        <select id="tz-select"></select></label>
      <label class="settings-row">Date format
        <select id="datefmt-select">
          <option value="iso">2026-07-06 14:30 (ISO)</option>
          <option value="us">Jul 6, 2026 2:30 PM (US)</option>
          <option value="eu">6 Jul 2026 14:30 (EU)</option>
        </select></label>
    </section>`;
  const list = el.querySelector(".keys-list");
  // v5 §14 / v6 §23 — theme selector, populated from config themes.available
  const themeSel = el.querySelector("#theme-select");
  for (const t of (ctx.themes ? ctx.themes() : ["dark_teal_default"])) {
    const o = document.createElement("option");
    o.value = t; o.textContent = t.replace(/_/g, " ");
    themeSel.appendChild(o);
  }
  themeSel.value = localStorage.getItem("tdl_theme") || "dark_teal_default";
  themeSel.addEventListener("change", () => ctx.setTheme(themeSel.value));
  // v5 §2 — interface language selector
  const langSel = el.querySelector("#lang-select");
  for (const l of ctx.languages()) {
    const o = document.createElement("option");
    o.value = l.code; o.textContent = l.name + (l.rtl ? " (RTL)" : "");
    langSel.appendChild(o);
  }
  langSel.value = localStorage.getItem("tdl_lang") || "en";
  langSel.addEventListener("change", () => ctx.setLanguage(langSel.value));
  // v6 §24 — night-side city lights on/off
  const cl = el.querySelector("#citylights-toggle");
  cl.checked = ctx.cityLights ? ctx.cityLights() : true;
  cl.addEventListener("change", () => ctx.setCityLights && ctx.setCityLights(cl.checked));
  // v6.1.1 — timezone + date format (applied to every rendered timestamp)
  const tzSel = el.querySelector("#tz-select");
  for (const g of TIMEZONES) {
    const og = document.createElement("optgroup");
    og.label = g.group;
    for (const [val, label] of g.zones) {
      const o = document.createElement("option");
      o.value = val; o.textContent = label;
      og.appendChild(o);
    }
    tzSel.appendChild(og);
  }
  tzSel.value = getTimeZone();
  tzSel.addEventListener("change", () => {
    setTimeZone(tzSel.value);
    if (ctx.onTimeSettingsChanged) ctx.onTimeSettingsChanged();
  });
  const dfSel = el.querySelector("#datefmt-select");
  dfSel.value = getDateFormat();
  dfSel.addEventListener("change", () => {
    setDateFormat(dfSel.value);
    if (ctx.onTimeSettingsChanged) ctx.onTimeSettingsChanged();
  });
  for (const k of data.keys || []) {
    const row = document.createElement("section");
    row.className = "key-row";
    row.innerHTML = `
      <h4>${esc(k.label)} ${k.required ? '<span class="chip chip-official">required for AI features</span>'
                                        : '<span class="chip">optional</span>'}
        <span class="key-state ${k.configured ? "conf-high" : "conf-low"}">
          ${k.configured ? "✓ configured (" + esc(k.masked) + ")" : "not set"}</span></h4>
      <p class="cp-meta">${esc(k.enables)}</p>
      <p class="cp-meta">How to get it: ${esc(k.signup)}</p>
      <div class="key-input"><input type="password" placeholder="paste key…" autocomplete="off">
        <button>save & test</button><span class="key-result cp-meta"></span></div>`;
    row.querySelector("button").addEventListener("click", async () => {
      const input = row.querySelector("input");
      const out = row.querySelector(".key-result");
      if (!input.value.trim()) return;
      out.textContent = "testing…";
      const res = await api.keySave(k.name, input.value.trim()).catch((e) => ({ ok: false, detail: e.message }));
      out.textContent = (res.ok ? "✓ " : "✗ ") + (res.detail || "");
      out.className = "key-result " + (res.ok ? "conf-high" : "conf-low");
      if (res.ok) {
        input.value = "";
        row.querySelector(".key-state").textContent = "✓ configured";
        row.querySelector(".key-state").className = "key-state conf-high";
        // v6.2 — INSTANT PING: the backend just kicked an AI warm-up; tell the
        // app so it re-reads ai_available and re-renders the feed, and show a
        // reassuring note that the system is lighting up.
        out.textContent = "✓ key live — warming up AI features across the system…";
        if (ctx.onAiKeySaved) ctx.onAiKeySaved();
      }
    });
    list.appendChild(row);
  }
}
