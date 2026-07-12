"""Roadmap Update 3 §3.5 Layer 1 — protocol-conformance tests against an
ADVERSARIAL simulator (necessary, NOT sufficient — the real-model gate is
scripts/verify_translation_live.py, run by a human against a real Ollama).

The simulator wraps a deterministic lexicon (never an echo server) and then
randomly perturbs its own replies per call with every failure mode from the
§3.1 retrospective table: JSON-shape replies despite plain-text prompting,
raw newlines inside long strings, dropped numbered lines, and English echoes.
Seeded RNG so the run is reproducible. Asserts BOTH bars from the spec:
  - ≥98% of individual strings end up exactly translated over 200 randomized
    calls (batch retry + straggler retry doing their jobs), and
  - ZERO multi-word strings are silently reported as translated while
    actually still being the English source (the honesty guarantee,
    checked programmatically — the v6.6.10 silent-passthrough class).
"""
import random
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.processing import i18n2  # noqa: E402


def _fake_translate(s: str, lang: str) -> str:
    # deterministic, checkable, never equal to the source
    return f"[{lang}] {s[::-1]}"


class AdversarialSimulator:
    """Stands in for llm.complete. Parses the numbered user message exactly
    like a model would see it, translates via the lexicon function, then
    perturbs its own reply per the §3.5 failure-mode table."""

    def __init__(self, lang: str, seed: int = 42):
        self.lang = lang
        self.rng = random.Random(seed)
        self.calls = 0

    def __call__(self, system, messages, max_tokens=0, timeout=0,
                 json_mode=False, interactive=False, prefer=None):
        assert json_mode is False, "protocol violation: json_mode must NEVER be used"
        self.calls += 1
        user = messages[0]["content"]
        items = re.findall(r"^(\d+)\.\s+(.*)$", user, re.MULTILINE)
        pairs = [(int(n), _fake_translate(s, self.lang)) for n, s in items]
        roll = self.rng.random()
        if roll < 0.05 and pairs:
            # JSON-object reply despite plain-text instructions
            body = ", ".join(f'"{n}": "{t}"' for n, t in pairs)
            return "{" + body + "}"
        if roll < 0.10 and pairs:
            # raw newline injected into one translated string
            k = self.rng.randrange(len(pairs))
            n, t = pairs[k]
            mid = max(1, len(t) // 2)
            pairs[k] = (n, t[:mid] + "\n" + t[mid:])
        elif roll < 0.15 and len(pairs) > 1:
            # one numbered line dropped entirely
            del pairs[self.rng.randrange(len(pairs))]
        elif roll < 0.20 and pairs:
            # English echoed back for one line (the v6.6.12 failure mode)
            k = self.rng.randrange(len(pairs))
            src = items[k][1] if k < len(items) else ""
            pairs[k] = (pairs[k][0], src)
        return "\n".join(f"{n}. {t}" for n, t in pairs)


class _MemCache(dict):
    def get_(self, key, default=None):
        return dict.get(self, key, default)


class TestAdversarialRuns(unittest.TestCase):
    def _patched(self, sim):
        cache = {}
        orig = (i18n2.llm.complete, i18n2.meta_get, i18n2.meta_set)
        i18n2.llm.complete = sim
        i18n2.meta_get = lambda k, d=None: cache.get(k, d)
        i18n2.meta_set = lambda k, v: cache.__setitem__(k, v)
        return orig, cache

    def _restore(self, orig):
        i18n2.llm.complete, i18n2.meta_get, i18n2.meta_set = orig

    def test_200_randomized_calls(self):
        sim = AdversarialSimulator("fr", seed=42)
        orig, _cache = self._patched(sim)
        try:
            total = correct = 0
            honesty_violations = []
            for call in range(200):
                texts = [f"the quick brown fox jumps over case {call} item {j}"
                         for j in range(8)]
                res = i18n2.translate_strings("fr", texts)
                for j, (src, dst) in enumerate(zip(texts, res["translations"])):
                    total += 1
                    if dst == _fake_translate(src, "fr"):
                        correct += 1
                    # honesty: a multi-word string that is STILL the English
                    # source must be listed in `untranslated` — never silent
                    if dst == src and j not in res["untranslated"]:
                        honesty_violations.append((call, j))
            rate = correct / total
            self.assertGreaterEqual(
                rate, 0.98,
                f"only {rate:.3%} of {total} strings translated correctly")
            self.assertEqual(honesty_violations, [],
                             "silent English passthrough reported as success")
        finally:
            self._restore(orig)

    def test_no_provider_reports_everything_untranslated(self):
        orig, _ = self._patched(lambda *a, **k: None)
        try:
            res = i18n2.translate_strings("fr", ["one two three", "four five six"])
            self.assertEqual(res["translations"], ["one two three", "four five six"])
            self.assertEqual(res["untranslated"], [0, 1])
        finally:
            self._restore(orig)

    def test_failures_are_never_cached(self):
        orig, cache = self._patched(lambda *a, **k: None)
        try:
            i18n2.translate_strings("fr", ["hello there world"])
            self.assertEqual(cache, {}, "an untranslated string was cached")
        finally:
            self._restore(orig)

    def test_cache_hit_short_circuits_llm(self):
        calls = []
        sim = AdversarialSimulator("fr", seed=7)

        def counting(*a, **k):
            calls.append(1)
            return sim(*a, **k)
        orig, _cache = self._patched(counting)
        try:
            i18n2.translate_strings("fr", ["a stable cached sentence here"])
            n1 = len(calls)
            i18n2.translate_strings("fr", ["a stable cached sentence here"])
            self.assertEqual(len(calls), n1, "cache hit still called the LLM")
        finally:
            self._restore(orig)


class TestParser(unittest.TestCase):
    def test_numbering_styles(self):
        for style in ("1. Bonjour\n2. Monde", "1) Bonjour\n2) Monde",
                      "1: Bonjour\n2: Monde", "1 - Bonjour\n2 - Monde"):
            p = i18n2.parse_reply(style, 2)
            self.assertEqual(p, {1: "Bonjour", 2: "Monde"}, style)

    def test_preamble_fence_and_quotes(self):
        raw = ('Sure, here are the translations:\n```\n1. "Flux en direct"\n'
               "2. Paramètres\n```\nLet me know if you need more!")
        self.assertEqual(i18n2.parse_reply(raw, 2),
                         {1: "Flux en direct", 2: "Paramètres"})

    def test_json_object_reply_salvaged(self):
        raw = '{"1": "Flux en direct", "2": "Param\\u00e8tres"}'
        self.assertEqual(i18n2.parse_reply(raw, 2),
                         {1: "Flux en direct", 2: "Paramètres"})

    def test_broken_line_only_loses_itself(self):
        raw = "1. Un\n???garbage???\n3. Trois"
        self.assertEqual(i18n2.parse_reply(raw, 3), {1: "Un", 3: "Trois"})

    def test_single_unnumbered_reply(self):
        self.assertEqual(i18n2.parse_reply("Conflits", 1), {1: "Conflits"})

    def test_batches_bounded_by_chars_and_count(self):
        long = "x" * 800
        b = i18n2._batches([long, long, long])
        self.assertEqual([len(x) for x in b], [1, 1, 1],
                         "3 long paragraphs must split into 3 batches of 1")
        b = i18n2._batches(["a"] * 45)
        self.assertTrue(all(len(x) <= i18n2.MAX_BATCH_COUNT for x in b))
        self.assertEqual(sum(len(x) for x in b), 45)


if __name__ == "__main__":
    unittest.main()
