// Section 5.1 — live feed: story clusters (never raw articles), one card
// per correlated event with a source-count badge, updated via WebSocket
// push with the Section 8.2 polling fallback handled in api/socket.js.
import { formatDateTime } from "../../data/timefmt.js";   // v6.1.1 tz-aware

export class LiveFeed {
  constructor(listEl, { onOpenStory, onOpenConflict, onOpenCountry } = {}) {
    this.listEl = listEl;
    this.onOpenStory = onOpenStory || (() => {});
    this.onOpenConflict = onOpenConflict || (() => {});   // v6.6.2 conflict chip
    this.onOpenCountry = onOpenCountry || (() => {});     // v8.16 impact chips
    this.stories = new Map(); // id -> story card data
    this._order = [];         // v8.16 — stable display order (new ids on TOP)
  }

  setStories(stories, { force = false } = {}) {
    // v6.6.4 — BLOCKING MECHANISM: never wipe a populated feed with an empty
    // list (owner: "no map/view mode should EVER clear the live feed"). A mode
    // toggle whose fetch momentarily returns nothing must not blank the feed.
    // Explicit resets (war-mode restore, category change) pass force:true.
    if (!force && (!stories || stories.length === 0) && this.stories.size > 0) {
      return;
    }
    const wasEmpty = this.stories.size === 0;
    this.stories.clear();
    for (const s of stories) this.stories.set(s.id, s);
    // v8.16 — only a FIRST fill (or forced reset) re-sorts by recency; a
    // periodic refresh keeps the on-screen order so cards never jump around
    // mid-list — genuinely new ids still pile in from the top via _render.
    if (wasEmpty || force || !this._order || this._order.length === 0) {
      this._order = [...this.stories.values()]
        .sort((a, b) => (b.last_updated_at || "").localeCompare(a.last_updated_at || ""))
        .map((s) => s.id);
    }
    this._render();
  }

  // v6.6.2 — a real snapshot of the current cards (full objects), so War Mode
  // can restore the exact accumulated feed on exit instead of re-fetching.
  snapshot() { return [...this.stories.values()]; }

  upsert(story, { flash = true } = {}) {
    this.stories.delete(story.id);
    this.stories.set(story.id, story);
    this._render(flash ? story.id : null);
  }

  // v8.13 — INCREMENTAL render (owner: "the live feed shouldnt flash/refresh the
  // whole thing every update"). The old path wiped `innerHTML` and rebuilt every
  // card on each push, so the entire list flickered (and flags/badges reloaded)
  // on every arrival. Now cards are reconciled: existing elements are reused +
  // reordered (appendChild MOVES a node, no re-create), only changed cards are
  // rewritten, and departed cards removed. Unchanged cards never touch the DOM.
  _cardKey(s) {
    // a signature of everything the card renders — cheap change detection
    return [s.headline, s.category, s.source_count, s.member_count, s.confidence,
            s.has_historical_link ? 1 : 0, Math.round((s.corroboration || 0) * 100),
            s.conflict_id || "", s.conflict_name || "", s.last_updated_at,
            (s.impact_chips || []).map((c) => c.name).join(",")].join("|");
  }
  _buildCard(s) {
    const card = document.createElement("div");
    card.dataset.id = s.id;
    const conf = s.confidence || "low";
    const when = formatDateTime(s.last_updated_at);   // v6.1.1 tz-aware
    card.className = "story-card";
    card.innerHTML = `
      <h3></h3>
      <div class="card-meta">
        <span class="chip cat-${s.category || "other"}">${s.category || "other"}</span>
        <span class="badge-src">${s.source_count || 0} src · ${s.member_count || 0} ev</span>
        <span class="conf conf-${conf}">${conf}</span>
        ${s.has_historical_link ? '<span class="badge-chain" title="linked to the historical fact chain">⛓ chain</span>' : ""}
        ${s.corroboration ? `<span class="badge-corrob" title="corroborated by physical sensors (thermal/air-traffic/seismic) agreeing with the reporting — score ${Math.round(s.corroboration * 100)}%">📡 corroborated ${Math.round(s.corroboration * 100)}%</span>` : ""}
        ${s.conflict_id && s.conflict_name ? `<span class="chip chip-conflict" data-cid="${s.conflict_id}" title="part of this conflict — open War Mode">⚔ ${s.conflict_name}</span>` : ""}
        <span>${when}</span>
      </div>`;
    card.querySelector("h3").textContent = s.headline || "(untitled story)";
    // v8.16 — 1-2 literally-named country/bloc chips with real flags (owner:
    // "display like 1-2 country chips nested in the event panels in the live
    // feed"; a NATO chip flies the NATO flag just like a country's)
    if (s.impact_chips && s.impact_chips.length) {
      const meta = card.querySelector(".card-meta");
      for (const ch of s.impact_chips.slice(0, 2)) {
        const chip = document.createElement("span");
        chip.className = "chip chip-impact";
        chip.title = ch.name;
        if (ch.flag) {
          const img = document.createElement("img");
          img.src = ch.flag; img.alt = ""; img.className = "chip-flag";
          img.addEventListener("error", () => img.remove());
          chip.appendChild(img);
        }
        chip.appendChild(document.createTextNode(ch.name));
        chip.addEventListener("click", (ev) => {
          ev.stopPropagation();
          this.onOpenCountry(ch);
        });
        meta.insertBefore(chip, meta.firstChild);
      }
    }
    const cchip = card.querySelector(".chip-conflict");
    if (cchip) cchip.addEventListener("click", (ev) => {
      ev.stopPropagation();
      this.onOpenConflict(cchip.dataset.cid);
    });
    card.addEventListener("click", () => this.onOpenStory(s.id));
    return card;
  }
  _render(flashId = null) {
    // v8.16 — STABLE top-pile ordering (owner: "new events in the live feed
    // should pile in from the TOP fluidly … not be glitchy or move around").
    // A card the feed has never shown enters at the TOP; every card already
    // on screen KEEPS its position (an update pulses in place, it does not
    // re-sort the list) — so nothing ever jumps into the middle. Only a full
    // reset (setStories clears _order) re-sorts by recency.
    if (!this._order) this._order = [];
    const have = new Set(this._order);
    const incoming = [...this.stories.values()]
      .filter((s) => !have.has(s.id))
      .sort((a, b) => (a.last_updated_at || "").localeCompare(b.last_updated_at || ""));
    for (const s of incoming) this._order.unshift(s.id);   // newest ends on top
    this._order = this._order.filter((id) => this.stories.has(id));
    const sorted = this._order.map((id) => this.stories.get(id)).slice(0, 100);
    if (!this._cards) this._cards = new Map();   // id -> {el, key}
    if (!sorted.length) {
      this._cards.clear();
      this.listEl.innerHTML =
        '<p style="color:var(--text-dim);font-size:13px">No stories yet. ' +
        "Stories appear when the correlation engine links events from ingested sources " +
        "(first links typically form within a few minutes of startup).</p>";
      return;
    }
    // if the empty-state placeholder is showing, clear it (no cards yet)
    const prevEmpty = this._cards.size === 0;
    if (prevEmpty) this.listEl.innerHTML = "";
    const wanted = new Set(sorted.map((s) => s.id));
    for (const [id, rec] of this._cards) {   // drop departed cards
      if (!wanted.has(id)) { rec.el.remove(); this._cards.delete(id); }
    }
    // v8.13.3 — cooler, more fluid streaming (owner: "stuff filling into it …
    // super cool moderately flashy"). A brand-new card slides+glows in
    // (`streaming-in`); on the first populate the whole list CASCADES with a
    // per-card stagger; an existing card whose content changed PULSES
    // (`flash`); unchanged cards never touch the DOM (no flicker). The old code
    // toggled a single flash on the pushed id — now the entrance IS the effect.
    let prev = null, newIndex = 0;
    for (const s of sorted) {
      const key = this._cardKey(s);
      let rec = this._cards.get(s.id);
      let isNew = false;
      if (!rec) {                          // new card
        rec = { el: this._buildCard(s), key };
        this._cards.set(s.id, rec);
        isNew = true;
      } else if (rec.key !== key) {        // changed → rebuild + pulse in place
        const fresh = this._buildCard(s);
        rec.el.replaceWith(fresh);
        rec.el = fresh; rec.key = key;
        fresh.classList.remove("flash"); void fresh.offsetWidth; fresh.classList.add("flash");
        setTimeout((el) => el.classList.remove("flash"), 1500, fresh);
      }
      // place in order (appendChild/insertBefore MOVES existing nodes, no flicker)
      const after = prev ? prev.nextSibling : this.listEl.firstChild;
      if (rec.el !== after) this.listEl.insertBefore(rec.el, after);
      if (isNew) {
        const el = rec.el;
        // cascade on first fill; a single slide-in for a live arrival
        el.style.animationDelay = prevEmpty ? Math.min(newIndex * 0.045, 0.6) + "s" : "0s";
        el.classList.remove("streaming-in"); void el.offsetWidth; el.classList.add("streaming-in");
        setTimeout((c) => { c.classList.remove("streaming-in"); c.style.animationDelay = ""; }, 1000, el);
        newIndex += 1;
      }
      prev = rec.el;
    }
  }
}
