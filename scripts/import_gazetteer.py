#!/usr/bin/env python3
"""v2 addendum §10 — one-time gazetteer import.

Loads the vendored GeoNames-derived dataset
(backend/data/gazetteer_cities.tsv.gz, cities15000-scale, ~32k places)
into the gazetteer_places / gazetteer_aliases tables. Run automatically at
startup when the table is empty; standalone:

    python scripts/import_gazetteer.py [--force]

Zero-install: the dataset is a flat file shipped in the repo — no runtime
network dependency. Applies gazetteer.min_population_threshold from
config.yaml. Geocoding data © GeoNames, licensed CC BY 4.0
(https://www.geonames.org) — attribution also shown in the app status
panel and README.
"""

import gzip
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import cfg  # noqa: E402
from backend.app.db.models import migrate  # noqa: E402
from backend.app.db.session import query_one, write_tx  # noqa: E402

DATA_FILE = REPO_ROOT / "backend" / "data" / "gazetteer_cities.tsv.gz"


def import_gazetteer(force: bool = False) -> int:
    migrate()
    existing = query_one("SELECT COUNT(*) AS n FROM gazetteer_places")["n"]
    if existing and not force:
        return existing
    if not DATA_FILE.exists():
        print(f"gazetteer dataset missing: {DATA_FILE}", file=sys.stderr)
        return 0
    min_pop = int(cfg("gazetteer", "min_population_threshold"))
    places, aliases = [], []
    with gzip.open(DATA_FILE, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9:
                continue
            gid, name, ascii_name, lat, lon, cc, admin1, pop, alias_str = parts[:9]
            population = int(pop or 0)
            if population < min_pop:
                continue
            places.append((int(gid), name, ascii_name, float(lat), float(lon),
                           cc, admin1, population))
            for alias in filter(None, alias_str.split("|")):
                aliases.append((alias, int(gid)))
    with write_tx() as conn:
        if force:
            conn.execute("DELETE FROM gazetteer_aliases")
            conn.execute("DELETE FROM gazetteer_places")
        conn.executemany(
            "INSERT OR IGNORE INTO gazetteer_places"
            " (id, name, ascii_name, lat, lon, country_code, admin1_code, population)"
            " VALUES (?,?,?,?,?,?,?,?)", places)
        conn.executemany(
            "INSERT OR IGNORE INTO gazetteer_aliases (alias, place_id) VALUES (?,?)",
            aliases)
    print(f"gazetteer imported: {len(places)} places, {len(aliases)} aliases"
          f" (min_population_threshold={min_pop})")
    return len(places)


if __name__ == "__main__":
    import_gazetteer(force="--force" in sys.argv)
