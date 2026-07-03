"""Stage 4 (Section 2.1, 5.4): cross-stream correlation.

For every embedded event/fact not yet assigned to a story, this compares it
against:
  (a) other embedded events/facts within same_window_max_gap_hours — a
      "same_window" match if cosine similarity >= same_window_similarity_threshold.
  (b) the full historical fact chain (all extracted_facts with an embedding,
      no time gate) — a "historical_chain" match if cosine similarity >=
      historical_similarity_threshold.

Geographic overlap (geo_overlap_radius_km) is a secondary signal only per
Section 5.4 step 5: it never gates a match, but a borderline same-window
candidate (just under threshold) that also has geo overlap is still
accepted, per "two events in different locations can still be one story" —
i.e. geography can only help a match, never block one.

All thresholds/intervals are read from backend/config.yaml (Section 7.2),
never hardcoded.
"""
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Event, ExtractedFact, Story, StoryMember
from app.logging_setup import log_with_fields

logger = logging.getLogger("correlation")

# Secondary-signal tolerance: how far below same_window_similarity_threshold
# a candidate may fall and still be accepted if geo overlap corroborates it.
_GEO_ASSIST_MARGIN = 0.03


class _Candidate:
    __slots__ = ("kind", "id", "embedding", "occurred_at", "lat", "lon", "story_id", "event_id")

    def __init__(self, kind, id, embedding, occurred_at, lat, lon, story_id, event_id=None):
        self.kind = kind  # "event" | "fact"
        self.id = id
        self.embedding = embedding
        self.occurred_at = occurred_at
        self.lat = lat
        self.lon = lon
        self.story_id = story_id
        # For a fact, the parent event it was extracted from (if any) — a
        # fact and its own parent event describe the same underlying
        # occurrence, not independent cross-stream evidence, so they must
        # never be allowed to "correlate" with each other.
        self.event_id = event_id

    def _same_underlying_occurrence(self, other: "_Candidate") -> bool:
        if self.id == other.id and self.kind == other.kind:
            return True
        if self.kind == "event" and other.kind == "fact":
            return other.event_id == self.id
        if self.kind == "fact" and other.kind == "event":
            return self.event_id == other.id
        return False


def _cosine_similarity(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _event_point(session: Session, event_id) -> tuple[Optional[float], Optional[float]]:
    if event_id is None:
        return None, None
    geom = cast(Event.location, Geometry)
    row = session.execute(
        select(
            func.ST_Y(geom).label("lat"),
            func.ST_X(geom).label("lon"),
        ).where(Event.id == event_id, Event.location.isnot(None))
    ).first()
    return (row.lat, row.lon) if row else (None, None)


def _story_id_for(session: Session, kind: str, item_id) -> Optional[str]:
    col = StoryMember.event_id if kind == "event" else StoryMember.fact_id
    row = session.execute(select(StoryMember.story_id).where(col == item_id).limit(1)).first()
    return row.story_id if row else None


def _load_pool(session: Session) -> list[_Candidate]:
    """All embedded events + facts, for use as same-window / historical
    candidates. Loaded once per run_correlation() call — fine at v1,
    single-user scale (Section 3 rationale)."""
    pool = []

    for event in session.query(Event).filter(Event.embedding.isnot(None)).all():
        lat, lon = _event_point(session, event.id)
        pool.append(
            _Candidate("event", event.id, [float(v) for v in event.embedding], event.occurred_at, lat, lon,
                       _story_id_for(session, "event", event.id))
        )

    for fact in session.query(ExtractedFact).filter(ExtractedFact.embedding.isnot(None)).all():
        lat, lon = _event_point(session, fact.event_id) if fact.event_id else (None, None)
        pool.append(
            _Candidate("fact", fact.id, [float(v) for v in fact.embedding], fact.when_occurred, lat, lon,
                       _story_id_for(session, "fact", fact.id), event_id=fact.event_id)
        )

    return pool


def _uncorrelated(pool: list[_Candidate]) -> list[_Candidate]:
    return [c for c in pool if c.story_id is None]


def _best_match(item: _Candidate, candidates: list[_Candidate], threshold: float,
                 geo_radius_km: float, allow_geo_assist: bool) -> Optional[tuple[_Candidate, float]]:
    best = None
    best_sim = 0.0
    for other in candidates:
        if item._same_underlying_occurrence(other):
            continue
        sim = _cosine_similarity(item.embedding, other.embedding)

        accept = sim >= threshold
        if not accept and allow_geo_assist and sim >= threshold - _GEO_ASSIST_MARGIN:
            if None not in (item.lat, item.lon, other.lat, other.lon):
                if _haversine_km(item.lat, item.lon, other.lat, other.lon) <= geo_radius_km:
                    accept = True  # secondary geo signal corroborates a borderline match

        if accept and sim > best_sim:
            best = other
            best_sim = sim

    return (best, best_sim) if best else None


def _attach_to_story(session: Session, item: _Candidate, story_id, linked_via: str, now: datetime) -> None:
    session.add(
        StoryMember(
            story_id=story_id,
            event_id=item.id if item.kind == "event" else None,
            fact_id=item.id if item.kind == "fact" else None,
            linked_via=linked_via,
            linked_at=now,
        )
    )
    item.story_id = story_id


def _create_story(session: Session, now: datetime) -> Story:
    story = Story(first_seen_at=now, last_updated_at=now)
    session.add(story)
    session.flush()  # populate story.id
    return story


def run_correlation(session: Session, batch_size: int = 200) -> tuple[int, int, set]:
    """Correlates up to batch_size uncorrelated items against the same-window
    and historical pools. Returns (same_window_links, historical_links,
    touched_story_ids) — touched_story_ids drives Stage 5 causal-linking, since
    Section 5.5 requires narrative regeneration only when a cluster actually
    gains a member, never on every page view."""
    settings = get_settings()
    corr = settings.correlation()
    same_window_threshold = corr["same_window_similarity_threshold"]
    historical_threshold = corr["historical_similarity_threshold"]
    max_gap = timedelta(hours=corr["same_window_max_gap_hours"])
    geo_radius_km = corr["geo_overlap_radius_km"]

    pool = _load_pool(session)
    targets = _uncorrelated(pool)[:batch_size]

    same_window_links = historical_links = 0
    touched_story_ids = set()
    now = datetime.now(timezone.utc)

    for item in targets:
        if item.story_id is not None:
            continue  # picked up a story via an earlier match this batch

        window_candidates = [
            c for c in pool
            if c.id != item.id and abs((c.occurred_at - item.occurred_at)) <= max_gap
        ]
        match = _best_match(item, window_candidates, same_window_threshold, geo_radius_km, allow_geo_assist=True)
        linked_via = "same_window"

        if match is None:
            # (b) full historical fact chain, no time gate, cosine similarity only.
            historical_candidates = [c for c in pool if c.kind == "fact" and c.id != item.id]
            match = _best_match(item, historical_candidates, historical_threshold, geo_radius_km, allow_geo_assist=False)
            linked_via = "historical_chain"

        if match is None:
            continue

        other, similarity = match
        story_id = other.story_id or _create_story(session, now).id
        if other.story_id is None:
            _attach_to_story(session, other, story_id, linked_via, now)

        _attach_to_story(session, item, story_id, linked_via, now)

        story = session.get(Story, story_id)
        story.last_updated_at = now
        touched_story_ids.add(story_id)

        if linked_via == "same_window":
            same_window_links += 1
        else:
            historical_links += 1

        log_with_fields(
            logger, logging.INFO, "correlation match",
            item_kind=item.kind, item_id=str(item.id), story_id=str(story_id),
            linked_via=linked_via, similarity=round(similarity, 4),
        )

    log_with_fields(
        logger, logging.INFO, "correlation batch complete",
        same_window_links=same_window_links, historical_links=historical_links,
        candidates_considered=len(targets),
    )
    return same_window_links, historical_links, touched_story_ids
