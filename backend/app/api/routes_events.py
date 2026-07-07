"""Section 8.1 — GET /api/events (bbox, category, since; v2: as_of, format=csv)."""

import csv
import io
import json

from ..db.session import query
from ..db.models import row_to_dict
from .router import route


@route("GET", "/api/events")
def list_events(params, q, body):
    limit = min(int(q.get("limit", 500)), 2000)
    conditions, args = ["1=1"], []
    if q.get("since"):
        conditions.append("e.occurred_at > ?")
        args.append(q["since"])
    if q.get("as_of"):  # v2 §4 time capsule
        conditions.append("e.occurred_at <= ?")
        args.append(q["as_of"])
    if q.get("category"):
        conditions.append("e.category = ?")
        args.append(q["category"])
    if q.get("bbox"):
        try:
            min_lon, min_lat, max_lon, max_lat = [float(x) for x in q["bbox"].split(",")]
        except ValueError:
            return 400, {"error": "bbox must be minLon,minLat,maxLon,maxLat"}
        conditions += ["e.location_lat IS NOT NULL",
                       "e.location_lat BETWEEN ? AND ?",
                       "e.location_lon BETWEEN ? AND ?"]
        args += [min_lat, max_lat, min_lon, max_lon]
    rows = query(
        "SELECT e.*, s.name AS src_name, s.url AS src_url, r.raw_content,"
        " (SELECT story_id FROM story_members m WHERE m.event_id = e.id LIMIT 1) AS story_id"
        " FROM events e JOIN raw_items r ON r.id = e.raw_item_id"
        " JOIN sources s ON s.id = r.source_id"
        f" WHERE {' AND '.join(conditions)}"
        " ORDER BY e.occurred_at DESC LIMIT ?", (*args, limit))
    events = []
    for r in rows:
        d = row_to_dict(r, drop=("embedding", "raw_content", "src_name", "src_url"))
        try:
            link = json.loads(r["raw_content"]).get("link", "")
        except (json.JSONDecodeError, TypeError):
            link = ""
        d["source"] = {"name": r["src_name"], "url": r["src_url"], "article_link": link}
        events.append(d)
    if q.get("format") == "csv":  # v2 §6.4 export
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "title", "category", "severity", "occurred_at",
                         "location_name", "lat", "lon", "source", "story_id"])
        for e in events:
            loc = e.get("location") or {}
            writer.writerow([e["id"], e["title"], e["category"], e["severity"],
                             e["occurred_at"], e.get("location_name") or "",
                             loc.get("lat", ""), loc.get("lon", ""),
                             e["source"]["name"], e.get("story_id") or ""])
        return 200, {"_raw_csv": buf.getvalue(), "_filename": "events.csv"}
    return 200, {"events": events}
