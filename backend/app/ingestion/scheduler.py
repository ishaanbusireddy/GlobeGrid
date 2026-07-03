"""APScheduler job registration (Section 13, Stage 1 of the pipeline —
Section 2.1). One job per registered source, at its configured interval
(Section 7.2 ingestion_intervals_seconds, overridden per-row by
sources.poll_interval_seconds). In-process; no Celery/Redis (Section 3.1).
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.models import Source
from app.db.session import get_session
from app.ingestion import common
from app.ingestion.sources import gdelt, market, reddit, rss, usgs
from app.logging_setup import log_with_fields

logger = logging.getLogger("scheduler")

_FETCHERS = {
    "rss": rss.fetch,
    "gdelt": gdelt.fetch,
    "usgs": usgs.fetch,
    "market": market.fetch,
    "reddit": reddit.fetch,
}


def _run_job(source_id) -> None:
    with get_session() as session:
        source = session.get(Source, source_id)
        if source is None:
            return

        fetch_fn = _FETCHERS.get(source.type)
        if fetch_fn is None:
            log_with_fields(
                logger, logging.ERROR, "no fetcher registered for source type",
                source_id=str(source.id), source_type=source.type,
            )
            return

        common.run_ingestion_job(session, source, fetch_fn)

        new_interval = common.current_interval_seconds(source)
        job = _scheduler.get_job(str(source.id)) if _scheduler else None
        if job is not None and job.trigger.interval.total_seconds() != new_interval:
            _scheduler.reschedule_job(
                str(source.id), trigger=IntervalTrigger(seconds=new_interval)
            )


_scheduler: BackgroundScheduler | None = None


def build_scheduler() -> BackgroundScheduler:
    global _scheduler
    scheduler = BackgroundScheduler()

    with get_session() as session:
        sources = session.query(Source).all()
        for source in sources:
            scheduler.add_job(
                _run_job,
                trigger=IntervalTrigger(seconds=source.poll_interval_seconds),
                args=[source.id],
                id=str(source.id),
                coalesce=True,
                max_instances=1,
            )

    _scheduler = scheduler
    return scheduler


def start() -> BackgroundScheduler:
    scheduler = build_scheduler()
    scheduler.start()
    log_with_fields(logger, logging.INFO, "scheduler started", job_count=len(scheduler.get_jobs()))
    return scheduler
