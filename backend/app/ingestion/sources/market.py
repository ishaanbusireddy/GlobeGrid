"""Alpha Vantage market data ingestion (Section 4.4). Free tier, key required
(ALPHAVANTAGE_API_KEY, Section 7.1); rate limits apply so responses are
cached only by virtue of the configured poll interval, not fetched on demand.

source.url carries the function/symbol query (e.g.
"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=SPY&interval=60min")
and this module appends the API key at fetch time so the key never sits in
the sources table.
"""
import httpx

from app.config import get_settings
from app.db.models import Source


def fetch(source: Source) -> list[dict]:
    settings = get_settings()
    if not settings.alphavantage_api_key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY is not configured (see backend/.env.example)")

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(source.url, params={"apikey": settings.alphavantage_api_key})
        resp.raise_for_status()
        data = resp.json()

    if "Note" in data or "Information" in data:
        # Rate-limit / throttle notice from Alpha Vantage — surfaced as a
        # failure so common.run_ingestion_job() applies the backoff policy.
        raise RuntimeError(data.get("Note") or data.get("Information"))

    return [data]
