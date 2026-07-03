"""Runs one full Phase 1 pass synchronously: ingest every registered source
once, extract raw_items into events/extracted_facts, embed anything new.
Useful for validating the data layer before wiring up the scheduler/API.

Usage: python scripts/run_ingestion_once.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.models import Source  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.ingestion import common  # noqa: E402
from app.ingestion.sources import gdelt, market, reddit, rss, usgs  # noqa: E402
from app.logging_setup import setup_logging  # noqa: E402
from app.processing.embed import run_embedding  # noqa: E402
from app.processing.extract import run_extraction  # noqa: E402

FETCHERS = {
    "rss": rss.fetch,
    "gdelt": gdelt.fetch,
    "usgs": usgs.fetch,
    "market": market.fetch,
    "reddit": reddit.fetch,
}


def main() -> None:
    setup_logging()

    with get_session() as session:
        sources = session.query(Source).all()
        print(f"Ingesting {len(sources)} source(s)...")
        for source in sources:
            fetch_fn = FETCHERS.get(source.type)
            if fetch_fn is None:
                print(f"  skip {source.name}: no fetcher for type={source.type}")
                continue
            common.run_ingestion_job(session, source, fetch_fn)
            print(f"  {source.name}: {source.health_status} (last_error={source.last_error})")

    with get_session() as session:
        succeeded, failed = run_extraction(session)
        print(f"Extraction: {succeeded} succeeded, {failed} failed")

    try:
        with get_session() as session:
            events_embedded, facts_embedded = run_embedding(session)
            print(f"Embedding: {events_embedded} events, {facts_embedded} facts")
    except Exception as exc:  # noqa: BLE001 - e.g. first-run model download needs network
        print(f"Embedding step failed: {exc}")


if __name__ == "__main__":
    main()
