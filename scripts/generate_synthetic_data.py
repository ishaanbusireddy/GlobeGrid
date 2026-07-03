"""Synthetic dataset generator (Section 12). Writes schema-exact rows to the
database for stress-testing Tier 1 rendering before the real pipeline is
wired in, and mirrors the same dataset to
frontend/src/data/syntheticDataset.js for local frontend dev (Section 13).

Section 12.1 defaults (all adjustable via CLI flags):
  --events 300    synthetic events across ~40 real population centers, jittered
  --stories 60    synthetic stories, each linking 2-6 events via story_members
  instability_scores backfilled hourly for the past 7 days

Every synthetic row is flagged so Phase 5 can purge it in one operation
(scripts/purge_synthetic.py): events via their raw_item's
raw_content={"_synthetic": true}, stories via causal_narrative._synthetic,
instability_scores via component_breakdown._synthetic, and all of them via
the dedicated "Synthetic Generator" source row.

Usage: python scripts/generate_synthetic_data.py [--events N] [--stories N] [--js-only]
"""
import argparse
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

REPO_ROOT = Path(__file__).resolve().parent.parent
JS_OUT = REPO_ROOT / "frontend" / "src" / "data" / "syntheticDataset.js"

# ~40 real-world population centers: (name, lat, lon)
POPULATION_CENTERS = [
    ("Tokyo", 35.68, 139.69), ("Delhi", 28.61, 77.21), ("Shanghai", 31.23, 121.47),
    ("São Paulo", -23.55, -46.63), ("Mexico City", 19.43, -99.13), ("Cairo", 30.04, 31.24),
    ("Mumbai", 19.08, 72.88), ("Beijing", 39.90, 116.41), ("Dhaka", 23.81, 90.41),
    ("Osaka", 34.69, 135.50), ("New York", 40.71, -74.01), ("Karachi", 24.86, 67.01),
    ("Buenos Aires", -34.60, -58.38), ("Istanbul", 41.01, 28.98), ("Kolkata", 22.57, 88.36),
    ("Lagos", 6.52, 3.38), ("London", 51.51, -0.13), ("Los Angeles", 34.05, -118.24),
    ("Manila", 14.60, 120.98), ("Rio de Janeiro", -22.91, -43.17), ("Tianjin", 39.34, 117.36),
    ("Kinshasa", -4.44, 15.27), ("Paris", 48.86, 2.35), ("Shenzhen", 22.54, 114.06),
    ("Jakarta", -6.21, 106.85), ("Bangalore", 12.97, 77.59), ("Moscow", 55.76, 37.62),
    ("Chennai", 13.08, 80.27), ("Lima", -12.05, -77.04), ("Bangkok", 13.76, 100.50),
    ("Seoul", 37.57, 126.98), ("Nagoya", 35.18, 136.91), ("Hyderabad", 17.39, 78.49),
    ("Tehran", 35.69, 51.39), ("Chicago", 41.88, -87.63), ("Chengdu", 30.57, 104.07),
    ("Nairobi", -1.29, 36.82), ("Ho Chi Minh City", 10.82, 106.63), ("Berlin", 52.52, 13.41),
    ("Sydney", -33.87, 151.21),
]

CATEGORIES = ["geopolitics", "finance", "disaster", "conflict", "other"]

TITLE_TEMPLATES = {
    "geopolitics": ["Election results contested in {place}", "Diplomatic summit convened in {place}",
                    "New sanctions announced affecting {place}", "Policy shift announced in {place}"],
    "finance": ["Market volatility spikes in {place} exchange", "Currency pressure builds in {place}",
                "Port congestion reported at {place} shipping hub", "Central bank intervention in {place}"],
    "disaster": ["Flooding reported near {place}", "Seismic activity recorded near {place}",
                 "Severe storm system approaching {place}", "Wildfire risk elevated around {place}"],
    "conflict": ["Border tensions escalate near {place}", "Protest movement grows in {place}",
                 "Security incident reported in {place}", "Ceasefire talks stall near {place}"],
    "other": ["Infrastructure disruption in {place}", "Public health advisory issued for {place}",
              "Communications outage affecting {place}", "Supply chain alert issued for {place}"],
}


def generate(events_count: int, stories_count: int, seed: int = 20260703) -> dict:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)

    events = []
    for _ in range(events_count):
        place, lat, lon = rng.choice(POPULATION_CENTERS)
        lat += rng.uniform(-2.5, 2.5)
        lon += rng.uniform(-2.5, 2.5)
        category = rng.choice(CATEGORIES)
        title = rng.choice(TITLE_TEMPLATES[category]).format(place=place)
        occurred = now - timedelta(hours=rng.uniform(0, 96))
        events.append({
            "id": str(uuid.uuid4()),
            "title": title,
            "description": title.lower(),
            "location": [round(lon, 4), round(lat, 4)],
            "location_name": place,
            "category": category,
            "severity": rng.randint(1, 5),
            "occurred_at": occurred.isoformat(),
            "source_name": "Synthetic Generator",
            "source_leaning": "n/a",
            "outbound_link": "https://example.com/synthetic",
            "_synthetic": True,
        })

    stories = []
    story_members = []
    event_pool = list(range(len(events)))
    rng.shuffle(event_pool)
    cursor = 0
    for i in range(stories_count):
        size = rng.randint(2, 6)
        if cursor + size > len(event_pool):
            cursor = 0
            rng.shuffle(event_pool)
        member_idx = event_pool[cursor:cursor + size]
        cursor += size

        member_events = [events[j] for j in member_idx]
        first_seen = min(e["occurred_at"] for e in member_events)
        last_updated = max(e["occurred_at"] for e in member_events)
        lead = member_events[0]

        story_id = str(uuid.uuid4())
        stories.append({
            "id": story_id,
            "headline": f"[SYNTHETIC] {lead['title']}",
            "summary": f"[SYNTHETIC PLACEHOLDER] Cluster of {size} correlated events centered on "
                       f"{lead['location_name']}. This summary is generated placeholder text, not real analysis.",
            "causal_narrative": {
                "_synthetic": True,
                "cause": f"[SYNTHETIC PLACEHOLDER] {lead['title']}",
                "affected": sorted({e["location_name"] for e in member_events}),
                "consequences": ["[SYNTHETIC PLACEHOLDER] downstream effect A",
                                 "[SYNTHETIC PLACEHOLDER] downstream effect B"],
                "confidence": rng.choice(["high", "medium", "low"]),
            },
            "confidence": rng.choice(["high", "medium", "low"]),
            "first_seen_at": first_seen,
            "last_updated_at": last_updated,
            "member_count": size,
            "source_count": rng.randint(2, 4),
            "categories": sorted({e["category"] for e in member_events}),
            "member_event_ids": [e["id"] for e in member_events],
            "_synthetic": True,
        })
        for e in member_events:
            story_members.append({
                "story_id": story_id,
                "event_id": e["id"],
                "fact_id": None,
                "linked_via": rng.choice(["same_window", "same_window", "historical_chain"]),
                "linked_at": last_updated,
            })

    instability = []
    for h in range(7 * 24, -1, -1):
        ts = now - timedelta(hours=h)
        base = 42 + 14 * rng.random() + 8 * (1 if h % 24 < 6 else 0)
        instability.append({
            "score": round(min(100.0, max(0.0, base + rng.uniform(-6, 6))), 2),
            "computed_at": ts.isoformat(),
            "component_breakdown": {"_synthetic": True, "volume": round(rng.uniform(0, 40), 2),
                                     "severity": round(rng.uniform(0, 40), 2),
                                     "spread": round(rng.uniform(0, 20), 2)},
        })

    return {"events": events, "stories": stories, "story_members": story_members,
            "instability_scores": instability}


def write_js(dataset: dict) -> None:
    JS_OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(dataset, indent=1)
    JS_OUT.write_text(
        "// GENERATED by scripts/generate_synthetic_data.py (Section 12) — do not edit by hand.\n"
        "// Mirrors the synthetic rows written to the database; purged in Phase 5.\n"
        f"const syntheticDataset = {body};\n\nexport default syntheticDataset;\n"
    )
    print(f"wrote {JS_OUT} ({JS_OUT.stat().st_size // 1024} KB)")


def write_db(dataset: dict) -> None:
    from datetime import datetime as dt

    from app.db.models import Event, InstabilityScore, RawItem, Source, Story, StoryMember
    from app.db.session import get_session

    def parse(ts):
        return dt.fromisoformat(ts)

    with get_session() as session:
        synth_source = session.query(Source).filter_by(name="Synthetic Generator").first()
        if synth_source is None:
            synth_source = Source(name="Synthetic Generator", type="rss",
                                  url="synthetic://generate_synthetic_data", leaning="n/a",
                                  poll_interval_seconds=86400, health_status="down",
                                  last_error="synthetic placeholder source — never fetched")
            session.add(synth_source)
            session.flush()

        for e in dataset["events"]:
            raw = RawItem(source_id=synth_source.id,
                          raw_content={"_synthetic": True, "title": e["title"],
                                       "link": e["outbound_link"]},
                          fetched_at=parse(e["occurred_at"]), processed=True)
            session.add(raw)
            session.flush()
            lon, lat = e["location"]
            session.add(Event(id=e["id"], raw_item_id=raw.id, title=e["title"],
                              description=e["description"], location=f"POINT({lon} {lat})",
                              location_name=e["location_name"], category=e["category"],
                              severity=e["severity"], occurred_at=parse(e["occurred_at"])))

        for s in dataset["stories"]:
            session.add(Story(id=s["id"], headline=s["headline"], summary=s["summary"],
                              causal_narrative=s["causal_narrative"], confidence=s["confidence"],
                              first_seen_at=parse(s["first_seen_at"]),
                              last_updated_at=parse(s["last_updated_at"])))
        session.flush()

        for m in dataset["story_members"]:
            session.add(StoryMember(story_id=m["story_id"], event_id=m["event_id"], fact_id=None,
                                    linked_via=m["linked_via"], linked_at=parse(m["linked_at"])))

        for i in dataset["instability_scores"]:
            session.add(InstabilityScore(score=i["score"], computed_at=parse(i["computed_at"]),
                                         component_breakdown=i["component_breakdown"]))

    print(f"wrote {len(dataset['events'])} events, {len(dataset['stories'])} stories, "
          f"{len(dataset['story_members'])} story_members, "
          f"{len(dataset['instability_scores'])} instability_scores to the database")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=300)
    parser.add_argument("--stories", type=int, default=60)
    parser.add_argument("--js-only", action="store_true",
                        help="only regenerate frontend/src/data/syntheticDataset.js, skip DB writes")
    args = parser.parse_args()

    dataset = generate(args.events, args.stories)
    write_js(dataset)
    if not args.js_only:
        write_db(dataset)


if __name__ == "__main__":
    main()
