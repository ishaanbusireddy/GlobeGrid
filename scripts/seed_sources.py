"""Seeds the sources table (Section 6.1) with the locked source list from
Section 4. Run once after migrations: `python scripts/seed_sources.py`.

GDELT Cloud is seeded with a placeholder URL and health_status="down" since
its exact REST endpoint isn't published in the build manual (see the NOTE in
app/ingestion/sources/gdelt.py) — update its url once you have the real
endpoint from an active GDELT Cloud account, then it will be picked up on
the next scheduler restart.

Alpha Vantage and Reddit rows use one representative endpoint each (the
manual specifies the source, not specific symbols/subreddits) — edit these
rows to track whatever symbols/subreddits you actually want correlated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config import get_settings  # noqa: E402
from app.db.models import Source  # noqa: E402
from app.db.session import get_session  # noqa: E402

INTERVALS = get_settings().ingestion_intervals_seconds()

SOURCES = [
    # --- 4.1 News (RSS) ---
    dict(name="BBC World", type="rss", url="https://feeds.bbci.co.uk/news/world/rss.xml",
         leaning="center", poll_interval_seconds=INTERVALS["rss"]),
    dict(name="Al Jazeera", type="rss", url="https://www.aljazeera.com/xml/rss/all.xml",
         leaning="center", poll_interval_seconds=INTERVALS["rss"]),
    dict(name="NYT World", type="rss", url="https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
         leaning="left", poll_interval_seconds=INTERVALS["rss"]),
    dict(name="Washington Post", type="rss", url="https://feeds.washingtonpost.com/rss/national",
         leaning="left", poll_interval_seconds=INTERVALS["rss"]),
    dict(name="CNN World", type="rss", url="http://rss.cnn.com/rss/edition_world.rss",
         leaning="left", poll_interval_seconds=INTERVALS["rss"]),
    dict(name="NPR", type="rss", url="https://feeds.npr.org/1001/rss.xml",
         leaning="left", poll_interval_seconds=INTERVALS["rss"]),
    dict(name="Reuters (via Google News)", type="rss",
         url="https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com",
         leaning="center", poll_interval_seconds=INTERVALS["rss"]),

    # --- 4.2 Structured global event data ---
    dict(name="GDELT DOC 2.0", type="gdelt", url="https://api.gdeltproject.org/api/v2/doc/doc",
         leaning="n/a", poll_interval_seconds=INTERVALS["rss"]),
    dict(name="GDELT Cloud", type="gdelt", url="https://REPLACE-WITH-REAL-GDELT-CLOUD-ENDPOINT",
         leaning="n/a", poll_interval_seconds=INTERVALS["gdelt_cloud"], health_status="down"),

    # --- 4.3 Physical world events ---
    dict(name="USGS Earthquakes", type="usgs",
         url="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
         leaning="n/a", poll_interval_seconds=INTERVALS["usgs"]),

    # --- 4.4 Markets ---
    dict(name="Alpha Vantage (SPY intraday)", type="market",
         url="https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=SPY&interval=60min",
         leaning="n/a", poll_interval_seconds=INTERVALS["market"]),

    # --- 4.5 Social ---
    dict(name="Reddit r/worldnews", type="reddit", url="https://oauth.reddit.com/r/worldnews/new",
         leaning="n/a", poll_interval_seconds=INTERVALS["reddit"]),
]


def main() -> None:
    with get_session() as session:
        existing = {s.name for s in session.query(Source).all()}
        created = 0
        for row in SOURCES:
            if row["name"] in existing:
                continue
            row.setdefault("health_status", "ok")
            session.add(Source(**row))
            created += 1
        print(f"Seeded {created} new source(s); {len(existing)} already present.")


if __name__ == "__main__":
    main()
