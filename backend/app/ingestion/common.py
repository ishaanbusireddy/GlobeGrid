"""Shared ingestion helpers: persisting raw items and updating source health,
including the exponential backoff policy in Section 10.2.

Each source module exposes fetch(source) -> list[dict], returning unmodified
payloads. run_ingestion_job() wraps that call in the failure-isolation model
from Section 2.3 / 10.2: a failure here updates health_status/last_error and
is logged, never raised to the scheduler.
"""
import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import RawItem, Source
from app.logging_setup import log_with_fields

logger = logging.getLogger("ingestion")

# In-memory backoff state per source id: current effective interval override.
# Not persisted — Section 6.1 has no field for it, and it resets to
# poll_interval_seconds on the next successful fetch (Section 10.2).
_backoff_seconds: dict = {}


def current_interval_seconds(source: Source) -> int:
    return _backoff_seconds.get(source.id, source.poll_interval_seconds)


def run_ingestion_job(session: Session, source: Source, fetch_fn: Callable[[Source], list]) -> None:
    settings = get_settings()
    resilience = settings.resilience()
    start = datetime.now(timezone.utc)

    try:
        items = fetch_fn(source)
        for raw_content in items:
            session.add(
                RawItem(
                    source_id=source.id,
                    raw_content=raw_content,
                    fetched_at=start,
                    processed=False,
                )
            )
        source.health_status = "ok"
        source.last_fetched_at = start
        source.last_error = None
        _backoff_seconds.pop(source.id, None)

        duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        log_with_fields(
            logger,
            logging.INFO,
            "ingestion job succeeded",
            source_id=str(source.id),
            status="ok",
            item_count=len(items),
            duration_ms=duration_ms,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 - a dead source must never raise to the scheduler
        prior = current_interval_seconds(source)
        backed_off = min(
            int(prior * resilience["backoff_multiplier"]),
            resilience["max_backoff_seconds"],
        )
        _backoff_seconds[source.id] = max(backed_off, source.poll_interval_seconds)

        source.health_status = "degraded" if source.health_status == "ok" else "down"
        source.last_error = str(exc)

        duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        log_with_fields(
            logger,
            logging.ERROR,
            "ingestion job failed",
            source_id=str(source.id),
            status=source.health_status,
            item_count=0,
            duration_ms=duration_ms,
            error=str(exc),
        )
