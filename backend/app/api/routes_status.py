"""GET /api/instability, GET /api/sources/status (Section 8.1)."""
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
