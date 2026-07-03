"""Stage 2 (Section 2.1): raw_item -> normalized events record + structured
extracted_facts row(s) (Section 5.9, the permanent fact chain).

The build manual specifies the schema (Section 6) and that "each raw item is
parsed into a normalized events record" but does not specify a
categorization/severity algorithm — this module implements a straightforward
keyword/magnitude-based heuristic per source type, isolated in
_classify_category_and_severity() and the per-source parsers below, so it
can be swapped for something smarter later without touching the pipeline
wiring in run_extraction().

Every processed raw_item is marked processed=True whether it succeeds or
fails (processing_error set on failure) — raw_items are never deleted, and a
single bad item never blocks the rest of the batch (Section 2.3).
"""
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Event, ExtractedFact, RawItem, Source
from app.logging_setup import log_with_fields

logger = logging.getLogger("extraction")

_CATEGORY_KEYWORDS = {
    "conflict": ["war", "conflict", "military", "attack", "strike", "invasion", "troops", "ceasefire"],
    "disaster": ["earthquake", "flood", "hurricane", "wildfire", "tsunami", "eruption", "disaster"],
    "finance": ["market", "stock", "currency", "inflation", "interest rate", "trade", "economy", "bank"],
    "geopolitics": ["election", "president", "minister", "sanctions", "diplomat", "summit", "treaty", "policy"],
}


def _classify_category_and_severity(text: str) -> tuple[str, int]:
    lowered = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            severity = 3 if category in ("conflict", "disaster") else 2
            return category, severity
    return "other", 1


def _magnitude_to_severity(magnitude: Optional[float]) -> int:
    if magnitude is None:
        return 1
    if magnitude < 3:
        return 1
    if magnitude < 4:
        return 2
    if magnitude < 5:
        return 3
    if magnitude < 6:
        return 4
    return 5


def _pct_change_to_severity(pct: float) -> int:
    pct = abs(pct)
    if pct < 0.5:
        return 1
    if pct < 1.5:
        return 2
    if pct < 3:
        return 3
    if pct < 5:
        return 4
    return 5


def _parse_rss(raw: dict) -> dict:
    title = raw.get("title") or ""
    summary = re.sub("<[^<]+?>", "", raw.get("summary") or "")
    category, severity = _classify_category_and_severity(f"{title} {summary}")

    occurred_at = datetime.now(timezone.utc)
    if raw.get("published"):
        try:
            occurred_at = parsedate_to_datetime(raw["published"])
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass

    return {
        "title": title,
        "description": summary or title,
        "location_name": None,
        "location": None,
        "category": category,
        "severity": severity,
        "occurred_at": occurred_at,
        "who": "unspecified",
        "what": title,
        "where": None,
    }


def _parse_gdelt(raw: dict) -> dict:
    title = raw.get("title") or ""
    country = raw.get("sourcecountry")
    category, severity = _classify_category_and_severity(title)

    occurred_at = datetime.now(timezone.utc)
    seendate = raw.get("seendate")
    if seendate:
        try:
            occurred_at = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return {
        "title": title,
        "description": title,
        "location_name": country,
        "location": None,
        "category": category,
        "severity": severity,
        "occurred_at": occurred_at,
        "who": raw.get("domain") or "unspecified",
        "what": title,
        "where": country,
    }


def _parse_usgs(raw: dict) -> dict:
    props = raw.get("properties", {})
    geom = raw.get("geometry", {})
    coords = geom.get("coordinates") or [None, None, None]
    lon, lat = coords[0], coords[1]
    place = props.get("place") or "Unknown location"
    magnitude = props.get("mag")

    occurred_at = datetime.now(timezone.utc)
    time_ms = props.get("time")
    if time_ms:
        occurred_at = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)

    title = f"M{magnitude} earthquake — {place}" if magnitude is not None else f"Earthquake — {place}"

    return {
        "title": title,
        "description": title,
        "location_name": place,
        "location": f"POINT({lon} {lat})" if lon is not None and lat is not None else None,
        "category": "disaster",
        "severity": _magnitude_to_severity(magnitude),
        "occurred_at": occurred_at,
        "who": "USGS",
        "what": title,
        "where": place,
    }


def _parse_market(raw: dict) -> dict:
    meta = raw.get("Meta Data", {})
    symbol = meta.get("2. Symbol", "unknown symbol")
    series_key = next((k for k in raw if k.startswith("Time Series")), None)
    series = raw.get(series_key, {}) if series_key else {}
    timestamps = sorted(series.keys(), reverse=True)

    pct_change = 0.0
    latest_ts = None
    if len(timestamps) >= 2:
        latest_ts, prev_ts = timestamps[0], timestamps[1]
        latest_close = float(series[latest_ts]["4. close"])
        prev_close = float(series[prev_ts]["4. close"])
        if prev_close:
            pct_change = (latest_close - prev_close) / prev_close * 100
    elif timestamps:
        latest_ts = timestamps[0]

    direction = "rose" if pct_change >= 0 else "dropped"
    title = f"{symbol} {direction} {abs(pct_change):.2f}%"

    occurred_at = datetime.now(timezone.utc)
    if latest_ts:
        try:
            occurred_at = datetime.strptime(latest_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return {
        "title": title,
        "description": title,
        "location_name": None,
        "location": None,
        "category": "finance",
        "severity": _pct_change_to_severity(pct_change),
        "occurred_at": occurred_at,
        "who": symbol,
        "what": title,
        "where": None,
    }


def _parse_reddit(raw: dict) -> dict:
    title = raw.get("title") or ""
    subreddit = raw.get("subreddit") or "unspecified"
    score = raw.get("score") or 0
    category, severity = _classify_category_and_severity(f"{subreddit} {title}")
    if score > 5000:
        severity = min(severity + 1, 5)

    occurred_at = datetime.now(timezone.utc)
    created_utc = raw.get("created_utc")
    if created_utc:
        occurred_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)

    return {
        "title": title,
        "description": title,
        "location_name": None,
        "location": None,
        "category": category,
        "severity": severity,
        "occurred_at": occurred_at,
        "who": f"r/{subreddit}",
        "what": title,
        "where": None,
    }


_PARSERS = {
    "rss": _parse_rss,
    "gdelt": _parse_gdelt,
    "usgs": _parse_usgs,
    "market": _parse_market,
    "reddit": _parse_reddit,
}


def extract_one(session: Session, raw_item: RawItem, source: Source) -> None:
    parser = _PARSERS.get(source.type)
    if parser is None:
        raise RuntimeError(f"no extraction parser registered for source type {source.type!r}")

    normalized = parser(raw_item.raw_content)

    event = Event(
        raw_item_id=raw_item.id,
        title=normalized["title"],
        description=normalized["description"],
        location=normalized["location"],
        location_name=normalized["location_name"],
        category=normalized["category"],
        severity=normalized["severity"],
        occurred_at=normalized["occurred_at"],
    )
    session.add(event)
    session.flush()  # populate event.id for the fact FK below

    session.add(
        ExtractedFact(
            event_id=event.id,
            source_id=source.id,
            who=normalized["who"],
            what=normalized["what"],
            where=normalized["where"],
            when_occurred=normalized["occurred_at"],
            created_at=datetime.now(timezone.utc),
        )
    )


def run_extraction(session: Session, batch_size: int = 200) -> tuple[int, int]:
    """Processes up to batch_size unprocessed raw_items. Returns (succeeded, failed)."""
    raw_items = (
        session.query(RawItem)
        .filter(RawItem.processed.is_(False))
        .limit(batch_size)
        .all()
    )

    succeeded = failed = 0
    for raw_item in raw_items:
        source = session.get(Source, raw_item.source_id)
        try:
            extract_one(session, raw_item, source)
            raw_item.processed = True
            raw_item.processing_error = None
            succeeded += 1
        except Exception as exc:  # noqa: BLE001 - one bad item must not block the batch
            raw_item.processed = True
            raw_item.processing_error = str(exc)
            failed += 1
            log_with_fields(
                logger, logging.ERROR, "extraction failed for raw_item",
                raw_item_id=str(raw_item.id), error=str(exc),
            )

    log_with_fields(
        logger, logging.INFO, "extraction batch complete",
        succeeded=succeeded, failed=failed,
    )
    return succeeded, failed
