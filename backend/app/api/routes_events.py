"""GET /api/events (Section 8.1)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import Geometry
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from app.api.common import event_point, parse_bbox, parse_since, source_and_link
from app.db.models import Event, RawItem
from app.db.session import get_db

router = APIRouter(prefix="/api/events", tags=["events"])

DEFAULT_LIMIT = 500


@router.get("")
def list_events(
    bbox: Optional[str] = None,
    category: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    session: Session = Depends(get_db),
):
    """Events within a map bounding box (Section 8.1). bbox is optional —
    "min_lon,min_lat,max_lon,max_lat"; when present, events with no
    resolvable location are naturally excluded (Section 5.2)."""
    query = session.query(Event)

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
        query = query.filter(
            Event.location.isnot(None),
            func.ST_Intersects(cast(Event.location, Geometry), envelope),
        )

    events = query.order_by(Event.occurred_at.desc()).limit(max(1, min(limit, 2000))).all()

    payload = []
    for event in events:
        raw_item = session.get(RawItem, event.raw_item_id)
        link_info = source_and_link(session, source_id=raw_item.source_id if raw_item else None, raw_item=raw_item)
        payload.append({
            "id": str(event.id),
            "title": event.title,
            "description": event.description,
            "location": event_point(session, event),
            "location_name": event.location_name,
            "category": event.category,
            "severity": event.severity,
            "occurred_at": event.occurred_at,
            **link_info,
        })

    return payload
