"""v6.6.6 — background profile synthesis.

Leader/party/stat AI syntheses used to run the LLM call INSIDE the request
handler. With a local Ollama provider a single 800-token generation can take
20-60s, which blew the client-side fetch timeout (leader-profile 12s, others
25s) → the page showed "profile unavailable" / the party pane never opened,
even though the model was working fine.

The fix: never block the request on generation. The route returns immediately
with whatever floor it has (curated data for major leaders, or an empty
synthesis), and kicks a daemon thread that generates the synthesis and writes
it to the `app_meta` cache. The frontend re-fetches once after a short delay
and upgrades in place. A small in-flight set prevents duplicate concurrent
generations for the same key."""

import threading

_inflight = set()
_lock = threading.Lock()


def inflight(key) -> bool:
    """True if a generation job for this key is currently running."""
    with _lock:
        return key in _inflight


def kick(key, fn):
    """Run fn() once in a daemon thread, de-duplicated by key. fn is expected
    to generate and cache a synthesis; its return value is ignored.

    Returns True whenever a job for this key is IN PROGRESS — whether this call
    started it or one was already running. v8.13.7 fix: it used to return False
    for an already-running job, which made the route report synth_pending=False
    on the frontend's 2nd poll while a slow (Ollama) generation was still going,
    so the page STOPPED polling before any AI field landed and the leader/party
    AI profile never appeared. Reporting the in-flight job as pending keeps the
    page polling until the fields are actually cached."""
    with _lock:
        if key in _inflight:
            return True   # already generating → still pending, keep polling
        _inflight.add(key)

    def _run():
        try:
            fn()
        except Exception:  # noqa: BLE001 — background best-effort, never crash
            pass
        finally:
            with _lock:
                _inflight.discard(key)

    threading.Thread(target=_run, daemon=True).start()
    return True
