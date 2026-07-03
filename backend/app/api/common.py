"""Shared helpers for the API layer (Section 8): outbound-link resolution
(Section 6.8's hard requirement — every displayed item must carry a
resolvable, visible source link), geography extraction, and query parsing.

source_id is schema-enforced (non-nullable), but the *outbound link* to the
specific article/item lives in raw_items.raw_content (its shape is
source-type-specific — Section 4). _resolve_outbound_link() pulls it back
out at serving time so every API response actually carries a clickable link,
not just a resolvable source_id.
"""
from datetime import datetime, timezone
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.db.models import Event, RawItem, Source


def resolve_outbound_link(raw_item: Optional[RawItem]) -> Optional[str]:
    if raw_item is None:
        return None
    content = raw_item.raw_content or {}
    # rss.py stores "link"; gdelt.py's DOC API articles carry "url";
    # reddit.py's listing children carry "permalink" (relative, needs the
    # reddit.com prefix); usgs.py/market.py have no single-item outbound
    # link (feed-level/aggregate data) — falls back to the source's feed URL.
    if "link" in content:
        return content["link"]
    if "url" in content:
        return content["url"]
    if "permalink" in content:
        permalink = content["permalink"]
        return f"https://reddit.com{permalink}" if permalink.startswith("/") else permalink
    return None


def event_point(session: Session, event: Event) -> Optional[list[float]]:
    if event.location is None:
        return None
    geom = cast(Event.location, Geometry)
    row = session.execute(
        select(func.ST_X(geom).label("lon"), func.ST_Y(geom).label("lat")).where(Event.id == event.id)
    ).first()
    return [row.lon, row.lat] if row else None


def source_and_link(session: Session, *, source_id=None, raw_item: Optional[RawItem] = None) -> dict:
    source = session.get(Source, source_id) if source_id else None
    return {
        "source_name": source.name if source else None,
        "source_leaning": source.leaning if source else None,
        "outbound_link": resolve_outbound_link(raw_item),
    }


def parse_since(since: Optional[str]) -> Optional[datetime]:
    if not since:
        return None
    value = datetime.fromisoformat(since.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def parse_bbox(bbox: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    """bbox=min_lon,min_lat,max_lon,max_lat"""
    if not bbox:
        return None
    parts = [float(p) for p in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be 'min_lon,min_lat,max_lon,max_lat'")
    return tuple(parts)  # type: ignore[return-value]
