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
    # led by the PM — but NOT semi-presidential, where the president dominates.
    # v6.6.4 — a CONSTITUTIONAL monarchy is PM-led too (owner: "Frederick X of
    # Denmark should NOT be listed as the actual main leader"); only ABSOLUTE
    # monarchies keep the monarch as paramount.
    parliamentary_led = ("parliamentary" in g and "semi-presidential" not in g) or \
        ("monarchy" in g and "absolute" not in g)
    if parliamentary_led:
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
    # v7 (owner) — a territory/autonomous region shows its OWN elected head,
    # never the sovereign's ceremonial monarch (King Frederik X was appearing
    # as "leader" of Greenland/Faroe via synced head_of_state rows). If the
    # territory has a local head_of_government, drop monarch-style
    # head_of_state rows entirely from its leadership list.
    if profile.get("status") == "territory":
        roles = {l["role"] for l in profile["leadership"]}
        if "head_of_government" in roles:
            profile["leadership"] = [
                l for l in profile["leadership"] if l["role"] != "head_of_state"]
    # v6.1 — which office actually leads the country. The UI must feature the
    # PARAMOUNT leader (Xi Jinping for China, not Premier Li Qiang; Putin for
    # Russia), which the naive "prefer prime minister" rule got wrong. Derive
    # it from the government type, with explicit overrides for the handful of
    # systems where the label doesn't tell the whole story.
    profile["paramount_role"] = _paramount_role(iso3, profile.get("government_type"),
                                                profile["leadership"])
    profile["paramount_title"] = _PARAMOUNT_TITLE.get(iso3)
    # v7 Part 6 — curated world-knowledge dossier, rendered instantly on open
    from ..geopolitics.world_knowledge import country_knowledge
    profile["knowledge"] = country_knowledge(iso3, profile)
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
    if not profile["legislature"]:   # v6.6.2 — explain absence instead of blank
        from ..geopolitics.country_extra import LEGISLATURE_NOTES
        profile["legislature_note"] = LEGISLATURE_NOTES.get(iso3) or (
            "No detailed seat composition is on file yet for this country's "
            "legislature. It will populate on the next data sync.")
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
    from ..geopolitics.country_extra import derive_alignments
    _al = derive_alignments(iso3)   # v6.6.2 — derived for EVERY country now
    if _al:
        profile["alignments"] = _al
    # v7.4.1 — autonomous regions inside this country (Iraq → Kurdistan, etc.)
    from ..geopolitics.autonomous_zones import zones_list as _az_list
    _azs = [z for z in _az_list() if z["parent"].lower() == (profile.get("name") or "").lower()]
    if _azs:
        profile["autonomous_zones"] = _azs
    # v7.4.1 — "other languages": ALL significant languages spoken in the country
    # (owner). Prefer the curated full list; else fall back to the remaining
    # official languages beyond the primary so the row is never empty.
    from ..geopolitics.country_extra import COUNTRY_OTHER_LANGUAGES
    _other = COUNTRY_OTHER_LANGUAGES.get(iso3)
    if not _other:
        _langs = profile.get("languages")
        if isinstance(_langs, str):
            try:
                _langs = json.loads(_langs)
            except (json.JSONDecodeError, TypeError):
                _langs = [_langs]
        _other = list(_langs or [])
    if _other:
        profile["other_languages"] = _other
    ag = query_one("SELECT * FROM country_agenda_synthesis WHERE country_id = ?", (iso3,))
    profile["agenda"] = dict(ag) if ag else None
    if profile["agenda"] and profile["agenda"].get("source_story_ids"):
        profile["agenda"]["source_story_ids"] = json.loads(
            profile["agenda"]["source_story_ids"])
    # v7.4.1 — every country shows a filled agenda: fall back to the curated
    # floor (composed from alignment + region) when no AI synthesis exists yet.
    if not profile["agenda"] or not (profile["agenda"].get("geopolitical_agenda")):
        from ..geopolitics.synthesis import curated_agenda
        ca = curated_agenda(iso3, profile)
        if ca:
            profile["agenda"] = ca
    trade = query_one("SELECT * FROM country_trade_stats WHERE country_id = ?", (iso3,))
    profile["trade"] = dict(trade) if trade else None
    profile["memberships"] = [dict(r) for r in query(
        "SELECT a.id AS alliance_id, a.name, a.type, am.status"
        " FROM alliance_memberships am"
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


COUNTRY_STAT_PROMPT = """You are an economic/demographic analyst. For the given
country and METRIC, produce a structured breakdown grounded in well-known
national figures.

Return ONLY valid JSON:
{
  "summary": string,                        // 2-3 sentences on this metric for the country
  "distribution_label": string,             // e.g. "Largest cities" or "By region"
  "distribution": [{"label": str, "value": number, "display": str}, ...],  // 4-8 items
  "composition_label": string,              // e.g. "GDP by sector" (may be empty [])
  "composition": [{"label": str, "value": number, "display": str}, ...],
  "trajectory": [{"label": str, "value": number, "display": str}, ...],    // 4-8 points over years
  "notes": [string, ...]                    // 1-3 caveats
}
For population: distribution = largest cities by population; composition may be
urban vs rural; trajectory = population over recent decades. For gdp: distribution
= largest economic regions/states; composition = GDP by sector (agriculture/
industry/services); trajectory = GDP over recent years. 'value' is a raw number
for bar sizing; 'display' is the human-readable label ("21.5M", "$3.2T", "58%").
Use your general knowledge; approximate is fine. Keep it factual, not invented
precision."""


@route("GET", "/api/country-stat")
def country_stat(params, q, body):
    """v6.6.5 — a drill-down breakdown for a country statistic (population/GDP/
    etc.): distribution by city/region, sector composition, and a growth
    trajectory. AI-synthesized from known national figures (cached), so a
    stat cell click always opens something useful without a vendored dataset."""
    import json as _json
    from ..db.models import meta_get, meta_set
    from ..processing import llm
    iso3 = (q.get("iso3") or "").upper()
    metric = (q.get("metric") or "population").lower()
    c = query_one("SELECT id, name, population, gdp_usd, gdp_per_capita_usd, area_km2,"
                  " region FROM countries WHERE id = ?", (iso3,))
    if not c:
        return 404, {"error": "country not registered"}
    headline = {"population": c["population"], "gdp": c["gdp_usd"],
                "gdp_per_capita": c["gdp_per_capita_usd"], "area": c["area_km2"]}.get(metric)
    key = f"cstat:{iso3}:{metric}"
    cached = meta_get(key)
    if cached:
        try:
            return 200, {"headline": headline, "detail": _json.loads(cached)}
        except _json.JSONDecodeError:
            pass
    if not llm.available():
        return 200, {"headline": headline, "detail": None}
    # v6.6.6 — NON-BLOCKING: generate in the background so the stat pane opens
    # instantly (same fix as leader/party pages); frontend re-fetches to upgrade.
    from ..processing.bg_synth import kick
    ctx = {"country": c["name"], "metric": metric, "region": c["region"],
           "population": c["population"], "gdp_usd": c["gdp_usd"],
           "area_km2": c["area_km2"]}
    pending = kick(key, lambda: _generate_country_stat(key, ctx))
    return 200, {"headline": headline, "detail": None, "detail_pending": pending}


def _generate_country_stat(key, ctx):
    """v6.6.6 — background country-stat detail generation + cache."""
    from ..processing import llm
    from ..db.models import meta_set
    text = llm.complete(COUNTRY_STAT_PROMPT,
                        [{"role": "user", "content": _json.dumps(ctx)}],
                        max_tokens=900, timeout=90, json_mode=True)
    if not text:
        return
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").removeprefix("json").strip()
    b = t.find("{")
    if b != -1:
        t = t[b:t.rfind("}") + 1]
    try:
        detail = _json.loads(t)
    except _json.JSONDecodeError:
        return
    meta_set(key, _json.dumps(detail))


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

# v8.9 — exactly the owner's ten modes. The two broad categoricals (religion /
# language) gained finer siblings (religious_sect / dialect); the old
# *_subnational area modes are gone (superseded by the tier-aware ?level=N path,
# which redraws ANY mode per administrative unit). `field` names the
# admin_thematic field a categorical mode resolves per unit.
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
    "religion": {"label": "Religion", "kind": "categorical",
                 "column": "dominant_religion", "field": "religion",
                 "source": "Pew Research Global Religious Landscape", "icon": "☯"},
    "religious_sect": {"label": "Religious sect", "kind": "categorical",
                       "column": "dominant_religion", "field": "sect",
                       "source": "Curated (Pew / national censuses)", "icon": "☪"},
    "language": {"label": "Language", "kind": "categorical",
                 "column": "dominant_language", "field": "language",
                 "source": "Ethnologue / national censuses", "icon": "文"},
    "dialect": {"label": "Dialect", "kind": "categorical",
                "column": "dominant_language", "field": "dialect",
                "source": "Curated (Ethnologue / glottolog)", "icon": "语"},
}


@route("GET", "/api/mapmodes")
def mapmodes_list(params, q, body):
    return 200, {"modes": [{"id": k, "label": v["label"], "kind": v["kind"],
                            "icon": v["icon"], "source": v["source"]}
                           for k, v in MAP_MODES.items()]}


def _unit_level_values(mode_id, mode, level):
    """v8.9 — compute the mode's value for every administrative unit at `level`,
    keyed by uid. Numeric modes read the curated per-unit demographics (units
    without their own figure are omitted, so they fall through to the country
    choropleth underneath). Categorical modes resolve religion/sect/language/
    dialect per unit via the curated sub-national layer over the country value.
    """
    from ..geopolitics import admin_atlas, admin_demographics, admin_thematic
    units = [u for u in admin_atlas.units() if u.get("level") == level]
    cc = {r["id"]: dict(r) for r in
          query("SELECT id, dominant_religion, dominant_language FROM countries")}
    values = {}
    if mode["kind"] == "categorical":
        field = mode["field"]
        for u in units:
            iso3 = u.get("country")
            base = cc.get(iso3, {})
            v = admin_thematic.unit_value(
                iso3, u.get("name"), field,
                base.get("dominant_religion"), base.get("dominant_language"))
            if v:
                values[u["uid"]] = v
        return values, sorted({v for v in values.values()})
    # numeric — only where a curated own figure exists for the unit
    for u in units:
        iso3, name = u.get("country"), u.get("name")
        area = u.get("area_km2") or 0
        dem = admin_demographics.lookup(iso3, name, area) if level == 1 else None
        pop = dem.get("pop") if dem else None
        gdp = dem.get("gdp") if dem else None
        if mode_id == "population" and pop:
            values[u["uid"]] = pop
        elif mode_id == "population_density" and pop and area > 0:
            values[u["uid"]] = round(pop / area, 2)
        elif mode_id == "gdp" and gdp:
            values[u["uid"]] = gdp
        elif mode_id == "gdp_per_capita" and gdp and pop:
            values[u["uid"]] = round(gdp / pop, 2)
        # hdi / nuclear_arsenal have no per-unit figure → left to the country base
    nums = sorted(values.values())
    return values, (nums[0] if nums else None, nums[-1] if nums else None)


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
        # v8.9 — sect/dialect country-base come from the curated overlay, not a
        # column (the DB only carries broad religion/language).
        if mode.get("field") == "sect":
            from ..geopolitics import admin_thematic
            values = {}
            for r in rows:
                values[r["id"]] = admin_thematic.country_sect(r["id"]) or r["v"]
        elif mode.get("field") == "dialect":
            from ..geopolitics import admin_thematic
            values = {}
            for r in rows:
                values[r["id"]] = admin_thematic.country_dialect(r["id"]) or r["v"]
        else:
            values = {r["id"]: r["v"] for r in rows}
    out = {"mode": params["mode"], "kind": mode["kind"], "label": mode["label"],
           "source": mode["source"], "values": values,
           "log_scale": bool(mode.get("log_scale"))}
    if mode["kind"] == "numeric":
        nums = sorted(values.values())
        out["min"] = nums[0] if nums else None
        out["max"] = nums[-1] if nums else None
    else:
        out["categories"] = sorted({v for v in values.values()})
    # v8.9 — tier-aware per-admin-unit values (keyed by uid) when ?level=N is set
    try:
        level = int(q.get("level") or 0)
    except (TypeError, ValueError):
        level = 0
    if level in (1, 2, 3):
        uvals, meta = _unit_level_values(params["mode"], mode, level)
        out["level"] = level
        out["unit_values"] = uvals
        if mode["kind"] == "numeric":
            out["unit_min"], out["unit_max"] = meta
        else:
            out["categories"] = sorted(set(out.get("categories", [])) | set(meta))
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


@route("GET", "/api/alliance/{aid}")
def alliance_profile(params, q, body):
    """v6.6.2 — the full bloc panel (owner: NATO/CSTO/EU/etc. should open pages
    like the UN). One call returns: the bloc record + leader, its members with
    flags and key stats, aggregate statistics, purpose/HQ/policies/measures,
    the conflicts its members are party to (for military blocs), recent tracked
    stories mentioning it, and — for the EU — a parliament breakdown."""
    from ..geopolitics.country_extra import (ALLIANCE_LEADERS, ALLIANCE_PROFILES,
                                             ALLIANCE_EMBLEMS, EU_PARLIAMENT)
    a = query_one("SELECT * FROM alliances WHERE id = ?", (params["aid"],))
    if a is not None:
        from ..geopolitics.world_knowledge import alliance_knowledge
    if not a:
        return 404, {"error": "alliance not registered"}
    out = dict(a)
    out["knowledge"] = alliance_knowledge(out["name"])   # v7 Part 6
    if out["name"] in ALLIANCE_LEADERS:
        out["leader"] = ALLIANCE_LEADERS[out["name"]]
    # v7.6 — real bloc flag/emblem (owner: "use real flags and logos for bloc panels")
    out["emblem_url"] = ALLIANCE_EMBLEMS.get(out["name"]) or (
        out.get("emblem_url") if isinstance(a, dict) else None)
    prof = ALLIANCE_PROFILES.get(out["name"])
    if prof:
        out["profile"] = prof
    # members with display data + running stat totals
    members = query(
        "SELECT c.id, c.name, c.flag_image_url, c.population, c.gdp_usd, c.region,"
        " am.status FROM alliance_memberships am JOIN countries c ON c.id = am.country_id"
        " WHERE am.alliance_id = ? ORDER BY c.name", (params["aid"],))
    out["members"] = [dict(m) for m in members]
    member_ids = [m["id"] for m in members if m["status"] == "member"]
    tot_pop = sum(m["population"] or 0 for m in members if m["status"] == "member")
    tot_gdp = sum(m["gdp_usd"] or 0 for m in members if m["status"] == "member")
    out["stats"] = {"member_count": len(member_ids), "total_population": tot_pop,
                    "total_gdp_usd": tot_gdp}
    # conflicts any member is a party to (esp. relevant for military blocs)
    if member_ids:
        marks = ",".join("?" * len(member_ids))
        out["conflicts"] = [dict(r) for r in query(
            f"SELECT DISTINCT c.id, c.name, c.status FROM conflicts c"
            f" JOIN conflict_parties cp ON cp.conflict_id = c.id"
            f" WHERE cp.country_id IN ({marks})"
            f" ORDER BY CASE c.status WHEN 'active' THEN 0 ELSE 1 END", member_ids)]
    else:
        out["conflicts"] = []
    # recent tracked stories mentioning the bloc by name (FTS-lite LIKE)
    out["recent_stories"] = [dict(r) for r in query(
        "SELECT DISTINCT s.id, s.headline, s.last_updated_at FROM stories s"
        " JOIN story_members m ON m.story_id = s.id"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE s.is_synthetic = 0 AND (f.who LIKE ? OR f.what LIKE ?)"
        " ORDER BY s.last_updated_at DESC LIMIT 8",
        (f"%{a['name']}%", f"%{a['name']}%"))]
    if out["name"] in ("EU", "European Union"):   # EU panel parliament breakdown
        out["parliament"] = EU_PARLIAMENT
    return 200, out


@route("GET", "/api/conflicts")
def conflicts_list(params, q, body):
    rows = query("SELECT * FROM conflicts ORDER BY"
                 " CASE status WHEN 'active' THEN 0 ELSE 1 END, started_at DESC")
    from ..geopolitics.world_knowledge import conflict_knowledge
    out = []
    for r in rows:
        d = dict(r)
        d["knowledge"] = conflict_knowledge(r["name"])   # v7 Part 6
        d["parties"] = [dict(p) for p in query(
            "SELECT cp.party_type, cp.role, cp.side, c.name AS country_name,"
            " c.id AS country_id, c.flag_image_url,"
            " n.name AS actor_name FROM conflict_parties cp"
            " LEFT JOIN countries c ON c.id = cp.country_id"
            " LEFT JOIN non_state_actors n ON n.id = cp.non_state_actor_id"
            " WHERE cp.conflict_id = ?", (r["id"],))]
        d["story_count"] = query_one(
            "SELECT COUNT(*) AS n FROM stories WHERE conflict_id = ?", (r["id"],))["n"]
        d["event_count"] = query_one(
            "SELECT COUNT(*) AS n FROM events WHERE conflict_id = ?", (r["id"],))["n"]
        # v8.13 — combined activity drives the directory order (owner: "order by
        # the highest number of stories/events to lowest").
        d["activity_count"] = (d["story_count"] or 0) + (d["event_count"] or 0)
        out.append(d)
    from ..geopolitics.seed_data import INSURGENCY_NAMES
    for _c in out:   # v6.6.5 — flag insurgencies for their own tab
        _c["is_insurgency"] = (_c.get("name") in INSURGENCY_NAMES
                               or "insurgency" in (_c.get("name") or "").lower())
    # v8.13 — most-active conflict first (the frontend tabs still filter by
    # status, so within each tab the busiest conflict leads). Active status is
    # only a tiebreak so a 0-activity ongoing conflict still beats a 0-activity
    # resolved one.
    out.sort(key=lambda c: (c["activity_count"],
                            0 if c.get("status") == "active" else -1,
                            c.get("started_at") or ""), reverse=True)
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


LEADER_PROFILE_PROMPT = """You are a political biographer. From the CONTEXT (a
world leader's name, the office(s) they hold, their party, and — when available
— a Wikipedia biography extract) write a comprehensive, neutral structured
profile of this specific real person.

Return ONLY valid JSON:
{
  "summary": string,                 // 2-4 sentences: who they are and why they matter now
  "ideology": string,                // their political ideology / orientation, one line
  "career_history": [string, ...],   // 4-7 bullets: prior professions & positions, roughly chronological
  "party_history": [string, ...],    // 1-4 bullets: party affiliations over time
  "key_policies": [string, ...]      // 4-7 bullets: signature policies / positions / agenda
}
Draw on your general knowledge of this well-known public figure — a Wikipedia
extract may NOT be provided, and you should still write a full, accurate
profile from what you know about them. Be factual and neutral; do not invent
oddly specific dates or figures you're unsure of, but DO give a genuinely
informative, detailed profile. If you truly don't recognize the person, keep
each field short and general rather than fabricating."""


def _wiki_intro_extract(clean):
    """v6.6.2 — a fuller multi-paragraph intro (action API extracts, plaintext)
    rather than the one-sentence REST summary, for the biography section."""
    import json as _json
    import urllib.request as _rq
    from ..processing import llm as _llm
    base = "https://en.wikipedia.org/w/api.php"
    q = urllib.parse.urlencode({"action": "query", "prop": "extracts",
                                "exintro": "1", "explaintext": "1", "redirects": "1",
                                "titles": clean, "format": "json"})
    try:
        req = _rq.Request(f"{base}?{q}", headers={"user-agent": _llm.USER_AGENT,
                                                  "accept": "application/json"})
        with _rq.urlopen(req, timeout=7) as resp:
            pages = _json.loads(resp.read()).get("query", {}).get("pages", {})
        for _pid, page in pages.items():
            ex = page.get("extract")
            if ex:
                return ex.strip()
    except Exception:  # noqa: BLE001
        pass
    return None


@route("GET", "/api/leader-profile")
def leader_profile(params, q, body):
    """v6.6 / v6.6.2 — a rich personal panel for any world leader: role/party/
    tenure from the leadership table, a fuller Wikipedia biography, and (when an
    AI provider is available, cached) an AI-synthesized structured profile —
    ideology, career history, party history, key policies."""
    import json as _json
    from ..db.models import meta_get, meta_set
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
        import urllib.request as _rq
        from ..processing import llm as _llm
        url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
               + urllib.parse.quote(clean.replace(" ", "_")) + "?redirect=true")
        req = _rq.Request(url, headers={"user-agent": _llm.USER_AGENT,
                                        "accept": "application/json"})
        with _rq.urlopen(req, timeout=6) as resp:
            d = _json.loads(resp.read())
        if d.get("type") != "disambiguation":
            bio = {"extract": _wiki_intro_extract(clean) or d.get("extract"),
                   "description": d.get("description"),
                   "url": (d.get("content_urls", {}).get("desktop", {}) or {}).get("page"),
                   "image_url": ((d.get("thumbnail") or {}).get("source"))}
    except Exception:  # noqa: BLE001 — offline/blocked: roles still render
        pass
    # v6.6.5 — portrait must resolve even when the REST summary has no thumbnail
    # (that was the empty-page bug for e.g. al-Sharaa). Fall back to the reliable
    # action-API pageimages+search path, and persist it.
    if not bio or not bio.get("image_url"):
        img = _wiki_action_image(clean)
        if img:
            bio = bio or {}
            bio["image_url"] = img
    # v6.6.5 — curated fallback data for major leaders (guaranteed floor)
    from ..geopolitics.leaders_detail import leader_detail
    detail = leader_detail(clean)
    # v6.6.7 — a curated professional headshot wins over a live wiki image that
    # might be a full-body/military shot (owner: Zelenskyy should be a headshot).
    if detail and detail.get("portrait_url"):
        bio = bio or {}
        bio["image_url"] = detail["portrait_url"]
    if detail and (not bio or not bio.get("extract")):
        bio = bio or {}
        bio.setdefault("extract", detail.get("bio_extract"))
    # AI-synthesized structured profile (cached; best-effort, degrades cleanly).
    # v6.6.6 — NON-BLOCKING: the LLM call (20-60s on local Ollama) used to run
    # inside this request and blow the client's fetch timeout → "profile
    # unavailable". Now: return instantly with the cached synthesis (if any) or
    # the curated floor, and kick a background job to generate/enrich + cache.
    # The frontend re-fetches once shortly after to pick up the richer result.
    curated_floor = None
    if detail:
        curated_floor = {k: detail[k] for k in _LEADER_FIELDS if k in detail}
    # v6.6.8 — per-field scaffolded synthesis (owner: "scaffold an outline …
    # have the AI fill in one by one"). Each field is its own small, fast LLM
    # call cached separately, so a slow local model fills the page progressively
    # instead of blocking on one big 800-token call that "takes too long".
    from ..processing import llm
    ctx = {"name": clean,
           "offices": [{"role": r.get("role"), "country": r.get("country_name"),
                        "party": r.get("party"), "since": r.get("since_date")}
                       for r in rows],
           "party": rows[0].get("party") if rows else None,
           "wikipedia_extract": ((bio or {}).get("extract") or "")[:1800]}
    base = f"leaderfield:{clean.lower()}"
    synth = {}
    missing = []
    for fld in _LEADER_FIELDS:
        c = meta_get(f"{base}:{fld}")
        if c is not None:
            try:
                synth[fld] = _json.loads(c)
            except _json.JSONDecodeError:
                synth[fld] = c
        elif curated_floor and fld in curated_floor:
            synth[fld] = curated_floor[fld]   # instant curated value; AI still enriches
            missing.append(fld)
        else:
            missing.append(fld)
    synth_pending = False
    if missing and llm.available() and (rows or bio):
        from ..processing.bg_synth import kick
        synth_pending = kick(base, lambda: _generate_leader_fields(base, ctx, missing))
    if not synth:
        synth = curated_floor
    return 200, {"name": clean, "roles": rows, "bio": bio,
                 "synthesis": synth or None, "synth_pending": synth_pending}


# v6.6.8 — the leader-profile outline (mirrors the old LEADER_PROFILE_PROMPT
# shape): each field is generated by its own focused prompt.
_LEADER_FIELDS = ("summary", "ideology", "career_history", "party_history", "key_policies")
_LEADER_FIELD_SPEC = {
    "summary": ("a 2-4 sentence neutral overview of who this person is and their "
                "current position/standing", "string", 220),
    "ideology": ("their political ideology / orientation in one concise line",
                 "string", 90),
    "career_history": ("4-7 bullet points tracing their career and rise to power, "
                       "chronological", "list", 320),
    "party_history": ("2-5 bullet points on their party affiliations and roles",
                      "list", 200),
    "key_policies": ("4-7 bullet points on their signature policies and positions",
                     "list", 320),
}


def _generate_leader_fields(base, ctx, fields):
    """v6.6.8 — background: fill each requested leader field with its own small
    LLM call, caching each independently so the page fills in progressively."""
    from ..processing import llm
    from ..db.models import meta_set
    who = _json.dumps(ctx, ensure_ascii=False)
    for fld in fields:
        want, kind, toks = _LEADER_FIELD_SPEC[fld]
        shape = ('{"value": ["bullet", ...]}' if kind == "list"
                 else '{"value": "..."}')
        prompt = (f"You are a political biographer. For the public figure in the "
                  f"CONTEXT, provide ONLY {want}. Draw on your general knowledge; "
                  f"a wiki extract may be absent. Return ONLY JSON {shape} — no "
                  f"extra keys, no commentary. If genuinely unknown, return an "
                  f"empty value.")
        text = llm.complete(prompt, [{"role": "user", "content": who}],
                            max_tokens=toks, timeout=45, json_mode=True)
        if not text:
            continue
        t = text.strip()
        if t.startswith("```"):
            t = t.strip("`").removeprefix("json").strip()
        b, e = t.find("{"), t.rfind("}")
        if b != -1 and e != -1:
            t = t[b:e + 1]
        try:
            val = _json.loads(t).get("value")
        except (_json.JSONDecodeError, AttributeError):
            continue
        if kind == "list" and not isinstance(val, list):
            val = [val] if val else []
        if val:
            meta_set(f"{base}:{fld}", _json.dumps(val))


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
    from ..geopolitics.world_knowledge import UN_BRIEF
    return 200, {"knowledge": {"brief": UN_BRIEF, "curated": True},   # v7 Part 6
                 "sub_orgs": _un_sub_orgs(),   # v6.6 — agency subtab data
        "security_council": {"permanent": permanent, "elected": elected},
                 "other_councils": [{"name": n, "note": d} for n, d in u.OTHER_COUNCILS],
                 "resolutions": resolutions}


@route("GET", "/api/un/feed")
def un_feed(params, q, body):
    """v7.4.1 — a live UN news stream nested against the UN page (owner). Returns
    recent stories that either come from a UN-family source OR mention the UN /
    a UN agency in their headline or summary. Newest first, capped."""
    like = ("%united nations%", "%\"un\"%", "% un %", "%unsc%", "%security council%",
            "%unhcr%", "%unicef%", "%ohchr%", "%peacekeep%", "%general assembly%",
            "%secretary-general%", "%guterres%", "%world food programme%", "%iaea%")
    # UN-family sources feed straight in
    un_src = query(
        "SELECT id FROM sources WHERE lower(name) LIKE '%un %' OR lower(name) LIKE 'un %'"
        " OR lower(name) LIKE '%united nations%' OR lower(name) LIKE '%unhcr%'"
        " OR lower(name) LIKE '%unicef%' OR lower(name) LIKE '%ohchr%'"
        " OR lower(name) LIKE '%reliefweb%' OR lower(name) LIKE '%ocha%'"
        " OR lower(name) LIKE '%world food programme%' OR lower(name) LIKE '%iaea%'"
        " OR lower(name) LIKE '%peacekeep%' OR lower(name) LIKE '%who %'"
        " OR lower(name) LIKE '%world health%' OR lower(name) LIKE '%unesco%'"
        " OR lower(name) LIKE '%unctad%' OR lower(name) LIKE '%court of justice%'")
    src_ids = [r["id"] for r in un_src]
    stories = {}
    if src_ids:
        marks = ",".join("?" * len(src_ids))
        rows = query(
            "SELECT DISTINCT st.id, st.headline, st.summary, st.first_seen_at,"
            "  MAX(e.occurred_at) AS last_occurred"
            " FROM events e JOIN raw_items r ON r.id = e.raw_item_id"
            " JOIN story_members m ON m.event_id = e.id"
            " JOIN stories st ON st.id = m.story_id"
            f" WHERE r.source_id IN ({marks}) AND COALESCE(st.is_synthetic,0) = 0"
            " GROUP BY st.id ORDER BY last_occurred DESC LIMIT 40", src_ids)
        for r in rows:
            stories[r["id"]] = dict(r)
    # plus keyword matches across all stories (never synthetic)
    kw = " OR ".join(["lower(headline) LIKE ?"] * len(like)
                     + ["lower(summary) LIKE ?"] * len(like))
    krows = query(
        "SELECT id, headline, summary, first_seen_at FROM stories"
        f" WHERE ({kw}) AND COALESCE(is_synthetic,0) = 0"
        " ORDER BY first_seen_at DESC LIMIT 40", like + like)
    for r in krows:
        stories.setdefault(r["id"], dict(r))
    out = sorted(stories.values(),
                 key=lambda s: s.get("last_occurred") or s.get("first_seen_at") or "",
                 reverse=True)[:40]
    return 200, {"stories": out}


@route("GET", "/api/recognition")
def recognition_subjects_route(params, q, body):
    """v7.4.1 — list the partially-recognized states the recognition map mode
    can visualize (Kosovo, Taiwan, Palestine, Israel, Western Sahara, …)."""
    from ..geopolitics.recognition import recognition_subjects
    return 200, {"subjects": recognition_subjects()}


@route("GET", "/api/recognition/{subject}")
def recognition_view_route(params, q, body):
    """v7.4.1 — who recognizes a given state and who doesn't, normalized over the
    seeded country universe so the map can color every country."""
    from ..geopolitics.recognition import recognition_view
    all_isos = [r["id"] for r in query(
        "SELECT id FROM countries WHERE length(id) = 3")]
    view = recognition_view(params["subject"], all_isos)
    if not view:
        return 404, {"error": "unknown recognition subject"}
    return 200, view


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
    from ..geopolitics.nsa_identity import NSA_IDENTITY
    out = []
    for r in rows:
        d = dict(r)
        # v7 — full official name + flag/emblem, like a country
        d.update(NSA_IDENTITY.get(r["name"], {}))
        from ..geopolitics.world_knowledge import nsa_knowledge
        d["knowledge"] = nsa_knowledge(r["name"])
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


@route("GET", "/api/disputed-zones")
def disputed_zones(params, q, body):
    """v6.6.2 — individually-named disputed territories (Crimea, Donetsk,
    Luhansk, Zaporizhzhia, Kherson, Kashmir, Taiwan, Western Sahara, Kosovo)
    with per-zone context, for the disputed-mode clickable breakdown."""
    from ..geopolitics.disputed_zones import zones_list
    return 200, {"zones": zones_list()}


@route("GET", "/api/autonomous-zones")
def autonomous_zones(params, q, body):
    """v7.4.1 — autonomous regions (Iraqi Kurdistan, Rojava, Bougainville,
    Zanzibar, Gagauzia, Åland, Nakhchivan, Hong Kong, Catalonia, Greenland) as a
    browsable entity type with per-zone breakdowns."""
    from ..geopolitics.autonomous_zones import zones_list
    return 200, {"zones": zones_list()}


@route("GET", "/api/autonomous-zones/{zid}")
def autonomous_zone_detail(params, q, body):
    from ..geopolitics.autonomous_zones import zone_by_id
    z = zone_by_id(params["zid"])
    if not z:
        return 404, {"error": "unknown autonomous zone"}
    # v7.6 — recent tracked coverage, so the panel matches a country/territory
    from .routes_v4 import _stories_mentioning
    z["recent_stories"] = _stories_mentioning(z["name"].split(" (")[0])
    return 200, z


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
