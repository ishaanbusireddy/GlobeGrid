"""v7 §4 — the Brier backtest harness: EARNING forecasting.enabled.

`forecasting.enabled` has shipped false since v3 because turning on forecasts
without a resolved scorecard history would be selling confidence the system
hasn't demonstrated. This module is how it gets earned, per category:

  1. REPLAY: walk the permanent fact chain story by story. For each story at
     time T, reconstruct the prediction the system WOULD have made (same
     deterministic consequence heuristics the live predictions pathway uses:
     "more linked events within the horizon"), using only facts known at T.
  2. GRADE: did the fact chain actually record confirming events inside the
     horizon? Confirmed/refuted exactly as the live grader would.
  3. SCORE: per-category Brier score (mean squared error of the stated
     probability vs the 0/1 outcome) into `forecast_scorecards`.
  4. GATE: a category only surfaces live forecasts once it clears the
     calibration bar (config: brier ceiling + minimum graded count). The
     gate is PER CATEGORY — conflict forecasting can earn its way on while
     finance stays dark.

The public accuracy dashboard (/api/forecasting/scorecard) shows all of it,
including the categories that FAIL — the honesty is the moat.
"""

import json
from datetime import datetime, timedelta, timezone

from ..config import cfg
from ..db.models import meta_get, meta_set, now_iso
from ..db.session import query, write_tx

# the probability the deterministic pathway would have stated, by how much
# corroboration the story had at prediction time (linked events so far).
# Deliberately simple and REPLAYABLE — no LLM, no hindsight.
_P_BY_LINKAGE = [(8, 0.85), (5, 0.75), (3, 0.65), (2, 0.55), (1, 0.45)]


def _ensure_table():
    with write_tx() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS forecast_scorecards (
            category TEXT PRIMARY KEY,
            graded INTEGER NOT NULL,
            confirmed INTEGER NOT NULL,
            brier REAL NOT NULL,
            calibration_bins TEXT,
            passed INTEGER NOT NULL,
            computed_at TEXT NOT NULL)""")


def _would_have_predicted(n_linked):
    for floor, p in _P_BY_LINKAGE:
        if n_linked >= floor:
            return p
    return 0.35


def run_backtest(horizon_hours=None, min_graded=None):
    """Replay the chain and (re)compute per-category scorecards. Returns the
    dashboard dict. Cheap enough to run on demand (pure SQL + arithmetic)."""
    _ensure_table()
    horizon = float(horizon_hours or cfg("forecasting", "default_horizon_hours"))
    bar_brier = float(cfg("forecasting", "calibration_brier_ceiling"))
    bar_n = int(min_graded or cfg("forecasting", "calibration_min_graded"))

    # every non-synthetic story with its category (dominant event category)
    # and its events ordered in time
    rows = query("""
        SELECT s.id AS story_id, MIN(e.occurred_at) AS t0,
               COUNT(e.id) AS total_events,
               (SELECT e2.category FROM events e2
                 JOIN story_members se2 ON se2.event_id = e2.id
                WHERE se2.story_id = s.id
                GROUP BY e2.category ORDER BY COUNT(*) DESC LIMIT 1) AS category
          FROM stories s
          JOIN story_members se ON se.story_id = s.id
          JOIN events e ON e.id = se.event_id
         WHERE s.is_synthetic = 0
         GROUP BY s.id HAVING total_events >= 2""")
    per_cat = {}
    for r in rows:
        cat = r["category"] or "other"
        try:
            t0 = datetime.fromisoformat(str(r["t0"]).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        # prediction moment: after the SECOND event (the story exists, the
        # system would have predicted "more linked developments within H")
        evs = query("""SELECT e.occurred_at FROM events e
                        JOIN story_members se ON se.event_id = e.id
                       WHERE se.story_id = ? ORDER BY e.occurred_at""",
                    (r["story_id"],))
        if len(evs) < 2:
            continue
        try:
            t_pred = datetime.fromisoformat(
                str(evs[1]["occurred_at"]).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        known = 2
        deadline = t_pred + timedelta(hours=horizon)
        # only grade if the horizon has fully elapsed (no peeking at open bets)
        if deadline > datetime.now(timezone.utc):
            continue
        confirmed = 0
        for ev in evs[2:]:
            try:
                t = datetime.fromisoformat(
                    str(ev["occurred_at"]).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            if t_pred < t <= deadline:
                confirmed = 1
                break
        p = _would_have_predicted(known)
        outcome = confirmed
        c = per_cat.setdefault(cat, {"graded": 0, "confirmed": 0, "sq": 0.0,
                                     "bins": {}})
        c["graded"] += 1
        c["confirmed"] += outcome
        c["sq"] += (p - outcome) ** 2
        b = f"{int(p * 10) / 10:.1f}"
        bb = c["bins"].setdefault(b, [0, 0])
        bb[0] += 1
        bb[1] += outcome

    computed_at = now_iso()
    out = []
    with write_tx() as conn:
        for cat, c in per_cat.items():
            brier = round(c["sq"] / c["graded"], 4) if c["graded"] else 1.0
            passed = int(c["graded"] >= bar_n and brier <= bar_brier)
            conn.execute(
                "INSERT INTO forecast_scorecards (category, graded, confirmed,"
                " brier, calibration_bins, passed, computed_at)"
                " VALUES (?,?,?,?,?,?,?)"
                " ON CONFLICT(category) DO UPDATE SET graded=excluded.graded,"
                " confirmed=excluded.confirmed, brier=excluded.brier,"
                " calibration_bins=excluded.calibration_bins,"
                " passed=excluded.passed, computed_at=excluded.computed_at",
                (cat, c["graded"], c["confirmed"], brier,
                 json.dumps(c["bins"]), passed, computed_at))
            out.append({"category": cat, "graded": c["graded"],
                        "confirmed": c["confirmed"], "brier": brier,
                        "passed": bool(passed), "bins": c["bins"]})
    meta_set("backtest:last_run", computed_at)
    out.sort(key=lambda x: x["brier"])
    return {"categories": out, "computed_at": computed_at,
            "bar": {"brier_ceiling": bar_brier, "min_graded": bar_n,
                    "horizon_hours": horizon},
            "note": ("A category surfaces live forecasts ONLY once it clears "
                     "the bar. Insufficient history reads as not-passed — "
                     "that is the design, not a bug.")}


def dashboard():
    """The public 'how right were we?' view (cached table + gate status)."""
    _ensure_table()
    rows = [dict(r) for r in query(
        "SELECT * FROM forecast_scorecards ORDER BY brier")]
    for r in rows:
        try:
            r["bins"] = json.loads(r.pop("calibration_bins") or "{}")
        except json.JSONDecodeError:
            r["bins"] = {}
        r["passed"] = bool(r["passed"])
    enabled_cats = [r["category"] for r in rows if r["passed"]]
    return {"categories": rows,
            "last_run": meta_get("backtest:last_run"),
            "forecasting_config_enabled": bool(cfg("forecasting", "enabled")),
            "categories_earned": enabled_cats,
            "bar": {"brier_ceiling": float(cfg("forecasting",
                                               "calibration_brier_ceiling")),
                    "min_graded": int(cfg("forecasting",
                                          "calibration_min_graded"))}}


def category_cleared(category):
    """Live gate used by the forecast pathway: config master switch AND the
    category has earned its calibration."""
    if not bool(cfg("forecasting", "enabled")):
        # v7 — the master switch may stay false; earned categories can still
        # surface if auto_enable_earned is on (the 'earn it' pathway).
        if not bool(cfg("forecasting", "auto_enable_earned")):
            return False
    _ensure_table()
    row = query("SELECT passed FROM forecast_scorecards WHERE category = ?",
                (category,))
    return bool(row and row[0]["passed"])
