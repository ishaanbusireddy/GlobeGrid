"""v6 §30 — web-search accuracy pipeline.

The Khamenei-era bug (v5 §15) and every 'missing/outdated data' report point
at one root fix: the refresh pipeline gets actual LIVE web search ahead of
its scheduled structured-source syncs, instead of waiting on Wikidata dumps
to catch up. A search API supplies fresh top results for a targeted query
('current head of state of X'); the Groq-first pipeline (§1) synthesizes /
verifies against those results BEFORE the refreshed value is written.

Search provider: accuracy.search_provider (config) — 'brave_free_tier' uses
the Brave Search API (BRAVE_SEARCH_API_KEY, free tier); with no key it falls
back to the keyless DuckDuckGo HTML endpoint (same parser the analyst uses).
Everything degrades cleanly offline: no search → no write, existing values
stay, job retries next cycle.

Also runs ON-DEMAND when the analyst detects its cached synthesis might be
stale for a live question (§29), not only on the scheduled cadence.
"""

import html
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from . import llm
from ..config import cfg, env
from ..db.models import now_iso
from ..db.session import query, write_tx

log = logging.getLogger("accuracy")

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"

_DDG_RESULT = re.compile(
    r'result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?result__snippet"[^>]*>(.*?)</a>',
    re.S)
_TAGS = re.compile(r"<[^>]+>")


def enabled() -> bool:
    try:
        return bool(cfg("accuracy", "web_search_verification_enabled"))
    except KeyError:
        return False


def web_search(question: str, max_results: int = 5) -> list[dict]:
    """Provider-abstracted search: Brave (key) → DuckDuckGo HTML (keyless).
    Returns [{title, snippet, url}]; [] on any failure. Never raises."""
    provider = "ddg"
    try:
        if str(cfg("accuracy", "search_provider")).startswith("brave") \
                and env("BRAVE_SEARCH_API_KEY"):
            provider = "brave"
    except KeyError:
        pass
    try:
        if provider == "brave":
            req = urllib.request.Request(
                BRAVE_URL + "?" + urllib.parse.urlencode({"q": question,
                                                          "count": max_results}),
                headers={"accept": "application/json",
                         "x-subscription-token": env("BRAVE_SEARCH_API_KEY"),
                         "user-agent": llm.USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            return [{"title": r.get("title", ""),
                     "snippet": _TAGS.sub("", r.get("description", "")),
                     "url": r.get("url", "")}
                    for r in (data.get("web", {}).get("results") or [])[:max_results]]
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(question)
        req = urllib.request.Request(url, headers={"user-agent": llm.USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as resp:
            page = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        log.info("web_search_unavailable", extra={"data": {"error": str(exc)[:120]}})
        return []
    out = []
    for m in _DDG_RESULT.finditer(page):
        href, title, snippet = m.group(1), m.group(2), m.group(3)
        title = html.unescape(_TAGS.sub("", title)).strip()
        snippet = html.unescape(_TAGS.sub("", snippet)).strip()
        if "uddg=" in href:
            try:
                href = urllib.parse.unquote(urllib.parse.parse_qs(
                    urllib.parse.urlparse(href).query)["uddg"][0])
            except (KeyError, IndexError):
                pass
        if title and snippet:
            out.append({"title": title, "snippet": snippet, "url": href})
        if len(out) >= max_results:
            break
    return out


def _extract(system: str, payload: dict) -> dict | None:
    text = llm.complete(system, [{"role": "user", "content": json.dumps(payload)}],
                        max_tokens=400, timeout=25)
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        return None
    return out if isinstance(out, dict) else None


LEADERSHIP_PROMPT = """You verify a country's current leadership against fresh web search
results. Return ONLY valid JSON:
{"name": string|null, "role_matches": true|false, "confidence": "high"|"medium"|"low"}
Rules: extract the CURRENT holder's name only if the search results clearly
state it; null when the results are ambiguous or off-topic. Never guess from
memory — the search results are the only evidence."""


def verify_leadership(iso3: str, role: str = "head_of_state") -> dict | None:
    """§30 — 'current head of state of X': search + Groq verification. Writes
    the refreshed value only on a high/medium-confidence extraction that
    differs from the stored one. Returns a result dict for callers (the
    analyst uses it inline) or None when the pipeline can't run."""
    if not enabled() or not llm.available():
        return None
    row = query("SELECT c.name AS country, l.name AS current FROM countries c"
                " LEFT JOIN country_leadership l ON l.country_id = c.id"
                " AND l.role = ? WHERE c.id = ?", (role, iso3))
    if not row:
        return None
    country, current = row[0]["country"], row[0]["current"]
    pretty_role = role.replace("_", " ")
    results = web_search(f"current {pretty_role} of {country}", max_results=5)
    if not results:
        return None
    out = _extract(LEADERSHIP_PROMPT, {
        "country": country, "role": pretty_role,
        "stored_value": current, "search_results": results})
    if not out or not out.get("name"):
        return None
    fresh_name = str(out["name"]).strip()
    changed = bool(current) and fresh_name.lower() not in current.lower() \
        and current.lower() not in fresh_name.lower()
    if out.get("confidence") in ("high", "medium") and (changed or not current):
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO country_leadership (country_id, role, name,"
                " last_refreshed_at) VALUES (?,?,?,?)"
                " ON CONFLICT(country_id, role) DO UPDATE SET"
                " name = excluded.name, last_refreshed_at = excluded.last_refreshed_at",
                (iso3, role, fresh_name, now_iso()))
        log.info("leadership_verified", extra={"data": {
            "country": iso3, "role": role, "was": current, "now": fresh_name}})
    elif out.get("confidence") in ("high", "medium"):
        # value confirmed — stamp the freshness so the staleness flag clears
        with write_tx() as conn:
            conn.execute("UPDATE country_leadership SET last_refreshed_at = ?"
                         " WHERE country_id = ? AND role = ?", (now_iso(), iso3, role))
    return {"country": country, "verified_name": fresh_name,
            "previous": current, "changed": changed,
            "confidence": out.get("confidence"), "sources": results[:3]}


def refresh_stale_leadership(limit: int = 3) -> int:
    """Scheduled job: verify the most-stale leadership rows ahead of (and
    independently of) the Wikidata sync. Bounded per cycle — the free search
    tier is a budget like any other."""
    if not enabled() or not llm.available():
        return 0
    from ..config import cfg as _cfg
    stale_days = float(_cfg("leadership_data", "staleness_warning_days"))
    rows = query(
        "SELECT country_id, role FROM country_leadership"
        " WHERE last_refreshed_at IS NULL"
        " OR last_refreshed_at < datetime('now', ?)"
        " ORDER BY last_refreshed_at IS NOT NULL, last_refreshed_at LIMIT ?",
        (f"-{stale_days} day", limit))
    done = 0
    for r in rows:
        try:
            if verify_leadership(r["country_id"], r["role"]):
                done += 1
        except Exception:  # noqa: BLE001 — per-row isolation
            log.exception("leadership_verify_failed",
                          extra={"data": {"country": r["country_id"]}})
    return done
