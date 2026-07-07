"""v2 addendum §1.4 — OpenSky Network (ADS-B) flight-disruption signal.

Anonymous REST access, budget-limited (§7.2). Watches a small set of
geopolitically sensitive bounding boxes; keeps an exponential moving
average of aircraft counts per box in app_meta and emits an event when
traffic collapses well below baseline — the airspace-closure signature
that correlates with conflict/disaster events. (Shipping/maritime remains
OPEN per the addendum — no clean free equivalent.)
"""

import json

from ...db.models import meta_get, meta_set, now_iso
from ..budget import spend
from ..http import fetch_url

# name -> (lamin, lomin, lamax, lomax)
WATCH_BOXES = {
    "Eastern Mediterranean": (31.0, 25.0, 37.0, 36.0),
    "Black Sea":             (41.0, 27.0, 47.5, 42.0),
    "Persian Gulf":          (23.5, 47.0, 30.5, 57.0),
    "Taiwan Strait":         (21.5, 117.0, 26.5, 122.5),
}
DROP_RATIO = 0.4     # alert when count falls below 40% of baseline
MIN_BASELINE = 20.0  # need a meaningful baseline before alerting
EMA_ALPHA = 0.2


def fetch(source: dict) -> list[dict]:
    state = json.loads(meta_get("opensky_baselines") or "{}")
    items = []
    for name, (lamin, lomin, lamax, lomax) in WATCH_BOXES.items():
        spend("opensky")
        url = (f"https://opensky-network.org/api/states/all?"
               f"lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}")
        data = json.loads(fetch_url(url, timeout=30))
        count = len(data.get("states") or [])
        baseline = state.get(name)
        if baseline is not None and baseline >= MIN_BASELINE and \
                count < baseline * DROP_RATIO:
            clat, clon = (lamin + lamax) / 2, (lomin + lomax) / 2
            items.append({
                "title": f"Air traffic collapse over {name}: {count} aircraft"
                         f" vs ~{baseline:.0f} baseline",
                "summary": "ADS-B aircraft count far below rolling baseline —"
                           " possible airspace closure or disruption.",
                "link": "https://globe.adsbexchange.com/"
                        f"?lat={clat:.1f}&lon={clon:.1f}&zoom=6",
                "published": now_iso(),
                "external_id": f"{name}-{now_iso()[:13]}",
                "lat": clat, "lon": clon,
                "location_name": name,
                "category": "conflict",
                "severity": 3,
                "who": f"OpenSky Network ({name} airspace)",
                "what": f"aircraft count dropped to {count} vs baseline {baseline:.0f}",
            })
        state[name] = count if baseline is None else \
            (1 - EMA_ALPHA) * baseline + EMA_ALPHA * count
    meta_set("opensky_baselines", json.dumps(state))
    return items
