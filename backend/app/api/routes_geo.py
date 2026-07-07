"""v3 §13-23 — geopolitical entity layer routes, plus §10.2 satellites and
§11 provenance verification."""

import json
import time

from ..db.models import meta_get, now_iso
from ..db.session import query, query_one, write_tx
from .router import route

# v6.1 — the executive office differs by system. In parliamentary republics
# and constitutional/parliamentary monarchies the head of GOVERNMENT (PM)
# leads and the head of state is ceremonial; in presidential, semi-presidential,
# absolute-monarchy, theocratic and one-party systems the head of STATE holds
# real executive power. A few need an explicit call regardless of label.
_PARAMOUNT_ROLE_OVERRIDE = {
    "CHN": "head_of_state",   # Xi Jinping (President + CCP General Secretary)
    "RUS": "head_of_state",   # Putin (President), not PM Mishustin
    "PRK": "head_of_state",   # Kim Jong Un
    "IRN": "head_of_state",   # Supreme Leader
    "AFG": "head_of_state",   # Taliban Supreme Leader (de facto)
    "SAU": "head_of_state",   # King (absolute monarchy)
    "VAT": "head_of_state",
}

# v6.1 — the paramount leader's real title, when it's more than the office
# name (China's power flows through the party post; Iran's through clergy)
_PARAMOUNT_TITLE = {
    "CHN": "President & CCP General Secretary (paramount leader)",
    "RUS": "President",
    "IRN": "Supreme Leader",
    "PRK": "Supreme Leader",
    "AFG": "Supreme Leader (Taliban, de facto)",
    "SAU": "King",
    "GBR": "Prime Minister",
    "DEU": "Chancellor",
}


def _paramount_role(iso3, government_type, leadership):
    roles = {l["role"] for l in leadership}
    if iso3 in _PARAMOUNT_ROLE_OVERRIDE:
        pick = _PARAMOUNT_ROLE_OVERRIDE[iso3]
        return pick if pick in roles else (next(iter(roles), None))
    g = (government_type or "").lower()
    # parliamentary systems (incl. parliamentary/constitutional monarchies)
    # led by the PM — but NOT semi-presidential, where the president dominates
    if "parliamentary" in g and "semi-presidential" not in g:
        pref = ["head_of_government", "head_of_state"]
    else:  # presidential / semi-presidential / absolute monarchy / theocratic
        pref = ["head_of_state", "head_of_government"]
    for r in pref:
        if r in roles:
            return r
    return next(iter(roles), None)


@route("GET", "/api/countries")
def countries_list(params, q, body):
    term = (q.get("q") or "").strip().lower()
    rows = query(
        "SELECT c.*, hs.name AS head_of_state, hg.name AS head_of_government"
        " FROM countries c"
        " LEFT JOIN country_leadership hs ON hs.country_id = c.id AND hs.role='head_of_state'"
        " LEFT JOIN country_leadership hg ON hg.country_id = c.id"
        "   AND hg.role='head_of_government'"
        " ORDER BY c.name")
    out = [dict(r) for r in rows]
    if term:
        out = [c for c in out if term in (c["name"] or "").lower()
               or term in (c.get("head_of_state") or "").lower()
               or term in (c.get("head_of_government") or "").lower()
               or term in (c.get("region") or "").lower()]
    return 200, {"countries": out}


@route("GET", "/api/countries/{iso3}")
def country_profile(params, q, body):
    iso3 = params["iso3"].upper()
    country = query_one("SELECT * FROM countries WHERE id = ?", (iso3,))
    if not country:
        return 404, {"error": "country not registered"}
    profile = dict(country)
    profile["leadership"] = [dict(r) for r in query(
        "SELECT role, name, party, since_date, last_refreshed_at, image_url"
        " FROM country_leadership WHERE country_id = ?", (iso3,))]
    # v6.1 — which office actually leads the country. The UI must feature the
    # PARAMOUNT leader (Xi Jinping for China, not Premier Li Qiang; Putin for
    # Russia), which the naive "prefer prime minister" rule got wrong. Derive
    # it from the government type, with explicit overrides for the handful of
    # systems where the label doesn't tell the whole story.
    profile["paramount_role"] = _paramount_role(iso3, profile.get("government_type"),
                                                profile["leadership"])
    profile["paramount_title"] = _PARAMOUNT_TITLE.get(iso3)
    # v5 §15 — visible staleness flag: a leadership row that has never synced,
    # or hasn't refreshed within its expected interval, is marked so the UI can
    # warn instead of silently serving old data forever (a leader who died in
    # Feb and was replaced in March should never sit unflagged for months).
    from ..config import cfg as _cfg
    from datetime import datetime, timezone, timedelta
    stale_days = float(_cfg("leadership_data", "staleness_warning_days"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    for l in profile["leadership"]:
        ra = l.get("last_refreshed_at")
        if not ra:
            l["stale"] = True
            l["stale_reason"] = "never synced from Wikidata (seed data)"
        else:
            try:
                fresh = datetime.fromisoformat(ra.replace("Z", "+00:00")) >= cutoff
            except (ValueError, AttributeError):
                fresh = True
            l["stale"] = not fresh
            l["stale_reason"] = (f"not refreshed in over {int(stale_days)} days"
                                 if not fresh else None)
    leg = query_one("SELECT * FROM country_legislature WHERE country_id = ?", (iso3,))
    profile["legislature"] = dict(leg) if leg else None
    if profile["legislature"] and profile["legislature"].get("seats_json"):
        try:  # v6.1 — parsed party seats for the parliamentary arc graphic
            profile["legislature"]["seats"] = json.loads(
                profile["legislature"]["seats_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    # v6.1 — currency, always present (owner: no gaps). Prefer the seeded row,
    # fall back to the vendored table so even a partially-migrated DB shows it.
    if not profile.get("currency_code"):
        from ..geopolitics.country_extra import CURRENCIES
        cur = CURRENCIES.get(iso3)
        if cur:
            profile["currency_code"], profile["currency_name"], \
                profile["currency_symbol"] = cur
    from ..geopolitics.country_extra import ALIGNMENTS
    if iso3 in ALIGNMENTS:   # v6.6 — experimental diplomatic-alignment map
        profile["alignments"] = ALIGNMENTS[iso3]
    ag = query_one("SELECT * FROM country_agenda_synthesis WHERE country_id = ?", (iso3,))
    profile["agenda"] = dict(ag) if ag else None
    if profile["agenda"] and profile["agenda"].get("source_story_ids"):
        profile["agenda"]["source_story_ids"] = json.loads(
            profile["agenda"]["source_story_ids"])
    trade = query_one("SELECT * FROM country_trade_stats WHERE country_id = ?", (iso3,))
    profile["trade"] = dict(trade) if trade else None
    profile["memberships"] = [dict(r) for r in query(
        "SELECT a.name, a.type, am.status FROM alliance_memberships am"
        " JOIN alliances a ON a.id = am.alliance_id WHERE am.country_id = ?"
        " ORDER BY a.name", (iso3,))]
    profile["relations"] = [dict(r) for r in query(
        "SELECT br.*, ca.name AS country_a_name, cb.name AS country_b_name"
        " FROM bilateral_relations br"
        " JOIN countries ca ON ca.id = br.country_a_id"
        " JOIN countries cb ON cb.id = br.country_b_id"
        " WHERE br.country_a_id = ? OR br.country_b_id = ?"
        " ORDER BY br.last_updated_at DESC", (iso3, iso3))]
    profile["sanctions_targeting"] = [dict(r) for r in query(
        "SELECT * FROM sanctions WHERE target_country_id = ? AND status = 'active'",
        (iso3,))]
    profile["sanctions_imposed"] = [dict(r) for r in query(
        "SELECT * FROM sanctions WHERE imposing_party_type = 'country'"
        " AND imposing_party_id = ? AND status = 'active'", (iso3,))]
    profile["treaties"] = [dict(r) for r in query(
        "SELECT t.name, t.treaty_type, t.status, ts.ratified FROM treaty_signatories ts"
        " JOIN treaties t ON t.id = ts.treaty_id WHERE ts.country_id = ?"
        " ORDER BY t.name", (iso3,))]
    profile["notable_persons"] = [dict(r) for r in query(
        "SELECT name, role_title, bio_summary FROM notable_persons"
        " WHERE affiliated_country_id = ?", (iso3,))]
    profile["elections"] = [dict(r) for r in query(
        "SELECT election_type, scheduled_date, status, result_summary FROM elections"
        " WHERE country_id = ? ORDER BY scheduled_date DESC", (iso3,))]
    # v6 §15 — current AND past conflicts, split so resolved history is
    # visible alongside active involvement
    all_conflicts = [dict(r) for r in query(
        "SELECT c.id, c.name, c.status, cp.role FROM conflict_parties cp"
        " JOIN conflicts c ON c.id = cp.conflict_id WHERE cp.country_id = ?", (iso3,))]
    profile["conflicts"] = [c for c in all_conflicts if c["status"] != "resolved"]
    profile["past_conflicts"] = [c for c in all_conflicts if c["status"] == "resolved"]
    # v6 §14 — territory linkage both ways: a territory links its sovereign,
    # a sovereign lists its territories
    if profile.get("sovereign_id"):
        sov = query_one("SELECT id, name, flag_image_url FROM countries WHERE id = ?",
                        (profile["sovereign_id"],))
        profile["sovereign"] = dict(sov) if sov else None
    profile["territories"] = [dict(r) for r in query(
        "SELECT id, name, flag_image_url, population FROM countries"
        " WHERE sovereign_id = ? ORDER BY name", (iso3,))]
    # v6 §15 — parsed languages list for display
    if profile.get("languages"):
        try:
            profile["languages"] = json.loads(profile["languages"])
        except (json.JSONDecodeError, TypeError):
            pass
    # recent tracked coverage mentioning the country (attribution surface)
    profile["recent_stories"] = [dict(r) for r in query(
        "SELECT DISTINCT s.id, s.headline, s.last_updated_at FROM stories s"
        " JOIN story_members m ON m.story_id = s.id"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE s.is_synthetic = 0 AND (f.who LIKE ? OR f.\"where\" LIKE ?)"
        " ORDER BY s.last_updated_at DESC LIMIT 8",
        (f"%{country['name']}%", f"%{country['name']}%"))]
    # --- v4 additions ---
    profile["border_disputes"] = [dict(r) for r in query(   # §5.3
        "SELECT bd.*, ca.name AS claimant_a_name, cb.name AS claimant_b_name"
        " FROM border_disputes bd"
        " JOIN countries ca ON ca.id = bd.claimant_a_id"
        " LEFT JOIN countries cb ON cb.id = bd.claimant_b_id"
        " WHERE bd.claimant_a_id = ? OR bd.claimant_b_id = ?", (iso3, iso3))]
    profile["parties"] = [dict(r) for r in query(           # §6.2
        "SELECT id, name, ideology_tags, founded_date FROM political_parties"
        " WHERE country_id = ? ORDER BY name", (iso3,))]
    profile["background"] = [dict(r) for r in query(        # §7 — attributed by origin
        "SELECT origin, title, extract, url, fetched_at FROM entity_background"
        " WHERE entity_type = 'country' AND entity_id = ?", (iso3,))]
    # §15.1 — honest thin-coverage indicator instead of implied confidence
    from ..config import cfg as _cfg
    floor = int(_cfg("coverage", "thin_coverage_story_floor"))
    profile["coverage"] = {"story_count": len(profile["recent_stories"]),
                           "thin": len(profile["recent_stories"]) < floor,
                           "floor": floor}
    return 200, profile


@route("GET", "/api/region/{region}")
def region_summary(params, q, body):
    """v5 §20 — region-level summary: every country in the region plus an
    aggregated view of current activity across them. Backs the analyst's
    'what's happening in Eastern Europe?' region match and its own pane page."""
    import urllib.parse
    region = urllib.parse.unquote(params["region"])
    # v6 §28 — countries.region now carries UN M49 sub-region names. A query
    # matches either one sub-region directly ('Eastern Europe') or a
    # colloquial/macro group ('Europe', 'Middle East') via m49.REGION_GROUPS,
    # which expands to its sub-regions plus any explicit extra countries.
    from ..geopolitics.m49 import REGION_GROUPS, REGION_GROUP_EXTRAS
    group = next((g for g in REGION_GROUPS if g.lower() == region.lower()), None)
    if group:
        subregions = REGION_GROUPS[group]
        extras = REGION_GROUP_EXTRAS.get(group, [])
        marks = ",".join("?" * len(subregions))
        sql = (f"SELECT id, name, iso2, region, status, flag_image_url FROM countries"
               f" WHERE region IN ({marks})")
        args = list(subregions)
        if extras:
            sql += f" OR id IN ({','.join('?' * len(extras))})"
            args += extras
        countries = query(sql + " ORDER BY name", args)
        region = group
    else:
        countries = query(
            "SELECT id, name, iso2, region, status, flag_image_url FROM countries"
            " WHERE region LIKE ? ORDER BY name", (f"%{region}%",))
    if not countries:
        return 404, {"error": f"no countries matched region '{region}'"}
    names = [c["name"] for c in countries]
    ids = [c["id"] for c in countries]
    # recent stories mentioning any country in the region
    like_clauses = " OR ".join(["f.who LIKE ? OR f.\"where\" LIKE ?"] * len(names))
    like_args = []
    for n in names:
        like_args += [f"%{n}%", f"%{n}%"]
    recent = query(
        "SELECT DISTINCT s.id, s.headline, s.last_updated_at FROM stories s"
        " JOIN story_members m ON m.story_id = s.id"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        f" WHERE s.is_synthetic = 0 AND ({like_clauses})"
        " ORDER BY s.last_updated_at DESC LIMIT 20", like_args) if names else []
    # conflicts with a party in the region
    marks = ",".join("?" * len(ids))
    conflicts = query(
        f"SELECT DISTINCT c.id, c.name, c.status FROM conflicts c"
        f" JOIN conflict_parties cp ON cp.conflict_id = c.id"
        f" WHERE cp.country_id IN ({marks})", ids) if ids else []
    return 200, {
        "region": region,
        "countries": [dict(c) for c in countries],
        "conflicts": [dict(c) for c in conflicts],
        "recent_stories": [dict(r) for r in recent],
    }


# ---------- v6 §16 — thematic map modes (CIA-Factbook-style data maps) ----------

# Registry-driven so a new mode is one entry, not new code (§16's "accept new
# modes cheaply"). Numeric modes choropleth a countries column; categorical
# modes color by distinct value; *_subnational modes add area polygons.
# v6.6 — nuclear-armed states, estimated warhead inventories (FAS/SIPRI 2025
# estimates, incl. Israel's undeclared arsenal)
NUCLEAR_WARHEADS = {"RUS": 5580, "USA": 5044, "CHN": 600, "FRA": 290,
                    "GBR": 225, "IND": 172, "PAK": 170, "ISR": 90, "PRK": 50}

MAP_MODES = {
    "hdi": {"label": "HDI", "kind": "numeric", "column": "hdi",
            "source": "UNDP Human Development Report", "icon": "◔"},
    "nuclear_arsenal": {"label": "Nuclear arsenals", "kind": "numeric",
                        "column": None, "source": "FAS/SIPRI estimates (2025)",
                        "icon": "☢", "log_scale": True},
    "gdp": {"label": "GDP (nominal)", "kind": "numeric", "column": "gdp_usd",
            "source": "World Bank Open Data", "icon": "$", "log_scale": True},
    "gdp_per_capita": {"label": "GDP per capita", "kind": "numeric",
                       "column": "gdp_per_capita_usd",
                       "source": "World Bank Open Data (derived)", "icon": "⌀",
                       "log_scale": True},
    "population": {"label": "Population", "kind": "numeric", "column": "population",
                   "source": "World Bank / UN Statistics", "icon": "◉",
                   "log_scale": True},
    "population_density": {"label": "Population density", "kind": "numeric",
                           "column": None,  # derived population / area_km2
                           "source": "World Bank / UN (derived)", "icon": "▦",
                           "log_scale": True},
    "religion": {"label": "Dominant religion", "kind": "categorical",
                 "column": "dominant_religion",
                 "source": "Pew Research Global Religious Landscape", "icon": "☯"},
    "language": {"label": "Dominant language", "kind": "categorical",
                 "column": "dominant_language",
                 "source": "Ethnologue / national censuses", "icon": "文"},
    "religion_subnational": {"label": "Religion (by area)", "kind": "categorical",
                             "column": "dominant_religion", "subnational": True,
                             "source": "Pew Research / national censuses", "icon": "☯²"},
    "language_subnational": {"label": "Language (by area)", "kind": "categorical",
                             "column": "dominant_language", "subnational": True,
                             "source": "Ethnologue / national censuses", "icon": "文²"},
}


@route("GET", "/api/mapmodes")
def mapmodes_list(params, q, body):
    return 200, {"modes": [{"id": k, "label": v["label"], "kind": v["kind"],
                            "icon": v["icon"], "source": v["source"],
                            "subnational": bool(v.get("subnational"))}
                           for k, v in MAP_MODES.items()]}


@route("GET", "/api/mapmodes/{mode}")
def mapmode_values(params, q, body):
    mode = MAP_MODES.get(params["mode"])
    if not mode:
        return 404, {"error": f"unknown map mode '{params['mode']}'"}
    if params["mode"] == "nuclear_arsenal":
        values = dict(NUCLEAR_WARHEADS)
    elif params["mode"] == "population_density":
        rows = query("SELECT id, population * 1.0 / area_km2 AS v FROM countries"
                     " WHERE population IS NOT NULL AND area_km2 > 0")
        values = {r["id"]: round(r["v"], 2) for r in rows}
    else:
        rows = query(f"SELECT id, {mode['column']} AS v FROM countries"
                     f" WHERE {mode['column']} IS NOT NULL")
        values = {r["id"]: r["v"] for r in rows}
    out = {"mode": params["mode"], "kind": mode["kind"], "label": mode["label"],
           "source": mode["source"], "values": values,
           "log_scale": bool(mode.get("log_scale"))}
    if mode["kind"] == "numeric":
        nums = sorted(values.values())
        out["min"] = nums[0] if nums else None
        out["max"] = nums[-1] if nums else None
    else:
        cats = sorted({v for v in values.values()})
        out["categories"] = cats
    if mode.get("subnational"):
        areas = []
        for a in query("SELECT country_id, name, zone_geojson, dominant_religion,"
                       " dominant_language, population FROM subnational_areas"):
            d = dict(a)
            try:
                d["zone_geojson"] = json.loads(d["zone_geojson"])
            except (json.JSONDecodeError, TypeError):
                continue
            d["value"] = d[mode["column"]]
            areas.append(d)
        out["areas"] = areas
        out["categories"] = sorted(set(out.get("categories", []))
                                   | {a["value"] for a in areas if a["value"]})
    return 200, out


@route("GET", "/api/alliances")
def alliances_list(params, q, body):
    rows = query("SELECT * FROM alliances ORDER BY name")
    out = []
    for r in rows:
        d = dict(r)
        d["members"] = [m["country_id"] for m in query(
            "SELECT country_id FROM alliance_memberships WHERE alliance_id = ?"
            " AND status = 'member'", (r["id"],))]
        out.append(d)
    from ..geopolitics.country_extra import ALLIANCE_LEADERS
    for _a in out:   # v6.6.1 — bloc leadership for the bloc panels
        if _a.get("name") in ALLIANCE_LEADERS:
            _a["leader"] = ALLIANCE_LEADERS[_a["name"]]
    return 200, {"alliances": out}


@route("GET", "/api/conflicts")
def conflicts_list(params, q, body):
    rows = query("SELECT * FROM conflicts ORDER BY"
                 " CASE status WHEN 'active' THEN 0 ELSE 1 END, started_at DESC")
    out = []
    for r in rows:
        d = dict(r)
        d["parties"] = [dict(p) for p in query(
            "SELECT cp.party_type, cp.role, cp.side, c.name AS country_name,"
            " c.id AS country_id, c.flag_image_url,"
            " n.name AS actor_name FROM conflict_parties cp"
            " LEFT JOIN countries c ON c.id = cp.country_id"
            " LEFT JOIN non_state_actors n ON n.id = cp.non_state_actor_id"
            " WHERE cp.conflict_id = ?", (r["id"],))]
        d["story_count"] = query_one(
            "SELECT COUNT(*) AS n FROM stories WHERE conflict_id = ?", (r["id"],))["n"]
        out.append(d)
    return 200, {"conflicts": out}


@route("GET", "/api/conflicts/{cid}/war_mode")
def war_mode(params, q, body):
    """v6 §8 — everything the dedicated conflict layout needs in one call:
    the conflict, its parties grouped by side (one color per side), the
    conflict-scoped subfactions with their zones, and a map frame (bbox)
    computed from the participants so the camera can zoom straight to the
    conflict zone."""
    import json as _json
    c = query_one("SELECT * FROM conflicts WHERE id = ?", (params["cid"],))
    if not c:
        return 404, {"error": "conflict not registered"}
    parties = [dict(p) for p in query(
        "SELECT cp.party_type, cp.role, cp.side, c.name AS country_name,"
        " c.id AS country_id, c.flag_image_url, c.capital,"
        " n.name AS actor_name, n.id AS actor_id, n.base_lat, n.base_lon"
        " FROM conflict_parties cp"
        " LEFT JOIN countries c ON c.id = cp.country_id"
        " LEFT JOIN non_state_actors n ON n.id = cp.non_state_actor_id"
        " WHERE cp.conflict_id = ?", (params["cid"],))]
    subfactions = []
    for sf in query("SELECT id, name, zone_geojson, side FROM conflict_subfactions"
                    " WHERE conflict_id = ?", (params["cid"],)):
        d = dict(sf)
        if d["zone_geojson"]:
            try:
                d["zone_geojson"] = _json.loads(d["zone_geojson"])
            except _json.JSONDecodeError:
                d["zone_geojson"] = None
        subfactions.append(d)
    # map frame: bbox over belligerents' capitals, NSA base coords, and
    # subfaction zone vertices — mediators/backers deliberately excluded so
    # a US-mediated conflict doesn't frame half the planet
    lats, lons = [], []
    for p in parties:
        if p["role"] != "belligerent":
            continue
        if p["country_id"]:
            cap = query_one("SELECT lat, lon FROM marked_locations WHERE category='capital'"
                            " AND country_id = ? LIMIT 1", (p["country_id"],))
            if cap:
                lats.append(cap["lat"]); lons.append(cap["lon"])
        elif p["base_lat"] is not None:
            lats.append(p["base_lat"]); lons.append(p["base_lon"])
    for sf in subfactions:
        gj = sf.get("zone_geojson")
        if gj and gj.get("coordinates"):
            for lon, lat in gj["coordinates"][0]:
                lats.append(lat); lons.append(lon)
    frame = None
    if lats:
        frame = {"min_lat": min(lats), "max_lat": max(lats),
                 "min_lon": min(lons), "max_lon": max(lons),
                 "center_lat": sum(lats) / len(lats),
                 "center_lon": sum(lons) / len(lons)}
    # infobox key facts
    stories_n = query_one("SELECT COUNT(*) AS n FROM stories WHERE conflict_id = ?",
                          (params["cid"],))["n"]
    recent = [dict(r) for r in query(
        "SELECT id, headline, last_updated_at FROM stories WHERE conflict_id = ?"
        " AND is_synthetic = 0 ORDER BY last_updated_at DESC LIMIT 5", (params["cid"],))]
    # v6.1 — real side NAMES (Russia / Ukraine), not "Side A" / "Side B".
    # Each side is named after its belligerent(s); "& allies" when a side's
    # belligerent has backers.
    def _party_name(p):
        return p.get("country_name") or p.get("actor_name") or "?"
    side_names = {}
    for s in ("a", "b"):
        belligs = [_party_name(p) for p in parties
                   if p["side"] == s and p["role"] == "belligerent"]
        backers = [p for p in parties if p["side"] == s and p["role"] == "backer"]
        if belligs:
            label = " / ".join(belligs[:2])
            if backers:
                label += " & allies"
            side_names[s] = label
    return 200, {"conflict": dict(c), "parties": parties, "subfactions": subfactions,
                 "frame": frame, "story_count": stories_n, "recent_stories": recent,
                 "side_names": side_names}


OOB_PROMPT = """You are a military-history analyst. From the CONTEXT (a conflict, its
belligerents and backers by side, start date, summary, and recent tracked
story headlines) write a structured order-of-battle and tactical history.

Return ONLY valid JSON:
{
  "order_of_battle": string,          // 2-4 sentences: the forces on each side
  "offensives": [string, ...],        // chronological major phases/offensives from the war's start to now, one bullet each
  "tactics_evolution": string,        // how each side's tactics evolved over the war
  "global_ramifications": string      // wider geopolitical/economic ramifications, referencing the tracked developments where relevant
}
Be accurate and concrete; never invent specific casualty numbers. Ground the
ramifications in the provided story headlines where you can."""


@route("GET", "/api/conflicts/{cid}/order_of_battle")
def order_of_battle(params, q, body):
    """v6.1.1 — AI order-of-battle + tactical history for War Mode, generated
    once and cached (regenerated only if missing). Lazy/separate from the
    war_mode call so entering War Mode stays fast. Degrades to a scaffold
    without an AI provider."""
    import json as _json
    from ..processing import llm
    from ..db.models import meta_get, meta_set
    c = query_one("SELECT * FROM conflicts WHERE id = ?", (params["cid"],))
    if not c:
        return 404, {"error": "conflict not registered"}
    cache_key = f"oob:{c['id']}"
    cached = meta_get(cache_key)
    if cached:
        try:
            return 200, {"order_of_battle": _json.loads(cached), "cached": True}
        except _json.JSONDecodeError:
            pass
    parties = [dict(p) for p in query(
        "SELECT cp.role, cp.side, co.name AS country_name, n.name AS actor_name"
        " FROM conflict_parties cp LEFT JOIN countries co ON co.id = cp.country_id"
        " LEFT JOIN non_state_actors n ON n.id = cp.non_state_actor_id"
        " WHERE cp.conflict_id = ?", (c["id"],))]
    stories = [r["headline"] for r in query(
        "SELECT headline FROM stories WHERE conflict_id = ? AND is_synthetic = 0"
        " ORDER BY last_updated_at DESC LIMIT 20", (c["id"],))]
    if not llm.available():
        return 200, {"order_of_battle": None, "ai_available": False,
                     "note": "AI order-of-battle needs a configured provider "
                             "(add a free Groq key in Settings)."}
    ctx = {"conflict": c["name"], "started_at": c["started_at"],
           "summary": c["summary"],
           "parties": [{"name": p["country_name"] or p["actor_name"],
                        "side": p["side"], "role": p["role"]} for p in parties],
           "recent_headlines": stories}
    text = llm.complete(OOB_PROMPT, [{"role": "user", "content": _json.dumps(ctx)}],
                        max_tokens=1100, timeout=45)
    if not text:
        return 200, {"order_of_battle": None, "ai_available": True,
                     "note": "generation returned nothing — try again shortly."}
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    if not text.startswith("{"):
        b = text.find("{")
        if b != -1:
            text = text[b:text.rfind("}") + 1]
    try:
        oob = _json.loads(text)
    except _json.JSONDecodeError:
        return 200, {"order_of_battle": None, "note": "malformed AI response."}
    meta_set(cache_key, _json.dumps(oob))
    return 200, {"order_of_battle": oob, "cached": False}


def _wiki_rest_image(clean: str) -> str:
    """Path 1 — Wikipedia REST summary (follows redirects, lead image)."""
    import json as _json
    import urllib.parse
    import urllib.request
    from ..processing import llm as _llm
    title = urllib.parse.quote(clean.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}?redirect=true"
    try:
        req = urllib.request.Request(url, headers={"user-agent": _llm.USER_AGENT,
                                                   "accept": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = _json.loads(resp.read())
        if data.get("type") == "disambiguation":
            return ""
        # v6.6 — prefer the THUMBNAIL: it's the infobox portrait (a proper
        # professional headshot crop) rather than a possibly full-body original
        return ((data.get("thumbnail") or {}).get("source")
                or (data.get("originalimage") or {}).get("source") or "")
    except Exception:  # noqa: BLE001 — best-effort
        return ""


def _wiki_action_image(clean: str) -> str:
    """Path 2 — the action API's pageimages, with a search step first so a
    name that isn't the exact article title still resolves (e.g. a leader
    whose stored name differs from their Wikipedia page title). This is the
    reliable path the single REST-title guess was missing (v6.3)."""
    import json as _json
    import urllib.parse
    import urllib.request
    from ..processing import llm as _llm

    def _get(url):
        req = urllib.request.Request(url, headers={"user-agent": _llm.USER_AGENT,
                                                   "accept": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            return _json.loads(resp.read())

    base = "https://en.wikipedia.org/w/api.php"
    # resolve the best-matching article title by search (handles name drift)
    title = clean
    try:
        sq = urllib.parse.urlencode({"action": "query", "list": "search",
                                     "srsearch": clean, "srlimit": "1",
                                     "format": "json"})
        sr = _get(f"{base}?{sq}").get("query", {}).get("search", [])
        if sr:
            title = sr[0].get("title") or clean
    except Exception:  # noqa: BLE001 — fall back to the raw name
        pass
    try:
        pq = urllib.parse.urlencode({"action": "query", "titles": title,
                                     "prop": "pageimages", "piprop": "original|thumbnail",
                                     "pithumbsize": "320", "redirects": "1",
                                     "format": "json"})
        pages = _get(f"{base}?{pq}").get("query", {}).get("pages", {})
        for _pid, page in pages.items():
            img = ((page.get("original") or {}).get("source")
                   or (page.get("thumbnail") or {}).get("source") or "")
            if img:
                return img
    except Exception:  # noqa: BLE001
        pass
    return ""


@route("GET", "/api/leader-profile")
def leader_profile(params, q, body):
    """v6.6 — a personal panel for any world leader: role/party/tenure from the
    leadership table + a Wikipedia biography extract fetched on demand."""
    name = (q.get("name") or "").strip()
    if not name:
        return 400, {"error": "name required"}
    clean = name.split("(")[0].strip()
    rows = [dict(r) for r in query(
        "SELECT l.*, c.name AS country_name, c.flag_image_url FROM country_leadership l"
        " JOIN countries c ON c.id = l.country_id WHERE l.name LIKE ?",
        (clean + "%",))]
    bio = None
    try:
        import json as _json
        import urllib.request as _rq
        from ..processing import llm as _llm
        url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
               + urllib.parse.quote(clean.replace(" ", "_")) + "?redirect=true")
        req = _rq.Request(url, headers={"user-agent": _llm.USER_AGENT,
                                        "accept": "application/json"})
        with _rq.urlopen(req, timeout=6) as resp:
            d = _json.loads(resp.read())
        if d.get("type") != "disambiguation":
            bio = {"extract": d.get("extract"), "description": d.get("description"),
                   "url": (d.get("content_urls", {}).get("desktop", {}) or {}).get("page"),
                   "image_url": ((d.get("thumbnail") or {}).get("source"))}
    except Exception:  # noqa: BLE001 — offline/blocked: roles still render
        pass
    return 200, {"name": clean, "roles": rows, "bio": bio}


@route("GET", "/api/leader-portrait")
def leader_portrait(params, q, body):
    """v6.2/v6.3 — fetch a leader's portrait from Wikipedia, cached in app_meta.
    Called on-demand when a country profile has a leader with no photo yet, so
    e.g. Xi Jinping shows next to the China flag immediately. v6.3 makes this
    RELIABLE: it tries the REST summary lead image first, then the action API's
    pageimages with a search step (so a name that isn't the exact article title
    still resolves) — the single REST-title guess used to silently miss for many
    leaders. Best-effort: returns image_url or null."""
    from ..db.models import meta_get, meta_set
    name = (q.get("name") or "").strip()
    if not name:
        return 400, {"error": "name required"}
    # normalize: drop parenthetical office notes ("(Supreme Leader)")
    clean = name.split("(")[0].strip()
    cache_key = f"portrait:{clean.lower()}"
    cached = meta_get(cache_key)
    if cached:
        return 200, {"name": clean, "image_url": cached, "cached": True}
    image = _wiki_rest_image(clean) or _wiki_action_image(clean)
    if image:
        meta_set(cache_key, image)   # only cache hits (retry misses next time)
        # also persist onto the leadership row so it survives without a re-fetch
        try:
            with write_tx() as conn:
                conn.execute("UPDATE country_leadership SET image_url = ?"
                             " WHERE name = ? AND (image_url IS NULL OR image_url = '')",
                             (image, name))
        except Exception:  # noqa: BLE001
            pass
    return 200, {"name": clean, "image_url": image or None, "cached": False}


def _un_sub_orgs():
    from ..geopolitics.un_data import UN_SUB_ORGS
    return UN_SUB_ORGS


@route("GET", "/api/un")
def un_overview(params, q, body):
    """v6.1 — United Nations panel: Security Council composition (permanent +
    elected members) and notable resolutions with their recorded vote tallies
    for the parliamentary vote graphic."""
    from ..geopolitics import un_data as u

    def _flag(iso3):
        r = query_one("SELECT flag_image_url FROM countries WHERE id = ?", (iso3,))
        return r["flag_image_url"] if r else None

    def _name(iso3):
        r = query_one("SELECT name FROM countries WHERE id = ?", (iso3,))
        return r["name"] if r else iso3

    permanent = [{"id": i, "name": _name(i), "flag_image_url": _flag(i)}
                 for i in u.UNSC_PERMANENT]
    elected = []
    for iso, disp, term in u.UNSC_ELECTED:
        real = u.ELECTED_ISO_FIX.get(iso, iso)
        elected.append({"id": real, "name": disp, "term": term,
                        "flag_image_url": _flag(real)})
    resolutions = []
    for r in u.RESOLUTIONS:
        nv = []
        for iso, vote in r["notable_votes"].items():
            real = u.ELECTED_ISO_FIX.get(iso, iso)
            nv.append({"id": real, "name": _name(real), "vote": vote,
                       "flag_image_url": _flag(real)})
        resolutions.append({**r, "notable_votes": nv})
    return 200, {"sub_orgs": _un_sub_orgs(),   # v6.6 — agency subtab data
        "security_council": {"permanent": permanent, "elected": elected},
                 "other_councils": [{"name": n, "note": d} for n, d in u.OTHER_COUNCILS],
                 "resolutions": resolutions}


@route("POST", "/api/conflicts/confirm_tag")
def confirm_conflict_tag(params, q, body):
    """§15.1 — one-click resolve of a suggested conflict tag."""
    if not isinstance(body, dict) or not body.get("story_id"):
        return 400, {"error": "body must be {story_id, confirm: true|false}"}
    story = query_one("SELECT suggested_conflict_id FROM stories WHERE id = ?",
                      (body["story_id"],))
    if not story:
        return 404, {"error": "story not found"}
    with write_tx() as conn:
        if body.get("confirm") and story["suggested_conflict_id"]:
            conn.execute(
                "UPDATE stories SET conflict_id = suggested_conflict_id,"
                " suggested_conflict_id = NULL WHERE id = ?", (body["story_id"],))
            conn.execute(
                "UPDATE events SET conflict_id = ? WHERE id IN"
                " (SELECT event_id FROM story_members WHERE story_id = ?"
                "  AND event_id IS NOT NULL)",
                (story["suggested_conflict_id"], body["story_id"]))
        else:
            conn.execute("UPDATE stories SET suggested_conflict_id = NULL WHERE id = ?",
                         (body["story_id"],))
    return 200, {"ok": True}


@route("GET", "/api/actors")
def actors_list(params, q, body):
    rows = query(
        "SELECT n.*, c.name AS affiliated_state_name FROM non_state_actors n"
        " LEFT JOIN countries c ON c.id = n.affiliated_state_id ORDER BY n.name")
    out = []
    for r in rows:
        d = dict(r)
        d["conflicts"] = [dict(p) for p in query(
            "SELECT c.id, c.name, cp.role FROM conflict_parties cp"
            " JOIN conflicts c ON c.id = cp.conflict_id"
            " WHERE cp.non_state_actor_id = ?", (r["id"],))]
        # v5 §11 — rough territory zones for the NSA map layer
        d["zones"] = [{"confidence": z["confidence"],
                       "geojson": json.loads(z["zone_geojson"])}
                      for z in query(
            "SELECT confidence, zone_geojson FROM non_state_actor_zones"
            " WHERE non_state_actor_id = ?", (r["id"],))]
        out.append(d)
    return 200, {"actors": out}


@route("GET", "/api/nsa-zones")
def nsa_zones(params, q, body):
    """v5 §11 — all NSA territory zones for the map layer, one call."""
    rows = query(
        "SELECT z.confidence, z.zone_geojson, n.id AS nsa_id, n.name AS nsa_name"
        " FROM non_state_actor_zones z JOIN non_state_actors n"
        " ON n.id = z.non_state_actor_id")
    return 200, {"zones": [{"nsa_id": r["nsa_id"], "nsa_name": r["nsa_name"],
                            "confidence": r["confidence"],
                            "geojson": json.loads(r["zone_geojson"])} for r in rows]}


@route("GET", "/api/orgs")
def orgs_list(params, q, body):
    return 200, {"organizations": [dict(r) for r in query(
        "SELECT * FROM international_organizations ORDER BY name")]}


@route("GET", "/api/marked-locations")
def marked_locations(params, q, body):
    rows = query("SELECT m.*, c.name AS country_name FROM marked_locations m"
                 " LEFT JOIN countries c ON c.id = m.country_id ORDER BY m.category, m.name")
    return 200, {"locations": [dict(r) for r in rows]}


@route("GET", "/api/relations")
def relations_matrix(params, q, body):
    """§19 — the full bilateral-relations picture at once."""
    rows = query(
        "SELECT br.*, ca.name AS country_a_name, cb.name AS country_b_name"
        " FROM bilateral_relations br"
        " JOIN countries ca ON ca.id = br.country_a_id"
        " JOIN countries cb ON cb.id = br.country_b_id"
        " ORDER BY br.last_updated_at DESC")
    parsed = []
    for r in rows:
        d = dict(r)
        if d.get("source_story_ids"):
            d["source_story_ids"] = json.loads(d["source_story_ids"])
        parsed.append(d)
    return 200, {"relations": parsed}


@route("GET", "/api/satellites")
def satellites(params, q, body):
    """§10.2 — cached TLEs for client-side propagation."""
    raw = meta_get("tle_data")
    if not raw:
        return 200, {"fetched_at": None, "satellites": [],
                     "note": "TLE data not yet fetched (daily CelesTrak job)"}
    return 200, json.loads(raw)


_prov_cache = {"at": 0.0, "result": None}


@route("GET", "/api/provenance")
def provenance_status(params, q, body):
    """§11 — walk the hash chains; cached 10 minutes (it's O(n))."""
    from ..processing.provenance import verify_all
    now = time.time()
    if _prov_cache["result"] is None or now - _prov_cache["at"] > 600 \
            or q.get("force") == "1":
        _prov_cache["result"] = verify_all()
        _prov_cache["result"]["verified_at"] = now_iso()
        _prov_cache["at"] = now
    return 200, _prov_cache["result"]


@route("GET", "/api/lineage/{fact_id}")
def lineage(params, q, body):
    """§8 — walk lineage_edges forward (BFS) from one fact."""
    root_id = params["fact_id"]
    root = query_one(
        'SELECT id, who, what, "where" AS where_text, when_occurred FROM extracted_facts'
        " WHERE id = ?", (root_id,))
    if not root:
        return 404, {"error": "fact not found"}
    nodes = {root_id: {**dict(root), "depth": 0}}
    edges = []
    frontier = [root_id]
    for depth in range(1, 7):  # bounded walk
        if not frontier or len(nodes) > 120:
            break
        marks = ",".join("?" * len(frontier))
        rows = query(
            f"SELECT le.from_fact_id, le.to_fact_id, le.via_story_id, le.created_at,"
            f' s.headline, f.who, f.what, f."where" AS where_text, f.when_occurred'
            f" FROM lineage_edges le"
            f" JOIN stories s ON s.id = le.via_story_id"
            f" JOIN extracted_facts f ON f.id = le.to_fact_id"
            f" WHERE le.from_fact_id IN ({marks})", frontier)
        frontier = []
        for r in rows:
            edges.append({"from": r["from_fact_id"], "to": r["to_fact_id"],
                          "via_story_id": r["via_story_id"], "headline": r["headline"]})
            if r["to_fact_id"] not in nodes:
                nodes[r["to_fact_id"]] = {
                    "id": r["to_fact_id"], "who": r["who"], "what": r["what"],
                    "where_text": r["where_text"], "when_occurred": r["when_occurred"],
                    "depth": depth}
                frontier.append(r["to_fact_id"])
    return 200, {"root": root_id, "nodes": list(nodes.values()), "edges": edges}
