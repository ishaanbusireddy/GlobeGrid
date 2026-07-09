"""V8 §4/§5 — the Administrative Atlas API.

Serves the variable-depth administrative hierarchy (ADM1 provinces/states now;
deeper tiers as the vendored data lands) that turns the map from ~200 country
polygons into thousands of individually-clickable units — each a real entity
with its own detail page, the way Greenland already is.

Endpoints (all read-only, time-capsule aware via ?as_of=YYYY-MM-DD):
  GET /api/admin/at?lat=&lon=      — resolve a click/point to its ADM1 unit
  GET /api/admin/country/{iso3}    — every unit inside a country (drill-down)
  GET /api/admin/search?q=         — search units by name / country
  GET /api/admin/{uid}             — full unit detail (ancestry, inherited
                                     country stats, siblings, recent coverage)

Boundaries themselves are vendored + rendered client-side from
frontend/src/data/adminBoundaries.js; the registry (administrative_units) and
the point-in-polygon (geopolitics/admin_atlas.py) live in the backend so events
resolve to units at ingestion and a click resolves to a unit on demand.

Q3/temporal: every unit carries effective_from/effective_to. as_of selects the
epoch real at that date. ADM1 today is present-day (Natural Earth is current),
so as_of doesn't yet prune anything — but the machinery is live, so curated
historical epochs (back to 1950, estimated where no data exists, switching to
real data as it becomes available in the last ~two decades) drop in as pure
data with no code change.
"""

import json

from ..db.session import query, query_one
from .router import route

# columns that a click / drill-down needs but a heavy detail call can skip
_LITE_COLS = ("admin_uid, country_id, adm_level, parent_uid, name, unit_type,"
              " centroid_lat, centroid_lon, bbox_json, effective_from,"
              " effective_to, source")


def _as_of_clause(alias: str, as_of):
    """Return (sql_fragment, params) restricting rows to units valid at as_of.
    A NULL effective_from means 'always'; a NULL effective_to means 'current'.
    When as_of is absent, no restriction (show the current present-day set)."""
    if not as_of:
        # present-day view: hide only units explicitly retired (effective_to set)
        return f" AND {alias}.effective_to IS NULL", []
    return (f" AND ({alias}.effective_from IS NULL OR {alias}.effective_from <= ?)"
            f" AND ({alias}.effective_to IS NULL OR {alias}.effective_to > ?)",
            [as_of, as_of])


def _unit_row(r) -> dict:
    d = dict(r)
    if d.get("bbox_json"):
        try:
            d["bbox"] = json.loads(d["bbox_json"])
        except (json.JSONDecodeError, TypeError):
            d["bbox"] = None
    d.pop("bbox_json", None)
    return d


def _country_summary(iso3):
    """Light country context for a unit panel: name, flag, status, and the
    headline stats an ADM1 unit INHERITS until province-level demographics
    are vendored (Q4 — deferred, clearly labelled inherited=True so the UI
    never presents a country figure as if it were the province's own)."""
    if not iso3:
        return None
    # Only base-DDL columns are selected explicitly — currency_* and other
    # ALTER-added v6.1 columns aren't present on a fresh install, and the unit
    # panel doesn't need them.
    c = query_one(
        "SELECT id, name, official_name, status, region, flag_image_url,"
        " population, gdp_usd, gdp_per_capita_usd, hdi, area_km2,"
        " dominant_language, dominant_religion"
        " FROM countries WHERE id = ?", (iso3,))
    if not c:
        return {"id": iso3, "name": iso3, "inherited": True}
    d = dict(c)
    d["inherited"] = True   # these are COUNTRY figures, shown until we have finer data
    return d


@route("GET", "/api/admin/history")
def admin_history(params, q, body):
    """V8 §Q3 — the curated border & sovereignty timeline since 1950. Optional
    ?country=ISO3 filters to a country's lineage; ?as_of=YYYY caps to changes
    that had already happened by that year (the time-capsule view)."""
    from ..geopolitics.admin_history import timeline, history_for, history_as_of
    country = (q.get("country") or "").strip()
    as_of = (q.get("as_of") or "").strip()
    if country:
        entries = history_for(country)
    elif as_of:
        entries = history_as_of(as_of)
    else:
        entries = timeline()
    return 200, {"count": len(entries), "entries": entries}


@route("GET", "/api/admin/at")
def admin_at(params, q, body):
    """Resolve a lat/lon to the smallest ADM1 unit containing it (click→unit)."""
    try:
        lat = float(q.get("lat"))
        lon = float(q.get("lon"))
    except (TypeError, ValueError):
        return 400, {"error": "lat and lon are required floats"}
    from ..geopolitics.admin_atlas import unit_at
    uid = unit_at(lat, lon)
    if uid is None:
        return 200, {"unit": None}
    row = query_one(f"SELECT {_LITE_COLS} FROM administrative_units"
                    " WHERE admin_uid = ?", (uid,))
    return 200, {"unit": _unit_row(row) if row else {"admin_uid": uid}}


@route("GET", "/api/admin/country/{iso3}")
def admin_by_country(params, q, body):
    """Every administrative unit inside a country — the drill-down list when
    you open a country and want its provinces."""
    iso3 = params["iso3"].upper()
    frag, ap = _as_of_clause("u", q.get("as_of"))
    try:
        level = int(q.get("level")) if q.get("level") else None
    except (TypeError, ValueError):
        level = None
    sql = (f"SELECT {_LITE_COLS} FROM administrative_units u"
           " WHERE u.country_id = ?" + frag)
    args = [iso3] + ap
    if level is not None:
        sql += " AND u.adm_level = ?"
        args.append(level)
    sql += " ORDER BY u.name"
    rows = query(sql, tuple(args))
    return 200, {"country": iso3, "count": len(rows),
                 "units": [_unit_row(r) for r in rows]}


@route("GET", "/api/admin/search")
def admin_search(params, q, body):
    term = (q.get("q") or "").strip()
    if not term:
        return 200, {"units": []}
    try:
        limit = min(int(q.get("limit", 20)), 100)
    except (TypeError, ValueError):
        limit = 20
    frag, ap = _as_of_clause("u", q.get("as_of"))
    like = f"%{term}%"
    rows = query(
        f"SELECT {_LITE_COLS} FROM administrative_units u"
        " WHERE (u.name LIKE ? OR u.country_id LIKE ?)" + frag +
        " ORDER BY (u.name = ?) DESC, LENGTH(u.name) LIMIT ?",
        tuple([like, like] + ap + [term, limit]))
    return 200, {"units": [_unit_row(r) for r in rows]}


@route("GET", "/api/admin/{uid}")
def admin_detail(params, q, body):
    """Full unit detail: the unit, its ancestry breadcrumbs, the parent
    country (with inherited stats), sibling units for navigation, and the
    recent tracked coverage that landed inside this unit."""
    try:
        uid = int(params["uid"])
    except (TypeError, ValueError):
        return 404, {"error": "admin unit id must be an integer"}
    row = query_one("SELECT * FROM administrative_units WHERE admin_uid = ?", (uid,))
    if not row:
        return 404, {"error": "administrative unit not found"}
    unit = _unit_row(row)

    # ancestry — walk parent_uid up to the root, then the country node.
    ancestry = []
    seen = set()
    pu = unit.get("parent_uid")
    while pu and pu not in seen:
        seen.add(pu)
        p = query_one("SELECT admin_uid, name, adm_level, parent_uid, country_id"
                      " FROM administrative_units WHERE admin_uid = ?", (pu,))
        if not p:
            break
        ancestry.append(dict(p))
        pu = p["parent_uid"]
    ancestry.reverse()

    country = _country_summary(unit.get("country_id"))

    # siblings — same country + same level (bounded; drill-down/nav aid)
    frag, ap = _as_of_clause("u", q.get("as_of"))
    siblings = query(
        f"SELECT admin_uid, name, unit_type, centroid_lat, centroid_lon"
        " FROM administrative_units u WHERE u.country_id = ? AND u.adm_level = ?"
        " AND u.admin_uid != ?" + frag + " ORDER BY u.name LIMIT 400",
        tuple([unit.get("country_id"), unit.get("adm_level", 1), uid] + ap))

    # direct children (deeper tier), if any exist yet
    children = query(
        f"SELECT admin_uid, name, unit_type, adm_level, centroid_lat, centroid_lon"
        " FROM administrative_units u WHERE u.parent_uid = ?" + frag +
        " ORDER BY u.name LIMIT 600", tuple([uid] + ap))

    # recent coverage — events tagged to this unit (v8 §4 events.admin_uid),
    # surfaced with the stories they belong to. Excludes synthetic.
    coverage = query(
        "SELECT DISTINCT s.id, s.headline, s.summary, s.story_type,"
        " s.last_updated_at FROM events e"
        " JOIN story_members sm ON sm.event_id = e.id"
        " JOIN stories s ON s.id = sm.story_id"
        " WHERE e.admin_uid = ? AND COALESCE(e.is_synthetic,0)=0"
        " AND COALESCE(s.is_synthetic,0)=0"
        " ORDER BY s.last_updated_at DESC LIMIT 10", (uid,))
    event_count = query_one(
        "SELECT COUNT(*) AS n FROM events WHERE admin_uid = ?"
        " AND COALESCE(is_synthetic,0)=0", (uid,))

    return 200, {
        "unit": unit,
        "ancestry": ancestry,
        "country": country,
        "siblings": [dict(r) for r in siblings],
        "children": [dict(r) for r in children],
        "coverage": [dict(r) for r in coverage],
        "event_count": event_count["n"] if event_count else 0,
    }
