"""RSS ingestion (Section 4.1): BBC World, Al Jazeera, NYT World, Washington
Post, CNN World, NPR, and Reuters-via-Google-News. All are polled from
source.url — the specific feed URLs live in the seeded sources rows
(scripts/seed_sources.py), not hardcoded here, so this module works for any
RSS-type source.
"""
import feedparser

from app.db.models import Source


def fetch(source: Source) -> list[dict]:
    parsed = feedparser.parse(source.url)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        raise RuntimeError(f"RSS parse failed for {source.url}: {parsed.get('bozo_exception')}")

    items = []
    for entry in parsed.entries:
        items.append(
            {
                "title": entry.get("title"),
                "summary": entry.get("summary", entry.get("description")),
                "link": entry.get("link"),
                "published": entry.get("published", entry.get("updated")),
                "id": entry.get("id", entry.get("link")),
            }
        )
    return items
