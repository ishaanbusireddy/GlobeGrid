"""USGS earthquake ingestion (Section 4.3). Real-time GeoJSON feed, no key."""
import httpx

from app.db.models import Source


def fetch(source: Source) -> list[dict]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(source.url)
        resp.raise_for_status()
        data = resp.json()
    return data.get("features", [])
