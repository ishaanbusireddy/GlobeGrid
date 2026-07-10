"""V8.8 — the Cities layer API.

Every city in the vendored GeoNames gazetteer (`gazetteer_places`, ~32k places
with population) becomes a clickable entity with its own panel — exactly like the
administrative units. A city is located inside the administrative atlas on demand
(`admin_atlas.unit_at`), so it knows which province / county / district it sits
in, and every admin-unit and country panel can list the cities inside it, largest
population first.

Endpoints (read-only):
  GET /api/cities                 — (in routes_v4) the population-tiered label layer
  GET /api/cities/country/{iso3}  — cities in a country, population desc
  GET /api/cities/admin/{uid}     — cities inside an admin unit's polygon, pop desc
  GET /api/cities/{id}            — one city's detail (country, admin unit, rank)

City data: GeoNames via the v2 gazetteer import (CC BY 4.0, credited).
"""
from ..db.session import query, query_one
from .router import route


def _iso3_to_iso2(iso3):
    r = query_one("SELECT iso2 FROM countries WHERE id = ?", (iso3,))
    return r["iso2"] if r and r["iso2"] else None


@route("GET", "/api/cities/country/{iso3}")
def cities_in_country(params, q, body):
    """The biggest cities in a country, population descending — powers the
    'Cities' section on a country panel."""
    iso3 = params["iso3"].upper()
    iso2 = _iso3_to_iso2(iso3)
    if not iso2:
        return 200, {"cities": [], "iso3": iso3, "count": 0}
    limit = min(int(q.get("limit", 60)), 500)
    rows = query(
        "SELECT id, name, lat, lon, population FROM gazetteer_places"
        " WHERE country_code = ? ORDER BY population DESC LIMIT ?", (iso2, limit))
    return 200, {"cities": [dict(r) for r in rows], "iso3": iso3, "count": len(rows),
                 "attribution": "Geocoding data © GeoNames (geonames.org), CC BY 4.0"}


@route("GET", "/api/cities/admin/{uid}")
def cities_in_admin(params, q, body):
    """Cities whose coordinates fall inside an admin unit's OWN polygon (any tier)
    — powers the 'Cities' section on an admin-unit panel. Bbox-prefilters the
    gazetteer, then point-in-polygon against the unit's rings."""
    try:
        uid = int(params["uid"])
    except (TypeError, ValueError):
        return 404, {"error": "uid must be an integer"}
    unit = query_one("SELECT admin_uid, country_id FROM administrative_units"
                     " WHERE admin_uid = ?", (uid,))
    if not unit:
        return 404, {"error": "administrative unit not found"}
    from ..geopolitics.admin_atlas import _load, _decode_ring, _ring_contains
    data = _load()
    enc = next((e for e in data["enc"] if e["i"] == uid), None)
    if not enc:
        return 200, {"cities": [], "uid": uid, "count": 0}
    rings = [_decode_ring(r) for r in enc["r"]]
    bb = enc["b"]   # [minLon, minLat, maxLon, maxLat]
    iso2 = _iso3_to_iso2(unit["country_id"])
    limit = min(int(q.get("limit", 40)), 200)
    sql = ("SELECT id, name, lat, lon, population FROM gazetteer_places"
           " WHERE lat >= ? AND lat <= ? AND lon >= ? AND lon <= ?")
    args = [bb[1], bb[3], bb[0], bb[2]]
    if iso2:
        sql += " AND country_code = ?"
        args.append(iso2)
    sql += " ORDER BY population DESC LIMIT 3000"
    out = []
    for r in query(sql, tuple(args)):
        for ring in rings:
            if _ring_contains(ring, r["lat"], r["lon"]):
                out.append(dict(r))
                break
        if len(out) >= limit:
            break
    return 200, {"cities": out, "uid": uid, "count": len(out),
                 "attribution": "Geocoding data © GeoNames (geonames.org), CC BY 4.0"}


@route("GET", "/api/cities/{id}")
def city_detail(params, q, body):
    """One city's full panel: its country (with flag), the smallest admin unit it
    sits inside (with ancestry to drill up), coordinates and national rank."""
    try:
        cid = int(params["id"])
    except (TypeError, ValueError):
        return 404, {"error": "city id must be an integer"}
    r = query_one("SELECT id, name, ascii_name, lat, lon, country_code, population"
                  " FROM gazetteer_places WHERE id = ?", (cid,))
    if not r:
        return 404, {"error": "city not found"}
    city = dict(r)
    cc = query_one("SELECT id, name, official_name, flag_image_url, status, region"
                   " FROM countries WHERE iso2 = ?", (city["country_code"],))
    country = dict(cc) if cc else None
    # the smallest admin unit containing the city + its ancestry breadcrumb
    from ..geopolitics import admin_atlas
    admin = None
    ancestry = []
    uid = admin_atlas.unit_at(city["lat"], city["lon"])
    if uid:
        au = query_one("SELECT admin_uid, name, unit_type, adm_level, parent_uid,"
                       " country_id, path FROM administrative_units WHERE admin_uid = ?", (uid,))
        if au:
            admin = dict(au)
            pu, seen = admin.get("parent_uid"), set()
            while pu and pu not in seen:
                seen.add(pu)
                p = query_one("SELECT admin_uid, name, adm_level, parent_uid"
                              " FROM administrative_units WHERE admin_uid = ?", (pu,))
                if not p:
                    break
                ancestry.append({"admin_uid": p["admin_uid"], "name": p["name"],
                                 "adm_level": p["adm_level"]})
                pu = p["parent_uid"]
            ancestry.reverse()
    rank = None
    if country:
        rr = query_one("SELECT COUNT(*) AS n FROM gazetteer_places"
                       " WHERE country_code = ? AND population > ?",
                       (city["country_code"], city["population"] or 0))
        rank = (rr["n"] + 1) if rr else None
    # nearby larger cities for context / navigation
    return 200, {"city": city, "country": country, "admin": admin,
                 "ancestry": ancestry, "national_rank": rank}
