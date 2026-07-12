"""v3 §13-23 — idempotent seeding of the geopolitical entity layer."""

import logging

from ..db.models import new_id, now_iso
from ..db.session import query, query_one, write_tx
from ..processing.entities import resolve_entity
from . import seed_data
from .m49 import M49_SUBREGION

log = logging.getLogger("geo_seed")

# v8.13.7 — government_type for the EU + North-American states that ship in
# seed_data.COUNTRIES_V4_EXTRA with a NULL type. Applied ONLY where the column
# is still NULL (see _seed_countries), so it never overrides a real seed value
# or a Wikidata-synced one. Keeps _paramount_role picking the right office once
# both a head of state and a head of government are seeded for these countries.
_GOV_TYPE_FILL = {
    # EU parliamentary republics — the PM leads
    "AUT": "federal parliamentary republic", "IRL": "parliamentary republic",
    "EST": "parliamentary republic", "LVA": "parliamentary republic",
    "HRV": "parliamentary republic", "BGR": "parliamentary republic",
    "CZE": "parliamentary republic", "SVK": "parliamentary republic",
    "SVN": "parliamentary republic", "MLT": "parliamentary republic",
    # EU semi-presidential republics — the president has real power
    "LTU": "semi-presidential republic",
    # EU constitutional monarchies — the PM leads (monarch ceremonial)
    "DNK": "parliamentary constitutional monarchy",
    "BEL": "federal parliamentary constitutional monarchy",
    "LUX": "parliamentary constitutional monarchy",
    # North America — Commonwealth realms (King is HoS, PM leads)
    "JAM": "parliamentary constitutional monarchy",
    "BHS": "parliamentary constitutional monarchy",
    "BLZ": "parliamentary constitutional monarchy",
    "ATG": "parliamentary constitutional monarchy",
    "GRD": "parliamentary constitutional monarchy",
    "KNA": "parliamentary constitutional monarchy",
    "LCA": "parliamentary constitutional monarchy",
    "VCT": "parliamentary constitutional monarchy",
    # North America — Caribbean parliamentary republics (president ceremonial)
    "BRB": "parliamentary republic", "TTO": "parliamentary republic",
    "DMA": "parliamentary republic",
}


def seed_all() -> dict:
    counts = {}
    counts["countries"] = _seed_countries()
    counts["alliances"] = _seed_alliances()
    counts["non_state_actors"] = _seed_nsas()
    counts["reclassified_nsas"] = _reclassify_governing_nsas()  # v6 §21
    counts["conflicts"] = _seed_conflicts()
    counts["marked_locations"] = _seed_marked()
    counts["organizations"] = _seed_orgs()
    counts["treaties"] = _seed_treaties()
    counts["sanctions"] = _seed_sanctions()
    counts["persons"] = _seed_persons()
    counts["elections"] = _seed_elections()
    counts["border_disputes"] = _seed_border_disputes()   # v4 §5.3
    counts["political_parties"] = _seed_parties()         # v4 §6.2
    counts["nsa_zones"] = _seed_nsa_zones()               # v5 §11
    counts["subfactions"] = _seed_subfactions()           # v6 §8
    counts["subnational_areas"] = _seed_subnational()     # v6 §16
    counts["administrative_units"] = _seed_administrative_units()  # v8 §4
    counts["events_admin_backfilled"] = _backfill_event_admin_uids()  # v8.3
    added = {k: v for k, v in counts.items() if v}
    if added:
        log.info("geo_seeded", extra={"data": added})
    check_completeness()                                  # v4 §5.1
    return counts


def _reclassify_governing_nsas() -> int:
    """v6 §21 — a non-state actor that became a country's actual governing
    authority is not a non-state actor anymore. Driven by
    seed_data.NSA_GOVERNING_RECLASSIFICATIONS so the Taliban/Afghanistan case
    is one data row, not special-cased code: removes the NSA row + its zones
    + any conflict-party references, and marks the country de_facto (its
    leadership rows come from the ordinary LEADERSHIP seed)."""
    done = 0
    with write_tx() as conn:
        for nsa_name, iso3 in seed_data.NSA_GOVERNING_RECLASSIFICATIONS:
            row = conn.execute("SELECT id FROM non_state_actors WHERE name = ?",
                               (nsa_name,)).fetchone()
            if not row:
                continue
            nsa_id = row["id"]
            conn.execute("DELETE FROM non_state_actor_zones"
                         " WHERE non_state_actor_id = ?", (nsa_id,))
            conn.execute("DELETE FROM conflict_parties"
                         " WHERE non_state_actor_id = ?", (nsa_id,))
            conn.execute("DELETE FROM non_state_actors WHERE id = ?", (nsa_id,))
            conn.execute("UPDATE countries SET status = 'de_facto' WHERE id = ?",
                         (iso3,))
            log.info("nsa_reclassified_as_government", extra={"data": {
                "actor": nsa_name, "country": iso3}})
            done += 1
    return done


def _flag_url(iso3: str) -> str | None:
    """v5 §7 — default flag image URL: a cached local file if refresh_flags
    already downloaded it, else a Wikimedia Commons Special:FilePath URL that
    redirects to the real SVG (never a Unicode flag emoji). refresh_flags()
    (sync.py) later swaps this for the locally cached path."""
    import urllib.parse
    from pathlib import Path
    from ..config import REPO_ROOT
    from .flag_names import FLAG_NAME
    cached = REPO_ROOT / "frontend" / "flags" / f"{iso3}.svg"
    if cached.exists():
        return f"/flags/{iso3}.svg"
    name = FLAG_NAME.get(iso3)
    if not name:
        return None
    fname = urllib.parse.quote(f"Flag of {name}.svg")
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{fname}?width=160"


def _seed_countries() -> int:
    added = 0
    rows = list(seed_data.COUNTRIES) + list(seed_data.COUNTRIES_V4_EXTRA)
    with write_tx() as conn:
        for iso3, name, capital, region, gov, lat, lon in rows:
            status = seed_data.COUNTRY_STATUS.get(iso3, "un_member")
            iso2 = seed_data.COUNTRY_ISO2.get(iso3)
            pop = seed_data.COUNTRY_POPULATION.get(iso3)
            flag = _flag_url(iso3)
            # v6 §28 — region comes from the UN M49 standard, never the
            # hand-assigned value on the seed tuple (that's how South Asia
            # lost Nepal/Bhutan/Sri Lanka/Maldives in the first place)
            region = M49_SUBREGION.get(iso3, region)
            cur = conn.execute(
                "INSERT OR IGNORE INTO countries (id, name, capital, region,"
                " government_type, boundary_ref, status, iso2, population,"
                " last_updated_at, flag_image_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (iso3, name, capital, region, gov, iso3, status, iso2, pop,
                 now_iso(), flag))
            added += cur.rowcount
            # v4 one-time enrichment of pre-v4 rows (status/iso2/population
            # were added by the schema migration with defaults); v5 fills the
            # flag URL but never overwrites a locally-cached one; v6 re-syncs
            # region to M49 on every startup (authoritative taxonomy)
            conn.execute(
                "UPDATE countries SET status = ?, iso2 = COALESCE(iso2, ?),"
                " population = COALESCE(population, ?), region = ?,"
                " flag_image_url = CASE WHEN flag_image_url LIKE '/flags/%'"
                "   THEN flag_image_url ELSE ? END WHERE id = ?",
                (status, iso2, pop, region, flag, iso3))
            # §17 — capitals auto-populate the marked-locations layer
            if capital and lat is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO marked_locations (id, name, lat, lon, category,"
                    " country_id, description) "
                    "SELECT ?, ?, ?, ?, 'capital', ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM marked_locations WHERE category='capital' AND country_id=?)",
                    (new_id(), f"{capital} (capital of {name})", lat, lon, iso3,
                     f"Capital of {name}.", iso3))
        # v6 §14 — major territories: own clickable profiles, status
        # 'territory', linked to their sovereign via sovereign_id
        from .country_stats import TERRITORIES
        for iso3, name, capital, sovereign, pop, lat, lon in TERRITORIES:
            region = M49_SUBREGION.get(iso3)
            cur = conn.execute(
                "INSERT OR IGNORE INTO countries (id, name, capital, region,"
                " government_type, boundary_ref, status, population, sovereign_id,"
                " last_updated_at, flag_image_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (iso3, name, capital, region, "dependent territory", iso3,
                 "territory", pop, sovereign, now_iso(), _flag_url(iso3)))
            added += cur.rowcount
            conn.execute("UPDATE countries SET status='territory', sovereign_id=?,"
                         " region=? WHERE id = ?", (sovereign, region, iso3))
            if capital and lat is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO marked_locations (id, name, lat, lon, category,"
                    " country_id, description) "
                    "SELECT ?, ?, ?, ?, 'capital', ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM marked_locations WHERE category='capital' AND country_id=?)",
                    (new_id(), f"{capital} (capital of {name})", lat, lon, iso3,
                     f"Capital of {name}.", iso3))
        # v8.13.7 — fill government_type for the EU + North-American states that
        # were seeded from COUNTRIES_V4_EXTRA with a NULL government_type (owner:
        # "seed all leaders of every EU and North American country"). A NULL type
        # made _paramount_role default to head_of_state, so seeding a ceremonial
        # president/monarch alongside the PM would have flipped the paramount
        # office to the figurehead. These correct strings keep the PM paramount
        # in the parliamentary states/realms and the president paramount in the
        # semi-presidential ones. Only fills where still NULL (never overrides a
        # real value or a Wikidata-synced one).
        for iso3, gtype in _GOV_TYPE_FILL.items():
            conn.execute(
                "UPDATE countries SET government_type = ?"
                " WHERE id = ? AND government_type IS NULL",
                (gtype, iso3))
        # v6 §15/§16 — profile depth from the vendored authoritative dataset
        # (World Bank / UNDP / Pew figures; the §30 accuracy pipeline refreshes
        # them). gdp_per_capita is derived, never independently guessed.
        import json as _json
        from .country_stats import COUNTRY_STATS
        for iso3, (official, area, gdp_b, hdi, langs, religion, lang) in \
                COUNTRY_STATS.items():
            gdp = gdp_b * 1e9 if gdp_b is not None else None
            pop_row = conn.execute("SELECT population FROM countries WHERE id = ?",
                                   (iso3,)).fetchone()
            pop = pop_row["population"] if pop_row else None
            gdp_pc = round(gdp / pop, 0) if (gdp and pop) else None
            conn.execute(
                "UPDATE countries SET official_name = ?, area_km2 = ?, gdp_usd = ?,"
                " hdi = ?, languages = ?, gdp_per_capita_usd = ?,"
                " dominant_religion = ?, dominant_language = ? WHERE id = ?",
                (official, area, gdp, hdi, _json.dumps(langs), gdp_pc,
                 religion, lang, iso3))
        # v6.1 — currency for every country (owner: "list every country's
        # currency"; no more gaps). Reference data, not LLM-guessed.
        from .country_extra import CURRENCIES, LEGISLATURES
        for iso3, (code, cur_name, symbol) in CURRENCIES.items():
            conn.execute(
                "UPDATE countries SET currency_code = ?, currency_name = ?,"
                " currency_symbol = ? WHERE id = ?",
                (code, cur_name, symbol, iso3))
        # v6.1 — per-party legislative seat composition for the parliamentary
        # graphic on major states (falls back to composition_summary elsewhere)
        for iso3, leg in LEGISLATURES.items():
            seats = _json.dumps(leg)
            summary = ", ".join(f"{p[0]} {p[1]}" for p in leg["parties"][:5])
            conn.execute(
                "INSERT INTO country_legislature (country_id, chamber_name,"
                " composition_summary, seats_json, last_refreshed_at)"
                " VALUES (?,?,?,?,?)"
                " ON CONFLICT(country_id) DO UPDATE SET"
                "   chamber_name = excluded.chamber_name,"
                "   composition_summary = COALESCE(country_legislature.composition_summary,"
                "     excluded.composition_summary),"
                "   seats_json = excluded.seats_json",
                (iso3, leg["chamber"], summary, seats, now_iso()))
        # v6.6 — world coverage: every country gets a head of state/government
        # (hand-curated seed_data.LEADERSHIP entries win via INSERT OR IGNORE)
        from .leaders_world import L as _world_leaders
        for iso3, role, name, party, since in list(seed_data.LEADERSHIP) + _world_leaders:
            conn.execute(
                "INSERT OR IGNORE INTO country_leadership (country_id, role, name, party,"
                " since_date, last_refreshed_at) VALUES (?,?,?,?,?,NULL)",
                (iso3, role, name, party, since))
            # v5 §15 — refresh rows that are still SEED data (never synced from
            # Wikidata) when the seed value changes, so a corrected seed fact
            # (e.g. the IRN Supreme Leader) actually reaches an existing DB
            # instead of being frozen by INSERT OR IGNORE. Synced rows
            # (last_refreshed_at NOT NULL) are authoritative and left alone.
            conn.execute(
                "UPDATE country_leadership SET name = ?, party = ?, since_date = ?"
                " WHERE country_id = ? AND role = ? AND last_refreshed_at IS NULL",
                (name, party, since, iso3, role))
    return added


def _seed_border_disputes() -> int:
    """v4 §5.3 — disputed boundaries as their own data layer."""
    added = 0
    with write_tx() as conn:
        for a, b, territory, status, summary in seed_data.BORDER_DISPUTES:
            exists = conn.execute(
                "SELECT 1 FROM border_disputes WHERE claimant_a_id = ?"
                " AND territory_name = ?", (a, territory)).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO border_disputes (id, claimant_a_id, claimant_b_id,"
                " territory_name, status, boundary_ref, summary) VALUES (?,?,?,?,?,?,?)",
                (new_id(), a, b, territory, status, None, summary))
            added += 1
    return added


def _seed_nsa_zones() -> int:
    """v5 §11 — rough NSA territory polygons (coarse, descriptive context)."""
    import json as _json
    added = 0
    for nsa_name, confidence, ring in seed_data.NSA_ZONES:
        nsa = query_one("SELECT id FROM non_state_actors WHERE name = ?", (nsa_name,))
        if not nsa:
            continue
        if query_one("SELECT 1 FROM non_state_actor_zones WHERE non_state_actor_id = ?",
                     (nsa["id"],)):
            continue
        geojson = _json.dumps({"type": "Polygon", "coordinates": [ring]})
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO non_state_actor_zones (id, non_state_actor_id, zone_geojson,"
                " confidence, last_updated_at) VALUES (?,?,?,?,?)",
                (new_id(), nsa["id"], geojson, confidence, now_iso()))
        added += 1
    return added


def _seed_parties() -> int:
    """v4 §6.2 — parties become first-class linkable entities (same
    canonical-entity pattern as NSAs and orgs). v6 §5 enriches existing rows
    with electoral history / coalitions / founding history."""
    import json as _json
    added = 0
    for name, iso3, ideology, founded in seed_data.POLITICAL_PARTIES:
        if query_one("SELECT 1 FROM political_parties WHERE name = ?", (name,)):
            continue
        cent = resolve_entity(name.split(" (")[0])
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO political_parties (id, name, country_id, ideology_tags,"
                " founded_date, canonical_entity_id, last_updated_at) VALUES (?,?,?,?,?,?,?)",
                (new_id(), name, iso3, ideology, founded, cent, now_iso()))
        added += 1
    # v6 §5 — profile depth on existing rows (idempotent: only fills NULLs)
    with write_tx() as conn:
        for name, extra in seed_data.PARTY_ENRICHMENT.items():
            conn.execute(
                "UPDATE political_parties SET"
                " electoral_history = COALESCE(electoral_history, ?),"
                " coalition_partners = COALESCE(coalition_partners, ?),"
                " founding_history = COALESCE(founding_history, ?)"
                " WHERE name = ?",
                (_json.dumps(extra["electoral_history"]),
                 _json.dumps(extra["coalition_partners"]),
                 extra["founding_history"], name))
        for name, extra in seed_data.PERSON_ENRICHMENT.items():
            portrait = None
            if extra.get("portrait"):
                import urllib.parse as _up
                portrait = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
                            + _up.quote(extra["portrait"]) + "?width=200")
            conn.execute(
                "UPDATE notable_persons SET"
                " electoral_history = COALESCE(electoral_history, ?),"
                " portrait_image_url = COALESCE(portrait_image_url, ?)"
                " WHERE name = ?",
                (_json.dumps(extra["electoral_history"]), portrait, name))
    return added


def check_completeness() -> dict:
    """v4 §5.1/§5.5 — startup completeness check: seeded country count vs
    the known-correct reference, plus profile resolvability for every
    entity that appears on the map. Logs a visible warning instead of
    leaving gaps silent."""
    from ..config import cfg
    ref = int(cfg("entity_completeness", "reference_country_count"))
    tol = int(cfg("entity_completeness", "completeness_warning_tolerance"))
    n = query_one("SELECT COUNT(*) AS n FROM countries")["n"]
    problems = []
    if n < ref - tol:
        problems.append(f"country table has {n} rows, expected ~{ref}"
                        f" (tolerance {tol}) — countries are missing")
    unresolvable = query_one(
        "SELECT COUNT(*) AS n FROM marked_locations m WHERE m.country_id IS NOT NULL"
        " AND NOT EXISTS (SELECT 1 FROM countries c WHERE c.id = m.country_id)")["n"]
    if unresolvable:
        problems.append(f"{unresolvable} marked locations reference countries"
                        " with no resolvable profile")
    orphan_parties = query_one(
        "SELECT COUNT(*) AS n FROM conflict_parties p WHERE p.country_id IS NOT NULL"
        " AND NOT EXISTS (SELECT 1 FROM countries c WHERE c.id = p.country_id)")["n"]
    if orphan_parties:
        problems.append(f"{orphan_parties} conflict parties reference countries"
                        " with no resolvable profile")
    # v6 §28 — verify every M49 sub-region's expected country count matches
    # what's actually assigned (the fix for 'South Asia is missing Nepal'),
    # same pattern as the total-count check above
    from ..db.session import query as _query
    from .m49 import expected_counts
    statuses = {r["id"]: r["status"] for r in _query("SELECT id, status FROM countries")}
    expected = expected_counts(statuses)
    actual = {r["region"]: r["n"] for r in _query(
        "SELECT region, COUNT(*) AS n FROM countries"
        " WHERE status != 'territory' GROUP BY region")}
    for sub, exp in sorted(expected.items()):
        got = actual.get(sub, 0)
        if got < exp:
            problems.append(f"M49 sub-region '{sub}' has {got} countries,"
                            f" expected {exp}")
    # v6 §15 — zero-empty-entry guarantee: every country profile must ship
    # complete. Fails loudly on any country with empty REQUIRED fields (the
    # fields the vendored dataset can guarantee offline); leadership rows
    # beyond the seed arrive via the Wikidata sync + §30 accuracy pipeline.
    empty = _query(
        "SELECT id FROM countries WHERE official_name IS NULL OR population IS NULL"
        " OR region IS NULL OR languages IS NULL OR flag_image_url IS NULL")
    if empty:
        problems.append(
            f"{len(empty)} countries have empty required profile fields"
            f" (e.g. {', '.join(r['id'] for r in empty[:6])}) — v6 §15 requires"
            " complete profiles")
    # v6 §21 — reclassification review: an NSA whose own description says it
    # governs a country should be reviewed for country-status reclassification
    governing = _query(
        "SELECT name FROM non_state_actors WHERE description_synthesis LIKE"
        " '%governing authority%' OR description_synthesis LIKE '%government of%'")
    for g in governing:
        problems.append(f"non-state actor '{g['name']}' reads as a governing"
                        " authority — review for country reclassification (v6 §21)")
    result = {"countries": n, "reference": ref, "problems": problems}
    if problems:
        log.warning("entity_completeness_gap", extra={"data": result})
    else:
        log.info("entity_completeness_ok", extra={"data": {"countries": n}})
    from ..db.models import meta_set
    import json as _json
    meta_set("entity_completeness", _json.dumps(result))
    return result


def _seed_alliances() -> int:
    added = 0
    with write_tx() as conn:
        for name, atype, founded, desc, members in seed_data.ALLIANCES:
            row = conn.execute("SELECT id FROM alliances WHERE name = ?", (name,)).fetchone()
            if row:
                aid = row["id"]
            else:
                aid = new_id()
                conn.execute("INSERT INTO alliances (id, name, type, founded_date,"
                             " description) VALUES (?,?,?,?,?)",
                             (aid, name, atype, founded, desc))
                added += 1
            for iso3 in members:
                conn.execute("INSERT OR IGNORE INTO alliance_memberships"
                             " (alliance_id, country_id) VALUES (?,?)", (aid, iso3))
    return added


def _seed_nsas() -> int:
    added = 0
    for name, atype, region, state, since, desc in seed_data.NON_STATE_ACTORS:
        base = seed_data.NSA_BASE_COORDS.get(name, (None, None))
        if query_one("SELECT 1 FROM non_state_actors WHERE name = ?", (name,)):
            # v4 §5.4 — backfill operating-area centroids on pre-v4 rows
            with write_tx() as conn:
                conn.execute("UPDATE non_state_actors SET base_lat = COALESCE(base_lat, ?),"
                             " base_lon = COALESCE(base_lon, ?) WHERE name = ?",
                             (base[0], base[1], name))
            continue
        # §16 — each NSA is its own canonical entity so ordinary extraction
        # and correlation associate coverage with it automatically
        cent = resolve_entity(name)
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO non_state_actors (id, name, actor_type, primary_region,"
                " affiliated_state_id, active_since, canonical_entity_id,"
                " description_synthesis, last_updated_at, base_lat, base_lon)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (new_id(), name, atype, region, state, since, cent, desc, now_iso(),
                 base[0], base[1]))
        added += 1
    return added


def _seed_conflicts() -> int:
    added = 0
    with write_tx() as conn:
        for name, region, started, status, summary, parties in seed_data.CONFLICTS:
            row = conn.execute("SELECT id FROM conflicts WHERE name = ?", (name,)).fetchone()
            if row:
                cid = row["id"]
            else:
                cid = new_id()
                conn.execute(
                    "INSERT INTO conflicts (id, name, region, started_at, status, summary,"
                    " last_updated_at) VALUES (?,?,?,?,?,?,?)",
                    (cid, name, region, started, status, summary, now_iso()))
                added += 1
            # explicit existence checks: the UNIQUE constraint contains NULL
            # columns, which SQLite treats as always-distinct, so INSERT OR
            # IGNORE alone would duplicate parties on every re-seed
            for ptype, ref, role, side in parties:      # v6 §8 — 4-tuples w/ side
                if ptype == "country":
                    exists = conn.execute(
                        "SELECT 1 FROM conflict_parties WHERE conflict_id = ?"
                        " AND country_id = ?", (cid, ref)).fetchone()
                    if not exists:
                        conn.execute(
                            "INSERT INTO conflict_parties (conflict_id, party_type,"
                            " country_id, role, side) VALUES (?,?,?,?,?)",
                            (cid, ptype, ref, role, side))
                    else:   # backfill side on pre-v6 rows
                        conn.execute(
                            "UPDATE conflict_parties SET side = ? WHERE conflict_id = ?"
                            " AND country_id = ? AND side IS NULL", (side, cid, ref))
                else:
                    nsa = conn.execute("SELECT id FROM non_state_actors WHERE name = ?",
                                       (ref,)).fetchone()
                    if not nsa:
                        continue
                    if not conn.execute(
                            "SELECT 1 FROM conflict_parties WHERE conflict_id = ?"
                            " AND non_state_actor_id = ?", (cid, nsa["id"])).fetchone():
                        conn.execute(
                            "INSERT INTO conflict_parties (conflict_id, party_type,"
                            " non_state_actor_id, role, side) VALUES (?,?,?,?,?)",
                            (cid, ptype, nsa["id"], role, side))
                    else:
                        conn.execute(
                            "UPDATE conflict_parties SET side = ? WHERE conflict_id = ?"
                            " AND non_state_actor_id = ? AND side IS NULL",
                            (side, cid, nsa["id"]))
    return added


def _seed_subnational() -> int:
    """v6 §16 — sub-national areas for area-level thematic map modes."""
    import json as _json
    from .country_stats import SUBNATIONAL_AREAS
    added = 0
    with write_tx() as conn:
        for iso3, name, religion, lang, pop, ring in SUBNATIONAL_AREAS:
            if conn.execute("SELECT 1 FROM subnational_areas WHERE country_id = ?"
                            " AND name = ?", (iso3, name)).fetchone():
                continue
            geojson = _json.dumps({"type": "Polygon", "coordinates": [ring]})
            conn.execute(
                "INSERT INTO subnational_areas (id, country_id, name, zone_geojson,"
                " dominant_religion, dominant_language, population)"
                " VALUES (?,?,?,?,?,?,?)",
                (new_id(), iso3, name, geojson, religion, lang, pop))
            added += 1
    return added


def _unit_source(u) -> str:
    """v8.14 — a unit's provenance tag. Honors an explicit `src` written by the
    builder (the GADM prefecture builder tags its units "gadm-4.1"); otherwise
    every deeper tier (level >= 2, not just == 2 — the old test mislabeled the
    DEU/POL/TZA level-3 rows as naturalearth) is geoBoundaries, ADM1 is NE."""
    if u.get("src"):
        return u["src"]
    return "geoboundaries-adm2" if u.get("level", 1) >= 2 else "naturalearth-10m"


def _seed_administrative_units() -> int:
    """v8 §4 — populate administrative_units from the vendored Administrative
    Atlas (admin_atlas.units(), built by scripts/build_admin_atlas.py from
    Natural Earth 10m ADM1, public domain). The registry rows carry stable
    admin_uids (the PRIMARY KEY), so INSERT OR IGNORE makes this idempotent — a
    re-seed is a no-op and never re-numbers a unit an event already references.

    ADM1 is present-day (Natural Earth is current), so effective_from/effective_to
    stay NULL (= always/currently valid); the temporal machinery (as_of epoch
    selection, curated historical units back to 1950) reads those columns and
    layers estimated-vs-real epochs on top in a later data pass — the scaffold
    is here now so nothing needs a schema change to add history."""
    import json as _json
    try:
        from .admin_atlas import units as _atlas_units
    except Exception:
        log.warning("admin_atlas_unavailable")
        return 0
    rows = _atlas_units()
    added = 0
    with write_tx() as conn:
        # v8.12/v8.14 — tree reconcile, now GENERIC. A unit's adm_level,
        # parent_uid or path can CHANGE between atlas builds (v8.12 relabeled
        # ESP/ITA/FRA municipios 3→2; the v8.14 GADM prefecture builder
        # re-levels China's counties 2→3 and re-parents them under the new
        # prefectures). INSERT OR IGNORE can't update an existing uid, so an
        # already-seeded DB would keep the stale tree. Instead of a bespoke
        # version marker per build, the reconcile is gated by a FINGERPRINT of
        # the atlas's own (uid, level, parent) tuples — any rebuild that moves a
        # unit changes the fingerprint and the reconcile runs exactly once.
        import hashlib as _hashlib
        fp = _hashlib.md5(_json.dumps(
            sorted([u["uid"], u.get("level", 1), u.get("parent")]
                   for u in rows), separators=(",", ":")).encode()).hexdigest()
        marker = conn.execute(
            "SELECT value FROM app_meta WHERE key='admin_level_reconcile'").fetchone()
        if not marker or marker["value"] != fp:
            relabel = [(u.get("level", 1), _unit_source(u), u.get("parent"),
                        u.get("path"), u["uid"],
                        u.get("level", 1), u.get("parent")) for u in rows]
            conn.executemany(
                "UPDATE administrative_units SET adm_level=?, source=?,"
                " parent_uid=?, path=COALESCE(?, path)"
                " WHERE admin_uid=? AND (adm_level<>? OR"
                " COALESCE(parent_uid,-1)<>COALESCE(?,-1))", relabel)
            conn.execute("INSERT OR REPLACE INTO app_meta(key, value)"
                         " VALUES('admin_level_reconcile', ?)", (fp,))
        existing = conn.execute(
            "SELECT COUNT(*) AS n FROM administrative_units").fetchone()["n"]
        if existing >= len(rows):
            return 0  # already fully seeded — skip the batch entirely
        params = []
        for u in rows:
            country = u.get("country") or None
            name = u["name"]
            level = u.get("level", 1)
            # v8.1 — ADM2 units carry a parent_uid (their ADM1 state) + a full
            # path ("USA/California/Los Angeles") + their own source tag.
            parent_uid = u.get("parent")
            path = u.get("path") or (f"{country}/{name}" if country else name)
            source = _unit_source(u)
            params.append((
                u["uid"], country, level, parent_uid, path,
                name, u.get("name_local"), (u.get("type") or None),
                u.get("clat"), u.get("clon"),
                _json.dumps(u["bbox"]) if u.get("bbox") else None,
                source, None, None,
            ))
        conn.executemany(
            "INSERT OR IGNORE INTO administrative_units"
            " (admin_uid, country_id, adm_level, parent_uid, path, name,"
            "  name_local, unit_type, centroid_lat, centroid_lon, bbox_json,"
            "  source, effective_from, effective_to)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", params)
        added = conn.execute(
            "SELECT COUNT(*) AS n FROM administrative_units").fetchone()["n"] - existing
    return added


def _backfill_event_admin_uids(batch: int = 8000) -> int:
    """v8.3 — resolve events.admin_uid for already-geocoded events that predate
    the v8 ingestion resolution (the curated historical packs + anything ingested
    before v8). Only touches rows with a lat/lon and a NULL admin_uid, so once
    backfilled a later boot finds nothing and this is a cheap no-op. Bounded per
    boot so a huge backlog never blocks startup — the remainder fills next boot.
    Lights up the Hotspots activity layer with the history already in the chain."""
    from .admin_atlas import unit_at
    rows = query(
        "SELECT id, location_lat, location_lon FROM events"
        " WHERE admin_uid IS NULL AND location_lat IS NOT NULL"
        " AND location_lon IS NOT NULL LIMIT ?", (batch,))
    if not rows:
        return 0
    updates = []
    for r in rows:
        try:
            uid = unit_at(r["location_lat"], r["location_lon"])
        except Exception:  # noqa: BLE001 — never let one bad row block the batch
            uid = None
        if uid is not None:
            updates.append((uid, r["id"]))
    if updates:
        with write_tx() as conn:
            conn.executemany("UPDATE events SET admin_uid = ? WHERE id = ?", updates)
    return len(updates)


def _seed_subfactions() -> int:
    """v6 §8 — conflict-scoped sub-national factions (War Mode only)."""
    import json as _json
    added = 0
    with write_tx() as conn:
        for conflict_name, name, side, ring in seed_data.CONFLICT_SUBFACTIONS:
            c = conn.execute("SELECT id FROM conflicts WHERE name = ?",
                             (conflict_name,)).fetchone()
            if not c:
                continue
            if conn.execute("SELECT 1 FROM conflict_subfactions WHERE conflict_id = ?"
                            " AND name = ?", (c["id"], name)).fetchone():
                continue
            geojson = _json.dumps({"type": "Polygon", "coordinates": [ring]}) if ring else None
            conn.execute(
                "INSERT INTO conflict_subfactions (id, conflict_id, name, zone_geojson,"
                " side) VALUES (?,?,?,?,?)", (new_id(), c["id"], name, geojson, side))
            added += 1
    return added


def _seed_marked() -> int:
    added = 0
    with write_tx() as conn:
        for name, category, lat, lon, desc in seed_data.MARKED_LOCATIONS:
            if conn.execute("SELECT 1 FROM marked_locations WHERE name = ?",
                            (name,)).fetchone():
                continue
            conn.execute("INSERT INTO marked_locations (id, name, lat, lon, category,"
                         " description) VALUES (?,?,?,?,?,?)",
                         (new_id(), name, lat, lon, category, desc))
            added += 1
    return added


def _seed_orgs() -> int:
    added = 0
    for name, otype, mandate, hq, founded in seed_data.ORGANIZATIONS:
        if query_one("SELECT 1 FROM international_organizations WHERE name = ?", (name,)):
            continue
        cent = resolve_entity(name)  # §18 — orgs are canonical entities too
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO international_organizations (id, name, org_type,"
                " mandate_summary, hq_location, canonical_entity_id, founded_date,"
                " last_updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (new_id(), name, otype, mandate, hq, cent, founded, now_iso()))
        added += 1
    return added


def _seed_treaties() -> int:
    added = 0
    with write_tx() as conn:
        for name, ttype, signed, status, summary, signatories in seed_data.TREATIES:
            row = conn.execute("SELECT id FROM treaties WHERE name = ?", (name,)).fetchone()
            if row:
                tid = row["id"]
            else:
                tid = new_id()
                conn.execute("INSERT INTO treaties (id, name, treaty_type, signed_at,"
                             " status, summary) VALUES (?,?,?,?,?,?)",
                             (tid, name, ttype, signed, status, summary))
                added += 1
            for iso3, ratified in signatories:
                conn.execute("INSERT OR IGNORE INTO treaty_signatories"
                             " (treaty_id, country_id, ratified) VALUES (?,?,?)",
                             (tid, iso3, ratified))
    return added


def _seed_sanctions() -> int:
    added = 0
    with write_tx() as conn:
        for ptype, pref, target_iso, target_nsa, reason, imposed, status in seed_data.SANCTIONS:
            if ptype == "country":
                pid = pref
            elif ptype == "alliance":
                row = conn.execute("SELECT id FROM alliances WHERE name = ?", (pref,)).fetchone()
                pid = row["id"] if row else pref
            else:
                row = conn.execute("SELECT id FROM international_organizations WHERE name = ?",
                                   (pref,)).fetchone()
                pid = row["id"] if row else pref
            nsa_id = None
            if target_nsa:
                row = conn.execute("SELECT id FROM non_state_actors WHERE name = ?",
                                   (target_nsa,)).fetchone()
                nsa_id = row["id"] if row else None
            exists = conn.execute(
                "SELECT 1 FROM sanctions WHERE imposing_party_id = ? AND"
                " COALESCE(target_country_id,'') = COALESCE(?, '') AND"
                " COALESCE(target_non_state_actor_id,'') = COALESCE(?, '')",
                (pid, target_iso, nsa_id)).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO sanctions (id, imposing_party_type, imposing_party_id,"
                " target_country_id, target_non_state_actor_id, reason, imposed_at, status)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (new_id(), ptype, pid, target_iso, nsa_id, reason, imposed, status))
            added += 1
    return added


def _seed_persons() -> int:
    added = 0
    for name, role, iso3, org_name, nsa_name, bio in seed_data.NOTABLE_PERSONS:
        if query_one("SELECT 1 FROM notable_persons WHERE name = ?", (name,)):
            continue
        cent = resolve_entity(name)  # §22 — persons are canonical entities
        org_id = nsa_id = None
        if org_name:
            row = query_one("SELECT id FROM international_organizations WHERE name = ?",
                            (org_name,))
            org_id = row["id"] if row else None
        if nsa_name:
            row = query_one("SELECT id FROM non_state_actors WHERE name = ?", (nsa_name,))
            nsa_id = row["id"] if row else None
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO notable_persons (id, name, role_title, affiliated_country_id,"
                " affiliated_org_id, affiliated_non_state_actor_id, canonical_entity_id,"
                " bio_summary) VALUES (?,?,?,?,?,?,?,?)",
                (new_id(), name, role, iso3, org_id, nsa_id, cent, bio))
        added += 1
    return added


def _seed_elections() -> int:
    added = 0
    with write_tx() as conn:
        for iso3, etype, date, status, result in seed_data.ELECTIONS:
            exists = conn.execute(
                "SELECT 1 FROM elections WHERE country_id = ? AND scheduled_date = ?",
                (iso3, date)).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO elections (id, country_id, election_type, scheduled_date,"
                " status, result_summary, leadership_refreshed) VALUES (?,?,?,?,?,?,?)",
                (new_id(), iso3, etype, date, status, result,
                 1 if status == "completed" else 0))
            added += 1
    return added
