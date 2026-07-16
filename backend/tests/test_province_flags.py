"""Admin-flag URL chain (v8.14). The frontend walks: flag_url (Commons
Special:FilePath — follows filename redirects, the historically-proven form) →
flag_url_alt (direct CDN md5-thumbnail — immune to FilePath rate-limits) →
remove the element (v8.13.9 owner rule: NO national fallback, NO placeholder).
These tests pin both URL shapes and every suppression rule, because v8.13.8/
v8.13.9 each shipped a regression in exactly this chain."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.geopolitics.province_flags import flag_url, flag_url_alt  # noqa: E402


class TestFlagChain(unittest.TestCase):
    def test_wyoming_primary_is_filepath(self):
        url = flag_url("Wyoming", "USA")
        self.assertIn("Special:FilePath", url)
        self.assertIn("Flag%20of%20Wyoming.svg", url)

    def test_wyoming_alt_is_cdn_md5_thumb(self):
        # md5("Flag_of_Wyoming.svg") starts "bc…" → /b/bc/ shard.
        url = flag_url_alt("Wyoming", "USA")
        self.assertIn("upload.wikimedia.org", url)
        self.assertIn("/b/bc/Flag_of_Wyoming.svg/", url)
        self.assertTrue(url.endswith(".png"))

    def test_suppressed_countries_have_no_flags(self):
        # India / China have no official subdivision flags; Pakistan is
        # curated-only; v8.16 adds IRN/TUR/SYR/IRQ/AZE (owner: no separatist
        # Khuzestan / Kurdistan / "South Azerbaijan" flags — official only).
        # Both chain slots must be None so nothing renders.
        for name, iso3 in (("Telangana", "IND"), ("Tibet", "CHN"),
                           ("Islamabad", "PAK"), ("Khuzestan", "IRN"),
                           ("Kurdistan", "IRN"), ("East Azerbaijan", "IRN"),
                           ("Diyarbakir", "TUR"), ("Erbil", "IRQ")):
            self.assertIsNone(flag_url(name, iso3), f"{name} primary")
            self.assertIsNone(flag_url_alt(name, iso3), f"{name} alt")

    def test_curated_pakistan_provinces_stay(self):
        # v8.16 — ALL Pakistani provinces now carry a curated OFFICIAL flag
        # (the provincial-government flags, never separatist ones)
        for name in ("Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan",
                     "Gilgit-Baltistan", "Azad Kashmir"):
            self.assertIsNotNone(flag_url(name, "PAK"), f"PAK {name} is curated")

    def test_russia_subjects_curated(self):
        # v8.16.1 — Russia's federal subjects were the blind-guess casualty
        # (owner: "buryatia no flag … jewish AR no flag"). Every subject is now
        # mapped to its canonical Commons filename by its EXACT atlas name.
        cases = {
            ("Republic of Buryatia", "RUS"): "Flag%20of%20Buryatia.svg",
            ("Jewish", "RUS"): "Jewish%20Autonomous%20Oblast",
            ("Amur", "RUS"): "Amur%20Oblast",
            ("Chechen Republic", "RUS"): "Chechen%20Republic",
            ("Republic of Tatarstan", "RUS"): "Flag%20of%20Tatarstan.svg",
        }
        for (name, iso3), frag in cases.items():
            url = flag_url(name, iso3)
            self.assertIsNotNone(url, f"{name} should be curated")
            self.assertIn("Special:FilePath", url)
            self.assertIn(frag, url, f"{name} -> {frag}")
            # alt (CDN thumb) exists exactly where the primary does
            self.assertIsNotNone(flag_url_alt(name, iso3), f"{name} alt")

    def test_georgia_collision_uses_us_state_file(self):
        # "Georgia" the US state must NEVER resolve to the sovereign's flag.
        url = flag_url("Georgia", "USA") or ""
        self.assertIn("U.S.%20state", url.replace("_", "%20"))

    def test_alt_tracks_primary_nullness(self):
        # Chain invariant: alt exists exactly where primary does.
        for name, iso3 in (("Bavaria", "DEU"), ("California", "USA"),
                           ("Telangana", "IND")):
            self.assertEqual(flag_url(name, iso3) is None,
                             flag_url_alt(name, iso3) is None, name)


if __name__ == "__main__":
    unittest.main()
