"""v2 addendum §3.7 — second-order causal reasoning.

Detects when two 'unrelated' story clusters are both downstream of a
shared root cause neither surfaced. Periodically picks pairs of recent
clusters that share canonical entities (§3.1) but were never correlated
directly, and asks a Section 9-style prompt specifically whether a common
upstream cause connects them. Deliberately last in the build order —
depends on canonicalization quality to find worthwhile candidate pairs.
"""

import itertools
import json
import logging
from datetime import datetime, timedelta, timezone

from . import llm
from ..config import cfg
from ..db.models import new_id, now_iso
from ..db.session import query, query_one, write_tx

log = logging.getLogger("second_order")

SYSTEM_PROMPT = """You are a geopolitical and global-events analyst. You will be given TWO
separately-correlated story clusters that share at least one entity but
were never directly linked. Determine whether a COMMON UPSTREAM CAUSE
plausibly connects them.

Return ONLY valid JSON matching this shape:
{
  "connected": true | false,
  "common_cause": string,
  "reasoning": string,
  "confidence": "high" | "medium" | "low"
}

Rules:
- Never state certainty the evidence does not support.
- If no credible common upstream cause exists, set connected to false.
- Do not invent facts not present in the input."""


def _story_entities(story_id: str) -> frozenset:
    rows = query(
        "SELECT f.canonical_entity_ids FROM story_members m"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE m.story_id = ? AND f.canonical_entity_ids IS NOT NULL", (story_id,))
    ents: set = set()
    for r in rows:
        ents.update(json.loads(r["canonical_entity_ids"]))
    return frozenset(ents)


def _cluster_summary(story_id: str) -> dict:
    story = query_one("SELECT headline, summary FROM stories WHERE id = ?", (story_id,))
    facts = query(
        'SELECT f.who, f.what, f."where" AS where_text, f.when_occurred'
        " FROM story_members m JOIN extracted_facts f"
        " ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE m.story_id = ? GROUP BY f.id ORDER BY f.when_occurred LIMIT 10", (story_id,))
    return {"headline": story["headline"],
            "facts": [{"who": f["who"], "what": f["what"], "where": f["where_text"] or "n/a",
                       "timestamp": f["when_occurred"]} for f in facts]}


def scan_once() -> int:
    """One scan pass; returns number of new second-order links stored."""
    if not llm.available():
        return 0
    min_shared = int(cfg("second_order", "min_shared_entities"))
    max_pairs = int(cfg("second_order", "max_pairs_per_scan"))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=96)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    stories = query(
        "SELECT id FROM stories WHERE is_synthetic = 0 AND last_updated_at >= ?"
        " ORDER BY last_updated_at DESC LIMIT 20", (cutoff,))
    ent_map = {s["id"]: _story_entities(s["id"]) for s in stories}

    candidates = []
    for a, b in itertools.combinations([s["id"] for s in stories], 2):
        shared = ent_map[a] & ent_map[b]
        if len(shared) < min_shared:
            continue
        pair = tuple(sorted((a, b)))
        already = query_one(
            "SELECT 1 FROM second_order_links WHERE story_a_id = ? AND story_b_id = ?",
            pair)
        directly_linked = query_one(
            "SELECT 1 FROM story_members m1 JOIN story_members m2"
            " ON m1.event_id = m2.event_id WHERE m1.story_id = ? AND m2.story_id = ?",
            (a, b))
        if not already and not directly_linked:
            candidates.append((pair, len(shared)))
    candidates.sort(key=lambda c: -c[1])

    stored = 0
    for (a, b), _n in candidates[:max_pairs]:
        try:
            payload = {"cluster_a": _cluster_summary(a), "cluster_b": _cluster_summary(b)}
            text = llm.complete(SYSTEM_PROMPT,
                                [{"role": "user", "content": json.dumps(payload)}],
                                max_tokens=800, timeout=60)
            if text is None:
                continue
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            verdict = json.loads(text)
            if not isinstance(verdict, dict) or \
                    verdict.get("confidence") not in ("high", "medium", "low"):
                continue
            if verdict.get("connected"):
                with write_tx() as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO second_order_links"
                        " (id, story_a_id, story_b_id, narrative, confidence, created_at)"
                        " VALUES (?,?,?,?,?,?)",
                        (new_id(), a, b, json.dumps(verdict), verdict["confidence"],
                         now_iso()))
                stored += 1
                log.info("second_order_link", extra={"data": {
                    "story_a": a, "story_b": b, "confidence": verdict["confidence"]}})
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("second_order_failed", extra={"data": {"error": str(exc)}})
    return stored
