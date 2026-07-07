"""SQLite connection management (zero-install adaptation of Section 3/6).

One connection per thread (SQLite requirement), WAL mode so the ingestion
threads, pipeline thread, and API server can read/write concurrently.

v6.4 — hardened against the Windows hang that made every DB-touching feature
(analyst, translation) stall forever while pure-network features (the Groq
ping) worked:

- `PRAGMA journal_mode=WAL` is set ONCE, on the first connection, not on every
  new thread's connection. Re-asserting WAL per-connection while other threads
  are mid-write can block hard on Windows (mandatory file locking), which is
  exactly the "a feature that opens a DB connection in a fresh thread hangs"
  symptom. New connections only set the cheap per-connection pragmas.
- Every connection gets an explicit `busy_timeout` so a lock wait is BOUNDED
  and raises `OperationalError` instead of hanging.
- The global write lock is a REENTRANT lock acquired with a timeout: a nested
  write (write_tx inside write_tx on one thread) can no longer self-deadlock,
  and genuine lock starvation surfaces as a clear error instead of an infinite
  stall.
"""

import logging
import sqlite3
import threading

from ..config import sqlite_path

log = logging.getLogger("db")

_local = threading.local()
# v6.4 — REENTRANT so a nested write_tx on the same thread can't self-deadlock.
_write_lock = threading.RLock()
_wal_ready = False
_wal_guard = threading.Lock()

# how long a write may wait for the serialization lock before giving up with a
# clear error (instead of hanging the request forever)
_WRITE_LOCK_TIMEOUT_S = 20.0
# SQLite busy handler: how long a statement waits on a file lock (ms)
_BUSY_TIMEOUT_MS = 8000


class WriteLockTimeout(OSError):
    """Raised when a write couldn't acquire the serialization lock in time —
    surfaced to the caller as a real error rather than an unbounded hang.
    Subclasses OSError so the existing best-effort handlers across the app
    (which already catch OSError) degrade gracefully instead of 500-ing."""


def _ensure_wal() -> None:
    """Set journal_mode=WAL exactly once, on a short-lived dedicated
    connection, before any per-thread connections start. Idempotent."""
    global _wal_ready
    if _wal_ready:
        return
    with _wal_guard:
        if _wal_ready:
            return
        conn = sqlite3.connect(str(sqlite_path()), timeout=30)
        try:
            conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.commit()
        finally:
            conn.close()
        _wal_ready = True


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        _ensure_wal()   # WAL is a DB-level persistent setting — set once, globally
        conn = sqlite3.connect(str(sqlite_path()), timeout=30)
        conn.row_factory = sqlite3.Row
        # per-connection pragmas only — NOT journal_mode (already WAL): cheap,
        # never contend on a file lock the way re-asserting WAL can on Windows.
        conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return conn


class write_tx:
    """Serialized write transaction: `with write_tx() as conn: ...`

    v6.4 — the lock is reentrant and acquired with a timeout, so a nested write
    on one thread can't deadlock and a stuck writer surfaces as a clear error
    instead of hanging the caller forever."""

    def __enter__(self) -> sqlite3.Connection:
        if not _write_lock.acquire(timeout=_WRITE_LOCK_TIMEOUT_S):
            raise WriteLockTimeout(
                f"could not acquire the DB write lock within {_WRITE_LOCK_TIMEOUT_S}s "
                "(a writer is stuck or the DB is heavily contended)")
        self.conn = get_conn()
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            _write_lock.release()
        return False


def query(sql: str, params=()) -> list[sqlite3.Row]:
    return get_conn().execute(sql, params).fetchall()


def query_one(sql: str, params=()):
    return get_conn().execute(sql, params).fetchone()
