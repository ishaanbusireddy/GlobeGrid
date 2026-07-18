"""Section 8.1 (v1) + v2 addendum routes.

GET  /api/stories            (since, limit, category, as_of, format=json|csv)
GET  /api/stories/{id}       full detail incl. predictions + second-order links
POST /api/translate          Section 5.8 display-time translation
GET  /api/predictions        §3.4 aggregated scorecard + recent grades
GET  /api/briefings          §6.1 latest (or ?date=YYYY-MM-DD) daily briefing
GET/POST/DELETE /api/watchlist  §6.2
GET  /api/search?q=          §6.4 FTS5 across stories + facts
GET  /api/graph              §6.3 canonical-entity co-occurrence graph

v2 §4: as_of reconstructs the feed as it stood at that moment (stories
filtered to first_seen_at <= as_of). v2 §3.3: member/source counts
exclude wire-copy duplicates.
"""

import csv
import io
import json
import re

from ..db.session import query, query_one, write_tx
from ..db.models import row_to_dict, new_id, now_iso, meta_get
from .router import route


def _member_events(story_id: str) -> list[dict]:
    rows = query(
        "SELECT e.*, m.linked_via, m.linked_at, s.id AS src_id, s.name AS src_name,"
        " s.url AS src_url, s.leaning AS src_leaning, s.kind AS src_kind,"
        " s.reliability_tier AS src_tier, r.raw_content,"
        " f.sentiment AS fact_sentiment, f.duplicate_of_fact_id"
        " FROM story_members m JOIN events e ON e.id = m.event_id"
        " JOIN raw_items r ON r.id = e.raw_item_id"
        " JOIN sources s ON s.id = r.source_id"
        " LEFT JOIN extracted_facts f ON f.event_id = e.id"
        " WHERE m.story_id = ? ORDER BY e.occurred_at", (story_id,))
    out = []
    for r in rows:
        d = row_to_dict(r, drop=("embedding", "raw_content", "src_id", "src_name",
                                 "src_url", "src_leaning", "src_kind", "src_tier",
                                 "fact_sentiment", "duplicate_of_fact_id"))
        try:
            link = json.loads(r["raw_content"]).get("link", "")
        except (json.JSONDecodeError, TypeError):
            link = ""
        d["source"] = {"id": r["src_id"], "name": r["src_name"], "url": r["src_url"],
                       "leaning": r["src_leaning"], "kind": r["src_kind"],
                       "reliability_tier": r["src_tier"],   # v5 §21 citation chip
                       "article_link": link}
        d["sentiment"] = r["fact_sentiment"]
        d["is_duplicate"] = r["duplicate_of_fact_id"] is not None
        out.append(d)
    return out


def _connected_history(story_id: str) -> list[dict]:
    """The fact-chain panel: members that arrived via historical_chain."""
    rows = query(
        'SELECT f.id, f.who, f.what, f."where" AS where_text, f.when_occurred,'
        " m.linked_at, s.name AS src_name, s.url AS src_url"
        " FROM story_members m JOIN extracted_facts f ON f.id = m.fact_id"
        " JOIN sources s ON s.id = f.source_id"
        " WHERE m.story_id = ? AND m.linked_via = 'historical_chain'"
        " ORDER BY f.when_occurred", (story_id,))
    return [{"id": r["id"], "who": r["who"], "what": r["what"], "where": r["where_text"],
             "when_occurred": r["when_occurred"], "linked_at": r["linked_at"],
             "source": {"name": r["src_name"], "url": r["src_url"]}} for r in rows]


# ---------------------------------------------------------------------------
# v8.16 — literal country-mention scan (owner: "scrape the title/articles of
# events for the country names literally mentioned and add those as impacted
# countries … display like 1-2 country chips nested in the event panels in the
# live feed"). High-precision by construction: only a word-boundary match of
# the country's actual name (or a curated unambiguous alias) counts, which is
# also the tightening fix for spurious NER chips (the Greenland-on-an-Iran-
# story bug — Greenland is never literally in that text, so it can't rank).
import re as _re2

# case-SENSITIVE acronyms/short forms (lowercase "us" is a pronoun) + common
# case-insensitive alternate names, each mapping to the DB country name.
_CHIP_ACRONYMS = {"US": "United States", "U.S.": "United States",
                  "USA": "United States", "UK": "United Kingdom",
                  "UAE": "United Arab Emirates", "DPRK": "North Korea",
                  "DRC": "Democratic Republic of the Congo"}
_CHIP_ALIASES = {"america": "United States", "britain": "United Kingdom",
                 "russian": "Russia", "ukrainian": "Ukraine",
                 "iranian": "Iran", "israeli": "Israel", "chinese": "China",
                 "turkish": "Turkey", "türkiye": "Turkey",
                 "north korean": "North Korea", "south korean": "South Korea",
                 "saudi": "Saudi Arabia", "burma": "Myanmar"}
# alliance/bloc chips that should read like countries, flag included (owner:
# "when NATO is affected, it should display the NATO flag just like a country")
_CHIP_BLOCS = ("NATO", "European Union", "African Union", "ASEAN",
               "Arab League", "BRICS", "OPEC", "Mercosur")

_chip_cache: dict = {}


def _chip_tables():
    """Build (case-insensitive regex, case-sensitive regex, name→row map) once."""
    if _chip_cache:
        return _chip_cache
    rows = query("SELECT id, name, status, flag_image_url FROM countries")
    by_name = {}
    ci_terms, cs_terms = [], []
    for r in rows:
        by_name[r["name"].lower()] = {"type": ("territory" if r["status"] == "territory"
                                               else "country"),
                                      "id": r["id"], "name": r["name"],
                                      "flag": r["flag_image_url"]}
        ci_terms.append(_re2.escape(r["name"]))
    for alias, target in _CHIP_ALIASES.items():
        if target.lower() in by_name:
            ci_terms.append(_re2.escape(alias))
    for acro in _CHIP_ACRONYMS:
        cs_terms.append(_re2.escape(acro))
    from ..geopolitics.country_extra import ALLIANCE_EMBLEMS
    for bloc in _CHIP_BLOCS:
        a = query_one("SELECT id, name FROM alliances WHERE name = ?", (bloc,))
        if a:
            by_name[bloc.lower()] = {"type": "alliance", "id": a["id"],
                                     "name": a["name"],
                                     "flag": ALLIANCE_EMBLEMS.get(bloc)}
            if bloc not in ("NATO",):        # NATO stays case-sensitive
                ci_terms.append(_re2.escape(bloc))
            else:
                cs_terms.append(_re2.escape(bloc))
    # longest-first so "South Korea" beats "Korea"-less partials
    ci_terms.sort(key=len, reverse=True)
    cs_terms.sort(key=len, reverse=True)
    _chip_cache["ci"] = _re2.compile(r"\b(" + "|".join(ci_terms) + r")\b",
                                     _re2.IGNORECASE)
    _chip_cache["cs"] = _re2.compile(r"\b(" + "|".join(cs_terms) + r")\b")
    _chip_cache["map"] = by_name
    return _chip_cache


def _literal_impact_chips(text: str, limit: int = 2) -> list[dict]:
    """Country/bloc chips literally named in `text`, first-mention order."""
    if not text:
        return []
    t = _chip_tables()
    found, seen = [], set()
    hits = []
    for m in t["ci"].finditer(text):
        hits.append((m.start(), m.group(1)))
    for m in t["cs"].finditer(text):
        hits.append((m.start(), m.group(1)))
    for _, raw in sorted(hits, key=lambda h: h[0]):
        low = raw.lower()
        name = (_CHIP_ACRONYMS.get(raw) or _CHIP_ALIASES.get(low) or raw).lower()
        row = t["map"].get(name)
        if row and row["name"] not in seen:
            seen.add(row["name"])
            found.append(dict(row))
            if len(found) >= limit:
                break
    return found


def _story_card(row) -> dict:
    d = row_to_dict(row, json_fields=("causal_narrative",), drop=("embedding",
                                                                  "needs_causal_refresh"))
    # v7 §6 — first located member event, so the audio briefing's globe
    # autopilot (and any pan-to) can fly to the story without a second fetch
    loc = query_one(
        "SELECT e.location_lat AS lat, e.location_lon AS lon FROM events e"
        " JOIN story_members m ON m.event_id = e.id"
        " WHERE m.story_id = ? AND e.location_lat IS NOT NULL LIMIT 1",
        (d["id"],))
    if loc:
        d["lat"], d["lon"] = loc["lat"], loc["lon"]
    # §3.3 — duplicates excluded from member/source counts
    stats = query_one(
        "SELECT COUNT(DISTINCT m.event_id) AS n_events,"
        " COUNT(DISTINCT r.source_id) AS n_sources"
        " FROM story_members m"
        " LEFT JOIN events e ON e.id = m.event_id"
        " LEFT JOIN raw_items r ON r.id = e.raw_item_id"
        " LEFT JOIN extracted_facts f ON f.event_id = e.id"
        " WHERE m.story_id = ? AND (f.duplicate_of_fact_id IS NULL)", (row["id"],))
    cats = query(
        "SELECT e.category, COUNT(*) AS n FROM story_members m"
        " JOIN events e ON e.id = m.event_id WHERE m.story_id = ?"
        " GROUP BY e.category ORDER BY n DESC", (row["id"],))
    d["member_count"] = stats["n_events"] or 0
    d["source_count"] = stats["n_sources"] or 0
    d["category"] = cats[0]["category"] if cats else "other"
    # v8.16 — carry the story's peak severity on the card so a breaking-news
    # toast + fanfare can fire the INSTANT the socket pushes it (owner: "no
    # delay, right when they enter feed") instead of waiting for the map to
    # refresh and then looking the severity up from the event list.
    sev = query_one(
        "SELECT MAX(e.severity) AS s FROM story_members m"
        " JOIN events e ON e.id = m.event_id WHERE m.story_id = ?", (row["id"],))
    d["severity"] = (sev["s"] if sev else None) or 0
    d["has_historical_link"] = bool(query_one(
        "SELECT 1 FROM story_members WHERE story_id = ? AND linked_via = 'historical_chain'"
        " LIMIT 1", (row["id"],)))
    # v7.4 — the real WHEN of the story: the min/max of its member events'
    # occurred_at, so the UI can date a story by when it actually happened
    # (a 1945 landmark reads "1945", not today's ingestion time).
    span = query_one(
        "SELECT MIN(e.occurred_at) AS first_occurred, MAX(e.occurred_at) AS last_occurred"
        " FROM story_members m JOIN events e ON e.id = m.event_id WHERE m.story_id = ?",
        (row["id"],))
    if span:
        d["first_occurred_at"] = span["first_occurred"]
        d["last_occurred_at"] = span["last_occurred"]
        # a story is "historical" when even its newest event predates the live
        # window — the UI badges it and shows the event date, not "today"
        import datetime as _dt
        try:
            newest = _dt.datetime.fromisoformat(
                (span["last_occurred"] or "").replace("Z", "+00:00"))
            d["is_historical"] = (
                _dt.datetime.now(_dt.timezone.utc) - newest).days > 60
        except (ValueError, TypeError):
            d["is_historical"] = False
    # v6.6.2 — attach the tagged conflict's name so the feed card can show a
    # clickable conflict chip that opens War Mode for it
    if d.get("conflict_id"):
        c = query_one("SELECT name FROM conflicts WHERE id = ?", (row["conflict_id"],))
        d["conflict_name"] = c["name"] if c else None
    # v8.16 — 1-2 literally-mentioned country/bloc chips for the feed card
    d["impact_chips"] = _literal_impact_chips(
        f"{d.get('headline') or ''} {d.get('summary') or ''}")
    return d


def _story_cards(rows) -> list:
    """v7.4.5 — batched equivalent of `_story_card` for the LIVE FEED list.

    The per-story `_story_card` ran ~6 sub-queries EACH; at limit=60 that is
    ~360 queries per `/api/stories` call, and the socket used to fire that call
    on every story push — under live ingestion the endpoint could exceed the
    client's 25s timeout, so `refreshStories()` threw and the feed stuck on
    "Connecting to the live feed…" while the map (a cheaper endpoint) kept
    working. This computes every aggregate in a handful of set-based queries
    keyed by story_id, so the feed list is fast and can't time out."""
    import datetime as _dt
    ids = [r["id"] for r in rows]
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    cards = {r["id"]: row_to_dict(
        r, json_fields=("causal_narrative",),
        drop=("embedding", "needs_causal_refresh")) for r in rows}

    # member/source counts (duplicates excluded), grouped
    for s in query(
            "SELECT m.story_id AS sid,"
            " COUNT(DISTINCT m.event_id) AS n_events,"
            " COUNT(DISTINCT r.source_id) AS n_sources"
            " FROM story_members m"
            " LEFT JOIN events e ON e.id = m.event_id"
            " LEFT JOIN raw_items r ON r.id = e.raw_item_id"
            " LEFT JOIN extracted_facts f ON f.event_id = e.id"
            f" WHERE m.story_id IN ({marks}) AND (f.duplicate_of_fact_id IS NULL)"
            " GROUP BY m.story_id", tuple(ids)):
        c = cards.get(s["sid"])
        if c:
            c["member_count"] = s["n_events"] or 0
            c["source_count"] = s["n_sources"] or 0

    # dominant category per story (highest member count)
    cat_best = {}
    for s in query(
            "SELECT m.story_id AS sid, e.category AS category, COUNT(*) AS n"
            " FROM story_members m JOIN events e ON e.id = m.event_id"
            f" WHERE m.story_id IN ({marks})"
            " GROUP BY m.story_id, e.category", tuple(ids)):
        cur = cat_best.get(s["sid"])
        if cur is None or (s["n"] or 0) > cur[1]:
            cat_best[s["sid"]] = (s["category"], s["n"] or 0)

    # first located member event (for pan-to / audio-briefing autopilot)
    for s in query(
            "SELECT m.story_id AS sid, e.location_lat AS lat, e.location_lon AS lon"
            " FROM story_members m JOIN events e ON e.id = m.event_id"
            f" WHERE m.story_id IN ({marks}) AND e.location_lat IS NOT NULL"
            " ORDER BY e.occurred_at", tuple(ids)):
        c = cards.get(s["sid"])
        if c and "lat" not in c:
            c["lat"], c["lon"] = s["lat"], s["lon"]

    # occurred span per story
    span = {}
    for s in query(
            "SELECT m.story_id AS sid, MIN(e.occurred_at) AS first_occurred,"
            " MAX(e.occurred_at) AS last_occurred"
            " FROM story_members m JOIN events e ON e.id = m.event_id"
            f" WHERE m.story_id IN ({marks}) GROUP BY m.story_id", tuple(ids)):
        span[s["sid"]] = s

    # historical-chain link presence
    hist = {r["story_id"] for r in query(
        "SELECT DISTINCT story_id FROM story_members"
        f" WHERE story_id IN ({marks}) AND linked_via = 'historical_chain'", tuple(ids))}

    # tagged conflict names
    conf_ids = [c["conflict_id"] for c in cards.values() if c.get("conflict_id")]
    conf_names = {}
    if conf_ids:
        cm = ",".join("?" * len(conf_ids))
        conf_names = {r["id"]: r["name"] for r in query(
            f"SELECT id, name FROM conflicts WHERE id IN ({cm})", tuple(conf_ids))}

    now_utc = _dt.datetime.now(_dt.timezone.utc)
    for sid, c in cards.items():
        c.setdefault("member_count", 0)
        c.setdefault("source_count", 0)
        c["category"] = cat_best.get(sid, ("other",))[0] or "other"
        c["has_historical_link"] = sid in hist
        sp = span.get(sid)
        if sp:
            c["first_occurred_at"] = sp["first_occurred"]
            c["last_occurred_at"] = sp["last_occurred"]
            try:
                newest = _dt.datetime.fromisoformat(
                    (sp["last_occurred"] or "").replace("Z", "+00:00"))
                c["is_historical"] = (now_utc - newest).days > 60
            except (ValueError, TypeError):
                c["is_historical"] = False
        if c.get("conflict_id"):
            c["conflict_name"] = conf_names.get(c["conflict_id"])
        # v8.16 — literal country/bloc chips (pure in-memory regex, no query)
        c["impact_chips"] = _literal_impact_chips(
            f"{c.get('headline') or ''} {c.get('summary') or ''}")
    # v8.18 — reverse translation: attach the English rendering of a non-English
    # headline/summary (stored under language='en' by the reverse-translate job)
    # so an English UI reads foreign feed items in English. One set-based query.
    for t in query(
            "SELECT content_id AS sid, field, translated_text FROM content_translations"
            f" WHERE language = 'en' AND content_id IN ({marks})"
            " AND field IN ('headline','summary')", tuple(ids)):
        c = cards.get(t["sid"])
        if c and t["translated_text"]:
            c["headline_en" if t["field"] == "headline" else "summary_en"] = t["translated_text"]
    # preserve the incoming row order (already sorted by the SQL ORDER BY)
    return [cards[i] for i in ids]


def _stories_rows(q) -> list:
    conditions, args = ["1=1"], []
    # v7.4.2 — the LIVE feed must NEVER show synthetic demo rows (owner: "the
    # live feed is now filled with synthetic data … real data stopped coming
    # in"). Synthetic stories carry current timestamps, so newest-first sorting
    # floated them to the top and pushed real stories past the limit — the feed
    # LOOKED all-synthetic. Exclude is_synthetic unless explicitly requested.
    if q.get("include_synthetic") != "1":
        conditions.append("COALESCE(s.is_synthetic, 0) = 0")
    # v7.4 — the LIVE feed only shows stories whose newest tracked event is
    # recent (owner: "Historical events and new stories from YEARS ago should
    # NOT appear in the live feed but instead somewhere else, like the
    # archives"). A story built purely from historical events (1945→2024 packs,
    # correctly dated by occurred_at) is thus kept out of the live feed but
    # stays fully browsable in the History/Archive view — which sets `from`/`to`
    # and therefore skips this gate, as do the `as_of` time-capsule and an
    # explicit include_historical=1.
    if not (q.get("from") or q.get("to") or q.get("as_of")
            or q.get("include_historical") == "1"):
        from datetime import datetime, timedelta, timezone as _tz
        from ..config import CONFIG
        days = int((CONFIG.get("feed") or {}).get("live_window_days", 45))
        cutoff = (datetime.now(_tz.utc) - timedelta(days=days)).isoformat(
            timespec="seconds").replace("+00:00", "Z")
        conditions.append(
            "EXISTS (SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
            " WHERE m.story_id = s.id AND e.occurred_at >= ?)")
        args.append(cutoff)
    if q.get("since"):
        conditions.append("s.last_updated_at > ?")
        args.append(q["since"])
    if q.get("as_of"):  # §4 time capsule
        conditions.append("s.first_seen_at <= ?")
        args.append(q["as_of"])
    if q.get("category"):
        conditions.append(
            "s.id IN (SELECT m.story_id FROM story_members m JOIN events e"
            " ON e.id = m.event_id WHERE e.category = ?)")
        args.append(q["category"])
    if q.get("watchlist") == "1":  # §6.2 watchlist-scoped feed
        conditions.append("(" + _watchlist_condition() + ")")
    if q.get("conflict_id"):  # v3 §15 — conflict tabs are just filtered feeds
        conditions.append("s.conflict_id = ?")
        args.append(q["conflict_id"])
    if q.get("story_type"):   # v4 §8.1 taxonomy
        conditions.append("s.story_type = ?")
        args.append(q["story_type"])
    if q.get("min_relevance"):  # v4 §9.1 — hide low-relevance local coverage
        conditions.append(
            "EXISTS (SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
            " WHERE m.story_id = s.id AND COALESCE(e.global_relevance_score, 1.0) >= ?)")
        args.append(float(q["min_relevance"]))
    if q.get("region"):       # v4 §9.2 — continent filter, one state across views
        conditions.append("(" + _region_condition(q["region"]) + ")")
    if q.get("development_type"):   # v5 §3 — military-development feed filter
        conditions.append(
            "EXISTS (SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
            " WHERE m.story_id = s.id AND e.development_type = ?)")
        args.append(q["development_type"])
    if q.get("war_tab"):      # v6 §8 — War Mode right-panel sub-filters:
        # Military / Civilian / Diplomatic / Economic over member events'
        # development_type + category
        tab = q["war_tab"]
        if tab == "military":
            conditions.append(
                "EXISTS (SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
                " WHERE m.story_id = s.id AND e.development_type IN ('military','conflict'))")
        elif tab == "civilian":
            conditions.append(
                "EXISTS (SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
                " WHERE m.story_id = s.id AND e.category IN ('disaster','other')"
                " AND e.development_type IS NULL)")
        elif tab == "diplomatic":
            conditions.append(
                "EXISTS (SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
                " WHERE m.story_id = s.id AND e.category = 'geopolitics'"
                " AND e.development_type IS NULL)")
        elif tab == "economic":
            conditions.append(
                "EXISTS (SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
                " WHERE m.story_id = s.id AND e.category = 'finance')")
    if q.get("from"):         # v5 §1 — History/archive date-range browsing
        conditions.append("s.first_seen_at >= ?")
        args.append(q["from"])
    if q.get("to"):
        conditions.append("s.first_seen_at <= ?")
        args.append(q["to"])
    # v5 §1 — explicit sort controls: newest (default) / oldest / most-active
    order = {
        "oldest": "s.last_updated_at ASC",
        "active": "(SELECT COUNT(*) FROM story_members m WHERE m.story_id = s.id) DESC,"
                  " s.last_updated_at DESC",
    }.get(q.get("sort"), "s.last_updated_at DESC")
    offset = max(0, int(q.get("offset", 0)))
    limit = min(int(q.get("limit", 50)), 200)
    return query(
        f"SELECT s.* FROM stories s WHERE {' AND '.join(conditions)}"
        f" ORDER BY {order} LIMIT ? OFFSET ?", (*args, limit, offset))


def _region_condition(region: str) -> str:
    """v4 §9.2 — a story belongs to a continent when a member fact mentions
    any of that continent's countries (countries.region prefix match, so
    'Europe' covers 'Western Europe' etc.)."""
    like = f"%{region.replace(chr(39), chr(39) * 2)}%"
    names = [r["name"].replace("'", "''") for r in query(
        "SELECT name FROM countries WHERE region LIKE ?", (like,))]
    if not names:
        return "1=0"
    clauses = []
    for n in names[:80]:
        clauses.append(
            "s.id IN (SELECT m.story_id FROM story_members m"
            " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
            f" WHERE f.who LIKE '%{n}%' OR f.\"where\" LIKE '%{n}%')")
    return " OR ".join(clauses)


def _watchlist_condition() -> str:
    items = query("SELECT kind, value FROM watchlist_items")
    if not items:
        return "1=0"
    clauses = []
    for it in items:
        v = it["value"].replace("'", "''")
        if it["kind"] == "category":
            clauses.append("s.id IN (SELECT m.story_id FROM story_members m"
                           f" JOIN events e ON e.id = m.event_id WHERE e.category = '{v}')")
        elif it["kind"] == "region":
            clauses.append("s.id IN (SELECT m.story_id FROM story_members m"
                           " JOIN events e ON e.id = m.event_id"
                           f" WHERE e.location_name LIKE '%{v}%')")
        else:  # entity (canonical id or name substring on who)
            clauses.append("s.id IN (SELECT m.story_id FROM story_members m"
                           " JOIN extracted_facts f ON f.event_id = m.event_id"
                           f" WHERE f.canonical_entity_ids LIKE '%{v}%'"
                           f" OR f.who LIKE '%{v}%')")
    return " OR ".join(clauses)


def _dedup_by_headline(cards: list) -> list:
    """v8.13 — collapse repeated stories in the History/archive view (owner: "the
    history archive repeats the same stories from 7/08 and 7/09"). The same real
    event reported across days/sources can spawn near-identical story cards; in
    the date-range archive they read as duplicates. Keep the first (newest, since
    the list is already sorted) card per normalized headline."""
    seen, out = set(), []
    for c in cards:
        key = re.sub(r"[^a-z0-9]+", " ", (c.get("headline") or "").lower()).strip()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


@route("GET", "/api/stories")
def list_stories(params, q, body):
    rows = _stories_rows(q)
    cards = _story_cards(rows)   # v7.4.5 — batched (was per-story; timed out under load)
    if q.get("from") or q.get("to"):   # v8.13 — archive view de-dups repeats
        cards = _dedup_by_headline(cards)
    if q.get("format") == "csv":  # §6.4 export
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "headline", "summary", "confidence", "category",
                         "member_count", "source_count", "first_seen_at",
                         "last_updated_at"])
        for c in cards:
            writer.writerow([c["id"], c["headline"], c["summary"], c["confidence"],
                             c["category"], c["member_count"], c["source_count"],
                             c["first_seen_at"], c["last_updated_at"]])
        return 200, {"_raw_csv": buf.getvalue(), "_filename": "stories.csv"}
    return 200, {"stories": cards}


@route("GET", "/api/conflicts/{cid}/feed")
def conflict_feed(params, q, body):
    """v7.5 — the dedicated War Mode feed: EVERYTHING pertaining to one conflict,
    in one call, split into a stories tab and an events tab (owner: "a specific
    live feed just for war mode that funnels all events corresponding to that
    war — one tab for stories one tab for events"). War Mode closes the general
    global feed and shows this conflict-only right panel instead."""
    cid = params["cid"]
    rows = query(
        "SELECT s.* FROM stories s WHERE s.conflict_id = ?"
        " AND COALESCE(s.is_synthetic,0)=0 ORDER BY s.last_updated_at DESC LIMIT 100",
        (cid,))
    stories = _story_cards(rows)
    # events: directly conflict-tagged OR a member of a story tagged to this
    # conflict — so nothing about the war is missed, however it got linked.
    events = [dict(e) for e in query(
        "SELECT DISTINCT e.id, e.title, e.description,"
        " e.location_lat AS lat, e.location_lon AS lon, e.location_name,"
        " e.category, e.severity, e.occurred_at, e.development_type,"
        " (SELECT m2.story_id FROM story_members m2 WHERE m2.event_id = e.id LIMIT 1)"
        "   AS story_id"
        " FROM events e"
        " LEFT JOIN story_members m ON m.event_id = e.id"
        " LEFT JOIN stories s ON s.id = m.story_id"
        " WHERE COALESCE(e.is_synthetic,0)=0 AND (e.conflict_id = ? OR s.conflict_id = ?)"
        " ORDER BY e.occurred_at DESC LIMIT 250", (cid, cid))]
    # v8.13.2 — the War Mode "stories" tab shows THREADS/patterns, not individual
    # articles (owner: "the stories tab should be threads/clusters/patterns of
    # what's happening, not individual news articles — the events tab is the
    # articles"). Real narrative threads (story_threads) whose members belong to
    # this conflict come first; any remaining stories are grouped into themed
    # buckets by category, so the tab always reads as patterns, never a flat list.
    threads = _conflict_threads(cid, stories)
    return 200, {"stories": stories, "events": events, "threads": threads,
                 "story_count": len(stories), "event_count": len(events),
                 "thread_count": len(threads)}


# v8.13.2 — bucket labels for the synthesized-thread fallback (a themed pattern
# name per event category so the war "stories" tab reads as narrative threads).
_THREAD_BUCKETS = {
    "conflict": "Military operations & fighting", "military": "Force posture & deployments",
    "geopolitics": "Diplomacy & international response", "finance": "Economic & sanctions impact",
    "domestic": "Internal politics & governance", "health": "Humanitarian & public health",
    "disaster": "Humanitarian & disaster", "technology": "Cyber & technology",
    "other": "Other developments",
}


def _conflict_threads(cid: str, story_cards: list) -> list:
    """Group this conflict's stories into narrative threads: real story_threads
    first, then a category-bucket fallback for the rest."""
    by_id = {c["id"]: c for c in story_cards}
    used = set()
    out = []
    # real threads whose members are in this conflict
    for t in query(
            "SELECT t.id, t.name, t.description, COUNT(*) AS n"
            " FROM story_threads t"
            " JOIN story_thread_members m ON m.thread_id = t.id"
            " JOIN stories s ON s.id = m.story_id"
            " WHERE s.conflict_id = ? GROUP BY t.id ORDER BY n DESC", (cid,)):
        members = [by_id[r["story_id"]] for r in query(
            "SELECT m.story_id FROM story_thread_members m JOIN stories s"
            " ON s.id = m.story_id WHERE m.thread_id = ? AND s.conflict_id = ?", (t["id"], cid))
            if r["story_id"] in by_id]
        if not members:
            continue
        used.update(c["id"] for c in members)
        out.append({"id": t["id"], "name": t["name"], "kind": "thread",
                    "description": t["description"], "stories": members,
                    "story_count": len(members)})
    # category-bucket fallback for stories not in a real thread
    buckets: dict = {}
    for c in story_cards:
        if c["id"] in used:
            continue
        cat = c.get("category") or "other"
        buckets.setdefault(cat, []).append(c)
    for cat, members in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        out.append({"id": f"bucket:{cid}:{cat}", "name": _THREAD_BUCKETS.get(cat, cat.title()),
                    "kind": "bucket", "description": None, "stories": members,
                    "story_count": len(members)})
    return out


def _impacted_entities(story_id: str) -> list[dict]:
    """v7.4.1 — the entities this story impacts, as typed clickable chips shown
    at the TOP of the story panel (owner: "at the top of event panels link
    impacted countries/blocs/NSAs/zones/territories"). Resolves the story's
    tracked canonical entity names against the entity tables."""
    rows = query(
        "SELECT DISTINCT f.canonical_entity_ids FROM story_members m"
        " JOIN extracted_facts f ON f.id = m.fact_id"
        " WHERE m.story_id = ? AND f.canonical_entity_ids IS NOT NULL"
        " UNION"
        " SELECT DISTINCT f.canonical_entity_ids FROM story_members m"
        " JOIN events e ON e.id = m.event_id"
        " JOIN extracted_facts f ON f.event_id = e.id"
        " WHERE m.story_id = ? AND f.canonical_entity_ids IS NOT NULL",
        (story_id, story_id))
    names = set()
    for r in rows:
        try:
            for cid in json.loads(r["canonical_entity_ids"]):
                ce = query_one("SELECT canonical_name FROM canonical_entities WHERE id = ?", (cid,))
                if ce:
                    names.add(ce["canonical_name"])
        except (json.JSONDecodeError, TypeError):
            continue
    if not names:
        return []
    out, seen = [], set()

    def _add(kind, eid, nm, flag=None):
        key = (kind, eid)
        if key not in seen:
            seen.add(key)
            item = {"type": kind, "id": eid, "name": nm}
            if flag:                       # v8.13.4 — real flag on country/territory chips
                item["flag"] = flag
            out.append(item)

    # v8.16 — the literal-mention tightening (owner: "greenland was struck as
    # an affected country for iran related news … make that better"). The
    # story's own text (headline + summary + member event titles) is the
    # ground truth: a COUNTRY chip must be literally named there, or it's
    # dropped as an NER/alias artifact. Non-country chips (NSAs, zones) keep
    # the entity path — their names rarely appear verbatim but are distinctive.
    st = query_one("SELECT headline, summary FROM stories WHERE id = ?", (story_id,))
    text_parts = [st["headline"] or "", st["summary"] or ""] if st else []
    for ev in query(
            "SELECT e.title FROM story_members m JOIN events e ON e.id = m.event_id"
            " WHERE m.story_id = ? LIMIT 30", (story_id,)):
        text_parts.append(ev["title"] or "")
    story_text = " ".join(text_parts)
    literal = {c["name"] for c in _literal_impact_chips(story_text, limit=12)}
    from ..geopolitics.country_extra import ALLIANCE_EMBLEMS

    for nm in list(names)[:60]:
        low = nm.lower()
        c = query_one("SELECT id, name, status, flag_image_url FROM countries WHERE lower(name) = ?", (low,))
        if c:
            if c["name"] in literal:
                _add("territory" if (c["status"] == "territory") else "country",
                     c["id"], c["name"], c["flag_image_url"])
            continue
        a = query_one("SELECT id, name FROM alliances WHERE lower(name) = ?", (low,))
        if a:
            # v8.16 — bloc chips carry their real flag (NATO like a country)
            _add("alliance", a["id"], a["name"], ALLIANCE_EMBLEMS.get(a["name"]))
            continue
        nsa = query_one("SELECT id, name FROM non_state_actors WHERE lower(name) = ?", (low,))
        if nsa:
            _add("non_state_actor", nsa["id"], nsa["name"]); continue
        ml = query_one("SELECT id, name FROM marked_locations WHERE lower(name) = ?", (low,))
        if ml:
            _add("zone", ml["id"], ml["name"]); continue
    # any literally-named country the entity path missed still gets its chip
    for chip in _literal_impact_chips(story_text, limit=12):
        _add(chip["type"], chip["id"], chip["name"], chip.get("flag"))
    # literal chips first, then the rest, capped
    out.sort(key=lambda i: 0 if i["name"] in literal else 1)
    return out[:16]


@route("GET", "/api/embedcheck")
def embed_check(params, q, body):
    """v8.18 — can this article URL be shown in an in-app iframe? Most major
    news sites send X-Frame-Options / CSP frame-ancestors that BLOCK embedding,
    and the browser can't observe that from JS — so the backend checks the
    response headers and the embedded-article pane decides honestly: embed when
    allowed, show a clean "opens in a new tab" card when blocked. Unknown
    (network failure / no headers) returns embeddable=null → the pane tries the
    iframe with the fallback link alongside."""
    import urllib.request as _ur
    url = (q.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return 400, {"error": "url must be http(s)"}
    try:
        req = _ur.Request(url, method="HEAD", headers={
            "User-Agent": "GlobeGrid/8.18 (embed-check; single-user local app)"})
        with _ur.urlopen(req, timeout=6) as r:
            xfo = (r.headers.get("X-Frame-Options") or "").lower()
            csp = (r.headers.get("Content-Security-Policy") or "").lower()
            blocked = ("deny" in xfo or "sameorigin" in xfo
                       or "frame-ancestors" in csp)
            return 200, {"embeddable": not blocked,
                         "reason": ("x-frame-options/frame-ancestors present"
                                    if blocked else "no embed-blocking headers")}
    except Exception as exc:  # noqa: BLE001 — unknown, let the client try
        return 200, {"embeddable": None, "reason": f"{type(exc).__name__}"}


@route("GET", "/api/chains")
def lineage_chains(params, q, body):
    """v7.4.1 — dedicated lineage / connected-history chains for the stories
    directory (owner: "a dedicated lineage / chains tab"). Returns recent stories
    that carry a historical-chain link, each with the chain of past facts it
    reaches back to — the fact chain made browsable."""
    rows = query(
        "SELECT DISTINCT s.id, s.headline, s.last_updated_at"
        " FROM stories s JOIN story_members m ON m.story_id = s.id"
        " WHERE m.linked_via = 'historical_chain' AND s.is_synthetic = 0"
        " ORDER BY s.last_updated_at DESC LIMIT 40")
    chains = []
    for r in rows:
        hist = _connected_history(r["id"])
        if not hist:
            continue
        chains.append({"id": r["id"], "headline": r["headline"],
                       "last_updated_at": r["last_updated_at"],
                       "chain": hist[:8], "chain_len": len(hist)})
    return 200, {"chains": chains}


@route("GET", "/api/stories/{id}")
def story_detail(params, q, body):
    row = query_one("SELECT * FROM stories WHERE id = ?", (params["id"],))
    if row is None:
        return 404, {"error": "story not found"}
    d = _story_card(row)
    d["impacted"] = _impacted_entities(row["id"])   # v7.4.1
    events = _member_events(row["id"])
    d["members"] = events
    d["connected_history"] = _connected_history(row["id"])
    d["sources"] = _dedupe_sources(events)
    d["bias_view"] = _bias_view(events)
    d["predictions"] = [dict(r) for r in query(          # §3.4 scorecard
        "SELECT id, consequence_text, predicted_at, status, resolved_at"
        " FROM predictions WHERE story_id = ? ORDER BY predicted_at", (row["id"],))]
    # --- v3 additions ---
    from ..processing.debate import debate_for_story
    d["debate"] = debate_for_story(row["id"])            # v3 §2
    d["versions"] = [dict(r) | {"causal_narrative": json.loads(r["causal_narrative"])
                                if r["causal_narrative"] else None}
                     for r in query(                     # v3 §12
        "SELECT id, causal_narrative, confidence, superseded_at"
        " FROM story_narrative_versions WHERE story_id = ?"
        " ORDER BY superseded_at DESC LIMIT 10", (row["id"],))]
    if row["conflict_id"]:
        c = query_one("SELECT id, name FROM conflicts WHERE id = ?", (row["conflict_id"],))
        d["conflict"] = dict(c) if c else None
    if row["suggested_conflict_id"]:                     # v3 §15 confirm step
        c = query_one("SELECT id, name FROM conflicts WHERE id = ?",
                      (row["suggested_conflict_id"],))
        d["suggested_conflict"] = dict(c) if c else None
    from ..processing.forecast import forecast_accuracy   # v3 §7 — a forecast is
    forecasts = [dict(r) for r in query(                  # never shown without
        "SELECT id, consequence_text, predicted_at, status, horizon_hours, region"
        " FROM predictions WHERE story_id = ? AND kind = 'forward_forecast'"
        " ORDER BY predicted_at DESC", (row["id"],))]     # its track record
    d["forecasts"] = {"items": forecasts,
                      "accuracy": forecast_accuracy()} if forecasts else None
    # lineage entry points: fact ids of historical-chain members (v3 §8)
    d["second_order_links"] = [                          # §3.7
        {**row_to_dict(r, json_fields=("narrative",)),
         "other_story_id": r["story_b_id"] if r["story_a_id"] == row["id"] else r["story_a_id"],
         "other_headline": r["other_headline"]}
        for r in query(
            "SELECT l.*, s2.headline AS other_headline FROM second_order_links l"
            " JOIN stories s2 ON s2.id ="
            "   CASE WHEN l.story_a_id = ? THEN l.story_b_id ELSE l.story_a_id END"
            " WHERE l.story_a_id = ? OR l.story_b_id = ?",
            (row["id"], row["id"], row["id"]))]
    return 200, d


def _dedupe_sources(events: list[dict]) -> list[dict]:
    seen, out = set(), []
    for e in events:
        key = e["source"]["id"]
        if key not in seen:
            seen.add(key)
            out.append(e["source"])
    return out


def _bias_view(events: list[dict]) -> dict:
    """Section 5.7 — same story grouped by outlet leaning; v2 §3.5 adds
    computed tone alongside the static label."""
    groups = {"left": [], "center": [], "right": []}
    for e in events:
        leaning = e["source"]["leaning"]
        if leaning in groups:
            groups[leaning].append({"outlet": e["source"]["name"],
                                    "headline": e["title"],
                                    "link": e["source"]["article_link"],
                                    "sentiment": e.get("sentiment"),
                                    "kind": e["source"].get("kind", "reported")})
    return groups


@route("POST", "/api/stories/{id}/feedback")
def story_feedback(params, q, body):
    """v3 §5 — 'was this really the same story?' one-tap feedback."""
    if not isinstance(body, dict) or body.get("vote") not in ("correct", "incorrect"):
        return 400, {"error": "body must be {vote: correct|incorrect}"}
    story = query_one("SELECT id FROM stories WHERE id = ?", (params["id"],))
    if not story:
        return 404, {"error": "story not found"}
    cat = query_one(
        "SELECT e.category, COUNT(*) AS n FROM story_members m"
        " JOIN events e ON e.id = m.event_id WHERE m.story_id = ?"
        " GROUP BY e.category ORDER BY n DESC LIMIT 1", (params["id"],))
    category = cat["category"] if cat else "other"
    with write_tx() as conn:
        conn.execute("INSERT INTO correlation_feedback (id, story_id, category, vote,"
                     " voted_at) VALUES (?,?,?,?,?)",
                     (new_id(), params["id"], category, body["vote"], now_iso()))
    return 200, {"ok": True, "category": category}


@route("GET", "/api/predictions")
def predictions_view(params, q, body):
    from ..processing.predictions import scorecard
    recent = query(
        "SELECT p.*, s.headline FROM predictions p JOIN stories s ON s.id = p.story_id"
        " WHERE p.status != 'pending' ORDER BY p.resolved_at DESC LIMIT 50")
    return 200, {"scorecard": scorecard(),
                 "recent": [dict(r) for r in recent]}


@route("GET", "/api/briefings")
def briefings_view(params, q, body):
    # v6.1 — period is 'day' (default) | 'week' | 'month'; v6.6.2 adds 'market'
    period = q.get("period", "day")
    if period not in ("day", "week", "month", "market"):
        period = "day"
    from ..processing.briefing import (generate_briefing, generate_market_briefing,
                                       _period_key)
    if period == "market":   # v6.6.2 — dynamic market briefing, hourly cache
        key = _period_key("market")
        row = query_one("SELECT * FROM daily_briefings WHERE briefing_date = ?", (key,))
        if row is None and q.get("generate") == "1":
            return 200, {"briefing": generate_market_briefing(), "period": "market"}
        return 200, {"briefing": dict(row) if row else None, "period": "market"}
    if q.get("date"):
        row = query_one("SELECT * FROM daily_briefings WHERE briefing_date = ?",
                        (q["date"],))
    else:
        # target the current period's key so week/month don't fall back to a daily row
        key = _period_key(period)
        row = query_one("SELECT * FROM daily_briefings WHERE briefing_date = ?", (key,))
        if row is None:
            row = query_one(
                "SELECT * FROM daily_briefings WHERE briefing_date = ?"
                if period == "day" else
                "SELECT * FROM daily_briefings WHERE briefing_date LIKE ?"
                " ORDER BY briefing_date DESC LIMIT 1",
                (key if period == "day" else
                 (f"{key[:4]}-W%" if period == "week" else f"{key}%"),))
    if row is None and q.get("generate") == "1":
        return 200, {"briefing": generate_briefing(period=period), "period": period}
    return 200, {"briefing": dict(row) if row else None, "period": period}


@route("GET", "/api/watchlist")
def watchlist_get(params, q, body):
    return 200, {"items": [dict(r) for r in query(
        "SELECT * FROM watchlist_items ORDER BY created_at DESC")]}


@route("POST", "/api/watchlist")
def watchlist_add(params, q, body):
    if not isinstance(body, dict) or body.get("kind") not in ("entity", "region", "category") \
            or not body.get("value"):
        return 400, {"error": "body must be {kind: entity|region|category, value}"}
    with write_tx() as conn:
        conn.execute("INSERT OR IGNORE INTO watchlist_items (id, kind, value, created_at)"
                     " VALUES (?,?,?,?)",
                     (new_id(), body["kind"], body["value"].strip(), now_iso()))
    return 200, {"ok": True}


@route("POST", "/api/watchlist/delete")
def watchlist_delete(params, q, body):
    if not isinstance(body, dict) or not body.get("id"):
        return 400, {"error": "body must be {id}"}
    with write_tx() as conn:
        conn.execute("DELETE FROM watchlist_items WHERE id = ?", (body["id"],))
    return 200, {"ok": True}


@route("GET", "/api/search")
def search(params, q, body):
    """§6.4 — FTS5 across story headlines/summaries and fact who/what/where."""
    term = (q.get("q") or "").strip()
    if not term:
        return 400, {"error": "q parameter required"}
    if meta_get("fts_enabled") != "1":
        return 503, {"error": "full-text search unavailable (SQLite built without FTS5)"}
    fts_term = " ".join(f'"{t}"' for t in term.split()[:6])
    stories = query(
        "SELECT s.* FROM fts_stories f JOIN stories s ON s.id = f.id"
        " WHERE fts_stories MATCH ? ORDER BY rank LIMIT 20", (fts_term,))
    facts = query(
        'SELECT ef.id, ef.who, ef.what, ef."where" AS where_text, ef.when_occurred,'
        " ef.event_id, src.name AS src_name,"
        " (SELECT story_id FROM story_members m WHERE m.fact_id = ef.id"
        "   OR m.event_id = ef.event_id LIMIT 1) AS story_id"
        " FROM fts_facts f JOIN extracted_facts ef ON ef.id = f.id"
        " JOIN sources src ON src.id = ef.source_id"
        " WHERE fts_facts MATCH ? ORDER BY rank LIMIT 30", (fts_term,))
    return 200, {
        "stories": [_story_card(r) for r in stories],
        "facts": [{"id": r["id"], "who": r["who"], "what": r["what"],
                   "where": r["where_text"], "when_occurred": r["when_occurred"],
                   "source": r["src_name"], "story_id": r["story_id"]} for r in facts],
    }


@route("GET", "/api/graph")
def graph(params, q, body):
    """§6.3 — canonical entities as nodes, same-story co-occurrence as edges."""
    limit = min(int(q.get("limit", 60)), 200)
    rows = query(
        "SELECT f.canonical_entity_ids, m.story_id FROM story_members m"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE f.canonical_entity_ids IS NOT NULL")
    by_story: dict = {}
    for r in rows:
        by_story.setdefault(r["story_id"], set()).update(
            json.loads(r["canonical_entity_ids"]))
    freq: dict = {}
    edges: dict = {}
    for ents in by_story.values():
        ents = sorted(ents)
        for e in ents:
            freq[e] = freq.get(e, 0) + 1
        for i, a in enumerate(ents):
            for b in ents[i + 1:]:
                edges[(a, b)] = edges.get((a, b), 0) + 1
    top = sorted(freq, key=freq.get, reverse=True)[:limit]
    top_set = set(top)
    from ..processing.entities import entity_names
    names = entity_names(top)
    return 200, {
        "nodes": [{"id": e, "name": names.get(e, e), "weight": freq[e]} for e in top],
        "edges": [{"a": a, "b": b, "weight": w} for (a, b), w in edges.items()
                  if a in top_set and b in top_set],
    }


# v7 — backend translation scrapped by owner decision (the LLM-translation
# experiment never worked reliably on small local models; the owner will
# architect a replacement). The language picker + LANGUAGES list remain in the
# frontend (RTL/dir/wordmark only).
