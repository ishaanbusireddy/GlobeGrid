"""v3 §7 — forward-looking risk forecasting.

THE HIGHEST REPUTATIONAL-RISK FEATURE IN THE SYSTEM, and it ships with
forecasting.enabled: false. Do not flip it on until the v2 prediction
scorecard has real resolved history — a forecasting feature with zero
track record is exactly what §7 warns against.

Discipline enforced here, per spec:
  - distinct, separately-labeled prompt path — never blended into the
    Section 9 causal narrative;
  - every forecast lands in the predictions table (kind=forward_forecast)
    and is graded by the same resolution job as everything else;
  - forecast confidence is CAPPED below 'high' until the scorecard has
    min_resolved_predictions_for_high_confidence resolved forecasts;
  - the API serves every forecast alongside the system's own historical
    forecast accuracy — a forecast without its track record attached is
    not shippable (§7.2), and the UI enforces that pairing.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from . import llm
from ..config import cfg
from ..db.models import new_id, now_iso
from ..db.session import query, query_one, write_tx
from .provenance import next_hashes

log = logging.getLogger("forecast")

FORECAST_PROMPT = """You are generating a SHORT-HORIZON RISK STATEMENT — a claim about the
near future, which is a fundamentally different kind of claim than a
causal narrative about the past. You will be given a recent story
cluster's facts.

Return ONLY valid JSON matching this shape:
{
  "forecast": string,          // 'elevated risk of X in region Y over the next N hours'
  "region": string,
  "confidence": "medium" | "low",
  "reasoning": string
}

Rules:
- Only state a forecast the evidence pattern actually supports; when the
  cluster doesn't support one, return {"forecast": null}.
- Heavily hedge: these are risk statements, not predictions of certainty.
- 'high' confidence is not available to you at all.
- Do not invent facts not present in the input."""


def enabled() -> bool:
    return bool(cfg("forecasting", "enabled"))


def forecast_accuracy() -> dict:
    """The track record that must accompany every displayed forecast."""
    rows = query("SELECT status, COUNT(*) AS n FROM predictions"
                 " WHERE kind = 'forward_forecast' AND status != 'pending'"
                 " GROUP BY status")
    counts = {r["status"]: r["n"] for r in rows}
    confirmed = counts.get("confirmed", 0)
    resolved = confirmed + counts.get("refuted", 0)
    return {
        "resolved_forecasts": resolved,
        "directionally_correct_pct": round(100.0 * confirmed / resolved, 1) if resolved else None,
        "high_confidence_unlocked": resolved >= int(
            cfg("forecasting", "min_resolved_predictions_for_high_confidence")),
    }


def generate_for_recent_stories(limit: int = 3) -> int:
    """One forecast pass over recently updated clusters. No-op unless
    forecasting.enabled is true AND an API key is present."""
    if not enabled() or not llm.available():
        return 0
    horizon = int(cfg("forecasting", "default_horizon_hours"))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    stories = query(
        "SELECT s.id FROM stories s WHERE s.is_synthetic = 0 AND s.last_updated_at >= ?"
        " AND NOT EXISTS (SELECT 1 FROM predictions p WHERE p.story_id = s.id"
        "                 AND p.kind = 'forward_forecast'"
        "                 AND p.predicted_at >= ?)"
        " ORDER BY s.last_updated_at DESC LIMIT ?", (cutoff, cutoff, limit))
    from .causal_link import _cluster_facts
    made = 0
    for s in stories:
        facts = _cluster_facts(s["id"])
        if len(facts) < 2:
            continue
        try:
            text = llm.complete(FORECAST_PROMPT,
                                [{"role": "user", "content": json.dumps(
                                    {"cluster_facts": facts, "horizon_hours": horizon})}],
                                max_tokens=600, timeout=60)
            if text is None:
                continue
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            out = json.loads(text)
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("forecast_failed", extra={"data": {"story_id": s["id"],
                                                           "error": str(exc)}})
            continue
        if not isinstance(out, dict) or not out.get("forecast"):
            continue
        pid, predicted_at = new_id(), now_iso()
        row_hash, prev_hash = next_hashes("predictions", {
            "id": pid, "story_id": s["id"], "consequence_text": out["forecast"],
            "predicted_at": predicted_at, "kind": "forward_forecast",
            "horizon_hours": horizon, "region": out.get("region")})
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO predictions (id, story_id, consequence_text, predicted_at,"
                " kind, horizon_hours, region, row_hash, prev_hash)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (pid, s["id"], out["forecast"], predicted_at, "forward_forecast",
                 horizon, out.get("region"), row_hash, prev_hash))
        made += 1
        log.info("forecast_logged", extra={"data": {"story_id": s["id"],
                                                    "region": out.get("region"),
                                                    "horizon_hours": horizon}})
    return made


# ===== v4 §10 — expert prognosis on conflicts and diplomatic processes =====

PROGNOSIS_PROMPT = """You are generating a LONG-HORIZON PROGNOSIS for an ongoing conflict or
diplomatic process — a discursive, analytical assessment of where it seems
to be heading, grounded ONLY in the tracked context provided.

Return ONLY valid JSON:
{
  "prognosis": string,          // 2-5 sentences, heavily hedged, evidence-grounded
  "region": string,
  "confidence": "medium" | "low",
  "key_drivers": string[]       // the 2-4 tracked factors your read rests on
}

Rules:
- A longer horizon earns NO relaxation of discipline: hedge heavily, cite
  only the provided context, and return {"prognosis": null} when the
  tracked evidence doesn't support a directional read.
- 'high' confidence is not available to you at all."""


def generate_prognoses(limit: int = 2) -> int:
    """v4 §10 — periodically refreshed long-horizon prognosis per active
    conflict, routed through the SAME tracked, graded predictions pathway
    (kind=forward_forecast, longer horizon_hours) — never a free-floating
    opinion. Gated by the same forecasting.enabled flag and the same
    confidence-capping rules as the 72h forecasts."""
    if not enabled() or not llm.available():
        return 0
    horizon = int(cfg("prognosis", "horizon_hours"))
    refresh_h = float(cfg("prognosis", "refresh_interval_hours"))
    made = 0
    conflicts = query("SELECT id, name, summary, status FROM conflicts"
                      " WHERE status IN ('active','ceasefire') LIMIT 20")
    for c in conflicts:
        if made >= limit:
            break
        # one prognosis per refresh window per conflict, attached to the
        # conflict's most recently updated story
        story = query_one(
            "SELECT id FROM stories WHERE conflict_id = ? AND is_synthetic = 0"
            " ORDER BY last_updated_at DESC LIMIT 1", (c["id"],))
        if not story:
            continue
        recent = query_one(
            "SELECT 1 FROM predictions WHERE story_id IN"
            " (SELECT id FROM stories WHERE conflict_id = ?)"
            " AND kind = 'forward_forecast' AND horizon_hours >= ?"
            " AND predicted_at >= datetime('now', ?)",
            (c["id"], horizon, f"-{refresh_h} hour"))
        if recent:
            continue
        heads = [dict(r) for r in query(
            "SELECT headline, summary, last_updated_at FROM stories"
            " WHERE conflict_id = ? AND is_synthetic = 0"
            " ORDER BY last_updated_at DESC LIMIT 12", (c["id"],))]
        if len(heads) < 3:
            continue    # §15.1 honesty: thin coverage earns no prognosis
        try:
            text = llm.complete(PROGNOSIS_PROMPT,
                                [{"role": "user", "content": json.dumps(
                                    {"conflict": {"name": c["name"], "status": c["status"],
                                                  "summary": c["summary"]},
                                     "tracked_stories": heads, "horizon_hours": horizon})}],
                                max_tokens=700, timeout=60)
            if text is None:
                continue
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            out = json.loads(text)
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("prognosis_failed", extra={"data": {"conflict": c["name"],
                                                            "error": str(exc)}})
            continue
        if not isinstance(out, dict) or not out.get("prognosis"):
            continue
        pid, predicted_at = new_id(), now_iso()
        row_hash, prev_hash = next_hashes("predictions", {
            "id": pid, "story_id": story["id"], "consequence_text": out["prognosis"],
            "predicted_at": predicted_at, "kind": "forward_forecast",
            "horizon_hours": horizon, "region": out.get("region")})
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO predictions (id, story_id, consequence_text, predicted_at,"
                " kind, horizon_hours, region, row_hash, prev_hash)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (pid, story["id"], out["prognosis"], predicted_at, "forward_forecast",
                 horizon, out.get("region"), row_hash, prev_hash))
        made += 1
        log.info("prognosis_logged", extra={"data": {"conflict": c["name"],
                                                     "horizon_hours": horizon}})
    return made
