"""v3 §5 — self-tuning correlation thresholds.

Aggregates thumbs-up/down feedback per category and nudges that
category's effective thresholds by a small bounded step per cycle —
a conservative EMA-style drift, not a learned model. The config defaults
remain the initialization, and min/max_threshold form the hard band the
tuning can never escape.

Direction: mostly-'incorrect' feedback (stories linked that shouldn't
have been) RAISES the thresholds (stricter matching); mostly-'correct'
feedback lowers them slightly toward catching more true links.
"""

import logging
from datetime import datetime, timedelta, timezone

from ..config import cfg
from ..db.models import now_iso
from ..db.session import query, write_tx

log = logging.getLogger("self_tuning")

MIN_VOTES_PER_CYCLE = 3  # don't move on a single stray vote


def aggregate_and_adjust() -> int:
    """One tuning cycle over recent feedback. Returns categories adjusted."""
    step = float(cfg("self_tuning", "adjustment_step"))
    lo = float(cfg("self_tuning", "min_threshold"))
    hi = float(cfg("self_tuning", "max_threshold"))
    window_hours = float(cfg("self_tuning", "aggregation_interval_hours"))
    default_same = float(cfg("correlation", "same_window_similarity_threshold"))
    default_hist = float(cfg("correlation", "historical_similarity_threshold"))

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    rows = query(
        "SELECT category,"
        " SUM(CASE WHEN vote = 'correct' THEN 1 ELSE 0 END) AS up,"
        " SUM(CASE WHEN vote = 'incorrect' THEN 1 ELSE 0 END) AS down"
        " FROM correlation_feedback WHERE voted_at >= ? GROUP BY category", (cutoff,))
    adjusted = 0
    for r in rows:
        total = (r["up"] or 0) + (r["down"] or 0)
        if total < MIN_VOTES_PER_CYCLE:
            continue
        # net direction in [-1, 1]; positive = links judged wrong -> stricter
        direction = ((r["down"] or 0) - (r["up"] or 0)) / total
        delta = step if direction > 0.2 else (-step if direction < -0.2 else 0.0)
        if delta == 0.0:
            continue
        current = query(
            "SELECT same_window_threshold, historical_threshold FROM category_thresholds"
            " WHERE category = ?", (r["category"],))
        same = current[0]["same_window_threshold"] if current else default_same
        hist = current[0]["historical_threshold"] if current else default_hist
        new_same = max(lo, min(hi, same + delta))
        new_hist = max(lo, min(hi, hist + delta))
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO category_thresholds (category, same_window_threshold,"
                " historical_threshold, last_adjusted_at) VALUES (?,?,?,?)"
                " ON CONFLICT(category) DO UPDATE SET"
                "   same_window_threshold = excluded.same_window_threshold,"
                "   historical_threshold = excluded.historical_threshold,"
                "   last_adjusted_at = excluded.last_adjusted_at",
                (r["category"], new_same, new_hist, now_iso()))
        adjusted += 1
        log.info("threshold_adjusted", extra={"data": {
            "category": r["category"], "delta": delta,
            "same_window": new_same, "historical": new_hist,
            "votes": {"correct": r["up"], "incorrect": r["down"]}}})
    return adjusted
