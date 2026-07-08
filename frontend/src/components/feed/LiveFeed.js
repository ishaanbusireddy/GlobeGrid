// Section 5.1 — live feed: story clusters (never raw articles), one card
// per correlated event with a source-count badge, updated via WebSocket
// push with the Section 8.2 polling fallback handled in api/socket.js.
import { formatDateTime } from "../../data/timefmt.js";   // v6.1.1 tz-aware

export class LiveFeed {
  constructor(listEl, { onOpenStory, onOpenConflict } = {}) {
    this.listEl = listEl;
    this.onOpenStory = onOpenStory || (() => {});
    this.onOpenConflict = onOpenConflict || (() => {});   // v6.6.2 conflict chip
    this.stories = new Map(); // id -> story card data
  }

  setStories(stories, { force = false } = {}) {
    // v6.6.4 — BLOCKING MECHANISM: never wipe a populated feed with an empty
    // list (owner: "no map/view mode should EVER clear the live feed"). A mode
    // toggle whose fetch momentarily returns nothing must not blank the feed.
    // Explicit resets (war-mode restore, category change) pass force:true.
    if (!force && (!stories || stories.length === 0) && this.stories.size > 0) {
      return;
    }
    this.stories.clear();
    for (const s of stories) this.stories.set(s.id, s);
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

  _render(flashId = null) {
    const sorted = [...this.stories.values()].sort(
      (a, b) => (b.last_updated_at || "").localeCompare(a.last_updated_at || ""));
    this.listEl.innerHTML = "";
    for (const s of sorted.slice(0, 100)) {
      const card = document.createElement("div");
      card.className = "story-card" + (s.id === flashId ? " flash" : "");
      const conf = s.confidence || "low";
      const when = formatDateTime(s.last_updated_at);   // v6.1.1 tz-aware
      card.innerHTML = `
        <h3></h3>
        <div class="card-meta">
          <span class="chip cat-${s.category || "other"}">${s.category || "other"}</span>
          <span class="badge-src">${s.source_count || 0} src · ${s.member_count || 0} ev</span>
          <span class="conf conf-${conf}">${conf}</span>
          ${s.has_historical_link ? '<span class="badge-chain" title="linked to the historical fact chain">⛓ chain</span>' : ""}
          ${s.conflict_id && s.conflict_name ? `<span class="chip chip-conflict" data-cid="${s.conflict_id}" title="part of this conflict — open War Mode">⚔ ${s.conflict_name}</span>` : ""}
          <span>${when}</span>
        </div>`;
      card.querySelector("h3").textContent = s.headline || "(untitled story)";
      // v6.6.2 — the conflict chip opens the conflict; don't also open the story
      const cchip = card.querySelector(".chip-conflict");
      if (cchip) cchip.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this.onOpenConflict(cchip.dataset.cid);
      });
      card.addEventListener("click", () => this.onOpenStory(s.id));
      this.listEl.appendChild(card);
    }
    if (!sorted.length) {
      this.listEl.innerHTML =
        '<p style="color:var(--text-dim);font-size:13px">No stories yet. ' +
        "Stories appear when the correlation engine links events from ingested sources " +
        "(first links typically form within a few minutes of startup).</p>";
    }
  }
}
