"""Reddit ingestion (Section 4.5). OAuth app-only (client credentials) flow
via REST, no third-party dependency. source.url carries the target subreddit
listing endpoint, e.g. "https://oauth.reddit.com/r/worldnews/new".
"""
import httpx

from app.config import get_settings
from app.db.models import Source

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_token_cache: dict = {}


def _get_token(client: httpx.Client, settings) -> str:
    cached = _token_cache.get("access_token")
    if cached:
        return cached

    resp = client.post(
        _TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(settings.reddit_client_id, settings.reddit_client_secret),
        headers={"User-Agent": settings.reddit_user_agent},
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _token_cache["access_token"] = token
    return token


def fetch(source: Source) -> list[dict]:
    settings = get_settings()
    if not (settings.reddit_client_id and settings.reddit_client_secret):
        raise RuntimeError("REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET are not configured (see backend/.env.example)")

    with httpx.Client(timeout=30.0) as client:
        token = _get_token(client, settings)
        resp = client.get(
            source.url,
            params={"limit": 50},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": settings.reddit_user_agent,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return [child["data"] for child in data.get("data", {}).get("children", [])]
