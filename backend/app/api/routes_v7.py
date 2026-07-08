"""v7 routes: Counterfactual Engine (§2), Situation Room (§3), forecasting
scorecard (§4), sensor corroboration (§5)."""

from .router import route


@route("POST", "/api/counterfactual")
def counterfactual_run(params, q, body):
    """v7 §2 — run (or fetch cached) a what-if scenario. Body: {perturbation,
    force?}. Returns the branching consequence tree with plausibility
    annotations grounded in GlobeGrid's own fact chain."""
    from ..processing import counterfactual as cfx
    if not isinstance(body, dict) or not (body.get("perturbation") or "").strip():
        return 400, {"error": "body must be {perturbation: string}"}
    return 200, cfx.run_scenario(body["perturbation"], force=bool(body.get("force")))


@route("GET", "/api/counterfactual/recent")
def counterfactual_recent(params, q, body):
    from ..processing import counterfactual as cfx
    return 200, {"scenarios": cfx.recent_scenarios()}


@route("POST", "/api/counterfactual/expand")
def counterfactual_expand(params, q, body):
    """v7.1 §2 — deepen one branch of a scenario into child consequences.
    Body: {perturbation, branch:{id,title,mechanism,domain,t_offset,affected}}."""
    from ..processing import counterfactual as cfx
    if not isinstance(body, dict) or not body.get("branch"):
        return 400, {"error": "body must be {perturbation, branch}"}
    return 200, cfx.expand_branch(body.get("perturbation"), body["branch"],
                                  force=bool(body.get("force")))


@route("GET", "/api/situation-room/{cid}")
def situation_room(params, q, body):
    """v7 §3 — the four-analyst threaded war room for a conflict. ?force=1
    regenerates even when the cached thread is current."""
    from ..processing import situation_room as sr
    return 200, sr.get_thread(params["cid"], force=q.get("force") == "1")


@route("GET", "/api/forecasting/scorecard")
def forecasting_scorecard(params, q, body):
    """v7 §4 — the public 'how right were we?' accuracy dashboard."""
    from ..processing import backtest
    return 200, backtest.dashboard()


@route("POST", "/api/forecasting/backtest")
def forecasting_backtest(params, q, body):
    """v7 §4 — replay the fact chain and recompute per-category Brier
    scorecards on demand."""
    from ..processing import backtest
    return 200, backtest.run_backtest()


@route("GET", "/api/sensors")
def sensors_recent(params, q, body):
    """v7.1 §5 — recent physical-sensor events (FIRMS thermal / OpenSky air /
    USGS seismic / ACLED) for the map overlay: the ground-truth layer the
    corroboration score is computed against. Tagged with a sensor_* category so
    the marked-locations pin pipeline renders each type in its own color."""
    from ..db.session import query
    rows = query(
        "SELECT e.id, e.title, e.location_lat AS lat, e.location_lon AS lon,"
        " e.occurred_at, src.type AS stype FROM events e"
        " JOIN raw_items ri ON ri.id = e.raw_item_id"
        " JOIN sources src ON src.id = ri.source_id"
        " WHERE src.type IN ('firms','opensky','usgs','acled','ais','nightlights')"
        "   AND e.location_lat IS NOT NULL AND e.is_synthetic = 0"
        " ORDER BY e.occurred_at DESC LIMIT 300")
    label = {"firms": "thermal anomaly", "opensky": "air-traffic anomaly",
             "usgs": "seismic event", "acled": "ACLED incident",
             "ais": "maritime-traffic anomaly", "nightlights": "nighttime blackout"}
    out = [{"id": r["id"], "lat": r["lat"], "lon": r["lon"],
            "name": r["title"], "occurred_at": r["occurred_at"],
            "sensor_type": r["stype"],
            "category": "sensor_" + r["stype"],
            "label": label.get(r["stype"], r["stype"])} for r in rows]
    return 200, {"sensors": out, "count": len(out)}
