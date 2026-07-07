// Tier 3 — v6.1.1 GEOGRAPHIC-BOX layout (was a flat list). No map, content
// first, under 2 seconds to first content on any device — but events are now
// grouped into continental panels so the view is spatially organised instead
// of one long chronological list.
import { formatDateTime } from "../../data/timefmt.js";

// continental bins as [minLon, maxLon, minLat, maxLat]; the first match wins,
// so overlapping regions (Middle East before Asia/Africa) are ordered.
const REGIONS = [
  ["North America", [-170, -50, 13, 85]],
  ["Central America & Caribbean", [-95, -58, 7, 25]],
  ["South America", [-92, -33, -60, 13]],
  ["Europe", [-25, 45, 35, 72]],
  ["Middle East", [30, 63, 12, 42]],
  ["Africa", [-20, 52, -40, 37]],
  ["Central & South Asia", [45, 92, 5, 55]],
  ["East & Southeast Asia", [92, 150, -11, 55]],
  ["Russia & North Asia", [45, 190, 50, 82]],
  ["Oceania", [110, 190, -50, 8]],
];

function regionOf(lat, lon) {
  if (lat == null || lon == null) return "Unlocated";
  for (const [name, [mnLon, mxLon, mnLat, mxLat]] of REGIONS) {
    if (lon >= mnLon && lon <= mxLon && lat >= mnLat && lat <= mxLat) return name;
  }
  return "Other / polar";
}

const CAT_ICON = { geopolitics: "🏛", finance: "💹", disaster: "🌪",
                   conflict: "⚔", military: "🪖", other: "•" };

export class Tier3List {
  constructor(host, { onSelectEvent } = {}) {
    this.host = host;
    this.onSelectEvent = onSelectEvent || (() => {});
    this.wrap = document.createElement("div");
    this.wrap.className = "t3-wrap t3-geo";
    host.appendChild(this.wrap);
  }

  destroy() { this.wrap.remove(); }

  setData({ events = [] }) {
    this.wrap.innerHTML = "";
    const byRegion = new Map();
    for (const r of REGIONS) byRegion.set(r[0], []);
    byRegion.set("Unlocated", []); byRegion.set("Other / polar", []);
    for (const e of events) {
      const reg = regionOf(e.lat, e.lon);
      (byRegion.get(reg) || byRegion.set(reg, []).get(reg)).push(e);
    }
    let any = false;
    for (const [region, evs] of byRegion) {
      if (!evs.length) continue;
      any = true;
      evs.sort((a, b) => (b.occurred_at || "").localeCompare(a.occurred_at || ""));
      const panel = document.createElement("div");
      panel.className = "t3-geo-panel";
      const head = document.createElement("div");
      head.className = "t3-geo-head";
      head.innerHTML = `<h3>${region}</h3><span class="t3-count">${evs.length}</span>`;
      panel.appendChild(head);
      for (const e of evs.slice(0, 40)) {
        const card = document.createElement("div");
        card.className = "t3-card";
        const when = formatDateTime(e.occurred_at);
        card.innerHTML = `
          <div><span class="chip cat-${e.category}">${CAT_ICON[e.category] || "•"} ${e.category}</span> <b></b></div>
          <div class="where"></div>`;
        card.querySelector("b").textContent = e.title;
        card.querySelector(".where").textContent =
          `${e.location_name || "—"} · sev ${e.severity} · ${when}`;
        card.addEventListener("click", () => this.onSelectEvent(e));
        panel.appendChild(card);
      }
      this.wrap.appendChild(panel);
    }
    if (!any) {
      this.wrap.innerHTML = '<p style="color:var(--text-dim)">No events yet — ingestion warming up.</p>';
    }
  }
}
