"""v2 addendum §1.3 — Bluesky public feed.

Uses the public AppView search endpoint (no auth) with server-side
keyword queries — the addendum's explicit instruction, since consuming
the raw Firehose and filtering client-side would be wasteful at this
scale.
"""

import json
import urllib.parse

from ..http import fetch_url

QUERIES = ["breaking news", "geopolitics", "earthquake OR wildfire OR flood"]
SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"


def fetch(source: dict) -> list[dict]:
    items, errors = [], []
    for q in QUERIES:
        url = f"{SEARCH_URL}?q={urllib.parse.quote(q)}&limit=15&sort=latest"
        try:
            data = json.loads(fetch_url(url, timeout=20))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{q}: {exc}")
            continue
        for post in data.get("posts", []):
            record = post.get("record", {})
            text = (record.get("text") or "").strip()
            if len(text) < 40:
                continue
            uri = post.get("uri", "")
            handle = (post.get("author") or {}).get("handle", "unknown")
            rkey = uri.rsplit("/", 1)[-1] if "/" in uri else uri
            items.append({
                "title": text[:200],
                "summary": f"@{handle} on Bluesky · {post.get('likeCount', 0)} likes",
                "link": f"https://bsky.app/profile/{handle}/post/{rkey}",
                "published": record.get("createdAt", ""),
                "external_id": uri,
                "who": f"@{handle} (Bluesky)",
            })
    if not items and errors:
        raise RuntimeError("; ".join(errors[:3]))
    seen, out = set(), []
    for i in items:
        if i["external_id"] not in seen:
            seen.add(i["external_id"])
            out.append(i)
    return out[:30]
