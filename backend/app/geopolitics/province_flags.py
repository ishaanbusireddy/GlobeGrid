"""V8.1 — provincial flags (with generated-seal fallback).

The owner: "add provincial flags or seals (if no flag) for every province."

We can't reach Wikidata from the build sandbox, so — exactly like the country
flags (seed._flag_url) — we CONSTRUCT a Wikimedia Commons Special:FilePath URL
from the unit name and let the user's BROWSER load it. Commons' de-facto naming
for first-level subdivisions is "Flag of {name}.svg", which resolves for a large
fraction (US states, German Länder, Indian states, …). When it 404s, the
frontend swaps in a deterministic generated SEAL (a monogram emblem), so EVERY
unit has a crest — flag where one exists, seal otherwise.

Two correctness guards:
  - COLLISION_BLOCK: subdivision names that equal a sovereign country (Georgia,
    Luxembourg, …) — a blind "Flag of {name}.svg" there would load the COUNTRY's
    flag, so we suppress the guess (→ seal) unless we have a curated correct URL.
  - CURATED: hand-verified correct filenames for the notable collisions.
"""
import urllib.parse

_BASE = "https://commons.wikimedia.org/wiki/Special:FilePath/{f}?width=160"

# (name, iso3) -> exact Commons filename (no path), for known collisions where
# the plain "Flag of {name}.svg" guess would resolve to the wrong entity.
CURATED = {
    ("Georgia", "USA"): "Flag of Georgia (U.S. state).svg",
    ("Punjab", "IND"): "Flag of Punjab, India.svg",
    ("Punjab", "PAK"): "Flag of Punjab (Pakistan).svg",
    ("Washington", "USA"): "Flag of Washington.svg",
    ("New York", "USA"): "Flag of New York (1901–2020).svg",
}

# Subdivision names that collide with a sovereign state name — suppress the blind
# guess (fall through to a generated seal) unless CURATED has an entry.
COLLISION_BLOCK = {
    "georgia", "luxembourg", "jersey", "guernsey", "monaco", "san marino",
    "malta", "singapore", "kuwait", "qatar", "bahrain", "brunei",
}


def flag_url(name, iso3, iso2=None):
    """Best-effort flag image URL for an administrative unit, or None to signal
    the frontend to draw a generated seal instead."""
    if not name:
        return None
    key = (name.strip(), (iso3 or "").upper())
    if key in CURATED:
        return _BASE.format(f=urllib.parse.quote(CURATED[key]))
    if name.strip().lower() in COLLISION_BLOCK:
        return None
    fname = urllib.parse.quote(f"Flag of {name.strip()}.svg")
    return _BASE.format(f=fname)
