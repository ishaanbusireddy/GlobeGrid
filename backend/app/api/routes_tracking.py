"""v8.16 — the live tracking windows: military, trade, resources, markets,
prediction markets, and the Diplomatic (bilateral relations) window.

Layering rule (the project's data-honesty standard, applied per window):
  LIVE      — what genuinely streams: military/conflict events extracted
              from the wire with coordinates, physical-sensor events
              (OpenSky air traffic, AIS shipping, FIRMS thermal, USGS —
              key-gated ones say so), market events, prediction-market odds.
  CURATED   — year-labelled statistical context (trade totals, resources,
              force posture) that has NO free real-time source; every figure
              carries its year + source and is never presented as live.
Everything here is also injected into the analyst bundle (routes_analyst
pulls tracking_context()) so the AI can reason over the same numbers.
"""

from ..db.session import query, query_one
from ..geopolitics import trade_data, ideology
from ..processing import predmarkets
from .router import route


def _country_name(iso3):
    row = query_one("SELECT name FROM countries WHERE id = ?", (iso3,))
    return row["name"] if row else iso3

# Curated force-posture layer for the Military window: headline deployments
# and standing postures (mid-2026 vintage, clearly labelled curated).
FORCE_POSTURE = [
    {"actor": "USA", "what": "Carrier strike groups — CENTCOM/Red Sea rotation + INDOPACOM presence",
     "where": "Arabian Sea / Western Pacific", "lat": 14.0, "lon": 58.0,
     "note": "Two-carrier posture ebbs/flows with Houthi + Iran tensions"},
    {"actor": "USA", "what": "~100k personnel in Europe (EUCOM), reinforced NATO east flank",
     "where": "Germany/Poland/Romania/Baltics", "lat": 52.2, "lon": 21.0,
     "note": "Enhanced Forward Presence battlegroups in 8 states"},
    {"actor": "RUS", "what": "~600k personnel committed to the Ukraine front",
     "where": "Eastern/Southern Ukraine fronts", "lat": 48.0, "lon": 37.5,
     "note": "Concentrations: Donetsk, Zaporizhzhia, Kursk axes"},
    {"actor": "CHN", "what": "PLA Eastern Theater — recurring large-scale drills around Taiwan",
     "where": "Taiwan Strait / First Island Chain", "lat": 24.0, "lon": 119.5,
     "note": "Air-defense-zone incursions near-daily; blockade-rehearsal exercises"},
    {"actor": "CHN", "what": "Militarized artificial islands, coast-guard pressure ops",
     "where": "South China Sea (Spratlys/Paracels/Scarborough)", "lat": 10.5, "lon": 114.5,
     "note": "Standing friction with PHL resupply missions at Second Thomas Shoal"},
    {"actor": "ISR", "what": "Northern Command posture vs Hezbollah; periodic Syria strikes",
     "where": "Israel–Lebanon border / Syria", "lat": 33.2, "lon": 35.5,
     "note": "Post-2024 campaign degraded but did not eliminate Hezbollah's arsenal"},
    {"actor": "IRN", "what": "IRGC missile/drone forces + proxy network (Iraq, Yemen, Lebanon)",
     "where": "Iran + regional proxies", "lat": 32.0, "lon": 53.0,
     "note": "Ballistic-missile inventory is the region's largest"},
    {"actor": "PRK", "what": "Artillery/missile posture on the DMZ; troops rotated to Russia",
     "where": "Korean DMZ", "lat": 38.3, "lon": 127.0,
     "note": "~11k+ troops sent to Russia's war effort since 2024"},
    {"actor": "IND/PAK", "what": "Line of Control standing confrontation",
     "where": "Kashmir LoC", "lat": 34.1, "lon": 74.5,
     "note": "Post-2025-war ceasefire holding with regular violations"},
]

_SENSOR_TYPES = ("firms", "opensky", "usgs", "acled", "ais", "nightlights")


@route("GET", "/api/military")
def military(params, q, body):
    """The Military window: LIVE extracted military/conflict events with
    precise coordinates + LIVE physical-sensor tracks + the curated posture
    layer. Every row says which layer it is."""
    try:
        limit = min(int(q.get("limit", 80)), 200)
    except (TypeError, ValueError):
        limit = 80
    ev = query(
        "SELECT e.id, e.title, e.category, e.development_type, e.severity,"
        " e.occurred_at, e.location_lat AS lat, e.location_lon AS lon,"
        " e.admin_uid, s.name AS source_name, s.type AS source_type"
        " FROM events e JOIN raw_items ri ON ri.id = e.raw_item_id JOIN sources s ON s.id = ri.source_id"
        " WHERE e.is_synthetic = 0 AND e.location_lat IS NOT NULL"
        " AND (e.category IN ('conflict') OR e.development_type IN"
        "      ('military','conflict') OR s.type IN"
        f"      {_SENSOR_TYPES!r})"
        " ORDER BY e.occurred_at DESC LIMIT ?", (limit,))
    events, sensors = [], []
    for r in ev:
        row = dict(r)
        row["layer"] = ("sensor" if r["source_type"] in _SENSOR_TYPES
                        else "extracted")
        (sensors if row["layer"] == "sensor" else events).append(row)
    return 200, {
        "events": events, "sensors": sensors, "posture": FORCE_POSTURE,
        "layers_note": (
            "LIVE 'extracted': military/conflict events pulled from the wire "
            "with coordinates. LIVE 'sensor': physical tracks — OpenSky air "
            "traffic, AIS shipping (key-gated: AIS_API_KEY), FIRMS thermal, "
            "USGS seismic. CURATED 'posture': standing deployments, "
            "mid-2026 vintage — context, not live tracks. No public "
            "real-time missile-track feed exists; missile EVENTS appear in "
            "the extracted layer the moment sources report them."),
    }


@route("GET", "/api/trade")
def trade_world(params, q, body):
    return 200, {"world": trade_data.WORLD_TRADE,
                 "countries_covered": sorted(trade_data.TRADE.keys())}


@route("GET", "/api/trade/{iso3}")
def trade_country(params, q, body):
    iso3 = (params.get("iso3") or "").upper()
    t = trade_data.trade_for(iso3)
    r = trade_data.resources_for(iso3)
    # LIVE layer: recent trade/tariff/finance news naming this country
    name = _country_name(iso3)
    stories = query(
        "SELECT id, headline, last_updated_at FROM stories WHERE is_synthetic=0"
        " AND (headline LIKE ? OR summary LIKE ?)"
        " AND (headline LIKE '%trade%' OR headline LIKE '%tariff%'"
        "      OR headline LIKE '%export%' OR headline LIKE '%import%'"
        "      OR headline LIKE '%sanction%')"
        " ORDER BY last_updated_at DESC LIMIT 8",
        (f"%{name}%", f"%{name}%"))
    return 200, {"iso3": iso3, "trade": t, "resources": r,
                 "live_trade_news": [dict(s) for s in stories],
                 "note": ("Curated statistics carry their year + source on "
                          "every figure — there is no free real-time "
                          "bilateral-trade feed; the live layer is the news "
                          "wire + markets." if t else
                          "No curated trade profile for this country yet — "
                          "the live news layer still applies.")}


@route("GET", "/api/markets/live")
def markets_live(params, q, body):
    rows = query(
        "SELECT e.title, e.occurred_at, s.name AS source_name"
        " FROM events e JOIN raw_items ri ON ri.id = e.raw_item_id JOIN sources s ON s.id = ri.source_id"
        " WHERE e.is_synthetic = 0 AND (s.type = 'market'"
        "   OR e.category = 'finance')"
        " ORDER BY e.occurred_at DESC LIMIT 40")
    briefing = query_one(
        "SELECT content, generated_at FROM daily_briefings"
        " WHERE briefing_date LIKE 'market%' ORDER BY generated_at DESC LIMIT 1")
    return 200, {"events": [dict(r) for r in rows],
                 "market_briefing": dict(briefing) if briefing else None,
                 "note": ("Live market EVENTS from the market source "
                          "(ALPHAVANTAGE_API_KEY-gated) + finance-category "
                          "wire stories. Not investment advice.")}


@route("GET", "/api/predmarkets")
def predmarkets_route(params, q, body):
    return 200, predmarkets.markets(q.get("q"))


@route("GET", "/api/ideologies")
def ideologies(params, q, body):
    return 200, {"values": ideology.all_values(), "default": ideology.DEFAULT}


@route("GET", "/api/diplomacy")
def diplomacy(params, q, body):
    """v8.16 — the Diplomatic Window v1: current stance, curated context and
    the shared live-coverage trail between any two countries."""
    a = (q.get("a") or "").upper()
    b = (q.get("b") or "").upper()
    if len(a) != 3 or len(b) != 3 or a == b:
        return 400, {"error": "pass two distinct iso3 codes, ?a=USA&b=CHN"}
    from ..geopolitics.country_extra import derive_alignments
    from ..geopolitics import world_knowledge
    na, nb = _country_name(a), _country_name(b)
    al = derive_alignments(a) or {}
    if b in (al.get("strong") or []):
        stance = "allies"
    elif b in (al.get("partner") or []):
        stance = "partners"
    elif b in (al.get("rival") or []):
        stance = "rivals"
    else:
        stance = "no strong standing alignment"
    shared = query(
        "SELECT id, headline, last_updated_at FROM stories WHERE is_synthetic=0"
        " AND (headline LIKE ? OR summary LIKE ?)"
        " AND (headline LIKE ? OR summary LIKE ?)"
        " ORDER BY last_updated_at DESC LIMIT 20",
        (f"%{na}%", f"%{na}%", f"%{nb}%", f"%{nb}%"))
    ka = world_knowledge.country_knowledge(a) or {}
    kb = world_knowledge.country_knowledge(b) or {}
    return 200, {
        "a": {"iso3": a, "name": na, "brief": (ka.get("brief") or "")[:900]},
        "b": {"iso3": b, "name": nb, "brief": (kb.get("brief") or "")[:900]},
        "stance": stance,
        "shared_coverage": [dict(s) for s in shared],
        "note": ("Shared coverage = tracked stories naming BOTH countries — "
                 "it deepens automatically as ingestion history grows."),
    }
