"""GET /api/stories, GET /api/stories/{id} (Section 8.1)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.common import parse_since, source_and_link
from app.db.models import Event, ExtractedFact, RawItem, Story, StoryMember
from app.db.session import get_db

router = APIRouter(prefix="/api/stories", tags=["stories"])

DEFAULT_LIMIT = 50


def _member_categories_and_sources(session: Session, members: list[StoryMember]) -> tuple[set, set]:
    categories = set()
    source_ids = set()
    for member in members:
        if member.event_id:
            event = session.get(Event, member.event_id)
            if event:
                categories.add(event.category)
                if event.raw_item:
                    source_ids.add(event.raw_item.source_id)
        if member.fact_id:
            fact = session.get(ExtractedFact, member.fact_id)
            if fact:
                source_ids.add(fact.source_id)
    return categories, source_ids


def story_summary(session: Session, story: Story) -> dict:
    members = session.query(StoryMember).filter(StoryMember.story_id == story.id).all()
    categories, source_ids = _member_categories_and_sources(session, members)

    return {
        "id": str(story.id),
        "headline": story.headline,
        "summary": story.summary,
        "confidence": story.confidence,
        "first_seen_at": story.first_seen_at,
        "last_updated_at": story.last_updated_at,
        "member_count": len(members),
        "source_count": len(source_ids),
        "categories": sorted(categories),
    }


@router.get("")
def list_stories(
    since: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    category: Optional[str] = None,
    session: Session = Depends(get_db),
):
    """List recent story clusters, newest first. `since` supports the
    Section 8.2 15s REST-polling fallback (`?since=<ISO timestamp>`)."""
    query = session.query(Story)

    since_dt = parse_since(since)
    if since_dt is not None:
        query = query.filter(Story.last_updated_at >= since_dt)

    stories = query.order_by(Story.last_updated_at.desc().nullslast()).limit(max(1, min(limit, 500))).all()

    summaries = [story_summary(session, s) for s in stories]
    if category:
        summaries = [s for s in summaries if category in s["categories"]]

    return summaries


@router.get("/{story_id}")
def get_story(story_id: str, session: Session = Depends(get_db)):
    """Full story detail: members, causal_narrative, sources (Section 8.1)."""
    story = session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")

    members = session.query(StoryMember).filter(StoryMember.story_id == story.id).all()

    member_payloads = []
    for member in members:
        if member.event_id:
            event = session.get(Event, member.event_id)
            raw_item = session.get(RawItem, event.raw_item_id) if event else None
            link_info = source_and_link(session, source_id=raw_item.source_id if raw_item else None, raw_item=raw_item)
            member_payloads.append({
                "kind": "event",
                "id": str(event.id),
                "title": event.title,
                "description": event.description,
                "category": event.category,
                "severity": event.severity,
                "occurred_at": event.occurred_at,
                "linked_via": member.linked_via,
                "linked_at": member.linked_at,
                **link_info,
            })
        elif member.fact_id:
            fact = session.get(ExtractedFact, member.fact_id)
            raw_item = None
            if fact and fact.event_id:
                event = session.get(Event, fact.event_id)
                raw_item = session.get(RawItem, event.raw_item_id) if event else None
            link_info = source_and_link(session, source_id=fact.source_id if fact else None, raw_item=raw_item)
            member_payloads.append({
                "kind": "fact",
                "id": str(fact.id),
                "who": fact.who,
                "what": fact.what,
                "where": fact.where,
                "when_occurred": fact.when_occurred,
                "linked_via": member.linked_via,
                "linked_at": member.linked_at,
                **link_info,
            })

    categories, source_ids = _member_categories_and_sources(session, members)

    return {
        "id": str(story.id),
        "headline": story.headline,
        "summary": story.summary,
        "causal_narrative": story.causal_narrative,
        "confidence": story.confidence,
        "first_seen_at": story.first_seen_at,
        "last_updated_at": story.last_updated_at,
        "categories": sorted(categories),
        "source_count": len(source_ids),
        "members": member_payloads,
    }
