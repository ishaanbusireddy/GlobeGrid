"""Map-supporting queries (Section 5.2): located events plus the
correlation-thread segments the Tier 1 globe animates between linked
stories. Cluster thresholds are echoed from config.yaml so the frontend
never hardcodes them."""

from ..config import cfg
from ..db.session import query
from .router import route


@route("GET", "/api/map/events")
def map_events(params, q, body):
    limit = min(int(q.get("limit", 500)), 2000)
    conditions, args = ["e.location_lat IS NOT NULL"], []
    if q.get("since"):
        conditions.append("e.occurred_at > ?")
        args.append(q["since"])
    if q.get("as_of"):  # v2 §4 time capsule
        conditions.append("e.occurred_at <= ?")
        args.append(q["as_of"])
    if q.get("category"):
        # v6.1 — 'military' is a derived map category (development_type), not a
        # stored e.category value, so filter on the development type for it
        if q["category"] == "military":
            conditions.append("e.development_type = 'military'"
                              " AND e.category != 'conflict'")
        else:
            conditions.append("e.category = ?")
            args.append(q["category"])
    if q.get("min_relevance"):   # v4 §9.1 — relevance-floor filter
        conditions.append("COALESCE(e.global_relevance_score, 1.0) >= ?")
        args.append(float(q["min_relevance"]))
    if q.get("conflict_id"):     # v4 §9.2 — conflict filter shared with feed
        conditions.append("e.conflict_id = ?")
        args.append(q["conflict_id"])
    rows = query(
        "SELECT e.id, e.title, e.location_lat AS lat, e.location_lon AS lon,"
        " e.location_name, e.category, e.severity, e.occurred_at,"
        " e.development_type, e.geocode_confidence, e.global_relevance_score,"
        " (SELECT story_id FROM story_members m WHERE m.event_id = e.id LIMIT 1) AS story_id"
        " FROM events e"
        f" WHERE {' AND '.join(conditions)}"
        " ORDER BY e.occurred_at DESC LIMIT ?", (*args, limit))
    events = [dict(r) for r in rows]
    # v6.1 — 'military' is its own map category (green), distinct from
    # 'conflict', shown OUTSIDE war mode too: a military development that isn't
    # part of a tracked conflict surfaces as its own colored marker.
    for e in events:
        if e.get("development_type") == "military" and e["category"] != "conflict":
            e["category"] = "military"

    # correlation threads: consecutive located events within one story
    by_story: dict = {}
    for e in events:
        if e["story_id"]:
            by_story.setdefault(e["story_id"], []).append(e)
    links = []
    for story_id, members in by_story.items():
        members.sort(key=lambda e: e["occurred_at"])
        for a, b in zip(members, members[1:]):
            if (a["lat"], a["lon"]) != (b["lat"], b["lon"]):
                links.append({"story_id": story_id,
                              "from": [a["lat"], a["lon"]],
                              "to": [b["lat"], b["lon"]]})

    return 200, {
        "events": events,
        "links": links,
        "cluster_config": {
            "cluster_pin_threshold": cfg("map", "cluster_pin_threshold"),
            "cluster_radius_km": cfg("map", "cluster_radius_km"),
        },
    }
