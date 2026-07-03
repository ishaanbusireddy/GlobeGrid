"""Purges every _synthetic-flagged row in a single operation (Section 12.2,
Section 16 checklist), once the real pipeline is wired in for Phase 5.

Scope (matching what generate_synthetic_data.py creates):
  - story_members of synthetic stories
  - stories with causal_narrative._synthetic = true
  - events belonging to raw_items with raw_content._synthetic = true,
    plus those raw_items
  - instability_scores with component_breakdown._synthetic = true
  - the "Synthetic Generator" source row itself

Real extracted_facts are untouched — the generator never writes facts, and
the fact chain is never deleted (Section 5.9).

Usage: python scripts/purge_synthetic.py [--dry-run]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import text  # noqa: E402

from app.db.session import get_session  # noqa: E402

STATEMENTS = [
    ("story_members", """
        DELETE FROM story_members WHERE story_id IN (
            SELECT id FROM stories WHERE causal_narrative->>'_synthetic' = 'true')"""),
    ("stories", "DELETE FROM stories WHERE causal_narrative->>'_synthetic' = 'true'"),
    ("events", """
        DELETE FROM events WHERE raw_item_id IN (
            SELECT id FROM raw_items WHERE raw_content->>'_synthetic' = 'true')"""),
    ("raw_items", "DELETE FROM raw_items WHERE raw_content->>'_synthetic' = 'true'"),
    ("instability_scores", """
        DELETE FROM instability_scores WHERE component_breakdown->>'_synthetic' = 'true'"""),
    ("sources", "DELETE FROM sources WHERE name = 'Synthetic Generator'"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report counts without deleting")
    args = parser.parse_args()

    with get_session() as session:
        if args.dry_run:
            checks = [
                ("stories", "SELECT count(*) FROM stories WHERE causal_narrative->>'_synthetic' = 'true'"),
                ("events", """SELECT count(*) FROM events WHERE raw_item_id IN (
                    SELECT id FROM raw_items WHERE raw_content->>'_synthetic' = 'true')"""),
                ("raw_items", "SELECT count(*) FROM raw_items WHERE raw_content->>'_synthetic' = 'true'"),
                ("instability_scores",
                 "SELECT count(*) FROM instability_scores WHERE component_breakdown->>'_synthetic' = 'true'"),
            ]
            for table, sql in checks:
                print(f"would purge {session.execute(text(sql)).scalar()} row(s) from {table}")
            return

        # One transaction — the whole purge succeeds or none of it does.
        for table, sql in STATEMENTS:
            result = session.execute(text(sql))
            print(f"purged {result.rowcount} row(s) from {table}")


if __name__ == "__main__":
    main()
