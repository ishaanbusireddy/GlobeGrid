"""Polyline codec round-trip: scripts/build_admin_atlas.encode_ring must be
exactly invertible by the backend's admin_atlas._decode_ring at the shared
QUANT=1000 (1e-3°) precision — the two halves are maintained in different
files and every atlas rebuild depends on them agreeing."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from build_admin_atlas import encode_ring, QUANT  # noqa: E402
from app.geopolitics.admin_atlas import _decode_ring  # noqa: E402

RING = [-119.417931, 36.778259,   # California-ish points, incl. negatives,
        -120.0, 37.25,            # duplicates after quantization, and the
        -120.0005, 37.2504,       # antimeridian neighbourhood
        179.9995, -41.5,
        -179.9995, -41.4]


class TestCodecRoundTrip(unittest.TestCase):
    def test_round_trip_within_quant(self):
        pts = _decode_ring(encode_ring(RING))
        self.assertEqual(len(pts), len(RING) // 2)
        tol = 0.5 / QUANT + 1e-9
        for i, (lon, lat) in enumerate(pts):
            self.assertAlmostEqual(lon, RING[2 * i], delta=tol)
            self.assertAlmostEqual(lat, RING[2 * i + 1], delta=tol)

    def test_double_encode_is_stable(self):
        # encode(decode(encode(x))) == encode(x): quantization is idempotent.
        enc1 = encode_ring(RING)
        flat2 = [c for pt in _decode_ring(enc1) for c in pt]
        self.assertEqual(enc1, encode_ring(flat2))


if __name__ == "__main__":
    unittest.main()
