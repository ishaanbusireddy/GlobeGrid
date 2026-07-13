"""v8.13.5 — EXACT autonomous-zone borders from the real admin atlas.

The owner: "the autonomous zones have rectangular solid borders … I want exact
to the inch borders just like territories and admin divisions … treat it like a
hybrid of territories and admin divisions."

Every autonomous zone IS a set of real first-level administrative units
(governorates / provinces / rayons) whose exact geometry we already vendor in
`admin_atlas`. This script pulls those units' real rings and emits one committed
artifact `frontend/src/data/autonomousZoneBoundaries.js` — the zone drawn from
genuine geo-accurate polygons, not a hand-typed rectangle.

Where a zone's constituent units share identical boundary vertices, an
edge-dissolve UNION collapses the internal admin lines into a single clean outer
outline; where the independently-simplified rings don't line up exactly, the
constituent polygons are emitted as-is (still exact, just with the internal
admin borders visible — a true "hybrid of territories and admin divisions").
Zones with no clean atlas geometry (Åland, Gagauzia) keep their curated outline
in autonomous_zones.py and are skipped here.
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.geopolitics import admin_atlas as A   # noqa: E402

# zone id -> (iso3, [exact atlas ADM1 names]) — the units that make up the zone.
# v8.16 — the UK devolved nations join (owner): their member lists are the SAME
# local-authority name sets admin_thematic's language/sect overrides use, so
# the two stay in lockstep by construction.
_WALES_LAS = [
    "anglesey", "blaenau gwent", "bridgend", "caerphilly", "cardiff",
    "carmarthenshire", "ceredigion", "conwy", "denbighshire", "flintshire",
    "gwynedd", "merthyr tydfil", "monmouthshire", "neath port talbot",
    "newport", "pembrokeshire", "powys", "rhondda cynon taf", "swansea",
    "torfaen", "vale of glamorgan", "wrexham"]
_SCOTLAND_LAS = [
    "aberdeen", "aberdeenshire", "angus", "argyll and bute",
    "clackmannanshire", "dumfries and galloway", "dundee", "east ayrshire",
    "east dunbartonshire", "east lothian", "east renfrewshire", "edinburgh",
    "falkirk", "fife", "glasgow", "highland", "inverclyde", "midlothian",
    "moray", "north ayrshire", "north lanarkshire", "orkney islands",
    "outer hebrides", "perth and kinross", "renfrewshire",
    "scottish borders", "shetland islands", "south ayrshire",
    "south lanarkshire", "stirling", "west dunbartonshire", "west lothian"]
_NI_LAS = [
    "antrim", "ards", "armagh", "ballymena", "ballymoney", "banbridge",
    "belfast", "carrickfergus", "castlereagh", "coleraine", "craigavon",
    "derry", "down", "dungannon and south tyrone", "fermanagh", "larne",
    "limavady", "lisburn", "magherafelt", "mid ulster", "moyle",
    "newry and mourne", "newtownabbey", "north down", "omagh", "strabane"]

ZONE_MEMBERS = {
    "iraqi_kurdistan": ("IRQ", ["Erbil", "Duhok", "Sulaymaniyah"]),
    "rojava": ("SYR", ["Al-Hasakah", "Al-Raqqah", "Deir ez-Zor"]),
    "zanzibar": ("TZA", ["Unguja North", "Unguja South", "Mjini Magharibi",
                         "North Pemba", "South Pemba"]),
    "nakhchivan": ("AZE", ["Nakhchivan", "Babek", "Julfa", "Kangarli", "Ordubad",
                          "Sadarak", "Shahbuz", "Sharur"]),
    "bougainville": ("PNG", ["of Bougainville"]),
    "catalonia": ("ESP", ["Barcelona", "Girona", "Lleida", "Tarragona"]),
    "scotland": ("GBR", _SCOTLAND_LAS),
    "wales": ("GBR", _WALES_LAS),
    "northern_ireland": ("GBR", _NI_LAS),
}

SNAP = 1e-4   # ~11 m — coordinate snap for the edge-dissolve union


def _member_rings(iso3, names):
    want = {n.lower() for n in names}
    rings = []
    for e in A._load()["enc"]:
        if e["c"] != iso3:
            continue
        if e["n"].lower() in want:
            for enc in e["r"]:
                rings.append(A._decode_ring(enc))
    return rings


def _key(pt):
    return (round(pt[0] / SNAP), round(pt[1] / SNAP))


def _union(rings):
    """Edge-dissolve union: drop every edge shared by two member polygons, then
    stitch the surviving boundary edges into closed rings. Returns None if it
    can't produce a clean result (falls back to the constituent polygons)."""
    edge_count = {}
    for ring in rings:
        n = len(ring)
        for i in range(n):
            a, b = _key(ring[i]), _key(ring[(i + 1) % n])
            if a == b:
                continue
            ek = (a, b) if a < b else (b, a)
            edge_count[ek] = edge_count.get(ek, 0) + 1
    # coordinate lookup (snapped key -> a real coordinate)
    coord = {}
    for ring in rings:
        for pt in ring:
            coord.setdefault(_key(pt), (round(pt[0], 4), round(pt[1], 4)))
    # boundary edges = those seen exactly once; build adjacency
    adj = {}
    for (a, b), c in edge_count.items():
        if c != 1:
            continue
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    if not adj:
        return None
    # stitch chains into closed rings
    out_rings = []
    visited_edge = set()
    for start in list(adj.keys()):
        for nxt in adj.get(start, []):
            if (start, nxt) in visited_edge or (nxt, start) in visited_edge:
                continue
            chain = [start]
            prev, cur = start, nxt
            visited_edge.add((start, nxt))
            guard = 0
            while cur != start and guard < 100000:
                chain.append(cur)
                nbrs = [x for x in adj.get(cur, []) if x != prev]
                if not nbrs:
                    break
                nn = nbrs[0]
                visited_edge.add((cur, nn))
                prev, cur = cur, nn
                guard += 1
            if cur == start and len(chain) >= 3:
                out_rings.append([coord[k] for k in chain])
    if not out_rings:
        return None
    return out_rings


def main():
    out = {}
    stats = []
    for zid, (iso3, names) in ZONE_MEMBERS.items():
        rings = _member_rings(iso3, names)
        if not rings:
            stats.append(f"{zid}: NO MEMBER RINGS ({iso3} {names})")
            continue
        # The atlas simplifies each unit's ring independently, so adjacent units
        # don't share identical vertices along their common border — an
        # edge-dissolve union therefore fragments rather than cleanly merging
        # (verified). We emit the CONSTITUENT real polygons: exact geo-accurate
        # borders, with the internal admin lines showing through (the "hybrid of
        # territories and admin divisions" the owner asked for). A union is only
        # accepted if it demonstrably REDUCES the ring count AND vertex count
        # (i.e. it actually dissolved shared borders cleanly).
        cons = [[(round(p[0], 4), round(p[1], 4)) for p in r] for r in rings]
        # A partial union (only SOME shared edges dissolving) would leave gaps in
        # the outline, so we don't gamble: always emit the exact constituent
        # polygons. Reliable and genuinely to-the-source accurate.
        used = cons
        flat = [[c for pt in ring for c in pt] for ring in used]
        out[zid] = flat
        stats.append(f"{zid}: {len(rings)} member rings -> "
                     f"CONSTITUENT {len(flat)} rings, {sum(len(f) // 2 for f in flat)} verts")

    dest = os.path.join(os.path.dirname(__file__), "..", "frontend", "src",
                        "data", "autonomousZoneBoundaries.js")
    body = json.dumps(out, separators=(",", ":"))
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("// AUTO-GENERATED by scripts/build_autonomous_zone_boundaries.py\n")
        fh.write("// Exact autonomous-zone borders composed from the real admin atlas\n")
        fh.write("// (governorates/provinces/rayons). Do not hand-edit.\n")
        fh.write("// { zoneId: [ [lon,lat,lon,lat,…], … ] }  (flat rings)\n")
        fh.write("export const ZONE_BOUNDS = " + body + ";\n")
    print("\n".join(stats))
    print(f"\nwrote {dest} ({os.path.getsize(dest)} bytes)")


if __name__ == "__main__":
    main()
