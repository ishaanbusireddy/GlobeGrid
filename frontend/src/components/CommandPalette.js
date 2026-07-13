// v2 addendum §5.3 — command palette (Ctrl/Cmd+K).
// Client-side fuzzy search over story headlines, canonical entities, and
// regions (backed by /api/search + current map data); selecting a result
// opens the story or triggers the fly-to camera. Also hosts saved camera
// bookmarks (localStorage — personal UI preference, no backend table).
import { api } from "../api/client.js";

const BOOKMARK_KEY = "tdl_camera_bookmarks";

export class CommandPalette {
  constructor({ onOpenStory, onFlyTo, getCamera, setCamera, getRegions }) {
    this.onOpenStory = onOpenStory;
    this.onFlyTo = onFlyTo;
    this.getCamera = getCamera;
    this.setCamera = setCamera;
    this.getRegions = getRegions || (() => []);
    this.el = document.createElement("div");
    this.el.id = "cmd-palette";
    this.el.className = "hidden";
    this.el.innerHTML = `
      <div class="cp-box">
        <input class="cp-input" placeholder="Search stories, entities, places…  (Esc to close)">
        <div class="cp-results"></div>
        <div class="cp-footer">
          <button class="cp-save-cam">★ bookmark camera</button>
          <span class="cp-hint">↵ open · Ctrl/Cmd+K toggle</span>
        </div>
      </div>`;
    document.body.appendChild(this.el);
    this.input = this.el.querySelector(".cp-input");
    this.results = this.el.querySelector(".cp-results");
    this._debounce = null;

    document.addEventListener("keydown", (ev) => {
      // v8.16 — Ctrl/Cmd+K replaced by the plain F key (owner request); the
      // F binding lives in App.js's single-key shortcut handler.
      if (ev.key === "Escape" && !this.el.classList.contains("hidden")) {
        this.hide();
      }
    });
    this.el.addEventListener("click", (ev) => { if (ev.target === this.el) this.hide(); });
    this.input.addEventListener("input", () => {
      clearTimeout(this._debounce);
      this._debounce = setTimeout(() => this._search(this.input.value.trim()), 200);
    });
    this.el.querySelector(".cp-save-cam").addEventListener("click", () => this._saveBookmark());
  }

  toggle() {
    this.el.classList.contains("hidden") ? this.show() : this.hide();
  }

  show() {
    this.el.classList.remove("hidden");
    this.input.value = "";
    this._renderDefault();
    this.input.focus();
  }

  hide() { this.el.classList.add("hidden"); }

  _bookmarks() { return JSON.parse(localStorage.getItem(BOOKMARK_KEY) || "[]"); }

  _saveBookmark() {
    const name = prompt("Bookmark name:");
    if (!name || !this.getCamera) return;
    const marks = this._bookmarks();
    marks.push({ name, camera: this.getCamera() });
    localStorage.setItem(BOOKMARK_KEY, JSON.stringify(marks.slice(-12)));
    this._renderDefault();
  }

  _row(label, meta, onPick) {
    const div = document.createElement("div");
    div.className = "cp-row";
    div.innerHTML = `<span class="cp-label"></span><span class="cp-meta"></span>`;
    div.querySelector(".cp-label").textContent = label;
    div.querySelector(".cp-meta").textContent = meta;
    div.addEventListener("click", () => { onPick(); this.hide(); });
    return div;
  }

  _renderDefault() {
    this.results.innerHTML = "";
    const marks = this._bookmarks();
    if (marks.length) {
      for (const [i, m] of marks.entries()) {
        const row = this._row(`★ ${m.name}`, "camera bookmark",
          () => this.setCamera && this.setCamera(m.camera));
        const del = document.createElement("button");
        del.className = "cp-del"; del.textContent = "✕";
        del.addEventListener("click", (ev) => {
          ev.stopPropagation();
          marks.splice(i, 1);
          localStorage.setItem(BOOKMARK_KEY, JSON.stringify(marks));
          this._renderDefault();
        });
        row.appendChild(del);
        this.results.appendChild(row);
      }
    }
    for (const r of this.getRegions().slice(0, 6)) {
      this.results.appendChild(this._row(`◎ ${r.name}`, "fly to region",
        () => this.onFlyTo(r.lat, r.lon)));
    }
  }

  async _search(term) {
    if (!term) { this._renderDefault(); return; }
    this.results.innerHTML = '<div class="cp-row cp-meta">searching…</div>';
    // local region matches first (instant)
    const rows = [];
    const lower = term.toLowerCase();
    for (const r of this.getRegions()) {
      if (r.name.toLowerCase().includes(lower)) {
        rows.push(this._row(`◎ ${r.name}`, "fly to", () => this.onFlyTo(r.lat, r.lon)));
        if (rows.length >= 4) break;
      }
    }
    try {
      const data = await api.search(term);
      for (const s of (data.stories || []).slice(0, 8)) {
        rows.push(this._row(s.headline, `story · ${s.confidence}`,
          () => this.onOpenStory(s.id)));
      }
      for (const f of (data.facts || []).slice(0, 6)) {
        rows.push(this._row(`${f.who} — ${f.what}`.slice(0, 90),
          `fact · ${f.source}${f.story_id ? " · in story" : ""}`,
          () => f.story_id && this.onOpenStory(f.story_id)));
      }
    } catch (err) {
      rows.push(this._row(`search unavailable: ${err.message}`, "", () => {}));
    }
    this.results.innerHTML = "";
    if (!rows.length) this.results.innerHTML = '<div class="cp-row cp-meta">no matches</div>';
    for (const r of rows) this.results.appendChild(r);
  }
}
