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

// v7 Part 6 — curated world-knowledge dossier, rendered INSTANTLY on open
// (no LLM, no network): the "explain this to someone who just discovered it"
// layer. `k` is the route's knowledge object {brief, region_brief?, curated}.
// v7.3 — break a dense one-paragraph brief into 2-sentence chunks so it reads
// as scannable paragraphs, not a wall of text (owner: "this is not readable at
// all … how is someone who doesnt know that much supposed to understand it").
function _paras(text) {
  const sentences = String(text || "").match(/[^.!?]+[.!?]+(?:["')\]]|\s|$)/g)
    || [text];
  const out = [];
  for (let i = 0; i < sentences.length; i += 2) {
    out.push(sentences.slice(i, i + 2).join("").trim());
  }
  return out.filter(Boolean);
}
export function knowledgeSection(k, title = "Deep background") {
  if (!k || (!k.brief && !k.region_brief)) return "";
  const tag = k.curated
    ? '<span class="chip">curated intelligence · early 2026</span>'
    : '<span class="chip">composed from tracked data</span>';
  const briefHtml = k.brief
    ? _paras(k.brief).map((p) => `<p class="knowledge-text">${esc(p)}</p>`).join("")
    : "";
  return `<section class="knowledge-sec"><h4>🌍 ${esc(title)} ${tag}</h4>
    ${briefHtml}
    ${k.region_brief ? `<div class="knowledge-region">
      <h5>Regional context${k.region ? ` — ${esc(k.region)}` : ""}</h5>
      ${_paras(k.region_brief).map((p) => `<p class="knowledge-text">${esc(p)}</p>`).join("")}
      </div>` : ""}
  </section>`;
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
  // v7.4.2 — every party in the seat arc is a CLICKABLE chip that opens its
  // full professional dossier (owner). Skip non-party buckets like Other/Vacant.
  const _skip = /^(other|vacant|independent|independent\/other)/i;
  const legend = parties.map((p) => {
    const clickable = p.name && !_skip.test(p.name);
    return `<span class="seat-legend${clickable ? " party-dossier-open" : ""}"${clickable ? ` data-party="${esc(p.name)}" role="button" tabindex="0"` : ""}><i style="background:${p.color}"></i>${esc(p.name)} <b>${p.seats}</b></span>`;
  }).join(" ");
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
  // v6.6.7 — the portrait AND the placeholder are ALWAYS clickable (open the
  // leader profile), regardless of whether a photo loaded.
  const leaderName = leader ? esc(leader.name) : "";
  const photo = (leader && leader.image_url)
    ? `<img class="leader-photo leader-open" data-leader="${leaderName}" title="open leader profile"
        src="${esc(leader.image_url)}" alt="${esc(leader.name)}"
        onerror="this.outerHTML='<div class=\\'leader-photo leader-photo-empty leader-open\\' data-leader=\\'${leaderName}\\'>👤</div>'">`
    : `<div class="leader-photo leader-photo-empty leader-open" data-leader="${leaderName}" title="open leader profile · fetching portrait…">👤</div>`;

  // v6.6.8 — a ceremonial head of state (a monarch in a constitutional/
  // parliamentary monarchy, where the PM is paramount) is clearly labeled as
  // NOT the actual ruler (owner: the King of Denmark is not the ruler).
  const gtype = (p.government_type || "").toLowerCase();
  const ceremonialMonarch = p.paramount_role === "head_of_government"
    && gtype.includes("monarchy") && !gtype.includes("absolute");
  const leadership = (p.leadership || []).map((l) => {
    const src = l.last_refreshed_at ? `synced ${l.last_refreshed_at.slice(0, 10)}` : "seed data";
    const isLead = l.role === p.paramount_role;   // v6.1 — mark who actually leads
    const ceremonial = ceremonialMonarch && l.role === "head_of_state";
    return `<div class="src-row"><span class="leaning">${esc(l.role.replace(/_/g, " "))}</span>
      <b class="leader-open" data-leader="${esc(l.name)}" style="cursor:pointer" title="open leader profile">${esc(l.name)}</b>${isLead ? ' <span class="chip" style="font-size:10px">★ leads</span>' : ""}${ceremonial ? ' <span class="chip" style="font-size:10px">ceremonial</span>' : ""}${l.party ? " · " + esc(l.party) : ""}
      <span class="cp-meta" style="margin-left:auto">${src}</span></div>`;
  }).join("") || '<p class="cp-meta">no leadership data yet (fills in from Wikidata)</p>';

  // v6.6.2 — bloc chips open the full bloc panel (click-through from members)
  const memberships = (p.memberships || []).map((m) =>
    `<button class="ap-chip bloc-link" data-id="${esc(m.alliance_id || "")}">${esc(m.name)}</button>`).join(" ") ||
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
  // v7.4.1 — ALL languages spoken in the country, shown right after the
  // official ones (owner). Drop any already listed as an official language so
  // the row genuinely reads as the *additional* tongues.
  const officialSet = new Set((Array.isArray(p.languages) ? p.languages : [])
    .map((s) => String(s).toLowerCase()));
  const otherLangs = Array.isArray(p.other_languages)
    ? p.other_languages.filter((l) => !officialSet.has(String(l).toLowerCase())).join(", ")
    : "";
  const fmtB = (v) => v >= 1e12 ? "$" + (v / 1e12).toFixed(2) + "T"
    : v >= 1e9 ? "$" + (v / 1e9).toFixed(1) + "B" : "$" + (v / 1e6).toFixed(0) + "M";
  // v6.6.5 — metric-bearing stat cells are clickable (data-metric) and open a
  // detail panel (distribution, sector/geographic breakdown, growth trajectory)
  const statCells = [
    p.population != null && ["Population", (p.population / 1e6).toFixed(2) + "M", "population"],
    p.gdp_usd != null && ["GDP (nominal)", fmtB(p.gdp_usd), "gdp"],
    p.gdp_per_capita_usd != null && ["GDP per capita",
      "$" + Math.round(p.gdp_per_capita_usd).toLocaleString(), "gdp_per_capita"],
    p.hdi != null && ["HDI", Number(p.hdi).toFixed(3), "hdi"],
    p.area_km2 != null && ["Area", Math.round(p.area_km2).toLocaleString() + " km²", "area"],
    langs && ["Languages", langs],
    otherLangs && ["Other languages", otherLangs],
    p.dominant_religion && ["Dominant religion", p.dominant_religion],
    p.currency_code && ["Currency",   // v6.1 — every country's currency
      `${p.currency_name} (${p.currency_code}${p.currency_symbol ? " " + p.currency_symbol : ""})`],
  ].filter(Boolean).map(([k, v, metric]) =>
    `<div class="stat-cell${metric ? " stat-clickable" : ""}"${metric ? ` data-metric="${metric}"` : ""}>
      <span class="stat-k">${esc(k)}${metric ? ' <span class="cp-meta">▸</span>' : ""}</span>
      <span class="stat-v">${esc(String(v))}</span></div>`).join("");
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
        <p class="cp-meta">${leader ? `<button class="ap-chip leader-open" data-leader="${leaderName}" title="open leader profile">${esc(leader.name)}</button>` + (leaderTitle ? " · " + esc(leaderTitle) : "") + " · " : ""}ruling: ${esc(rulingParty)}</p>
        <p class="cp-meta">${esc(p.capital || "—")} · ${esc(p.region || "—")}${p.government_type ? " · " + esc(p.government_type) : ""}</p>
        <p class="cp-meta">${trade}${pop ? " · " + pop : ""}</p>
      </div>
    </div>
    ${statCells ? `<section><h4>Key statistics</h4><div class="stat-grid">${statCells}</div></section>` : ""}
    ${knowledgeSection(p.knowledge, "Country intelligence")}
    ${territories}
    ${freshness(p.last_updated_at)}
    ${backgroundSection(p.background)}
    <section><h4>Leadership</h4>${leadership}</section>
    <section><h4>Member of</h4>${memberships}</section>
    ${(p.legislature && p.legislature.seats)
      ? `<section><h4>Legislature</h4>${parliamentGraphic(p.legislature)}</section>`
      : (p.legislature && p.legislature.composition_summary
          ? `<section><h4>Legislature</h4><p>${esc(p.legislature.chamber_name || "")}</p><p class="cp-meta">${esc(p.legislature.composition_summary)}</p></section>`
          : (p.legislature_note   /* v6.6.2 — explain absence, don't leave blank */
              ? `<section><h4>Legislature</h4><p class="cp-meta">${esc(p.legislature_note)}</p></section>`
              : ""))}
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
    ${(p.autonomous_zones || []).length ? `<section><h4>🏛 Autonomous regions</h4>
      ${p.autonomous_zones.map((z) =>
        `<button class="ap-chip az-open" data-id="${esc(z.id)}">🏛 ${esc(z.name)}</button>`).join(" ")}</section>` : ""}
    <section><h4>Recent tracked coverage ${thinBadge(p.coverage)}</h4>${storyChips(p.recent_stories)}</section>`;

  wireStoryChips(el, ctx);
  // v7.4.1 — autonomous-region chips open the region page
  el.querySelectorAll(".az-open").forEach((b) =>
    b.addEventListener("click", () => ctx.openAutonomousZone && ctx.openAutonomousZone(b.dataset.id)));
  // v7.4.2 — every parliament party is clickable → its full dossier
  el.querySelectorAll(".party-dossier-open").forEach((b) =>
    b.addEventListener("click", () => ctx.openPartyDossier
      && ctx.openPartyDossier(b.dataset.party, p.id)));
  // v6.2 — if the featured leader has no photo yet, fetch it on demand from
  // Wikipedia (reliable lead image) and swap it in, so e.g. Xi Jinping shows
  // next to the China flag immediately instead of waiting on a weekly sync.
  // v6.6 — experimental: diplomatic-alignment overlay button (derived for all
  // countries in v6.6.2). Placed in the header actions row (v6.6.2 — was
  // absolutely positioned and collided with the thin-coverage badge). Reflects
  // the live on/off state and re-targets when you navigate to another country.
  if (p && p.alignments) {
    const meta = el.querySelector(".wiki-head-meta") || el;
    const btn = document.createElement("button");
    btn.className = "ap-chip align-btn";
    const on = ctx.alignmentActive && ctx.alignmentActive() === p.id;
    btn.textContent = on ? "🗺 alignments ✓" : "🗺 alignments";
    btn.title = "toggle allies (green), partners (light green) and rivals (red) on the map";
    btn.addEventListener("click", () => {
      const active = ctx.showAlignments && ctx.showAlignments(p.id, p.alignments);
      btn.textContent = active ? "🗺 alignments ✓" : "🗺 alignments";
    });
    meta.appendChild(btn);
    // v6.6.2 — if alignment mode is already ON for a DIFFERENT country, opening
    // this one re-targets the overlay to it (owner: "should switch to that
    // country's alignments, not the previous country's").
    if (ctx.alignmentActive && ctx.alignmentActive() && ctx.alignmentActive() !== p.id) {
      ctx.showAlignments(p.id, p.alignments);
      btn.textContent = "🗺 alignments ✓";
    }
  }
  // v7.4.1 — recognition map mode: for a partially-recognized state (Kosovo,
  // Taiwan, Palestine, Israel, Western Sahara, N. Cyprus, Abkhazia, S. Ossetia)
  // a button colors who recognizes it (green) vs who doesn't (red).
  const RECOGNITION_SUBJECTS = new Set(["XKX", "TWN", "PSE", "ISR", "ESH", "CYN", "ABK", "OST"]);
  if (p && RECOGNITION_SUBJECTS.has(p.id) && ctx.showRecognition) {
    const meta = el.querySelector(".wiki-head-meta") || el;
    const rbtn = document.createElement("button");
    rbtn.className = "ap-chip recog-btn";
    const on = ctx.recognitionActive && ctx.recognitionActive() === p.id;
    rbtn.textContent = on ? "🏳 recognition ✓" : "🏳 recognition";
    rbtn.title = "who recognizes this state (green) vs who doesn't (red)";
    rbtn.addEventListener("click", async () => {
      const active = await ctx.showRecognition(p.id);
      rbtn.textContent = active ? "🏳 recognition ✓" : "🏳 recognition";
    });
    meta.appendChild(rbtn);
  }
  const ph = el.querySelector(".leader-photo-empty[data-leader]");
  if (ph && ph.dataset.leader) {
    api.leaderPortrait(ph.dataset.leader).then((r) => {
      if (r && r.image_url && ph.isConnected) {
        const img = new Image();
        img.className = "leader-photo leader-open";   // v6.6.7 stays clickable
        img.alt = ph.dataset.leader;
        img.dataset.leader = ph.dataset.leader;
        img.src = r.image_url;
        img.onerror = () => { /* keep placeholder */ };
        img.style.cursor = "pointer";
        img.title = "open leader profile";
        img.onclick = () => ctx.openLeader && ctx.openLeader(ph.dataset.leader);
        img.onload = () => ph.replaceWith(img);
      }
    }).catch(() => {});
  }
  // v6.6.7 — leader portrait/name/placeholder always open the profile
  el.querySelectorAll(".leader-open[data-leader]").forEach((b) =>
    b.addEventListener("click", () => b.dataset.leader && ctx.openLeader
      && ctx.openLeader(b.dataset.leader)));
  el.querySelectorAll(".party-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("party", b.dataset.id)));
  el.querySelectorAll(".country-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.id)));
  el.querySelectorAll(".conflict-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openConflict(b.dataset.id)));
  el.querySelectorAll(".compare-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openCompare(iso3, b.dataset.id)));
  el.querySelectorAll(".bloc-link").forEach((b) =>   // v6.6.2 — open bloc panel
    b.addEventListener("click", () => b.dataset.id && ctx.openEntity("alliance", b.dataset.id)));
  el.querySelectorAll(".stat-cell.stat-clickable").forEach((c) =>   // v6.6.5 stat detail
    c.addEventListener("click", () =>
      ctx.openCountryStat && ctx.openCountryStat(iso3, c.dataset.metric, p.name)));
}

// ---------- §6.2 other wiki pages ----------

export async function renderParty(el, id, ctx) {
  el.innerHTML = `<p class="cp-meta">loading party…</p>`;
  const p = await api.party(id).catch(() => null);
  if (!p) { el.innerHTML = `<p class="cp-meta">This party could not be loaded. Try again in a moment.</p>`; return; }
  paintParty(el, id, p, ctx);
  // v6.6.6 — AI synthesis generates in the background; re-fetch once to upgrade.
  if (p.synth_pending) {
    setTimeout(async () => {
      const p2 = await api.party(id).catch(() => null);
      if (p2 && p2.synthesis && el.isConnected) paintParty(el, id, p2, ctx);
    }, 5000);
  }
}

function paintParty(el, id, p, ctx) {
  const leaders = (p.leaders || []).map((l) =>
    `<div class="src-row"><b class="leader-open" data-leader="${esc(l.name)}" style="cursor:pointer" title="open leader profile">${esc(l.name)}</b>
     <span class="cp-meta">${esc(l.role.replace(/_/g, " "))} · since ${esc(l.since_date || "?")}</span></div>`
  ).join("") || '<p class="cp-meta">no tracked officeholders</p>';
  const s0 = p.synthesis || {};
  const leadName = (p.leaders || [])[0] && p.leaders[0].name;
  // v6.6.8 — a country-page-style stat grid so party pages read as richly.
  const statGrid = `<section><div class="stat-grid">
    <div class="stat-cell"><span class="cp-meta">Country</span><b>${esc(p.country_name || "—")}</b></div>
    <div class="stat-cell"><span class="cp-meta">Founded</span><b>${esc(p.founded_date || "—")}</b></div>
    <div class="stat-cell"><span class="cp-meta">Leader</span><b>${esc(leadName || "—")}</b></div>
    <div class="stat-cell"><span class="cp-meta">Position</span><b>${esc(s0.ideology || (p.ideology_tags || "").split(";")[0] || "—")}</b></div>
    </div></section>`;
  el.innerHTML = `
    <div class="wiki-header"><div class="wiki-flag">🏛</div>
      <div class="wiki-head-meta"><h1>${esc(p.name)}</h1>
        <p class="cp-meta">${esc(p.country_name || "")} · founded ${esc(p.founded_date || "?")}</p>
        <p class="cp-meta">ideology: ${esc((p.ideology_tags || "").replace(/;/g, " · "))}</p>
      </div></div>
    ${freshness(p.last_updated_at)}
    ${statGrid}
    ${(p.synth_pending && !p.synthesis) ? `<p class="cp-meta">✨ generating a detailed profile with AI… (updates in a moment)</p>` : ""}
    ${(() => { const s = p.synthesis; const b = (a) => (a || []).map((x) => `<li>${esc(x)}</li>`).join("");
      if (!s) return "";
      return `${s.summary ? `<section><p>${esc(s.summary)}</p></section>` : ""}
        ${s.ideology ? `<p class="leader-ideology"><span class="cp-meta">Ideology:</span> ${esc(s.ideology)}</p>` : ""}
        ${(s.history || []).length ? `<section><h4>History</h4><ul class="leader-list">${b(s.history)}</ul></section>` : ""}
        ${(s.positions || []).length ? `<section><h4>Positions &amp; platform</h4><ul class="leader-list">${b(s.positions)}</ul></section>` : ""}
        ${s.electoral ? `<section><h4>Electoral standing</h4><p>${esc(s.electoral)}</p></section>` : ""}`;
    })()}
    ${backgroundSection(p.background)}
    ${p.founding_history ? `<section><h4>Founding history <span class="cp-meta">(AI-synthesized, source-linked)</span></h4><p>${esc(p.founding_history)}</p></section>` : ""}
    ${partyElectoralSection(p.electoral_history)}
    ${partyCoalitionSection(p.coalition_partners)}
    <section><h4>Officeholders in tracked leadership</h4>${leaders}</section>
    <section><h4>Recent tracked coverage</h4>${storyChips(p.recent_stories)}</section>`;
  wireStoryChips(el, ctx);
  // v6.6.8 — officeholder names open the leader profile
  el.querySelectorAll(".leader-open[data-leader]").forEach((b) =>
    b.addEventListener("click", () => b.dataset.leader && ctx.openLeader
      && ctx.openLeader(b.dataset.leader)));
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
  // v7 — NSAs get a real flag/emblem + full official name, like a country
  const flag = a.flag_image_url
    ? `<img class="wiki-flag-img" src="${esc(a.flag_image_url)}" alt=""
         onerror="this.outerHTML='<div class=&quot;wiki-flag&quot;>◈</div>'">`
    : '<div class="wiki-flag">◈</div>';
  el.innerHTML = `
    <div class="wiki-header">${flag}
      <div class="wiki-head-meta"><h1>${esc(a.name)}</h1>
        ${a.official_name ? `<p class="cp-meta nsa-official">${esc(a.official_name)}</p>` : ""}
        <p class="cp-meta">${esc(a.actor_type)} · ${esc(a.primary_region || "")}
          · active since ${esc(a.active_since || "?")}</p>
        ${a.affiliated_state_name ? `<p class="cp-meta">reported backing: ${esc(a.affiliated_state_name)}</p>` : ""}
      </div></div>
    ${freshness(a.last_updated_at)}
    ${knowledgeSection(a.knowledge)}
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

// v6.6.2 — full bloc panel modeled on the UN page: leader portrait, purpose &
// HQ, policies/strategies, aggregate stats, member flag grid (click-through),
// conflicts members are party to (military blocs), recent stories, notable
// measures, and — for the EU — a parliament hemicycle. One backend call.
export async function renderAlliance(el, id, ctx) {
  let a;
  try { a = await api.alliance(id); }
  catch { el.innerHTML = "<p>alliance not registered</p>"; return; }
  if (!a || a.error) { el.innerHTML = "<p>alliance not registered</p>"; return; }
  const prof = a.profile || {};
  const stats = a.stats || {};
  const fmtN = (n) => n >= 1e12 ? "$" + (n / 1e12).toFixed(1) + "T"
    : n >= 1e9 ? "$" + (n / 1e9).toFixed(0) + "B" : "$" + (n || 0);
  const fmtPop = (n) => n >= 1e9 ? (n / 1e9).toFixed(2) + "B"
    : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : String(n || 0);
  const memberChips = (a.members || []).filter((m) => m.status === "member").map((m) =>
    `<button class="ap-chip country-link" data-id="${esc(m.id)}">
      ${m.flag_image_url ? flagInline(m) : ""} ${esc(m.name)}</button>`).join(" ");
  const observers = (a.members || []).filter((m) => m.status !== "member");
  // v6.6.4 — a recognizable emblem per bloc; v7.4 — REAL bloc flags/emblems
  // from Wikimedia (owner: "make sure bloc panels have actual symbols or flags
  // of the blocs … not random ahh emojis"). Falls back to the emoji on load
  // error so a bloc without a hosted flag still shows something sensible.
  const BLOC_EMBLEM = {
    "NATO": "🛡️", "European Union": "🇪🇺", "CSTO": "🛡️", "Arab League": "🕌",
    "ASEAN": "🌏", "African Union": "🌍", "BRICS": "🧱", "OPEC": "🛢️",
    "Five Eyes": "👁️", "QUAD": "🀫", "AUKUS": "⚓", "G7": "7️⃣", "OECD": "📊",
    "SCO": "🌏", "Mercosur": "🌎", "GCC": "🕌", "ECOWAS": "🌍",
  };
  const BLOC_FLAG_FILE = {
    "NATO": "Flag of NATO.svg", "European Union": "Flag of Europe.svg",
    "African Union": "Flag of the African Union.svg", "ASEAN": "Flag of ASEAN.svg",
    "Arab League": "Flag of the Arab League.svg",
    "SCO": "Flag of the Shanghai Cooperation Organisation.svg",
    "CSTO": "Emblem of the Collective Security Treaty Organization.svg",
    "Mercosur": "Flag of Mercosur.svg", "ECOWAS": "Flag of ECOWAS.svg",
    "GCC": "Flag of the Cooperation Council for the Arab States of the Gulf.svg",
    "OPEC": "Flag of OPEC.svg", "OECD": "OECD logo.svg", "AUKUS": "AUKUS logo.svg",
  };
  const emblemChar = BLOC_EMBLEM[a.name] || "⬡";
  // v7.6 — prefer the backend's data-driven emblem_url (broader bloc coverage),
  // then the local file map, then the emoji fallback on load error.
  const flagFile = BLOC_FLAG_FILE[a.name];
  const emblemUrl = a.emblem_url
    || (flagFile ? `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(flagFile)}` : null);
  const emblem = emblemUrl
    ? `<img class="wiki-flag-img" src="${esc(emblemUrl)}${emblemUrl.includes("?") ? "" : "?width=120"}"
         alt="${esc(a.name)} flag"
         onerror="this.outerHTML='<div style=&quot;font-size:56px;text-align:center&quot;>${emblemChar}</div>'">`
    : `<div style="font-size:56px;text-align:center">${emblemChar}</div>`;
  el.innerHTML = `
    <div class="wiki-header"><div class="wiki-flag">${emblem}</div>
      <div class="wiki-head-meta"><h1>${esc(a.name)}</h1>
        <p class="cp-meta">${esc(a.type)} bloc · founded ${esc(a.founded_date || "?")}
          · ${stats.member_count || 0} members${prof.hq ? " · HQ " + esc(prof.hq) : ""}</p>
      </div></div>
    ${freshness(a.last_updated_at)}
    ${a.leader ? `<section><h4>Leadership</h4>
      <div class="wiki-header"><div class="leader-photo leader-photo-empty" data-leader="${esc(a.leader[0])}">👤</div>
      <div><b class="leader-link" data-leader="${esc(a.leader[0])}" style="cursor:pointer">${esc(a.leader[0])}</b>
        <p class="cp-meta">${esc(a.leader[1])} · since ${esc(a.leader[2])}</p></div></div>
    </section>` : ""}
    ${knowledgeSection(a.knowledge, "Bloc intelligence")}
    <section><h4>Purpose</h4><p>${esc(prof.purpose || a.description || "—")}</p></section>
    <section class="bloc-stats"><h4>Statistics</h4>
      <div class="stat-grid">
        <div class="stat-cell"><span class="cp-meta">Members</span><b>${stats.member_count || 0}</b></div>
        <div class="stat-cell"><span class="cp-meta">Combined population</span><b>${fmtPop(stats.total_population)}</b></div>
        <div class="stat-cell"><span class="cp-meta">Combined GDP</span><b>${fmtN(stats.total_gdp_usd)}</b></div>
      </div></section>
    ${prof.policies ? `<section><h4>Policies & strategies</h4>
      <ul class="bloc-policies">${prof.policies.map((p) => `<li>${esc(p)}</li>`).join("")}</ul></section>` : ""}
    <section class="bloc-parliament"></section>
    <section class="bloc-conflicts"></section>
    <section class="bloc-stories"><h4>Recent related stories</h4><p class="cp-meta">loading…</p></section>
    ${prof.measures && prof.measures.length ? `<section><h4>Recent measures</h4>
      ${prof.measures.map(([t, d]) => `<div class="src-row"><b>${esc(t)}</b>
        <span class="cp-meta" style="margin-left:auto">${esc(d)}</span></div>`).join("")}</section>` : ""}
    <section><h4>Members <span class="cp-meta">(${stats.member_count || 0} — click to open)</span></h4>
      <div class="member-grid">${memberChips || '<span class="cp-meta">roster syncing…</span>'}</div>
      ${observers.length ? `<p class="cp-meta" style="margin-top:8px">Observers / candidates: ${
        observers.map((o) => esc(o.name)).join(", ")}</p>` : ""}
    </section>`;
  el.querySelectorAll(".country-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.id)));
  // leader portrait + click-through to the leader profile page
  const bph = el.querySelector(".leader-photo-empty[data-leader]");
  if (bph) api.leaderPortrait(bph.dataset.leader).then((r) => {
    if (r && r.image_url && bph.isConnected) {
      const img = new Image(); img.className = "leader-photo"; img.src = r.image_url;
      img.style.cursor = "pointer";
      img.onload = () => { bph.replaceWith(img);
        img.addEventListener("click", () => ctx.openLeader && ctx.openLeader(bph.dataset.leader)); };
    }
  }).catch(() => {});
  el.querySelectorAll(".leader-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openLeader && ctx.openLeader(b.dataset.leader)));
  // EU parliament hemicycle — reuse the same column-first oneChamber graphic
  if (a.parliament) {
    const host = el.querySelector(".bloc-parliament");
    const cham = { chamber: "European Parliament", total: a.parliament.total,
                   parties: a.parliament.groups.map(([abbr, , seats, color]) => [abbr, seats, color]) };
    host.innerHTML = `<h4>Parliament breakdown</h4>${oneChamber(cham, "European Parliament")}`;
  }
  // conflicts members are party to
  const cf = el.querySelector(".bloc-conflicts");
  if ((a.conflicts || []).length) {
    cf.innerHTML = `<h4>Conflicts involving members</h4>` + a.conflicts.map((c) =>
      `<div class="src-row conflict-hit" data-id="${esc(c.id)}" style="cursor:pointer">
        <b>${esc(c.name)}</b><span class="chip" style="margin-left:auto">${esc(c.status)}</span></div>`).join("");
    cf.querySelectorAll(".conflict-hit").forEach((r) =>
      r.addEventListener("click", () => ctx.openConflict && ctx.openConflict(r.dataset.id)));
  }
  // recent stories from the same backend call (no extra request)
  const bs = el.querySelector(".bloc-stories");
  const hits = a.recent_stories || [];
  bs.innerHTML = `<h4>Recent related stories</h4>` + (hits.length
    ? hits.map((h) => `<div class="src-row story-hit" data-id="${esc(h.id)}" style="cursor:pointer">
        <b>${esc(h.headline || "")}</b></div>`).join("")
    : `<p class="cp-meta">no tracked stories mention ${esc(a.name)} yet</p>`);
  bs.querySelectorAll(".story-hit").forEach((r) =>
    r.addEventListener("click", () => ctx.openStory && ctx.openStory(r.dataset.id)));
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
    if (backers.length) inner += `<div class="war-line"><span class="war-role">Supporting states</span> ${backers.map(partyChip).join(" ")}</div>`;
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
      <p class="cp-meta">This panel is the conflict's own analysis, events and
        stories — the global live feed is left untouched (reopens on exit).</p>
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
  // v6.6 — column-first fill (sorted by angular fraction), matching the
  // parliamentary hemicycles, so for/against/abstain form clean wedges.
  // v6.6.2 BUGFIX: the tally uses yes/no/abstain, but this read for/against
  // (always undefined→0) — the graphic showed "for 0, against 0" while the
  // text tally showed the real numbers. Read yes/no with for/against fallback.
  tally = tally || {};
  const yes = tally.yes ?? tally.for ?? 0;
  const no = tally.no ?? tally.against ?? 0;
  const abstain = tally.abstain ?? 0;
  const groups = [["for", yes, "#3ddc84"], ["against", no, "#ff5a5a"],
                  ["abstain", abstain, "#8a94a8"]];
  const colors = [];
  for (const [, n, c] of groups) for (let i = 0; i < n; i++) colors.push(c);
  const n = colors.length || 1;
  const rows = Math.max(2, Math.min(10, Math.ceil(Math.sqrt(n / 2.5))));
  const radii = [], weights = [];
  for (let i = 0; i < rows; i++) { const r = 1 + (rows === 1 ? 0 : i / (rows - 1)); radii.push(r); weights.push(r); }
  const wsum = weights.reduce((a, b) => a + b, 0);
  const rowCounts = []; let assigned = 0;
  for (let i = 0; i < rows; i++) { const c = Math.round(n * weights[i] / wsum); rowCounts.push(c); assigned += c; }
  rowCounts[rows - 1] += n - assigned;
  const W = 260, H = 140, cx = W / 2, cy = H - 8, maxR = Math.min(cx - 8, cy - 8);
  const seats = [];
  for (let i = 0; i < rows; i++) {
    const rr = (radii[i] / 2) * maxR, cnt = Math.max(0, rowCounts[i]);
    for (let j = 0; j < cnt; j++) {
      const t = cnt === 1 ? 0.5 : j / (cnt - 1);
      const ang = Math.PI - t * Math.PI;
      seats.push({ x: cx + rr * Math.cos(ang), y: cy - rr * Math.sin(ang), t });
    }
  }
  seats.sort((a, b) => a.t - b.t);
  const dots = seats.map((sd, i) =>
    `<circle cx="${sd.x.toFixed(1)}" cy="${sd.y.toFixed(1)}" r="2.8" fill="${colors[i] || "#888"}"></circle>`);
  return `<svg viewBox="0 0 ${W} ${H}" class="parliament-svg" preserveAspectRatio="xMidYMax meet">${dots.join("")}</svg>
    <div class="seat-legend-row"><span class="seat-legend"><i style="background:#3ddc84"></i>for <b>${yes}</b></span>
    <span class="seat-legend"><i style="background:#ff5a5a"></i>against <b>${no}</b></span>
    <span class="seat-legend"><i style="background:#8a94a8"></i>abstain <b>${abstain}</b></span></div>`;
}

const VOTE_CLASS = { yes: "vote-yes", no: "vote-no", abstain: "vote-abstain" };

function unSubOrgsHtml(orgs) {   // v6.6 — major UN organs & agencies
  if (!orgs || !orgs.length) return "";
  return `<section><h4>Organs &amp; agencies</h4>` + orgs.map((o) => `
    <details class="un-org"><summary><b>${esc(o.name)}</b> — ${esc(o.role.slice(0, 60))}…</summary>
      <p class="cp-meta">HQ: ${esc(o.hq)} · Head: ${esc(o.head)} · ${esc(o.members)}</p>
      <p>${esc(o.role)}</p></details>`).join("") + `</section>`;
}

const memberChip = (m) => `<button class="ap-chip country-link" data-id="${esc(m.id)}">${flagInline(m)} ${esc(m.name)}${m.term ? ` <i class="cp-meta">${esc(m.term)}</i>` : ""}</button>`;

// wire the country-link + resolution-expand handlers inside a UN content host
function wireUnContent(host, ctx) {
  host.querySelectorAll(".country-link").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.id)));
  // v7.4.1 — the nested UN news feed on the Overview tab (owner: "un-related
  // news should have its own feed that streams … nested against the UN page").
  const unFeed = host.querySelector(".un-news-feed");
  if (unFeed) {
    api.unFeed().then((d) => {
      const stories = d.stories || [];
      if (!stories.length) {
        unFeed.innerHTML = `<p class="cp-meta">No UN-tagged stories yet — they stream in as UN-family sources publish.</p>`;
        return;
      }
      unFeed.innerHTML = "";
      for (const s of stories) {
        const row = document.createElement("div");
        row.className = "story-card";
        row.style.cursor = "pointer";
        row.innerHTML = `<h3></h3>
          <div class="card-meta"><span class="cp-meta" style="margin-left:auto">${(s.last_occurred || s.first_seen_at || "").slice(0, 10)}</span></div>`;
        row.querySelector("h3").textContent = s.headline || "(untitled)";
        row.addEventListener("click", () => ctx.openStory && ctx.openStory(s.id));
        unFeed.appendChild(row);
      }
    }).catch(() => {
      unFeed.innerHTML = `<p class="cp-meta">UN news feed unavailable right now.</p>`;
    });
  }
  host.querySelectorAll(".res-expand").forEach((b) =>
    b.addEventListener("click", () => {
      const full = host.querySelector(`.res-full[data-ri="${b.dataset.ri}"]`);
      if (!full) return;
      const open = full.classList.toggle("hidden");
      b.textContent = open ? "▾ full breakdown" : "▴ hide breakdown";
      full.querySelectorAll(".country-link").forEach((cb) =>
        cb.addEventListener("click", () => ctx.openEntity("country", cb.dataset.id)));
    }));
}

// the resolutions block (with full-breakdown expanders), shared by the main UN
// page and the UNGA sub-page
function unResolutionsHtml(resList) {
  const voteCol = (r, kind, label, cls) => {
    const named = (r.notable_votes || []).filter((v) => v.vote === kind);
    const total = kind === "yes" ? r.tally.yes : kind === "no" ? r.tally.no : r.tally.abstain;
    const rest = Math.max(0, (total || 0) - named.length);
    return `<div class="vote-col"><div class="vote-col-head ${cls}">${label} (${total || 0})</div>
      ${named.map((v) => `<button class="ap-chip country-link ${cls}" data-id="${esc(v.id)}">${flagInline(v)} ${esc(v.name)}</button>`).join(" ")
        || '<span class="cp-meta">none named</span>'}
      ${rest ? `<div class="cp-meta">+ ${rest} more ${label.toLowerCase()}</div>` : ""}</div>`;
  };
  return (resList || []).map((r, ri) => {
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
        <button class="ap-chip res-expand" data-ri="${ri}">▾ full breakdown</button>
        <div class="res-full hidden" data-ri="${ri}">
          ${voteCol(r, "yes", "For", "vote-yes")}
          ${voteCol(r, "no", "Against", "vote-no")}
          ${voteCol(r, "abstain", "Abstain", "vote-abstain")}
        </div>
      </div>`;
  }).join("");
}

// the main UN overview page content
function unMainHtml(d) {
  const sc = d.security_council || {};
  return `
    <div class="wiki-header"><div class="wiki-head-meta">
      <h1>🇺🇳 United Nations</h1>
      <p class="cp-meta">Security Council, recent resolutions and how members voted.</p>
    </div></div>
    ${knowledgeSection(d.knowledge, "UN intelligence")}
    <section><h4>Security Council — Permanent members (P5, veto power)</h4>
      ${sc.permanent ? sc.permanent.map(memberChip).join(" ") : ""}</section>
    <section><h4>Security Council — Elected members</h4>
      ${sc.elected ? sc.elected.map(memberChip).join(" ") : ""}</section>
    <section><h4>Other principal organs</h4>
      ${(d.other_councils || []).map((c) => `<div class="src-row"><b>${esc(c.name)}</b> <span class="cp-meta">${esc(c.note)}</span></div>`).join("")}</section>
    <section class="un-news-section"><h4>📰 Live UN news</h4>
      <p class="cp-meta">Stories from UN-family sources and reporting that mentions the UN.</p>
      <div class="un-news-feed"><p class="cp-meta">loading…</p></div></section>
    <section><h4>Notable resolutions & recorded votes</h4>${unResolutionsHtml(d.resolutions)}</section>`;
}

// a sub-organ page, structured like the main page (facts + role, and the
// council/assembly its data belongs to)
function unOrgHtml(org, d) {
  const sc = d.security_council || {};
  const isUNGA = /General Assembly/i.test(org.name);
  const isUNSC = /Security Council/i.test(org.name);
  let extra = "";
  if (isUNSC) {
    // v6.6.6 — the UNSC tab now also lists the Security Council resolutions
    // (the fill was landing only on the overview/UNGA before).
    const scRes = (d.resolutions || []).filter((r) => /Security Council/i.test(r.body || ""));
    extra = `<section><h4>Permanent members (P5)</h4>${(sc.permanent || []).map(memberChip).join(" ")}</section>
      <section><h4>Elected members</h4>${(sc.elected || []).map(memberChip).join(" ")}</section>
      <section><h4>Resolutions & recorded votes</h4>${unResolutionsHtml(scRes.length ? scRes : d.resolutions)}</section>`;
  } else if (isUNGA) {
    const gaRes = (d.resolutions || []).filter((r) => /General Assembly/i.test(r.body || ""));
    extra = `<section><h4>Recent resolutions & recorded votes</h4>${unResolutionsHtml(gaRes.length ? gaRes : d.resolutions)}</section>`;
  }
  return `
    <div class="wiki-header"><div class="wiki-head-meta">
      <h1>${esc(org.name)}</h1>
      <p class="cp-meta">${esc(org.members)}</p></div></div>
    <section><h4>Key facts</h4>
      <div class="stat-grid">
        <div class="stat-cell"><span class="cp-meta">Headquarters</span><b>${esc(org.hq)}</b></div>
        <div class="stat-cell"><span class="cp-meta">Head</span><b>${esc(org.head)}</b></div>
        <div class="stat-cell"><span class="cp-meta">Membership</span><b>${esc(org.members)}</b></div>
      </div></section>
    <section><h4>Mandate</h4><p>${esc(org.role)}</p></section>
    ${extra}`;
}

// v6.6.2 — the UN page is now tabbed: a horizontal, navigable top-tab bar with
// the main overview plus each principal organ/agency as its OWN page (structured
// like the main page), replacing the old inline <details> accordions.
export async function renderUN(el, ctx) {
  const d = await api.un();
  const orgs = d.sub_orgs || [];
  const short = (n) => {
    const m = n.match(/\(([^)]+)\)/);   // prefer the abbreviation
    return m ? m[1] : n.split(/[\s—]/)[0];
  };
  const tabs = [{ label: "Overview", org: null },
                ...orgs.map((o) => ({ label: short(o.name), org: o }))];
  el.innerHTML = `<div class="un-tabs conflict-tabs">${tabs.map((t, i) =>
    `<button class="conflict-tab un-tab ${i === 0 ? "active" : ""}" data-i="${i}">${esc(t.label)}</button>`).join("")}</div>
    <div class="un-content"></div>`;
  const content = el.querySelector(".un-content");
  const show = (i) => {
    el.querySelectorAll(".un-tab").forEach((b, bi) => b.classList.toggle("active", bi === i));
    content.innerHTML = tabs[i].org ? unOrgHtml(tabs[i].org, d) : unMainHtml(d);
    wireUnContent(content, ctx);
  };
  el.querySelectorAll(".un-tab").forEach((b) =>
    b.addEventListener("click", () => show(+b.dataset.i)));
  show(0);
}

// ---------- v6.6.6 — Antarctica ----------

// Clicking the Antarctic landmass (no country polygon) opens this page: the
// continent, the Antarctic Treaty, and the seven territorial claims as chips
// that open the matching disputed-zone breakdown.
export async function renderAntarctica(el, ctx) {
  el.innerHTML = `<h1>🧊 Antarctica</h1>
    <p class="cp-meta">The southern polar continent · no permanent population · governed by the Antarctic Treaty System</p>`;
  const d = await api.disputedZones().catch(() => ({ zones: [] }));
  const claims = (d.zones || []).filter((z) => (z.id || "").startsWith("antarctica_"));
  el.innerHTML += `
    <section><p>Antarctica is the only continent with no sovereign government and
      no indigenous population. Roughly 98% is covered by ice averaging ~1.9 km
      thick — about 60% of the world's fresh water. It hosts only research
      stations, staffed by scientists and support crews from many nations.</p></section>
    <section><h4>The Antarctic Treaty</h4>
      <p>The 1959 Antarctic Treaty (in force 1961), now with 50+ parties,
      reserves the continent for peaceful and scientific use, bans military
      activity and mineral mining (the 1991 Madrid Protocol), and — crucially —
      <b>freezes all territorial claims</b>: it neither recognizes, disputes, nor
      establishes them. Seven states nonetheless maintain formal claims, three of
      which overlap on the Antarctic Peninsula.</p></section>
    <section><h4>Territorial claims (frozen)</h4>
      <p class="cp-meta">Seven claimant states — click a claim for its full breakdown.</p>
      <div class="disp-list">${claims.map((z) =>
        `<button class="ap-chip disp-open" data-id="${esc(z.id)}">⚑ ${esc(z.name)}
          <span class="cp-meta">${esc((z.claimants || [])[0] || "")}</span></button>`).join(" ")
        || '<p class="cp-meta">Enable disputed mode to see the claims on the map.</p>'}</div></section>
    <section><h4>Key facts</h4>
      <div class="stat-grid">
        <div class="stat-cell"><span class="cp-meta">Area</span><b>14.2M km²</b></div>
        <div class="stat-cell"><span class="cp-meta">Ice volume</span><b>~26.5M km³</b></div>
        <div class="stat-cell"><span class="cp-meta">Coldest recorded</span><b>−89.2 °C</b></div>
        <div class="stat-cell"><span class="cp-meta">Population</span><b>~1,000–5,000 (seasonal)</b></div>
      </div></section>`;
  el.querySelectorAll(".disp-open").forEach((b) =>
    b.addEventListener("click", () => ctx.openDisputedZone(b.dataset.id)));
}

// ---------- v6.6.2 — disputed territories ----------

// directory of all disputed zones; each opens its own breakdown
export async function renderDisputedZones(el, ctx) {
  el.innerHTML = `<h1>⚑ Disputed territories</h1>
    <p class="cp-meta">Contested regions with rival claims — click one for the full breakdown.</p>
    <div class="disp-list"><p class="cp-meta">loading…</p></div>`;
  const d = await api.disputedZones().catch(() => ({ zones: [] }));
  const list = el.querySelector(".disp-list");
  list.innerHTML = (d.zones || []).map((z) =>
    `<div class="src-row disp-row" data-id="${esc(z.id)}" style="cursor:pointer">
      <b>${esc(z.name)}</b>
      <span class="cp-meta" style="margin-left:auto">${esc(z.status)}</span></div>`).join("");
  list.querySelectorAll(".disp-row").forEach((r) =>
    r.addEventListener("click", () => ctx.openDisputedZone(r.dataset.id)));
}

// per-zone breakdown with context
export async function renderDisputedZone(el, zid, ctx) {
  const d = await api.disputedZones().catch(() => ({ zones: [] }));
  const z = (d.zones || []).find((x) => x.id === zid);
  if (!z) { el.innerHTML = "<p>disputed zone not found</p>"; return; }
  el.innerHTML = `
    <div class="wiki-header"><div class="wiki-flag">⚑</div>
      <div class="wiki-head-meta"><h1>${esc(z.name)}</h1>
        <p class="cp-meta">${esc(z.status)}</p></div></div>
    <section><h4>Control &amp; claims</h4>
      <div class="stat-grid">
        <div class="stat-cell"><span class="cp-meta">De-facto control</span><b>${esc(z.controller)}</b></div>
        <div class="stat-cell"><span class="cp-meta">Claimants</span><b>${(z.claimants || []).map(esc).join(" vs ")}</b></div>
      </div></section>
    <section><h4>Context</h4><p class="leader-bio">${esc(z.context)}</p></section>`;
}

// v7.4.1 — autonomous regions directory + per-zone page (a new entity type:
// self-governing regions inside a sovereign parent).
export async function renderAutonomousZones(el, ctx) {
  el.innerHTML = `<h1>🏛 Autonomous regions</h1>
    <p class="cp-meta">Self-governing regions with real autonomy inside a sovereign state —
      click one for its full breakdown.</p>
    <div class="az-list"><p class="cp-meta">loading…</p></div>`;
  const d = await api.autonomousZones().catch(() => ({ zones: [] }));
  const list = el.querySelector(".az-list");
  list.innerHTML = (d.zones || []).map((z) =>
    `<div class="src-row az-row" data-id="${esc(z.id)}" style="cursor:pointer">
      <b>${esc(z.name)}</b>
      <span class="cp-meta" style="margin-left:auto">in ${esc(z.parent)}</span></div>`).join("");
  list.querySelectorAll(".az-row").forEach((r) =>
    r.addEventListener("click", () => ctx.openAutonomousZone(r.dataset.id)));
}

export async function renderAutonomousZone(el, zid, ctx) {
  el.innerHTML = `<p class="cp-meta">loading…</p>`;
  const z = await api.autonomousZone(zid).catch(() => null);
  if (!z) { el.innerHTML = "<p>autonomous region not found</p>"; return; }
  // v7.6 — render EXACTLY like a country/territory panel: flag, leader(s), a
  // full stat grid, the legislature seat-arc, a strategic agenda, deep
  // background, and recent coverage (owner: "complete with everything a country
  // would have"). Every leader/party/parent name is a clickable chip.
  const st = z.stats || {};
  const leaderChip = (l) => l && l.name
    ? `<b class="leader-open" data-leader="${esc(l.name)}" style="cursor:pointer" title="open leader profile">${esc(l.name)}</b>`
      + (l.title ? ` <span class="cp-meta">— ${esc(l.title)}</span>` : "")
      + (l.party ? ` · <b class="party-dossier-open" data-party="${esc(l.party)}" style="cursor:pointer">${esc(l.party)}</b>` : "")
    : "";
  const cell = (label, val) => val
    ? `<div class="stat-cell"><span class="cp-meta">${esc(label)}</span><b>${esc(val)}</b></div>` : "";
  let html = `
    <div class="wiki-header">
      <div class="wiki-flag">${z.flag_url ? flagImg({ flag_image_url: z.flag_url, name: z.name }) : "🏛"}</div>
      <div class="wiki-head-meta"><h1>${esc(z.name)}</h1>
        <p class="cp-meta">Autonomous region of <b class="az-parent" data-name="${esc(z.parent)}" style="cursor:pointer">${esc(z.parent)}</b>${z.official_name ? " · " + esc(z.official_name) : ""}</p>
        ${z.leader ? `<p class="cp-meta">${leaderChip(z.leader)}</p>` : ""}
        ${z.leader2 ? `<p class="cp-meta">${leaderChip(z.leader2)}</p>` : ""}
      </div></div>
    <section><h4>Key facts</h4>
      <div class="stat-grid">
        ${cell("Parent state", z.parent).replace("<b>", `<b class="az-parent" data-name="${esc(z.parent)}" style="cursor:pointer">`)}
        ${cell("Capital / seat", z.capital)}
        ${cell("Population", st.population)}
        ${cell("Area", st.area_km2 ? st.area_km2 + " km²" : "")}
        ${cell("Languages", st.languages)}
        ${cell("Currency", st.currency)}
        ${cell("Established", z.established)}
      </div></section>`;
  if (z.legislature && (z.legislature.parties || []).length) {
    html += `<section><h4>Legislature — ${esc(z.legislature.chamber)}</h4>${oneChamber(z.legislature, "Legislature")}</section>`;
  } else if (z.legislature && z.legislature.chamber) {
    html += `<section><h4>Legislature</h4><p class="cp-meta">${esc(z.legislature.chamber)}${z.legislature.total ? " · " + z.legislature.total + " seats" : ""}</p></section>`;
  }
  if (z.agenda) {
    html += `<section><h4>Strategic agenda</h4><div class="narrative-box">${esc(z.agenda)}</div></section>`;
  }
  html += `<section><h4>Basis of autonomy</h4><p>${esc(z.autonomy_basis)}</p></section>
    <section><h4>Deep background</h4><p class="leader-bio">${esc(z.context)}</p></section>`;
  if ((z.recent_stories || []).length) {
    html += `<section><h4>Recent tracked coverage</h4>${storyChips(z.recent_stories, ctx)}</section>`;
  }
  el.innerHTML = html;
  // wire clickable chips
  el.querySelectorAll(".az-parent").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntityByName && ctx.openEntityByName("country", b.dataset.name)));
  el.querySelectorAll(".leader-open[data-leader]").forEach((b) =>
    b.addEventListener("click", () => ctx.openLeader && ctx.openLeader(b.dataset.leader)));
  el.querySelectorAll(".party-dossier-open[data-party]").forEach((b) =>
    b.addEventListener("click", () => ctx.openPartyDossier && ctx.openPartyDossier(b.dataset.party, null)));
  wireStoryChips(el, ctx);
}

// v7.4.2 — a full professional PARTY DOSSIER page, reachable from every
// parliament seat-arc chip (owner: "a full professional dossier on EVERYTHING
// about them"). Renders the curated dossier (ideology, economic/social position,
// EU stance, coalitions, electoral history, leader, stances, geopolitics), then
// merges the AI synthesis over it when a provider filled one in.
export async function renderPartyDossier(el, name, iso, ctx) {
  el.innerHTML = `<h1>${esc(name)}</h1><p class="cp-meta">loading dossier…</p>`;
  const d = await api.partyDossier(name, iso).catch(() => null);
  if (!d) { el.innerHTML = `<h1>${esc(name)}</h1><p>dossier unavailable</p>`; return; }
  const dos = d.dossier || {};
  const syn = d.synthesis || null;
  const row = (label, val) => val
    ? `<div class="stat-cell" style="grid-column:1/-1"><span class="stat-k">${esc(label)}</span><span class="stat-v">${esc(val)}</span></div>` : "";
  const list = (label, arr) => (arr && arr.length)
    ? `<section><h4>${esc(label)}</h4><ul class="deep-summary">${arr.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></section>` : "";
  const sect = (label, val) => val ? `<section><h4>${esc(label)}</h4><p>${esc(val)}</p></section>` : "";
  // v7.6 — real party logo/emblem when curated (owner: "add logos for every
  // political party"), else the 🏛 glyph.
  const plogo = dos.logo_url
    ? `<img class="wiki-flag-img" src="${esc(dos.logo_url)}" alt="${esc(name)} logo"
         onerror="this.outerHTML='<div style=&quot;font-size:44px&quot;>🏛</div>'">`
    : "🏛";
  let html = `<div class="wiki-header"><div class="wiki-flag">${plogo}</div>
    <div class="wiki-head-meta"><h1>${esc(dos.full_name || name)}</h1>
      <p class="cp-meta">${esc(dos.ideology || "Political party")}${dos.country ? " · " + esc(dos.country) : ""}</p></div></div>`;
  if (!dos.curated && dos.note) {
    html += `<p class="cp-meta">${esc(dos.note)}</p>`;
  }
  html += `<div class="stat-grid">
      ${row("Ideology", dos.ideology)}
      ${row("Economic position", dos.economic_position)}
      ${row("Social position", dos.social_position)}
      ${row("EU / integration stance", dos.eu_stance)}
      ${row("Current leader", dos.leader)}
      ${row("Coalitions", dos.coalitions)}
      ${row("Electoral record", dos.electoral)}
    </div>`;
  html += list("Signature stances", dos.stances);
  html += sect("Geopolitical ramifications", dos.geopolitical);
  // AI synthesis (merged over the curated floor when present)
  if (syn) {
    html += sect("Summary", syn.summary);
    html += list("History", syn.history);
    html += list("Policy positions", syn.positions);
    html += sect("Electoral standing", syn.electoral);
  } else if (d.synth_pending) {
    html += `<p class="cp-meta">Generating a deeper AI profile… reopen shortly.</p>`;
  }
  // officeholders from country_leadership belonging to this party
  if (d.party && (d.party.id)) {
    html += `<p class="cp-meta">Registered party · id ${esc(d.party.id)}</p>`;
  }
  if ((d.recent_stories || []).length) {
    html += `<section><h4>Recent tracked coverage</h4>${storyChips(d.recent_stories)}</section>`;
  }
  el.innerHTML = html;
  wireStoryChips(el, ctx);
  // v7.4.2 — if the AI profile was pending, re-fetch once to upgrade in place
  if (d.synth_pending) {
    setTimeout(() => renderPartyDossier(el, name, iso, ctx), 6000);
  }
}

// v6.6.5 — a country statistic detail panel: distribution (by city/province),
// composition (GDP by sector / geographic), and a growth trajectory. Uses an
// AI synthesis grounded in the country's known figures (no vendored city-level
// dataset needed); a simple bar shows the distribution.
const STAT_LABEL = { population: "Population", gdp: "GDP", gdp_per_capita: "GDP per capita",
                     hdi: "HDI", area: "Area" };
export async function renderCountryStat(el, iso3, metric, countryName, ctx) {
  el.innerHTML = `<h1>${esc(countryName || iso3)} — ${esc(STAT_LABEL[metric] || metric)}</h1>
    <p class="cp-meta">loading breakdown…</p>`;
  const d = await api.countryStat(iso3, metric).catch(() => null);
  if (!d || !d.detail) {
    // v6.6.6 — the breakdown generates in the background; if pending, re-fetch.
    if (d && d.detail_pending) {
      el.innerHTML = `<h1>${esc(countryName || iso3)} — ${esc(STAT_LABEL[metric] || metric)}</h1>
        <p class="cp-meta">✨ generating a detailed breakdown with AI… (updates in a moment).
        Headline figure: ${esc(String(d.headline || "—"))}.</p>`;
      setTimeout(() => { if (el.isConnected) renderCountryStat(el, iso3, metric, countryName, ctx); }, 5500);
      return;
    }
    el.innerHTML = `<h1>${esc(countryName || iso3)} — ${esc(STAT_LABEL[metric] || metric)}</h1>
      <p class="cp-meta">A detailed breakdown loads when an AI provider is
      configured (run Ollama or add a key). Headline figure: ${esc(String(d && d.headline || "—"))}.</p>`;
    return;
  }
  const s = d.detail;
  const bars = (arr) => {
    const max = Math.max(1, ...(arr || []).map((x) => x.value || 0));
    return (arr || []).map((x) =>
      `<div class="stat-bar-row"><span class="stat-bar-label">${esc(x.label)}</span>
        <span class="stat-bar" style="width:${Math.round((x.value || 0) / max * 100)}%"></span>
        <span class="stat-bar-val">${esc(x.display || String(x.value))}</span></div>`).join("");
  };
  el.innerHTML = `
    <h1>${esc(countryName || iso3)} — ${esc(STAT_LABEL[metric] || metric)}</h1>
    ${s.summary ? `<section><p>${esc(s.summary)}</p></section>` : ""}
    ${(s.distribution || []).length ? `<section><h4>${esc(s.distribution_label || "Distribution")}</h4>
      <div class="stat-bars">${bars(s.distribution)}</div></section>` : ""}
    ${(s.composition || []).length ? `<section><h4>${esc(s.composition_label || "Composition")}</h4>
      <div class="stat-bars">${bars(s.composition)}</div></section>` : ""}
    ${(s.trajectory || []).length ? `<section><h4>Trend over time</h4>
      <div class="stat-bars">${bars(s.trajectory)}</div></section>` : ""}
    ${(s.notes || []).length ? `<section><h4>Notes</h4><ul class="leader-list">${
      s.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></section>` : ""}
    <p class="cp-meta">AI-synthesized from known national figures — approximate, not an official dataset.</p>`;
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
  // v7.4.1 — a dedicated "chains" tab renders fact-chain lineage instead of the
  // normal directory list (owner request).
  const tabDefs = ["", ...Object.keys(TYPE_META), "chains"];
  const tabs = tabDefs.map((t) => {
    const label = t === "chains" ? "🔗 chains"
      : t ? TYPE_META[t][0] + " " + TYPE_META[t][1] : "all";
    return `<button class="conflict-tab dir-tab ${((activeType || "") === t) ? "active" : ""}"
      data-type="${t}">${label}</button>`;
  }).join("");
  if (activeType === "chains") {
    el.innerHTML = `<h1>Stories</h1>
      <p class="cp-meta">Lineage / chains — how today's stories connect back through the
        permanent fact chain across time.</p>
      <div class="dir-tabs">${tabs}</div><div class="chains-list"><p class="cp-meta">loading…</p></div>`;
    el.querySelectorAll(".dir-tab").forEach((b) =>
      b.addEventListener("click", () => ctx.openDirectory(b.dataset.type || null)));
    const clist = el.querySelector(".chains-list");
    try {
      const cd = await api.lineageChains();
      const chains = cd.chains || [];
      if (!chains.length) { clist.innerHTML = `<p class="cp-meta">No historical-chain links yet — they form as the fact chain grows.</p>`; return; }
      clist.innerHTML = "";
      for (const ch of chains) {
        const card = document.createElement("div");
        card.className = "story-card dir-card";
        card.style.cursor = "pointer";
        card.innerHTML = `<div class="card-meta"><span class="chip">🔗 chain</span>
            <span class="cp-meta">${ch.chain_len} linked facts</span>
            <span class="cp-meta" style="margin-left:auto">${esc((ch.last_updated_at || "").slice(0, 10))}</span></div>
          <h3></h3>
          <ul class="chain-facts">${(ch.chain || []).map((f) =>
            `<li>${esc((f.when_occurred || "").slice(0, 10))} — ${esc((f.what || f.who || "").slice(0, 100))}</li>`).join("")}</ul>`;
        card.querySelector("h3").textContent = ch.headline || "(untitled)";
        card.addEventListener("click", () => ctx.openStory(ch.id));
        clist.appendChild(card);
      }
    } catch (err) {
      clist.innerHTML = `<p class="cp-meta">Chains unavailable: ${esc(err.message || "")}</p>`;
    }
    return;
  }
  const data = await api.storiesDirectory(activeType || undefined);
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
  // v6.6 — Display and AI/keys are separate selectable tabs, Display first
  el.innerHTML = `<h1>Settings</h1>
    <div class="settings-tabs">
      <button class="stab active" data-tab="display">Display</button>
      <button class="stab" data-tab="ai">AI &amp; API keys</button>
    </div>
    <div class="settings-tab-display"></div>
    <div class="settings-tab-ai hidden">
    <section><h4>🖥 Local AI — Ollama (primary)</h4>
      <p class="ollama-status">${olStatus}</p>
      <p class="cp-meta">Verify everything end-to-end on the
        <a href="/api/diagnostics" target="_blank">diagnostics page</a>.</p>
    </section>
    <h4>☁ Cloud keys (optional fallback)</h4>
    <p class="cp-meta">Keys are written straight to <code>${esc(data.env_path)}</code> — no manual
      file editing. Each save runs a live test call so you know the key actually works (§14).</p>
    <div class="keys-list"></div>
    </div>
    <section class="display-sec"><h4>Display</h4>
      <label class="settings-row">Color theme
        <select id="theme-select"></select></label>
      <label class="settings-row">Font style
        <select id="font-select">
          <option value="sans">Sans (default)</option>
          <option value="serif">Serif</option>
          <option value="mono">Monospace</option>
          <option value="condensed">Condensed</option>
          <option value="rounded">Rounded</option>
        </select></label>
      <label class="settings-row">Interface language
        <select id="lang-select"></select></label>
      <label class="settings-row">Night-side city lights
        <input type="checkbox" id="citylights-toggle"></label>
      <label class="settings-row">Breaking-event pop-up alerts
        <input type="checkbox" id="alerts-toggle"></label>
      <label class="settings-row">Timezone
        <select id="tz-select"></select></label>
      <label class="settings-row">Date format
        <select id="datefmt-select">
          <option value="iso">2026-07-06 14:30 (ISO)</option>
          <option value="us">Jul 6, 2026 2:30 PM (US)</option>
          <option value="eu">6 Jul 2026 14:30 (EU)</option>
        </select></label>
    </section>`;
  // v6.6 — move the Display section into its tab, wire the tab switcher
  const dispHost = el.querySelector(".settings-tab-display");
  const dispSec = el.querySelector(".display-sec");
  if (dispHost && dispSec) dispHost.appendChild(dispSec);
  el.querySelectorAll(".stab").forEach((b) => b.addEventListener("click", () => {
    el.querySelectorAll(".stab").forEach((x) => x.classList.toggle("active", x === b));
    el.querySelector(".settings-tab-display").classList.toggle("hidden", b.dataset.tab !== "display");
    el.querySelector(".settings-tab-ai").classList.toggle("hidden", b.dataset.tab !== "ai");
  }));
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
  // v6.6.4 — font style selector
  const fontSel = el.querySelector("#font-select");
  if (fontSel) {
    fontSel.value = ctx.font ? ctx.font() : "sans";
    fontSel.addEventListener("change", () => ctx.setFont && ctx.setFont(fontSel.value));
  }
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
  // v6.6.2 — breaking-event pop-up alert toggle
  const al = el.querySelector("#alerts-toggle");
  if (al) {
    al.checked = ctx.alertsEnabled ? ctx.alertsEnabled() : true;
    al.addEventListener("change", () => ctx.setAlertsEnabled && ctx.setAlertsEnabled(al.checked));
  }
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


// v6.6 / v6.6.2 — rich personal profile panel for a world leader: large
// portrait, offices held, AI-synthesized ideology / career / party history /
// key policies, and a full Wikipedia biography.
export async function renderLeader(el, name, ctx) {
  el.innerHTML = `<h1>${esc(name)}</h1><p class="cp-meta">loading profile…</p>`;
  let d = await api.leaderProfile(name).catch(() => null);
  if (!d || (!(d.roles || []).length && !d.synthesis && !(d.bio && d.bio.extract))) {
    el.innerHTML = `<h1>${esc(name)}</h1>
      <p class="cp-meta">No profile is available for this name yet. Detailed
      profiles generate live when an AI provider (Ollama or a key) is running —
      open this page again in a few seconds.</p>`;
    return;
  }
  paintLeader(el, name, d, ctx);
  // v6.6.8 — the profile fills in FIELD BY FIELD in the background; poll a few
  // times to paint each field as it lands (fast per-field generation).
  if (d.synth_pending) {
    let tries = 0;
    const poll = async () => {
      if (!el.isConnected || tries++ >= 5) return;
      const d2 = await api.leaderProfile(name).catch(() => null);
      if (d2 && el.isConnected) paintLeader(el, name, d2, ctx);
      if (d2 && d2.synth_pending) setTimeout(poll, 4000);
    };
    setTimeout(poll, 3500);
  }
}

function paintLeader(el, name, d, ctx) {
  const bio = d.bio || {};
  const s = d.synthesis || null;
  const pendingNote = (d.synth_pending && !s)
    ? `<p class="cp-meta">✨ generating a detailed profile with AI… (updates in a moment)</p>` : "";
  const img = bio.image_url
    ? `<img class="leader-photo leader-photo-lg" src="${esc(bio.image_url)}">`
    : `<div class="leader-photo leader-photo-lg leader-photo-empty">👤</div>`;
  const bullets = (arr) => (arr || []).map((x) => `<li>${esc(x)}</li>`).join("");
  const flag = (d.roles || []).find((r) => r.flag_image_url);
  el.innerHTML = `
    <div class="wiki-header">${img}
      <div class="wiki-head-meta"><h1>${esc(d.name)}</h1>
        <p class="cp-meta">${esc(bio.description || (d.roles || [])[0]?.role?.replace(/_/g, " ") || "")}
          ${flag ? " · " + esc(flag.country_name) : ""}</p>
        ${s && s.ideology ? `<p class="leader-ideology"><span class="cp-meta">Ideology:</span> ${esc(s.ideology)}</p>` : ""}
      </div></div>
    ${pendingNote}
    ${s && s.summary ? `<section><p>${esc(s.summary)}</p></section>` : ""}
    <section><h4>Offices held</h4>${(d.roles || []).map((r) => `<div class="src-row">
       <span class="leaning">${esc((r.role || "").replace(/_/g, " "))}</span>
       <b>${esc(r.country_name || "")}</b>
       <span class="cp-meta">${esc(r.party || "")}${r.since_date ? " · since " + esc(r.since_date) : ""}</span></div>`).join("")
       || '<p class="cp-meta">no tracked office</p>'}</section>
    ${s && (s.career_history || []).length ? `<section><h4>Career &amp; positions</h4>
       <ul class="leader-list">${bullets(s.career_history)}</ul></section>` : ""}
    ${s && (s.party_history || []).length ? `<section><h4>Party history</h4>
       <ul class="leader-list">${bullets(s.party_history)}</ul></section>` : ""}
    ${s && (s.key_policies || []).length ? `<section><h4>Key policies &amp; positions</h4>
       <ul class="leader-list">${bullets(s.key_policies)}</ul></section>` : ""}
    ${bio.extract ? `<section><h4>Biography</h4><p class="leader-bio">${esc(bio.extract)}</p>
       ${bio.url ? `<p><a href="${esc(bio.url)}" target="_blank" rel="noopener">Wikipedia →</a></p>` : ""}</section>`
     : `<p class="cp-meta">Biography &amp; AI profile load live when online with an AI provider configured.</p>`}`;
}
