"""v3 §24 / v5.2 — LLM-powered conversational analyst panel.

A smart geopolitical assistant grounded FIRST in GlobeGrid's own data —
the entity layer (§13-23), the correlated story fact chain, and the causal
narratives / instability index the pipeline generates — and augmented with
live web search when a question reaches past what the fact chain covers.
Every tracked claim cites the source story it came from; web-sourced facts
are labeled as such, never blended in silently.

v5.2 changes over the original §24 build:
- Routes through the processing.llm provider abstraction (Groq by default,
  Claude optional) instead of a hardcoded Anthropic call — so the panel
  actually works on a free key.
- Real multi-turn conversation: prior turns of the session are replayed to
  the model, so follow-ups ('and what about its neighbours?') keep context.
- Handles conversational / meta input naturally ('hi', 'what can you do?')
  instead of dumping unrelated stories at it.
- Pulls each retrieved story's causal narrative + confidence into the
  context, so the analyst can reason about cause and effect, not just
  headlines.
- Optional keyless web search (DuckDuckGo) for questions the tracked data
  doesn't cover; degrades cleanly when offline.

Forecast questions still route to the §7 tracked forecasting pathway rather
than improvising a prediction inline. Without any AI provider configured the
panel falls back to a cited retrieval-only summary.
"""

import concurrent.futures as cf
import html
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from ..config import cfg
from ..db.models import meta_get, new_id, now_iso
from ..db.session import query, query_one, write_tx
from ..processing import llm
from .router import route

log = logging.getLogger("analyst")

# v6.3.2 — a hard wall-clock deadline for potentially-hanging I/O (web search,
# the LLM call). Nested library timeouts (urllib's `timeout=`) don't always
# cover every hang scenario — a DNS resolution stall on some Windows/firewall/
# antivirus setups can block well past the declared socket timeout, which is
# exactly the kind of thing that turned "the analyst took too long" from a
# 1-in-100 fluke into a reproducible failure. Running the call in a worker
# thread and giving up on the FUTURE after N seconds guarantees the request
# handler returns to the client well under ITS OWN abort ceiling, no matter
# what's actually stuck underneath.
_IO_POOL = cf.ThreadPoolExecutor(max_workers=6, thread_name_prefix="analyst-io")


def _bounded(fn, timeout_s: float, default, label: str):
    """Run fn() with a hard deadline; on timeout OR any failure, return
    `default` instead of blocking the caller. Never raises — for optional,
    best-effort calls (web search) that should always degrade quietly."""
    fut = _IO_POOL.submit(fn)
    try:
        return fut.result(timeout=timeout_s)
    except cf.TimeoutError:
        log.warning("analyst_deadline_exceeded",
                    extra={"data": {"call": label, "timeout_s": timeout_s}})
        return default
    except Exception as exc:  # noqa: BLE001 — any failure = no result, never blocks
        log.warning("analyst_bounded_call_failed",
                    extra={"data": {"call": label, "error": str(exc)[:160]}})
        return default


def _bounded_or_raise(fn, timeout_s: float, timeout_message: str, label: str):
    """Run fn() with a hard deadline; on TIMEOUT ONLY, raise ProviderError with
    a clear message. Any other exception from fn() (e.g. ProviderError with the
    real provider error) propagates UNCHANGED — this must never swallow the
    actual reason a call failed, only guard against it hanging forever."""
    fut = _IO_POOL.submit(fn)
    try:
        return fut.result(timeout=timeout_s)
    except cf.TimeoutError:
        log.warning("analyst_deadline_exceeded",
                    extra={"data": {"call": label, "timeout_s": timeout_s}})
        raise ProviderError(timeout_message)


class ProviderError(Exception):
    """v6.3.1 — the LLM provider was configured but the call failed (bad key,
    decommissioned model, rate limit, timeout). Carries the provider's real
    message so the analyst can tell the user WHAT went wrong instead of hiding
    every failure behind a generic 'add a key' fallback."""

ANSWER_PROMPT = """You are GlobeGrid's analyst — a sharp, conversational geopolitical
intelligence assistant embedded in a live global-events platform. You are
talking with a user in an ongoing chat.

You are given, for each question, a CONTEXT BUNDLE containing:
- GlobeGrid's own tracked data: matching entities (countries, conflicts,
  alliances, non-state actors), correlated story clusters with their
  summaries and AI-generated causal narratives, and the current global
  instability index.
- Optional WEB SEARCH results, when the tracked data doesn't fully cover
  the question.

How to answer (v6 §29 quality bar):
- Be genuinely helpful and natural. If the user just greets you or asks what
  you can do, respond conversationally and briefly explain that you can
  answer questions about live global events, conflicts, countries and the
  causal stories GlobeGrid is tracking. Do NOT dump unrelated stories at a
  greeting.
- VOICE (v7.4.1): sound like the sharpest geopolitics expert the user knows,
  talking TO them — plain, concrete, specific, a little opinionated. Name the
  real players, places, numbers and moves. NEVER use hollow analyst-filler:
  "the structural forces at work", "underlying dynamics", "a complex
  interplay", "geopolitical landscape", "delicate balance", "ripple effects",
  "at a crossroads", "it is important to note", "navigating tensions". If a
  sentence could describe any country or any conflict, delete it and write the
  specific truth instead. Detailed does NOT mean vague or bureaucratic.
- STRUCTURE (v6.6.4): open with a one-sentence takeaway, then organize the
  answer under short markdown "### " section headers (e.g. "### What's
  happening", "### Why it matters", "### Key players", "### What to watch")
  with 4-7 concise BULLETS each (prefer bullets over paragraphs — the user
  wants detailed, scannable, bullet-heavy answers). Leave a blank line
  between sections. Aim for a thorough, genuinely informative answer
  (roughly 250-450 words), then put any even-fuller prose analysis in the
  separate "deep_dive" field — the UI offers it as an expandable 'read more'.
  A pure greeting can skip all structure and just reply naturally.
- NEVER print raw internal identifiers (story ids, UUIDs, hashes) in the
  answer text — refer to events by their headline or a short natural
  description. Machine-readable ids belong ONLY in "cited_story_ids", which
  the UI renders as clickable event chips.
- The bundle may include a "screen" object describing what panel/page the
  user currently has open. screen.top_panel is AUTHORITATIVE for "this"/
  "here"/"what am I looking at": it is the panel visible RIGHT NOW. If it
  conflicts with an older focused_entity, ALWAYS prefer screen.top_panel —
  never comment on a previously-opened panel the user has moved past.
- The bundle may include "world_knowledge": a curated intelligence dossier
  (history, actors, stakes, status through early 2026) about the entity in
  question or on screen, and "historical_eras": a 1945→present arc of how the
  modern world was built (postwar/Cold-War order → unipolar moment →
  multipolar disorder). Treat both as reliable grounding and WEAVE them into
  your answer freely — combined with your own general knowledge of history,
  cultures, religions, geopolitics, economics and markets. Assume the user
  may know NOTHING about the topic: define actors and terms on first
  mention, give the one-paragraph origin story (reaching back decades where it
  helps) before the latest twist, and make the answer self-contained for a
  total newcomer while staying sharp for experts.
- Lead with GlobeGrid's tracked data when it's relevant — reference the
  causal narratives and cite the story ids you used. When you rely on a web
  search result instead, say so explicitly ('per a web search, ...') so the
  user knows it isn't from GlobeGrid's tracked fact chain. A
  "live_verification" object in the bundle is a fresh web-checked fact —
  prefer it over anything older.
- For REGION questions the bundle carries the region's countries, conflicts,
  story threads and recent stories: name the concrete linked developments
  (wars, expansions, armament) in your bullets — never a one-line summary.
- You MAY use web results and general knowledge to give a useful answer, but
  never present a guess as a tracked fact, and never state certainty the
  evidence doesn't support. Prefer 'as of the most recent tracked story...'
  framing for time-sensitive claims.
- If the question asks for a prediction ('will X happen?'), don't improvise
  one — note that GlobeGrid routes forecasts through its tracked, graded
  forecasting pathway.

Return ONLY valid JSON (no prose outside it):
{
  "answer": string,                 // bulleted markdown reply
  "deep_dive": string|null,         // optional fuller prose analysis
  "confidence": "high" | "medium" | "low",
  "cited_story_ids": string[],      // tracked story ids you actually used (may be empty)
  "used_web": boolean               // true if you leaned on a web result
}"""

FORECAST_WORDS = re.compile(r"\b(will|going to|predict|forecast|escalate|likely to"
                            r"|what happens next|outlook)\b", re.I)

# conversational / meta input that must NOT be treated as a data query —
# a greeting should get a greeting, not three unrelated story citations
_SMALLTALK = re.compile(
    r"^\s*(hi|hey|hello|yo|sup|howdy|good (morning|afternoon|evening)|"
    r"how are you|how's it going|what'?s up|thanks|thank you|ok|okay|cool|"
    r"who are you|what are you|what can you do|help|test)\b[\s!?.]*", re.I)


# v4 §16.3 — generic trailing words carry no identity: 'Israel–Palestine
# Conflict' should match on its parties, not require 2-of-3 tokens
# including 'conflict'
GENERIC_CONFLICT_WORDS = {"war", "conflict", "crisis", "dispute", "insurgency",
                          "civil", "movement"}


def _leader_match(question: str) -> str | None:
    """v6.6.7 — if the question names a tracked leader, return that leader's
    name so the analyst can navigate to their profile. Matches the full name,
    or a distinctive surname (>=5 chars) as a whole word to avoid false hits."""
    ql = " " + (question or "").lower() + " "
    best = None
    for r in query("SELECT DISTINCT name FROM country_leadership WHERE name IS NOT NULL"):
        nm = (r["name"] or "").strip()
        if not nm:
            continue
        low = nm.lower()
        if low in ql:
            return nm
        parts = [p for p in re.split(r"[^\w]+", low) if p]
        surname = parts[-1] if parts else ""
        if len(surname) >= 5 and re.search(r"\b" + re.escape(surname) + r"\b", ql):
            best = best or nm
    return best


# v8.13 — the analyst can drive the whole UI, not just open entity pages.
_MAPMODE_KEYWORDS = {
    "hdi": "hdi", "human development": "hdi", "nuclear": "nuclear_arsenal",
    "gdp per capita": "gdp_per_capita", "gdp": "gdp", "population density": "population_density",
    "population": "population", "religious sect": "religious_sect", "sect": "religious_sect",
    "religion": "religion", "dialect": "dialect", "language": "language",
    "climate": "climate", "altitude": "altitude", "elevation": "altitude",
}
_UI_ACTIONS = {
    "settings": "settings", "what if": "whatif", "what-if": "whatif",
    "counterfactual": "whatif",
    "united nations": "un", "un panel": "un", "conflicts": "conflicts",
    "sources": "sources", "briefing": "briefing", "stories": "stories",
    "hotspots": "hotspots", "all events": "events", "every event": "events",
    "browse events": "events", "all the events": "events",
}


def _mapmode_match(lowered: str) -> dict | None:
    """"show the religion map", "switch to population density", "climate mode"."""
    if not any(w in lowered for w in ("map", "mode", "colou", "color", "choropleth", "show", "shade")):
        return None
    # longest keyword first so "gdp per capita" beats "gdp", "religious sect" beats "religion"
    for kw in sorted(_MAPMODE_KEYWORDS, key=len, reverse=True):
        if kw in lowered:
            mid = _MAPMODE_KEYWORDS[kw]
            return {"type": "mapmode", "id": mid, "name": kw, "context": {"mode": mid}}
    return None


def _ui_match(lowered: str) -> dict | None:
    """"open settings", "open the what-if engine", "show the UN panel"."""
    if not any(w in lowered for w in ("open", "show", "go to", "take me", "bring up")):
        return None
    for kw in sorted(_UI_ACTIONS, key=len, reverse=True):
        if kw in lowered:
            act = _UI_ACTIONS[kw]
            return {"type": "ui", "id": act, "name": kw, "context": {"action": act}}
    return None


def _candidate_phrases(question: str) -> list:
    """Capitalized multi/single-word phrases from the ORIGINAL question — the
    proper nouns a division/city name would appear as."""
    return re.findall(r"\b([A-Z][\w’'-]+(?:\s+[A-Z][\w’'-]+){0,3})", question or "")


def _admin_unit_match(question: str) -> dict | None:
    """A province/state/district/… named in the question → its unit page."""
    for cand in _candidate_phrases(question):
        row = query_one(
            "SELECT admin_uid, name, country_id, adm_level FROM administrative_units"
            " WHERE name = ? COLLATE NOCASE LIMIT 1", (cand,))
        if row:
            return {"type": "admin", "id": row["admin_uid"], "name": row["name"],
                    "context": dict(row)}
    return None


def _city_match(question: str) -> dict | None:
    """A gazetteer city named in the question → its city page (largest match)."""
    for cand in _candidate_phrases(question):
        row = query_one(
            "SELECT id, name, country_code, population FROM gazetteer_places"
            " WHERE name = ? COLLATE NOCASE ORDER BY population DESC LIMIT 1", (cand,))
        if row:
            return {"type": "city", "id": row["id"], "name": row["name"],
                    "context": dict(row)}
    return None


def _entity_match(question: str) -> dict | None:
    """Path 1 — structured entity match against the §13-23 layer."""
    lowered = question.lower()
    strip_generic = bool(cfg("analyst_panel_fixes", "conflict_token_strip_generic_words"))
    party_aliases = bool(cfg("analyst_panel_fixes", "conflict_alias_individual_parties"))
    for r in query("SELECT id, name, summary, status, region FROM conflicts"):
        tokens = [t for t in re.split(r"[^\w]+", r["name"].lower()) if len(t) > 3]
        if strip_generic:
            tokens = [t for t in tokens if t not in GENERIC_CONFLICT_WORDS]
        hit = r["name"].lower() in lowered or (
            tokens and sum(1 for t in tokens if t in lowered) >= max(1, len(tokens) - 1))
        if not hit and party_aliases:
            # each side of a multi-party conflict name is its own alias, so
            # 'Palestine' alone reaches Israel–Palestine Conflict (§16.3)
            sides = [s.strip().lower() for s in
                     re.split(r"[–—-]| vs ", r["name"].split(" (")[0]) if len(s.strip()) > 3]
            sides = [re.sub(r"\b(" + "|".join(GENERIC_CONFLICT_WORDS) + r")\b", "", s).strip()
                     for s in sides]
            hit = any(s and re.search(r"\b" + re.escape(s) + r"\b", lowered) for s in sides)
        if hit:
            return {"type": "conflict", "id": r["id"], "name": r["name"],
                    "context": dict(r)}
    for r in query("SELECT id, name FROM countries"):
        if r["name"].lower() in lowered:
            profile = query_one(
                "SELECT c.name, c.capital, c.region, c.government_type,"
                " a.geopolitical_agenda, a.economic_agenda, a.stance_summary"
                " FROM countries c LEFT JOIN country_agenda_synthesis a"
                " ON a.country_id = c.id WHERE c.id = ?", (r["id"],))
            leaders = query("SELECT role, name FROM country_leadership"
                            " WHERE country_id = ?", (r["id"],))
            ctx = dict(profile) if profile else {"name": r["name"]}
            ctx["leadership"] = [dict(x) for x in leaders]
            return {"type": "country", "id": r["id"], "name": r["name"], "context": ctx}
    for r in query("SELECT id, name, description_synthesis, actor_type, primary_region"
                   " FROM non_state_actors"):
        if r["name"].lower() in lowered or \
                r["name"].split(" (")[0].lower() in lowered:
            return {"type": "non_state_actor", "id": r["id"], "name": r["name"],
                    "context": dict(r)}
    for r in query("SELECT id, name, type, description FROM alliances"):
        if r["name"].lower() in lowered:
            return {"type": "alliance", "id": r["id"], "name": r["name"],
                    "context": dict(r)}
    for r in query("SELECT id, name, lat, lon, category, description"
                   " FROM marked_locations WHERE category != 'capital'"):
        if r["name"].split(" (")[0].lower() in lowered:
            return {"type": "location", "id": r["id"], "name": r["name"],
                    "context": dict(r)}
    # v8.13 — the analyst opens ANYTHING (owner: "the analyst should be able to
    # open any … districts, divisions, cities, map modes, menus"). A map-mode /
    # UI-action command is checked first (they're explicit "show the X map" /
    # "open X" instructions), then administrative divisions and cities by name.
    mm = _mapmode_match(lowered)
    if mm:
        return mm
    ui = _ui_match(lowered)
    if ui:
        return ui
    admin = _admin_unit_match(question)
    if admin:
        return admin
    city = _city_match(question)
    if city:
        return city
    # v5 §20 — region match: 'what's happening in Eastern Europe?' resolves to
    # a region (distinct countries.region values), opening a region summary
    # page rather than failing to match or defaulting to a single country.
    region = _match_region(lowered)
    if region:
        return {"type": "region", "id": region, "name": region,
                "context": {"region": region}}
    return None


# named regions the analyst recognizes — v6 §28: values are UN M49
# sub-region names (what countries.region now carries) or m49.REGION_GROUPS
# keys (colloquial groupings the region route expands itself)
_REGION_ALIASES = {
    "eastern europe": "Eastern Europe", "western europe": "Western Europe",
    "southern europe": "Southern Europe", "northern europe": "Northern Europe",
    "central europe": "Eastern Europe", "europe": "Europe",
    "middle east": "Middle East", "north africa": "Northern Africa",
    "northern africa": "Northern Africa",
    "west africa": "Western Africa", "western africa": "Western Africa",
    "east africa": "Eastern Africa", "eastern africa": "Eastern Africa",
    "central africa": "Middle Africa", "southern africa": "Southern Africa",
    "africa": "Africa", "sub-saharan africa": "Sub-Saharan Africa",
    "south asia": "Southern Asia", "southern asia": "Southern Asia",
    "east asia": "Eastern Asia", "eastern asia": "Eastern Asia",
    "southeast asia": "South-Eastern Asia", "south-east asia": "South-Eastern Asia",
    "central asia": "Central Asia", "western asia": "Western Asia",
    "caucasus": "Western Asia",
    "south america": "South America", "north america": "Northern America",
    "northern america": "Northern America", "latin america": "Latin America",
    "central america": "Central America", "caribbean": "Caribbean",
    "oceania": "Oceania", "balkans": "Balkans", "asia": "Asia",
    "americas": "Americas",
}


def _match_region(lowered: str) -> str | None:
    # longest alias first so 'eastern europe' wins over 'europe'
    for alias in sorted(_REGION_ALIASES, key=len, reverse=True):
        if alias in lowered:
            return _REGION_ALIASES[alias]
    return None


def _story_context(row) -> dict:
    """One retrieved story, cleaned and enriched with its causal narrative +
    confidence so the analyst can reason about cause/effect, not just read a
    headline. Headlines/summaries are normalized (v4 §11 link-strip) so the
    model never sees tracker-URL / hashtag junk from raw wire copy."""
    from ..processing.textquality import normalize_headline, normalize_summary
    out = {"id": row["id"],
           "headline": normalize_headline(row["headline"] or ""),
           "summary": normalize_summary(row["summary"] or ""),
           "last_updated_at": row["last_updated_at"]}
    if bool(cfg("analyst_panel", "include_causal_narrative_in_context")):
        try:
            narr = row["causal_narrative"]
        except (KeyError, IndexError):
            narr = None
        if narr:
            try:
                out["causal_narrative"] = json.loads(narr)
            except (json.JSONDecodeError, TypeError):
                pass
        try:
            if row["confidence"]:
                out["confidence"] = row["confidence"]
        except (KeyError, IndexError):
            pass
    return out


def _freeform_retrieval(question: str, entity_name: str | None) -> list[dict]:
    """Path 2 — FTS5 + embedding similarity over recent stories."""
    limit = int(cfg("analyst_panel", "max_context_stories_per_query"))
    lookback = int(cfg("analyst_panel", "freeform_retrieval_lookback_days"))
    results, seen = [], set()

    def add(row):
        if row["id"] not in seen:
            seen.add(row["id"])
            results.append(_story_context(row))

    if meta_get("fts_enabled") == "1":
        terms = [t for t in re.split(r"[^\w]+", question) if len(t) > 3][:6]
        if entity_name:
            terms = [entity_name.split(" (")[0]] + terms
        if terms:
            fts = " OR ".join(f'"{t}"' for t in terms)
            try:
                for row in query(
                        "SELECT s.id, s.headline, s.summary, s.last_updated_at,"
                        " s.causal_narrative, s.confidence"
                        " FROM fts_stories f JOIN stories s ON s.id = f.id"
                        " WHERE fts_stories MATCH ? AND s.is_synthetic = 0"
                        " AND s.last_updated_at >= datetime('now', ?)"
                        " ORDER BY rank LIMIT ?", (fts, f"-{lookback} day", limit)):
                    add(row)
            except Exception:  # noqa: BLE001 — malformed FTS input
                pass

    # v6.3 — query-time embedding is OFF by default (embedding_retrieval_enabled).
    # Re-encoding recent headlines through sentence-transformers on every
    # question was the analyst-timeout root cause: 10-30s of blocking CPU work
    # before the LLM call. FTS5 already grounds the answer; when it comes up
    # short we top up with the most RECENT stories (a cheap indexed query), so
    # the model always has fresh context without paying the embedding tax.
    embed_on = False
    try:
        embed_on = bool(cfg("analyst_panel", "embedding_retrieval_enabled"))
    except (KeyError, TypeError):
        embed_on = False

    if embed_on and len(results) < limit:
        from ..processing.embed import embed_text, cosine
        qvec = embed_text(question)
        try:
            scan_limit = int(cfg("analyst_panel", "embedding_scan_limit"))
        except (KeyError, TypeError):
            scan_limit = 40
        recent = query(
            "SELECT id, headline, summary, last_updated_at, causal_narrative, confidence"
            " FROM stories WHERE is_synthetic = 0 AND last_updated_at >= datetime('now', ?)"
            " ORDER BY last_updated_at DESC LIMIT ?", (f"-{lookback} day", scan_limit))
        scored = sorted(
            ((cosine(qvec, embed_text(r["headline"])), r) for r in recent),
            key=lambda x: -x[0])
        for sim, row in scored:
            if sim < 0.25 or len(results) >= limit:
                break
            add(row)
    elif len(results) < limit:
        # fast recency top-up (no embedding) — keeps the bundle fresh cheaply
        for row in query(
                "SELECT id, headline, summary, last_updated_at, causal_narrative, confidence"
                " FROM stories WHERE is_synthetic = 0"
                " AND last_updated_at >= datetime('now', ?)"
                " ORDER BY last_updated_at DESC LIMIT ?", (f"-{lookback} day", limit)):
            if len(results) >= limit:
                break
            add(row)
    return results[:limit]


def _web_search(question: str) -> list[dict]:
    """v6 §30 — delegates to the shared accuracy pipeline's provider-
    abstracted search (Brave with a key, keyless DuckDuckGo otherwise).
    Best-effort: [] on any failure, the analyst relies on tracked data."""
    if not bool(cfg("analyst_panel", "web_search_enabled")):
        return []
    max_results = int(cfg("analyst_panel", "web_search_max_results"))
    if max_results <= 0:
        return []
    from ..processing.accuracy import web_search
    out = web_search(question, max_results=max_results)
    if out:
        log.info("analyst_web_search", extra={"data": {"results": len(out)}})
    return out


def _region_deep_dive(region: str) -> dict:
    """v6 §29 — a region answer must link real content: the region's
    countries AND its conflicts AND its story threads AND recent stories,
    not a one-line summary. Reuses the §28 M49 region resolution."""
    from .routes_geo import region_summary
    status, data = region_summary({"region": region}, {}, None)
    if status != 200:
        return {}
    country_names = [c["name"] for c in data.get("countries", [])]
    threads = []
    if country_names:
        like = " OR ".join(["s.headline LIKE ?"] * len(country_names))
        args = [f"%{n}%" for n in country_names]
        threads = [dict(r) for r in query(
            "SELECT DISTINCT t.id, t.name, t.description FROM story_threads t"
            " JOIN story_thread_members tm ON tm.thread_id = t.id"
            f" JOIN stories s ON s.id = tm.story_id WHERE {like} LIMIT 6", args)]
    return {"countries": data.get("countries", []),
            "conflicts": data.get("conflicts", []),
            "threads": threads,
            "recent_stories": data.get("recent_stories", [])}


def _live_verification(entity: dict | None) -> dict | None:
    """v6 §29/§30 — when the matched entity is a country whose leadership
    row is stale, run the on-demand search-verify pass so the answer isn't
    built on cached synthesis that may have expired. Bounded + best-effort."""
    if not entity or entity.get("type") != "country":
        return None
    from ..config import cfg as _cfg
    stale_days = float(_cfg("leadership_data", "staleness_warning_days"))
    stale = query_one(
        "SELECT 1 FROM country_leadership WHERE country_id = ?"
        " AND role = 'head_of_state' AND (last_refreshed_at IS NULL"
        " OR last_refreshed_at < datetime('now', ?))",
        (entity["id"], f"-{stale_days} day"))
    if not stale:
        return None
    try:
        from ..processing.accuracy import verify_leadership
        return verify_leadership(entity["id"])
    except Exception:  # noqa: BLE001 — verification is augmentation, never a blocker
        log.exception("analyst_live_verify_failed")
        return None


def _prior_turns(session_id: str) -> list[dict]:
    """Recent conversation turns, oldest-first, as chat messages — this is
    what makes the analyst hold a real multi-turn conversation instead of
    treating every question in isolation."""
    n = int(cfg("analyst_panel", "conversation_history_turns"))
    if n <= 0:
        return []
    rows = query(
        "SELECT role, content FROM analyst_messages WHERE session_id = ?"
        " ORDER BY created_at DESC LIMIT ?", (session_id, n * 2))
    turns = [{"role": r["role"] if r["role"] in ("user", "assistant") else "user",
              "content": r["content"]} for r in reversed(rows)]
    return turns


def _language_system(lang: str | None) -> str:
    """v8.16.1 — when the user's UI is in a non-English language, tell the model
    to compose its WHOLE answer natively in that language (owner: "analyst in
    the mode of a different language should be preset to respond … in that
    language"). Native generation is one call — faster and far more natural than
    generating English then machine-translating it after the fact. The JSON
    envelope stays English (keys + enum values the code parses); only the human
    prose in `answer`/`deep_dive` switches language."""
    if not lang or lang == "en":
        return ANSWER_PROMPT
    from ..i18n_names import LANGUAGE_NAMES
    name = LANGUAGE_NAMES.get(lang, lang)
    return ANSWER_PROMPT + (
        f"\n\nLANGUAGE (v8.16.1): the user's interface language is {name}. Write the "
        f"ENTIRE human-readable prose — the \"answer\" and \"deep_dive\" string values, "
        f"including the \"### \" section headers — in fluent, natural {name}. The user "
        f"may also write to you in {name}; understand it and reply in {name}. Keep the "
        f"JSON structure itself and the \"confidence\" enum in English; translate only "
        f"the prose the user reads. Never mix English sentences into a {name} answer.")


def _answer_with_llm(question: str, bundle: dict, session_id: str, lang: str = "en"):
    """Route the analyst turn through the provider abstraction (Groq/Claude/…)
    with the conversation history for real multi-turn context."""
    system_prompt = _language_system(lang)
    messages = _prior_turns(session_id)
    messages.append({"role": "user", "content": json.dumps(
        {"question": question, "context_bundle": bundle})})
    # v6.3 — the answer is ONE Groq call, bounded by config so it can never
    # approach the client's abort. Token budget + timeout are tunable
    # (analyst_panel.answer_max_tokens / .answer_timeout_seconds).
    try:
        max_tokens = int(cfg("analyst_panel", "answer_max_tokens"))
    except (KeyError, TypeError):
        max_tokens = 650
    try:
        timeout = int(float(cfg("analyst_panel", "answer_timeout_seconds")))
    except (KeyError, TypeError):
        timeout = 24
    # v6.3.1 — json_mode=True makes Groq/Gemini/Ollama return a guaranteed valid
    # JSON object, so a chatty model can no longer produce output we have to
    # throw away. If a provider still returns prose (older model, Claude), we
    # SALVAGE it as the answer instead of failing the whole turn.
    # v6.4.2 — interactive: a user is waiting, so a short Groq rate-limit
    # window is waited out + retried instead of failing the turn
    text = llm.complete(system_prompt, messages, max_tokens=max_tokens,
                        timeout=timeout, json_mode=True, interactive=True)
    if text is None:
        # some models/providers reject response_format — retry once in plain
        # mode (the salvage path below handles non-JSON prose either way).
        # v6.3.2 — the retry uses a SHORTER budget than the first attempt, not
        # the same one again: a naive "retry with the full timeout" doubles the
        # worst-case wait (up to 2x answer_timeout_seconds), which is exactly
        # the kind of self-inflicted latency that can push a request past the
        # client's 60s abort. Bounding the retry keeps the TOTAL worst case
        # close to the original single-call ceiling.
        retry_timeout = max(8, timeout // 2)
        text = llm.complete(system_prompt, messages, max_tokens=max_tokens,
                            timeout=retry_timeout, json_mode=False,
                            interactive=True)
    if text is None:
        raise ProviderError(llm.last_error() or "no AI provider available")
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    # smaller models sometimes wrap JSON in stray prose — grab the object
    inner = text
    if not inner.startswith("{"):
        brace = inner.find("{")
        if brace != -1:
            inner = inner[brace:inner.rfind("}") + 1]
    try:
        out = json.loads(inner)
    except json.JSONDecodeError:
        # SALVAGE: the model answered, just not as JSON — use its prose so the
        # user gets a real reply rather than an error/empty fallback.
        cleaned = re.sub(r"^\s*\{?\s*[\"']?answer[\"']?\s*:\s*", "", text)
        return {"answer": cleaned.strip() or text, "deep_dive": None,
                "confidence": "medium", "cited_story_ids": [], "used_web": False}
    if not isinstance(out, dict) or not isinstance(out.get("answer"), str):
        raise ValueError("malformed analyst answer")
    if out.get("confidence") not in ("high", "medium", "low"):
        out["confidence"] = "low"
    return out


def _session(session_id: str | None) -> str:
    if session_id and query_one("SELECT 1 FROM analyst_sessions WHERE id = ?",
                                (session_id,)):
        return session_id
    sid = new_id()
    with write_tx() as conn:
        conn.execute("INSERT INTO analyst_sessions (id, started_at) VALUES (?,?)",
                     (sid, now_iso()))
    return sid


@route("POST", "/api/analyst/ask")
def ask(params, q, body):
    if not cfg("analyst_panel", "enabled"):
        return 503, {"error": "analyst panel disabled in config"}
    if not isinstance(body, dict) or not (body.get("question") or "").strip():
        return 400, {"error": "body must be {question, session_id?, focused_entity?}"}
    question = body["question"].strip()[:800]
    session_id = _session(body.get("session_id"))
    focused = body.get("focused_entity")  # §24.1 context-aware opening
    # v8.16.1 — the active UI language, so the answer is composed natively in it
    lang = (body.get("lang") or "en") if isinstance(body.get("lang"), str) else "en"

    with write_tx() as conn:
        conn.execute("INSERT INTO analyst_messages (id, session_id, role, content,"
                     " focused_entity_context, created_at) VALUES (?,?,?,?,?,?)",
                     (new_id(), session_id, "user", question,
                      json.dumps(focused) if focused else None, now_iso()))

    # v5.2 — a greeting or meta question ('hi', 'what can you do?') gets a
    # natural reply, NOT three unrelated story citations. Let the model
    # answer conversationally with an empty data bundle; fall back to a
    # friendly canned line when no provider is configured.
    if _SMALLTALK.match(question) and len(question) < 64 and not FORECAST_WORDS.search(question):
        if llm.available():
            try:
                # v6.3.2 — hard wall-clock deadline (35s: comfortably under the
                # client's 60s abort even accounting for the internal retry)
                out = _bounded_or_raise(lambda: _answer_with_llm(question, {
                    "note": "The user sent a greeting or a meta question about you."
                            " Respond conversationally and briefly; no GlobeGrid data"
                            " was retrieved for this turn."}, session_id, lang), 35,
                    "the AI provider took too long to respond", "smalltalk_answer")
                return _store_answer(session_id, out["answer"],
                                     out.get("confidence", "high"), [], None)
            except (urllib.error.URLError, OSError, json.JSONDecodeError,
                    ValueError, ProviderError) as exc:
                log.warning("analyst_llm_failed", extra={"data": {"error": str(exc)}})
        return _store_answer(
            session_id,
            "Hi — I'm GlobeGrid's analyst. Ask me about live global events, conflicts, "
            "countries, alliances, or the causal stories the platform is tracking, and "
            "I'll answer from the fact chain (and pull from the web when a question "
            "reaches past what's tracked).", "high", [], None)

    # §24.4 scope boundary: forecast questions route to the §7 pathway
    if FORECAST_WORDS.search(question):
        from ..processing.forecast import enabled as forecasting_enabled, forecast_accuracy
        acc = forecast_accuracy()
        if forecasting_enabled():
            answer = ("Forecast-type questions go through GlobeGrid's tracked forecasting "
                      "pathway, where every forecast is logged and graded against what "
                      "actually happens — check the forecasts on the relevant story pages. "
                      f"Track record so far: {acc['resolved_forecasts']} resolved forecasts"
                      + (f", {acc['directionally_correct_pct']}% directionally correct."
                         if acc['directionally_correct_pct'] is not None else "."))
        else:
            answer = ("GlobeGrid doesn't improvise predictions in chat. Its forward-"
                      "forecasting pathway is currently disabled (it ships off until the "
                      "prediction scorecard has enough resolved history to make forecasts "
                      "accountable), so no forecast is available for this question.")
        return _store_answer(session_id, answer, "low", [], None)

    # Path 1 (structured) + Path 2 (freeform), merged into one bundle (§24.2).
    # v4 §16.2 — the question's own text ALWAYS gets first shot at the
    # entity layer; a focused entity (current page context) is only a
    # fallback when the question itself resolves to nothing. A stale or
    # even genuinely-current focus never overrides what was actually asked.
    entity = _entity_match(question)
    if entity is None and focused and isinstance(focused, dict) and focused.get("name"):
        # defense in depth (§16.2): ignore focus context past the staleness
        # window even if a future code path forgets to clear it
        stale_after = float(cfg("analyst_panel_fixes", "focus_staleness_timeout_seconds"))
        set_at = focused.get("set_at")
        fresh = True
        if set_at is not None:
            try:
                import time as _time
                fresh = (_time.time() * 1000 - float(set_at)) / 1000 <= stale_after
            except (TypeError, ValueError):
                fresh = True
        if fresh:
            entity = _entity_match(str(focused.get("name")))
    stories = _freeform_retrieval(question, entity["name"] if entity else None)

    # v6.2 — SPEED: the answer LLM call is the only thing on the hot path.
    # Web search and on-demand leadership verification were adding 8-33s of
    # blocking network+LLM latency BEFORE the answer even started, which is
    # what made a simple 'ukraine war' query blow the client timeout. Both are
    # now (a) skipped entirely when GlobeGrid already has a matched entity or
    # any tracked stories, and (b) hard-bounded and config-gated when they do
    # run. A well-covered query now hits only one Groq call (~a few seconds).
    web_results = []
    thin = entity is None and not stories
    if thin and bool(cfg("analyst_panel", "web_search_enabled")):
        # v6.3.2 — HARD wall-clock deadline (12s), not just the internal
        # urllib `timeout=8` on the request. On some Windows/firewall/AV
        # setups a DNS resolution stall isn't fully bounded by that socket
        # timeout and can hang far longer — this is the prime suspect for
        # "consulting the fact chain & web… (forever)": a question that
        # doesn't match tracked data falls into this branch, and a stuck DNS
        # lookup for duckduckgo.com blocks the whole request well past 60s.
        # _bounded gives up and returns [] instead of ever blocking that long.
        web_results = _bounded(lambda: _web_search(question), 12, [], "web_search")

    latest_instability = query_one(
        "SELECT score FROM instability_scores WHERE is_synthetic = 0"
        " ORDER BY computed_at DESC LIMIT 1")
    bundle = {"entity": entity, "stories": stories, "web_results": web_results,
              "global_instability_index": latest_instability["score"]
              if latest_instability else None}
    # v6 §29 — screen-aware: whatever panel/page is open right now rides in
    # the bundle so 'this conflict' needs no restating
    if isinstance(body.get("screen"), dict):
        bundle["screen"] = body["screen"]
    # v7 Part 6 — curated world-knowledge dossier for the matched entity AND
    # the panel currently on screen: the analyst answers with real depth even
    # for a user who knows nothing about the topic.
    try:
        from ..geopolitics import world_knowledge as wk
        packs = []
        if entity:
            et, eid = entity.get("type"), entity.get("id")
            nm = entity.get("name") or eid
            if et == "country":
                packs.append(wk.context_pack("country", eid, entity))
            elif et == "conflict":
                packs.append(wk.context_pack("conflict", nm))
            elif et == "alliance":
                packs.append(wk.context_pack("alliance", nm))
            elif et == "non_state_actor":
                packs.append(wk.context_pack("non_state_actor", nm))
        tp = (bundle.get("screen") or {}).get("top_panel") or {}
        if tp.get("kind") == "country" and tp.get("id"):
            prof = query_one("SELECT * FROM countries WHERE id = ?", (tp["id"],))
            packs.append(wk.context_pack("country", tp["id"],
                                         dict(prof) if prof else None))
        elif tp.get("kind") == "war" and tp.get("id"):
            crow = query_one("SELECT name FROM conflicts WHERE id = ?", (tp["id"],))
            if crow:
                packs.append(wk.context_pack("conflict", crow["name"]))
        elif tp.get("kind") == "un":
            packs.append(wk.context_pack("un", None))
        packs = [p for p in packs if p]
        if packs:
            # dedupe while preserving order (entity + screen often coincide)
            seen, uniq = set(), []
            for p in packs:
                if p not in seen:
                    seen.add(p)
                    uniq.append(p)
            bundle["world_knowledge"] = "\n\n".join(uniq)
        # v7.2 — the seven-decade historical arc, always available so the
        # analyst can place any current event in its 1945→present context
        # for a total newcomer.
        from ..geopolitics.world_knowledge import era_context
        bundle["historical_eras"] = era_context()
    except Exception:  # noqa: BLE001 — knowledge is enrichment, never a blocker
        pass
    # v6 §29 — region questions produce real deep-dive content: linked
    # countries + conflicts + story threads + events, not a one-liner
    region_links = None
    if entity and entity.get("type") == "region":
        region_links = _region_deep_dive(entity["id"])
        bundle["region_content"] = region_links
    # v6.2 — live leadership verification is OFF the synchronous hot path (it
    # ran a web search + a second LLM call, ~30s). It stays available but only
    # when explicitly enabled; the seeded/synced leadership is used otherwise.
    if bool(cfg("analyst_panel", "live_verify_on_hot_path")):
        verification = _live_verification(entity)
        if verification:
            bundle["live_verification"] = verification

    navigation = None
    if entity:
        navigation = {"type": entity["type"], "id": entity["id"], "name": entity["name"]}
    else:
        # v6.6.7 — no structured entity, but the question may name a leader →
        # navigate to that leader's profile page.
        _lname = _leader_match(question)
        if _lname:
            navigation = {"type": "leader", "name": _lname}

    # v5.2 — always answer through the model when a provider is available,
    # even with empty tracked data: it can lean on web results or answer
    # conversationally rather than refusing outright.
    provider_error = None
    if llm.available():
        try:
            # v6.3.2 — hard wall-clock deadline (answer_timeout_seconds + 12s
            # buffer for the plain-mode retry) around the WHOLE LLM call, so a
            # nested timeout that doesn't get honored by the OS/network layer
            # still can't block the request past this ceiling.
            try:
                budget = int(float(cfg("analyst_panel", "answer_timeout_seconds"))) + 12
            except (KeyError, TypeError):
                budget = 36
            out = _bounded_or_raise(
                lambda: _answer_with_llm(question, bundle, session_id), budget,
                f"the AI provider took longer than {budget}s to respond", "answer_llm")
            valid_ids = {s["id"] for s in stories}
            cited = [c for c in out.get("cited_story_ids", []) if c in valid_ids]
            # §24.4 guardrail: never navigate on a weak answer
            min_conf = str(cfg("analyst_panel", "min_confidence_to_navigate"))
            rank = {"low": 0, "medium": 1, "high": 2}
            # v6.6.7 — a deterministic leader/entity name match navigates even on
            # a low-confidence answer (the match itself is unambiguous).
            nav = navigation if (navigation and navigation.get("type") == "leader") \
                or rank[out["confidence"]] >= rank.get(min_conf, 1) else None
            deep = out.get("deep_dive")
            return _store_answer(session_id, out["answer"], out["confidence"], cited,
                                 nav, deep_dive=deep if isinstance(deep, str) else None,
                                 linked=region_links)
        except ProviderError as exc:
            # v6.3.1 — the provider IS configured but the call failed; keep the
            # real reason so we can tell the user (bad key / dead model / etc.)
            provider_error = str(exc)
            log.warning("analyst_provider_error", extra={"data": {"error": provider_error}})
        except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as exc:
            provider_error = str(exc)
            log.warning("analyst_llm_failed", extra={"data": {"error": provider_error}})

    # v6.3.1 — a CONFIGURED provider that errored is a real, fixable problem:
    # surface the actual reason (bad/expired key, decommissioned model, rate
    # limit) instead of the misleading "no AI provider" copy.
    if provider_error:
        return _store_answer(
            session_id,
            "The AI provider is configured but the call failed, so I couldn't generate a "
            "full answer. Reason: " + provider_error + ". Check your key in Settings, or "
            "the model name in config (llm_provider.groq_model) if it was decommissioned.",
            "low", [s["id"] for s in stories[:5]] if stories else [], navigation)

    # retrieval-only mode (no provider or LLM failure): cited summary, no prose
    # v6.6.7 — a deterministic leader match still navigates even with no AI/data.
    if entity is None and navigation and navigation.get("type") == "leader":
        return _store_answer(
            session_id,
            f"Opening the profile for {navigation['name']}. (Add a free AI key, e.g. Groq, "
            "in Settings for a full conversational answer.)", "low", [], navigation)
    if entity is None and navigation is None and not stories and not web_results:
        return _store_answer(
            session_id,
            "GlobeGrid doesn't have current tracked data on that, and no AI provider is "
            "configured to reason further. Add a free AI key (Groq recommended) in "
            "Settings to unlock full analyst answers with web search.", "low", [], None)
    parts = []
    if entity:
        ctx = entity["context"]
        detail = ctx.get("summary") or ctx.get("description_synthesis") \
            or ctx.get("stance_summary") or ctx.get("description") or ""
        parts.append(f"GlobeGrid tracks {entity['name']} ({entity['type'].replace('_', ' ')})."
                     + (f" {detail}" if detail else ""))
    if stories:
        parts.append(f"{len(stories)} recent tracked stories match — most recent: "
                     f"“{stories[0]['headline']}”. Citations below.")
    parts.append("(Add a free AI key, e.g. Groq, in Settings for full conversational "
                 "analyst answers.)")
    return _store_answer(session_id, " ".join(parts), "low",
                         [s["id"] for s in stories[:5]], navigation)


def _store_answer(session_id, answer, confidence, cited, navigation,
                  deep_dive=None, linked=None):
    mid = new_id()
    with write_tx() as conn:
        conn.execute(
            "INSERT INTO analyst_messages (id, session_id, role, content, cited_story_ids,"
            " suggested_navigation, created_at) VALUES (?,?,?,?,?,?,?)",
            (mid, session_id, "assistant", answer,
             json.dumps(cited) if cited else None,
             json.dumps(navigation) if navigation else None, now_iso()))
        conn.execute("UPDATE analyst_sessions SET last_message_at = ? WHERE id = ?",
                     (now_iso(), session_id))
    citations = []
    if cited:
        marks = ",".join("?" * len(cited))
        citations = [dict(r) for r in query(
            f"SELECT id, headline FROM stories WHERE id IN ({marks})", cited)]
    return 200, {"session_id": session_id, "message_id": mid, "answer": answer,
                 "confidence": confidence, "citations": citations,
                 "suggested_navigation": navigation,
                 # v6 §29 — expandable fuller analysis + region deep-dive links
                 "deep_dive": deep_dive, "linked": linked}


@route("GET", "/api/analyst/diagnostics")
def diagnostics(params, q, body):
    """v6.3.1 — a self-test for the analyst's LLM path so a broken key/model is
    diagnosable in one click instead of guessing. Reports which providers are
    usable and does a live minimal call, returning the raw result or the real
    provider error. Hit /api/analyst/diagnostics in the browser."""
    from ..processing import llm as _llm
    providers = {}
    for name in _llm._order():
        providers[name] = _llm._usable(name)
    result = {"providers_usable": providers, "ai_available": _llm.available(),
              "groq_model": _llm._groq_model()}
    if _llm.available():
        import time as _time
        t0 = _time.time()
        text = _llm.complete(
            "You are a test. Reply with a JSON object: {\"ok\": true}.",
            [{"role": "user", "content": "ping"}],
            max_tokens=20, timeout=20, json_mode=True, interactive=True)
        result["live_call_ms"] = int((_time.time() - t0) * 1000)
        result["live_call_ok"] = bool(text)
        result["live_call_reply"] = (text or "")[:200]
        result["live_call_error"] = _llm.last_error()
    return 200, result


@route("GET", "/api/analyst/history")
def history(params, q, body):
    session_id = q.get("session_id")
    if not session_id:
        row = query_one("SELECT id FROM analyst_sessions ORDER BY started_at DESC LIMIT 1")
        if not row:
            return 200, {"session_id": None, "messages": []}
        session_id = row["id"]
    messages = [dict(r) for r in query(
        "SELECT * FROM analyst_messages WHERE session_id = ? ORDER BY created_at",
        (session_id,))]
    for m in messages:
        for f in ("cited_story_ids", "suggested_navigation", "focused_entity_context"):
            if m.get(f):
                m[f] = json.loads(m[f])
    return 200, {"session_id": session_id, "messages": messages}


@route("POST", "/api/analyst/clear")
def clear_history(params, q, body):
    """v7.3 — wipe conversation history. Clears the given session (or all
    sessions when none is named) so the next question starts a fresh thread."""
    from ..db.session import write_tx
    session_id = (body or {}).get("session_id") or q.get("session_id")
    with write_tx() as conn:
        if session_id:
            conn.execute("DELETE FROM analyst_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM analyst_sessions WHERE id = ?", (session_id,))
        else:
            conn.execute("DELETE FROM analyst_messages")
            conn.execute("DELETE FROM analyst_sessions")
    return 200, {"cleared": True}
