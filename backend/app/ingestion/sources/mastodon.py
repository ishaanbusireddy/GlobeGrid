"""v2 addendum §1.3 — Mastodon public feeds.

Polls the public hashtag timelines of a small curated instance list — no
auth needed for public timelines. Less locked-down alternative to Reddit.
"""

import json
import re

from ..http import fetch_url

INSTANCES = ["mastodon.social", "mstdn.social"]
HASHTAGS = ["worldnews", "geopolitics", "breakingnews"]

_TAG_RE = re.compile(r"<[^>]+>")


def fetch(source: dict) -> list[dict]:
    items, errors = [], []
    for instance in INSTANCES:
        for tag in HASHTAGS:
            url = f"https://{instance}/api/v1/timelines/tag/{tag}?limit=10"
            try:
                posts = json.loads(fetch_url(url, timeout=20))
            except Exception as exc:  # noqa: BLE001 — one instance down != source down
                errors.append(f"{instance}/{tag}: {exc}")
                continue
            for post in posts:
                text = _TAG_RE.sub(" ", post.get("content", "")).strip()
                if len(text) < 40 or post.get("reblog"):
                    continue
                items.append({
                    "title": text[:200],
                    "summary": f"#{tag} on {instance} · "
                               f"{post.get('reblogs_count', 0)} boosts",
                    "link": post.get("url", ""),
                    "published": post.get("created_at", ""),
                    "external_id": post.get("uri") or post.get("id"),
                    "who": f"Mastodon #{tag} community",
                })
    if not items and errors:
        raise RuntimeError("; ".join(errors[:3]))
    # dedupe by external_id across instances
    seen, out = set(), []
    for i in items:
        if i["external_id"] not in seen:
            seen.add(i["external_id"])
            out.append(i)
    return out[:30]
