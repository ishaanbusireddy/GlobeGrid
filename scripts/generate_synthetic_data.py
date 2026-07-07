#!/usr/bin/env python3
"""Section 12 — synthetic dataset generator.

    python scripts/generate_synthetic_data.py            generate
    python scripts/generate_synthetic_data.py --purge    delete ALL synthetic rows

Defaults (Section 12.1): 300 events across ~40 real-world population
centers with randomized jitter, 60 stories linking 2-6 events each,
clearly-labeled placeholder causal_narrative JSON, instability_scores
backfilled hourly for the past 7 days. Every row carries the _synthetic
flag (is_synthetic column) so Phase 5 can purge in one operation.

Also mirrors the output into frontend/src/data/syntheticDataset.js for
local frontend dev per Section 13.
"""

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.app.db.models import migrate, new_id, now_iso, pack_embedding  # noqa: E402
from backend.app.db.session import write_tx, query  # noqa: E402
from backend.app.ingestion.seed import get_synthetic_source_id  # noqa: E402
from backend.app.processing.embed import embed_text  # noqa: E402
from backend.app.processing.gazetteer import PLACES, POPULATION_CENTERS  # noqa: E402

N_EVENTS = 300
N_STORIES = 60
JITTER_DEG = 1.5

CATEGORIES = ["geopolitics", "finance", "disaster", "conflict", "other"]
TEMPLATES = [
    ("Port congestion reported at major shipping hub",
     "shipping delays reported, {place}, container backlog", "finance"),
    ("Currency drops sharply against the dollar",
     "currency depreciation, {place}, central bank pressure", "finance"),
    ("Large protest gathers in city center",
     "mass protest, {place}, government response pending", "geopolitics"),
    ("Magnitude 5.8 earthquake strikes region",
     "seismic event, {place}, structural damage assessed", "disaster"),
    ("Cross-border shelling reported overnight",
     "artillery exchange, {place}, casualties unconfirmed", "conflict"),
    ("Parliament passes emergency budget measure",
     "emergency legislation, {place}, fiscal response", "geopolitics"),
    ("Wildfire forces evacuations near suburbs",
     "wildfire spread, {place}, evacuation orders issued", "disaster"),
    ("Regional stock index falls 3% on policy news",
     "equity sell-off, {place}, policy uncertainty", "finance"),
    ("Diplomatic talks stall over trade terms",
     "negotiation impasse, {place}, tariff dispute", "geopolitics"),
    ("Supply disruption hits energy exports",
     "energy export disruption, {place}, pipeline maintenance", "finance"),
]


def generate() -> None:
    random.seed(42)
    migrate()
    source_id = get_synthetic_source_id()
    now = datetime.now(timezone.utc)
    events, stories, members, scores = [], [], [], []

    for _ in range(N_EVENTS):
        center = random.choice(POPULATION_CENTERS)
        lat0, lon0 = PLACES[center]
        title, desc_tpl, category = random.choice(TEMPLATES)
        place = center.title()
        occurred = now - timedelta(hours=random.uniform(0, 7 * 24))
        events.append({
            "id": new_id(), "title": title,
            "description": desc_tpl.format(place=place),
            "lat": lat0 + random.uniform(-JITTER_DEG, JITTER_DEG),
            "lon": lon0 + random.uniform(-JITTER_DEG, JITTER_DEG),
            "location_name": place, "category": category,
            "severity": random.randint(1, 5),
            "occurred_at": occurred.isoformat(timespec="seconds").replace("+00:00", "Z"),
        })

    pool = list(events)
    random.shuffle(pool)
    idx = 0
    for _ in range(N_STORIES):
        size = random.randint(2, 6)
        chunk = pool[idx:idx + size]
        idx += size
        if len(chunk) < 2:
            break
        chunk.sort(key=lambda e: e["occurred_at"])
        story_id = new_id()
        placeholder = {
            "cause": f"[SYNTHETIC PLACEHOLDER] Simulated trigger event near "
                     f"{chunk[0]['location_name']} — not real analysis.",
            "affected": [e["location_name"] for e in chunk[:3]],
            "consequences": ["[SYNTHETIC PLACEHOLDER] downstream effect A",
                             "[SYNTHETIC PLACEHOLDER] downstream effect B"],
            "confidence": random.choice(["high", "medium", "low"]),
        }
        stories.append({
            "id": story_id,
            "headline": f"[SYNTHETIC] {chunk[0]['title']}",
            "summary": "[SYNTHETIC PLACEHOLDER] Structurally valid demo story cluster "
                       f"linking {len(chunk)} generated events. Not real analysis.",
            "causal_narrative": placeholder,
            "confidence": placeholder["confidence"],
            "first_seen_at": chunk[0]["occurred_at"],
            "last_updated_at": chunk[-1]["occurred_at"],
        })
        for i, e in enumerate(chunk):
            members.append({
                "story_id": story_id, "event_id": e["id"],
                "linked_via": "historical_chain" if (i == len(chunk) - 1 and len(chunk) > 2)
                              else "same_window",
                "linked_at": e["occurred_at"],
            })

    for h in range(7 * 24, -1, -1):
        t = now - timedelta(hours=h)
        base = 35 + 20 * random.random() + 10 * (1 if h % 24 < 6 else 0)
        scores.append({
            "id": new_id(), "score": round(min(100, base), 2),
            "computed_at": t.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "component_breakdown": {"volume": {"raw": random.randint(20, 90)},
                                    "severity": {"raw": round(random.uniform(1, 4), 2)},
                                    "spread": {"raw": random.randint(3, 20)},
                                    "_synthetic": True},
        })

    with write_tx() as conn:
        for e in events:
            raw_id = new_id()
            conn.execute(
                "INSERT INTO raw_items (id, source_id, raw_content, fetched_at, processed,"
                " external_id) VALUES (?,?,?,?,1,?)",
                (raw_id, source_id, json.dumps({"title": e["title"], "_synthetic": True}),
                 now_iso(), e["id"]))
            conn.execute(
                "INSERT INTO events (id, raw_item_id, title, description, location_lat,"
                " location_lon, location_name, category, severity, occurred_at, embedding,"
                " is_synthetic) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
                (e["id"], raw_id, e["title"], e["description"], e["lat"], e["lon"],
                 e["location_name"], e["category"], e["severity"], e["occurred_at"],
                 pack_embedding(embed_text(e["description"]))))
        for s in stories:
            conn.execute(
                "INSERT INTO stories (id, headline, summary, causal_narrative, confidence,"
                " first_seen_at, last_updated_at, needs_causal_refresh, is_synthetic)"
                " VALUES (?,?,?,?,?,?,?,0,1)",
                (s["id"], s["headline"], s["summary"], json.dumps(s["causal_narrative"]),
                 s["confidence"], s["first_seen_at"], s["last_updated_at"]))
        for m in members:
            conn.execute(
                "INSERT OR IGNORE INTO story_members (story_id, event_id, linked_via,"
                " linked_at, is_synthetic) VALUES (?,?,?,?,1)",
                (m["story_id"], m["event_id"], m["linked_via"], m["linked_at"]))
        for sc in scores:
            conn.execute(
                "INSERT INTO instability_scores (id, score, computed_at,"
                " component_breakdown, is_synthetic) VALUES (?,?,?,?,1)",
                (sc["id"], sc["score"], sc["computed_at"],
                 json.dumps(sc["component_breakdown"])))

    _mirror_to_frontend(events, stories, members, scores)
    print(f"synthetic: {len(events)} events, {len(stories)} stories, "
          f"{len(members)} members, {len(scores)} instability scores")


def _mirror_to_frontend(events, stories, members, scores) -> None:
    """Section 13: frontend/src/data/syntheticDataset.js mirrors the generator."""
    dataset = {
        "generated_at": now_iso(),
        "_synthetic": True,
        "events": [{**{k: v for k, v in e.items() if k not in ("lat", "lon")},
                    "location": {"lat": e["lat"], "lon": e["lon"]},
                    "_synthetic": True} for e in events],
        "stories": [{**s, "_synthetic": True} for s in stories],
        "story_members": [{**m, "_synthetic": True} for m in members],
        "instability_scores": scores,
    }
    out = REPO_ROOT / "frontend" / "src" / "data" / "syntheticDataset.js"
    out.write_text(
        "// GENERATED by scripts/generate_synthetic_data.py (Section 12) — do not edit.\n"
        "// Placeholder demo data, every row flagged _synthetic: true (purgeable).\n"
        "export const SYNTHETIC_DATASET = "
        + json.dumps(dataset, indent=1) + ";\n", encoding="utf-8")
    print(f"mirrored -> {out.relative_to(REPO_ROOT)}")


def purge() -> None:
    """Section 12.2 / 16 — delete every _synthetic-flagged row, one operation."""
    migrate()
    with write_tx() as conn:
        n_members = conn.execute("DELETE FROM story_members WHERE is_synthetic = 1").rowcount
        n_stories = conn.execute("DELETE FROM stories WHERE is_synthetic = 1").rowcount
        n_facts = conn.execute("DELETE FROM extracted_facts WHERE is_synthetic = 1").rowcount
        n_events = conn.execute("DELETE FROM events WHERE is_synthetic = 1").rowcount
        conn.execute("DELETE FROM raw_items WHERE source_id IN"
                     " (SELECT id FROM sources WHERE type = 'synthetic')")
        n_scores = conn.execute("DELETE FROM instability_scores WHERE is_synthetic = 1").rowcount
    print(f"purged synthetic rows: {n_events} events, {n_stories} stories, "
          f"{n_members} members, {n_facts} facts, {n_scores} instability scores")
    remaining = query("SELECT COUNT(*) AS n FROM events WHERE is_synthetic = 1")[0]["n"]
    print(f"synthetic events remaining: {remaining}")


if __name__ == "__main__":
    if "--purge" in sys.argv:
        purge()
    else:
        generate()
