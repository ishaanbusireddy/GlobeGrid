"""Stage 2 — extraction (v1 Sections 2.1, 5.4 step 1; v2 addendum §2, §3).

Turns each raw_items row into a normalized events record plus a structured
who/what/where/when extracted_facts row (the fact chain, Section 5.9).

v2 additions at this stage:
  - entities come from the NER layer (spaCy when installed, regex
    fallback — §3.2) and are canonicalized (§3.1) into
    extracted_facts.canonical_entity_ids;
  - per-article sentiment (§3.5) stored on the fact;
  - near-duplicate / wire-copy detection (§3.3): a new fact whose
    embedding is near-identical (>= near_duplicate_similarity_threshold)
    to a recent fact is marked duplicate_of_fact_id — kept forever (the
    chain is never trimmed) but excluded from instability volume and
    story member-counts;
  - process_pending() returns full event payloads so the scheduler can
    broadcast event_created the moment extraction lands (§2).

The normalized description used for embedding is entities + location +
action — deliberately NOT the raw headline — because raw text differs
wildly by source for the same underlying event (Section 5.4 step 1).
"""

import html
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from ..config import cfg
from ..db.models import new_id, now_iso, pack_embedding, unpack_embedding
from ..db.session import write_tx, query
from .embed import embed_text, cosine
from .entities import canonical_ids_json
from .gazetteer import geocode_text
from .ner import extract_entities
from .sentiment import score_text

log = logging.getLogger("extract")

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

CATEGORY_KEYWORDS = {
    "conflict": ["war", "attack", "strike", "missile", "troops", "military", "clash",
                 "offensive", "airstrike", "shelling", "insurgent", "ceasefire", "hostage",
                 "killed", "bombing", "drone", "combat", "invasion", "fighting"],
    "disaster": ["earthquake", "quake", "hurricane", "typhoon", "cyclone", "flood",
                 "wildfire", "tsunami", "volcano", "eruption", "landslide", "drought",
                 "storm", "tornado", "magnitude", "aftershock"],
    "finance": ["market", "stocks", "shares", "currency", "inflation", "interest rate",
                "central bank", "bond", "economy", "gdp", "trade", "tariff", "oil price",
                "recession", "earnings", "ipo", "crypto", "exports", "sanctions",
                # v4 §13.2 — central-bank / economic-release vocabulary so
                # these route cleanly into economic_agenda synthesis
                "rate decision", "monetary policy", "fomc", "rate cut", "rate hike",
                "basis points", "quantitative", "cpi", "unemployment rate", "payrolls",
                "stimulus", "fiscal", "debt ceiling", "imf", "world bank",
                # v6.6 — owner: too many finance events classifying as 'other'
                "stock market", "wall street", "nasdaq", "s&p 500", "dow jones",
                "federal reserve", "treasury", "bank of", "merger", "acquisition",
                "hedge fund", "private equity", "bankruptcy", "profit", "revenue",
                "quarterly results", "billion deal", "investors", "bailout",
                "currency devalu", "bond yield", "credit rating"],
    # v6.6/v8.13 — dedicated technology category. Short-token word-boundary
    # matching (_kw_hit) lets "ai" be a safe bare keyword now (\bai\b), so it no
    # longer needs the fragile " ai " space-padding that missed "AI." / "AI,".
    "technology": ["artificial intelligence", "ai", "a.i.", "openai", "anthropic", "chatgpt",
                   "semiconductor", "chipmaker", "nvidia", "software", "startup",
                   "silicon valley", "cyberattack", "cybersecurity", "data breach",
                   "ransomware", "hacking", "hacker", "quantum", "robotics", "spacex",
                   "satellite launch", "rocket launch", "smartphone", "data center",
                   "cloud computing", "5g network", "social media", "tech giant",
                   "microchip", "chip export", "machine learning", "autonomous vehicle",
                   "electric vehicle", "battery plant", "app store", "antitrust",
                   "algorithm", "encryption", "gadget", "operating system", "big tech"],
    # v8.13 — DOMESTIC: a country's internal politics/crime/civil life that is NOT
    # international geopolitics (owner: "add a domestic events category"). Deliberately
    # everyday-governance vocabulary so ordinary national news stops landing in
    # geopolitics or, worse, being conflict-tagged.
    # v8.16 — retuned per geopolitics/category_defs.py: domestic is "random
    # national news" — local crime/courts, SPORTS, entertainment/culture, civic
    # life. Macro-financial words and national-election words were REMOVED from
    # this list (they belong to finance/geopolitics), and the tie-break priority
    # now puts finance+geopolitics ABOVE domestic, per the owner: "not finance
    # related things or large level political news".
    "domestic": ["crime", "murder", "homicide", "shooting", "robbery", "arrest", "police",
                 "court ruling", "verdict", "lawsuit",
                 "scandal", "bribery", "cabinet reshuffle",
                 "healthcare bill", "welfare", "pension", "labor strike",
                 "teachers strike", "railway strike", "school", "university", "housing",
                 "wildfire evacuation", "local election", "by-election", "governor",
                 "mayor", "civil unrest", "riot",
                 "demonstration", "curfew", "public sector", "national holiday",
                 # sports — squarely domestic (owner)
                 "football", "soccer", "cricket", "olympics", "championship",
                 "tournament", "premier league", "world cup", "cup final", "nba",
                 "nfl", "mlb", "grand slam", "tennis", "golf", "formula 1", "f1 ",
                 "athlete", "stadium", "playoff", "medal", "goalkeeper", "striker",
                 "innings", "wicket", "derby win", "relegation", "transfer window",
                 # entertainment / culture / human interest
                 "box office", "film festival", "movie", "celebrity", "singer",
                 "album", "concert", "museum", "art exhibition", "heritage",
                 "lottery", "zoo", "theme park", "restaurant", "tourism boom"],
    # v8.13 — HEALTH: disease/pandemic/public-health (distinct from acute disaster).
    "health": ["pandemic", "epidemic", "outbreak", "virus", "covid", "influenza", "flu",
               "measles", "ebola", "cholera", "malaria", "vaccine", "vaccination",
               "who declares", "public health", "hospital", "disease", "infection",
               "quarantine", "mpox", "bird flu", "health emergency", "opioid", "fda approval"],
    "geopolitics": ["election", "president", "prime minister", "parliament", "treaty", "summit",
                    "diplomat", "embassy", "united nations", "nato", "coalition", "vote",
                    "referendum", "foreign policy", "talks", "agreement", "border dispute",
                    "sanctions", "alliance", "bilateral", "ambassador", "state visit",
                    # v8.16 — widen so cross-border stories stop falling to 'other'
                    "foreign minister", "minister", "opposition leader", "president-elect",
                    "peace deal", "peacekeeping", "annex", "sovereignty", "extradition",
                    "asylum", "refugee", "migrants", "deportation", "visa", "aid package",
                    "humanitarian aid", "war crimes", "icc", "geneva", "security council",
                    "european union", "brussels", "kremlin", "white house", "beijing",
                    "downing street", "delegation", "accord", "memorandum", "ratif"],
}

# v5 §3 — split the conflict bucket. 'military' = posturing/drills/deals
# that are tracked and shown but must NOT auto-populate a conflict tab;
# 'conflict' = literal war-scale developments (active fighting, territorial
# change, ceasefire/negotiation moves). Only conflict-category events get a
# development_type at all; everything else stays NULL.
MILITARY_DEV_KEYWORDS = [
    "test", "drill", "exercise", "war game", "wargame", "maneuver", "manoeuvre",
    "posturing", "deploys", "deployment", "arms deal", "weapons deal", "arms sale",
    "weapons sale", "unveils", "showcase", "parade", "buildup", "build-up",
    "reinforce", "patrol", "flyby", "fly-by", "show of force", "procurement",
    "missile test", "sea trial", "commission", "delivery of", "sells", "purchase",
]
CONFLICT_DEV_KEYWORDS = [
    "attack", "strike", "airstrike", "shelling", "bombing", "offensive", "assault",
    "invasion", "advance", "captured", "seized", "recaptured", "ceasefire", "truce",
    "negotiation", "peace talks", "killed", "casualties", "front line", "frontline",
    "besieged", "siege", "counteroffensive", "withdrawal", "retreat", "clashes",
]

SEVERITY_KEYWORDS = {
    5: ["war declared", "nuclear", "invasion", "major earthquake", "hundreds killed",
        "thousands killed", "catastroph", "collapse of government", "coup"],
    4: ["killed", "dead", "explosion", "crash", "state of emergency", "evacuat",
        "airstrike", "missile", "assassin", "default", "crisis"],
    3: ["injured", "protest", "sanction", "sell-off", "plunge", "clash", "outbreak",
        "wildfire", "flood", "strike action"],
    2: ["warns", "tension", "dispute", "downgrade", "recall", "delay", "shortage"],
}


def strip_html(text: str) -> str:
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", text or ""))).strip()


# v7.4.1 — categorization accuracy pass (owner: "improve the accuracy of event/
# story categorization"). Two problems fixed here:
#  (1) naive substring matching produced false positives — "war" hit "warning"/
#      "toward"/"warm", "market" hit "supermarket", "coup" hit "couple". Short
#      keywords (<=5 chars, single word) now require WORD BOUNDARIES.
#  (2) raw hit-count ties defaulted arbitrarily. A fixed priority breaks ties so
#      unambiguous categories (disaster, conflict) win over the catch-all.
import re as _re

# v8.13 — tie-break priority, most-specific first. Technology now sits ABOVE
# finance (the owner's "tech keeps classifying as finance/geopolitics" bug: a
# tech+markets story like "Nvidia earnings jump on AI demand" tied finance vs
# technology and finance won on both count and priority — now technology wins the
# tie). health/domestic slot above finance/geopolitics so a disease outbreak or
# an internal-affairs story isn't swept into the catch-all geopolitics bucket.
# v8.16 — domestic moved BELOW finance and geopolitics (owner: domestic must
# be "random national news … not finance related things or large level
# political news" — on a tie, the macro category wins; sports/culture words
# only ever hit the domestic list, so real domestic stories still land there).
# The full normative definition of every category lives in
# geopolitics/category_defs.py — that file wins any dispute.
_CAT_PRIORITY = ["disaster", "conflict", "health", "technology",
                 "finance", "geopolitics", "domestic"]
# a small compiled word-boundary matcher cache for short single-word keywords
_WB_CACHE: dict[str, "_re.Pattern"] = {}


def _kw_hit(keyword: str, lowered: str) -> bool:
    kw = keyword.strip()
    # multi-word phrases: a plain substring is specific enough
    if " " in kw:
        return kw in lowered
    # v8.14 — EVERY single-word keyword gets word boundaries, not just short
    # ones. The old `len(kw) > 5 → substring` shortcut let "market" (6 chars)
    # hit "supermarket" — the exact bug the boundary rule was added for in
    # v7.4.1, silently regressed by the length gate; caught by
    # backend/tests/test_classify.py.
    pat = _WB_CACHE.get(kw)
    if pat is None:
        pat = _re.compile(r"\b" + _re.escape(kw) + r"\b")
        _WB_CACHE[kw] = pat
    return bool(pat.search(lowered))


def classify_category(text: str) -> str:
    lowered = text.lower()
    scores = {}
    for cat, words in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for w in words if _kw_hit(w, lowered))
    best_hits = max(scores.values()) if scores else 0
    if best_hits == 0:
        return "other"
    # among the top-scorers, pick the highest-priority category (deterministic)
    top = [c for c, n in scores.items() if n == best_hits]
    for cat in _CAT_PRIORITY:
        if cat in top:
            return cat
    return top[0]


def classify_severity(text: str) -> int:
    lowered = text.lower()
    for level in (5, 4, 3, 2):
        if any(w in lowered for w in SEVERITY_KEYWORDS[level]):
            return level
    return 1


def classify_development_type(text: str, category: str) -> str | None:
    """v5 §3 — for conflict-category events, distinguish literal war-scale
    'conflict' from 'military' posturing/drills/deals. Non-conflict events
    return None (the column stays NULL). When both vocabularies hit,
    conflict wins — active fighting outranks posturing."""
    if category != "conflict":
        return None
    lowered = text.lower()
    conflict_hit = sum(1 for w in CONFLICT_DEV_KEYWORDS if w in lowered)
    military_hit = sum(1 for w in MILITARY_DEV_KEYWORDS if w in lowered)
    if conflict_hit == 0 and military_hit == 0:
        return "conflict"   # conflict-category with no posturing cue defaults to conflict
    return "conflict" if conflict_hit >= military_hit else "military"


def normalize_action(title: str) -> str:
    words = re.findall(r"[a-zA-Z0-9%$.-]+", (title or "").lower())
    return " ".join(words[:24])


def parse_timestamp(value) -> str:
    """Best-effort parse of RSS/API timestamps to ISO-8601 Z."""
    if not value:
        return now_iso()
    value = str(value).strip()
    try:  # unix epoch
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z")
    except (ValueError, OSError, OverflowError):
        pass
    from email.utils import parsedate_to_datetime
    try:  # RFC 2822 (RSS pubDate)
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z")
    except (ValueError, TypeError):
        pass
    try:  # ISO
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except ValueError:
        return now_iso()


def build_normalized_item(payload: dict) -> dict:
    """Source adapters store a pre-normalized envelope in raw_content; this
    turns it into event/fact fields. Envelope keys: title, summary, link,
    published, plus optional lat/lon/location_name/category/severity/who/
    what that structured sources (USGS, FIRMS, GDELT Events, market) set
    directly."""
    title = strip_html(payload.get("title", ""))[:300] or "(untitled item)"
    summary = strip_html(payload.get("summary", ""))[:600]
    text = f"{title}. {summary}"

    # v6 §10 — local-language reporting is translated to English at INGESTION
    # time so entity extraction, geocoding, classification and the correlation
    # embedding all compare meaning rather than scripts (feeds v3 §4's
    # cross-lingual matching). The ORIGINAL title stays on the item for
    # display and citation; display-time translation is §11's separate path.
    # Degrades to the original text when no provider is configured.
    from .translate import to_english_for_correlation
    text = to_english_for_correlation(text)

    entities = extract_entities(text)
    who = payload.get("who") or ("; ".join(entities[:4]) if entities else "unattributed")
    action = payload.get("what") or normalize_action(title)

    # v4 §3.1 — explicit geocode confidence: structured source coords score
    # highest, exact gazetteer city match next, country-level centroid low.
    # The map must never imply more precision than the resolution has.
    geocode_confidence = None
    if payload.get("lat") is not None and payload.get("lon") is not None:
        loc = (payload.get("location_name") or "unknown", payload["lat"], payload["lon"])
        geocode_confidence = 0.95
    else:
        loc = geocode_text(text)
        if loc:
            geocode_confidence = 0.55 if _is_country_level(loc[0]) else 0.8
    location_name = loc[0] if loc else None

    # entities + location + action (Section 5.4 step 1)
    description = " | ".join(p for p in (who, location_name or "", action) if p)

    category = payload.get("category") or classify_category(text)
    return {
        "title": title,
        "description": description,
        "lat": loc[1] if loc else None,
        "lon": loc[2] if loc else None,
        "location_name": location_name,
        "category": category,
        "severity": int(payload.get("severity") or classify_severity(text)),
        "occurred_at": parse_timestamp(payload.get("published")),
        "who": who,
        "what": action,
        "link": payload.get("link", ""),
        "entities": entities,
        "sentiment": round(score_text(text), 4),
        "geocode_confidence": geocode_confidence,
        # v5 §3 — conflict vs military-development split
        "development_type": payload.get("development_type")
        or classify_development_type(text, category),
    }


def _is_country_level(place_name: str | None) -> bool:
    """Country/region centroid resolutions are real but imprecise (§3.1)."""
    from .gazetteer import PLACES
    return bool(place_name) and place_name.lower() in PLACES


_ENTITY_NAME_CACHE: dict = {"at": 0.0, "names": set()}


def _known_entity_names() -> set:
    """Lowercased names of tracked countries/orgs/NSAs/conflicts, cached
    5 min — the §9.1 'linked to the entity layer beyond a place name' signal."""
    import time
    if time.time() - _ENTITY_NAME_CACHE["at"] > 300:
        names = set()
        for sql in ("SELECT name FROM countries",
                    "SELECT name FROM international_organizations",
                    "SELECT name FROM non_state_actors",
                    "SELECT name FROM alliances"):
            try:
                names.update(r["name"].lower() for r in query(sql))
            except Exception:  # noqa: BLE001 — entity layer not seeded yet
                pass
        _ENTITY_NAME_CACHE.update(at=time.time(), names=names)
    return _ENTITY_NAME_CACHE["names"]


# v6 §2 — gdelt types removed with the sources themselves; historical GDELT
# facts keep their stored relevance scores, nothing recomputes for them
BROAD_SCOPE_SOURCE_TYPES = {"usgs", "market", "firms",
                            "volcano", "opensky", "acled"}


def global_relevance(item: dict, source_type: str, source_kind: str) -> float:
    """v4 §9.1 — 0-1 relevance of an event to a global-geopolitics tool,
    from three concrete signals: entity-layer linkage beyond a place name,
    severity floor, and the source's typical scope."""
    score = 0.15
    known = _known_entity_names()
    text = f"{item['title']} {item['who']}".lower()
    if any(n in text for n in known if len(n) > 3):
        score += 0.35
    sev = item.get("severity") or 1
    if sev >= 3:
        score += 0.2
    if sev >= 4:
        score += 0.1
    if source_type in BROAD_SCOPE_SOURCE_TYPES or source_kind == "official":
        score += 0.2
    elif source_type in ("rss", "wikipedia", "wiki_views"):
        score += 0.1
    # v6.6.4 — hard-penalize US sports and obscure local-interest items that
    # carry no global connection (owner: "idw hear abt some Denver Broncos bs";
    # "filter obscure US local news, like some random individual death"). Push
    # them below the default relevance floor unless a real global entity is
    # named (that entity boost above still applies and can rescue a rare case).
    if _is_low_global_interest(text) and not any(
            n in text for n in known if len(n) > 3):
        score = min(score, 0.12)
    return round(min(1.0, score), 3)


# sports leagues/teams + local-blotter markers that shouldn't reach a global
# geopolitics feed on their own
_SPORTS_TERMS = (
    "nfl", "nba", "mlb", "nhl", "ncaa", "super bowl", "playoff", "touchdown",
    "quarterback", "home run", "world series", "stanley cup", "march madness",
    "broncos", "cowboys", "packers", "lakers", "yankees", "red sox", "celtics",
    "premier league fixture", "box score", "final score", "coach fired",
    "draft pick", "free agent", "mvp award", "wide receiver", "point guard",
)
_LOCAL_BLOTTER_TERMS = (
    "obituary", "local man", "local woman", "high school", "county fair",
    "city council votes to", "found dead in", "car crash on", "house fire",
    "lottery winner", "missing dog", "weather forecast for", "road closure",
    "traffic accident", "shooting at a", "arrested for dui",
)


def _is_low_global_interest(text: str) -> bool:
    return (any(t in text for t in _SPORTS_TERMS)
            or any(t in text for t in _LOCAL_BLOTTER_TERMS))


def _find_near_duplicate(vec, occurred_at: str) -> str | None:
    """§3.3 — wire-copy check against the recent same-window fact pool."""
    threshold = float(cfg("correlation", "near_duplicate_similarity_threshold"))
    gap_hours = float(cfg("correlation", "same_window_max_gap_hours"))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=gap_hours)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    rows = query(
        "SELECT id, embedding FROM extracted_facts"
        " WHERE is_synthetic = 0 AND embedding IS NOT NULL"
        " AND duplicate_of_fact_id IS NULL AND created_at >= ?"
        " ORDER BY created_at DESC LIMIT 1500", (cutoff,))
    for row in rows:
        if cosine(vec, unpack_embedding(row["embedding"])) >= threshold:
            return row["id"]
    return None


def process_pending(limit: int = 200) -> list[dict]:
    """Run Stage 2 + 3 on unprocessed raw items. Returns one payload dict
    per new event (for the §2 event_created broadcast). Each item is
    wrapped in its own error boundary (Section 2.3)."""
    rows = query(
        "SELECT r.id, r.source_id, r.raw_content, s.name AS src_name, s.kind AS src_kind,"
        " s.type AS src_type"
        " FROM raw_items r JOIN sources s ON s.id = r.source_id"
        " WHERE r.processed = 0 ORDER BY r.fetched_at LIMIT ?", (limit,))
    new_events = []
    for row in rows:
        try:
            # v7.4.1 — GDELT is permanently banned: never extract an event from a
            # GDELT-typed source even if a stray raw_item slipped in. Mark it
            # processed so it's skipped forever without ever entering the chain.
            _st = (row["src_type"] or "").lower()
            _sn = (row["src_name"] or "").lower()
            if _st in ("gdelt", "gdelt_events") or "gdelt" in _sn:
                with write_tx() as conn:
                    conn.execute("UPDATE raw_items SET processed = 1 WHERE id = ?",
                                 (row["id"],))
                continue
            payload = json.loads(row["raw_content"])
            item = build_normalized_item(payload)
            vec = embed_text(item["description"])
            emb = pack_embedding(vec)
            duplicate_of = _find_near_duplicate(vec, item["occurred_at"])
            canonical_ids = canonical_ids_json(item["entities"])
            event_id, fact_id = new_id(), new_id()
            created_at = now_iso()
            # v3 §11 — hash-chained provenance on every fact insert
            from .provenance import next_hashes
            row_hash, prev_hash = next_hashes("extracted_facts", {
                "id": fact_id, "event_id": event_id, "source_id": row["source_id"],
                "who": item["who"], "what": item["what"], "where": item["location_name"],
                "when_occurred": item["occurred_at"], "created_at": created_at})
            relevance = global_relevance(item, row["src_type"], row["src_kind"])
            # v8 §4 — resolve the event to the ADM1 unit it lands in (province/
            # state), so its coverage surfaces on that unit's page and the
            # same-unit correlation boost can fire. Best-effort: a geocode with
            # no lat/lon, or a resolution hiccup, simply leaves admin_uid NULL.
            admin_uid = None
            if item["lat"] is not None and item["lon"] is not None:
                try:
                    from ..geopolitics.admin_atlas import unit_at as _unit_at
                    admin_uid = _unit_at(item["lat"], item["lon"])
                except Exception:  # noqa: BLE001 — never block ingestion on this
                    admin_uid = None
            with write_tx() as conn:
                conn.execute(
                    "INSERT INTO events (id, raw_item_id, title, description, location_lat,"
                    " location_lon, location_name, category, severity, occurred_at, embedding,"
                    " geocode_confidence, global_relevance_score, development_type, admin_uid)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (event_id, row["id"], item["title"], item["description"], item["lat"],
                     item["lon"], item["location_name"], item["category"], item["severity"],
                     item["occurred_at"], emb, item["geocode_confidence"], relevance,
                     item["development_type"], admin_uid))
                conn.execute(
                    'INSERT INTO extracted_facts (id, event_id, source_id, who, what, "where",'
                    " when_occurred, embedding, created_at, canonical_entity_ids,"
                    " duplicate_of_fact_id, sentiment, row_hash, prev_hash)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (fact_id, event_id, row["source_id"], item["who"], item["what"],
                     item["location_name"], item["occurred_at"], emb, created_at,
                     canonical_ids, duplicate_of, item["sentiment"], row_hash, prev_hash))
                conn.execute("UPDATE raw_items SET processed = 1 WHERE id = ?", (row["id"],))
            if duplicate_of:
                log.info("near_duplicate", extra={"data": {"fact_id": fact_id,
                                                           "duplicate_of": duplicate_of}})
            new_events.append({
                "event_id": event_id,
                "fact_id": fact_id,
                "duplicate": bool(duplicate_of),
                "ws_payload": {
                    "id": event_id, "title": item["title"],
                    "category": item["category"], "severity": item["severity"],
                    "occurred_at": item["occurred_at"],
                    "location": ({"lat": item["lat"], "lon": item["lon"]}
                                 if item["lat"] is not None else None),
                    "location_name": item["location_name"],
                    "geocode_confidence": item["geocode_confidence"],
                    "global_relevance_score": relevance,
                    "development_type": item["development_type"],
                    "source": {"name": row["src_name"], "kind": row["src_kind"]},
                    "story_id": None,
                },
            })
        except Exception as exc:  # noqa: BLE001 — Stage 2 failure is per-item
            log.warning("extract_failed", extra={"data": {"raw_item_id": row["id"],
                                                          "error": str(exc)}})
            with write_tx() as conn:
                conn.execute(
                    "UPDATE raw_items SET processed = 1, processing_error = ? WHERE id = ?",
                    (str(exc)[:500], row["id"]))
    return new_events
