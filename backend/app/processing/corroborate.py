"""v7 §5 — ground-truth fusion: the corroboration score.

Text can lie; physics is harder. When a conflict/military/disaster story's
location coincides in SPACE (radius) and TIME (window) with events from
physical-sensor sources the LLM cannot hallucinate — NASA FIRMS thermal
anomalies, OpenSky air-traffic anomalies, USGS seismic events, ACLED coded
incidents, AIS maritime-chokepoint anomalies, and VIIRS nighttime-lights
blackouts (v7.2) — the story earns a corroboration score: text + physical
signal agreeing. That is the difference between a news reader and an
intelligence platform.

Score: 0.35 for the first corroborating sensor event, +0.15 each additional,
capped at 0.95; different SENSOR TYPES corroborating the same story add a
+0.1 diversity bonus. Stored on the story (`corroboration`,
`corroboration_detail`) and pushed live so open feeds update in place.
"""

import json
import math

from ..db.models import now_iso
from ..db.session import query, write_tx
import logging

log = logging.getLogger("corroborate")

SENSOR_SOURCE_TYPES = ("firms", "opensky", "usgs", "acled", "ais", "nightlights")
RADIUS_KM = 120.0
WINDOW_HOURS = 36.0


def ensure_columns():
    cols = {r["name"] for r in query("PRAGMA table_info(stories)")}
    with write_tx() as conn:
        if "corroboration" not in cols:
            conn.execute("ALTER TABLE stories ADD COLUMN corroboration REAL")
        if "corroboration_detail" not in cols:
            conn.execute("ALTER TABLE stories ADD COLUMN corroboration_detail TEXT")


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def score_recent(limit=12):
    """Corroborate the most recent located conflict/military/disaster stories
    against sensor-sourced events. Returns [{story_id, corroboration, detail}]
    for stories whose score CHANGED (for live push)."""
    stories = query("""
        SELECT s.id, e.location_lat AS lat, e.location_lon AS lon,
               e.occurred_at, e.category, s.corroboration AS old
          FROM stories s
          JOIN story_members sm ON sm.story_id = s.id
          JOIN events e ON e.id = sm.event_id
         WHERE s.is_synthetic = 0 AND e.location_lat IS NOT NULL
           AND e.category IN ('conflict','military','disaster')
         GROUP BY s.id ORDER BY s.last_updated_at DESC LIMIT ?""", (limit,))
    changed = []
    for st in stories:
        sensors = query("""
            SELECT e.id, e.title, e.location_lat AS lat, e.location_lon AS lon,
                   src.type AS stype
              FROM events e
              JOIN raw_items ri ON ri.id = e.raw_item_id
              JOIN sources src ON src.id = ri.source_id
             WHERE src.type IN ({q}) AND e.location_lat IS NOT NULL
               AND ABS(julianday(e.occurred_at) - julianday(?)) <= ?
             LIMIT 400""".format(q=",".join("?" * len(SENSOR_SOURCE_TYPES))),
            (*SENSOR_SOURCE_TYPES, st["occurred_at"], WINDOW_HOURS / 24.0))
        hits, types = [], set()
        for sn in sensors:
            try:
                d = _haversine_km(st["lat"], st["lon"], sn["lat"], sn["lon"])
            except (TypeError, ValueError):
                continue
            if d <= RADIUS_KM:
                hits.append({"type": sn["stype"], "title": sn["title"],
                             "km": round(d)})
                types.add(sn["stype"])
        score = None
        if hits:
            score = min(0.95, 0.35 + 0.15 * (len(hits) - 1)
                        + (0.1 if len(types) > 1 else 0.0))
            score = round(score, 2)
        if score != st["old"] and (score or st["old"]):
            detail = {"hits": hits[:6], "sensor_types": sorted(types),
                      "radius_km": RADIUS_KM, "window_hours": WINDOW_HOURS,
                      "scored_at": now_iso()}
            try:
                with write_tx() as conn:
                    conn.execute(
                        "UPDATE stories SET corroboration = ?,"
                        " corroboration_detail = ? WHERE id = ?",
                        (score, json.dumps(detail), st["id"]))
                changed.append({"story_id": st["id"], "corroboration": score,
                                "detail": detail})
            except Exception:  # noqa: BLE001
                continue
    if changed:
        log.info("corroboration_updated",
                 extra={"data": {"stories": len(changed)}})
    return changed
