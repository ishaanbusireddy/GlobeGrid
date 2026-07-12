"""Event categorization on a labelled set (the v8.13.0 taxonomy: 8 categories
incl. technology / domestic / health, word-boundary keywords, fixed priority
tie-break). These are behavioural pins — if a keyword-table edit flips one of
these, that's a regression the owner reported before (v6.6 "nothing classifies
as technology"; v7.4.1 "war" ≠ "warning")."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.processing.extract import classify_category, classify_severity  # noqa: E402

LABELLED = [
    ("Nvidia earnings jump on surging AI demand", "technology"),
    ("Magnitude 7.1 earthquake strikes off Japan, tsunami warning issued", "disaster"),
    ("Artillery fire resumes on the front line as ceasefire collapses", "conflict"),
    ("Central bank raises interest rates to combat stubborn inflation", "finance"),
    ("Foreign ministers sign bilateral treaty at United Nations summit", "geopolitics"),
    ("Cholera outbreak spreads in refugee camps, WHO declares emergency", "health"),
    ("Supreme court verdict sparks nationwide protests over corruption scandal", "domestic"),
    ("Hurricane makes landfall, widespread flooding reported", "disaster"),
    # word-boundary rule: "war" must NOT hit inside "warning" (→ not conflict)
    ("Government issues warning about severe weather", "other"),
    ("Couple celebrates anniversary at local supermarket opening", "other"),  # "coup"≠"couple"
]


class TestClassify(unittest.TestCase):
    def test_labelled_set(self):
        for text, want in LABELLED:
            got = classify_category(text)
            self.assertEqual(got, want, f"{text!r} → {got}, wanted {want}")

    def test_severity_monotonic_bounds(self):
        self.assertIn(classify_severity("routine trade statistics published"), (1, 2))
        self.assertGreaterEqual(
            classify_severity("nuclear strike kills hundreds in massacre"), 4)


if __name__ == "__main__":
    unittest.main()
