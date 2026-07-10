"""TalkDiplomacy Live — application entrypoint (Stage 6, Sections 2.1, 8).

Zero-install adaptation of the FastAPI layer: a ThreadingHTTPServer from
the standard library serving

  - the Section 8.1 REST contract under /api/* (route modules),
  - the Section 8.2 WebSocket at /ws/feed (stdlib RFC 6455 upgrade),
  - the buildless static frontend from frontend/ at /.

Run directly (`python -m backend.app.main` from the repo root) or via the
repo-root `run.py` launcher.
"""

import json
import logging
import mimetypes
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if __package__ in (None, ""):  # allow `python backend/app/main.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent))
    __package__ = "backend.app"  # noqa: A001

from .api import router  # noqa: E402
from .api import (routes_admin, routes_analyst, routes_cities, routes_diag,  # noqa: E402,F401
                  routes_events, routes_geo, routes_v7, routes_map, routes_status,
                  routes_stories, routes_v4)
from .config import API_PORT, REPO_ROOT, cfg  # noqa: E402
from .db.models import migrate  # noqa: E402
from .ingestion.scheduler import start_all  # noqa: E402
from .ingestion.seed import seed_sources  # noqa: E402
from .logging_setup import setup_logging  # noqa: E402
from .websocket import feed_socket  # noqa: E402

log = logging.getLogger("main")

FRONTEND_DIR = REPO_ROOT / "frontend"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "TalkDiplomacyLive/1.0"

    def log_message(self, fmt, *args):  # route access logs through JSON logging
        log.debug("http", extra={"data": {"line": fmt % args}})

    # --- helpers ---

    def _send_json(self, status: int, obj) -> None:
        body = json.dumps(obj, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode(errors="replace")

    def _handle_api(self, method: str) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        try:
            status, obj = router.dispatch(method, parsed.path, query,
                                          self._read_body() if method == "POST" else None)
        except Exception as exc:  # noqa: BLE001 — serving layer never crashes
            log.exception("api_error", extra={"data": {"path": parsed.path}})
            status, obj = 500, {"error": str(exc)}
        if isinstance(obj, dict) and "_raw_html" in obj:  # v6.3.3 diagnostics page
            body = obj["_raw_html"].encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if isinstance(obj, dict) and "_raw_csv" in obj:  # v2 §6.4 CSV export
            body = obj["_raw_csv"].encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="{obj.get("_filename", "export.csv")}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json(status, obj)

    def _handle_websocket(self) -> None:
        key = self.headers.get("Sec-WebSocket-Key")
        if not key or "websocket" not in (self.headers.get("Upgrade") or "").lower():
            self._send_json(400, {"error": "expected WebSocket upgrade"})
            return
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", feed_socket.accept_key(key))
        self.end_headers()
        self.wfile.flush()
        feed_socket.serve_connection(self.connection)  # blocks for connection lifetime
        self.close_connection = True

    def _serve_static(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html") or path.startswith("/story/"):
            file_path = FRONTEND_DIR / "index.html"
        else:
            candidate = (FRONTEND_DIR / path.lstrip("/")).resolve()
            if not str(candidate).startswith(str(FRONTEND_DIR.resolve())):
                self._send_json(403, {"error": "forbidden"})
                return
            file_path = candidate
        if not file_path.is_file():
            self._send_json(404, {"error": "not found"})
            return
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if file_path.suffix == ".js":
            ctype = "text/javascript"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    # --- verbs ---

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/ws/feed"):
            self._handle_websocket()
        elif self.path.startswith("/api/"):
            self._handle_api("GET")
        else:
            self._serve_static()

    def do_POST(self):  # noqa: N802
        if self.path.startswith("/api/"):
            self._handle_api("POST")
        else:
            self._send_json(404, {"error": "not found"})


def _bind_server(preferred_port: int) -> ThreadingHTTPServer:
    """Bind the preferred port, falling back to nearby/known-good ports.
    Windows frequently reserves blocks of ports (Hyper-V/WSL excluded port
    ranges) which raises WinError 10013 on bind — that must not be fatal
    for a zero-setup launcher. Port 0 (OS-assigned) is the last resort."""
    candidates = []
    for p in (preferred_port, preferred_port + 1, preferred_port + 2,
              preferred_port + 3, 8080, 8880, 3000, 5000, 0):
        if p not in candidates:
            candidates.append(p)
    last_err: OSError | None = None
    for port in candidates:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            if port != preferred_port:
                log.warning("port_fallback", extra={"data": {
                    "requested": preferred_port, "bound": server.server_address[1],
                    "reason": str(last_err)}})
            return server
        except OSError as exc:  # includes PermissionError / WinError 10013
            last_err = exc
    raise last_err  # every candidate failed — genuinely can't serve


def create_app(start_scheduler: bool = True) -> ThreadingHTTPServer:
    setup_logging()
    from .config import CONFIG
    from .config_schema import validate_config
    validate_config(CONFIG)  # v2 §7.3 — fail loud on a bad config.yaml
    migrate()
    # v7.4.1 — GDELT is permanently banned; hard-purge any GDELT source + all
    # of its derived rows at every boot before anything else touches the chain.
    try:
        from .ingestion.backfill import purge_gdelt
        _purged = purge_gdelt()
        if _purged["sources"]:
            log.info("gdelt_purged_on_boot", extra={"data": _purged})
    except Exception:  # noqa: BLE001 — a purge hiccup must never block serving
        log.exception("gdelt_purge_failed")
    from .processing.embed import ensure_embedder_consistency
    ensure_embedder_consistency()
    # v2 §10 — one-time gazetteer import from the vendored dataset
    try:
        import sys as _sys
        _sys.path.insert(0, str(REPO_ROOT))
        from scripts.import_gazetteer import import_gazetteer
        import_gazetteer()
    except Exception:  # noqa: BLE001 — geocoding falls back to the built-in dict
        log.exception("gazetteer_import_failed")
    added = seed_sources()
    # v3 §13-23 — geopolitical entity layer seeds (idempotent)
    try:
        from .geopolitics.seed import seed_all
        seed_all()
    except Exception:  # noqa: BLE001 — entity layer absence never blocks serving
        log.exception("geo_seed_failed")
    if start_scheduler:
        start_all()
    server = _bind_server(API_PORT)
    server.daemon_threads = True
    log.info("startup", extra={"data": {"sources_seeded": added,
                                        "port": server.server_address[1],
                                        "recompute_interval":
                                            cfg("instability", "recompute_interval_seconds")}})
    return server


def main() -> None:
    server = create_app()
    log.info("serving", extra={"data": {
        "url": f"http://localhost:{server.server_address[1]}"}})
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutdown")


if __name__ == "__main__":
    main()
