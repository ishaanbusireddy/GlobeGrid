"""v2 addendum §1.2/§1.3 — Wikipedia signals.

Two source types share this module:
  - 'wikipedia': the Wikimedia featured-feed "In the news" items — a
    curated cross-check against the automated feed (sanity signal, not a
    primary source).
  - 'wiki_views': pageview-spike detection — for the most-active recent
    canonical entities, compare yesterday's article views against the
    prior week's average; a large spike is a strong, low-noise attention
    signal.
"""

import json
import re
import urllib.parse
from datetime import datetime, timedelta, timezone

from ...db.session import query
from ..http import fetch_url

_TAG_RE = re.compile(r"<[^>]+>")

SPIKE_RATIO = 3.0
MIN_VIEWS = 5000
MAX_ENTITIES = 8


def fetch_current_events(source: dict) -> list[dict]:
    day = datetime.now(timezone.utc)
    url = (f"https://api.wikimedia.org/feed/v1/wikipedia/en/featured/"
           f"{day.year}/{day.month:02d}/{day.day:02d}")
    data = json.loads(fetch_url(url, headers={"Accept": "application/json"}))
    items = []
    for entry in data.get("news", []):
        text = _TAG_RE.sub("", entry.get("story", "")).strip()
        if not text:
            continue
        links = entry.get("links") or []
        first = links[0] if links else {}
        page_url = (first.get("content_urls", {}).get("desktop", {}) or {}).get("page", "")
        items.append({
            "title": text[:280],
            "summary": "Wikipedia Current Events (curated cross-check)",
            "link": page_url or "https://en.wikipedia.org/wiki/Portal:Current_events",
            "published": day.strftime("%Y-%m-%dT00:00:00Z"),
            "external_id": text[:120],
        })
    return items


def _recent_entity_names(limit: int) -> list[str]:
    rows = query(
        "SELECT ce.canonical_name, COUNT(*) AS n FROM extracted_facts f"
        " JOIN json_each(f.canonical_entity_ids) je"
        " JOIN canonical_entities ce ON ce.id = je.value"
        " WHERE f.created_at >= datetime('now', '-2 day')"
        " GROUP BY ce.id ORDER BY n DESC LIMIT ?", (limit,))
    return [r["canonical_name"] for r in rows]


def fetch_pageview_spikes(source: dict) -> list[dict]:
    now = datetime.now(timezone.utc)
    end = (now - timedelta(days=1)).strftime("%Y%m%d")
    start = (now - timedelta(days=8)).strftime("%Y%m%d")
    items = []
    for name in _recent_entity_names(MAX_ENTITIES):
        title = urllib.parse.quote(name.replace(" ", "_"), safe="")
        url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
               f"en.wikipedia/all-access/all-agents/{title}/daily/{start}/{end}")
        try:
            data = json.loads(fetch_url(url, headers={"Accept": "application/json"}))
        except Exception:  # noqa: BLE001 — article may not exist; skip quietly
            continue
        points = data.get("items", [])
        if len(points) < 3:
            continue
        views = [p["views"] for p in points]
        yesterday = views[-1]
        baseline = sum(views[:-1]) / max(1, len(views) - 1)
        if yesterday >= MIN_VIEWS and baseline > 0 and yesterday / baseline >= SPIKE_RATIO:
            items.append({
                "title": f"Attention spike: Wikipedia views for {name} up "
                         f"{yesterday / baseline:.1f}x",
                "summary": f"{yesterday:,} views yesterday vs {baseline:,.0f}/day prior"
                           " week average.",
                "link": f"https://en.wikipedia.org/wiki/{title}",
                "published": (now - timedelta(days=1)).strftime("%Y-%m-%dT12:00:00Z"),
                "external_id": f"{name}-{end}",
                "who": name,
                "what": f"public attention spike, {yesterday / baseline:.1f}x baseline views",
            })
    return items


def fetch(source: dict) -> list[dict]:
    if source["type"] == "wiki_views":
        return fetch_pageview_spikes(source)
    return fetch_current_events(source)
