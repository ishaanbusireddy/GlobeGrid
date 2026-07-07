#!/usr/bin/env python3
"""v3 §11 — walk the hash chains and confirm every hash matches.

    python scripts/verify_provenance.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.db.models import migrate  # noqa: E402
from backend.app.processing.provenance import verify_all  # noqa: E402

if __name__ == "__main__":
    migrate()
    result = verify_all()
    for chain in result["chains"]:
        state = "OK" if chain["ok"] else f"BROKEN at rowid {chain.get('broken_at_rowid')}"
        print(f"{chain['table']}: {state} ({chain['checked']} hashed rows checked)")
    print(f"\nchain integrity: {'VERIFIED' if result['ok'] else 'FAILED'}")
    print(result["scope_note"])
    sys.exit(0 if result["ok"] else 1)
