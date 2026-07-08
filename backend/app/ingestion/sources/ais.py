"""v7.2 §4 — AIS vessel-traffic signal at maritime chokepoints.

The seagoing companion to OpenSky's airspace watch: keeps a rolling
baseline of vessel counts through the world's strategic straits and canals
and emits an event when traffic collapses (blockade / closure / diversion)
or spikes hard above baseline (a convoy or a pile-up behind a closed
chokepoint) — the physical-sensor corroboration for a conflict or shipping
story. Requires a free AISStream / AISHub key (AIS_API_KEY in .env); with
no key it declines cleanly and the pipeline simply skips it. Live AIS is
proxy-blocked in the build sandbox, so it degrades to no events there.
"""

import json

from ...config import env
from ...db.models import meta_get, meta_set, now_iso
from ..budget import spend
from ..http import SourceNotConfigured, fetch_url

# name -> (lamin, lomin, lamax, lomax) — the chokepoints that move the world's
# trade and where a closure is a first-order geopolitical event.
WATCH_STRAITS = {
    "Strait of Hormuz":   (25.5, 55.0, 27.5, 57.5),
    "Bab-el-Mandeb":      (12.0, 42.5, 14.0, 44.5),
    "Suez Canal":         (29.9, 32.3, 31.3, 32.7),
    "Strait of Malacca":  (1.0, 100.0, 5.5, 104.5),
    "Taiwan Strait":      (23.0, 118.0, 26.0, 121.0),
    "Bosphorus":          (40.9, 28.9, 41.3, 29.2),
    "Panama Canal":       (8.9, -80.0, 9.4, -79.5),
    "Strait of Gibraltar": (35.8, -5.7, 36.2, -5.2),
}
DROP_RATIO = 0.4     # closure signature — count far below baseline
SPIKE_RATIO = 2.5    # pile-up / convoy signature — count far above baseline
MIN_BASELINE = 8.0   # need a meaningful baseline before alerting
EMA_ALPHA = 0.2


def _vessel_count(key: str, box) -> int:
    """Query a vessel count for a bounding box. AISHub-style REST shape;
    any transport/parse failure raises and the caller lets the source
    degrade for this cycle."""
    lamin, lomin, lamax, lomax = box
    spend("ais")
    url = (f"https://data.aishub.net/ws.php?username={key}&format=1&output=json"
           f"&latmin={lamin}&lonmin={lomin}&latmax={lamax}&lonmax={lomax}")
    data = json.loads(fetch_url(url, timeout=30))
    # AISHub returns [meta, [vessels...]]; be tolerant of either shape.
    if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
        return len(data[1])
    if isinstance(data, list):
        return len(data)
    return len(data.get("vessels") or data.get("data") or [])


def fetch(source: dict) -> list[dict]:
    key = env("AIS_API_KEY")
    if not key:
        raise SourceNotConfigured(
            "AIS_API_KEY not set (free signup at aishub.net or aisstream.io)")
    state = json.loads(meta_get("ais_baselines") or "{}")
    items = []
    for name, box in WATCH_STRAITS.items():
        count = _vessel_count(key, box)
        baseline = state.get(name)
        clat, clon = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        if baseline is not None and baseline >= MIN_BASELINE:
            if count < baseline * DROP_RATIO:
                items.append(_event(
                    name, clat, clon,
                    f"Vessel traffic collapse at {name}: {count} vs"
                    f" ~{baseline:.0f} baseline",
                    "AIS vessel count far below rolling baseline — possible"
                    " closure, blockade, or diversion of the chokepoint.",
                    count, baseline, 4))
            elif count > baseline * SPIKE_RATIO:
                items.append(_event(
                    name, clat, clon,
                    f"Vessel pile-up at {name}: {count} vs ~{baseline:.0f}"
                    " baseline",
                    "AIS vessel count far above baseline — congestion, a"
                    " convoy, or ships queuing behind a blocked passage.",
                    count, baseline, 3))
        state[name] = count if baseline is None else \
            (1 - EMA_ALPHA) * baseline + EMA_ALPHA * count
    meta_set("ais_baselines", json.dumps(state))
    return items


def _event(name, lat, lon, title, summary, count, baseline, severity):
    return {
        "title": title,
        "summary": summary,
        "link": f"https://www.marinetraffic.com/en/ais/home/centerx:{lon:.1f}"
                f"/centery:{lat:.1f}/zoom:7",
        "published": now_iso(),
        "external_id": f"ais-{name}-{now_iso()[:13]}",
        "lat": lat, "lon": lon,
        "location_name": name,
        "category": "conflict",
        "severity": severity,
        "who": f"AIS ({name})",
        "what": f"vessel count {count} vs baseline {baseline:.0f}",
    }
