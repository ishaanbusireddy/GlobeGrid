// Section 5.10 — system status panel: health of every registered source
// (ok / degraded / down), refreshed periodically. A dead source is
// surfaced here, never silently dropped.
import { api } from "../../api/client.js";

export class StatusPanel {
  constructor(drawerEl, toggleBtn, onSelectSource) {
    this.drawer = drawerEl;
    this.toggleBtn = toggleBtn;
    this.onSelectSource = onSelectSource;   // v7.4.1 — click a source → its stories
    this.timer = null;
    toggleBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      this.drawer.classList.contains("hidden") ? this.open() : this.close();
    });
    // v5 §19 — standard drawer dismissal that was missing: Escape closes,
    // and a click anywhere outside the drawer (or its toggle) closes. The
    // in-drawer button is wired in refresh() to this same close(), not a
    // separate no-op, which was the root cause of "can't close once opened".
    this._onKey = (ev) => {
      if (ev.key === "Escape" && !this.drawer.classList.contains("hidden")) this.close();
    };
    this._onDocClick = (ev) => {
      if (this.drawer.classList.contains("hidden")) return;
      if (!this.drawer.contains(ev.target) && ev.target !== this.toggleBtn) this.close();
    };
    document.addEventListener("keydown", this._onKey);
    document.addEventListener("click", this._onDocClick);
    this.timer = setInterval(() => {
      if (!this.drawer.classList.contains("hidden")) this.refresh();
    }, 30000);
  }

  open() {
    this.drawer.classList.remove("hidden");
    this.toggleBtn.classList.add("active");
    this.refresh();
  }

  close() {
    this.drawer.classList.add("hidden");
    this.toggleBtn.classList.remove("active");
  }

  async refresh() {
    try {
      const data = await api.sourcesStatus();
      this.drawer.innerHTML =
        '<div class="sp-head"><h3>Source health</h3>'
        + '<button class="sp-close" title="Close (Esc)" aria-label="Close">×</button></div>';
      this.drawer.querySelector(".sp-close").addEventListener("click", () => this.close());
      for (const s of data.sources || []) {
        const row = document.createElement("div");
        row.className = "src-row";
        const bars = (s.recent_history || []).map((h) =>
          `<i class="up-bar up-${h}"></i>`).join("");
        const uptime = s.uptime_24h_pct == null ? "" : ` ${s.uptime_24h_pct}%`;
        // v5 §5/§21 — visible reliability tier on every source
        const tier = s.reliability_tier || "medium";
        row.innerHTML = `
          <span class="health-dot health-${s.health_status}"></span>
          <span class="tier-chip tier-${tier}" title="reliability tier">${tier[0].toUpperCase()}</span>
          <b style="flex:0 0 138px"></b>
          <span class="up-bars" title="last checks${uptime}">${bars}</span>
          <span class="err" style="margin-left:auto"></span>`;
        row.querySelector("b").textContent =
          s.name + (s.kind === "official" ? " (official)" : "");
        row.querySelector(".err").textContent =
          s.health_status === "ok"
            ? `${uptime || ""} last: ${(s.last_fetched_at || "").slice(11, 19) || "–"}`
            : (s.last_error || "").slice(0, 48);
        row.title = `${s.type} · every ${s.poll_interval_seconds}s · click to see its stories`;
        // v7.4.1 — click a source to open the stories/events it fed (owner)
        if (this.onSelectSource) {
          row.classList.add("src-clickable");
          row.addEventListener("click", () => this.onSelectSource(s));
        }
        this.drawer.appendChild(row);
      }
      // v3 §11 — visible chain-verification indicator, with the scope
      // caveat stated plainly (proves our records unaltered, not that
      // sources were true)
      try {
        const prov = await api.provenance();
        const row = document.createElement("div");
        row.className = "prov-row " + (prov.ok ? "prov-ok" : "prov-bad");
        const checked = (prov.chains || []).reduce((s, c) => s + (c.checked || 0), 0);
        row.textContent = prov.ok
          ? `provenance chain verified (${checked} hashed rows) · ${prov.verified_at || ""}`
          : "PROVENANCE CHAIN BROKEN — records were altered after writing";
        row.title = prov.scope_note || "";
        this.drawer.appendChild(row);
      } catch { /* provenance endpoint unavailable */ }
      for (const line of data.attribution || []) {
        const p = document.createElement("p");
        p.className = "attribution";
        p.textContent = line;
        this.drawer.appendChild(p);
      }
      // v4 §22 — the consolidated sources & credits page
      const credits = document.createElement("button");
      credits.className = "filter-chip credits-link";
      credits.textContent = "full sources & credits page →";
      credits.style.marginTop = "8px";
      this.drawer.appendChild(credits);
    } catch (err) {
      this.drawer.innerHTML = `<h3>Source health</h3><p>unavailable: ${err.message}</p>`;
    }
  }
}
