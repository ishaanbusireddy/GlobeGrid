"""v7.2 §4 — nighttime-lights (VIIRS DNB) blackout signal.

Watches the radiance of populated, conflict-prone cities and emits an event
when a place goes DARK relative to its rolling baseline — the satellite
signature of a grid collapse, a siege, a bombing campaign, or a disaster
that cuts power. The physical corroboration for a war/disaster story: when
text says "the city lost power" and the sky agrees, the story earns a
corroboration score. Requires a NASA Earthdata token (NASA_EARTHDATA_TOKEN
in .env) for the VIIRS Black Marble VNP46 product; with no token it declines
cleanly. Live imagery is proxy-blocked in the build sandbox — degrades to no
events there.
"""

import json

from ...config import env
from ...db.models import meta_get, meta_set, now_iso
from ..budget import spend
from ..http import SourceNotConfigured, fetch_url

# name -> (lat, lon) — cities where a sudden loss of light is a signal, not noise
WATCH_CITIES = {
    "Gaza City":    (31.50, 34.47),
    "Kharkiv":      (49.99, 36.23),
    "Khartoum":     (15.50, 32.56),
    "Beirut":       (33.89, 35.50),
    "Sanaa":        (15.37, 44.19),
    "Damascus":     (33.51, 36.29),
    "Mariupol":     (47.10, 37.55),
    "Aleppo":       (36.20, 37.16),
    "Port-au-Prince": (18.59, -72.31),
}
DARK_RATIO = 0.45    # radiance below 45% of baseline = a blackout signature
MIN_BASELINE = 5.0   # nW/cm²/sr — need real light before a drop means anything
EMA_ALPHA = 0.25


def _radiance(token: str, lat: float, lon: float) -> float:
    """Mean VIIRS DNB radiance over a small box around the city. Uses the
    NASA GIBS/Black-Marble tile service shape; any failure raises and the
    source degrades for this cycle rather than crashing the pipeline."""
    spend("nightlights")
    # A compact statistics query around the point (product VNP46A2, last night).
    url = (f"https://ladsweb.modaps.eosdis.nasa.gov/api/v2/measures/point"
           f"?product=VNP46A2&lat={lat:.3f}&lon={lon:.3f}&token={token}")
    data = json.loads(fetch_url(url, timeout=45))
    if isinstance(data, dict):
        for k in ("radiance", "value", "mean", "DNB_At_Sensor_Radiance"):
            if k in data:
                return float(data[k])
    raise ValueError("no radiance field in response")


def fetch(source: dict) -> list[dict]:
    token = env("NASA_EARTHDATA_TOKEN")
    if not token:
        raise SourceNotConfigured(
            "NASA_EARTHDATA_TOKEN not set (free signup at urs.earthdata.nasa.gov)")
    state = json.loads(meta_get("nightlights_baselines") or "{}")
    items = []
    for name, (lat, lon) in WATCH_CITIES.items():
        rad = _radiance(token, lat, lon)
        baseline = state.get(name)
        if baseline is not None and baseline >= MIN_BASELINE and \
                rad < baseline * DARK_RATIO:
            items.append({
                "title": f"{name} goes dark: nighttime radiance {rad:.1f} vs"
                         f" ~{baseline:.1f} baseline",
                "summary": "VIIRS nighttime-lights radiance far below its"
                           " rolling baseline — the satellite signature of a"
                           " power-grid collapse, siege, or disaster blackout.",
                "link": "https://worldview.earthdata.nasa.gov/"
                        f"?v={lon-3:.1f},{lat-3:.1f},{lon+3:.1f},{lat+3:.1f}"
                        "&l=VIIRS_SNPP_DayNightBand_At_Sensor_Radiance",
                "published": now_iso(),
                "external_id": f"nl-{name}-{now_iso()[:10]}",
                "lat": lat, "lon": lon,
                "location_name": name,
                "category": "conflict",
                "severity": 4,
                "who": f"VIIRS nighttime lights ({name})",
                "what": f"radiance dropped to {rad:.1f} vs baseline {baseline:.1f}",
            })
        state[name] = rad if baseline is None else \
            (1 - EMA_ALPHA) * baseline + EMA_ALPHA * rad
    meta_set("nightlights_baselines", json.dumps(state))
    return items
