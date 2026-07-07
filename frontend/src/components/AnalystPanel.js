// v3 §24 — the analyst orb + slide-in panel.
// A glowing point-of-light docked bottom-right (idle: slow pulse;
// brightens when instability crosses a threshold). Clicking expands a
// slide-in panel: conversation above, single-line input below. Answers
// carry inline citation chips (deep links to stories) and, when Path 1
// resolved an entity, a navigation affordance — auto-acted-on when the
// 'Auto-navigate for me' toggle is on (§24.4), never on low-confidence
// answers (guardrail enforced server-side).
import { api } from "../api/client.js";

const AUTONAV_KEY = "tdl_autonav";
const ORB_BRIGHT_INSTABILITY = 60;

export class AnalystPanel {
  constructor({ onOpenStory, onNavigate, getFocusedEntity, getScreen,
                onOpenThread, autoNavDefault = true }) {
    this.onOpenStory = onOpenStory;
    this.onNavigate = onNavigate;
    this.getFocusedEntity = getFocusedEntity || (() => null);
    this.getScreen = getScreen || (() => null);       // v6 §29 screen-aware
    this.onOpenThread = onOpenThread || (() => {});
    this.sessionId = null;
    this.autoNav = localStorage.getItem(AUTONAV_KEY) === null
      ? autoNavDefault : localStorage.getItem(AUTONAV_KEY) === "1";

    this.orb = document.createElement("button");
    this.orb.id = "analyst-orb";
    this.orb.title = "Ask the analyst";
    this.orb.innerHTML = '<span class="orb-core"></span>';
    document.body.appendChild(this.orb);

    this.panel = document.createElement("div");
    this.panel.id = "analyst-panel";
    this.panel.className = "hidden";
    this.panel.innerHTML = `
      <div class="ap-head">
        <span>ANALYST <em>· grounded in GlobeGrid data</em></span>
        <label class="ap-autonav" title="jump the UI to the answer's subject automatically">
          <input type="checkbox" ${this.autoNav ? "checked" : ""}> auto-navigate
        </label>
        <button class="ap-close">✕</button>
      </div>
      <div class="ap-messages"></div>
      <form class="ap-form">
        <input class="ap-input" placeholder="what's the status of… ?" autocomplete="off">
        <button type="button" class="ap-stop hidden" title="stop this response">◼ stop</button>
      </form>`;
    document.body.appendChild(this.panel);
    this.messagesEl = this.panel.querySelector(".ap-messages");
    this.input = this.panel.querySelector(".ap-input");
    this.stopBtn = this.panel.querySelector(".ap-stop");
    this.inflight = null;   // v6.1 — AbortController for the running request
    this.stopBtn.addEventListener("click", () => this._stop());

    this.orb.addEventListener("click", () => this.toggle());
    this.panel.querySelector(".ap-close").addEventListener("click", () => this.hide());
    this.panel.querySelector(".ap-autonav input").addEventListener("change", (ev) => {
      this.autoNav = ev.target.checked;
      localStorage.setItem(AUTONAV_KEY, this.autoNav ? "1" : "0");
    });
    this.panel.querySelector(".ap-form").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const question = this.input.value.trim();
      if (question) { this.input.value = ""; this._ask(question); }
    });
    this._loadHistory();
  }

  setInstability(score) {
    this.orb.classList.toggle("orb-bright", (score || 0) >= ORB_BRIGHT_INSTABILITY);
  }

  toggle() {
    this.panel.classList.contains("hidden") ? this.show() : this.hide();
  }

  show() {
    this.panel.classList.remove("hidden");
    this.input.focus();
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  hide() { this.panel.classList.add("hidden"); }

  async _loadHistory() {
    try {
      const data = await api.analystHistory();
      this.sessionId = data.session_id;
      for (const m of (data.messages || []).slice(-20)) {
        this._render(m.role, m.content, m.cited_story_ids
          ? m.cited_story_ids.map((id) => ({ id, headline: "cited story" })) : [],
          m.suggested_navigation, false);
      }
    } catch { /* fresh session */ }
  }

  _stop() {
    if (this.inflight) {
      this.inflight.abort(new Error("stopped by user"));
      this.inflight = null;
    }
  }

  async _ask(question) {
    this._render("user", question, [], null, false);
    const thinking = document.createElement("div");
    thinking.className = "ap-msg ap-assistant ap-thinking";
    thinking.textContent = "consulting the fact chain & web…";
    this.messagesEl.appendChild(thinking);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    // v6.1 — show the Stop button and arm an AbortController for this request
    this.inflight = new AbortController();
    this.stopBtn.classList.remove("hidden");
    try {
      const res = await api.analystAsk(question, this.sessionId,
                                       this.getFocusedEntity(), this.getScreen(),
                                       this.inflight.signal);
      thinking.remove();
      this.sessionId = res.session_id || this.sessionId;
      this._render("assistant", res.answer, res.citations || [],
                   res.suggested_navigation, true, res.confidence,
                   res.deep_dive, res.linked);   // v6 §29
      // §24.4 — auto-navigate only when toggled on; the affordance itself
      // is always rendered regardless (transparency is not optional)
      if (this.autoNav && res.suggested_navigation && this.onNavigate) {
        this.onNavigate(res.suggested_navigation);
      }
    } catch (err) {
      const stopped = this.inflight && this.inflight.signal.aborted;
      thinking.textContent = stopped
        ? "⏹ stopped."
        : (/timeout/i.test(err.message)
            ? "the analyst took too long and was stopped — try a narrower "
              + "question, or check your AI key in Settings."
            : `analyst unavailable: ${err.message}`);
    } finally {
      this.inflight = null;
      this.stopBtn.classList.add("hidden");
    }
  }

  // minimal, XSS-safe markdown: escape first, then re-introduce only a
  // known-safe subset (bold/italic/code/links/line breaks). The analyst now
  // returns real prose — possibly with web-source links — so plain
  // textContent would show raw ** and [](: markup.
  _md(text) {
    const esc = (text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return esc
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
               '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\n/g, "<br>");
  }

  _render(role, text, citations, navigation, scroll, confidence,
          deepDive, linked) {
    const div = document.createElement("div");
    div.className = `ap-msg ap-${role}`;
    const body = document.createElement("div");
    if (role === "assistant") body.innerHTML = this._md(text);
    else body.textContent = text;
    div.appendChild(body);
    // v6 §29 — bulleted answers carry an expandable deep-dive (same
    // two-density pattern as story synthesis)
    if (deepDive) {
      const btn = document.createElement("button");
      btn.className = "ap-chip ap-deepdive";
      btn.textContent = "≡ deep dive";
      const dd = document.createElement("div");
      dd.className = "ap-deepdive-body";
      dd.style.display = "none";
      dd.innerHTML = this._md(deepDive);
      btn.addEventListener("click", () => {
        const open = dd.style.display !== "none";
        dd.style.display = open ? "none" : "block";
        btn.textContent = open ? "≡ deep dive" : "≡ collapse";
      });
      div.appendChild(btn);
      div.appendChild(dd);
    }
    // v6 §29 — region deep-dive links: countries + threads + stories as
    // actual linked content, not a one-line summary
    if (linked) {
      const wrap = document.createElement("div");
      wrap.className = "ap-citations";
      for (const c of (linked.countries || []).slice(0, 10)) {
        const chip = document.createElement("button");
        chip.className = "ap-chip";
        chip.textContent = c.name;
        chip.addEventListener("click", () =>
          this.onNavigate && this.onNavigate({ type: "country", id: c.id, name: c.name }));
        wrap.appendChild(chip);
      }
      for (const c of (linked.conflicts || [])) {
        const chip = document.createElement("button");
        chip.className = "ap-chip ap-nav";
        chip.textContent = "⚔ " + c.name;
        chip.addEventListener("click", () =>
          this.onNavigate && this.onNavigate({ type: "conflict", id: c.id, name: c.name }));
        wrap.appendChild(chip);
      }
      for (const t of (linked.threads || [])) {
        const chip = document.createElement("button");
        chip.className = "ap-chip";
        chip.textContent = "🧵 " + t.name;
        chip.addEventListener("click", () => this.onOpenThread(t.id));
        wrap.appendChild(chip);
      }
      for (const st of (linked.recent_stories || []).slice(0, 5)) {
        const chip = document.createElement("button");
        chip.className = "ap-chip";
        chip.textContent = "⌕ " + (st.headline || "").slice(0, 44);
        chip.addEventListener("click", () => this.onOpenStory(st.id));
        wrap.appendChild(chip);
      }
      if (wrap.children.length) div.appendChild(wrap);
    }
    if (confidence) {
      const conf = document.createElement("span");
      conf.className = `conf conf-${confidence}`;
      conf.textContent = confidence;
      div.appendChild(conf);
    }
    if (citations && citations.length) {
      const chips = document.createElement("div");
      chips.className = "ap-citations";
      for (const c of citations) {
        const chip = document.createElement("button");
        chip.className = "ap-chip";
        chip.textContent = "⌕ " + (c.headline || c.id).slice(0, 44);
        chip.title = c.headline || c.id;
        chip.addEventListener("click", () => this.onOpenStory(c.id));
        chips.appendChild(chip);
      }
      div.appendChild(chips);
    }
    if (navigation) {
      const nav = document.createElement("button");
      nav.className = "ap-chip ap-nav";
      nav.textContent = `Open: ${navigation.name} →`;
      nav.addEventListener("click", () => this.onNavigate && this.onNavigate(navigation));
      div.appendChild(nav);
    }
    this.messagesEl.appendChild(div);
    if (scroll !== false) this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }
}
