#!/usr/bin/env python3
"""V8.14 — the GADM upgrade pass: China's PREFECTURE tier + a pluggable
post-2022 India district source.

WHY THIS SCRIPT EXISTS (the two verified data-availability limits from
v8.13.6/v8.13.7): geoBoundaries gbOpen carries NO Chinese prefecture layer
(its CHN ADM2 *and* ADM3 are both county-level, and its shapeIDs are gB
hashes, not GB/T-2260 codes, so counties can't be dissolved upward), and its
India ADM2 predates the 2022 Andhra Pradesh district reorganisation. The only
sources that DO carry those tiers — GADM 4.1 and the Indian government /
DataV mirrors — are blocked by the build sandbox's network policy (verified
HTTP 000 against seven hosts in v8.13.7). This script is therefore written to
be RUN BY THE OWNER on an open network; it is pure stdlib, caches every
download beside itself, and re-emits the exact same two committed artifacts
as build_admin_atlas_deeper.py.

What it does, in order:
  1. Loads the CURRENT combined atlas (backend/app/geopolitics/admin_atlas.py,
     i.e. whatever build_admin_atlas_deeper.py last produced).
  2. Fetches GADM 4.1 China ADM2 (the genuine 339-ish prefecture tier:
     prefecture-level cities, autonomous prefectures, leagues) and APPENDS the
     prefectures as level-2 units under their NE ADM1 provinces. All existing
     uids stay byte-stable — new units only ever take fresh uids at the end.
  3. RE-LEVELS the existing geoBoundaries CHN counties from level 2 → level 3
     and RE-PARENTS each to the prefecture containing its centroid (falling
     back to its old province parent where no prefecture matches — variable
     depth, Q1). Their uids DO NOT change, so events referencing them are
     safe; the backend seed's fingerprint-gated reconcile (v8.14) updates
     adm_level/parent_uid/path on an already-seeded DB automatically.
  4. Optionally (--india-adm2 URL_OR_PATH) REPLACES India's district tier with
     a post-2022 source (any GeoJSON FeatureCollection of districts). This is
     the one operation that renumbers uids (India's old district uids are
     retired and fresh uids appended) — the same honest limitation documented
     since v8.12. Skipped entirely unless the flag is passed.
  5. Re-emits frontend/src/data/adminBoundaries.js and
     backend/app/geopolitics/admin_atlas.py.

GADM licence note: GADM data is freely available for academic and
non-commercial use; redistribution is restricted, which is a second reason
the fetch happens on the owner's machine rather than being vendored here.

Usage (owner's machine, open network):
    python scripts/build_admin_atlas_gadm.py
    python scripts/build_admin_atlas_gadm.py --india-adm2 https://…/india_districts_2023.geojson
    python scripts/build_admin_atlas_gadm.py --india-adm2 C:\\path\\to\\districts.json
"""
import argparse
import base64
import gzip
import json
import sys
import urllib.request
import zipfile
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_admin_atlas import (REPO, MIN_RING_PTS, _dp, _rings_of, _bbox,
                               _centroid, encode_ring, _DECODER_SRC)
from build_admin_atlas_deeper import DEEP_TOL, _area_km2

GADM_JSON = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{iso3}_{lvl}.json"
GADM_ZIP = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{iso3}_{lvl}.json.zip"


def _fetch_gadm(iso3, lvl):
    """Fetch a GADM 4.1 GeoJSON level, caching beside the script. Tries the
    plain .json first, then the .json.zip (GADM serves some levels only
    zipped)."""
    cache = REPO / "scripts" / f"_gadm41_{iso3.lower()}_{lvl}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    last = None
    for url in (GADM_JSON.format(iso3=iso3, lvl=lvl),
                GADM_ZIP.format(iso3=iso3, lvl=lvl)):
        print(f"fetching {url} …", file=sys.stderr)
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                data = r.read()
            if url.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    inner = [n for n in zf.namelist() if n.endswith(".json")]
                    data = zf.read(inner[0])
            cache.write_bytes(data)
            return json.loads(data.decode("utf-8"))
        except Exception as e:  # noqa: BLE001 — try the next URL form
            last = e
            print(f"  … failed ({type(e).__name__}: {e})", file=sys.stderr)
    raise SystemExit(f"could not fetch GADM {iso3} level {lvl}: {last}\n"
                     "(This host must be reachable — run on an open network, "
                     "not the build sandbox.)")


def _load_geojson(url_or_path):
    p = Path(url_or_path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    with urllib.request.urlopen(url_or_path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def _simplify(geom):
    """geometry → list of flat [lon,lat,…] rings at the atlas's DEEP_TOL."""
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
            flat.append(x)
            flat.append(y)
        rings_flat.append(flat)
    return rings_flat


def _first_prop(props, *keys):
    for k in keys:
        v = (props.get(k) or "").strip() if isinstance(props.get(k), str) else props.get(k)
        if v:
            return str(v).strip()
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--india-adm2", default=None, metavar="URL_OR_PATH",
                    help="optional post-2022 India district GeoJSON "
                         "(REPLACES India's district tier; renumbers its uids)")
    args = ap.parse_args()

    sys.path.insert(0, str(REPO / "backend"))
    from app.geopolitics import admin_atlas
    from app.geopolitics.admin_atlas import _decode_ring, _ring_contains
    data = admin_atlas._load()
    units = data["units"]
    enc = data["enc"]
    enc_by_uid = {e["i"]: e for e in enc}
    next_id = max(u["uid"] for u in units) + 1

    # ---- point-in-polygon over a set of enc entries --------------------------
    def resolver_for(entries):
        res = []
        for e in entries:
            bb = e["b"]
            area = (bb[2] - bb[0]) * (bb[3] - bb[1])
            res.append((e["i"], bb, area, [_decode_ring(r) for r in e["r"]]))
        return res

    def smallest_at(res, lat, lon):
        best, best_area = None, 1e18
        for uid, bb, area, rings in res:
            if lon < bb[0] or lon > bb[2] or lat < bb[1] or lat > bb[3]:
                continue
            for ring in rings:
                if _ring_contains(ring, lat, lon):
                    if area < best_area:
                        best_area, best = area, uid
                    break
        return best

    name_by_uid = {u["uid"]: u["name"] for u in units}

    # ============ 1. China prefectures (GADM 4.1 ADM2, level 2) ==============
    gj = _fetch_gadm("CHN", 2)
    chn_l1 = resolver_for([enc_by_uid[u["uid"]] for u in units
                           if u["country"] == "CHN" and u.get("level", 1) == 1
                           and u["uid"] in enc_by_uid])
    pref_units, pref_enc = [], []
    for f in gj["features"]:
        p = f.get("properties", {})
        geom = f.get("geometry")
        name = _first_prop(p, "NAME_2", "shapeName", "name")
        if not geom or not name:
            continue
        rings_flat = _simplify(geom)
        if not rings_flat:
            continue
        bb = _bbox(rings_flat)
        cx, cy = _centroid(rings_flat)
        parent = smallest_at(chn_l1, cy, cx)
        parent_name = name_by_uid.get(parent)
        uid = next_id
        next_id += 1
        pref_enc.append({"i": uid, "n": name, "c": "CHN", "b": bb,
                         "r": [encode_ring(r) for r in rings_flat]})
        eng = _first_prop(p, "ENGTYPE_2") or "Prefecture"
        pref_units.append({
            "uid": uid, "name": name, "name_local": _first_prop(p, "NL_NAME_2") or None,
            "country": "CHN", "iso2": "", "level": 2,
            "parent": parent, "path": "/".join(x for x in ("CHN", parent_name, name) if x),
            "clat": cy, "clon": cx, "bbox": bb,
            "area_km2": _area_km2(rings_flat),
            "type": eng, "src": "gadm-4.1",
        })
        name_by_uid[uid] = name
    if len(pref_units) < 300:
        raise SystemExit(f"GADM CHN ADM2 returned only {len(pref_units)} usable "
                         "units — expected ~340 prefectures; refusing to ship a "
                         "partial tier.")
    print(f"CHN prefectures (GADM ADM2): {len(pref_units)} units "
          f"({sum(1 for u in pref_units if u['parent'])} province-linked)",
          file=sys.stderr)

    # ============ 2. Re-level CHN counties 2 → 3 under the prefectures =======
    pref_res = resolver_for(pref_enc)
    relinked, kept = 0, 0
    for u in units:
        if u["country"] == "CHN" and u.get("level", 1) == 2:
            u["level"] = 3
            if u.get("type") in (None, "District", "County"):
                u["type"] = "County"
            new_parent = smallest_at(pref_res, u["clat"], u["clon"])
            if new_parent:
                u["parent"] = new_parent
                u["path"] = "/".join(x for x in (
                    "CHN", name_by_uid.get(new_parent), u["name"]) if x)
                relinked += 1
            else:
                kept += 1  # keeps its province parent — variable depth (Q1)
    print(f"CHN counties re-leveled 2→3: {relinked} prefecture-linked, "
          f"{kept} kept their province parent", file=sys.stderr)

    # ============ 3. Optional: post-2022 India districts ======================
    ind_units, ind_enc = [], []
    dropped_ind = 0
    if args.india_adm2:
        gj = _load_geojson(args.india_adm2)
        ind_l1 = resolver_for([enc_by_uid[u["uid"]] for u in units
                               if u["country"] == "IND" and u.get("level", 1) == 1
                               and u["uid"] in enc_by_uid])
        for f in gj.get("features", []):
            p = f.get("properties", {})
            geom = f.get("geometry")
            name = _first_prop(p, "shapeName", "NAME_2", "district", "DISTRICT",
                               "dtname", "name")
            if not geom or not name:
                continue
            rings_flat = _simplify(geom)
            if not rings_flat:
                continue
            bb = _bbox(rings_flat)
            cx, cy = _centroid(rings_flat)
            parent = smallest_at(ind_l1, cy, cx)
            uid = next_id
            next_id += 1
            ind_enc.append({"i": uid, "n": name, "c": "IND", "b": bb,
                            "r": [encode_ring(r) for r in rings_flat]})
            ind_units.append({
                "uid": uid, "name": name, "name_local": None, "country": "IND",
                "iso2": "", "level": 2, "parent": parent,
                "path": "/".join(x for x in ("IND", name_by_uid.get(parent), name) if x),
                "clat": cy, "clon": cx, "bbox": bb,
                "area_km2": _area_km2(rings_flat),
                "type": "District", "src": "india-post2022",
            })
            name_by_uid[uid] = name
        if len(ind_units) < 700:
            raise SystemExit(f"India source yielded only {len(ind_units)} districts "
                             "— post-2022 India has 750+; refusing a partial tier.")
        # retire the old pre-2022 districts (this is the uid renumber)
        old_ind = {u["uid"] for u in units
                   if u["country"] == "IND" and u.get("level", 1) == 2}
        units = [u for u in units if u["uid"] not in old_ind]
        enc = [e for e in enc if e["i"] not in old_ind]
        dropped_ind = len(old_ind)
        print(f"IND districts REPLACED: {dropped_ind} pre-2022 retired, "
              f"{len(ind_units)} post-2022 appended (uids renumbered — as "
              "documented since v8.12; DB rows for retired uids are orphaned "
              "but harmless)", file=sys.stderr)

    # ============ 4. Emit both artifacts ======================================
    all_units = units + pref_units + ind_units
    all_enc = enc + pref_enc + ind_enc
    lvl_by_uid = {u["uid"]: u.get("level", 1) for u in all_units}
    by_level = {}
    for e in all_enc:
        by_level.setdefault(lvl_by_uid.get(e["i"], 1), []).append(e)

    fe = REPO / "frontend" / "src" / "data" / "adminBoundaries.js"
    with open(fe, "w", encoding="utf-8") as fh:
        fh.write("// GENERATED by scripts/build_admin_atlas*.py — DO NOT EDIT.\n")
        fh.write("// V8 — ADM1 (Natural Earth) + deeper tiers (geoBoundaries +\n")
        fh.write("// GADM 4.1 CHN prefectures), polyline-encoded.\n")
        for lvl in (1, 2, 3):
            fh.write(f"export const ADMIN{lvl}_ENC = ")
            json.dump(by_level.get(lvl, []), fh, separators=(",", ":"), ensure_ascii=False)
            fh.write(";\n")
    print(f"wrote {fe} ({fe.stat().st_size // 1024} KB; "
          + ", ".join(f"ADM{l} {len(by_level.get(l, []))}" for l in (1, 2, 3)) + ")",
          file=sys.stderr)

    be = REPO / "backend" / "app" / "geopolitics" / "admin_atlas.py"
    blob = gzip.compress(json.dumps({"units": all_units, "enc": all_enc},
                                    separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    b64 = base64.b64encode(blob).decode("ascii")
    with open(be, "w", encoding="utf-8") as fh:
        fh.write('"""GENERATED by scripts/build_admin_atlas*.py — DO NOT EDIT.\n\n')
        fh.write("V8 — the admin-unit registry (ADM1 + deeper tiers, incl. GADM 4.1\n")
        fh.write("CHN prefectures) + encoded rings + a pure-python decoder. unit_at()\n")
        fh.write('returns the SMALLEST containing unit. Data gzip+base64 embedded.\n"""\n')
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
    print("done. Commit both artifacts; the seed's fingerprint reconcile "
          "updates an already-seeded DB on next boot.", file=sys.stderr)


if __name__ == "__main__":
    main()
