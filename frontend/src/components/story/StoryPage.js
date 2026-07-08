// Section 5.3 — story page: headline, AI summary, confidence indicator,
// timeline of which source lit up when, full source list with outbound
// links (always visible — Section 6.8), the connected-history fact-chain
// panel, the Section 5.7 bias/blindspot view, and Section 5.8
// display-time translation.
import { api } from "../../api/client.js";

// v6.2 — render markdown-ish bullet text as a real <ul>, XSS-safe (escape
// first, then only introduce <li>/<b>). Non-bullet lines become paragraphs.
function bulletsToHtml(text) {
  const esc = (t) => (t || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const bold = (t) => esc(t).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  const lines = (text || "").split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  let html = "", inList = false;
  for (const line of lines) {
    const m = line.match(/^[-*•]\s+(.*)/);
    if (m) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${bold(m[1])}</li>`; }
    else { if (inList) { html += "</ul>"; inList = false; } html += `<p>${bold(line)}</p>`; }
  }
  if (inList) html += "</ul>";
  return html || esc(text);
}

// v3 §12 — word-level LCS diff, old vs new, changed spans highlighted
function diffBlock(label, oldText, newText) {
  const a = (oldText || "").split(/\s+/), b = (newText || "").split(/\s+/);
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--)
    for (let j = n - 1; j >= 0; j--)
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out = document.createElement("div");
  out.className = "diff-block";
  const head = document.createElement("b");
  head.textContent = label;
  out.appendChild(head);
  const body = document.createElement("div");
  let i = 0, j = 0;
  const push = (text, cls) => {
    const span = document.createElement("span");
    if (cls) span.className = cls;
    span.textContent = text + " ";
    body.appendChild(span);
  };
  while (i < m || j < n) {
    if (i < m && j < n && a[i] === b[j]) { push(a[i]); i++; j++; }
    else if (j < n && (i === m || dp[i][j + 1] >= dp[i + 1][j])) { push(b[j], "diff-add"); j++; }
    else if (i < m) { push(a[i], "diff-del"); i++; }
  }
  out.appendChild(body);
  return out;
}

export class StoryPage {
  // v4 §17 — story pages render in the same left-docked sliding pane as
  // country/wiki pages (one panel component, distinguished by template),
  // with the pane's navigation stack: event -> linked country -> back.
  constructor(pane, { onOpenStory, onWatch, onOpenLineage, onPanTo, onOpenEntity } = {}) {
    this.pane = pane;
    this.onOpenStory = onOpenStory || (() => {});
    this.onWatch = onWatch || (() => {});
    this.onOpenLineage = onOpenLineage || (() => {});   // v3 §8
    this.onPanTo = onPanTo || null;                     // v6.6.8 pan to event
    this.onOpenEntity = onOpenEntity || null;           // v7.4.1 impacted chips
  }

  close() { this.pane.close(); }

  async open(storyId, { syntheticStory = null } = {}) {
    await this.pane.push({
      key: `story:${storyId}`,
      title: "story",
      targetType: "story",
      targetId: storyId,
      render: async (el) => {
        const story = syntheticStory || await api.story(storyId);
        this._render(story, el);
        this.pane.host.querySelector(".pane-title").textContent =
          (story.headline || "story").slice(0, 60);
      },
    });
  }

  _render(s, host) {
    const page = document.createElement("div");
    page.className = "story-page story-in-pane";
    const conf = s.confidence || "low";
    const n = s.causal_narrative;

    page.innerHTML = `
      <div class="close-row">
        <span class="conf conf-${conf}">confidence: ${conf}</span>
      </div>
      <h1></h1>
      <div class="impacted-row"></div>
      <div class="corroboration-banner"></div>
      <ul class="summary-bullets"></ul>
      <div class="full-summary-row">
        <button class="full-summary-btn">≡ full summary</button>
        <button class="full-summary-btn pan-to-event" hidden>⌖ pan to event</button>
        <p class="summary hidden"></p></div>
      <div class="read-more-row"><button class="read-more-btn">☰ read more — deeper synthesis</button>
        <div class="deep-summary hidden"></div></div>
      <div class="v3-toprow">
        <span class="feedback-row">was this really the same story?
          <button class="fb-up" title="yes — correctly linked">👍</button>
          <button class="fb-down" title="no — wrongly linked">👎</button></span>
        <span class="tag-suggest hidden"></span>
      </div>
      <section class="sec-narrative"><h4>Causal storyline</h4><div class="narrative-grid"></div>
        <div class="counter-reading hidden"></div></section>
      <section class="sec-debate hidden"><h4>The debate — three analysts, same evidence
        <span class="disagreement-badge"></span></h4><div class="debate-cols"></div></section>
      <section class="sec-forecasts hidden"><h4>Forward forecasts — tracked & graded</h4>
        <div class="fcasts"></div></section>
      <section class="sec-predictions"><h4>Prediction scorecard — AI gets graded</h4><div class="preds"></div></section>
      <section class="sec-versions hidden"><h4>How this analysis evolved</h4><div class="vers"></div></section>
      <section class="sec-timeline"><h4>Timeline — which source lit up when</h4><div class="tl"></div></section>
      <section class="sec-history"><h4>Connected history — fact chain</h4><div class="hist"></div></section>
      <section class="sec-secondorder"><h4>Possibly connected — shared root cause</h4><div class="so"></div></section>
      <section class="sec-bias"><h4>Bias / blindspot view</h4><div class="bias-cols"></div></section>
      <section class="sec-trace"><h4>Why these were grouped — reasoning trace</h4>
        <button class="trace-btn">show the correlation engine's work</button>
        <div class="trace-body hidden"></div></section>
      <section class="sec-sources"><h4>All sources</h4><div class="srcs"></div></section>
      <div class="watch-row">
        <button class="watch-cat">☆ watch category</button>
        <button class="watch-region">☆ watch region</button>
      </div>`;

    page.querySelector("h1").textContent = s.headline || "(untitled story)";
    // v7.4.1 — impacted entities at the TOP: clickable chips for the countries,
    // blocs, NSAs and zones this story touches (owner request).
    const impactedRow = page.querySelector(".impacted-row");
    const impacted = s.impacted || [];
    if (impacted.length && this.onOpenEntity) {
      const icon = { country: "🏳", territory: "🏝", alliance: "🤝",
                     non_state_actor: "⚑", zone: "⚑" };
      impactedRow.innerHTML = `<span class="impacted-label">Impacts:</span> ` +
        impacted.map((e) =>
          `<button class="ap-chip impacted-chip" data-type="${e.type}" data-id="${(e.id + "").replace(/"/g, "")}">${icon[e.type] || "•"} ${(e.name || "").replace(/</g, "&lt;")}</button>`).join(" ");
      impactedRow.querySelectorAll(".impacted-chip").forEach((b) =>
        b.addEventListener("click", () => this.onOpenEntity(b.dataset.type, b.dataset.id)));
    } else {
      impactedRow.remove();
    }
    // v6 §3 — two densities of the SAME synthesis: digestible bullets by
    // default (sentence-split from the stored summary + causal consequences),
    // with the fuller prose behind the 'full summary' expand — never two
    // different generations
    page.querySelector(".summary").textContent = s.summary || "";
    const bulletsEl = page.querySelector(".summary-bullets");
    const sentences = (s.summary || "").match(/[^.!?]+[.!?]+/g) || [];
    const bullets = sentences.map((x) => x.trim()).filter((x) => x.length > 8);
    for (const cons of ((n && n.consequences) || []).slice(0, 3)) {
      if (!bullets.some((b) => b.includes(cons.slice(0, 30)))) {
        bullets.push("Likely consequence: " + cons.replace(/\.?$/, "."));
      }
    }
    for (const b of bullets.slice(0, 6)) {
      const li = document.createElement("li");
      li.textContent = b;
      bulletsEl.appendChild(li);
    }
    if (!bullets.length) bulletsEl.classList.add("hidden");
    // v6.6 — 'full summary' now forces an EXPANDED AI regeneration (more
    // bullets, headers, every thread covered) replacing the quick synthesis
    page.querySelector(".full-summary-btn").addEventListener("click", async (ev) => {
      const out = page.querySelector(".deep-summary");
      out.classList.remove("hidden");
      ev.target.disabled = true; ev.target.textContent = "≡ expanding…";
      const res = await api.deepSummary(s.id, true).catch((e) => ({ error: e.message }));
      ev.target.disabled = false; ev.target.textContent = "≡ full summary";
      if (res.deep_summary) { out.innerHTML = bulletsToHtml(res.deep_summary); s.deep_summary = res.deep_summary; }
    });

    // v4 §11.2 — 'read more': deeper synthesis generated on demand, cached
    const rmBtn = page.querySelector(".read-more-btn");
    rmBtn.addEventListener("click", async () => {
      const out = page.querySelector(".deep-summary");
      if (!out.classList.contains("hidden")) { out.classList.add("hidden"); return; }
      out.classList.remove("hidden");
      // v6.2 — the deep synthesis is now big-picture markdown bullets; render
      // them as an actual list, not a wall of text.
      if (s.deep_summary) { out.innerHTML = bulletsToHtml(s.deep_summary); return; }
      out.textContent = "synthesizing…";
      const res = await api.deepSummary(s.id).catch((e) => ({ error: e.message }));
      if (res.deep_summary) {
        out.innerHTML = bulletsToHtml(res.deep_summary);
        s.deep_summary = res.deep_summary;
      } else { out.textContent = res.note || res.error || "unavailable"; }
    });

    // v4 §20 — reasoning trace: which threshold fired, actual similarity,
    // same-window vs historical-chain, plus the debate disagreement score
    // v6.6.8 — story-page text is translated by the site-wide DOM translator
    // (translation scrapped in v7; owner will architect a replacement).
    // v6.6 — deep synthesis auto-generates the moment the story opens
    setTimeout(() => { try { rmBtn.click(); } catch {} }, 60);
    page.querySelector(".trace-btn").addEventListener("click", async (ev) => {
      const body = page.querySelector(".trace-body");
      body.classList.toggle("hidden");
      if (!body.classList.contains("hidden") && !body.dataset.loaded) {
        body.innerHTML = '<p class="cp-meta">loading trace…</p>';
        try {
          const t = await api.storyTrace(s.id);
          body.dataset.loaded = "1";
          const rows = (t.members || []).map((m) => `
            <div class="trace-row">
              <span class="via-${m.linked_via}">${m.linked_via === "historical_chain" ? "⛓" : "◆"}</span>
              <span class="trace-title">${(m.title || "(fact-only member)").replace(/</g, "&lt;")}</span>
              <span class="cp-meta">${m.linked_via.replace("_", " ")}${
                m.similarity_to_previous != null
                  ? ` · cos ${m.similarity_to_previous} vs "${(m.compared_with || "").slice(0, 36).replace(/</g, "&lt;")}…"`
                  : ""}</span>
            </div>`).join("");
          body.innerHTML = `
            <p class="cp-meta">category <b>${t.category}</b> · thresholds in force:
              same-window ≥ <b>${t.thresholds.same_window}</b>,
              historical chain ≥ <b>${t.thresholds.historical_chain}</b>
              (+${t.thresholds.entity_overlap_boost} shared-entity boost) ·
              embedder <b>${t.embedder}</b>${t.disagreement_score != null
                ? ` · analyst disagreement ${(t.disagreement_score * 100).toFixed(0)}%` : ""}</p>
            ${rows}<p class="cp-meta">${t.note}</p>`;
        } catch (err) {
          body.innerHTML = `<p class="cp-meta">trace unavailable: ${err.message}</p>`;
        }
      }
    });

    // v7.1 §5 — ground-truth corroboration: text + physical sensors agreeing
    const cbanner = page.querySelector(".corroboration-banner");
    const esc = (t) => String(t ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    if (s.corroboration && cbanner) {
      let det = s.corroboration_detail;
      if (typeof det === "string") { try { det = JSON.parse(det); } catch { det = null; } }
      const pct = Math.round(s.corroboration * 100);
      const types = (det?.sensor_types || []).map((t) => ({
        firms: "🔥 thermal", opensky: "✈ air-traffic", usgs: "地 seismic",
        acled: "⚔ ACLED" }[t] || t)).join(" · ");
      const hits = (det?.hits || []).slice(0, 4).map((h) =>
        `<li>${esc(h.title || h.type)} <span class="cp-meta">(${esc(h.type)}, ${h.km} km away)</span></li>`).join("");
      cbanner.innerHTML = `
        <div class="corrob-head">📡 <b>Corroborated ${pct}%</b>
          <span class="cp-meta">physical sensors agree with the reporting</span></div>
        ${types ? `<p class="cp-meta">signals: ${types}</p>` : ""}
        ${hits ? `<ul class="corrob-hits">${hits}</ul>` : ""}
        <p class="cp-meta">A story earns corroboration when tracked physical-sensor
          events (thermal/air-traffic/seismic/ACLED) coincide in space and time
          with what the text reports — text alone can be wrong; physics is harder.</p>`;
    }

    // causal narrative
    const grid = page.querySelector(".narrative-grid");
    if (n && typeof n === "object") {
      grid.innerHTML = `
        <div class="narrative-box cause"><b>Likely cause</b><span></span></div>
        <div class="narrative-box affected"><b>Affected</b><ul></ul></div>
        <div class="narrative-box conseq" style="grid-column:1/-1"><b>Likely consequences</b><ul></ul></div>`;
      grid.querySelector(".cause span").textContent = n.cause || "—";
      for (const a of n.affected || []) {
        const li = document.createElement("li"); li.textContent = a;
        grid.querySelector(".affected ul").appendChild(li);
      }
      for (const c of n.consequences || []) {
        const li = document.createElement("li"); li.textContent = c;
        grid.querySelector(".conseq ul").appendChild(li);
      }
    } else {
      // v6.1 — message reflects the ACTUAL provider state (ai_available from
      // /api/config), not a hardcoded Anthropic-era string. With Groq (or any
      // key) configured, the narrative is simply still being generated for
      // this cluster; without one, tell the user how to enable it.
      const aiOn = !!(window.__gg && window.__gg.state
        && window.__gg.state.clientConfig
        && window.__gg.state.clientConfig.ai_available);
      grid.innerHTML = '<div class="narrative-box" style="grid-column:1/-1">' +
        (aiOn
          ? "Causal storyline is being generated for this cluster — it appears "
            + "once the AI has correlated enough of its members. Check back in a "
            + "moment, or add more coverage to speed it up."
          : "Causal storylines are AI-generated. Add a free AI key "
            + "(Groq recommended — console.groq.com/keys) in Settings to enable "
            + "them.") + "</div>";
    }

    // v3 §5 — correlation feedback thumbs
    page.querySelector(".fb-up").addEventListener("click", async (ev) => {
      await api.storyFeedback(s.id, "correct");
      ev.target.parentElement.innerHTML = "✓ thanks — feeds threshold tuning";
    });
    page.querySelector(".fb-down").addEventListener("click", async (ev) => {
      await api.storyFeedback(s.id, "incorrect");
      ev.target.parentElement.innerHTML = "✓ noted — thresholds will tighten";
    });

    // v3 §15 — suggested conflict tag confirm step
    if (s.suggested_conflict) {
      const el = page.querySelector(".tag-suggest");
      el.classList.remove("hidden");
      el.innerHTML = `suggested: part of <b></b> `;
      el.querySelector("b").textContent = s.suggested_conflict.name;
      const yes = document.createElement("button");
      yes.textContent = "confirm";
      const no = document.createElement("button");
      no.textContent = "dismiss";
      yes.addEventListener("click", async () => {
        await api.confirmConflictTag(s.id, true);
        el.innerHTML = `✓ tagged: ${s.suggested_conflict.name}`;
      });
      no.addEventListener("click", async () => {
        await api.confirmConflictTag(s.id, false);
        el.remove();
      });
      el.append(yes, no);
    }

    // v3 §3 — the counter-reading, plainly labeled, right under the narrative
    if (s.counter_argument) {
      const cr = page.querySelector(".counter-reading");
      cr.classList.remove("hidden");
      const downgraded = s.confidence_pre_devil_advocate
        ? ` <span class="cp-meta">(confidence lowered from ${s.confidence_pre_devil_advocate}` +
          ` by this challenge)</span>` : "";
      cr.innerHTML = `<b>A counter-reading:</b> <span></span>${downgraded}`;
      cr.querySelector("span").textContent = s.counter_argument;
    }

    // v3 §2 — the debate: three personas, same evidence
    const debate = s.debate || {};
    if (Object.keys(debate).length >= 2) {
      page.querySelector(".sec-debate").classList.remove("hidden");
      const badge = page.querySelector(".disagreement-badge");
      if (s.disagreement_score != null) {
        const high = s.disagreement_score >= 0.35;
        badge.className = "disagreement-badge " + (high ? "dis-high" : "dis-low");
        badge.textContent = high
          ? `⚡ analysts disagree (${(s.disagreement_score * 100).toFixed(0)}%)`
          : `analysts broadly agree (${(s.disagreement_score * 100).toFixed(0)}% divergence)`;
      }
      const cols = page.querySelector(".debate-cols");
      const ICONS = { skeptic: "🔍", historian: "📜", optimist: "🌅" };
      for (const persona of ["skeptic", "historian", "optimist"]) {
        const n = debate[persona];
        if (!n) continue;
        const col = document.createElement("div");
        col.className = "debate-col";
        col.innerHTML = `<h5>${ICONS[persona] || ""} ${persona}
          <span class="conf conf-${n.confidence}">${n.confidence}</span></h5><p></p>`;
        col.querySelector("p").textContent = n.cause;
        cols.appendChild(col);
      }
    }

    // v3 §7 — forecasts never render without their track record
    if (s.forecasts && s.forecasts.items.length) {
      page.querySelector(".sec-forecasts").classList.remove("hidden");
      const el = page.querySelector(".fcasts");
      const acc = s.forecasts.accuracy;
      const record = acc.directionally_correct_pct != null
        ? `this system's forecasts have been directionally correct ` +
          `${acc.directionally_correct_pct}% of the time, based on ` +
          `${acc.resolved_forecasts} resolved forecasts`
        : `no resolved forecast history yet (${acc.resolved_forecasts} graded) — ` +
          `treat with corresponding caution`;
      el.innerHTML = `<p class="cp-meta">Track record: ${record}.</p>`;
      for (const f of s.forecasts.items) {
        const div = document.createElement("div");
        div.className = "pred-item pred-" + f.status;
        div.innerHTML = `<span class="pred-status">${f.status}</span>
          <span></span><span class="cp-meta" style="margin-left:auto">` +
          `${f.horizon_hours || "?"}h · ${f.region || ""}</span>`;
        div.querySelector("span:nth-child(2)").textContent = f.consequence_text;
        el.appendChild(div);
      }
    }

    // v3 §12 — version history with word-level diff
    if ((s.versions || []).length) {
      page.querySelector(".sec-versions").classList.remove("hidden");
      const el = page.querySelector(".vers");
      const current = s.causal_narrative;
      s.versions.forEach((v, i) => {
        const div = document.createElement("div");
        div.className = "version-item";
        const label = `superseded ${(v.superseded_at || "").slice(0, 16).replace("T", " ")}` +
          ` · was ${v.confidence}`;
        div.innerHTML = `<button class="ver-toggle">v-${i + 1} · ${label}</button>
          <div class="ver-diff hidden"></div>`;
        div.querySelector(".ver-toggle").addEventListener("click", () => {
          const body = div.querySelector(".ver-diff");
          body.classList.toggle("hidden");
          if (!body.innerHTML && v.causal_narrative && current) {
            body.appendChild(diffBlock("cause", v.causal_narrative.cause, current.cause));
            body.appendChild(diffBlock("consequences",
              (v.causal_narrative.consequences || []).join("; "),
              (current.consequences || []).join("; ")));
          } else if (!body.innerHTML) {
            body.textContent = "no comparable narrative content";
          }
        });
        el.appendChild(div);
      });
    }

    // prediction scorecard (§3.4)
    const preds = page.querySelector(".preds");
    for (const p of s.predictions || []) {
      const div = document.createElement("div");
      div.className = "pred-item pred-" + p.status;
      const icon = p.status === "confirmed" ? "✔" : p.status === "refuted" ? "✘" : "…";
      div.innerHTML = `<span class="pred-status">${icon} ${p.status}</span> <span></span>`;
      div.querySelector("span:last-child").textContent = p.consequence_text;
      preds.appendChild(div);
    }
    if (!(s.predictions || []).length) {
      preds.innerHTML = '<p style="color:var(--text-dim)">No predictions logged yet — '
        + "they appear when the causal storyline states consequences.</p>";
    }

    // timeline
    const tl = page.querySelector(".tl");
    for (const m of s.members || []) {
      const item = document.createElement("div");
      item.className = "timeline-item";
      const when = (m.occurred_at || "").replace("T", " ").replace("Z", " UTC");
      const official = m.source?.kind === "official"
        ? ' <span class="chip chip-official">official</span>' : "";
      const dup = m.is_duplicate ? ' <span class="cp-meta">(wire copy)</span>' : "";
      item.innerHTML = `<time>${when}</time>
        <span class="via-${m.linked_via}" title="${m.linked_via}">${m.linked_via === "historical_chain" ? "⛓" : "◆"}</span>
        <span class="tl-body"></span>`;
      const body = item.querySelector(".tl-body");
      body.textContent = `${m.source?.name || "?"} — ${m.title}`;
      body.insertAdjacentHTML("beforeend", official + dup);
      if (m.source?.article_link) {
        const a = document.createElement("a");
        a.href = m.source.article_link; a.target = "_blank"; a.rel = "noopener";
        a.textContent = " ↗"; body.appendChild(a);
      }
      tl.appendChild(item);
    }
    if (!(s.members || []).length) tl.innerHTML = '<p style="color:var(--text-dim)">no member events</p>';

    // connected history (the surfaced fact chain — Section 5.3)
    const hist = page.querySelector(".hist");
    for (const f of s.connected_history || []) {
      const div = document.createElement("div");
      div.className = "history-item";
      div.innerHTML = `<b></b> <span></span>
        <button class="ap-chip lineage-btn" title="everything this fact fed into">🦋 lineage</button>
        <br><small style="color:var(--text-dim)"></small>`;
      div.querySelector("b").textContent = f.who;
      div.querySelector("span").textContent = `${f.what} (${f.where || "n/a"})`;
      div.querySelector("small").textContent =
        `${(f.when_occurred || "").slice(0, 16).replace("T", " ")} · ${f.source?.name || ""} · linked ${(f.linked_at || "").slice(0, 16).replace("T", " ")}`;
      div.querySelector(".lineage-btn").addEventListener("click",
        () => this.onOpenLineage(f.id));   // v3 §8
      hist.appendChild(div);
    }
    if (!(s.connected_history || []).length) {
      hist.innerHTML = '<p style="color:var(--text-dim)">No long-horizon links yet — this cluster is same-window only.</p>';
    }

    // second-order links (§3.7)
    const so = page.querySelector(".so");
    for (const link of s.second_order_links || []) {
      const div = document.createElement("div");
      div.className = "history-item";
      const n = link.narrative || {};
      div.innerHTML = `<b class="so-headline" style="cursor:pointer"></b>
        <span class="conf conf-${link.confidence}"> ${link.confidence}</span><br>
        <span class="so-cause"></span>`;
      div.querySelector(".so-headline").textContent = "↔ " + (link.other_headline || "related cluster");
      div.querySelector(".so-cause").textContent = n.common_cause || "";
      div.querySelector(".so-headline").addEventListener("click",
        () => this.onOpenStory(link.other_story_id));
      so.appendChild(div);
    }
    if (!(s.second_order_links || []).length) {
      page.querySelector(".sec-secondorder").style.display = "none";
    }

    // bias view (v2 §3.5: computed tone alongside the static label)
    const bias = page.querySelector(".bias-cols");
    const groups = s.bias_view || { left: [], center: [], right: [] };
    const toneLabel = (v) => v == null ? "" :
      v > 0.15 ? "tone +" : v < -0.15 ? "tone −" : "tone ·";
    for (const leaning of ["left", "center", "right"]) {
      const col = document.createElement("div");
      col.className = "bias-col";
      col.innerHTML = `<h5>${leaning}</h5>`;
      for (const item of groups[leaning] || []) {
        const d = document.createElement("div");
        d.className = "bias-item";
        d.innerHTML = `<b></b> <span class="cp-meta tone"></span><br><span></span>`;
        d.querySelector("b").textContent = item.outlet;
        d.querySelector(".tone").textContent = toneLabel(item.sentiment);
        d.querySelector("span:last-child").textContent = item.headline;
        col.appendChild(d);
      }
      if (!(groups[leaning] || []).length) {
        col.innerHTML += '<div class="bias-item" style="color:var(--text-dim)">no coverage</div>';
      }
      bias.appendChild(col);
    }

    // sources (attribution always visible — Section 6.8; v5 §21 reliability tier)
    const srcs = page.querySelector(".srcs");
    for (const src of s.sources || []) {
      const row = document.createElement("div");
      row.className = "source-row";
      const tier = src.reliability_tier || "medium";
      row.innerHTML = `<span class="leaning">${src.leaning || "n/a"}</span>`
        + `<span class="cite-tier tier-${tier}" title="source reliability tier">${tier}</span> <b></b> `;
      row.querySelector("b").textContent = src.name;
      const a = document.createElement("a");
      a.href = src.article_link || src.url; a.target = "_blank"; a.rel = "noopener";
      a.textContent = src.article_link ? "article ↗" : "source ↗";
      row.appendChild(a);
      srcs.appendChild(row);
    }

    // v6.6.8 — Pan to Event: styled like the full-summary button and sitting
    // next to it; flies the map to the story's first located member event. The
    // old per-summary "translate" feature is deleted (the whole site now
    // translates via the DOM translator).
    const panBtn = page.querySelector(".pan-to-event");
    const ev0 = (s.members || []).find((m) => m.location_lat != null && m.location_lon != null);
    if (panBtn && ev0 && this.onPanTo) {
      panBtn.hidden = false;
      panBtn.addEventListener("click", () =>
        this.onPanTo(ev0.location_lat, ev0.location_lon));
    }

    // §6.2 quick-pin watch buttons
    page.querySelector(".watch-cat").addEventListener("click", async (ev) => {
      await api.watchlistAdd("category", s.category || "other");
      ev.target.textContent = "★ watching category";
      this.onWatch();
    });
    const region = (s.members || []).map((m) => m.location_name).find(Boolean);
    const regionBtn = page.querySelector(".watch-region");
    if (region) {
      regionBtn.addEventListener("click", async (ev) => {
        await api.watchlistAdd("region", region);
        ev.target.textContent = `★ watching ${region}`;
        this.onWatch();
      });
    } else regionBtn.style.display = "none";

    host.innerHTML = "";
    host.appendChild(page);
  }
}
