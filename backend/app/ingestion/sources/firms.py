"""v2 addendum §1.1 — NASA FIRMS wildfire / thermal anomalies.

Free MAP_KEY required (https://firms.modaps.eosdis.nasa.gov/api/) via
FIRMS_MAP_KEY in .env. Fetches last-24h VIIRS detections (CSV) and emits
the strongest fires as disaster events; low-FRP noise is filtered so the
map shows real fires, not every agricultural burn.
"""

import csv
import io

from ...config import env
from ..http import SourceNotConfigured, fetch_url

MIN_FRP = 100.0   # fire radiative power (MW) floor — keeps signal, drops noise
MAX_ITEMS = 30


def fetch(source: dict) -> list[dict]:
    key = env("FIRMS_MAP_KEY")
    if not key:
        raise SourceNotConfigured("FIRMS_MAP_KEY not set (free signup at firms.modaps.eosdis.nasa.gov)")
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/world/1"
    body = fetch_url(url, timeout=60).decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(body))
    fires = []
    for row in reader:
        try:
            frp = float(row.get("frp") or 0)
        except ValueError:
            continue
        if frp >= MIN_FRP and row.get("confidence", "n") in ("h", "high", "nominal", "n"):
            fires.append((frp, row))
    fires.sort(key=lambda f: -f[0])

    items = []
    for frp, row in fires[:MAX_ITEMS]:
        lat, lon = float(row["latitude"]), float(row["longitude"])
        day, time4 = row.get("acq_date", ""), (row.get("acq_time") or "0000").zfill(4)
        items.append({
            "title": f"Major thermal anomaly detected (FRP {frp:.0f} MW)",
            "summary": f"VIIRS satellite fire detection at {lat:.2f}, {lon:.2f};"
                       f" brightness {row.get('bright_ti4', '?')} K.",
            "link": "https://firms.modaps.eosdis.nasa.gov/map/"
                    f"#d:24hrs;@{lon:.1f},{lat:.1f},7z",
            "published": f"{day}T{time4[:2]}:{time4[2:]}:00Z" if day else "",
            "external_id": f"{day}-{time4}-{lat:.3f}-{lon:.3f}",
            "lat": lat, "lon": lon,
            "category": "disaster",
            "severity": 4 if frp >= 500 else 3,
            "who": "NASA FIRMS (VIIRS)",
            "what": f"wildfire thermal anomaly, {frp:.0f} MW radiative power",
        })
    return items
