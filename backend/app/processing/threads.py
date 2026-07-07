"""v6 §27 — Story Threads: the macro-trend grouping layer above stories.

Individual story clusters (v1 §5.4) are too granular for trends like
'Strait of Hormuz Developments' or 'EU-Russia Tensions'. A thread groups
related stories over time — a presentation layer, never a replacement for
the underlying story taxonomy. Assignment runs as a periodic job:

1. every unthreaded recent story is compared against existing threads by
   shared canonical entities + embedding proximity to the thread centroid;
2. still-unthreaded stories are clustered among themselves; a cluster of
   two or more becomes a new thread;
3. the thread name/description are synthesized by the Groq-first pipeline
   (v6 §1) with a deterministic entity-based fallback, so threads exist
   with or without an AI key.
"""

import json
import logging

from . import llm
from .embed import embed_text, cosine
from ..db.models import new_id, now_iso
from ..db.session import query, query_one, write_tx

log = logging.getLogger("threads")

JOIN_SIMILARITY = 0.5      # cosine to thread centroid
PAIR_SIMILARITY = 0.55     # cosine between two unthreaded stories
MIN_SHARED_ENTITIES = 1


def _entities(story_id: str) -> frozenset:
    rows = query(
        "SELECT f.canonical_entity_ids FROM story_members m"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE m.story_id = ? AND f.canonical_entity_ids IS NOT NULL", (story_id,))
    ents: set = set()
    for r in rows:
        try:
            ents.update(json.loads(r["canonical_entity_ids"]))
        except (json.JSONDecodeError, TypeError):
            pass
    return frozenset(ents)


def _entity_label(entity_ids: frozenset) -> str | None:
    if not entity_ids:
        return None
    marks = ",".join("?" * len(entity_ids))
    row = query_one(
        f"SELECT canonical_name FROM canonical_entities WHERE id IN ({marks})"
        " ORDER BY LENGTH(canonical_name) LIMIT 1", tuple(entity_ids))
    return row["canonical_name"] if row else None


def _name_thread(headlines: list[str], fallback_entity: str | None) -> tuple[str, str]:
    """Thread name + description, LLM-synthesized with a deterministic
    fallback. Names are short noun phrases ('Strait of Hormuz Developments'),
    not sentences."""
    fallback_name = (f"{fallback_entity} Developments" if fallback_entity
                     else f"Related Developments ({headlines[0][:40]}…)")
    fallback_desc = (f"Ongoing thread grouping {len(headlines)} related tracked"
                     " stories." )
    if not llm.available():
        return fallback_name, fallback_desc
    out = llm.complete(
        "You are naming a macro-trend thread that groups related news story"
        " clusters. Return ONLY valid JSON: {\"name\": string, \"description\":"
        " string}. The name is a short, specific noun phrase like 'Strait of"
        " Hormuz Developments' (max 60 chars, no trailing period); the"
        " description is 1-2 sentences summarizing the ongoing trend.",
        [{"role": "user", "content": json.dumps({"story_headlines": headlines[:10]})}],
        max_tokens=250, timeout=45)
    if not out:
        return fallback_name, fallback_desc
    out = out.strip()
    if out.startswith("```"):
        out = out.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(out)
        name = str(data.get("name") or "").strip()[:80]
        desc = str(data.get("description") or "").strip()[:400]
        if name:
            return name, desc or fallback_desc
    except json.JSONDecodeError:
        pass
    return fallback_name, fallback_desc


def assign_threads(lookback_days: int = 30, max_new_threads: int = 4) -> int:
    """One assignment pass; returns number of membership rows written."""
    unthreaded = [dict(r) for r in query(
        "SELECT id, headline FROM stories s WHERE is_synthetic = 0"
        " AND last_updated_at >= datetime('now', ?)"
        " AND NOT EXISTS (SELECT 1 FROM story_thread_members m WHERE m.story_id = s.id)"
        " ORDER BY last_updated_at DESC LIMIT 60", (f"-{lookback_days} day",))]
    if not unthreaded:
        return 0
    for s in unthreaded:
        s["ents"] = _entities(s["id"])
        s["vec"] = embed_text(s["headline"] or "")

    # existing threads with centroid + entity pool
    threads = []
    for t in query("SELECT id, name FROM story_threads"):
        members = query(
            "SELECT s.id, s.headline FROM story_thread_members m"
            " JOIN stories s ON s.id = m.story_id WHERE m.thread_id = ?"
            " ORDER BY s.last_updated_at DESC LIMIT 12", (t["id"],))
        if not members:
            continue
        vecs = [embed_text(m["headline"] or "") for m in members]
        centroid = [sum(col) / len(col) for col in zip(*vecs)]
        ents: set = set()
        for m in members:
            ents |= _entities(m["id"])
        threads.append({"id": t["id"], "centroid": centroid, "ents": ents})

    written = 0
    still = []
    with write_tx() as conn:
        for s in unthreaded:
            joined = False
            for t in threads:
                shared = len(s["ents"] & t["ents"])
                sim = cosine(s["vec"], t["centroid"])
                if (shared >= MIN_SHARED_ENTITIES and sim >= JOIN_SIMILARITY) \
                        or shared >= 2:
                    conn.execute(
                        "INSERT OR IGNORE INTO story_thread_members (thread_id, story_id)"
                        " VALUES (?,?)", (t["id"], s["id"]))
                    conn.execute("UPDATE story_threads SET last_updated_at = ?"
                                 " WHERE id = ?", (now_iso(), t["id"]))
                    t["ents"] |= s["ents"]
                    written += 1
                    joined = True
                    break
            if not joined:
                still.append(s)

    # cluster the leftovers into new threads
    made = 0
    used: set = set()
    for i, a in enumerate(still):
        if a["id"] in used or made >= max_new_threads:
            continue
        group = [a]
        for b in still[i + 1:]:
            if b["id"] in used:
                continue
            shared = len(a["ents"] & b["ents"])
            if shared >= MIN_SHARED_ENTITIES and \
                    cosine(a["vec"], b["vec"]) >= PAIR_SIMILARITY:
                group.append(b)
        if len(group) < 2:
            continue
        shared_ents = frozenset.intersection(*(g["ents"] for g in group)) \
            if all(g["ents"] for g in group) else frozenset()
        name, desc = _name_thread([g["headline"] for g in group],
                                  _entity_label(shared_ents))
        tid = new_id()
        with write_tx() as conn:
            # UNIQUE(name): a same-named thread absorbs the group instead
            existing = conn.execute("SELECT id FROM story_threads WHERE name = ?",
                                    (name,)).fetchone()
            if existing:
                tid = existing["id"]
            else:
                conn.execute(
                    "INSERT INTO story_threads (id, name, description, first_seen_at,"
                    " last_updated_at) VALUES (?,?,?,?,?)",
                    (tid, name, desc, now_iso(), now_iso()))
                made += 1
            for g in group:
                conn.execute("INSERT OR IGNORE INTO story_thread_members"
                             " (thread_id, story_id) VALUES (?,?)", (tid, g["id"]))
                used.add(g["id"])
                written += 1
        log.info("thread_created", extra={"data": {"name": name,
                                                   "stories": len(group)}})
    return written
