#!/usr/bin/env python3
"""V8 — the Administrative Atlas build pipeline (Phase V8.0: ADM1 provinces).

Fetches REAL admin-1 (state/province) boundaries from Natural Earth (public
domain, ~3,600 units worldwide), simplifies + polyline-encodes them into the
SAME format the country boundaries use (frontend/src/data/boundaryCodec.js), and
emits two vendored artifacts:

  frontend/src/data/adminBoundaries.js   — encoded rings for the renderers
  backend/app/geopolitics/admin_atlas.py — the unit registry (id/name/country/
                                           centroid/level/bbox) + a pure-Python
                                           ring decoder, so the backend can do
                                           point-in-polygon (event->unit, /at).

No numpy/PIL/shapely — pure stdlib + a tiny Douglas-Peucker. Build-time only;
the outputs are committed and served, so the runtime stays zero-install.

Per owner decisions: everything vendored in-repo (Q2); ADM1 rides the proven
vector renderer (the raster/SDF GPU spine is the later phase, needed only at
ADM2's ~45k units). geoBoundaries/OSM deeper tiers + full historical epochs are
the follow-on data passes.

Usage:  python scripts/build_admin_atlas.py
"""
import gzip
import json
import math
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
          "master/geojson/ne_10m_admin_1_states_provinces.geojson")
QUANT = 1000            # matches boundaryCodec.js decodeRing quant
SIMPLIFY_TOL = 0.02     # degrees (~2km) — full 10m detail simplified for web
MIN_RING_PTS = 4


# ---------------------------------------------------------------- polyline enc
def _encode_signed(num: int, out: list):
    v = num << 1
    if num < 0:
        v = ~v
    while v >= 0x20:
        out.append(chr((0x20 | (v & 0x1f)) + 63))
        v >>= 5
    out.append(chr(v + 63))


def encode_ring(flat):
    """flat = [lon,lat,lon,lat,...] floats -> polyline string (delta lon then lat)."""
    out = []
    plon = plat = 0
    for i in range(0, len(flat), 2):
        lon = int(round(flat[i] * QUANT))
        lat = int(round(flat[i + 1] * QUANT))
        _encode_signed(lon - plon, out)
        _encode_signed(lat - plat, out)
        plon, plat = lon, lat
    return "".join(out)


# ---------------------------------------------------------------- geometry
def _dp(points, tol):
    """Douglas-Peucker on [(lon,lat),...]; pure python."""
    if len(points) < 3:
        return points
    dmax, idx = 0.0, 0
    ax, ay = points[0]
    bx, by = points[-1]
    dx, dy = bx - ax, by - ay
    norm = dx * dx + dy * dy
    for i in range(1, len(points) - 1):
        px, py = points[i]
        if norm == 0:
            d = math.hypot(px - ax, py - ay)
        else:
            t = ((px - ax) * dx + (py - ay) * dy) / norm
            t = max(0.0, min(1.0, t))
            d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        left = _dp(points[:idx + 1], tol)
        right = _dp(points[idx:], tol)
        return left[:-1] + right
    return [points[0], points[-1]]


def _rings_of(geom):
    """Yield outer rings (list of (lon,lat)) from Polygon/MultiPolygon."""
    t = geom.get("type")
    if t == "Polygon":
        for ring in geom["coordinates"]:
            yield ring
    elif t == "MultiPolygon":
        for poly in geom["coordinates"]:
            for ring in poly:
                yield ring


def _bbox(rings_flat):
    mnx = mny = 1e9
    mxx = mxy = -1e9
    for r in rings_flat:
        for i in range(0, len(r), 2):
            x, y = r[i], r[i + 1]
            mnx = min(mnx, x); mxx = max(mxx, x)
            mny = min(mny, y); mxy = max(mxy, y)
    return [round(mnx, 3), round(mny, 3), round(mxx, 3), round(mxy, 3)]


def _centroid(rings_flat):
    """Area-weighted centroid of the largest ring (label/click-fallback anchor)."""
    best, best_area = None, -1
    for r in rings_flat:
        area = cx = cy = 0.0
        n = len(r)
        for i in range(0, n, 2):
            x0, y0 = r[i], r[i + 1]
            j = (i + 2) % n
            x1, y1 = r[j], r[j + 1]
            cross = x0 * y1 - x1 * y0
            area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross
        if abs(area) < 1e-12:
            continue
        area *= 0.5
        cx /= (6 * area); cy /= (6 * area)
        if abs(area) > best_area:
            best_area, best = abs(area), (round(cx, 4), round(cy, 4))
    if best:
        return best
    # degenerate: mean of first ring
    r = rings_flat[0]
    xs = r[0::2]; ys = r[1::2]
    return (round(sum(xs) / len(xs), 4), round(sum(ys) / len(ys), 4))


# ---------------------------------------------------------------- main
def fetch_source():
    cache = REPO / "scripts" / "_ne_admin1.geojson"
    if cache.exists():
        return json.loads(cache.read_text())
    print("fetching Natural Earth admin-1 …", file=sys.stderr)
    with urllib.request.urlopen(NE_URL, timeout=60) as r:
        data = r.read()
    cache.write_bytes(data)
    return json.loads(data)


def main():
    gj = fetch_source()
    feats = gj["features"]
    print(f"source features: {len(feats)}", file=sys.stderr)

    units = []      # registry rows
    enc = []        # encoded boundary entries
    next_id = 1
    for f in feats:
        p = f.get("properties", {})
        geom = f.get("geometry")
        if not geom:
            continue
        iso3 = (p.get("adm0_a3") or p.get("iso_a2") or "").strip()
        # Prefer the English name for the primary display label so the product
        # is globally readable (Bavaria, not Bayern; Saxony, not Sachsen) and
        # keep the endonym as name_local. NE 10m's `name` is English for some
        # countries (US states) and the local script for others (German
        # Länder), so name_en is the consistent choice.
        name = (p.get("name_en") or p.get("name") or p.get("gn_name")
                or p.get("woe_name") or "").strip()
        if not name:
            continue
        local = (p.get("name") or "").strip()
        name_local = local if (local and local != name) else None
        iso2 = (p.get("iso_3166_2") or "").strip()

        rings_flat = []
        for ring in _rings_of(geom):
            pts = [(c[0], c[1]) for c in ring if len(c) >= 2]
            if len(pts) < MIN_RING_PTS:
                continue
            simp = _dp(pts, SIMPLIFY_TOL)
            if len(simp) < 3:
                continue
            flat = []
            for x, y in simp:
                flat.append(x); flat.append(y)
            rings_flat.append(flat)
        if not rings_flat:
            continue

        uid = next_id
        next_id += 1
        bb = _bbox(rings_flat)
        cx, cy = _centroid(rings_flat)
        enc.append({
            "i": uid, "n": name, "c": iso3, "b": bb,
            "r": [encode_ring(r) for r in rings_flat],
        })
        units.append({
            "uid": uid, "name": name, "name_local": name_local,
            "country": iso3, "iso2": iso2,
            "level": 1, "clat": cy, "clon": cx, "bbox": bb,
            "type": (p.get("type_en") or "").strip(),
        })

    # ---- frontend artifact ---------------------------------------------------
    fe = REPO / "frontend" / "src" / "data" / "adminBoundaries.js"
    with open(fe, "w", encoding="utf-8") as fh:
        fh.write("// GENERATED by scripts/build_admin_atlas.py — DO NOT EDIT.\n")
        fh.write("// V8 §3 — real ADM1 (province/state) boundaries, Natural Earth\n")
        fh.write("// (public domain), polyline-encoded like the country layer.\n")
        fh.write("export const ADMIN1_ENC = ")
        json.dump(enc, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write(";\n")
    print(f"wrote {fe} ({fe.stat().st_size // 1024} KB, {len(enc)} units)",
          file=sys.stderr)

    # ---- backend artifact ----------------------------------------------------
    be = REPO / "backend" / "app" / "geopolitics" / "admin_atlas.py"
    payload = {"units": units, "enc": enc}
    blob = gzip.compress(json.dumps(payload, separators=(",", ":"),
                                    ensure_ascii=False).encode("utf-8"))
    import base64
    b64 = base64.b64encode(blob).decode("ascii")
    with open(be, "w", encoding="utf-8") as fh:
        fh.write('"""GENERATED by scripts/build_admin_atlas.py — DO NOT EDIT.\n\n')
        fh.write("V8 — the admin-unit registry + encoded rings + a pure-python\n")
        fh.write("decoder, so the backend can point-in-polygon (event->unit, /at)\n")
        fh.write('without shapely. Data gzip+base64 embedded to keep the module small.\n"""\n')
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
    print(f"wrote {be} ({be.stat().st_size // 1024} KB)", file=sys.stderr)
    print("done.", file=sys.stderr)


_DECODER_SRC = '''
def _decode_ring(s, quant=1000):
    out = []
    lon = lat = i = 0
    n = len(s)
    while i < n:
        for k in range(2):
            result = shift = 0
            while True:
                b = ord(s[i]) - 63; i += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if k == 0:
                lon += delta
            else:
                lat += delta
        out.append((lon / quant, lat / quant))
    return out


def _ring_contains(ring, lat, lon):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and \\
           (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-9) + xi):
            inside = not inside
        j = i
    return inside


_RINGS = None

def _rings():
    global _RINGS
    if _RINGS is None:
        _RINGS = []
        for e in _load()['enc']:
            bb = e['b']
            area = (bb[2] - bb[0]) * (bb[3] - bb[1])
            _RINGS.append((e['i'], bb, area, [_decode_ring(r) for r in e['r']]))
    return _RINGS


def unit_at(lat, lon):
    """Return admin_uid of the smallest ADM1 unit containing the point, or None."""
    best, best_area = None, 1e18
    for uid, bb, area, rings in _rings():
        if lon < bb[0] or lon > bb[2] or lat < bb[1] or lat > bb[3]:
            continue
        for ring in rings:
            if _ring_contains(ring, lat, lon):
                if area < best_area:
                    best_area, best = area, uid
                break
    return best
'''


if __name__ == "__main__":
    main()
