"""v8.18 — pins for the classification/threads/predmarkets/map-data fixes.

Covers the pure-logic surface of the v8.18 batch:
  - prediction-market conflict filtering (war-mode odds must be conflict-
    specific, generic conflict words never match, honest empty note)
  - thread topical tokens (the description-as-topic gate's tokenizer)
  - altitude coverage (no seeded country may be blank on the altitude map)
  - Rojava marked historical + dropped from the live zone layer
No DB, no network — same contract as the rest of backend/tests/.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.processing import predmarkets  # noqa: E402
from app.processing.threads import _topic_tokens  # noqa: E402
from app.geopolitics import admin_climate, autonomous_zones  # noqa: E402
from app.geopolitics.seed_data import COUNTRIES  # noqa: E402


def _prime_cache(rows):
    """Fill the predmarkets cache so markets() never hits the network."""
    import time
    predmarkets._CACHE.update(at=time.time(), rows=rows, live=True, error=None)


_ROWS = [
    {"source": "Polymarket", "title": "Will the US strike Iran again in 2026?",
     "yes_price": 0.4, "volume_24h": 900, "url": "u", "ends": None},
    {"source": "Kalshi", "title": "Russia-Ukraine ceasefire by December?",
     "yes_price": 0.2, "volume_24h": 800, "url": "u", "ends": None},
    {"source": "Polymarket", "title": "Will there be a new war in 2026?",
     "yes_price": 0.6, "volume_24h": 700, "url": "u", "ends": None},
]


class TestPredMarketConflictFilter(unittest.TestCase):
    def test_conflict_terms_match_only_that_conflict(self):
        _prime_cache(_ROWS)
        out = predmarkets.markets("U.S.–Iran War United States Iran Israel")
        titles = [m["title"] for m in out["markets"]]
        self.assertTrue(any("Iran" in t for t in titles))
        self.assertFalse(any("Ukraine" in t for t in titles),
                         "an unrelated conflict's market leaked through")
        # the generic "new war" bet must NOT ride in on the word "war"
        self.assertFalse(any("new war" in t for t in titles))

    def test_generic_words_never_match(self):
        _prime_cache(_ROWS)
        out = predmarkets.markets("war conflict crisis ceasefire")
        self.assertEqual(out["markets"], [])
        self.assertIn("distinctive", out["note"].lower())

    def test_no_match_is_honest_not_random(self):
        _prime_cache(_ROWS)
        out = predmarkets.markets("Bougainville Papua Guinea")
        self.assertEqual(out["markets"], [])
        self.assertIn("no conflict-specific", out["note"].lower())

    def test_unfiltered_feed_unchanged(self):
        _prime_cache(_ROWS)
        out = predmarkets.markets(None)
        self.assertEqual(len(out["markets"]), 3)


class TestThreadTopicTokens(unittest.TestCase):
    def test_specific_names_survive_generic_words_dropped(self):
        toks = _topic_tokens("US-Turkey Relations",
                             "Ongoing thread grouping tracked stories.")
        self.assertIn("turkey", toks)
        # generic filler must not become topic signature
        for generic in ("relations", "ongoing", "thread", "stories"):
            self.assertNotIn(generic, toks)

    def test_iran_headline_does_not_hit_turkey_topic(self):
        topic = _topic_tokens("US-Turkey Relations")
        headline = _topic_tokens("Iran vows response after strikes on nuclear sites")
        self.assertFalse(headline & topic,
                         "an Iran headline must share no topic token with a "
                         "US-Turkey thread")


class TestAltitudeCoverage(unittest.TestCase):
    def test_every_country_has_an_elevation(self):
        blanks = [row[0] for row in COUNTRIES
                  if admin_climate.country_elevation(row[0]) is None]
        self.assertEqual(blanks, [], f"countries blank on altitude map: {blanks}")

    def test_curated_beats_fallback(self):
        # Nepal's curated 3265m must survive the fallback addition
        self.assertEqual(admin_climate.country_elevation("NPL"), 3265)


class TestZonesHistorical(unittest.TestCase):
    def test_rojava_flagged_historical(self):
        z = autonomous_zones.zone_by_id("rojava")
        self.assertIsNotNone(z)
        self.assertTrue(z["historical"])

    def test_live_layer_excludes_historical(self):
        live_ids = {z["id"] for z in autonomous_zones.zones_list(include_historical=False)}
        self.assertNotIn("rojava", live_ids)
        self.assertIn("iraqi_kurdistan", live_ids)
        # the full directory still lists it (page kept, flagged)
        all_ids = {z["id"] for z in autonomous_zones.zones_list()}
        self.assertIn("rojava", all_ids)


if __name__ == "__main__":
    unittest.main()
