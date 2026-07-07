"""Section 4.3 — USGS earthquake GeoJSON feed (free, no key)."""

from ..http import fetch_json


def _severity_from_magnitude(mag: float) -> int:
    if mag >= 7.0:
        return 5
    if mag >= 6.0:
        return 4
    if mag >= 5.0:
        return 3
    if mag >= 4.0:
        return 2
    return 1


def fetch(source: dict) -> list[dict]:
    data = fetch_json(source["url"])
    items = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [None, None])
        mag = props.get("mag") or 0.0
        place = props.get("place") or "unknown location"
        items.append({
            "title": props.get("title") or f"M {mag} — {place}",
            "summary": f"Magnitude {mag} earthquake, {place}, depth "
                       f"{coords[2] if len(coords) > 2 else '?'} km.",
            "link": props.get("url", ""),
            "published": str((props.get("time") or 0) / 1000.0),
            "external_id": feature.get("id"),
            "lat": coords[1], "lon": coords[0],
            "location_name": place,
            "category": "disaster",
            "severity": _severity_from_magnitude(float(mag)),
            "who": "USGS seismic network",
            "what": f"magnitude {mag} earthquake near {place}",
        })
    return items
