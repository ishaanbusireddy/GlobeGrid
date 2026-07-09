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
    # v8.7 — a big global broadening pass: every entry below was verified to have
    # geoBoundaries ADM2 count > its Natural Earth ADM1 count (so it nests, never
    # duplicates). Skipped where gB ADM2 == NE ADM1 (Algeria, Greece, Belgium,
    # Philippines — those would duplicate).
    ("COL", 2),   # Colombian municipios   (parent: department)
    ("VEN", 2),   # Venezuelan municipios  (parent: state)
    ("PER", 2),   # Peruvian provinces     (parent: region)
    ("CHL", 2),   # Chilean provinces      (parent: region)
    ("IRN", 2),   # Iranian counties       (parent: province)
    ("IRQ", 2),   # Iraqi districts        (parent: governorate)
    ("SAU", 2),   # Saudi governorates     (parent: region)
    ("PAK", 2),   # Pakistani districts    (parent: province)
    ("BGD", 2),   # Bangladeshi districts  (parent: division)
    ("KAZ", 2),   # Kazakh districts       (parent: region)
    ("MYS", 2),   # Malaysian districts    (parent: state)
    ("VNM", 2),   # Vietnamese districts   (parent: province)
    ("THA", 2),   # Thai districts (amphoe)(parent: province)
    ("ETH", 2),   # Ethiopian zones        (parent: region)
    ("MAR", 2),   # Moroccan provinces     (parent: region)
    ("SWE", 2),   # Swedish municipalities (parent: county)
    ("NOR", 2),   # Norwegian municipalities(parent: county)
    ("PRT", 2),   # Portuguese municipios  (parent: district)
    ("NLD", 2),   # Dutch gemeenten        (parent: province)
    ("CZE", 2),   # Czech districts        (parent: region)
    ("ROU", 2),   # Romanian communes      (parent: county)
    # Italy: its NE ADM1 IS the provinces, and gB ADM3 duplicates them — but gB
    # ADM4 (7,901 comuni) is a genuine deeper tier. Fetch ADM4, STORE as level 3
    # (the comune is the same conceptual depth as a Spanish municipio), via the
    # GB_LEVEL override below, so it renders on the existing ADM3 line layer.
    ("ITA", 3),   # Italian comuni         (parent: province) — fetched from gB ADM4
    # v8.8 — a fifth broadening pass: ~40 more countries, every one pre-verified
    # (gB ADM2 > NE ADM1, so a genuine deeper tier). Africa, MENA, Latin America,
    # the Balkans, the Alpine/Nordic states, and more of Asia.
    ("AGO", 2), ("MOZ", 2), ("TZA", 2), ("UGA", 2), ("GHA", 2), ("SDN", 2),
    ("ZWE", 2), ("ZMB", 2), ("CMR", 2), ("CIV", 2), ("SEN", 2), ("MLI", 2),
    ("MDG", 2), ("UZB", 2), ("AFG", 2), ("GEO", 2), ("SYR", 2),
    ("JOR", 2), ("LBN", 2), ("YEM", 2), ("OMN", 2), ("ECU", 2), ("BOL", 2),
    ("PRY", 2), ("URY", 2), ("GTM", 2), ("CUB", 2), ("DOM", 2), ("BGR", 2),
    ("SRB", 2), ("HRV", 2), ("AUT", 2), ("CHE", 2), ("FIN", 2), ("DNK", 2),
    ("IRL", 2), ("SVK", 2), ("NPL", 2), ("MMR", 2), ("KHM", 2), ("NZL", 2),
    # v8.9 — a sixth broadening pass. Each is guarded at build time by the new
    # nesting check (auto-skips any that geoBoundaries doesn't actually split
    # below the province layer), so the list can be generous. East/Central/South
    # Africa, the Maghreb, Central America, the Caucasus/Central Asia, the
    # Baltics, and more of East Asia + the Middle East.
    ("KEN", 2), ("TZA", 3), ("MWI", 2), ("RWA", 2), ("BEN", 2), ("TGO", 2),
    ("GAB", 2), ("COD", 2), ("NAM", 2), ("BWA", 2), ("TCD", 2), ("NER", 2),
    ("TUN", 2), ("LBY", 2), ("LSO", 2), ("SSD", 2),
    ("HND", 2), ("NIC", 2), ("CRI", 2), ("PAN", 2), ("SLV", 2),
    ("MNG", 2), ("KOR", 2), ("LKA", 2), ("LAO", 2),
    ("LTU", 2), ("EST", 2), ("HUN", 2), ("BLR", 2),
    ("ARM", 2), ("KGZ", 2), ("TJK", 2), ("ISR", 2),
]
LEVEL_TYPE = {2: "District", 3: "Sub-district"}
# fetch a DIFFERENT geoBoundaries level than the stored level. Italy's comuni are
# gB ADM4 but conceptually a level-3 unit (municipality under province).
GB_LEVEL = {("ITA", 3): 4}
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
    ("COL", 2): "Municipio", ("VEN", 2): "Municipio", ("PER", 2): "Province",
    ("CHL", 2): "Province", ("IRN", 2): "County", ("IRQ", 2): "District",
    ("SAU", 2): "Governorate", ("PAK", 2): "District", ("BGD", 2): "District",
    ("KAZ", 2): "District", ("MYS", 2): "District", ("VNM", 2): "District",
    ("THA", 2): "District", ("ETH", 2): "Zone", ("MAR", 2): "Province",
    ("SWE", 2): "Municipality", ("NOR", 2): "Municipality", ("PRT", 2): "Municipio",
    ("NLD", 2): "Gemeente", ("CZE", 2): "District", ("ROU", 2): "Commune",
    ("ITA", 3): "Comune",
    # v8.8 — locally-correct labels for the fifth pass
    ("AGO", 2): "Municipality", ("MOZ", 2): "District", ("TZA", 2): "District",
    ("UGA", 2): "County", ("GHA", 2): "District", ("SDN", 2): "District",
    ("ZWE", 2): "District", ("ZMB", 2): "District", ("CMR", 2): "Department",
    ("CIV", 2): "Department", ("SEN", 2): "Department", ("MLI", 2): "Cercle",
    ("MDG", 2): "District", ("UZB", 2): "District", ("AFG", 2): "District",
    ("GEO", 2): "Municipality", ("SYR", 2): "District", ("JOR", 2): "District",
    ("LBN", 2): "District", ("YEM", 2): "District", ("OMN", 2): "Wilayat",
    ("ECU", 2): "Canton", ("BOL", 2): "Province", ("PRY", 2): "District",
    ("URY", 2): "Municipality", ("GTM", 2): "Municipio", ("CUB", 2): "Municipio",
    ("DOM", 2): "Municipio", ("BGR", 2): "Municipality", ("SRB", 2): "Municipality",
    ("HRV", 2): "Municipality", ("AUT", 2): "District", ("CHE", 2): "District",
    ("FIN", 2): "Municipality", ("DNK", 2): "Municipality", ("IRL", 2): "County",
    ("SVK", 2): "District", ("NPL", 2): "District", ("MMR", 2): "District",
    ("KHM", 2): "District", ("NZL", 2): "District",
    # v8.9 — sixth pass labels
    ("KEN", 2): "Sub-county", ("TZA", 3): "Ward", ("MWI", 2): "District",
    ("RWA", 2): "District", ("BEN", 2): "Commune", ("TGO", 2): "Prefecture",
    ("GAB", 2): "Department", ("COD", 2): "Territory", ("NAM", 2): "Constituency",
    ("BWA", 2): "District", ("TCD", 2): "Department", ("NER", 2): "Department",
    ("TUN", 2): "Delegation", ("LBY", 2): "District", ("LSO", 2): "Community Council",
    ("SSD", 2): "County", ("HND", 2): "Municipio", ("NIC", 2): "Municipio",
    ("CRI", 2): "Canton", ("PAN", 2): "District", ("SLV", 2): "Municipio",
    ("MNG", 2): "Sum", ("KOR", 2): "Municipality", ("LKA", 2): "DS Division",
    ("LAO", 2): "District", ("LTU", 2): "Municipality", ("EST", 2): "Municipality",
    ("HUN", 2): "District", ("BLR", 2): "District", ("ARM", 2): "Community",
    ("KGZ", 2): "District", ("TJK", 2): "District", ("ISR", 2): "Subdistrict",
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

    # v8.9 — how many ADM1 (province/state) units each country already has, so a
    # new task can be auto-rejected when geoBoundaries doesn't actually go deeper.
    adm1_count_by_iso = {}
    for u in adm1_units:
        adm1_count_by_iso[u["country"]] = adm1_count_by_iso.get(u["country"], 0) + 1

    for iso3, lvl in TASKS:
        fetch_lvl = GB_LEVEL.get((iso3, lvl), lvl)   # v8.7 — Italy: fetch ADM4, store as 3
        try:
            gj = fetch(iso3, fetch_lvl)
        except Exception as e:  # noqa: BLE001 — a missing country must not abort the build
            print(f"{iso3} ADM{lvl}: SKIPPED ({type(e).__name__}: {e})", file=sys.stderr)
            continue
        feats = gj["features"]
        # v8.9 — nesting guard: a genuine DEEPER tier has more units than the
        # country's ADM1 layer. If geoBoundaries returns no more than the NE ADM1
        # count, it's the SAME level (a duplicate that would double-plot the
        # province borders, not nest) — skip it. Catches the Algeria/Greece/
        # Belgium/Philippines class and any newly-added country that doesn't nest.
        _named = sum(1 for f in feats
                     if (f.get("properties", {}).get("shapeName") or "").strip())
        _base = adm1_count_by_iso.get(iso3, 0)
        if _base and _named <= _base:
            print(f"{iso3} ADM{lvl}: SKIPPED ({_named} units ≤ {_base} ADM1 — "
                  f"not a deeper tier)", file=sys.stderr)
            continue
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
