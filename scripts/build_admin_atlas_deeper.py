#!/usr/bin/env python3
"""V8.1/V8.2 — the deeper administrative tiers (ADM2, ADM3, …).

Generalized successor to the ADM2-only builder: takes a list of (iso3, level)
TASKS and appends each geoBoundaries level to the atlas, parent-linking every
unit to the SMALLEST existing unit that contains its centroid — so ADM2 links to
the ADM1 province it sits in, and ADM3 links to the ADM2 district loaded earlier
in the SAME run. Variable depth (Q1): where a country has no real ADM2 in a
region, its ADM3 simply links up to the ADM1 province.

Reads the vendored ADM1 base (Natural Earth) and rebuilds ALL deeper tiers from
TASKS, in task order, so uids stay STABLE as long as existing tasks keep their
place (append new tasks at the END). ADM1 stays byte-verbatim. Emits:

  frontend/src/data/adminBoundaries.js   → ADMIN1_ENC (verbatim) + ADMIN2_ENC + ADMIN3_ENC
  backend/app/geopolitics/admin_atlas.py → combined registry; unit_at() = smallest

geoBoundaries (gbOpen, CC-BY) is git-LFS, fetched from the media host. Pure
stdlib. Build-time only; outputs committed. Usage: python scripts/build_admin_atlas_deeper.py
"""
import base64
import gzip
import json
import math
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_admin_atlas import (REPO, SIMPLIFY_TOL, MIN_RING_PTS, _dp, _rings_of,
                               _bbox, _centroid, encode_ring, _DECODER_SRC)

DEEP_TOL = max(SIMPLIFY_TOL, 0.025)
_EARTH_R_KM = 6371.0088


def _area_km2(rings_flat):
    """V8.5 — real (approximate) surface area of a unit from its own polygon,
    summed over all rings via the spherical-excess line-integral. Areas are
    computed from the SIMPLIFIED geometry the atlas stores, so they're honest
    approximations (a few % off the exact figure); good enough to show + to
    derive density. Holes are rare in admin units, so all rings are additive."""
    total = 0.0
    for flat in rings_flat:
        n = len(flat) // 2
        if n < 3:
            continue
        s = 0.0
        for i in range(n):
            lon1 = math.radians(flat[2 * i]); lat1 = math.radians(flat[2 * i + 1])
            j = (i + 1) % n
            lon2 = math.radians(flat[2 * j]); lat2 = math.radians(flat[2 * j + 1])
            s += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
        total += abs(s * _EARTH_R_KM * _EARTH_R_KM / 2.0)
    return int(round(total))
GB = ("https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/"
      "releaseData/gbOpen/{iso3}/ADM{lvl}/geoBoundaries-{iso3}-ADM{lvl}_simplified.geojson")

# (iso3, level) in the order they are appended. KEEP existing entries in place
# (uids are positional so events/seeded rows stay stable); add new tiers at the
# END. Only add ADM2 where Natural Earth's ADM1 is the country's TOP subdivision
# (US states, German Länder, Chinese provinces …) so the tier nests cleanly —
# NOT France/Italy/Spain, whose NE ADM1 is already the 2nd level.
TASKS = [
    ("USA", 2),   # US counties            (parent: state)
    ("DEU", 2),   # German Regierungsbezirke (parent: Land)
    ("DEU", 3),   # German Kreise          (parent: Regierungsbezirk, else Land)
    # v8.4 — broaden the district tier to a global, newsworthy spread.
    # (China is deliberately excluded: geoBoundaries' CHN ADM2 and ADM3 are BOTH
    # county-level with different romanizations, so they'd duplicate — no clean
    # prefecture→county chain to nest.)
    ("UKR", 2),   # Ukrainian raions       (parent: oblast)
    ("IND", 2),   # Indian districts       (parent: state)
    ("JPN", 2),   # Japanese municipalities(parent: prefecture)
    ("POL", 2),   # Polish powiaty         (parent: voivodeship)
    ("POL", 3),   # Polish gminy           (parent: powiat) — 2nd clean 3-level showcase
    ("TUR", 2),   # Turkish districts      (parent: province)
    ("CAN", 2),   # Canadian census div.   (parent: province)
    ("AUS", 2),   # Australian LGAs        (parent: state)
    # v8.5 — a second global broadening pass across four more continents. Each is
    # a clean nest: the country's Natural Earth ADM1 IS its top subdivision
    # (states/provinces/governorates), so geoBoundaries ADM2 slots one level below.
    # (France/Italy/Spain stay OUT — their NE ADM1 is already the 2nd level.)
    ("BRA", 2),   # Brazilian municipalities (parent: state)
    ("MEX", 2),   # Mexican municipios     (parent: state)
    ("NGA", 2),   # Nigerian LGAs          (parent: state)
    ("IDN", 2),   # Indonesian regencies   (parent: province)
    ("ARG", 2),   # Argentine departments  (parent: province)
    ("ZAF", 2),   # South African districts(parent: province)
    ("EGY", 2),   # Egyptian markaz        (parent: governorate)
    # v8.6 — resolve three earlier exclusions.
    # China: add ONLY ADM2 (counties). The v8.4 note's duplication worry was
    # between gB CHN ADM2 and ADM3 (both county-level); adding a SINGLE tier under
    # the provinces is a clean, if flatter, nest (no prefecture layer — variable
    # depth, Q1). Provinces (NE ADM1) → counties (gB ADM2).
    ("CHN", 2),   # Chinese counties       (parent: province — no prefecture tier)
    # France & Spain: their NE ADM1 IS the 2nd level (departments / provincias),
    # so the clean DEEPER tier is gB ADM3 (arrondissements / municipios), which
    # centroid-links straight to those NE units. (Italy stays OUT — its gB ADM3 is
    # only ~107 = its provinces again, which would duplicate NE, not nest.)
    ("FRA", 3),   # French arrondissements (parent: department)
    ("ESP", 3),   # Spanish municipios     (parent: province)
]
LEVEL_TYPE = {2: "District", 3: "Sub-district"}
# nicer, locally-correct unit-type labels per (iso3, level); falls back to LEVEL_TYPE
TYPE_OVERRIDE = {
    ("USA", 2): "County", ("DEU", 2): "Regierungsbezirk", ("DEU", 3): "Kreis",
    ("UKR", 2): "Raion",
    ("IND", 2): "District", ("JPN", 2): "Municipality",
    ("POL", 2): "Powiat", ("POL", 3): "Gmina",
    ("TUR", 2): "District", ("CAN", 2): "Census Division", ("AUS", 2): "LGA",
    ("BRA", 2): "Município", ("MEX", 2): "Municipio", ("NGA", 2): "LGA",
    ("IDN", 2): "Regency", ("ARG", 2): "Department", ("ZAF", 2): "District",
    ("EGY", 2): "Markaz",
    ("CHN", 2): "County", ("FRA", 3): "Arrondissement", ("ESP", 3): "Municipio",
}


def fetch(iso3, lvl):
    cache = REPO / "scripts" / f"_gb_{iso3.lower()}_adm{lvl}.geojson"
    if cache.exists():
        return json.loads(cache.read_text())
    print(f"fetching geoBoundaries {iso3} ADM{lvl} …", file=sys.stderr)
    with urllib.request.urlopen(GB.format(iso3=iso3, lvl=lvl), timeout=120) as r:
        data = r.read()
    cache.write_bytes(data)
    return json.loads(data)


def main():
    sys.path.insert(0, str(REPO / "backend"))
    from app.geopolitics import admin_atlas
    from app.geopolitics.admin_atlas import _decode_ring, _ring_contains
    data = admin_atlas._load()

    # base = ADM1 only (deeper tiers are fully regenerated from TASKS)
    adm1_units = [u for u in data["units"] if u.get("level", 1) == 1]
    adm1_uids = {u["uid"] for u in adm1_units}
    adm1_enc = [e for e in data["enc"] if e["i"] in adm1_uids]

    # v8.5 — real per-unit area on the ADM1 tier too, computed from each unit's
    # OWN (decoded) polygon so every unit in the atlas carries an area figure.
    _area_by_uid = {}
    for e in adm1_enc:
        # admin_atlas._decode_ring yields (lon,lat) tuples; flatten to the
        # [lon,lat,…] shape _area_km2 expects.
        flat_rings = [[c for pt in _decode_ring(r) for c in pt] for r in e["r"]]
        _area_by_uid[e["i"]] = _area_km2(flat_rings)
    for u in adm1_units:
        u["area_km2"] = _area_by_uid.get(u["uid"], 0)

    # a growing point-in-polygon resolver (smallest containing unit), seeded
    # with ADM1 and extended after each task so deeper tiers link to shallower.
    resolver = []  # (uid, bbox, area, [decoded rings]), name for path
    name_by_uid = {}
    for e in adm1_enc:
        bb = e["b"]
        area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        resolver.append((e["i"], bb, area, [_decode_ring(r) for r in e["r"]]))
    for u in adm1_units:
        name_by_uid[u["uid"]] = u["name"]

    def smallest_at(lat, lon):
        best, best_area = None, 1e18
        for uid, bb, area, rings in resolver:
            if lon < bb[0] or lon > bb[2] or lat < bb[1] or lat > bb[3]:
                continue
            for ring in rings:
                if _ring_contains(ring, lat, lon):
                    if area < best_area:
                        best_area, best = area, uid
                    break
        return best

    next_id = max(adm1_uids) + 1
    deeper_units, deeper_enc = [], []

    for iso3, lvl in TASKS:
        try:
            gj = fetch(iso3, lvl)
        except Exception as e:  # noqa: BLE001 — a missing country must not abort the build
            print(f"{iso3} ADM{lvl}: SKIPPED ({type(e).__name__}: {e})", file=sys.stderr)
            continue
        feats = gj["features"]
        added, linked, new_res = 0, 0, []
        for f in feats:
            p = f.get("properties", {})
            geom = f.get("geometry")
            name = (p.get("shapeName") or "").strip()
            if not geom or not name:
                continue
            rings_flat = []
            for ring in _rings_of(geom):
                pts = [(c[0], c[1]) for c in ring if len(c) >= 2]
                if len(pts) < MIN_RING_PTS:
                    continue
                simp = _dp(pts, DEEP_TOL)
                if len(simp) < 3:
                    continue
                flat = []
                for x, y in simp:
                    flat.append(x); flat.append(y)
                rings_flat.append(flat)
            if not rings_flat:
                continue
            bb = _bbox(rings_flat)
            cx, cy = _centroid(rings_flat)
            parent = smallest_at(cy, cx)
            if parent:
                linked += 1
            # path: country / …ancestors… / name (walk the resolver's names)
            parent_name = name_by_uid.get(parent)
            path = "/".join(x for x in (iso3, parent_name, name) if x)
            uid = next_id
            next_id += 1
            decoded = [_decode_ring(encode_ring(r)) for r in rings_flat]  # match stored precision
            deeper_enc.append({"i": uid, "n": name, "c": iso3, "b": bb,
                               "r": [encode_ring(r) for r in rings_flat]})
            deeper_units.append({
                "uid": uid, "name": name, "name_local": None, "country": iso3,
                "iso2": (p.get("shapeISO") or "").strip(), "level": lvl,
                "parent": parent, "path": path,
                "clat": cy, "clon": cx, "bbox": bb,
                "area_km2": _area_km2(rings_flat),   # v8.5 — real area from the polygon
                "type": TYPE_OVERRIDE.get((iso3, lvl), LEVEL_TYPE.get(lvl, f"ADM{lvl}")),
            })
            name_by_uid[uid] = name
            area = (bb[2] - bb[0]) * (bb[3] - bb[1])
            new_res.append((uid, bb, area, decoded))
            added += 1
        # add this task's units so the NEXT (deeper) task can link to them
        resolver.extend(new_res)
        print(f"{iso3} ADM{lvl}: {added} units ({linked} parent-linked)", file=sys.stderr)

    # ---- frontend artifact: ADMIN1_ENC verbatim + per-level exports ----------
    by_level = {}
    for u, e in zip(deeper_units, deeper_enc):
        by_level.setdefault(u["level"], []).append(e)
    fe = REPO / "frontend" / "src" / "data" / "adminBoundaries.js"
    with open(fe, "w", encoding="utf-8") as fh:
        fh.write("// GENERATED by scripts/build_admin_atlas*.py — DO NOT EDIT.\n")
        fh.write("// V8 — ADM1 (Natural Earth) + V8.1/V8.2 deeper tiers (geoBoundaries),\n")
        fh.write("// polyline-encoded. ADMIN{N}_ENC = the units at admin level N.\n")
        fh.write("export const ADMIN1_ENC = ")
        json.dump(adm1_enc, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write(";\n")
        for lvl in (2, 3):
            fh.write(f"export const ADMIN{lvl}_ENC = ")
            json.dump(by_level.get(lvl, []), fh, separators=(",", ":"), ensure_ascii=False)
            fh.write(";\n")
    print(f"wrote {fe} ({fe.stat().st_size // 1024} KB; ADM1 {len(adm1_enc)}, "
          f"ADM2 {len(by_level.get(2, []))}, ADM3 {len(by_level.get(3, []))})", file=sys.stderr)

    # ---- backend artifact: combined; unit_at → smallest -----------------------
    all_units = adm1_units + deeper_units
    all_enc = adm1_enc + deeper_enc
    be = REPO / "backend" / "app" / "geopolitics" / "admin_atlas.py"
    blob = gzip.compress(json.dumps({"units": all_units, "enc": all_enc},
                                    separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    b64 = base64.b64encode(blob).decode("ascii")
    with open(be, "w", encoding="utf-8") as fh:
        fh.write('"""GENERATED by scripts/build_admin_atlas*.py — DO NOT EDIT.\n\n')
        fh.write("V8/V8.1/V8.2 — the admin-unit registry (ADM1 + deeper tiers) + encoded\n")
        fh.write("rings + a pure-python decoder. unit_at() returns the SMALLEST containing\n")
        fh.write('unit. Data gzip+base64 embedded to keep the module small.\n"""\n')
        fh.write("import base64, gzip, json\n\n")
        fh.write("_BLOB = (\n")
        for i in range(0, len(b64), 100):
            fh.write("    " + json.dumps(b64[i:i + 100]) + "\n")
        fh.write(")\n\n")
        fh.write("_DATA = None\n\n")
        fh.write("def _load():\n")
        fh.write("    global _DATA\n")
        fh.write("    if _DATA is None:\n")
        fh.write("        _DATA = json.loads(gzip.decompress(base64.b64decode(_BLOB)))\n")
        fh.write("    return _DATA\n\n")
        fh.write("def units():\n    return _load()['units']\n\n")
        fh.write(_DECODER_SRC)
    print(f"wrote {be} ({be.stat().st_size // 1024} KB, {len(all_units)} units)",
          file=sys.stderr)
    print("done.", file=sys.stderr)


if __name__ == "__main__":
    main()
