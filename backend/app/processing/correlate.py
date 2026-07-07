"""Stage 4 — cross-stream correlation engine (v1 Section 5.4; v2 §3.1/3.3/3.6).

For each new event:
  (a) same-window pass: cosine similarity against events within
      same_window_max_gap_hours, threshold same_window_similarity_threshold.
  (b) historical pass: cosine similarity against the ENTIRE fact chain
      (no time gate), stricter historical_similarity_threshold — the
      long-horizon memory that differentiates this system (Section 2.2).

Secondary signals (never hard gates):
  - geographic overlap within geo_overlap_radius_km (v1 step 5);
  - shared canonical entities (v2 §3.1) add entity_overlap_boost.

v2 §3.3: facts marked duplicate_of_fact_id (wire copies) are excluded as
historical candidates so syndicated copies don't self-correlate.

v2 §3.6: the historical pass reads from an in-memory fact-chain cache
(incrementally appended by created_at) instead of re-fetching and
re-unpacking every embedding from SQLite each pass. Full ANN indexing
stays deferred per the addendum ("build when the linear scan is actually
measured as slow, not preemptively") — this cache is the sanctioned
intermediate step and the swap point when that day comes.

Writes stories + story_members with linked_via = 'same_window' |
'historical_chain'. All thresholds come from config.yaml (Section 7.2).
"""

import json
import logging
import threading
from datetime import datetime, timedelta, timezone

from ..config import cfg
from ..db.models import new_id, now_iso, unpack_embedding
from ..db.session import query, query_one, write_tx
from .embed import cosine
from .gazetteer import haversine_km

log = logging.getLogger("correlate")

GEO_BOOST = 0.02  # secondary-signal nudge, well under threshold spacing


def _iso_hours_ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(
        timespec="seconds").replace("+00:00", "Z")


class FactChainCache:
    """§3.6 — in-memory copy of the historical fact chain for the linear
    cosine scan: (fact_id, event_id, when_occurred, embedding, entity_ids)."""

    def __init__(self) -> None:
        self._facts: list[tuple] = []
        self._loaded_through = ""
        self._lock = threading.Lock()

    def _append_since(self, since: str) -> None:
        rows = query(
            "SELECT id, event_id, when_occurred, created_at, embedding, canonical_entity_ids"
            " FROM extracted_facts WHERE is_synthetic = 0 AND embedding IS NOT NULL"
            " AND duplicate_of_fact_id IS NULL AND created_at > ?"
            " ORDER BY created_at", (since,))
        for r in rows:
            ents = frozenset(json.loads(r["canonical_entity_ids"])
                             if r["canonical_entity_ids"] else [])
            self._facts.append((r["id"], r["event_id"], r["when_occurred"],
                                unpack_embedding(r["embedding"]), ents))
            self._loaded_through = max(self._loaded_through, r["created_at"])

    def snapshot(self) -> list[tuple]:
        with self._lock:
            self._append_since(self._loaded_through)
            return list(self._facts)

    def invalidate(self) -> None:
        with self._lock:
            self._facts.clear()
            self._loaded_through = ""


fact_chain_cache = FactChainCache()


def effective_thresholds(category: str) -> tuple[float, float]:
    """v3 §5 — per-category tuned thresholds, else the config defaults."""
    row = query_one("SELECT same_window_threshold, historical_threshold"
                    " FROM category_thresholds WHERE category = ?", (category,))
    if row:
        return float(row["same_window_threshold"]), float(row["historical_threshold"])
    return (float(cfg("correlation", "same_window_similarity_threshold")),
            float(cfg("correlation", "historical_similarity_threshold")))


def _geo_boost(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return 0.0
    radius = float(cfg("correlation", "geo_overlap_radius_km"))
    return GEO_BOOST if haversine_km(lat1, lon1, lat2, lon2) <= radius else 0.0


def _entities_of_event(event_id: str) -> frozenset:
    row = query_one("SELECT canonical_entity_ids FROM extracted_facts WHERE event_id = ?"
                    " LIMIT 1", (event_id,))
    if row and row["canonical_entity_ids"]:
        return frozenset(json.loads(row["canonical_entity_ids"]))
    return frozenset()


def _entity_boost(ents_a: frozenset, ents_b: frozenset) -> float:
    if ents_a and ents_b and ents_a & ents_b:
        return float(cfg("correlation", "entity_overlap_boost"))
    return 0.0


def _story_of_event(event_id: str):
    row = query_one("SELECT story_id FROM story_members WHERE event_id = ? LIMIT 1",
                    (event_id,))
    return row["story_id"] if row else None


def _add_member(conn, story_id: str, *, event_id=None, fact_id=None, linked_via: str):
    conn.execute(
        "INSERT OR IGNORE INTO story_members (story_id, event_id, fact_id, linked_via,"
        " linked_at) VALUES (?,?,?,?,?)",
        (story_id, event_id, fact_id, linked_via, now_iso()))
    conn.execute(
        "UPDATE stories SET last_updated_at = ?, needs_causal_refresh = 1 WHERE id = ?",
        (now_iso(), story_id))


def _create_story(conn, headline: str, first_seen_at: str) -> str:
    story_id = new_id()
    # v4 §11.1 — normalize only the system's own display headline; the raw
    # source text on the underlying raw_item is never modified
    from .textquality import normalize_headline
    conn.execute(
        "INSERT INTO stories (id, headline, summary, confidence, first_seen_at,"
        " last_updated_at, needs_causal_refresh) VALUES (?,?,?,?,?,?,1)",
        (story_id, normalize_headline(headline), "", "low", first_seen_at, now_iso()))
    return story_id


def correlate_event(event_id: str) -> dict:
    """Run both correlation passes for one event. Returns
    {story_id, created, updated} or {} when nothing linked."""
    ev = query_one("SELECT * FROM events WHERE id = ?", (event_id,))
    if ev is None or ev["embedding"] is None:
        return {}
    vec = unpack_embedding(ev["embedding"])
    ev_entities = _entities_of_event(event_id)
    # v3 §5 — per-category self-tuned thresholds override the config default
    # (within the configured safe band); fall back to config when untuned.
    same_thresh, hist_thresh = effective_thresholds(ev["category"])
    gap_hours = float(cfg("correlation", "same_window_max_gap_hours"))

    created = updated = False
    story_id = _story_of_event(event_id)

    # --- (a) same-window pass ---
    window_rows = query(
        "SELECT e.id, e.title, e.occurred_at, e.location_lat, e.location_lon, e.embedding,"
        " f.canonical_entity_ids"
        " FROM events e LEFT JOIN extracted_facts f ON f.event_id = e.id"
        " WHERE e.id != ? AND e.is_synthetic = 0 AND e.embedding IS NOT NULL"
        " AND e.occurred_at >= ?"
        " ORDER BY e.occurred_at DESC LIMIT 2000",
        (event_id, _iso_hours_ago(gap_hours)))
    best_match, best_sim = None, same_thresh
    for other in window_rows:
        sim = cosine(vec, unpack_embedding(other["embedding"]))
        sim += _geo_boost(ev["location_lat"], ev["location_lon"],
                          other["location_lat"], other["location_lon"])
        other_ents = frozenset(json.loads(other["canonical_entity_ids"])
                               if other["canonical_entity_ids"] else [])
        sim += _entity_boost(ev_entities, other_ents)
        if sim >= best_sim:
            best_match, best_sim = other, sim

    if best_match is not None:
        other_story = _story_of_event(best_match["id"])
        with write_tx() as conn:
            if story_id is None and other_story is None:
                first_seen = min(ev["occurred_at"], best_match["occurred_at"])
                story_id = _create_story(conn, ev["title"], first_seen)
                _add_member(conn, story_id, event_id=best_match["id"], linked_via="same_window")
                created = True
            else:
                story_id = story_id or other_story
                if other_story is None:
                    _add_member(conn, story_id, event_id=best_match["id"],
                                linked_via="same_window")
            _add_member(conn, story_id, event_id=event_id, linked_via="same_window")
            updated = not created
        log.info("correlated", extra={"data": {"event_id": event_id, "via": "same_window",
                                               "similarity": round(best_sim, 4),
                                               "story_id": story_id}})

    # --- (b) historical fact-chain pass (no time gate, cached chain §3.6) ---
    window_floor = _iso_hours_ago(gap_hours)
    best_fact, best_fact_sim = None, hist_thresh
    for fact_id, fact_event_id, when_occurred, fact_vec, fact_ents in \
            fact_chain_cache.snapshot():
        if fact_event_id == event_id or when_occurred >= window_floor:
            continue
        sim = cosine(vec, fact_vec) + _entity_boost(ev_entities, fact_ents)
        if sim >= best_fact_sim:
            best_fact, best_fact_sim = (fact_id, fact_event_id), sim

    if best_fact is not None:
        with write_tx() as conn:
            if story_id is None:
                story_id = _create_story(conn, ev["title"], ev["occurred_at"])
                _add_member(conn, story_id, event_id=event_id, linked_via="same_window")
                created = True
            _add_member(conn, story_id, fact_id=best_fact[0],
                        event_id=best_fact[1], linked_via="historical_chain")
            # v3 §8 — record the lineage edge at the exact moment one fact
            # influences a future one (the historical_chain link IS that event)
            new_fact = conn.execute(
                "SELECT id FROM extracted_facts WHERE event_id = ? LIMIT 1",
                (event_id,)).fetchone()
            if new_fact:
                conn.execute(
                    "INSERT OR IGNORE INTO lineage_edges (id, from_fact_id, to_fact_id,"
                    " via_story_id, created_at) VALUES (?,?,?,?,?)",
                    (new_id(), best_fact[0], new_fact["id"], story_id, now_iso()))
            updated = not created
        log.info("correlated", extra={"data": {"event_id": event_id,
                                               "via": "historical_chain",
                                               "similarity": round(best_fact_sim, 4),
                                               "story_id": story_id}})

    if story_id is None:
        return {}
    # v5 §6 — THE conflict-tab bug: v3 §15.1 specified auto-suggest but only
    # the confirm/clear half was ever implemented, so suggested_conflict_id
    # was never written and every conflict tab stayed empty. Write it here,
    # in the correlation step, the moment a story shares canonical entities
    # with a conflict's registered parties — gated on development_type =
    # 'conflict' (v5 §3) so posturing/drills never populate a conflict tab.
    try:
        _suggest_conflict_tag(story_id)
    except Exception:  # noqa: BLE001 — suggestion is best-effort, never blocks
        log.exception("conflict_suggest_failed", extra={"data": {"story_id": story_id}})
    return {"story_id": story_id, "created": created, "updated": updated}


def _conflict_party_entities() -> dict:
    """canonical-entity-id set per conflict, from registered parties (v3 §15).
    NSAs carry a canonical id directly; countries resolve theirs by name."""
    from .entities import resolve_entity
    out: dict = {}
    for row in query(
            "SELECT cp.conflict_id, cp.country_id, n.canonical_entity_id,"
            " c.name AS country_name FROM conflict_parties cp"
            " LEFT JOIN non_state_actors n ON n.id = cp.non_state_actor_id"
            " LEFT JOIN countries c ON c.id = cp.country_id"):
        ents = out.setdefault(row["conflict_id"], set())
        if row["canonical_entity_id"]:
            ents.add(row["canonical_entity_id"])
        elif row["country_name"]:
            cent = resolve_entity(row["country_name"])
            if cent:
                ents.add(cent)
    return out


def _suggest_conflict_tag(story_id: str) -> None:
    """Write stories.suggested_conflict_id when a story's member facts share
    canonical entities with a conflict's parties AND at least one member
    event is development_type='conflict'. One-click confirm still applies
    (routes_geo.confirm_conflict_tag) — this only fills the suggest queue
    that v3 left permanently empty."""
    existing = query_one(
        "SELECT conflict_id, suggested_conflict_id FROM stories WHERE id = ?",
        (story_id,))
    if not existing or existing["conflict_id"] or existing["suggested_conflict_id"]:
        return  # already tagged or already suggested
    # v5 §3 — only literal war-scale ('conflict') developments qualify;
    # a story that's purely 'military' posturing never auto-suggests a tag
    has_conflict_dev = query_one(
        "SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
        " WHERE m.story_id = ? AND e.development_type = 'conflict' LIMIT 1",
        (story_id,))
    if not has_conflict_dev:
        return
    story_ents: set = set()
    for f in query(
            "SELECT f.canonical_entity_ids FROM story_members m"
            " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
            " WHERE m.story_id = ? AND f.canonical_entity_ids IS NOT NULL",
            (story_id,)):
        story_ents.update(json.loads(f["canonical_entity_ids"]))
    if not story_ents:
        return
    floor = float(cfg("geopolitical_entities", "conflict_autotag_confidence_floor"))
    best_cid, best_conf = None, 0.0
    for cid, ents in _conflict_party_entities().items():
        matches = len(story_ents & ents)
        if matches == 0:
            continue
        confidence = min(1.0, 0.6 + 0.15 * matches)
        if confidence > best_conf:
            best_cid, best_conf = cid, confidence
    if best_cid and best_conf >= floor:
        with write_tx() as conn:
            conn.execute("UPDATE stories SET suggested_conflict_id = ? WHERE id = ?",
                         (best_cid, story_id))
        log.info("conflict_suggested", extra={"data": {"story_id": story_id,
                                                       "conflict_id": best_cid,
                                                       "confidence": round(best_conf, 2)}})


def correlate_new_events(event_ids: list[str]) -> list[dict]:
    """Correlation failures on one item never block the batch (Section 10.2)."""
    results = []
    for event_id in event_ids:
        try:
            res = correlate_event(event_id)
            if res:
                results.append(res)
        except Exception:  # noqa: BLE001
            log.exception("correlate_failed", extra={"data": {"event_id": event_id}})
    return results
