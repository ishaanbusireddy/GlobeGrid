"""DB-layer smoke tests — migration idempotence, the events-category CHECK,
write_tx reentrancy and concurrency. Each scenario runs in a fresh SUBPROCESS
against a throwaway sqlite file because config.py reads DATABASE_URL at import
time: once app.db.session is imported, its connection target is fixed, so an
in-process env swap would silently keep writing to the developer's real DB.
The subprocess boundary is the only honest isolation."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _run(snippet: str) -> subprocess.CompletedProcess:
    """Run `snippet` in a fresh interpreter against a fresh temp DB."""
    tmp = tempfile.mkdtemp(prefix="gg_test_db_")
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{tmp}/test.db"
    pre = ("import sys\n"
           f"sys.path.insert(0, {str(REPO / 'backend')!r})\n")
    return subprocess.run([sys.executable, "-c", pre + snippet],
                          capture_output=True, text=True, env=env,
                          cwd=str(REPO), timeout=120)


class TestMigration(unittest.TestCase):
    def test_migrate_twice_is_idempotent(self):
        r = _run(
            "from app.db.models import migrate, SCHEMA_VERSION\n"
            "from app.db.session import query_one\n"
            "migrate()\n"
            "migrate()\n"
            "v = query_one('SELECT MAX(version) AS v FROM schema_migrations')\n"
            "assert v and v['v'] == SCHEMA_VERSION, dict(v or {})\n"
            "print('MIGRATE_OK')\n")
        self.assertIn("MIGRATE_OK", r.stdout, r.stderr[-2000:])

    def test_events_check_admits_v8_13_taxonomy(self):
        # The v8.13.0 root-cause bug: 'technology' was in the classifier but
        # not the CHECK, so every tech insert rolled the pipeline back.
        r = _run(
            "from app.db.models import migrate\n"
            "from app.db.session import query_one\n"
            "migrate()\n"
            "ddl = query_one(\"SELECT sql FROM sqlite_master WHERE name='events'\")['sql']\n"
            "for cat in ('technology','domestic','health','conflict','other'):\n"
            "    assert f\"'{cat}'\" in ddl, cat\n"
            "print('CHECK_OK')\n")
        self.assertIn("CHECK_OK", r.stdout, r.stderr[-2000:])


class TestWriteTx(unittest.TestCase):
    def test_nested_write_tx_does_not_deadlock(self):
        # v6.4 — the global write lock is an RLock; nesting must return fast,
        # not self-deadlock (the pre-v6.4 Windows hang class).
        r = _run(
            "from app.db.models import migrate\n"
            "from app.db.session import write_tx\n"
            "import time\n"
            "migrate()\n"
            "t0 = time.monotonic()\n"
            "with write_tx() as c1:\n"
            "    with write_tx() as c2:\n"
            "        c2.execute(\"INSERT OR REPLACE INTO app_meta(key,value)"
            " VALUES('t','1')\")\n"
            "assert time.monotonic() - t0 < 5\n"
            "print('NESTED_OK')\n")
        self.assertIn("NESTED_OK", r.stdout, r.stderr[-2000:])

    def test_concurrent_writers_finish(self):
        r = _run(
            "from app.db.models import migrate\n"
            "from app.db.session import write_tx, query_one\n"
            "import threading\n"
            "migrate()\n"
            "def w(i):\n"
            "    for j in range(5):\n"
            "        with write_tx() as c:\n"
            "            c.execute(\"INSERT OR REPLACE INTO app_meta(key,value)"
            " VALUES(?,?)\", (f'k{i}', str(j)))\n"
            "ts = [threading.Thread(target=w, args=(i,)) for i in range(8)]\n"
            "[t.start() for t in ts]\n"
            "[t.join(timeout=30) for t in ts]\n"
            "assert not any(t.is_alive() for t in ts), 'stuck writer thread'\n"
            "assert query_one(\"SELECT value FROM app_meta WHERE key='k7'\")\n"
            "print('CONCURRENT_OK')\n")
        self.assertIn("CONCURRENT_OK", r.stdout, r.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
