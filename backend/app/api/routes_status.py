"""GET /api/instability, GET /api/sources/status (Section 8.1), plus the
Section 5.8 display-time translation call (POST /api/translate)."""
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import InstabilityScore, Source
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["status"])

_RANGE_RE = re.compile(r"^(\d+)([hd])$")


def _parse_range(range_str: str) -> timedelta:
    match = _RANGE_RE.match(range_str.strip())
    if not match:
        raise HTTPException(status_code=400, detail="range must look like '72h' or '7d'")
    amount, unit = match.groups()
    amount = int(amount)
    return timedelta(hours=amount) if unit == "h" else timedelta(days=amount)


@router.get("/instability")
def get_instability(range: str = "72h", session: Session = Depends(get_db)):
    """Latest score + historical trend (Section 8.1), default 72h."""
    window = _parse_range(range)
    since = datetime.now(timezone.utc) - window

    history = (
        session.query(InstabilityScore)
        .filter(InstabilityScore.computed_at >= since)
        .order_by(InstabilityScore.computed_at.asc())
        .all()
    )
    latest = history[-1] if history else session.query(InstabilityScore).order_by(
        InstabilityScore.computed_at.desc()
    ).first()

    return {
        "latest": {
            "score": float(latest.score),
            "computed_at": latest.computed_at,
            "component_breakdown": latest.component_breakdown,
        } if latest else None,
        "history": [
            {"score": float(row.score), "computed_at": row.computed_at}
            for row in history
        ],
    }


@router.get("/sources/status")
def get_sources_status(session: Session = Depends(get_db)):
    """Health status of every registered source (Section 8.1, 5.10)."""
    sources = session.query(Source).order_by(Source.name).all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "type": s.type,
            "leaning": s.leaning,
            "poll_interval_seconds": s.poll_interval_seconds,
            "health_status": s.health_status,
            "last_fetched_at": s.last_fetched_at,
            "last_error": s.last_error,
        }
        for s in sources
    ]


class TranslateRequest(BaseModel):
    text: str
    target_language: str = "English"


@router.post("/translate")
def translate(body: TranslateRequest):
    """Section 5.8: translation happens at display time, not ingestion time —
    the original text is never modified; the client keeps it and toggles.
    Short-summary translation only (full-article translation is out of
    scope; the outbound link to the original suffices)."""
    settings = get_settings()
    if not settings.claude_api_key:
        raise HTTPException(status_code=503, detail="translation unavailable: CLAUDE_API_KEY not configured")
    if len(body.text) > 4000:
        raise HTTPException(status_code=400, detail="display-time translation is for short summaries only")

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.claude_api_key)
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system="Translate the user's text. Return only the translation, no commentary.",
        messages=[{"role": "user", "content": f"Translate into {body.target_language}:\n\n{body.text}"}],
    )
    translated = "".join(block.text for block in response.content if block.type == "text")
    return {"original": body.text, "translated": translated, "target_language": body.target_language}
