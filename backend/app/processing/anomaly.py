"""v3 §6 — anomaly / changepoint detection on the instability index.

Stdlib-only, consistent with the zero-install build:
  - rolling z-score: latest reading vs mean/stddev of the trailing window
    (default 30 days), flagged past a threshold (default 2.5);
  - CUSUM (cumulative sum control chart) over the same window for
    sustained shifts rather than single spikes.

Anomalies are flagged, never acted on automatically: a marker on the
trend line and a row in anomaly_flags — no notifications (out of scope
per §1.2).
"""

import logging
import math
from datetime import datetime, timedelta, timezone

from ..config import cfg
from ..db.models import new_id, now_iso
from ..db.session import query, query_one, write_tx

log = logging.getLogger("anomaly")

CUSUM_K_FACTOR = 0.5   # slack, in stddevs — standard CUSUM parameterization
CUSUM_H_FACTOR = 4.0   # decision interval, in stddevs


def check_latest() -> list[dict]:
    """Run both detectors against the newest instability reading. Returns
    any new flags created (deduped: one flag per method per reading)."""
    window_days = float(cfg("anomaly", "zscore_window_days"))
    z_threshold = float(cfg("anomaly", "zscore_flag_threshold"))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    rows = query("SELECT score, computed_at FROM instability_scores"
                 " WHERE is_synthetic = 0 AND computed_at >= ? ORDER BY computed_at",
                 (cutoff,))
    if len(rows) < 12:  # not enough history to call anything unusual
        return []
    scores = [r["score"] for r in rows]
    latest = scores[-1]
    baseline = scores[:-1]
    mean = sum(baseline) / len(baseline)
    variance = sum((s - mean) ** 2 for s in baseline) / len(baseline)
    std = math.sqrt(variance)
    flags = []

    if std > 1e-6:
        z = (latest - mean) / std
        if abs(z) >= z_threshold and _not_recently_flagged("zscore"):
            flags.append(_flag("zscore", latest, round(z, 3)))

    if cfg("anomaly", "cusum_enabled") and std > 1e-6:
        k, h = CUSUM_K_FACTOR * std, CUSUM_H_FACTOR * std
        s_hi = s_lo = 0.0
        for s in scores:
            s_hi = max(0.0, s_hi + (s - mean) - k)
            s_lo = max(0.0, s_lo + (mean - s) - k)
        stat = max(s_hi, s_lo)
        if stat >= h and _not_recently_flagged("cusum"):
            flags.append(_flag("cusum", latest, round(stat / std, 3)))
    return flags


def _not_recently_flagged(method: str) -> bool:
    recent = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    return query_one("SELECT 1 FROM anomaly_flags WHERE method = ? AND detected_at >= ?"
                     " LIMIT 1", (method, recent)) is None


def _flag(method: str, score_value: float, stat: float) -> dict:
    row = {"id": new_id(), "detected_at": now_iso(), "method": method,
           "score_value": score_value, "z_or_cusum_value": stat}
    with write_tx() as conn:
        conn.execute("INSERT INTO anomaly_flags (id, detected_at, method, score_value,"
                     " z_or_cusum_value) VALUES (?,?,?,?,?)",
                     (row["id"], row["detected_at"], method, score_value, stat))
    log.info("anomaly_flagged", extra={"data": row})
    return row
