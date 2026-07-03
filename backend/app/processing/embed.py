"""Stage 3 (Section 2.1, 3.1): embeds every extracted fact and event from its
normalized description, not raw text — all-MiniLM-L6-v2, 384-dim, CPU, no
external API (EMBEDDING_MODEL_NAME, Section 7.1).
"""
import logging
from functools import lru_cache

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Event, ExtractedFact
from app.logging_setup import log_with_fields

logger = logging.getLogger("embedding")


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embedding_model_name)


def _fact_text(fact: ExtractedFact) -> str:
    parts = [fact.who, fact.what]
    if fact.where:
        parts.append(fact.where)
    return " — ".join(p for p in parts if p)


def run_embedding(session: Session, batch_size: int = 200) -> tuple[int, int]:
    """Embeds up to batch_size unembedded events and batch_size unembedded
    extracted_facts. Returns (events_embedded, facts_embedded)."""
    model = _get_model()

    events = session.query(Event).filter(Event.embedding.is_(None)).limit(batch_size).all()
    if events:
        vectors = model.encode([e.description for e in events], normalize_embeddings=True)
        for event, vector in zip(events, vectors):
            event.embedding = vector.tolist()

    facts = (
        session.query(ExtractedFact)
        .filter(ExtractedFact.embedding.is_(None))
        .limit(batch_size)
        .all()
    )
    if facts:
        vectors = model.encode([_fact_text(f) for f in facts], normalize_embeddings=True)
        for fact, vector in zip(facts, vectors):
            fact.embedding = vector.tolist()

    log_with_fields(
        logger, logging.INFO, "embedding batch complete",
        events_embedded=len(events), facts_embedded=len(facts),
    )
    return len(events), len(facts)
