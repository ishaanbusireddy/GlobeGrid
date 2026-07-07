#!/usr/bin/env python3
"""TalkDiplomacy Live — one-command launcher.

    python run.py               start everything, open the browser
    python run.py --no-browser  start without opening a browser
    python run.py --synthetic   seed the Section 12 demo dataset first
                                (purge later with:
                                 python scripts/generate_synthetic_data.py --purge)

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
        from backend.app.db.models import migrate
        migrate()
        import scripts.generate_synthetic_data as synth
        synth.generate()

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
