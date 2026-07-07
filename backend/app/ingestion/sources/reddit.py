"""Section 4.5 — Reddit ingestion (OAuth client-credentials, free app key)."""

import base64
import json
import time
import urllib.parse

from ...config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from ..http import SourceNotConfigured, fetch_url

SUBREDDITS = "worldnews+geopolitics+economics"

_token: dict = {"value": None, "expires": 0.0}


def _access_token() -> str:
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    creds = base64.b64encode(f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}".encode()).decode()
    body = fetch_url(
        "https://www.reddit.com/api/v1/access_token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={"Authorization": f"Basic {creds}", "User-Agent": REDDIT_USER_AGENT,
                 "Content-Type": "application/x-www-form-urlencoded"})
    data = json.loads(body)
    _token["value"] = data["access_token"]
    _token["expires"] = time.time() + data.get("expires_in", 3600)
    return _token["value"]


def fetch(source: dict) -> list[dict]:
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
        raise SourceNotConfigured("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set")
    token = _access_token()
    body = fetch_url(
        f"https://oauth.reddit.com/r/{SUBREDDITS}/hot?limit=25",
        headers={"Authorization": f"Bearer {token}", "User-Agent": REDDIT_USER_AGENT})
    data = json.loads(body)
    items = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        if post.get("stickied"):
            continue
        items.append({
            "title": post.get("title", ""),
            "summary": (post.get("selftext") or "")[:500]
                       or f"r/{post.get('subreddit')} · {post.get('score', 0)} points",
            "link": "https://www.reddit.com" + post.get("permalink", ""),
            "published": str(post.get("created_utc", "")),
            "external_id": post.get("name") or post.get("id"),
            "who": f"r/{post.get('subreddit', 'reddit')} community",
        })
    return [i for i in items if i["title"]]
