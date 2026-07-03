"""Stage 5 (Section 2.1, 5.5): one Claude API call per newly formed or
updated story cluster, using the exact prompt template from Section 9.

Called from the pipeline right after correlate.run_correlation() adds a
member to a story (see run_causal_linking / scripts/run_correlation_once.py)
— this is what makes "regenerated only when new members are added, never on
every page view" (Section 5.5) hold without needing extra tracking schema:
regeneration is event-driven off the correlation step itself, not polled by
the API layer.
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Event, ExtractedFact, Source, Story, StoryMember
from app.logging_setup import log_with_fields

logger = logging.getLogger("causal_link")

# Section 9 — verbatim, do not edit without updating the manual.
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

_VALID_CONFIDENCE = {"high", "medium", "low"}


def _validate_shape(parsed: dict) -> bool:
    if not isinstance(parsed, dict):
        return False
    if not isinstance(parsed.get("cause"), str):
        return False
    if not isinstance(parsed.get("affected"), list) or not all(isinstance(x, str) for x in parsed["affected"]):
        return False
    if not isinstance(parsed.get("consequences"), list) or not all(isinstance(x, str) for x in parsed["consequences"]):
        return False
    if parsed.get("confidence") not in _VALID_CONFIDENCE:
        return False
    return True


def _cluster_facts_payload(session: Session, story: Story) -> list[dict]:
    members = session.query(StoryMember).filter(StoryMember.story_id == story.id).all()
    facts = []

    for member in members:
        if member.event_id is not None:
            event = session.get(Event, member.event_id)
            source = None
            if event.raw_item and event.raw_item.source:
                source = event.raw_item.source.name
            facts.append({
                "source": source or "unknown",
                "timestamp": event.occurred_at.isoformat(),
                "who": event.location_name or "unspecified",
                "what": event.description,
                "where": event.location_name or "n/a",
            })
        elif member.fact_id is not None:
            fact = session.get(ExtractedFact, member.fact_id)
            source = session.get(Source, fact.source_id)
            facts.append({
                "source": source.name if source else "unknown",
                "timestamp": fact.when_occurred.isoformat(),
                "who": fact.who,
                "what": fact.what,
                "where": fact.where or "n/a",
            })

    return facts


def _derive_headline_summary(parsed: dict) -> tuple[str, str]:
    # Section 9's locked prompt/output shape has no headline/summary fields
    # (those belong to stories per Section 6.5, generated separately here
    # rather than by altering the fixed Section 9 call) — derived directly
    # from the structured narrative so they stay consistent with it.
    headline = parsed["cause"][:200] if parsed["cause"] else "Untitled story"
    consequence_text = "; ".join(parsed["consequences"]) if parsed["consequences"] else "no clear downstream effects identified"
    summary = f"{parsed['cause']} Affected: {', '.join(parsed['affected']) or 'unspecified'}. Consequences: {consequence_text}."
    return headline, summary


def _call_claude(client, model: str, user_payload: dict) -> tuple[Optional[dict], int, int]:
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(user_payload)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None, input_tokens, output_tokens

    return (parsed if _validate_shape(parsed) else None), input_tokens, output_tokens


def generate_causal_narrative(session: Session, story: Story) -> None:
    settings = get_settings()
    if not settings.claude_api_key:
        raise RuntimeError("CLAUDE_API_KEY is not configured (see backend/.env.example)")

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.claude_api_key)
    user_payload = {"cluster_facts": _cluster_facts_payload(session, story)}

    parsed = None
    total_input_tokens = total_output_tokens = 0
    start = time.monotonic()

    for attempt in range(2):  # one retry on malformed output, per Section 9
        parsed, input_tokens, output_tokens = _call_claude(client, settings.claude_model, user_payload)
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        if parsed is not None:
            break

    latency_ms = int((time.monotonic() - start) * 1000)
    log_with_fields(
        logger, logging.INFO, "causal-link LLM call",
        story_id=str(story.id), input_tokens=total_input_tokens,
        output_tokens=total_output_tokens, latency_ms=latency_ms,
        attempts=attempt + 1, succeeded=parsed is not None,
    )

    if parsed is None:
        # Second failure: mark confidence low with a null narrative rather
        # than blocking the pipeline (Section 9).
        story.causal_narrative = None
        story.confidence = "low"
        return

    story.causal_narrative = parsed
    story.confidence = parsed["confidence"]
    story.headline, story.summary = _derive_headline_summary(parsed)


def run_causal_linking(session: Session, story_ids) -> tuple[int, int]:
    """Generates/regenerates the narrative for exactly the given story ids
    (the ones that just gained a member in this pass). Returns
    (succeeded, failed) — a failure here never blocks other clusters in the
    same batch (Section 10.2)."""
    succeeded = failed = 0
    for story_id in story_ids:
        story = session.get(Story, story_id)
        if story is None:
            continue
        try:
            generate_causal_narrative(session, story)
            succeeded += 1
        except Exception as exc:  # noqa: BLE001 - one bad cluster must not block the rest
            failed += 1
            log_with_fields(
                logger, logging.ERROR, "causal linking failed for story",
                story_id=str(story_id), error=str(exc),
            )

    log_with_fields(
        logger, logging.INFO, "causal linking batch complete",
        succeeded=succeeded, failed=failed,
    )
    return succeeded, failed
