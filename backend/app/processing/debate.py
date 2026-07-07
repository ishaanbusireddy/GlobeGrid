"""v3 §2 — multi-agent debate causal engine.

Runs the Section 9 cluster payload through three independent LLM calls —
Skeptic, Historian, Optimist — identical input, different persona framing,
routed through the configured provider fallback (v5 §18). All three
outputs are stored; the primary single-call narrative remains the
displayed default. disagreement_score = average pairwise embedding
distance between the personas' cause strings; high disagreement is
surfaced as a distinct UI state, not buried in a number.

Independently-failing step: a debate failure never blocks the primary
narrative (v1 §10.2 discipline). Graceful no-op without a configured AI
provider.
"""

import itertools
import json
import logging

from . import llm
from ..config import cfg
from ..db.models import new_id, now_iso
from ..db.session import query, write_tx
from .causal_link import SYSTEM_PROMPT, _cluster_facts, _validate
from .embed import embed_text, cosine

log = logging.getLogger("debate")

PERSONA_PREFIXES = {
    "skeptic": (
        "PERSONA: THE SKEPTIC. Before anything else, actively look for reasons the"
        " causal claim might be wrong, overstated, or coincidental. Prefer the most"
        " conservative reading the evidence still supports.\n\n"),
    "historian": (
        "PERSONA: THE HISTORIAN. Weigh this cluster against similar historical"
        " patterns — does the sequence match how comparable situations have"
        " actually unfolded before? Ground the causal reading in precedent.\n\n"),
    "optimist": (
        "PERSONA: THE OPTIMIST. Give the most charitable causal reading the"
        " evidence actually supports — not blind positivity, just the"
        " least-skeptical honest interpretation.\n\n"),
}


def _persona_call(persona: str, payload: dict):
    text = llm.complete(PERSONA_PREFIXES[persona] + SYSTEM_PROMPT,
                        [{"role": "user", "content": json.dumps(payload)}],
                        max_tokens=1024, timeout=60)
    if text is None:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    narrative = json.loads(text)
    return narrative if _validate(narrative) else None


def generate_debate(story_id: str) -> float | None:
    """Run all personas for one story; returns disagreement_score or None."""
    if not llm.available():
        return None
    personas = cfg("debate", "personas")
    facts = _cluster_facts(story_id)
    if not facts:
        return None
    payload = {"cluster_facts": facts}
    outputs = {}
    for persona in personas:
        if persona not in PERSONA_PREFIXES:
            continue
        try:
            narrative = _persona_call(persona, payload)
            if narrative:
                outputs[persona] = narrative
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("debate_persona_failed", extra={"data": {
                "story_id": story_id, "persona": persona, "error": str(exc)}})
    if len(outputs) < 2:
        return None

    # disagreement = average pairwise embedding distance between cause strings
    vecs = {p: embed_text(n["cause"]) for p, n in outputs.items()}
    distances = [1.0 - cosine(vecs[a], vecs[b])
                 for a, b in itertools.combinations(vecs, 2)]
    disagreement = round(sum(distances) / len(distances), 4)

    with write_tx() as conn:
        for persona, narrative in outputs.items():
            conn.execute(
                "INSERT INTO causal_debate (id, story_id, persona, narrative, generated_at)"
                " VALUES (?,?,?,?,?)"
                " ON CONFLICT(story_id, persona) DO UPDATE SET"
                "   narrative = excluded.narrative, generated_at = excluded.generated_at",
                (new_id(), story_id, persona, json.dumps(narrative), now_iso()))
        conn.execute(
            "UPDATE stories SET disagreement_score = ?, debate_generated_at = ?"
            " WHERE id = ?", (disagreement, now_iso(), story_id))
    log.info("debate_generated", extra={"data": {"story_id": story_id,
                                                 "personas": list(outputs),
                                                 "disagreement": disagreement}})
    return disagreement


def debate_for_story(story_id: str) -> dict:
    rows = query("SELECT persona, narrative, generated_at FROM causal_debate"
                 " WHERE story_id = ?", (story_id,))
    out = {}
    for r in rows:
        try:
            out[r["persona"]] = json.loads(r["narrative"])
        except json.JSONDecodeError:
            continue
    return out
