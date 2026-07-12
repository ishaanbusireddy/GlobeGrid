"""v8.14 — GlobeGrid's smoke-test suite (Update 1 §1.1).

Pure-stdlib unittest, zero installs (same ground rule as the app). Run from
the repo root with:

    python run_tests.py

Layout:
  test_admin_data.py      curated-table keys resolve against the atlas
                          (SUBNATIONAL / demographics UNITS / _GDP_USD) —
                          the "silently-dead override" bug class (v8.11,
                          reintroduced v8.13.7, caught by this suite)
  test_classify.py        event categorization on a labelled set
  test_province_flags.py  admin-flag URL chain (primary + alt + suppression)
  test_codec.py           polyline encode/decode round-trip
  test_db.py              migration idempotence + write_tx reentrancy +
                          events-category CHECK — each scenario in a fresh
                          SUBPROCESS because config.py reads DATABASE_URL at
                          import time (an in-process env swap can't retarget
                          an already-imported session module)
"""
