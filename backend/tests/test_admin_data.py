"""Curated-table ↔ atlas key integrity (the v8.11 silently-dead-override bug
class). A SUBNATIONAL / demographics key whose (iso3, name) doesn't match a
real atlas ADM1 unit silently does NOTHING — the map falls back to the country
value with no error — so this suite makes any future mismatch a loud test
failure instead. v8.13.7 reintroduced 30 dead keys exactly this way; they were
found by writing this test (fixed in v8.14)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.geopolitics.admin_atlas import units  # noqa: E402
from app.geopolitics import admin_demographics, admin_thematic  # noqa: E402


def _adm1_names(lower=False):
    by_iso = {}
    for u in units():
        if u.get("level", 1) == 1:
            n = u["name"].lower() if lower else u["name"]
            by_iso.setdefault(u["country"], set()).add(n)
    return by_iso


class TestSubnationalKeys(unittest.TestCase):
    def test_every_override_resolves(self):
        adm1 = _adm1_names(lower=True)
        dead = [k for k in admin_thematic.SUBNATIONAL
                if k[1] not in adm1.get(k[0], set())]
        self.assertEqual(dead, [],
                         f"{len(dead)} SUBNATIONAL overrides are silently dead "
                         f"(no matching atlas ADM1 unit): {dead[:10]}")


class TestDemographicsKeys(unittest.TestCase):
    def test_population_units_resolve(self):
        adm1 = _adm1_names()
        dead = [k for k in admin_demographics.UNITS
                if k[1] not in adm1.get(k[0], set())]
        self.assertEqual(dead, [],
                         f"{len(dead)} demographics UNITS keys are dead: {dead[:10]}")

    def test_gdp_units_resolve(self):
        adm1 = _adm1_names()
        dead = [k for k in admin_demographics._GDP_USD
                if k[1] not in adm1.get(k[0], set())]
        self.assertEqual(dead, [], f"{len(dead)} _GDP_USD keys are dead: {dead[:10]}")

    def test_lookup_disambiguates_moscow(self):
        # v8.6 — two RUS ADM1 units are both named "Moscow"; the closest-area
        # candidate must win (city ≈ 2.5k km² vs oblast ≈ 44k km²).
        city = admin_demographics.lookup("RUS", "Moscow", 2500)
        oblast = admin_demographics.lookup("RUS", "Moscow", 44000)
        self.assertTrue(city and oblast)
        self.assertGreater(city["pop"], oblast["pop"],
                           "Moscow-city (13M) must out-populate Moscow-oblast (8.5M)")


class TestAtlasIntegrity(unittest.TestCase):
    def test_uids_unique(self):
        us = units()
        uids = [u["uid"] for u in us]
        self.assertEqual(len(uids), len(set(uids)), "duplicate admin uids")

    def test_parents_exist_and_anomalies_stay_pinned(self):
        # Every parent uid must exist. Parent level is NORMALLY shallower, but
        # centroid point-in-polygon linking produces a small, known set of
        # cross-border/enclave artifacts (~38 in the v8.12 atlas): Aksai Chin
        # counties whose centroid falls in Ladakh, Llívia inside France,
        # LoC-straddling districts (same-level parents), and Swiss Bettingen
        # whose centroid lands in Germany's Kreis Lörrach (a deeper parent).
        # These are documented data quirks, not build errors — but a GROWING
        # count would be one, so the ceiling is pinned.
        us = units()
        by_uid = {u["uid"]: u for u in us}
        anomalies = 0
        for u in us:
            p = u.get("parent")
            if p is None:
                continue
            self.assertIn(p, by_uid, f"uid {u['uid']} parent {p} missing")
            if by_uid[p].get("level", 1) >= u.get("level", 1):
                anomalies += 1
        self.assertLessEqual(anomalies, 60,
                             f"{anomalies} non-shallower parent links — the "
                             "cross-border artifact count grew; check the "
                             "latest atlas build")

    def test_areas_nonnegative(self):
        bad = [u["uid"] for u in units() if (u.get("area_km2") or 0) < 0]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
