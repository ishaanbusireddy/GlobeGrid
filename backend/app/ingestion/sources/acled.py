"""v2 addendum §1.1 — ACLED-style coded conflict data.

Flagged OPEN in the addendum: ACLED's free tier requires registered
researcher/org approval, a real approval step unlike the fully-open
sources. The adapter is ready — set ACLED_KEY and ACLED_EMAIL in .env
once access is granted; until then the source shows degraded with a
clear reason, never blocking anything else.
"""

import json
import urllib.parse
from datetime import datetime, timedelta, timezone

from ...config import env
from ..http import SourceNotConfigured, fetch_url

SEVERITY_BY_EVENT_TYPE = {
    "Battles": 4, "Explosions/Remote violence": 4,
    "Violence against civilians": 4, "Riots": 3, "Protests": 2,
    "Strategic developments": 2,
}


def fetch(source: dict) -> list[dict]:
    key, email = env("ACLED_KEY"), env("ACLED_EMAIL")
    if not (key and email):
        raise SourceNotConfigured(
            "ACLED_KEY / ACLED_EMAIL not set (registered-access tier, approval pending)")
    since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    params = urllib.parse.urlencode({
        "key": key, "email": email, "limit": 50,
        "event_date": since, "event_date_where": ">=",
    })
    data = json.loads(fetch_url(f"https://api.acleddata.com/acled/read?{params}",
                                timeout=45))
    items = []
    for row in data.get("data", []):
        etype = row.get("event_type", "")
        items.append({
            "title": f"{etype}: {row.get('sub_event_type', '')} in "
                     f"{row.get('location', row.get('country', ''))}"[:280],
            "summary": (row.get("notes") or "")[:500],
            "link": "https://acleddata.com/data-export-tool/",
            "published": f"{row.get('event_date', '')}T12:00:00Z",
            "external_id": row.get("event_id_cnty") or row.get("data_id"),
            "lat": float(row["latitude"]) if row.get("latitude") else None,
            "lon": float(row["longitude"]) if row.get("longitude") else None,
            "location_name": row.get("location") or row.get("country"),
            "category": "conflict",
            "severity": SEVERITY_BY_EVENT_TYPE.get(etype, 3),
            "who": "; ".join(filter(None, [row.get("actor1"), row.get("actor2")]))
                   or "unattributed",
            "what": f"{etype.lower()} — {row.get('sub_event_type', '').lower()}",
        })
    return items
