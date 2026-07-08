"""v2 addendum §6.1 — auto-generated daily briefing.

One scheduled job per day (briefing.daily_briefing_hour_utc): pulls the
top N stories of the past 24h by member count + severity contribution and
synthesizes them into a digest with one LLM call (routed through the v5 §18
provider fallback). Same caching discipline as Section 9 — generated once
per day, never regenerated on view. Without a configured AI provider a
structured non-AI digest is stored instead (sources and headlines only,
clearly labeled).
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from . import llm
from ..config import cfg
from ..db.models import new_id, now_iso
from ..db.session import query, query_one, write_tx

log = logging.getLogger("briefing")

BRIEFING_PROMPT = """You are writing a structured daily global-events briefing from correlated
story clusters. Organize it as markdown with short "### " section headers by
THEME and REGION (e.g. "### Conflicts", "### Europe", "### Asia-Pacific",
"### Economy & markets", "### Technology") — only include sections that have
real content. Under each header write 2-5 tight bullet points; each bullet is
one development with its why-it-matters in the same line. Start with a
"### Top line" section of the 2-3 most consequential developments. No walls
of prose, no preamble, no sign-off. Ground every claim in the supplied
stories. Write like a sharp human desk editor briefing a smart reader — plain
and concrete, naming the real actors and stakes. NEVER use hollow analyst-filler
("structural forces", "underlying dynamics", "complex interplay", "geopolitical
landscape", "ripple effects", "at a crossroads"); if a line could describe any
story anywhere, replace it with the specific development."""


# v6.1 — weekly and monthly briefings alongside the daily one. Each period
# gets its own cache key in daily_briefings.briefing_date so no schema change
# is needed: 'YYYY-MM-DD' (day), 'YYYY-Www' (week), 'YYYY-MM' (month).
_PERIOD_HOURS = {"day": 24, "week": 24 * 7, "month": 24 * 30}


def _period_key(period: str, now=None) -> str:
    now = now or datetime.now(timezone.utc)
    if period == "week":
        iso = now.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if period == "month":
        return now.strftime("%Y-%m")
    if period == "market":   # v6.6.2 — dynamic: refresh hourly
        return now.strftime("MKT-%Y-%m-%d-%H")
    return now.strftime("%Y-%m-%d")


# v6.6.2 — market briefing: cover global markets, then TENTATIVELY forecast
# specific moves grounded in the tracked finance/technology/geopolitics stories.
MARKET_PROMPT = """You are a markets strategist writing a briefing for a global-events
terminal. Using ONLY the supplied recent stories (finance, technology and
market-moving geopolitics) plus the global instability score, write markdown:

### Market overview
2-4 bullets on the broad state of global markets implied by these developments
(risk-on/off, sectors in focus, commodities, rates, FX) — reason from the
stories, don't invent index levels you weren't given.

### Tentative forecasts
3-6 bullets, each naming a specific instrument/sector/asset (a named company,
index, commodity or currency that appears in or is clearly implied by the
stories) with a hedged directional call and the story-based rationale. Prefix
each with a confidence word (Low/Medium). These are speculative and MUST read
as tentative — never as advice.

### Watch next
1-3 bullets on upcoming catalysts to watch from the tracked stories.

End with: "_Speculative, story-derived — not financial advice._"
No preamble, no other sections. Ground everything in the supplied stories."""


def _market_stories(limit: int, hours: int = 48) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    rows = query(
        "SELECT DISTINCT s.id, s.headline, s.summary, s.confidence,"
        " (SELECT COUNT(*) FROM story_members m WHERE m.story_id = s.id) AS members"
        " FROM stories s"
        " JOIN story_members m ON m.story_id = s.id"
        " JOIN events e ON e.id = m.event_id"
        " WHERE s.is_synthetic = 0 AND s.last_updated_at >= ?"
        "   AND e.category IN ('finance','technology','geopolitics')"
        " ORDER BY s.last_updated_at DESC LIMIT ?", (cutoff, limit))
    return [dict(r) for r in rows]


def generate_market_briefing() -> dict | None:
    """v6.6.2 — a dynamic markets briefing (global overview + tentative,
    story-grounded forecasts). Cached hourly so it stays fresh but cheap."""
    key = _period_key("market")
    cached = query_one("SELECT * FROM daily_briefings WHERE briefing_date = ?", (key,))
    if cached:
        return dict(cached)
    stories = _market_stories(int(cfg("briefing", "top_n_stories")) * 2)
    latest = query_one("SELECT score FROM instability_scores WHERE is_synthetic = 0"
                       " ORDER BY computed_at DESC LIMIT 1")
    content = None
    if llm.available() and stories:
        payload = {"instability_score": latest["score"] if latest else None,
                   "stories": stories}
        content = llm.complete(MARKET_PROMPT,
                               [{"role": "user", "content": json.dumps(payload)}],
                               max_tokens=1200, timeout=90)
        content = content.strip() if content else None
    if not content:
        lines = ["### Market overview",
                 "_Automated digest (no AI provider — run Ollama or add a key for"
                 " narrative market analysis)._", ""]
        if stories:
            lines.append("### Market-relevant stories")
            for s in stories[:8]:
                lines.append(f"- **{s['headline']}** — {s['members']} linked items")
        else:
            lines.append("- No market-relevant stories in the last 48h yet.")
        lines += ["", "_Speculative, story-derived — not financial advice._"]
        content = "\n".join(lines)
    row = {"id": new_id(), "briefing_date": key, "content": content,
           "generated_at": now_iso()}
    with write_tx() as conn:
        conn.execute("INSERT OR IGNORE INTO daily_briefings"
                     " (id, briefing_date, content, generated_at) VALUES (?,?,?,?)",
                     (row["id"], key, content, row["generated_at"]))
    return row


def _top_stories(top_n: int, hours: int = 24) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    rows = query(
        "SELECT s.id, s.headline, s.summary, s.confidence,"
        " (SELECT COUNT(*) FROM story_members m WHERE m.story_id = s.id) AS members,"
        " (SELECT COALESCE(MAX(e.severity),1) FROM story_members m"
        "   JOIN events e ON e.id = m.event_id WHERE m.story_id = s.id) AS max_severity"
        " FROM stories s WHERE s.is_synthetic = 0 AND s.last_updated_at >= ?"
        " ORDER BY (members * 2 + max_severity) DESC, s.last_updated_at DESC LIMIT ?",
        (cutoff, top_n))
    return [dict(r) for r in rows]


def generate_briefing(briefing_date: str | None = None,
                      period: str = "day") -> dict | None:
    """Generate (or return cached) briefing. period is 'day' | 'week' | 'month';
    each has its own cache key so weekly/monthly digests coexist with daily."""
    hours = _PERIOD_HOURS.get(period, 24)
    briefing_date = briefing_date or _period_key(period)
    cached = query_one("SELECT * FROM daily_briefings WHERE briefing_date = ?",
                       (briefing_date,))
    if cached:
        return dict(cached)
    top_n = int(cfg("briefing", "top_n_stories")) * (3 if period == "month"
                                                     else 2 if period == "week" else 1)
    stories = _top_stories(top_n, hours)
    if not stories:
        return None
    latest = query_one("SELECT score FROM instability_scores WHERE is_synthetic = 0"
                       " ORDER BY computed_at DESC LIMIT 1")
    content = None
    label = {"day": "daily", "week": "weekly", "month": "monthly"}.get(period, "daily")
    if llm.available():
        payload = {"date": briefing_date, "period": label,
                   "instability_score": latest["score"] if latest else None,
                   "stories": stories}
        sys_prompt = BRIEFING_PROMPT.replace("daily", label) if period != "day" \
            else BRIEFING_PROMPT
        content = llm.complete(sys_prompt,
                               [{"role": "user", "content": json.dumps(payload)}],
                               max_tokens=1500, timeout=90)
        if content:
            content = content.strip()
    if not content:
        # v6.6.1 — structured fallback: sectioned + bulleted, not a flat list
        lines = [f"### {label.capitalize()} digest — {briefing_date}",
                 "_Automated digest (no AI provider — run Ollama or add a key"
                 " for narrative briefings)._", "", "### Top developments"]
        for s in stories[:5]:
            lines.append(f"- **{s['headline']}** — {s['members']} linked items,"
                         f" confidence {s['confidence']}")
        rest = stories[5:]
        if rest:
            lines += ["", "### Also tracking"]
            for s in rest:
                lines.append(f"- {s['headline']}")
        content = "\n".join(lines)
    row = {"id": new_id(), "briefing_date": briefing_date, "content": content,
           "generated_at": now_iso()}
    with write_tx() as conn:
        conn.execute("INSERT OR IGNORE INTO daily_briefings"
                     " (id, briefing_date, content, generated_at) VALUES (?,?,?,?)",
                     (row["id"], briefing_date, content, row["generated_at"]))
    log.info("briefing_generated", extra={"data": {"date": briefing_date,
                                                   "stories": len(stories)}})
    return row
