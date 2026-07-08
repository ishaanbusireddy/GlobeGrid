"""v6.6.6 — LLM-assisted event geoplacement correction.

The gazetteer places events by string-matching place names, which sometimes
resolves an incidental mention to the wrong country — events "randomly popping
up in India" being the reported symptom (a stray capitalized span matching an
obscure Indian locality, or an incidental country mention taken as the
dateline). Owner: "use the LLM to place and understand events (or move them
after initial placement)".

This runs as a bounded background correction: it takes recent events whose
geocode is missing or only country-level (low confidence), asks the model for
the real location (country + city + coordinates), and updates the row. The
map then shows the corrected position. Deliberately small per tick and gated
on a reachable provider so it never slows ingestion or burns rate limit."""

import json as _json

from ..db.session import query, write_tx
from ..db.models import now_iso
from . import llm

GEOPLACE_PROMPT = """You are a geolocation analyst. Given a news event's title and
description, identify WHERE in the world the event actually takes place — the
primary location the event is about, not merely a country mentioned in passing.

Return ONLY valid JSON:
{
  "place": string,        // "City, Country" or "Country" if no city is clear
  "country_iso3": string, // ISO-3166 alpha-3, e.g. "USA", "UKR", "" if unclear
  "lat": number,          // decimal latitude of that place
  "lon": number,          // decimal longitude
  "confidence": number    // 0.0-1.0, your confidence in this placement
}
If the event has no meaningful physical location (e.g. a purely abstract
market note), return {"place":"","country_iso3":"","lat":0,"lon":0,"confidence":0}."""


def place_event(title, description):
    """Ask the model to locate one event. Returns a dict with place/lat/lon/
    confidence, or None. Best-effort; never raises."""
    if not llm.available():
        return None
    ctx = {"title": title or "", "description": (description or "")[:600]}
    try:
        text = llm.complete(GEOPLACE_PROMPT,
                            [{"role": "user", "content": _json.dumps(ctx)}],
                            max_tokens=160, timeout=40, json_mode=True)
    except Exception:  # noqa: BLE001
        return None
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").removeprefix("json").strip()
    b = t.find("{")
    if b != -1:
        t = t[b:t.rfind("}") + 1]
    try:
        d = _json.loads(t)
    except _json.JSONDecodeError:
        return None
    try:
        lat = float(d.get("lat"))
        lon = float(d.get("lon"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    return {"place": d.get("place") or "", "lat": lat, "lon": lon,
            "confidence": float(d.get("confidence") or 0.7)}


def correct_recent(limit=4):
    """v6.6.6 — re-place a small batch of recent events whose geocode is missing
    or only country-level (confidence < 0.7 or NULL). Updates the DB and returns
    a list of {id, lat, lon, location_name} for the events that were moved, so
    the caller can push a live 'event_relocated' to move the map pins."""
    if not llm.available():
        return []
    rows = query(
        "SELECT id, title, description, location_lat, location_lon, geocode_confidence"
        " FROM events"
        " WHERE is_synthetic = 0"
        "   AND (geocode_confidence IS NULL OR geocode_confidence < 0.7)"
        "   AND (llm_geoplaced IS NULL OR llm_geoplaced = 0)"
        " ORDER BY occurred_at DESC LIMIT ?",
        (limit,))
    moved = []
    for r in rows:
        placed = place_event(r["title"], r["description"])
        # mark as attempted either way so we don't retry the same event forever
        try:
            with write_tx() as conn:
                if placed:
                    conn.execute(
                        "UPDATE events SET location_lat = ?, location_lon = ?,"
                        " location_name = COALESCE(NULLIF(?, ''), location_name),"
                        " geocode_confidence = ?, llm_geoplaced = 1 WHERE id = ?",
                        (placed["lat"], placed["lon"], placed["place"],
                         max(placed["confidence"], 0.7), r["id"]))
                else:
                    conn.execute("UPDATE events SET llm_geoplaced = 1 WHERE id = ?",
                                 (r["id"],))
        except Exception:  # noqa: BLE001
            continue
        if placed:
            moved.append({"id": r["id"], "lat": placed["lat"], "lon": placed["lon"],
                          "location_name": placed["place"]})
    return moved


def ensure_column():
    """Add the llm_geoplaced flag column if the schema predates it (additive,
    idempotent)."""
    try:
        with write_tx() as conn:
            cols = [c[1] for c in conn.execute("PRAGMA table_info(events)").fetchall()]
            if "llm_geoplaced" not in cols:
                conn.execute("ALTER TABLE events ADD COLUMN llm_geoplaced INTEGER DEFAULT 0")
    except Exception:  # noqa: BLE001
        pass
