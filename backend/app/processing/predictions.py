"""v2 addendum §3.4 — prediction resolution job.

A scheduled job checks pending predictions against facts newly linked to
the same story cluster since the prediction was made. One BATCHED LLM call
(routed through the v5 §18 provider fallback) judges confirmed/refuted (not
per-prediction), with the same confidence discipline as Section 9: no clear
evidence -> stays pending. Graceful no-op without a configured AI provider.
"""

import json
import logging

from . import llm
from ..config import cfg
from ..db.models import now_iso
from ..db.session import query, write_tx

log = logging.getLogger("predictions")

JUDGE_SYSTEM_PROMPT = """You are grading earlier analytical predictions against facts that were
reported later. For each prediction you receive the predicted consequence
and facts that emerged afterwards on the same story cluster.

Return ONLY valid JSON: an array of objects, one per prediction:
[{"id": string, "verdict": "confirmed" | "refuted" | "pending"}]

Rules:
- "confirmed" only when a later fact clearly shows the consequence happened.
- "refuted" only when a later fact clearly shows it did not / cannot happen.
- Anything ambiguous stays "pending". Never guess.
- Do not invent facts not present in the input."""

def _pending_with_new_facts(batch_size: int) -> list[dict]:
    rows = query(
        "SELECT p.id, p.story_id, p.consequence_text, p.predicted_at"
        " FROM predictions p WHERE p.status = 'pending'"
        " ORDER BY p.predicted_at LIMIT ?", (batch_size,))
    out = []
    for p in rows:
        facts = query(
            'SELECT f.id, f.who, f.what, f."where" AS where_text, f.when_occurred'
            " FROM story_members m JOIN extracted_facts f"
            " ON f.id = m.fact_id OR f.event_id = m.event_id"
            " WHERE m.story_id = ? AND m.linked_at > ? AND f.duplicate_of_fact_id IS NULL"
            " GROUP BY f.id ORDER BY f.when_occurred DESC LIMIT 12",
            (p["story_id"], p["predicted_at"]))
        if facts:
            out.append({
                "id": p["id"],
                "consequence": p["consequence_text"],
                "later_facts": [{"fact_id": f["id"], "who": f["who"], "what": f["what"],
                                 "where": f["where_text"] or "n/a",
                                 "timestamp": f["when_occurred"]} for f in facts],
            })
    return out


def _judge(batch: list[dict]):
    text = llm.complete(JUDGE_SYSTEM_PROMPT,
                        [{"role": "user", "content": json.dumps({"predictions": batch})}],
                        max_tokens=1024, timeout=60)
    if text is None:
        raise ValueError("no AI provider available")
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    verdicts = json.loads(text)
    if not isinstance(verdicts, list):
        raise ValueError("judge output not a list")
    return verdicts


def resolve_pending() -> int:
    """Run one resolution pass. Returns number of predictions resolved."""
    if not llm.available():
        return 0
    batch = _pending_with_new_facts(int(cfg("predictions", "batch_size")))
    if not batch:
        return 0
    try:
        verdicts = _judge(batch)
    except (ValueError, json.JSONDecodeError) as exc:
        log.warning("prediction_judge_failed", extra={"data": {"error": str(exc)}})
        return 0
    by_id = {b["id"]: b for b in batch}
    resolved = 0
    with write_tx() as conn:
        for v in verdicts:
            pid, verdict = v.get("id"), v.get("verdict")
            if pid not in by_id or verdict not in ("confirmed", "refuted"):
                continue
            confirming = by_id[pid]["later_facts"][0]["fact_id"] if verdict == "confirmed" else None
            conn.execute(
                "UPDATE predictions SET status = ?, resolved_at = ?, confirming_fact_id = ?"
                " WHERE id = ? AND status = 'pending'",
                (verdict, now_iso(), confirming, pid))
            resolved += 1
    if resolved:
        log.info("predictions_resolved", extra={"data": {"count": resolved}})
    return resolved


def scorecard() -> dict:
    """Aggregate predicted-vs-actual accuracy view (§3.4)."""
    rows = query("SELECT status, COUNT(*) AS n FROM predictions GROUP BY status")
    counts = {r["status"]: r["n"] for r in rows}
    confirmed = counts.get("confirmed", 0)
    refuted = counts.get("refuted", 0)
    graded = confirmed + refuted
    return {
        "pending": counts.get("pending", 0),
        "confirmed": confirmed,
        "refuted": refuted,
        "accuracy": round(confirmed / graded, 3) if graded else None,
    }
