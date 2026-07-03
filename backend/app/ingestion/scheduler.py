"""APScheduler job registration (Section 13). In-process, no Celery/Redis
(Section 3.1). Registers:
  - one ingestion job per registered source (Stage 1), at its configured
    interval (Section 7.2 / sources.poll_interval_seconds), with the
    Section 10.2 backoff applied on failure;
  - one pipeline job running Stages 2-5 (extract -> embed -> correlate ->
    causal-link) over whatever new raw_items have accumulated, at the
    shortest configured ingestion interval (derived from config, not a new
    hardcoded tunable) — each stage wrapped in its own error boundary
    (Section 2.3);
  - the instability job (Section 5.6) at recompute_interval_seconds.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
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


def _run_pipeline() -> None:
    """Stages 2-5 over newly ingested raw_items. Each stage has its own
    error boundary — a failure in one never blocks the others or the
    scheduler (Section 2.3, 10.2)."""
    from app.processing.extract import run_extraction

    touched = set()
    try:
        with get_session() as session:
            run_extraction(session)
    except Exception as exc:  # noqa: BLE001
        log_with_fields(logger, logging.ERROR, "extraction stage failed", error=str(exc))

    try:
        from app.processing.embed import run_embedding
        with get_session() as session:
            run_embedding(session)
    except Exception as exc:  # noqa: BLE001 - e.g. model download unavailable
        log_with_fields(logger, logging.ERROR, "embedding stage failed", error=str(exc))

    try:
        from app.processing.correlate import run_correlation
        with get_session() as session:
            _, _, touched = run_correlation(session)
    except Exception as exc:  # noqa: BLE001
        log_with_fields(logger, logging.ERROR, "correlation stage failed", error=str(exc))

    if touched and get_settings().claude_api_key:
        try:
            from app.processing.causal_link import run_causal_linking
            with get_session() as session:
                run_causal_linking(session, touched)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(logger, logging.ERROR, "causal-link stage failed", error=str(exc))


def _run_instability() -> None:
    try:
        from app.processing.instability import compute_score
        with get_session() as session:
            compute_score(session)
    except Exception as exc:  # noqa: BLE001
        log_with_fields(logger, logging.ERROR, "instability job failed", error=str(exc))


_scheduler: BackgroundScheduler | None = None


def build_scheduler() -> BackgroundScheduler:
    global _scheduler
    scheduler = BackgroundScheduler()
    settings = get_settings()

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

    pipeline_interval = min(settings.ingestion_intervals_seconds().values())
    scheduler.add_job(
        _run_pipeline,
        trigger=IntervalTrigger(seconds=pipeline_interval),
        id="pipeline_stages_2_to_5",
        coalesce=True,
        max_instances=1,
    )

    scheduler.add_job(
        _run_instability,
        trigger=IntervalTrigger(seconds=settings.instability()["recompute_interval_seconds"]),
        id="instability_index",
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
