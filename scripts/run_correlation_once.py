"""Runs one correlation + causal-linking pass over whatever is already in
the database (Phase 1's ingest -> extract -> embed output). Useful for
validating Phase 2 without wiring up the scheduler/API yet.

Usage: python scripts/run_correlation_once.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.session import get_session  # noqa: E402
from app.logging_setup import setup_logging  # noqa: E402
from app.processing.causal_link import run_causal_linking  # noqa: E402
from app.processing.correlate import run_correlation  # noqa: E402


def main() -> None:
    setup_logging()

    with get_session() as session:
        same_window, historical, touched = run_correlation(session)
        print(f"Correlation: {same_window} same-window link(s), {historical} historical-chain link(s), "
              f"{len(touched)} story(s) touched")

    if not touched:
        print("No stories touched — nothing to causal-link.")
        return

    try:
        with get_session() as session:
            succeeded, failed = run_causal_linking(session, touched)
            print(f"Causal linking: {succeeded} succeeded, {failed} failed")
    except Exception as exc:  # noqa: BLE001 - e.g. CLAUDE_API_KEY not configured/no network
        print(f"Causal linking step failed: {exc}")


if __name__ == "__main__":
    main()
