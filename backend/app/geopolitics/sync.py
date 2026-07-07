"""v3 §13.2/§14/§23 + §10.2 — slow-refresh sync jobs.

Two different update models, deliberately not conflated (§13.2):
slow-changing reference facts refresh from free structured APIs (Wikidata
leadership weekly, World Bank trade monthly, CelesTrak TLEs daily);
agendas/stances are AI-synthesized elsewhere (synthesis.py). A completed
election immediately triggers a one-off leadership refresh for that
country (§23.1). Every job degrades gracefully offline.
"""

import json
import logging
import urllib.parse

from ..config import cfg
from ..db.models import meta_get, meta_set, now_iso
from ..db.session import query, write_tx
from ..ingestion.http import fetch_url

log = logging.getLogger("geo_sync")

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WORLDBANK_API = "https://api.worldbank.org/v2/country/{iso3}/indicator/NY.GDP.MKTP.CD"
CELESTRAK_TLE = ("https://celestrak.org/NORAD/elements/gp.php"
                 "?GROUP=stations&FORMAT=tle")

LEADERSHIP_QUERY = """
SELECT ?iso3 ?role ?personLabel ?partyLabel ?image WHERE {
  VALUES ?iso3 { %s }
  ?country wdt:P298 ?iso3 .
  { ?country wdt:P35 ?person . BIND("head_of_state" AS ?role) }
  UNION
  { ?country wdt:P6 ?person . BIND("head_of_government" AS ?role) }
  OPTIONAL { ?person wdt:P102 ?party . }
  OPTIONAL { ?person wdt:P18 ?image . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""

# v4 §5.1 — the completeness fix is a full sync against Wikidata's
# sovereign-state query, not a bigger hand-curated list
SOVEREIGN_QUERY = """
SELECT DISTINCT ?iso3 ?iso2 ?countryLabel ?capitalLabel WHERE {
  ?country wdt:P31 wd:Q3624078 ; wdt:P298 ?iso3 .
  OPTIONAL { ?country wdt:P297 ?iso2 . }
  OPTIONAL { ?country wdt:P36 ?capital . }
  FILTER NOT EXISTS { ?country wdt:P576 ?dissolved . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""

# v4 §5.1 — alliance rosters queried from Wikidata membership data
# (manual transcription is precisely how the Baltics got dropped)
ALLIANCE_QIDS = {
    "NATO": "Q7184", "European Union": "Q458", "ASEAN": "Q7768",
    "African Union": "Q7159", "OPEC": "Q7795", "CSTO": "Q1520204",
    "BRICS": "Q47722", "G7": "Q170481",
}
MEMBERSHIP_QUERY = """
SELECT ?iso3 WHERE {
  ?country wdt:P463 wd:%s ; wdt:P298 ?iso3 .
}"""


def refresh_leadership(iso3_list: list[str] | None = None) -> int:
    """Weekly Wikidata sync (§13.2); or targeted after an election (§23.1)."""
    if iso3_list is None:
        iso3_list = [r["id"] for r in query("SELECT id FROM countries")]
    if not iso3_list:
        return 0
    values = " ".join(f'"{c}"' for c in iso3_list[:100])
    q = urllib.parse.urlencode({"query": LEADERSHIP_QUERY % values, "format": "json"})
    body = fetch_url(f"{WIKIDATA_SPARQL}?{q}",
                     headers={"Accept": "application/sparql-results+json"}, timeout=60)
    data = json.loads(body)
    updated = 0
    with write_tx() as conn:
        for b in data.get("results", {}).get("bindings", []):
            iso3 = b["iso3"]["value"]
            role = b["role"]["value"]
            name = b.get("personLabel", {}).get("value")
            party = b.get("partyLabel", {}).get("value")
            image = b.get("image", {}).get("value")  # v4 §6.1 header photo
            if not name or name.startswith("Q"):  # unresolved label
                continue
            conn.execute(
                "INSERT INTO country_leadership (country_id, role, name, party,"
                " last_refreshed_at, image_url) VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(country_id, role) DO UPDATE SET"
                "   name = excluded.name, party = excluded.party,"
                "   last_refreshed_at = excluded.last_refreshed_at,"
                "   image_url = COALESCE(excluded.image_url, image_url)",
                (iso3, role, name, party, now_iso(), image))
            updated += 1
    log.info("wikidata_leadership_synced", extra={"data": {"rows": updated}})
    return updated


def refresh_trade_stats() -> int:
    """Monthly World Bank GDP snapshot (§13.2 — free, no key)."""
    updated = 0
    for r in query("SELECT id FROM countries"):
        iso3 = r["id"]
        try:
            body = fetch_url(WORLDBANK_API.format(iso3=iso3)
                             + "?format=json&per_page=1&mrnev=1", timeout=20)
            data = json.loads(body)
            point = data[1][0] if isinstance(data, list) and len(data) > 1 and data[1] else None
            if not point or point.get("value") is None:
                continue
            with write_tx() as conn:
                conn.execute(
                    "INSERT INTO country_trade_stats (country_id, gdp_usd, as_of_date)"
                    " VALUES (?,?,?)"
                    " ON CONFLICT(country_id) DO UPDATE SET"
                    "   gdp_usd = excluded.gdp_usd, as_of_date = excluded.as_of_date",
                    (iso3, float(point["value"]), str(point.get("date", ""))))
            updated += 1
        except Exception:  # noqa: BLE001 — per-country isolation
            continue
    log.info("worldbank_trade_synced", extra={"data": {"rows": updated}})
    return updated


def election_triggered_refreshes() -> int:
    """§23.1 — a completed election is exactly when leadership is stale."""
    if not cfg("geopolitical_entities", "election_triggered_leadership_refresh"):
        return 0
    due = query("SELECT id, country_id FROM elections"
                " WHERE status = 'completed' AND leadership_refreshed = 0")
    refreshed = 0
    for e in due:
        try:
            refresh_leadership([e["country_id"]])
            refreshed += 1
        except Exception as exc:  # noqa: BLE001 — offline: retry next cycle
            log.warning("election_refresh_failed", extra={"data": {
                "country": e["country_id"], "error": str(exc)}})
            continue
        with write_tx() as conn:
            conn.execute("UPDATE elections SET leadership_refreshed = 1 WHERE id = ?",
                         (e["id"],))
    return refreshed


def refresh_tles() -> int:
    """v3 §10.2 — daily TLE fetch from CelesTrak, cached in app_meta for the
    frontend's client-side propagation."""
    body = fetch_url(CELESTRAK_TLE, timeout=45).decode("utf-8", errors="replace")
    lines = [ln.rstrip() for ln in body.splitlines() if ln.strip()]
    sats = []
    for i in range(0, len(lines) - 2, 3):
        name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            sats.append({"name": name.strip(), "l1": l1, "l2": l2})
    if sats:
        meta_set("tle_data", json.dumps({"fetched_at": now_iso(), "satellites": sats[:60]}))
        log.info("tle_refreshed", extra={"data": {"satellites": len(sats[:60])}})
    return len(sats)


def suggest_conflict_tags() -> int:
    """§15.1 — auto-suggestion, not full automation: when a recent story
    shares canonical entities with a conflict's registered parties, suggest
    the tag (one-click confirm in the UI) rather than silently assigning."""
    floor = float(cfg("geopolitical_entities", "conflict_autotag_confidence_floor"))
    # party canonical-entity ids per conflict (NSAs carry them directly;
    # countries match via their canonical entity if one exists by name)
    from ..processing.entities import resolve_entity
    conflict_ents: dict[str, set] = {}
    for row in query(
            "SELECT cp.conflict_id, cp.party_type, cp.country_id, n.canonical_entity_id,"
            " c.name AS country_name FROM conflict_parties cp"
            " LEFT JOIN non_state_actors n ON n.id = cp.non_state_actor_id"
            " LEFT JOIN countries c ON c.id = cp.country_id"):
        ents = conflict_ents.setdefault(row["conflict_id"], set())
        if row["canonical_entity_id"]:
            ents.add(row["canonical_entity_id"])
        elif row["country_name"]:
            cent = resolve_entity(row["country_name"])
            if cent:
                ents.add(cent)
    suggested = 0
    stories = query(
        "SELECT s.id FROM stories s WHERE s.is_synthetic = 0 AND s.conflict_id IS NULL"
        " AND s.suggested_conflict_id IS NULL"
        " AND s.last_updated_at >= datetime('now', '-3 day') LIMIT 50")
    for s in stories:
        story_ents: set = set()
        for f in query("SELECT f.canonical_entity_ids FROM story_members m"
                       " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
                       " WHERE m.story_id = ? AND f.canonical_entity_ids IS NOT NULL",
                       (s["id"],)):
            story_ents.update(json.loads(f["canonical_entity_ids"]))
        if not story_ents:
            continue
        best_conflict, best_conf = None, 0.0
        for cid, ents in conflict_ents.items():
            matches = len(story_ents & ents)
            if matches == 0:
                continue
            confidence = min(1.0, 0.6 + 0.15 * matches)
            if confidence > best_conf:
                best_conflict, best_conf = cid, confidence
        if best_conflict and best_conf >= floor:
            with write_tx() as conn:
                conn.execute("UPDATE stories SET suggested_conflict_id = ? WHERE id = ?",
                             (best_conflict, s["id"]))
            suggested += 1
    if suggested:
        log.info("conflict_tags_suggested", extra={"data": {"count": suggested}})
    return suggested


# ===== v4 additions =====

def sync_countries_from_wikidata() -> int:
    """v4 §5.1 — completeness guarantee: pull the full sovereign-state list
    and add anything the seed missed (never deletes; status defaults to
    un_member and can be curated). Degrades cleanly offline."""
    q = urllib.parse.urlencode({"query": SOVEREIGN_QUERY, "format": "json"})
    body = fetch_url(f"{WIKIDATA_SPARQL}?{q}",
                     headers={"Accept": "application/sparql-results+json"}, timeout=90)
    data = json.loads(body)
    have = {r["id"] for r in query("SELECT id FROM countries")}
    added = 0
    with write_tx() as conn:
        for b in data.get("results", {}).get("bindings", []):
            iso3 = b["iso3"]["value"].upper()
            if iso3 in have or len(iso3) != 3:
                continue
            name = b.get("countryLabel", {}).get("value") or iso3
            if name.startswith("Q"):
                continue
            conn.execute(
                "INSERT OR IGNORE INTO countries (id, name, capital, iso2, status,"
                " boundary_ref, last_updated_at) VALUES (?,?,?,?,?,?,?)",
                (iso3, name, b.get("capitalLabel", {}).get("value"),
                 b.get("iso2", {}).get("value"), "un_member", iso3, now_iso()))
            added += 1
            have.add(iso3)
    if added:
        log.info("wikidata_countries_added", extra={"data": {"added": added}})
    from .seed import check_completeness
    check_completeness()
    return added


def sync_alliance_memberships() -> int:
    """v4 §5.1 — alliance rosters from Wikidata's actual membership data,
    additive (curated rosters remain; missing members get filled in)."""
    added = 0
    for name, qid in ALLIANCE_QIDS.items():
        row = query("SELECT id FROM alliances WHERE name = ?", (name,))
        if not row:
            continue
        aid = row[0]["id"]
        try:
            q = urllib.parse.urlencode({"query": MEMBERSHIP_QUERY % qid,
                                        "format": "json"})
            body = fetch_url(f"{WIKIDATA_SPARQL}?{q}",
                             headers={"Accept": "application/sparql-results+json"},
                             timeout=60)
            data = json.loads(body)
        except Exception as exc:  # noqa: BLE001 — per-alliance isolation
            log.warning("alliance_sync_failed", extra={"data": {
                "alliance": name, "error": str(exc)[:120]}})
            continue
        with write_tx() as conn:
            for b in data.get("results", {}).get("bindings", []):
                iso3 = b["iso3"]["value"].upper()
                if not query("SELECT 1 FROM countries WHERE id = ?", (iso3,)):
                    continue
                cur = conn.execute(
                    "INSERT OR IGNORE INTO alliance_memberships (alliance_id, country_id)"
                    " VALUES (?,?)", (aid, iso3))
                added += cur.rowcount
            conn.execute("UPDATE alliances SET last_updated_at = ? WHERE id = ?",
                         (now_iso(), aid))
    if added:
        log.info("alliance_memberships_synced", extra={"data": {"added": added}})
    return added


WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"

# Wikipedia article-title overrides where the entity name alone is ambiguous
_WIKI_TITLE_OVERRIDES = {
    "Georgia": "Georgia (country)",
    "Renaissance": "Renaissance (French political party)",
    "Morena": "National Regeneration Movement",
    "CDU": "Christian Democratic Union of Germany",
    "SPD": "Social Democratic Party of Germany",
}


def refresh_background_content() -> int:
    """v4 §7 — background knowledge (Wikipedia primary) cached per entity
    on the slow reference-data cadence. Grokipedia is OPEN per the manual:
    no official API exists, so it stays behind external_content.
    grokipedia_enabled = false and is skipped unless flipped on."""
    if not cfg("external_content", "wikipedia_enabled"):
        return 0
    per_cycle = int(cfg("external_content", "entities_per_cycle"))
    interval_h = float(cfg("external_content", "refresh_interval_hours"))

    targets: list[tuple[str, str, str]] = []   # (entity_type, entity_id, title)
    for r in query("SELECT id, name FROM countries"):
        targets.append(("country", r["id"], r["name"]))
    for r in query("SELECT id, name FROM political_parties"):
        targets.append(("party", r["id"], r["name"].split(" (")[0]))
    for r in query("SELECT id, name FROM non_state_actors"):
        targets.append(("non_state_actor", r["id"], r["name"].split(" (")[0]))
    for r in query("SELECT id, name FROM international_organizations"):
        targets.append(("org", r["id"], r["name"]))
    for r in query("SELECT id, name FROM notable_persons"):
        targets.append(("person", r["id"], r["name"]))
    for r in query("SELECT id, name FROM conflicts"):
        targets.append(("conflict", r["id"], r["name"]))

    fresh = {(r["entity_type"], r["entity_id"]) for r in query(
        "SELECT entity_type, entity_id FROM entity_background"
        " WHERE origin = 'wikipedia' AND fetched_at >= datetime('now', ?)",
        (f"-{interval_h} hour",))}
    done = 0
    for etype, eid, title in targets:
        if done >= per_cycle:
            break
        if (etype, eid) in fresh:
            continue
        wiki_title = _WIKI_TITLE_OVERRIDES.get(title, title)
        try:
            body = fetch_url(WIKIPEDIA_SUMMARY
                             + urllib.parse.quote(wiki_title.replace(" ", "_")),
                             headers={"Accept": "application/json"}, timeout=20)
            data = json.loads(body)
        except Exception:  # noqa: BLE001 — per-entity isolation; retry next cycle
            continue
        extract = data.get("extract")
        if not extract or data.get("type") == "disambiguation":
            continue
        url = (data.get("content_urls", {}).get("desktop", {}) or {}).get("page")
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO entity_background (id, entity_type, entity_id, origin,"
                " title, extract, url, fetched_at) VALUES (?,?,?,?,?,?,?,?)"
                " ON CONFLICT(entity_type, entity_id, origin) DO UPDATE SET"
                "   title = excluded.title, extract = excluded.extract,"
                "   url = excluded.url, fetched_at = excluded.fetched_at",
                (__import__("uuid").uuid4().hex, etype, eid, "wikipedia",
                 data.get("title"), extract[:2400], url, now_iso()))
        done += 1
    if done:
        log.info("background_content_refreshed", extra={"data": {"entities": done}})
    return done


def fetch_background_now(entity_type: str, entity_id: str) -> dict | None:
    """v6.2 — INSTANT background: fetch one entity's Wikipedia summary on
    demand and cache it, instead of waiting for the slow weekly reference
    cadence. Called by the /api/background route when the entity_background
    table has no Wikipedia row yet for the requested entity. Best-effort:
    returns the cached row dict on success, None if offline/unresolvable."""
    if not cfg("external_content", "wikipedia_enabled"):
        return None
    name = None
    for tbl, split in (("countries", False), ("political_parties", True),
                       ("non_state_actors", True),
                       ("international_organizations", False),
                       ("notable_persons", False), ("conflicts", False)):
        r = query(f"SELECT name FROM {tbl} WHERE id = ?", (entity_id,))
        if r:
            name = r[0]["name"]
            if split:
                name = name.split(" (")[0]
            break
    if not name:
        return None
    wiki_title = _WIKI_TITLE_OVERRIDES.get(name, name)
    try:
        body = fetch_url(WIKIPEDIA_SUMMARY
                         + urllib.parse.quote(wiki_title.replace(" ", "_")),
                         headers={"Accept": "application/json"}, timeout=12)
        data = json.loads(body)
    except Exception:  # noqa: BLE001 — offline/blocked; caller degrades cleanly
        return None
    extract = data.get("extract")
    if not extract or data.get("type") == "disambiguation":
        return None
    url = (data.get("content_urls", {}).get("desktop", {}) or {}).get("page")
    row = {"origin": "wikipedia", "title": data.get("title"),
           "extract": extract[:2400], "url": url, "fetched_at": now_iso()}
    with write_tx() as conn:
        conn.execute(
            "INSERT INTO entity_background (id, entity_type, entity_id, origin,"
            " title, extract, url, fetched_at) VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(entity_type, entity_id, origin) DO UPDATE SET"
            "   title = excluded.title, extract = excluded.extract,"
            "   url = excluded.url, fetched_at = excluded.fetched_at",
            (__import__("uuid").uuid4().hex, entity_type, entity_id, "wikipedia",
             row["title"], row["extract"], row["url"], row["fetched_at"]))
    return row


# v6 §2 — the GDELT-backed historical_backfill job is gone with GDELT itself.
# Conflict context now accumulates from the broader v5/v6 source list; the
# 'backfilled_conflicts' meta key is left in place so a downgrade never
# re-runs old state.


def dynamic_poll_factor(source_type: str) -> float:
    """v4 §13.1 — an actively escalating conflict earns tighter polling for
    the broad-scope sources; a quiet world keeps the configured cadence."""
    try:
        if not cfg("sourcing", "dynamic_polling_by_conflict_activity"):
            return 1.0
    except KeyError:
        return 1.0
    if source_type != "rss":
        return 1.0
    row = query("SELECT COUNT(*) AS n FROM events WHERE conflict_id IS NOT NULL"
                " AND occurred_at >= datetime('now', '-6 hour')")
    n = row[0]["n"] if row else 0
    if n >= 30:
        return 0.5
    if n >= 10:
        return 0.75
    return 1.0


# ===== v5 additions =====

def refresh_flags() -> int:
    """v5 §7 — download each country's flag SVG from Wikimedia Commons once
    and cache it locally under frontend/flags/{iso3}.svg, then point
    countries.flag_image_url at the local path. Small (~199 SVGs), so this
    runs on the slow reference cadence and degrades cleanly offline (a flag
    that fails to fetch just keeps its remote Special:FilePath URL). Never a
    Unicode flag emoji — real images only (§7)."""
    from pathlib import Path
    from ..config import REPO_ROOT
    from .flag_names import FLAG_NAME
    import urllib.parse
    flags_dir = REPO_ROOT / "frontend" / "flags"
    flags_dir.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for r in query("SELECT id FROM countries"):
        iso3 = r["id"]
        dest = flags_dir / f"{iso3}.svg"
        if dest.exists() and dest.stat().st_size > 200:
            # ensure the DB points at the cached copy
            with write_tx() as conn:
                conn.execute("UPDATE countries SET flag_image_url = ? WHERE id = ?",
                             (f"/flags/{iso3}.svg", iso3))
            continue
        name = FLAG_NAME.get(iso3)
        if not name:
            continue
        url = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
               + urllib.parse.quote(f"Flag of {name}.svg"))
        try:
            body = fetch_url(url, headers={"Accept": "image/svg+xml"}, timeout=25)
            if not body or len(body) < 200 or b"<svg" not in body[:2000].lower():
                continue
            dest.write_bytes(body)
            with write_tx() as conn:
                conn.execute("UPDATE countries SET flag_image_url = ? WHERE id = ?",
                             (f"/flags/{iso3}.svg", iso3))
            fetched += 1
        except Exception:  # noqa: BLE001 — per-flag isolation, retry next cycle
            continue
    if fetched:
        log.info("flags_cached", extra={"data": {"downloaded": fetched}})
    return fetched
