// v4 §6/§17/§18 — the ONE left-docked sliding pane that serves country
// profiles, wiki pages, story pages, directories, settings, and compare
// view alike, distinguished only by content template. Real navigation
// stack (back returns to where you came from), prev/next arrows for
// wiki sequences, fullscreen toggle, a bookmark icon on every page, and
// the user's own annotations section (§19) rendered distinctly from AI
// content. All motion comes from the shared transition variables in
// styles.css (§18) and respects prefers-reduced-motion.
import { api } from "../../api/client.js";

export class SlidePane {
  constructor(hostEl, { durationMs = 300, onNavigate,
                        resizable = true, minWidth = 280, maxWidth = 900,
                        persist = true } = {}) {
    this.host = hostEl;
    this.onNavigate = onNavigate || (() => {});
    this.stack = [];           // [{key, title, targetType, targetId, sequence, render}]
    this.directory = null;     // /api/wiki/directory cache for prev/next
    this.reduced = window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.duration = this.reduced ? 0 : durationMs;
    this.minWidth = minWidth; this.maxWidth = maxWidth;   // v5 §10
    this.persist = persist;
    document.documentElement.style.setProperty("--pane-ms", this.duration + "ms");

    this.host.innerHTML = `
      <div class="pane-chrome">
        <button class="pane-back" title="back">←</button>
        <button class="pane-prev hidden" title="previous entry">⟨</button>
        <button class="pane-next hidden" title="next entry">⟩</button>
        <span class="pane-title"></span>
        <button class="pane-bookmark hidden" title="bookmark this page">☆</button>
        <button class="pane-full" title="fullscreen">⛶</button>
        <button class="pane-close" title="close">✕</button>
      </div>
      <div class="pane-content"></div>
      ${resizable ? '<div class="pane-resize" title="drag to resize"></div>' : ""}`;
    this.contentEl = this.host.querySelector(".pane-content");
    this.host.querySelector(".pane-back").addEventListener("click", () => this.back());
    this.host.querySelector(".pane-close").addEventListener("click", () => this.close());
    this.host.querySelector(".pane-full").addEventListener("click", () =>
      this.host.classList.toggle("pane-fullscreen"));
    this.host.querySelector(".pane-prev").addEventListener("click", () => this._step(-1));
    this.host.querySelector(".pane-next").addEventListener("click", () => this._step(1));
    this.host.querySelector(".pane-bookmark").addEventListener("click", () =>
      this._toggleBookmark());
    // v5 §10 — drag-resize handle on the inner edge, width persisted so it
    // doesn't reset every session; clamped to min/max (fullscreen is a
    // separate toggle for going full-width, v4 §6.2)
    const savedW = persist && parseInt(localStorage.getItem("tdl_pane_width") || "", 10);
    this.width = savedW && savedW >= minWidth && savedW <= maxWidth ? savedW : 480;
    document.documentElement.style.setProperty("--pane-width", this.width + "px");
    if (resizable) this._initResize(this.host.querySelector(".pane-resize"));
  }

  _initResize(handle) {
    let startX = 0, startW = 0, dragging = false;
    const onMove = (ev) => {
      if (!dragging) return;
      const w = Math.max(this.minWidth, Math.min(this.maxWidth,
        startW + (ev.clientX - startX)));
      this.width = w;
      document.documentElement.style.setProperty("--pane-width", w + "px");
    };
    const onUp = () => {
      if (!dragging) return;
      dragging = false;
      document.body.style.userSelect = "";
      this.host.classList.remove("pane-resizing");
      if (this.persist) localStorage.setItem("tdl_pane_width", String(this.width));
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    handle.addEventListener("pointerdown", (ev) => {
      dragging = true; startX = ev.clientX; startW = this.host.offsetWidth;
      document.body.style.userSelect = "none";
      this.host.classList.add("pane-resizing");
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
    });
  }

  async _dir() {
    if (!this.directory) {
      this.directory = await api.wikiDirectory().catch(() => ({}));
    }
    return this.directory;
  }

  isOpen() { return this.host.classList.contains("pane-open"); }

  top() { return this.stack[this.stack.length - 1] || null; }

  async push(entry, { replace = false } = {}) {
    if (replace && this.stack.length) this.stack.pop();
    this.stack.push(entry);
    if (!this.isOpen()) {
      this.host.classList.add("pane-open");   // slide in from the dock edge
    }
    await this._renderTop({ animate: !replace });
    this.onNavigate(entry);
  }

  async back() {
    if (this.stack.length <= 1) { this.close(); return; }
    this.stack.pop();
    await this._renderTop({ animate: true, reverse: true });
  }

  close() {
    this.stack = [];
    this.host.classList.remove("pane-open", "pane-fullscreen");
    this.contentEl.innerHTML = "";
    this.onNavigate(null);   // §16.2 — closing the pane clears focus context
  }

  async _renderTop({ animate = true, reverse = false } = {}) {
    const entry = this.top();
    if (!entry) return;
    const chromeTitle = this.host.querySelector(".pane-title");
    chromeTitle.textContent = entry.title || "";
    // §18 — content cross-fades a short distance; the shell stays put
    if (animate && this.duration) {
      this.contentEl.classList.remove("pane-anim-in", "pane-anim-back");
      void this.contentEl.offsetWidth;   // restart animation
      this.contentEl.classList.add(reverse ? "pane-anim-back" : "pane-anim-in");
    }
    this.contentEl.innerHTML = '<p class="cp-meta pane-loading">loading…</p>';
    this.contentEl.scrollTop = 0;
    const el = document.createElement("div");
    el.className = "pane-page";
    try {
      await entry.render(el, this);
    } catch (err) {
      el.innerHTML = `<p>failed to load: ${String(err.message || err).replace(/</g, "&lt;")}</p>`;
    }
    // only paint if this entry is still on top (user may have navigated on)
    if (this.top() === entry) {
      this.contentEl.innerHTML = "";
      this.contentEl.appendChild(el);
      await this._chrome(entry);
      if (entry.targetType && entry.targetId) {
        this._annotations(el, entry).catch(() => {});
      }
    }
  }

  async _chrome(entry) {
    const prev = this.host.querySelector(".pane-prev");
    const next = this.host.querySelector(".pane-next");
    const bm = this.host.querySelector(".pane-bookmark");
    const seq = entry.sequence;
    if (seq) {
      const dir = await this._dir();
      const list = dir[seq.type] || [];
      const idx = list.findIndex((x) => x.id === seq.id);
      prev.classList.toggle("hidden", !(idx > 0));
      next.classList.toggle("hidden", !(idx >= 0 && idx < list.length - 1));
      this._seqState = { list, idx, type: seq.type };
    } else {
      prev.classList.add("hidden");
      next.classList.add("hidden");
      this._seqState = null;
    }
    if (entry.targetType && entry.targetId) {
      bm.classList.remove("hidden");
      try {
        const data = await api.bookmarks();
        const isB = (data.bookmarks || []).some((b) =>
          b.target_type === entry.targetType && b.target_id === entry.targetId);
        bm.textContent = isB ? "★" : "☆";
        bm.classList.toggle("bookmarked", isB);
      } catch { bm.textContent = "☆"; }
    } else {
      bm.classList.add("hidden");
    }
  }

  _step(delta) {
    if (!this._seqState) return;
    const { list, idx, type } = this._seqState;
    const target = list[idx + delta];
    if (!target || !this.openEntity) return;
    this.openEntity(type, target.id, { replace: true });
  }

  async _toggleBookmark() {
    const entry = this.top();
    if (!entry || !entry.targetType) return;
    const bmType = entry.targetType === "person" ? "notable_person" : entry.targetType;
    try {
      const res = await api.bookmarkToggle(bmType, entry.targetId);
      const bm = this.host.querySelector(".pane-bookmark");
      bm.textContent = res.bookmarked ? "★" : "☆";
      bm.classList.toggle("bookmarked", !!res.bookmarked);
    } catch { /* backend unavailable */ }
  }

  // §19 — personal annotations: distinctly styled, never blended with AI
  // output; target_type person→person (annotations table uses 'person')
  async _annotations(el, entry) {
    const type = entry.targetType === "notable_person" ? "person" : entry.targetType;
    const section = document.createElement("section");
    section.className = "annot-section";
    section.innerHTML = `<h4>Your notes <span class="cp-meta">(yours, not the AI's)</span></h4>
      <div class="annot-list"></div>
      <div class="annot-add"><textarea rows="2"
        placeholder="your own read on this — saved locally"></textarea>
        <button>save note</button></div>`;
    el.appendChild(section);
    const listEl = section.querySelector(".annot-list");
    const paint = async () => {
      listEl.innerHTML = "";
      const data = await api.annotations(type, entry.targetId).catch(() => null);
      for (const a of (data && data.annotations) || []) {
        const row = document.createElement("div");
        row.className = "annot-item";
        row.innerHTML = `<span class="annot-text"></span>
          <span class="cp-meta">${(a.updated_at || "").slice(0, 16).replace("T", " ")}</span>
          <button class="cp-del" title="delete note">✕</button>`;
        row.querySelector(".annot-text").textContent = a.note_text;
        row.querySelector(".cp-del").addEventListener("click", async () => {
          await api.annotationDelete(a.id);
          paint();
        });
        listEl.appendChild(row);
      }
    };
    await paint();
    section.querySelector("button").addEventListener("click", async () => {
      const ta = section.querySelector("textarea");
      if (!ta.value.trim()) return;
      await api.annotationSave(type, entry.targetId, ta.value.trim());
      ta.value = "";
      paint();
    });
  }
}
