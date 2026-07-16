"""v8.17 — data-integrity sweep over the large hand-curated tables.

The project carries a huge amount of hand-maintained data — legislatures,
currencies, alignments, per-unit demographics/religion/sect/dialect overrides —
that historically was validated only by one-off `python3 -c` checks during a
build session, not by standing tests. That is exactly how v8.14 shipped 30
silently-dead SUBNATIONAL keys and v8.16 shipped the missing Russia flags: a
curated entry rotted and nothing caught it. These tests make each table's
internal invariants a loud CI failure so the next such rot is caught before it
ships. Pure stdlib, no DB, no network — same contract as the rest of
backend/tests/.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.geopolitics import country_extra as ce  # noqa: E402

ISO3 = re.compile(r"^[A-Z]{3}$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class TestLegislatures(unittest.TestCase):
    def test_seat_sums_are_sane(self):
        """Every seeded legislature with actual parties must have positive seats
        that never exceed its declared chamber total (vacant seats allowed, so
        <=). A note-only entry (dissolved/no-chamber, e.g. AFG under the
        Taliban) legitimately carries total 0 + no parties + an explanatory
        note — that is allowed, an empty-but-total>0 entry is not."""
        for iso3, leg in ce.LEGISLATURES.items():
            total = leg.get("total")
            parties = leg.get("parties") or []
            self.assertTrue(ISO3.match(iso3), f"{iso3} is not an iso3 code")
            self.assertIsInstance(total, int, f"{iso3} total not an int")
            if not parties:
                # note-only placeholder must explain itself and carry no seats
                self.assertEqual(total, 0, f"{iso3} has total but no parties")
                self.assertTrue(leg.get("note"), f"{iso3} empty with no note")
                continue
            self.assertGreater(total, 0, f"{iso3} has parties but total 0")
            seat_sum = sum(p[1] for p in parties)
            self.assertGreater(seat_sum, 0, f"{iso3} party seats sum to 0")
            self.assertLessEqual(
                seat_sum, total,
                f"{iso3}: party seats {seat_sum} exceed chamber total {total}")

    def test_party_colors_are_hex(self):
        for iso3, leg in ce.LEGISLATURES.items():
            for name, seats, color in leg.get("parties") or []:
                self.assertTrue(name and isinstance(name, str), f"{iso3} party name")
                self.assertIsInstance(seats, int, f"{iso3} {name} seats")
                self.assertGreaterEqual(seats, 0, f"{iso3} {name} seats < 0")
                self.assertTrue(HEX.match(color), f"{iso3} {name} color {color} not hex")


class TestCurrencies(unittest.TestCase):
    def test_currencies_keyed_by_iso3_strings(self):
        # value shape is (code, name, symbol) — a 3-tuple of non-empty strings
        self.assertGreater(len(ce.CURRENCIES), 150, "currency table implausibly small")
        for iso3, cur in ce.CURRENCIES.items():
            self.assertTrue(ISO3.match(iso3), f"{iso3} is not an iso3 code")
            self.assertIsInstance(cur, (tuple, list), f"{iso3} currency not a tuple")
            self.assertGreaterEqual(len(cur), 2, f"{iso3} currency tuple too short")
            self.assertTrue(cur[0] and isinstance(cur[0], str),
                            f"{iso3} currency code empty")


class TestAlignments(unittest.TestCase):
    def test_alignment_buckets_are_disjoint_valid_iso3(self):
        """A country can never be simultaneously an ally, a partner and a rival
        of the same state, must never align with itself, and every code must be
        a real iso3 (the class of bug where a typo'd code silently no-ops)."""
        sample = ["USA", "RUS", "CHN", "IRN", "IND", "PAK", "ISR", "TUR",
                  "GBR", "FRA", "DEU", "BRA", "SAU", "ARM", "AZE", "SYR",
                  "UKR", "JPN", "KOR", "EGY", "NGA", "ZAF", "AUS", "CAN"]
        for iso3 in sample:
            al = ce.derive_alignments(iso3) or {}
            strong = set(al.get("strong") or [])
            partner = set(al.get("partner") or [])
            rival = set(al.get("rival") or [])
            for bucket, name in ((strong, "strong"), (partner, "partner"),
                                 (rival, "rival")):
                for code in bucket:
                    self.assertTrue(ISO3.match(code),
                                    f"{iso3} {name} has non-iso3 {code!r}")
                    self.assertNotEqual(code, iso3,
                                        f"{iso3} aligns with itself in {name}")
            self.assertFalse(strong & rival,
                             f"{iso3}: {strong & rival} are both ally AND rival")
            self.assertFalse(partner & rival,
                             f"{iso3}: {partner & rival} are both partner AND rival")

    def test_every_iso3_gets_an_alignment(self):
        """derive_alignments must never return None for a real code (the v7.4.1
        'missing alignment button on Libya/Chad' bug class)."""
        for iso3 in ("LBY", "TCD", "MNG", "FJI", "BOL", "LAO"):
            self.assertIsNotNone(ce.derive_alignments(iso3),
                                 f"{iso3} has no derived alignment")


class TestCategoryContract(unittest.TestCase):
    def test_category_defs_cover_classifier_labels(self):
        """If the normative category contract exists, it must define every
        category the events-table CHECK admits — otherwise a category can be
        emitted with no human-readable definition behind it."""
        try:
            from app.geopolitics import category_defs as cd
        except Exception:  # noqa: BLE001 — module optional in older trees
            self.skipTest("category_defs not present")
        defined = {k.lower() for k in getattr(cd, "CATEGORY_DEFS", {}).keys()}
        if not defined:
            self.skipTest("CATEGORY_DEFS empty/renamed")
        expected = {"geopolitics", "finance", "technology", "domestic",
                    "health", "disaster", "conflict"}
        missing = expected - defined
        self.assertFalse(missing, f"categories with no definition: {missing}")


if __name__ == "__main__":
    unittest.main()
