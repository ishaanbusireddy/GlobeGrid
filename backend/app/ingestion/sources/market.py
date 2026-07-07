"""Section 4.4 (v1) + v2 addendum §1.4/§7.2 — Alpha Vantage market data.

v2: broader watchlist including crypto (which reacts faster to shocks
than equities — useful correlation-timing signal), spent deliberately
against the 25-requests/day free-tier budget (§7.2): one symbol per poll
on a strict rotation persisted in app_meta, so every symbol gets checked
roughly daily instead of the first few hogging every call. A quote only
becomes an event when the daily move is significant.
"""

import json

from ...config import ALPHAVANTAGE_API_KEY
from ...db.models import meta_get, meta_set
from ..budget import spend
from ..http import SourceNotConfigured, fetch_json

EQUITY_WATCHLIST = ["SPY", "QQQ", "DIA", "IWM", "GLD", "SLV", "USO", "UNG",
                    "UUP", "FXE", "EEM", "TLT", "VIXY", "XLE", "XLF"]
CRYPTO_WATCHLIST = ["BTC", "ETH", "SOL"]
SIGNIFICANT_MOVE_PCT = 1.5
CRYPTO_SIGNIFICANT_MOVE_PCT = 4.0


def _rotation_next() -> tuple[str, str]:
    """Persistent round-robin over equities + crypto (survives restarts)."""
    symbols = [("equity", s) for s in EQUITY_WATCHLIST] + \
              [("crypto", s) for s in CRYPTO_WATCHLIST]
    idx = int(meta_get("market_rotation_idx") or 0) % len(symbols)
    meta_set("market_rotation_idx", str(idx + 1))
    return symbols[idx]


def _equity_quote(symbol: str) -> list[dict]:
    data = fetch_json(
        f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}"
        f"&apikey={ALPHAVANTAGE_API_KEY}")
    if "Note" in data or "Information" in data:
        raise RuntimeError("Alpha Vantage rate limit reached")
    quote = data.get("Global Quote") or {}
    try:
        change_pct = float((quote.get("10. change percent") or "0%").rstrip("%"))
    except ValueError:
        change_pct = 0.0
    if abs(change_pct) < SIGNIFICANT_MOVE_PCT:
        return []
    direction = "rose" if change_pct > 0 else "fell"
    day = quote.get("07. latest trading day", "")
    return [{
        "title": f"{symbol} {direction} {abs(change_pct):.2f}% on the day",
        "summary": f"Price {quote.get('05. price', '?')}, volume {quote.get('06. volume', '?')}.",
        "link": "https://www.alphavantage.co/",
        "published": f"{day}T21:00:00Z" if day else "",
        "external_id": f"{symbol}-{day}",
        "category": "finance",
        "severity": 3 if abs(change_pct) >= 3 else 2,
        "who": symbol,
        "what": f"{direction} {abs(change_pct):.2f} percent",
    }]


def _crypto_quote(symbol: str) -> list[dict]:
    data = fetch_json(
        f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY"
        f"&symbol={symbol}&market=USD&apikey={ALPHAVANTAGE_API_KEY}")
    if "Note" in data or "Information" in data:
        raise RuntimeError("Alpha Vantage rate limit reached")
    series = data.get("Time Series (Digital Currency Daily)") or {}
    days = sorted(series.keys(), reverse=True)[:2]
    if len(days) < 2:
        return []
    def close(d):
        row = series[d]
        return float(row.get("4. close") or row.get("4a. close (USD)") or 0)
    latest, prior = close(days[0]), close(days[1])
    if not prior:
        return []
    change_pct = (latest - prior) / prior * 100
    if abs(change_pct) < CRYPTO_SIGNIFICANT_MOVE_PCT:
        return []
    direction = "rose" if change_pct > 0 else "fell"
    return [{
        "title": f"{symbol} {direction} {abs(change_pct):.1f}% in 24h",
        "summary": f"Close ${latest:,.0f} vs ${prior:,.0f} prior day.",
        "link": "https://www.alphavantage.co/",
        "published": f"{days[0]}T00:00:00Z",
        "external_id": f"{symbol}-{days[0]}",
        "category": "finance",
        "severity": 3 if abs(change_pct) >= 8 else 2,
        "who": symbol,
        "what": f"{direction} {abs(change_pct):.1f} percent in 24 hours",
    }]


def fetch(source: dict) -> list[dict]:
    if not ALPHAVANTAGE_API_KEY:
        raise SourceNotConfigured("ALPHAVANTAGE_API_KEY not set")
    spend("alphavantage")  # §7.2 — skip quietly for the day once exhausted
    kind, symbol = _rotation_next()
    return _crypto_quote(symbol) if kind == "crypto" else _equity_quote(symbol)
