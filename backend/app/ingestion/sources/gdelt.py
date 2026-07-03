"""GDELT ingestion (Section 4.2).

Two source rows are expected: type="gdelt" with a DOC 2.0 URL, and a second
type="gdelt" row (or a distinct "gdelt_cloud" convention — see NOTE below)
for GDELT Cloud. Distinguished at fetch time by whether the source URL
targets api.gdeltproject.org (DOC 2.0, fully documented, no key) or a GDELT
Cloud host (docs.gdeltcloud.com describes the product but does not publish
the literal REST path — that endpoint must be confirmed from an active
GDELT Cloud account before enabling that source row).
"""
import httpx

from app.db.models import Source

DOC_API_HOST = "api.gdeltproject.org"

# GDELT DOC 2.0 requires a non-empty query. The manual does not specify search
# terms, so this pulls broad world-event coverage across the categories used
# by events.category (Section 6.3) rather than a single narrow keyword.
DOC_API_QUERY_TERMS = ["geopolitics", "conflict", "disaster", "economy OR markets"]


def _fetch_doc_api(source: Source) -> list[dict]:
    items = []
    with httpx.Client(timeout=30.0) as client:
        for term in DOC_API_QUERY_TERMS:
            resp = client.get(
                source.url,
                params={
                    "query": term,
                    "mode": "artlist",
                    "format": "json",
                    "maxrecords": 75,
                    "timespan": "1h",
                    "sort": "datedesc",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            for article in data.get("articles", []):
                items.append(article)
    return items


def _fetch_cloud(source: Source) -> list[dict]:
    # NOTE: GDELT Cloud's REST contract is not published in the build manual
    # (Section 4.2 only links to docs.gdeltcloud.com). This calls source.url
    # as configured — set it to the exact endpoint from an active GDELT
    # Cloud account before enabling this source row; until then this source
    # should be left disabled (health_status starts "down" is expected).
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(source.url)
        resp.raise_for_status()
        data = resp.json()
    return data if isinstance(data, list) else data.get("results", [])


def fetch(source: Source) -> list[dict]:
    if DOC_API_HOST in source.url:
        return _fetch_doc_api(source)
    return _fetch_cloud(source)
