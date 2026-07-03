"""Map-related endpoints supporting the world map view (Section 5.2, 8.1).

Section 8.1 only locks GET /api/events for map bounding-box queries; this
adds the pin-density clustering behavior Section 5.2 describes ("Pin density
above a threshold collapses into a cluster marker showing count; clicking
expands") as a server-side convenience so the frontend doesn't have to
reimplement it — cluster_pin_threshold/cluster_radius_km come straight from
backend/config.yaml's map: section, never hardcoded.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import Geometry
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from app.api.common import event_point, parse_bbox, parse_since
from app.config import get_settings
from app.db.models import Event
from app.db.session import get_db

router = APIRouter(prefix="/api/map", tags=["map"])

_EARTH_RADIUS_KM = 6371.0


def _haversine_km(a: list[float], b: list[float]) -> float:
    import math

    lon1, lat1 = a
    lon2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(x))


def _cluster(points: list[dict], radius_km: float, pin_threshold: int) -> list[dict]:
    """Greedy radius clustering: any pin within radius_km of a cluster's
    running centroid joins that cluster. Groups larger than pin_threshold are
    emitted as a single cluster marker with a count; smaller groups are
    emitted as individual pins (Section 5.2)."""
    remaining = list(points)
    clusters = []

    while remaining:
        seed = remaining.pop(0)
        group = [seed]
        still_remaining = []
        for point in remaining:
            if _haversine_km(seed["location"], point["location"]) <= radius_km:
                group.append(point)
            else:
                still_remaining.append(point)
        remaining = still_remaining

        if len(group) > pin_threshold:
            avg_lon = sum(p["location"][0] for p in group) / len(group)
            avg_lat = sum(p["location"][1] for p in group) / len(group)
            clusters.append({
                "type": "cluster",
                "location": [avg_lon, avg_lat],
                "count": len(group),
                "event_ids": [p["id"] for p in group],
            })
        else:
            clusters.extend({"type": "pin", **p} for p in group)

    return clusters


@router.get("/clusters")
def map_clusters(
    bbox: Optional[str] = None,
    category: Optional[str] = None,
    since: Optional[str] = None,
    session: Session = Depends(get_db),
):
    settings = get_settings()
    map_config = settings.map()

    query = session.query(Event).filter(Event.location.isnot(None))

    since_dt = parse_since(since)
    if since_dt is not None:
        query = query.filter(Event.occurred_at >= since_dt)
    if category:
        query = query.filter(Event.category == category)

    try:
        bounds = parse_bbox(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if bounds is not None:
        min_lon, min_lat, max_lon, max_lat = bounds
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        query = query.filter(func.ST_Intersects(cast(Event.location, Geometry), envelope))

    events = query.all()
    points = [
        {"id": str(e.id), "location": event_point(session, e), "category": e.category, "severity": e.severity}
        for e in events
    ]
    points = [p for p in points if p["location"] is not None]

    return _cluster(points, map_config["cluster_radius_km"], map_config["cluster_pin_threshold"])
