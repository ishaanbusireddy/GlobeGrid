"""Section 5.6 — instability index.

Weighted sum of (event volume, average severity, distinct regions) over a
rolling window, normalized 0-100. All weights and intervals come from
config.yaml (instability.*) — never hardcoded. Written to
instability_scores on the configured schedule; history retained
indefinitely for the homepage trend line.
"""

import json
import logging
import math
from datetime import datetime, timedelta, timezone

from ..config import cfg
from ..db.models import new_id, now_iso
from ..db.session import query, write_tx

log = logging.getLogger("instability")

# Volume normalization scale: events-per-window at which the volume
# component saturates. Chosen for single-user ingestion volumes; the
# log curve keeps low-volume readings meaningful.
VOLUME_SATURATION = 400.0
SPREAD_SATURATION = 25.0


def compute_score() -> dict:
    window_hours = float(cfg("instability", "rolling_window_hours"))
    w_volume = float(cfg("instability", "weight_volume"))
    w_severity = float(cfg("instability", "weight_severity"))
    w_spread = float(cfg("instability", "weight_spread"))

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    # v2 §3.3 — wire-copy duplicates are excluded from the volume count so
    # syndicated reprints don't inflate the index.
    # v5 §5 — each event carries its source's reliability_tier so low-tier
    # volume (raw GDELT Events) can't drown out high-tier signal.
    rows = query(
        "SELECT e.severity, e.location_name, s.reliability_tier FROM events e"
        " JOIN raw_items r ON r.id = e.raw_item_id"
        " JOIN sources s ON s.id = r.source_id"
        " WHERE e.is_synthetic = 0 AND e.occurred_at >= ?"
        " AND NOT EXISTS (SELECT 1 FROM extracted_facts f WHERE f.event_id = e.id"
        "                 AND f.duplicate_of_fact_id IS NOT NULL)", (cutoff,))

    # v5 §5 — tier weighting: low-tier events count less toward volume/spread
    # so a flood of noisy GDELT Events can't dominate the index. Config-gated;
    # weight 1.0 for all tiers when reliability tiers are disabled.
    tiers_on = bool(cfg("source_quality", "reliability_tiers_enabled"))
    TIER_W = {"high": 1.0, "medium": 0.65, "low": 0.3} if tiers_on else {}
    def tw(r):
        return TIER_W.get(r["reliability_tier"], 1.0)

    volume = sum(tw(r) for r in rows)
    total_w = volume or 1.0
    avg_severity = (sum(r["severity"] * tw(r) for r in rows) / total_w) if rows else 0.0
    regions = {r["location_name"] for r in rows if r["location_name"]}

    volume_score = min(1.0, math.log1p(volume) / math.log1p(VOLUME_SATURATION))
    severity_score = avg_severity / 5.0
    spread_score = min(1.0, len(regions) / SPREAD_SATURATION)

    score = 100.0 * (w_volume * volume_score
                     + w_severity * severity_score
                     + w_spread * spread_score)
    # v6 §22 — recalibration: the raw formula reads far too high at a normal
    # baseline (a routine day scored ~73 because volume/spread saturate on
    # ordinary wire traffic). Dividing by baseline_divisor re-anchors a
    # routine day to the ~10-25 band while genuinely severe multi-region
    # escalation still approaches the top. The divisor is a §7.2 config
    # constant to be retuned empirically against real ingestion volume
    # (instability.recalibration_pending flags that pass as still open).
    try:
        divisor = float(cfg("instability", "baseline_divisor"))
    except KeyError:
        divisor = 1.0
    score = score / max(1.0, divisor)
    score = max(0.0, min(100.0, round(score, 2)))

    breakdown = {
        "volume": {"raw": round(volume, 1), "normalized": round(volume_score, 4),
                   "weight": w_volume},
        "severity": {"raw": round(avg_severity, 3), "normalized": round(severity_score, 4),
                     "weight": w_severity},
        "spread": {"raw": len(regions), "normalized": round(spread_score, 4),
                   "weight": w_spread},
        "window_hours": window_hours,
    }
    with write_tx() as conn:
        conn.execute(
            "INSERT INTO instability_scores (id, score, computed_at, component_breakdown)"
            " VALUES (?,?,?,?)",
            (new_id(), score, now_iso(), json.dumps(breakdown)))
    log.info("instability_computed", extra={"data": {"score": score, "volume": volume,
                                                     "regions": len(regions)}})
    return {"score": score, "computed_at": now_iso(), "component_breakdown": breakdown}
