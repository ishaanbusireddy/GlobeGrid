"""Gazetteer + geo math (v1 Section 5.2/5.4; upgraded per v2 addendum §10).

v2: geocode_text() now resolves against the gazetteer_places SQLite table
(GeoNames cities15000-scale, ~32k places, imported from the vendored TSV
by scripts/import_gazetteer.py — Geocoding data © GeoNames, CC BY 4.0).
The built-in PLACES dict below remains the authority for country/region
names (the cities dataset has no country entries) and the fallback if the
table hasn't been imported. Function signature is unchanged, so nothing
else in the extraction pipeline had to change (§10.1).

Matching: candidate spans are extracted from the text (capitalized word
runs and prepositional phrases), then looked up exactly against
ascii_name/aliases; multiple candidates sharing a name are disambiguated
by population (§10.1). Countries rank with a synthetic 10M population so
a megacity mention outranks its country, but a country mention beats
same-named small towns.
"""

import math
import re
import unicodedata
from functools import lru_cache

# name -> (lat, lon). Countries use a representative point (capital).
PLACES = {
    # --- countries / regions ---
    "afghanistan": (34.5, 69.2), "albania": (41.3, 19.8), "algeria": (36.8, 3.1),
    "argentina": (-34.6, -58.4), "armenia": (40.2, 44.5), "australia": (-35.3, 149.1),
    "austria": (48.2, 16.4), "azerbaijan": (40.4, 49.9), "bangladesh": (23.8, 90.4),
    "belarus": (53.9, 27.6), "belgium": (50.8, 4.4), "bolivia": (-16.5, -68.1),
    "bosnia": (43.9, 18.4), "brazil": (-15.8, -47.9), "bulgaria": (42.7, 23.3),
    "myanmar": (19.7, 96.1), "burma": (19.7, 96.1), "cambodia": (11.6, 104.9),
    "cameroon": (3.9, 11.5), "canada": (45.4, -75.7), "chad": (12.1, 15.0),
    "chile": (-33.4, -70.7), "china": (39.9, 116.4), "colombia": (4.7, -74.1),
    "congo": (-4.3, 15.3), "costa rica": (9.9, -84.1), "croatia": (45.8, 16.0),
    "cuba": (23.1, -82.4), "cyprus": (35.2, 33.4), "czech republic": (50.1, 14.4),
    "denmark": (55.7, 12.6), "dominican republic": (18.5, -69.9),
    "ecuador": (-0.2, -78.5), "egypt": (30.0, 31.2), "el salvador": (13.7, -89.2),
    "eritrea": (15.3, 38.9), "estonia": (59.4, 24.8), "ethiopia": (9.0, 38.7),
    "finland": (60.2, 24.9), "france": (48.9, 2.4), "georgia": (41.7, 44.8),
    "germany": (52.5, 13.4), "ghana": (5.6, -0.2), "greece": (38.0, 23.7),
    "guatemala": (14.6, -90.5), "haiti": (18.5, -72.3), "honduras": (14.1, -87.2),
    "hungary": (47.5, 19.0), "iceland": (64.1, -21.9), "india": (28.6, 77.2),
    "indonesia": (-6.2, 106.8), "iran": (35.7, 51.4), "iraq": (33.3, 44.4),
    "ireland": (53.3, -6.3), "israel": (31.8, 35.2), "italy": (41.9, 12.5),
    "ivory coast": (5.3, -4.0), "jamaica": (18.0, -76.8), "japan": (35.7, 139.7),
    "jordan": (31.9, 35.9), "kazakhstan": (51.2, 71.4), "kenya": (-1.3, 36.8),
    "north korea": (39.0, 125.8), "south korea": (37.6, 127.0), "kosovo": (42.7, 21.2),
    "kuwait": (29.4, 48.0), "kyrgyzstan": (42.9, 74.6), "laos": (17.976, 102.6),
    "latvia": (56.9, 24.1), "lebanon": (33.9, 35.5), "libya": (32.9, 13.2),
    "lithuania": (54.7, 25.3), "luxembourg": (49.6, 6.1), "madagascar": (-18.9, 47.5),
    "malawi": (-13.96, 33.8), "malaysia": (3.1, 101.7), "mali": (12.6, -8.0),
    "malta": (35.9, 14.5), "mexico": (19.4, -99.1), "moldova": (47.0, 28.9),
    "mongolia": (47.9, 106.9), "montenegro": (42.4, 19.3), "morocco": (34.0, -6.8),
    "mozambique": (-25.9, 32.6), "namibia": (-22.6, 17.1), "nepal": (27.7, 85.3),
    "netherlands": (52.4, 4.9), "new zealand": (-41.3, 174.8), "nicaragua": (12.1, -86.3),
    "niger": (13.5, 2.1), "nigeria": (9.1, 7.5), "north macedonia": (42.0, 21.4),
    "norway": (59.9, 10.8), "oman": (23.6, 58.5), "pakistan": (33.7, 73.1),
    "palestine": (31.9, 35.2), "gaza": (31.5, 34.5), "panama": (9.0, -79.5),
    "papua new guinea": (-9.4, 147.2), "paraguay": (-25.3, -57.6), "peru": (-12.0, -77.0),
    "philippines": (14.6, 121.0), "poland": (52.2, 21.0), "portugal": (38.7, -9.1),
    "qatar": (25.3, 51.5), "romania": (44.4, 26.1), "russia": (55.8, 37.6),
    "rwanda": (-1.9, 30.1), "saudi arabia": (24.7, 46.7), "senegal": (14.7, -17.5),
    "serbia": (44.8, 20.5), "sierra leone": (8.5, -13.2), "singapore": (1.4, 103.8),
    "slovakia": (48.1, 17.1), "slovenia": (46.1, 14.5), "somalia": (2.0, 45.3),
    "south africa": (-25.7, 28.2), "south sudan": (4.9, 31.6), "spain": (40.4, -3.7),
    "sri lanka": (6.9, 79.9), "sudan": (15.6, 32.5), "sweden": (59.3, 18.1),
    "switzerland": (46.9, 7.4), "syria": (33.5, 36.3), "taiwan": (25.0, 121.6),
    "tajikistan": (38.6, 68.8), "tanzania": (-6.8, 39.3), "thailand": (13.8, 100.5),
    "tunisia": (36.8, 10.2), "turkey": (39.9, 32.9), "turkmenistan": (37.9, 58.4),
    "uganda": (0.3, 32.6), "ukraine": (50.5, 30.5), "united arab emirates": (24.5, 54.4),
    "united kingdom": (51.5, -0.1), "britain": (51.5, -0.1), "uk": (51.5, -0.1),
    "united states": (38.9, -77.0), "us": (38.9, -77.0), "usa": (38.9, -77.0),
    "uruguay": (-34.9, -56.2), "uzbekistan": (41.3, 69.3), "venezuela": (10.5, -66.9),
    "vietnam": (21.0, 105.9), "yemen": (15.4, 44.2), "zambia": (-15.4, 28.3),
    "zimbabwe": (-17.8, 31.1),
    # --- major cities / population centers ---
    "kabul": (34.5, 69.2), "tokyo": (35.7, 139.7), "delhi": (28.6, 77.2),
    "new delhi": (28.6, 77.2), "shanghai": (31.2, 121.5), "sao paulo": (-23.6, -46.6),
    "mumbai": (19.1, 72.9), "beijing": (39.9, 116.4), "cairo": (30.0, 31.2),
    "dhaka": (23.8, 90.4), "osaka": (34.7, 135.5), "karachi": (24.9, 67.0),
    "istanbul": (41.0, 28.9), "buenos aires": (-34.6, -58.4), "kolkata": (22.6, 88.4),
    "lagos": (6.5, 3.4), "manila": (14.6, 121.0), "rio de janeiro": (-22.9, -43.2),
    "guangzhou": (23.1, 113.3), "moscow": (55.8, 37.6), "los angeles": (34.1, -118.2),
    "paris": (48.9, 2.4), "jakarta": (-6.2, 106.8), "bangkok": (13.8, 100.5),
    "seoul": (37.6, 127.0), "nagoya": (35.2, 136.9), "lima": (-12.0, -77.0),
    "london": (51.5, -0.1), "tehran": (35.7, 51.4), "chennai": (13.1, 80.3),
    "bogota": (4.7, -74.1), "new york": (40.7, -74.0), "washington": (38.9, -77.0),
    "chicago": (41.9, -87.6), "houston": (29.8, -95.4), "san francisco": (37.8, -122.4),
    "lahore": (31.5, 74.3), "shenzhen": (22.5, 114.1), "bangalore": (13.0, 77.6),
    "ho chi minh city": (10.8, 106.7), "hyderabad": (17.4, 78.5), "hong kong": (22.3, 114.2),
    "baghdad": (33.3, 44.4), "riyadh": (24.7, 46.7), "santiago": (-33.4, -70.7),
    "madrid": (40.4, -3.7), "toronto": (43.7, -79.4), "johannesburg": (-26.2, 28.0),
    "berlin": (52.5, 13.4), "kyiv": (50.5, 30.5), "kiev": (50.5, 30.5),
    "rome": (41.9, 12.5), "geneva": (46.2, 6.1), "brussels": (50.8, 4.4),
    "vienna": (48.2, 16.4), "athens": (38.0, 23.7), "dubai": (25.2, 55.3),
    "tel aviv": (32.1, 34.8), "jerusalem": (31.8, 35.2), "damascus": (33.5, 36.3),
    "beirut": (33.9, 35.5), "amman": (31.9, 35.9), "ankara": (39.9, 32.9),
    "nairobi": (-1.3, 36.8), "addis ababa": (9.0, 38.7), "khartoum": (15.6, 32.5),
    "casablanca": (33.6, -7.6), "accra": (5.6, -0.2), "abuja": (9.1, 7.5),
    "kinshasa": (-4.3, 15.3), "dakar": (14.7, -17.5), "mexico city": (19.4, -99.1),
    "havana": (23.1, -82.4), "caracas": (10.5, -66.9), "sydney": (-33.9, 151.2),
    "melbourne": (-37.8, 145.0), "auckland": (-36.8, 174.8), "wellington": (-41.3, 174.8),
    "taipei": (25.0, 121.6), "pyongyang": (39.0, 125.8), "hanoi": (21.0, 105.9),
    "islamabad": (33.7, 73.1), "colombo": (6.9, 79.9), "kathmandu": (27.7, 85.3),
    "tashkent": (41.3, 69.3), "almaty": (43.2, 76.9), "minsk": (53.9, 27.6),
    "warsaw": (52.2, 21.0), "prague": (50.1, 14.4), "budapest": (47.5, 19.0),
    "bucharest": (44.4, 26.1), "belgrade": (44.8, 20.5), "sofia": (42.7, 23.3),
    "helsinki": (60.2, 24.9), "stockholm": (59.3, 18.1), "oslo": (59.9, 10.8),
    "copenhagen": (55.7, 12.6), "amsterdam": (52.4, 4.9), "lisbon": (38.7, -9.1),
    "dublin": (53.3, -6.3), "edinburgh": (56.0, -3.2), "zurich": (47.4, 8.5),
}

# Longest names first so "south korea" beats "korea"-less scans, "new york"
# beats "york", etc.
_SORTED_NAMES = sorted(PLACES.keys(), key=len, reverse=True)
_PATTERNS = {name: re.compile(r"\b" + re.escape(name) + r"\b") for name in _SORTED_NAMES}

COUNTRY_RANK_POPULATION = 10_000_000  # §10.1 disambiguation weight for countries

_CANDIDATE_RE = re.compile(
    r"\b(?:in|near|at|outside|across|from)\s+([A-Z][\w'’.-]+(?:\s+[A-Z][\w'’.-]+){0,2})"
    r"|\b([A-Z][\w'’.-]+(?:\s+[A-Z][\w'’.-]+){0,2})")


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


# v7 — common English words that are ALSO city names somewhere on Earth
# ("Central" LA, "Mobile" AL, "Split" HR, "Nice" FR, "Reading" UK, "Most" CZ,
# "Bath" UK, "Deal" UK, "Sale" AUS, "Along" IN, "Date" JP, "Media" PA, ...).
# A single ambiguous word never geocodes an event on its own — it's how
# "Central bank holds rates steady" pinned to Central, Louisiana and finance
# copy pooled events at random cities. Multi-word spans ("Nice, France") and
# datelines still resolve normally.
AMBIGUOUS_SINGLE = frozenset(
    "central mobile split nice most bath deal sale reading along date media "
    "normal surprise commerce enterprise industry price march best close hit "
    "man bar of many crane eagle liberty union orange golden pen "
    "same rally front".split())

# v7.3 — a lone capitalized token matching a tiny place is almost always a
# name-fragment collision (e.g. "Le Pen" → Pen, a ~30k town near Mumbai), not
# the story's real location; single-word body matches must clear this bar.
# Datelines (step 1) and multi-word place names bypass it entirely.
SINGLE_TOKEN_MIN_POP = 100000


def _candidate_spans(text: str) -> list[str]:
    """Capitalized 1-3 word runs plus their sub-spans, order-preserving."""
    seen, out = set(), []
    for m in _CANDIDATE_RE.finditer(text or ""):
        span = (m.group(1) or m.group(2) or "").strip(" .,'’-")
        if not span:
            continue
        words = span.split()
        subs = [" ".join(words[i:j]) for i in range(len(words))
                for j in range(len(words), i, -1)]
        for sub in subs:
            key = sub.lower()
            if len(sub) >= 3 and key not in seen:
                seen.add(key)
                out.append(sub)
        if len(out) > 24:
            break
    return out


def _gazetteer_ready() -> bool:
    try:
        from ..db.session import query_one
        row = query_one("SELECT COUNT(*) AS n FROM gazetteer_places LIMIT 1")
        return bool(row and row["n"])
    except Exception:  # noqa: BLE001 — table absent pre-migration
        return False


@lru_cache(maxsize=4096)
def _lookup_place(name_lower: str):
    """Best gazetteer_places hit for one candidate span (population-ranked)."""
    from ..db.session import query_one
    row = query_one(
        "SELECT name, lat, lon, population FROM gazetteer_places"
        " WHERE ascii_name = ? COLLATE NOCASE OR name = ? COLLATE NOCASE"
        " ORDER BY population DESC LIMIT 1", (name_lower, name_lower))
    if row is None:
        row = query_one(
            "SELECT p.name, p.lat, p.lon, p.population FROM gazetteer_aliases a"
            " JOIN gazetteer_places p ON p.id = a.place_id"
            " WHERE a.alias = ? COLLATE NOCASE ORDER BY p.population DESC LIMIT 1",
            (name_lower,))
    return (row["name"], row["lat"], row["lon"], row["population"]) if row else None


def _dict_geocode(text: str):
    lowered = (text or "").lower()
    for name in _SORTED_NAMES:
        if name in lowered and _PATTERNS[name].search(lowered):
            lat, lon = PLACES[name]
            return name.title(), lat, lon
    return None


# v6 §25 — dateline pattern: "TEHRAN — ..." / "Kyiv (Reuters) - ..." at the
# very start of the text. An explicit dateline is the article's own statement
# of where the story happened; it outranks every incidental mention.
_DATELINE = re.compile(
    r"^\s*([A-Za-z][A-Za-z .'’-]{2,28}?)(?:,\s*[A-Za-z .]{2,24})?"
    r"\s*(?:\([A-Za-z /.]+\))?\s*[—–-]{1,2}\s+")


def geocode_text(text: str):
    """Return (place_name, lat, lon) for the best-ranked place mentioned in
    the text, or None. Signature unchanged from v1 (§10.1).

    v6 §25 location precision: an explicit DATELINE wins outright; without
    one, the FIRST explicit place mention in the text outranks later ones
    (population only breaks near-ties) — never any-match-wins, which is how
    a Tehran funeral story ended up geocoded to Delhi off an incidental
    mention deeper in the body."""
    if not text:
        return None
    if not _gazetteer_ready():
        return _dict_geocode(text)

    # 1. dateline beats everything
    m = _DATELINE.match(text)
    if m:
        span = m.group(1).strip()
        hit = _lookup_place(_ascii(span).lower())
        if hit:
            return (hit[0], hit[1], hit[2])
        low = span.lower()
        if low in PLACES:
            lat, lon = PLACES[low]
            return (span.title(), lat, lon)

    # 2. no dateline: collect candidates WITH their text positions
    lowered = text.lower()
    candidates = []  # (position, -population, name, lat, lon)
    for name in _SORTED_NAMES:
        if name in lowered and _PATTERNS[name].search(lowered):
            lat, lon = PLACES[name]
            candidates.append((lowered.find(name), -COUNTRY_RANK_POPULATION,
                               name.title(), lat, lon))
    for span in _candidate_spans(text):
        low_span = _ascii(span).lower()
        # v7 — a lone common-English word can't geocode a story by itself
        if " " not in low_span and low_span in AMBIGUOUS_SINGLE:
            continue
        hit = _lookup_place(low_span)
        # v7.3 — a LONE capitalized token that resolves to a tiny place is
        # almost always a name-fragment collision, not the story's location
        # (owner: "Le Pen" → "Pen", a 30k-pop town near Mumbai, pooled French
        # politics into India). Require a meaningful population for single-word
        # matches; multi-word places and datelines are unaffected.
        if hit and " " not in low_span and (hit[3] or 0) < SINGLE_TOKEN_MIN_POP:
            continue
        if hit:
            pos = lowered.find(span.lower())
            if pos < 0:
                pos = len(lowered)
            candidates.append((pos, -hit[3], hit[0], hit[1], hit[2]))
    if not candidates:
        return None
    # earliest mention first; only IMMEDIATELY adjacent mentions (within ~15
    # chars, e.g. "Tehran, Iran") compete on population — a city 40 chars
    # later is a different mention, not a qualifier of the first
    candidates.sort()
    first_pos = candidates[0][0]
    near = [c for c in candidates if c[0] - first_pos <= 15]
    near.sort(key=lambda c: c[1])   # most-populous of the near-front mentions
    _, _, name, lat, lon = near[0]
    return (name, lat, lon)


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


# ~40 real-world population centers used by scripts/generate_synthetic_data.py
POPULATION_CENTERS = [
    "tokyo", "delhi", "shanghai", "sao paulo", "mumbai", "beijing", "cairo",
    "dhaka", "karachi", "istanbul", "buenos aires", "lagos", "manila",
    "rio de janeiro", "moscow", "los angeles", "paris", "jakarta", "bangkok",
    "seoul", "lima", "london", "tehran", "bogota", "new york", "chicago",
    "lahore", "hong kong", "baghdad", "riyadh", "santiago", "madrid",
    "toronto", "johannesburg", "berlin", "kyiv", "nairobi", "mexico city",
    "sydney", "singapore",
]
