#!/usr/bin/env python3
"""Roadmap Update 3 §3.5 Layer 2 — the REAL-MODEL translation gate.

This is the step every prior translation attempt (v6.6.8 → v6.6.12) skipped,
and its absence is the single reason five "verified" releases were each
broken on the owner's machine. Run it on the machine with a reachable model
(local Ollama, or a configured cloud key):

    python scripts/verify_translation_live.py            # fr, es, sq
    python scripts/verify_translation_live.py de ja ar   # your choice

It translates a fixed 30-string set — short labels plus one long paragraph,
deliberately including the exact welcome-popup text class that broke
v6.6.11 — into each target language against the REAL configured model,
prints every raw reply and parsed result for human review, and exits
non-zero if anything fell back to English (printing exactly which strings
and why — never a silent pass).

Until this script has passed on a real model, the feature is
"built and simulator-tested", NOT "verified" — that distinction is the whole
lesson of the v6.6.x history.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.processing import i18n2, llm  # noqa: E402

# 30 strings: real UI labels, chip text, one long welcome-popup paragraph
# (the v6.6.11 breaker class), sentences with $ (the String.replace hazard),
# and proper nouns that legitimately survive translation unchanged.
FIXED_SET = [
    "Live feed", "Settings", "Conflicts", "Stories", "Sources",
    "War Mode", "Breaking news", "Instability index", "Map modes",
    "Political parties", "Recent tracked coverage", "Border & sovereignty history",
    "Show all events", "Pan to this area", "Connecting to the live feed…",
    "How to navigate the globe", "Rotate the globe by dragging; scroll to zoom.",
    "Press Escape to close one layer at a time.",
    "This unit's own figures", "Estimated figures — derived, not a recorded census figure",
    "Oil prices rose 4% to $92 per barrel after the announcement.",
    "The ceasefire collapsed within hours as artillery fire resumed.",
    "NATO", "Iraqi Kurdistan", "United Nations Security Council",
    "No AI provider configured — add a free key or run Ollama.",
    "Every event you see links back to a resolvable public source.",
    "Welcome to GlobeGrid — a real-time global event intelligence system. "
    "It ingests news wires, earthquake sensors and market data, extracts "
    "who-what-where-when facts into a permanent chain, and correlates events "
    "across streams and across time to build causal storylines you can "
    "explore on the globe. Nothing you see is invented: every card links "
    "back to its sources, and figures that are estimates are always "
    "labelled as estimates.",
    "Severity", "Confidence",
]


def main(langs: list[str]) -> int:
    if not llm.available():
        print("✗ No AI provider reachable (llm.available() = False).")
        print("  Start Ollama (`ollama serve` + `ollama pull llama3.1`) or add a")
        print("  cloud key, then re-run. This script exists precisely because a")
        print("  simulator pass is NOT a verification — do not skip it.")
        return 2
    overall_fail = 0
    for lang in langs:
        print("=" * 72)
        print(f"TARGET LANGUAGE: {lang}")
        print("=" * 72)
        # v8.15.1 — translate_strings now works in budgeted slices (the
        # `deferred` list), exactly like the frontend's progressive fill.
        # Loop until nothing is deferred: successes are cached, so each round
        # only spends model time on the remainder.
        res = i18n2.translate_strings(lang, FIXED_SET, interactive=True)
        rounds = 1
        while res["deferred"] and rounds < 30:
            res = i18n2.translate_strings(lang, FIXED_SET, interactive=True)
            rounds += 1
        if res["deferred"]:
            print(f"✗ {lang}: {len(res['deferred'])} strings STILL deferred "
                  f"after {rounds} rounds — the model may be unreachable or "
                  "pathologically slow.")
            overall_fail += len(res["deferred"])
        deferred_left = set(res["deferred"])
        for i, (src, dst) in enumerate(zip(FIXED_SET, res["translations"])):
            if i in res["untranslated"]:
                mark = "✗ ENGLISH (attempted, model failed)"
            elif i in deferred_left:
                mark = "✗ DEFERRED (never attempted — gate/budget)"
            else:
                mark = "✓"
            print(f"[{i:02d}] {mark}")
            print(f"     EN: {src[:100]}")
            print(f"     {lang}: {dst[:100]}")
        n_fail = len(res["untranslated"])
        if n_fail:
            print(f"\n✗ {lang}: {n_fail}/{len(FIXED_SET)} strings fell back to "
                  f"English (indices {res['untranslated']}).")
            print(f"  Last provider error: {llm.last_error()}")
            print("  Paste this whole output into an issue — with the raw "
                  "diagnostics at GET /api/i18n/diagnostics it contains "
                  "everything needed.")
            overall_fail += n_fail
        elif not deferred_left:
            print(f"\n✓ {lang}: all {len(FIXED_SET)} strings translated.")
    print("=" * 72)
    if overall_fail:
        print(f"RESULT: FAIL — {overall_fail} total fallbacks. The feature is "
              "NOT verified on this machine.")
        return 1
    print("RESULT: PASS — a real model translated the full fixed set. This is "
          "the Phase-B gate the changelog can cite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["fr", "es", "sq"]))
