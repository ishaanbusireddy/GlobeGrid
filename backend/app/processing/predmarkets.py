"""v8.16 — live prediction-market tracking (Polymarket + Kalshi).

Public read-only endpoints, no keys required:
  - Polymarket Gamma API: https://gamma-api.polymarket.com/markets
  - Kalshi public markets: https://api.elections.kalshi.com/trade-api/v2/markets

Both are fetched best-effort with short timeouts, filtered to
geopolitics/conflict-relevant markets by keyword, normalized to one shape,
and cached (60s) so the UI can poll freely. In the build sandbox both hosts
are proxy-blocked and this degrades to an empty list with a `live: false`
flag + explanation — the standard honest-degradation pattern. A `q=` filter
narrows to one conflict's markets for the War Mode sentiment strip.
"""

import json
import logging
import threading
import time
import urllib.request

log = logging.getLogger("predmarkets")

_CACHE = {"at": 0.0, "rows": [], "live": False, "error": None}
_LOCK = threading.Lock()
_TTL = 60.0

GEO_KEYWORDS = [
    "war", "ceasefire", "invasion", "strike", "missile", "nuclear", "nato",
    "russia", "ukraine", "china", "taiwan", "iran", "israel", "gaza",
    "hezbollah", "houthi", "north korea", "election", "president", "regime",
    "sanction", "tariff", "coup", "treaty", "peace", "putin", "zelensky",
    "xi ", "khamenei", "opec", "oil",
]


def _get_json(url, timeout=8):
    req = urllib.request.Request(url, headers={
        "User-Agent": "GlobeGrid/8.16 (event-intelligence; contact via repo)",
        "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _geo_relevant(title: str) -> bool:
    t = (title or "").lower()
    return any(k in t for k in GEO_KEYWORDS)


def _fetch_polymarket():
    rows = []
    data = _get_json("https://gamma-api.polymarket.com/markets"
                     "?active=true&closed=false&limit=100"
                     "&order=volume24hr&ascending=false")
    for m in data if isinstance(data, list) else []:
        title = m.get("question") or m.get("title") or ""
        if not _geo_relevant(title):
            continue
        try:
            prices = json.loads(m.get("outcomePrices") or "[]")
            yes = float(prices[0]) if prices else None
        except (ValueError, TypeError, json.JSONDecodeError):
            yes = None
        rows.append({
            "source": "Polymarket", "title": title.strip()[:160],
            "yes_price": yes,
            "volume_24h": float(m.get("volume24hr") or 0),
            "url": ("https://polymarket.com/event/" + (m.get("slug") or ""))
                   if m.get("slug") else "https://polymarket.com",
            "ends": m.get("endDate"),
        })
    return rows


def _fetch_kalshi():
    rows = []
    data = _get_json("https://api.elections.kalshi.com/trade-api/v2/markets"
                     "?limit=100&status=open")
    for m in (data.get("markets") or []):
        title = m.get("title") or ""
        if not _geo_relevant(title):
            continue
        yes_cents = m.get("yes_bid") or m.get("last_price")
        rows.append({
            "source": "Kalshi", "title": title.strip()[:160],
            "yes_price": (yes_cents / 100.0) if isinstance(yes_cents, (int, float)) else None,
            "volume_24h": float(m.get("volume_24h") or m.get("volume") or 0),
            "url": "https://kalshi.com/markets/" + (m.get("ticker") or ""),
            "ends": m.get("close_time"),
        })
    return rows


def markets(q: str | None = None, limit: int = 40) -> dict:
    """Cached, merged, volume-sorted geopolitics markets from both venues.
    `q` (optional) keyword-filters titles (the War Mode per-conflict strip)."""
    now = time.time()
    with _LOCK:
        if now - _CACHE["at"] > _TTL:
            rows, errs = [], []
            for name, fn in (("polymarket", _fetch_polymarket),
                             ("kalshi", _fetch_kalshi)):
                try:
                    rows.extend(fn())
                except Exception as exc:  # noqa: BLE001 — degrade, never raise
                    errs.append(f"{name}: {type(exc).__name__}")
            rows.sort(key=lambda r: r.get("volume_24h") or 0, reverse=True)
            _CACHE.update(at=now, rows=rows, live=bool(rows),
                          error="; ".join(errs) if errs else None)
        rows = list(_CACHE["rows"])
        live, error = _CACHE["live"], _CACHE["error"]
    filtered_note = None
    if q:
        # v8.18 — the War Mode strip passes a conflict's DISTINCTIVE terms (party
        # names + conflict name). A market must hit one of those distinctive
        # terms — generic conflict words ("war", "ceasefire", "conflict"…) are
        # stripped so we don't return every "will there be a war" bet as if it
        # were about THIS conflict (owner: "war-mode odds show random Polymarket
        # bets, not conflict-specific ones").
        generic = {"war", "conflict", "crisis", "dispute", "standoff", "civil",
                   "ceasefire", "tensions", "insurgency", "and", "the", "of",
                   "vs", "allies", "backers", "supporters"}
        ql = [w for w in q.lower().replace("–", " ").replace("-", " ").split()
              if len(w) > 2 and w not in generic]
        if ql:
            rows = [r for r in rows
                    if any(w in r["title"].lower() for w in ql)]
            if not rows:
                filtered_note = ("No conflict-specific prediction markets are "
                                 "open right now for this conflict. Only markets "
                                 "naming its parties are shown — never unrelated "
                                 "geopolitics bets.")
        else:
            rows = []
            filtered_note = ("No distinctive market terms for this conflict — "
                             "showing none rather than unrelated bets.")
    return {"live": live, "error": error, "markets": rows[:limit],
            "note": (filtered_note if filtered_note else
                     "Real-money prediction-market odds (Polymarket + Kalshi "
                     "public APIs), refreshed ≤60s. Prices are crowd "
                     "probabilities, not facts."
                     if live else
                     "Prediction-market feeds unreachable from this network "
                     "right now — the window fills the moment "
                     "gamma-api.polymarket.com / api.elections.kalshi.com "
                     "are reachable. No synthetic odds are ever shown.")}
