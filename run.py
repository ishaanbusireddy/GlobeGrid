#!/usr/bin/env python3
"""TalkDiplomacy Live — one-command launcher.

    python run.py               start everything, open the browser
    python run.py --no-browser  start without opening a browser

The synthetic/demo dataset was removed at the owner's request (v7.4.4): the
app now only ever shows REAL backend data. To clean any synthetic rows left
in an older database, run: python scripts/generate_synthetic_data.py --purge

Zero-install build: Python 3.10+ standard library only. No PostgreSQL, no
pip install, no npm. The database is a SQLite file created automatically
at backend/data/talkdiplomacy_live.db.

Optional (real causal narratives / translation): set CLAUDE_API_KEY in a
.env file at the repo root — copy backend/.env.example to .env.
"""

import sys
import threading
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

MIN_PY = (3, 10)
if sys.version_info < MIN_PY:
    sys.exit(f"Python {MIN_PY[0]}.{MIN_PY[1]}+ required, found {sys.version.split()[0]}")


def main() -> None:
    args = set(sys.argv[1:])
    from backend.app.main import create_app

    if "--synthetic" in args:
        # v7.4.4 — the demo dataset was deleted (owner: "delete the synthetic
        # data, I don't need it"). This flag no longer seeds anything; the app
        # shows only real backend data. Purge old rows with
        # scripts/generate_synthetic_data.py --purge.
        print("note: --synthetic was removed in v7.4.4; starting with real data only.")

    server = create_app()
    # use the actually-bound port — create_app falls back automatically if
    # the configured port is reserved (Windows excluded port ranges, etc.)
    url = f"http://localhost:{server.server_address[1]}"
    print(f"\n  TalkDiplomacy Live -> {url}   (Ctrl+C to stop)\n")
    if "--no-browser" not in args:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
