"""Section 10.1 — structured JSON logging.

Every log record is one JSON line: timestamp, level, logger, message, plus
any structured fields passed via `extra={"data": {...}}`. Output goes to a
size-rotated file (LOG_DIR/app.log) and the console.
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import LOG_DIR, LOG_LEVEL


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        data = getattr(record, "data", None)
        if isinstance(data, dict):
            line.update(data)
        if record.exc_info:
            line["exc"] = self.formatException(record.exc_info)
        return json.dumps(line, ensure_ascii=False, default=str)


def setup_logging() -> logging.Logger:
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if root.handlers:  # idempotent across re-imports
        return root
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    fmt = JsonLineFormatter()

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    return root


def job_log(logger: logging.Logger, *, source_id: str, status: str, item_count: int,
            duration_ms: int, error: str | None = None) -> None:
    """One structured line per ingestion job run (Section 10.1)."""
    logger.info("ingestion_job", extra={"data": {
        "source_id": source_id, "status": status, "item_count": item_count,
        "duration_ms": duration_ms, "error": error,
    }})
