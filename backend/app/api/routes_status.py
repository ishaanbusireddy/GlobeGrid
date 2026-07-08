"""Section 8.1 — GET /api/instability (range, default 72h; v2: as_of) and
GET /api/sources/status (v2 §7.1: uptime history). Plus GET /api/config —
client-relevant tunables (map clustering, §5 graphics defaults) so the
frontend never hardcodes config values."""

from datetime import datetime, timedelta, timezone

from ..config import cfg
from ..db.session import query, query_one
from ..db.models import row_to_dict
from .router import route

GEONAMES_ATTRIBUTION = "Geocoding data © GeoNames (geonames.org), CC BY 4.0"


def _parse_range(value: str) -> float:
    value = (value or "72h").strip().lower()
    try:
        if value.endswith("d"):
            return float(value[:-1]) * 24
        if value.endswith("h"):
            return float(value[:-1])
        return float(value)
    except ValueError:
        return 72.0


@route("GET", "/api/instability")
def instability(params, q, body):
    hours = _parse_range(q.get("range", "72h"))
    anchor = q.get("as_of")  # v2 §4 — nearest reading at or before as_of
    if anchor:
        latest = query_one(
            "SELECT * FROM instability_scores WHERE computed_at <= ?"
            " ORDER BY computed_at DESC LIMIT 1", (anchor,))
        anchor_dt = anchor
    else:
        latest = query_one(
            "SELECT * FROM instability_scores ORDER BY computed_at DESC LIMIT 1")
        anchor_dt = datetime.now(timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z")
    cutoff = (datetime.fromisoformat(anchor_dt.replace("Z", "+00:00"))
              - timedelta(hours=hours)).isoformat(timespec="seconds").replace("+00:00", "Z")
    history = query(
        "SELECT * FROM instability_scores WHERE computed_at >= ? AND computed_at <= ?"
        " ORDER BY computed_at", (cutoff, anchor_dt))
    anomalies = query(  # v3 §6 — flags shown as markers on the trend line
        "SELECT detected_at, method, score_value, z_or_cusum_value FROM anomaly_flags"
        " WHERE detected_at >= ? AND detected_at <= ? ORDER BY detected_at",
        (cutoff, anchor_dt))
    return 200, {
        "latest": row_to_dict(latest, json_fields=("component_breakdown",)) if latest else None,
        "history": [row_to_dict(r, json_fields=("component_breakdown",)) for r in history],
        "anomalies": [dict(a) for a in anomalies],
        "range_hours": hours,
        "as_of": anchor,
    }


@route("GET", "/api/sources/status")
def sources_status(params, q, body):
    # v6 §2 — retired sources (is_active=0, e.g. GDELT) drop out of the live
    # health drawer; their historical facts keep attribution elsewhere
    rows = query("SELECT id, name, type, url, leaning, kind, reliability_tier,"
                 " poll_interval_seconds, health_status, last_fetched_at, last_error"
                 " FROM sources WHERE type != 'synthetic' AND is_active = 1"
                 " ORDER BY CASE reliability_tier WHEN 'high' THEN 0 WHEN 'medium' THEN 1"
                 " ELSE 2 END, name")
    day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(
        timespec="seconds").replace("+00:00", "Z")
    sources = []
    for r in rows:
        d = dict(r)
        # v2 §7.1 — 24h uptime percentage + compact recent history
        stats = query_one(
            "SELECT COUNT(*) AS total,"
            " SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS ok_count"
            " FROM source_uptime_history WHERE source_id = ? AND checked_at >= ?",
            (r["id"], day_ago))
        d["uptime_24h_pct"] = (round(100.0 * stats["ok_count"] / stats["total"], 1)
                               if stats["total"] else None)
        recent = query(
            "SELECT status FROM source_uptime_history WHERE source_id = ?"
            " ORDER BY checked_at DESC LIMIT 24", (r["id"],))
        d["recent_history"] = [x["status"] for x in reversed(recent)]
        sources.append(d)
    return 200, {"sources": sources, "attribution": [GEONAMES_ATTRIBUTION]}


@route("GET", "/api/sources/{sid}/stories")
def source_stories(params, q, body):
    """v7.4.1 — click a source in the health drawer to see the stories/events
    it fed (owner). Walks source → raw_items → events → story_members → stories,
    newest first, capped."""
    sid = params["sid"]
    src = query_one("SELECT id, name, type FROM sources WHERE id = ?", (sid,))
    if not src:
        return 404, {"error": "source not found"}
    rows = query(
        "SELECT DISTINCT st.id, st.headline, st.summary, st.first_seen_at,"
        "  MAX(e.occurred_at) AS last_occurred, COUNT(DISTINCT e.id) AS n_events"
        " FROM events e"
        " JOIN raw_items r ON r.id = e.raw_item_id"
        " JOIN story_members m ON m.event_id = e.id"
        " JOIN stories st ON st.id = m.story_id"
        " WHERE r.source_id = ?"
        " GROUP BY st.id"
        " ORDER BY st.first_seen_at DESC LIMIT 60", (sid,))
    stories = [dict(r) for r in rows]
    # also raw events from this source not (yet) correlated into a story
    loose = query(
        "SELECT e.id, e.title, e.location_name, e.category, e.occurred_at"
        " FROM events e JOIN raw_items r ON r.id = e.raw_item_id"
        " LEFT JOIN story_members m ON m.event_id = e.id"
        " WHERE r.source_id = ? AND m.story_id IS NULL"
        " ORDER BY e.occurred_at DESC LIMIT 40", (sid,))
    return 200, {"source": dict(src), "stories": stories,
                 "uncorrelated_events": [dict(r) for r in loose]}


@route("GET", "/api/config")
def client_config(params, q, body):
    """Client-relevant tunables only — never secrets."""
    from ..processing import llm as _llm
    from ..config import APP_VERSION
    return 200, {
        "app_version": APP_VERSION,
        # v6.1 — honest AI state so every fallback message (causal storyline,
        # country agenda, translation) reflects the *actual* provider instead
        # of a hardcoded "Set CLAUDE_API_KEY" string from the Anthropic era.
        "ai_available": _llm.available(),
        "map": {
            "cluster_pin_threshold": cfg("map", "cluster_pin_threshold"),
            "cluster_radius_km": cfg("map", "cluster_radius_km"),
        },
        "graphics": {
            "quality_tier": cfg("graphics", "quality_tier"),
            "idle_tour_seconds": cfg("graphics", "idle_tour_seconds"),
            "ambient_sound_default": cfg("graphics", "ambient_sound_default"),
        },
        # --- v4 client tunables (manual §26) ---
        "globe": {
            "hit_test_use_facing_occlusion": cfg("globe", "hit_test_use_facing_occlusion"),
            "cluster_screen_distance_px": cfg("globe", "cluster_screen_distance_px"),
            "boundary_resolution": cfg("globe", "boundary_resolution"),
            "boundary_resolution_far_zoom": cfg("globe", "boundary_resolution_far_zoom"),
        },
        "geocoding": {
            "min_confidence_for_solid_marker":
                cfg("geocoding", "min_confidence_for_solid_marker"),
        },
        "map2d": {
            "wraparound_enabled": cfg("map2d", "wraparound_enabled"),
            "city_label_min_population_by_zoom":
                cfg("map2d", "city_label_min_population_by_zoom"),
        },
        "relevance": {
            "global_relevance_default_filter":
                cfg("relevance", "global_relevance_default_filter"),
            "global_relevance_floor": cfg("relevance", "global_relevance_floor"),
        },
        "audio": {
            "master_gain_default": cfg("audio", "master_gain_default"),
            "preset": cfg("audio", "preset"),
            "presets_active": cfg("audio", "presets_active"),   # v6 §17
        },
        "panes": {
            "transition_duration_ms": cfg("panes", "transition_duration_ms"),
            "respect_prefers_reduced_motion":
                cfg("panes", "respect_prefers_reduced_motion"),
        },
        "alerts": {
            "in_app_breaking_alert_severity_floor":
                cfg("alerts", "in_app_breaking_alert_severity_floor"),
        },
        "annotations": {"enabled": cfg("annotations", "enabled")},
        "coverage": {"thin_coverage_story_floor":
                     cfg("coverage", "thin_coverage_story_floor")},
        "onboarding": {"require_ai_key_before_first_run":
                       cfg("onboarding", "require_ai_key_before_first_run")},
        # --- v5 client tunables (manual §22) ---
        "panels": {
            "resizable": cfg("panels", "resizable"),
            "min_width_px": cfg("panels", "min_width_px"),
            "max_width_px": cfg("panels", "max_width_px"),
            "persist_across_restarts": cfg("panels", "persist_across_restarts"),
        },
        "themes": {"available": cfg("themes", "available")},
        "content": {"strip_links_from_titles": cfg("content", "strip_links_from_titles")},
        "globe_v5": {"terrain_texture_enabled": cfg("globe", "terrain_texture_enabled"),
                     "beacon_render_mode": cfg("globe", "beacon_render_mode")},
        # --- v6 client tunables (manual §32) ---
        "ui": {"vr_button_visible": cfg("ui", "vr_button_visible"),
               "city_lights_enabled_default": cfg("ui", "city_lights_enabled_default"),
               "wordmark_transliteration": cfg("ui", "wordmark_transliteration"),
               "terrain_button_visible": cfg("ui", "terrain_button_visible")},
        "war_mode": {"enabled": cfg("war_mode", "enabled")},
        "translation": {"instant_translate_on_arrival":
                        cfg("translation", "instant_translate_on_arrival")},
        "map_rendering": {"tile_based_2d": cfg("map_rendering", "tile_based_2d"),
                          "tile_size_deg": cfg("map_rendering", "tile_size_deg")},
        "attribution": [GEONAMES_ATTRIBUTION,
                        "Boundaries & coastlines: Natural Earth (public domain)"],
    }
