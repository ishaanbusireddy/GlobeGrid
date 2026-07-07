"""Stage 5 — causal linking via the configured LLM provider (Sections 5.5
and 9).

One call per newly formed or updated story cluster, routed through
processing.llm's provider-fallback abstraction (v5 §18) — Groq by default,
Claude as an optional upgrade — rather than a single hardcoded provider.
The system prompt and JSON output shape are the Section 9 template
verbatim. Output is validated; malformed JSON triggers exactly one retry; a
second failure (or no configured provider) marks the story confidence
'low' with a null narrative rather than blocking the pipeline.

Results are cached on stories.causal_narrative and regenerated only when
new members are added (needs_causal_refresh flag) — never on page view.
"""

import json
import logging
import time

from . import llm
from ..db.models import now_iso
from ..db.session import query, query_one, write_tx

log = logging.getLogger("causal_link")

# Section 9 system prompt — verbatim.
SYSTEM_PROMPT = """You are a geopolitical and global-events analyst. You will be given a cluster
of correlated facts, each with a timestamp and source. Determine whether
they describe a connected sequence of cause and effect.

Return ONLY valid JSON matching this shape:
{
  "cause": string,
  "affected": string[],
  "consequences": string[],
  "confidence": "high" | "medium" | "low"
}

Rules:
- Never state certainty the evidence does not support.
- Use timestamp order as a first signal for causal direction, but only
  state a direction when the evidence actually supports it.
- If the cluster does not support a clear causal story, set confidence
  to "low" and describe the connection as correlational, not causal.
- Do not invent facts not present in the input."""

def _cluster_facts(story_id: str) -> list[dict]:
    rows = query(
        'SELECT f.who, f.what, f."where" AS where_text, f.when_occurred, s.name AS source'
        " FROM story_members m JOIN extracted_facts f ON f.id = m.fact_id"
        " JOIN sources s ON s.id = f.source_id WHERE m.story_id = ?"
        " UNION "
        'SELECT f.who, f.what, f."where", f.when_occurred, s.name'
        " FROM story_members m JOIN events e ON e.id = m.event_id"
        " JOIN extracted_facts f ON f.event_id = e.id"
        " JOIN sources s ON s.id = f.source_id WHERE m.story_id = ?"
        " ORDER BY when_occurred", (story_id, story_id))
    return [{"source": r["source"], "timestamp": r["when_occurred"], "who": r["who"],
             "what": r["what"], "where": r["where_text"] or "n/a"} for r in rows]


def _validate(narrative) -> bool:
    return (isinstance(narrative, dict)
            and isinstance(narrative.get("cause"), str)
            and isinstance(narrative.get("affected"), list)
            and all(isinstance(x, str) for x in narrative["affected"])
            and isinstance(narrative.get("consequences"), list)
            and all(isinstance(x, str) for x in narrative["consequences"])
            and narrative.get("confidence") in ("high", "medium", "low"))


def _causal_override() -> str | None:
    """v6 §1 — causal narratives are the one quality-critical, low-volume
    call site allowed an independent provider override
    (llm_provider.causal_link_override); everything else defaults to Groq."""
    from ..config import cfg
    try:
        return str(cfg("llm_provider", "causal_link_override")) or None
    except (KeyError, TypeError):
        return None


def _call_llm(payload: dict):
    """Returns (narrative_dict_or_None, latency_ms)."""
    start = time.monotonic()
    text = llm.complete(SYSTEM_PROMPT,
                        [{"role": "user", "content": json.dumps(payload)}],
                        max_tokens=1024, timeout=60, prefer=_causal_override())
    latency_ms = int((time.monotonic() - start) * 1000)
    if text is None:
        return None, latency_ms
    log.info("causal_llm_call", extra={"data": {"latency_ms": latency_ms}})
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        narrative = json.loads(text)
    except json.JSONDecodeError:
        return None, latency_ms
    return (narrative if _validate(narrative) else None), latency_ms


def generate_for_story(story_id: str) -> None:
    """Generate (or refuse gracefully) the causal narrative for one story."""
    facts = _cluster_facts(story_id)
    narrative = None
    if llm.available() and facts:
        payload = {"cluster_facts": facts}
        narrative, _ = _call_llm(payload)
        if narrative is None:  # one retry on malformed output (Section 9)
            narrative, _ = _call_llm(payload)
    elif not llm.available():
        log.info("causal_llm_skipped", extra={"data": {
            "story_id": story_id, "reason": "no AI provider configured"}})

    # v3 §12 — preserve the outgoing narrative version before overwriting
    prior = query_one("SELECT causal_narrative, confidence FROM stories WHERE id = ?",
                      (story_id,))
    with write_tx() as conn:
        if prior and prior["causal_narrative"] and narrative is not None:
            from ..db.models import new_id as _nid
            conn.execute(
                "INSERT INTO story_narrative_versions (id, story_id, causal_narrative,"
                " confidence, superseded_at) VALUES (?,?,?,?,?)",
                (_nid(), story_id, prior["causal_narrative"], prior["confidence"],
                 now_iso()))
        if narrative is not None:
            summary = _derive_summary(narrative, facts)
            conn.execute(
                "UPDATE stories SET causal_narrative = ?, confidence = ?, summary = ?,"
                " needs_causal_refresh = 0, counter_argument = NULL,"
                " confidence_pre_devil_advocate = NULL WHERE id = ?",
                (json.dumps(narrative), narrative["confidence"], summary, story_id))
            # v2 §3.4 — one predictions row per stated consequence, so the
            # scorecard can grade the model against later facts.
            # v3 §11 — each prediction insert is hash-chained.
            from ..db.models import new_id
            from .provenance import next_hashes
            for consequence in narrative.get("consequences", []):
                exists = conn.execute(
                    "SELECT 1 FROM predictions WHERE story_id = ? AND consequence_text = ?",
                    (story_id, consequence)).fetchone()
                if not exists:
                    pid, predicted_at = new_id(), now_iso()
                    row_hash, prev_hash = next_hashes("predictions", {
                        "id": pid, "story_id": story_id,
                        "consequence_text": consequence, "predicted_at": predicted_at,
                        "kind": "retrospective_consequence",
                        "horizon_hours": None, "region": None})
                    conn.execute(
                        "INSERT INTO predictions (id, story_id, consequence_text,"
                        " predicted_at, kind, row_hash, prev_hash) VALUES (?,?,?,?,?,?,?)",
                        (pid, story_id, consequence, predicted_at,
                         "retrospective_consequence", row_hash, prev_hash))
        else:
            # Fallback path: low confidence, null narrative, pipeline unblocked.
            conn.execute(
                "UPDATE stories SET causal_narrative = NULL, confidence = 'low',"
                " summary = COALESCE(NULLIF(summary,''), ?), needs_causal_refresh = 0"
                " WHERE id = ?",
                (_derive_summary(None, facts), story_id))


def _derive_summary(narrative, facts) -> str:
    from .textquality import normalize_summary   # v4 §11.1
    if narrative:
        parts = [narrative["cause"]]
        if narrative["affected"]:
            parts.append("Affected: " + ", ".join(narrative["affected"][:5]) + ".")
        if narrative["consequences"]:
            parts.append("Likely consequences: " + "; ".join(narrative["consequences"][:3]) + ".")
        return normalize_summary(" ".join(p.rstrip(".") + "." for p in parts if p))
    if facts:
        span = f"{facts[0]['timestamp'][:10]} – {facts[-1]['timestamp'][:10]}"
        outlets = sorted({f["source"] for f in facts})
        return (f"Cluster of {len(facts)} correlated facts ({span}) reported by "
                f"{', '.join(outlets[:4])}. Causal analysis pending.")
    return "Correlated story cluster. Causal analysis pending."


DEVILS_ADVOCATE_PROMPT = """You are stress-testing a causal claim before it is shown to a reader.
Given the primary causal narrative and the underlying cluster facts,
answer specifically: what would have to be false for this causal claim
to be wrong?

Return ONLY valid JSON matching this shape:
{
  "counter_argument": string,
  "weakens_confidence": true | false,
  "revised_confidence": "high" | "medium" | "low" | null
}

Rules:
- Your job is to catch overclaiming, not to add reassurance. You may only
  lower confidence, never raise it — if the claim survives your challenge,
  set weakens_confidence to false and revised_confidence to null.
- The counter_argument must be a genuine alternative reading of the same
  evidence, not a generic disclaimer.
- Do not invent facts not present in the input."""

_CONF_RANK = {"low": 0, "medium": 1, "high": 2}


def devils_advocate_pass(story_id: str) -> None:
    """v3 §3 — one extra call that can only ever LOWER confidence."""
    if not llm.available() or not cfg_devils_advocate_enabled():
        return
    story = query_one("SELECT causal_narrative, confidence FROM stories WHERE id = ?",
                      (story_id,))
    if not story or not story["causal_narrative"]:
        return
    payload = {"primary_narrative": json.loads(story["causal_narrative"]),
               "cluster_facts": _cluster_facts(story_id)}
    text = llm.complete(DEVILS_ADVOCATE_PROMPT,
                        [{"role": "user", "content": json.dumps(payload)}],
                        max_tokens=700, timeout=60, prefer=_causal_override())
    if text is None:
        log.warning("devils_advocate_failed", extra={"data": {
            "story_id": story_id, "error": "no provider available"}})
        return
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError as exc:
        log.warning("devils_advocate_failed", extra={"data": {"story_id": story_id,
                                                              "error": str(exc)}})
        return
    if not isinstance(verdict, dict) or not isinstance(verdict.get("counter_argument"), str):
        return
    weakens = bool(verdict.get("weakens_confidence"))
    revised = verdict.get("revised_confidence")
    with write_tx() as conn:
        if weakens and revised in ("high", "medium", "low") and \
                _CONF_RANK[revised] < _CONF_RANK.get(story["confidence"], 0):
            # downgrade only — the pass can never raise confidence (§3.1)
            conn.execute(
                "UPDATE stories SET counter_argument = ?,"
                " confidence_pre_devil_advocate = confidence, confidence = ?"
                " WHERE id = ?",
                (verdict["counter_argument"], revised, story_id))
            log.info("devils_advocate_downgrade", extra={"data": {
                "story_id": story_id, "from": story["confidence"], "to": revised}})
        else:
            conn.execute("UPDATE stories SET counter_argument = ? WHERE id = ?",
                         (verdict["counter_argument"], story_id))


def cfg_devils_advocate_enabled() -> bool:
    from ..config import cfg
    return bool(cfg("devils_advocate", "enabled"))


def refresh_pending(limit: int = 10) -> int:
    """Process clusters flagged by Stage 4; per-cluster error boundaries so a
    failure on one cluster never blocks the batch (Section 10.2)."""
    rows = query("SELECT id FROM stories WHERE needs_causal_refresh = 1 AND is_synthetic = 0"
                 " ORDER BY last_updated_at LIMIT ?", (limit,))
    done = 0
    for row in rows:
        try:
            generate_for_story(row["id"])
            done += 1
        except Exception:  # noqa: BLE001
            log.exception("causal_link_failed", extra={"data": {"story_id": row["id"]}})
            with write_tx() as conn:
                conn.execute("UPDATE stories SET needs_causal_refresh = 0,"
                             " confidence = 'low' WHERE id = ?", (row["id"],))
            continue
        # v3 §3 devil's advocate + §2 debate: independently-failing layers —
        # neither ever blocks the primary narrative (v1 §10.2 discipline).
        try:
            devils_advocate_pass(row["id"])
        except Exception:  # noqa: BLE001
            log.exception("devils_advocate_error", extra={"data": {"story_id": row["id"]}})
        try:
            from .debate import generate_debate
            generate_debate(row["id"])
        except Exception:  # noqa: BLE001
            log.exception("debate_error", extra={"data": {"story_id": row["id"]}})
    return done
