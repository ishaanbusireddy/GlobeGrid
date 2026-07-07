#!/usr/bin/env python3
"""Seed/refresh the Section 4 source list (idempotent).
Run automatically at startup; standalone use: python scripts/seed_sources.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.db.models import migrate  # noqa: E402
from backend.app.ingestion.seed import seed_sources  # noqa: E402

if __name__ == "__main__":
    migrate()
    added = seed_sources()
    print(f"sources seeded (new: {added})")
