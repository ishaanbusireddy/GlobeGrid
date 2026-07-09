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


def untag_wrong_insurgency_stories(limit: int = 5000) -> int:
    """v8.13 — repair existing mis-tags: clear conflict_id from any story tagged
    into an insurgency (or intra-state conflict) whose facts DON'T name that
    conflict's distinctive (non-state-actor) entity. This undoes the owner's
    reported "random Indian news → Naxalite–Maoist insurgency" bad tags left in
    the DB by the pre-v8.13 rule (a lone host-country match sufficed). One-time,
    idempotent: a story correctly tagged (its NSA IS named) is left untouched."""
    detail = _conflict_party_entities()
    # only insurgency/intra-state conflicts that actually carry a distinctive party
    suspect = {cid: rec for cid, rec in detail.items()
               if rec["is_insurgency"] and rec["distinctive"]}
    if not suspect:
        return 0
    cleared = 0
    for r in query(
            "SELECT id, conflict_id FROM stories WHERE conflict_id IN ({})".format(
                ",".join("?" * len(suspect))), tuple(suspect.keys())):
        rec = suspect.get(r["conflict_id"])
        if not rec:
            continue
        story_ents: set = set()
        for f in query(
                "SELECT f.canonical_entity_ids FROM story_members m"
                " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
                " WHERE m.story_id = ? AND f.canonical_entity_ids IS NOT NULL", (r["id"],)):
            try:
                story_ents.update(json.loads(f["canonical_entity_ids"]))
            except (ValueError, TypeError):
                pass
        if not (story_ents & rec["distinctive"]):   # the insurgent group isn't named
            with write_tx() as conn:
                conn.execute("UPDATE stories SET conflict_id = NULL,"
                             " suggested_conflict_id = NULL WHERE id = ?", (r["id"],))
            cleared += 1
            if cleared >= limit:
                break
    return cleared


def reclassify_untagged_conflicts(limit: int = 2000) -> int:
    """v7.4 — run the conflict auto-classifier over stories that have no firm
    conflict_id yet, so existing/backfilled coverage funnels into War Mode and
    the conflict tabs without waiting for each story to be re-correlated."""
    rows = query(
        "SELECT id FROM stories WHERE conflict_id IS NULL"
        " ORDER BY last_updated_at DESC LIMIT ?", (limit,))
    n = 0
    for r in rows:
        try:
            _suggest_conflict_tag(r["id"])
            n += 1
        except Exception:  # noqa: BLE001 — best-effort, never blocks startup
            pass
    return n


def _conflict_party_entities() -> dict:
    """canonical-entity-id set per conflict, from registered parties (v3 §15).
    NSAs carry a canonical id directly; countries resolve theirs by name.

    v7.4.2 — RESOLVED/old conflicts are EXCLUDED (owner: "dont tag new stories
    into old conflicts, separate old conflicts from ongoing conflicts"). Only
    ongoing (active/ceasefire) and frozen conflicts accept fresh coverage; a
    resolved war (Gulf Wars, Afghanistan 2001-21, …) never absorbs a new story
    off a shared belligerent name.

    v8.13 — each conflict now also records its DISTINCTIVE entities (the
    non-state-actor party ids) and whether it's an insurgency, separately from
    the generic host-country entities. `_suggest_conflict_tag` uses this to stop
    tagging every story about a big country into that country's own insurgency
    (owner: "random Indian news takes me to the Naxalite–Maoist insurgency" —
    India is a party to its own insurgency, so a lone India match wrongly qualified
    it). Returns {cid: {"all": set, "distinctive": set, "is_insurgency": bool}}."""
    from .entities import resolve_entity
    from ..geopolitics.seed_data import INSURGENCY_NAMES
    out: dict = {}
    for row in query(
            "SELECT cp.conflict_id, cp.country_id, n.canonical_entity_id,"
            " c.name AS country_name, cf.name AS conflict_name FROM conflict_parties cp"
            " JOIN conflicts cf ON cf.id = cp.conflict_id"
            " LEFT JOIN non_state_actors n ON n.id = cp.non_state_actor_id"
            " LEFT JOIN countries c ON c.id = cp.country_id"
            " WHERE cf.status NOT IN ('resolved', 'ended')"):
        rec = out.setdefault(row["conflict_id"], {
            "all": set(), "distinctive": set(),
            "is_insurgency": (row["conflict_name"] in INSURGENCY_NAMES
                              or "insurgency" in (row["conflict_name"] or "").lower())})
        if row["canonical_entity_id"]:
            # a non-state actor (Naxalites, PKK, Houthis…) — the DISTINCTIVE
            # signal for a conflict, especially an intra-state one.
            rec["all"].add(row["canonical_entity_id"])
            rec["distinctive"].add(row["canonical_entity_id"])
        elif row["country_name"]:
            cent = resolve_entity(row["country_name"])
            if cent:
                rec["all"].add(cent)
    return out


def _suggest_conflict_tag(story_id: str) -> None:
    """v7.4 — AUTO-CLASSIFY a story into a conflict (owner: "i want to see all
    the appropriate events for things like israel, iran, ukraine, etc going into
    the conflict slots and appearing in war mode … instead of just having the
    user manually tag them"). A story whose facts share canonical entities with
    a conflict's parties is auto-assigned `conflict_id` (so it appears in War
    Mode / conflict tabs immediately) on a strong match; a weaker single-party
    match still only fills `suggested_conflict_id` for one-click confirm.

    The old gate required a war-scale development_type='conflict' event, which
    starved the conflict tabs — now any event category qualifies as long as the
    story genuinely names the conflict's parties (that is the signal)."""
    existing = query_one(
        "SELECT conflict_id, suggested_conflict_id FROM stories WHERE id = ?",
        (story_id,))
    if not existing or existing["conflict_id"]:
        return  # already firmly tagged — never override a human/auto assignment
    story_ents: set = set()
    for f in query(
            "SELECT f.canonical_entity_ids FROM story_members m"
            " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
            " WHERE m.story_id = ? AND f.canonical_entity_ids IS NOT NULL",
            (story_id,)):
        try:
            story_ents.update(json.loads(f["canonical_entity_ids"]))
        except (ValueError, TypeError):
            pass
    if not story_ents:
        return
    # does the story carry a conflict/military development? two party matches
    # don't need it, but a lone match does (so a US–Israel trade story doesn't
    # get funnelled into the Israel–Palestine war off one shared entity).
    has_conflict_dev = query_one(
        "SELECT 1 FROM story_members m JOIN events e ON e.id = m.event_id"
        " WHERE m.story_id = ? AND (e.development_type IN ('conflict','military')"
        " OR e.category IN ('conflict','military')) LIMIT 1", (story_id,))
    # v8.13 — pick the best conflict, but track HOW it matched: total party
    # matches AND distinctive (non-state-actor) matches. An insurgency/intra-state
    # conflict must be matched by a DISTINCTIVE entity (the actual insurgent
    # group), never by the host country alone — otherwise every story about a big
    # country funnels into that country's own insurgency (the owner's Naxalite
    # bug: India is a party to the Naxalite–Maoist insurgency, so an India match
    # wrongly qualified).
    best_cid, best_matches, best_distinct, best_insurgency = None, 0, 0, False
    for cid, rec in _conflict_party_entities().items():
        matches = len(story_ents & rec["all"])
        distinct = len(story_ents & rec["distinctive"])
        # an insurgency with NO distinctive (NSA) match doesn't count at all
        if rec["is_insurgency"] and distinct == 0:
            continue
        if matches > best_matches:
            best_cid, best_matches, best_distinct = cid, matches, distinct
            best_insurgency = rec["is_insurgency"]
    if not best_cid:
        return
    # strong = ≥2 belligerent entities named (e.g. BOTH Israel & Hamas, or both
    # Russia & Ukraine), OR ≥1 party + an actual conflict/military development.
    # For an insurgency the qualifying match MUST include the insurgent group
    # itself (best_distinct >= 1, already guaranteed above), so "India + a random
    # clash keyword" no longer tags into the Naxalite insurgency.
    strong = best_matches >= 2 or (best_matches >= 1 and has_conflict_dev)
    if best_insurgency:
        strong = strong and best_distinct >= 1
    with write_tx() as conn:
        if strong:
            conn.execute("UPDATE stories SET conflict_id = ?,"
                         " suggested_conflict_id = NULL WHERE id = ?",
                         (best_cid, story_id))
            log.info("conflict_auto_tagged",
                     extra={"data": {"story_id": story_id, "conflict_id": best_cid,
                                     "party_matches": best_matches}})
        elif not existing["suggested_conflict_id"]:
            conn.execute("UPDATE stories SET suggested_conflict_id = ? WHERE id = ?",
                         (best_cid, story_id))


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
