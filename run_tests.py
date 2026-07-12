#!/usr/bin/env python3
"""v8.14 — run GlobeGrid's smoke-test suite (backend/tests/, pure stdlib).

Usage:  python run_tests.py            # whole suite
        python run_tests.py classify   # only test files matching a substring

Zero installs, same as the app itself. Exits non-zero on any failure so it
slots straight into a pre-commit hook or CI step.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent


def main() -> int:
    pattern = "test_*.py"
    if len(sys.argv) > 1:
        pattern = f"test_*{sys.argv[1]}*.py"
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(REPO / "backend" / "tests"),
        pattern=pattern,
        top_level_dir=str(REPO / "backend"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
