"""Instability index (Section 5.6): one composite 0-100 number reflecting
how tense/chaotic the world is right now.

v1 formula (locked): weighted sum of (event volume, average severity tag,
number of distinct regions involved) over the rolling window, normalized to
0-100. Weights, recompute interval, and window all come from config.yaml's
instability: section (Section 7.2) — never hardcoded.

Computed on a schedule (registered in ingestion/scheduler.py); every reading
is appended to instability_scores with a component_breakdown for
transparency (Section 6.7). Score history is retained indefinitely.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Event, InstabilityScore
from app.logging_setup import log_with_fields

logger = logging.getLogger("instability")

# Normalization ceilings: the event volume / distinct-region counts at which
# each sub-score saturates at 1.0. These are scale anchors for the 0-100
# output range, not tunable behavior thresholds — the *weights* between
# components are the Section 7.2 tunables.
VOLUME_CEILING = 200.0
SPREAD_CEILING = 40.0
SEVERITY_CEILING = 5.0  # severity is already a 1-5 scale (Section 6.3)


def compute_score(session: Session) -> InstabilityScore:
    settings = get_settings()
    cfg = settings.instability()
    window_start = datetime.now(timezone.utc) - timedelta(hours=cfg["rolling_window_hours"])

    events = session.query(Event).filter(Event.occurred_at >= window_start).all()

    volume = len(events)
    avg_severity = (sum(e.severity for e in events) / volume) if volume else 0.0
    regions = len({e.location_name for e in events if e.location_name})

    volume_component = min(volume / VOLUME_CEILING, 1.0)
    severity_component = avg_severity / SEVERITY_CEILING
    spread_component = min(regions / SPREAD_CEILING, 1.0)

    score = 100.0 * (
        cfg["weight_volume"] * volume_component
        + cfg["weight_severity"] * severity_component
        + cfg["weight_spread"] * spread_component
    )
    score = round(min(max(score, 0.0), 100.0), 2)

    row = InstabilityScore(
        score=score,
        computed_at=datetime.now(timezone.utc),
        component_breakdown={
            "volume": {"events_in_window": volume, "component": round(volume_component, 4)},
            "severity": {"average": round(avg_severity, 2), "component": round(severity_component, 4)},
            "spread": {"distinct_regions": regions, "component": round(spread_component, 4)},
            "weights": {
                "volume": cfg["weight_volume"],
                "severity": cfg["weight_severity"],
                "spread": cfg["weight_spread"],
            },
            "window_hours": cfg["rolling_window_hours"],
        },
    )
    session.add(row)

    log_with_fields(
        logger, logging.INFO, "instability score computed",
        score=score, events_in_window=volume, distinct_regions=regions,
        avg_severity=round(avg_severity, 2),
    )
    return row
