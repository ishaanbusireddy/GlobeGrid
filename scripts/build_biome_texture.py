"""v6 §19 — bake the globe's biome/elevation texture from vendored data.

Replaces the v5 procedural-noise terrain with a REAL equirectangular texture:
land shapes rasterized from the vendored Natural Earth coastline rings
(frontend/src/data/worldCoastline.js — the same data the base map draws, so
terrain and coastlines always agree), colored by latitude-banded biome
palette in the spirit of NASA Blue Marble (which can't be vendored at repo
size; the banding + desert-belt heuristic is a documented approximation of
it), with deterministic value-noise elevation shading baked in.

Output: frontend/src/data/biomeTexture.js exporting a PNG data URL the
WebGL2 globe loads as an ordinary texture and samples in the sphere shader's
UV space. Pure stdlib (zlib+struct PNG writer) — zero-install preserved.

Usage: python scripts/build_biome_texture.py [--width 1024]
"""

import base64
import math
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W = 1024
if "--width" in sys.argv:
    W = int(sys.argv[sys.argv.index("--width") + 1])
H = W // 2


def load_rings():
    src = (ROOT / "frontend/src/data/worldCoastline.js").read_text()
    m = re.search(r"COASTLINES\s*=\s*(\[\[.*?\]\])\s*;", src, re.S)
    rings = []
    for ring_m in re.finditer(r"\[([-0-9.,\s]+)\]", m.group(1)):
        nums = [float(x) for x in ring_m.group(1).split(",") if x.strip()]
        pts = list(zip(nums[0::2], nums[1::2]))
        if len(pts) >= 4:
            rings.append(pts)
    return rings


def rasterize_land(rings):
    """Even-odd scanline fill over the equirectangular grid."""
    land = bytearray(W * H)
    for y in range(H):
        lat = 90.0 - (y + 0.5) * 180.0 / H
        xs_all = []
        for ring in rings:
            xs = []
            n = len(ring)
            for i in range(n - 1):
                (x1, y1), (x2, y2) = ring[i], ring[i + 1]
                if (y1 <= lat < y2) or (y2 <= lat < y1):
                    t = (lat - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                xs_all.append((xs[j], xs[j + 1]))
        for x0, x1 in xs_all:
            px0 = max(0, int((x0 + 180.0) / 360.0 * W))
            px1 = min(W - 1, int((x1 + 180.0) / 360.0 * W))
            for px in range(px0, px1 + 1):
                land[y * W + px] = 1
    # Antarctica's ring set doesn't close across the pole edge — fill below -78
    for y in range(H):
        lat = 90.0 - (y + 0.5) * 180.0 / H
        if lat < -78:
            for px in range(W):
                land[y * W + px] = 1
    return land


def _hash2(x, y):
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def value_noise(x, y, scale):
    xf, yf = x / scale, y / scale
    x0, y0 = int(xf), int(yf)
    fx, fy = xf - x0, yf - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash2(x0, y0)
    b = _hash2(x0 + 1, y0)
    c = _hash2(x0, y0 + 1)
    d = _hash2(x0 + 1, y0 + 1)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy


def fbm(x, y):
    return (0.5 * value_noise(x, y, 96) + 0.3 * value_noise(x, y, 34)
            + 0.2 * value_noise(x, y, 12))


# v6.1.1 — vendored major mountain ranges: (name, peak_height 0-1, width°,
# [(lon,lat), ...] centreline). Splatted as gaussian ridges into an elevation
# field so the globe shows REAL topography (Himalayas, Andes, Rockies, Alps,
# ...) with hillshade relief, not a flat biome blob.
MOUNTAIN_RANGES = [
    ("Himalayas", 1.0, 3.2, [(71, 36), (77, 35), (82, 30), (88, 28), (92, 28), (97, 29)]),
    ("Karakoram/Hindu Kush", 0.92, 2.6, [(66, 34), (71, 36), (75, 36)]),
    ("Tian Shan", 0.78, 2.6, [(70, 42), (78, 42), (86, 43), (94, 43)]),
    ("Kunlun/Tibet", 0.85, 4.0, [(80, 35), (90, 35), (98, 34)]),
    ("Andes", 0.95, 2.4, [(-70, 10), (-72, 0), (-70, -15), (-69, -30), (-70, -45), (-73, -52)]),
    ("Rockies", 0.8, 2.8, [(-150, 62), (-140, 55), (-118, 45), (-110, 40), (-106, 35)]),
    ("Sierra Madre", 0.7, 2.0, [(-106, 30), (-104, 24), (-100, 18)]),
    ("Alps", 0.78, 1.8, [(6, 46), (10, 47), (14, 47), (16, 46)]),
    ("Caucasus", 0.82, 1.6, [(40, 43), (44, 42), (48, 41)]),
    ("Zagros", 0.72, 2.2, [(46, 38), (50, 34), (54, 30), (57, 27)]),
    ("Alborz/Elburz", 0.7, 1.4, [(48, 37), (52, 36), (56, 37)]),
    ("Atlas", 0.62, 1.6, [(-8, 31), (-4, 32), (2, 34), (7, 36)]),
    ("Ethiopian Highlands", 0.66, 2.6, [(36, 6), (38, 10), (39, 14), (40, 12)]),
    ("Ural", 0.5, 1.6, [(60, 66), (59, 60), (58, 54), (57, 50)]),
    ("Scandinavian", 0.58, 1.6, [(6, 62), (12, 65), (18, 68), (24, 70)]),
    ("Appalachians", 0.45, 1.8, [(-84, 34), (-80, 38), (-75, 42), (-70, 45)]),
    ("Great Dividing Range", 0.5, 1.8, [(146, -20), (149, -28), (150, -34), (148, -37)]),
    ("Japanese Alps", 0.6, 1.2, [(137, 36), (139, 37), (141, 39), (142, 43)]),
    ("Drakensberg", 0.55, 1.6, [(28, -28), (29, -30), (28, -31)]),
    ("Altai/Sayan", 0.72, 2.4, [(86, 49), (92, 51), (98, 51), (104, 52)]),
]


def _lonlat_to_px(lon, lat):
    return ((lon + 180.0) / 360.0 * W, (90.0 - lat) / 180.0 * H)


def build_elevation(land):
    """Land elevation field 0..1: gaussian mountain ridges + light base noise."""
    elev = [0.0] * (W * H)
    px_per_deg = W / 360.0
    for _name, height, width_deg, line in MOUNTAIN_RANGES:
        rad = max(1, int(width_deg * px_per_deg * 2.2))
        inv2s2 = 1.0 / (2.0 * (width_deg * px_per_deg) ** 2)
        # densify the centreline so ridges are continuous
        for (lon0, lat0), (lon1, lat1) in zip(line, line[1:]):
            seg = max(1, int(math.hypot(lon1 - lon0, lat1 - lat0) * 2))
            for s in range(seg + 1):
                t = s / seg
                cx, cy = _lonlat_to_px(lon0 + (lon1 - lon0) * t,
                                       lat0 + (lat1 - lat0) * t)
                x0, x1 = int(cx - rad), int(cx + rad)
                y0, y1 = max(0, int(cy - rad)), min(H - 1, int(cy + rad))
                for yy in range(y0, y1 + 1):
                    for xx in range(x0, x1 + 1):
                        wx = xx % W
                        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                        v = height * math.exp(-d2 * inv2s2)
                        idx = yy * W + wx
                        if v > elev[idx]:
                            elev[idx] = v
    # add gentle base relief on land so plains aren't dead flat
    for y in range(H):
        for x in range(W):
            idx = y * W + x
            if land[idx]:
                elev[idx] = min(1.0, elev[idx] + 0.12 * fbm(x, y))
    return elev


# latitude-banded biome palette (r,g,b); high elevation adds rock + snow
def biome_color(lat, elev, desert, hillshade):
    a = abs(lat)
    if a > 78:
        base = (235, 240, 245)          # ice sheet
    elif a > 66:
        base = (170, 165, 150)          # tundra
    elif a > 55:
        base = (58, 92, 60)             # boreal forest
    elif a > 38:
        base = (92, 122, 66)            # temperate
    elif a > 12:
        base = (194, 168, 116) if desert else (128, 138, 74)
    else:
        base = (46, 102, 48)            # tropical forest
    # v6.1.1 — elevation zones: bare rock on high slopes, snow on peaks (the
    # snowline drops toward the poles), so ranges read as ranges
    snowline = 0.72 - 0.006 * a
    if elev > snowline:
        base = (240, 244, 250)          # snow / glacier
    elif elev > 0.42:
        rock = (120, 110, 100)
        m = min(1.0, (elev - 0.42) / 0.3)
        base = tuple(int(base[k] * (1 - m) + rock[k] * m) for k in range(3))
    # hillshade: directional relief (already 0.55..1.15), plus a mild elevation
    # brighten so high ground pops
    shade = hillshade * (0.9 + 0.18 * elev)
    return tuple(max(0, min(255, int(c * shade))) for c in base)


def build_pixels(land):
    elev = build_elevation(land)
    px = bytearray(W * H * 4)
    # NW light direction for the hillshade
    lx, ly, lz = -0.5, -0.6, 0.62
    for y in range(H):
        lat = 90.0 - (y + 0.5) * 180.0 / H
        for x in range(W):
            i = (y * W + x) * 4
            idx = y * W + x
            if land[idx]:
                e = elev[idx]
                # slope from elevation gradient (scaled so relief is visible)
                ex = (elev[y * W + (x + 1) % W] - elev[y * W + (x - 1) % W]) * 8.0
                ey = ((elev[min(H - 1, y + 1) * W + x]
                       - elev[max(0, y - 1) * W + x]) * 8.0)
                nx, ny, nz = -ex, -ey, 1.0
                nl = math.sqrt(nx * nx + ny * ny + nz * nz)
                hs = (nx * lx + ny * ly + nz * lz) / nl
                hillshade = 0.62 + 0.55 * max(0.0, hs)
                dry = value_noise(x + 4096, y + 4096, 140)
                desert = 12 < abs(lat) < 38 and dry > 0.46
                r, g, b = biome_color(lat, e, desert, hillshade)
                px[i], px[i + 1], px[i + 2], px[i + 3] = r, g, b, 255
            else:
                depth = 0.85 + 0.15 * (abs(lat) / 90.0)
                px[i] = int(12 * depth)
                px[i + 1] = int(32 * depth)
                px[i + 2] = int(58 * depth)
                px[i + 3] = 255
    return bytes(px)


def write_png(pixels):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    raw = b"".join(b"\x00" + pixels[y * W * 4:(y + 1) * W * 4] for y in range(H))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def main():
    rings = load_rings()
    print(f"rings: {len(rings)}; rasterizing {W}x{H}…")
    land = rasterize_land(rings)
    print(f"land coverage: {100.0 * sum(land) / (W * H):.1f}%")
    png = write_png(build_pixels(land))
    b64 = base64.b64encode(png).decode()
    out = ROOT / "frontend/src/data/biomeTexture.js"
    out.write_text(
        "// v6 §19 — baked biome/elevation texture (equirectangular). Generated by\n"
        "// scripts/build_biome_texture.py from the vendored Natural Earth coastline\n"
        "// rings — real land shapes, latitude-banded biome palette, noise-shaded\n"
        "// relief. Regenerate with: python scripts/build_biome_texture.py\n"
        f"export const BIOME_TEXTURE_DATAURL = \"data:image/png;base64,{b64}\";\n")
    print(f"wrote {out} ({len(png) / 1024:.0f} KB png, {len(b64) / 1024:.0f} KB b64)")


if __name__ == "__main__":
    main()
