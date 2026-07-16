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
import hashlib
import urllib.parse


def _commons_thumb(filename, width=160):
    """Direct Wikimedia CDN thumbnail URL for a Commons file.

    v8.13.7 — the old approach hit `commons.wikimedia.org/wiki/Special:FilePath/…`,
    a 302-REDIRECT endpoint that Wikimedia rate-limits: a country page that lists
    ~50 state chips fires ~50 of those at once, many get throttled → they 404 →
    the frontend fell back to the NATIONAL flag, so states WITH their own flag
    (Wyoming, Bavaria, …) wrongly showed the country flag. The direct upload host
    (`upload.wikimedia.org/.../thumb/{a}/{ab}/{file}/{w}px-{file}.png`, where
    a/ab are the first hex chars of md5(underscored filename)) is the CDN itself —
    no redirect, no throttle, safe to embed in bulk. All our files are .svg, so
    the thumbnail is a rendered PNG."""
    name = filename.replace(" ", "_")
    md5 = hashlib.md5(name.encode("utf-8")).hexdigest()
    enc = urllib.parse.quote(name)
    return ("https://upload.wikimedia.org/wikipedia/commons/thumb/"
            f"{md5[0]}/{md5[0:2]}/{enc}/{width}px-{enc}.png")


# retained for any caller that still wants the (throttled) redirect form
_BASE = "https://commons.wikimedia.org/wiki/Special:FilePath/{f}?width=160"

# (name, iso3) -> exact Commons filename (no path), for known collisions where
# the plain "Flag of {name}.svg" guess would resolve to the wrong entity, AND —
# v8.13.4 — for units inside a NO_SUBDIVISION_FLAGS country that DO have a real
# official flag (checked first, so the country-wide suppression doesn't hide them).
CURATED = {
    ("Georgia", "USA"): "Flag of Georgia (U.S. state).svg",
    ("Washington", "USA"): "Flag of Washington.svg",
    ("New York", "USA"): "Flag of New York (1901–2020).svg",
    # Pakistan — only these provinces carry a genuine official/semi-official flag;
    # the rest (Balochistan, Khyber Pakhtunkhwa, FATA, Islamabad) have none, so
    # they fall through to the national flag rather than a separatist/ethnic guess.
    ("Punjab", "PAK"): "Flag of Punjab (Pakistan).svg",
    ("Sindh", "PAK"): "Flag of Sindh.svg",
    ("Gilgit-Baltistan", "PAK"): "Flag of Gilgit-Baltistan.svg",
    ("Azad Kashmir", "PAK"): "Flag of Azad Kashmir.svg",
    # v8.16 — the remaining Pakistani provinces (owner: "make sure ALL of the
    # pakistani admin divs get their official flags"): the provincial-
    # GOVERNMENT flags, never the ethnic/separatist ones. A 404 (naming drift)
    # degrades to nothing via the standard two-candidate chain — never wrong.
    ("Khyber Pakhtunkhwa", "PAK"): "Flag of Khyber Pakhtunkhwa.svg",
    ("Baluchistan", "PAK"): "Flag of Balochistan, Pakistan.svg",
    ("Balochistan", "PAK"): "Flag of Balochistan, Pakistan.svg",
}

# v8.16.1 — Russia's 85 federal subjects, keyed by the EXACT Natural-Earth atlas
# name (see admin_atlas). Owner report: "some flags show in russia … other times
# don't … buryatia no flag … jewish AR no flag." Root cause: Russia was NOT
# curated and NOT suppressed, so every subject's flag was the blind
# `Flag of {name}.svg` guess — which matches for a few (the atlas name happens
# to equal the Commons filename) and 404s for the rest (Commons uses
# "…Oblast" / "…Republic" / a short endonym the atlas name doesn't carry), and
# a 404 shows NOTHING under the v8.13.9 no-fallback rule. Almost every Russian
# subject DOES have a real official flag, so this maps each to its canonical
# Commons filename. The primary URL (Special:FilePath) FOLLOWS REDIRECTS, so a
# canonical name that is itself a Commons redirect still resolves to the file.
_RUS_SUBJECT_FLAGS = {
    "Altai Republic": "Flag of the Altai Republic.svg",
    "Amur": "Flag of Amur Oblast.svg",
    "Arkhangelsk": "Flag of Arkhangelsk Oblast.svg",
    "Astrakhan": "Flag of Astrakhan Oblast.svg",
    "Autonomous Republic of Crimea": "Flag of Crimea.svg",
    "Bashkortostan": "Flag of Bashkortostan.svg",
    "Belgorod": "Flag of Belgorod Oblast.svg",
    "Bryansk": "Flag of Bryansk Oblast.svg",
    "Chechen Republic": "Flag of the Chechen Republic.svg",
    "Chelyabinsk": "Flag of Chelyabinsk Oblast.svg",
    "Chukotka Autonomous Okrug": "Flag of Chukotka.svg",
    "Chuvash Republic": "Flag of Chuvashia.svg",
    "Irkutsk": "Flag of Irkutsk Oblast.svg",
    "Ivanovo": "Flag of Ivanovo Oblast.svg",
    "Jewish": "Flag of the Jewish Autonomous Oblast.svg",
    "Kabardino-Balkaria": "Flag of Kabardino-Balkaria.svg",
    "Kaliningrad": "Flag of Kaliningrad Oblast.svg",
    "Kaluga": "Flag of Kaluga Oblast.svg",
    "Kamchatka Krai": "Flag of Kamchatka Krai.svg",
    "Karachay-Cherkess Republic": "Flag of Karachay-Cherkessia.svg",
    "Karelia": "Flag of Karelia.svg",
    "Kemerovo": "Flag of Kemerovo Oblast.svg",
    "Khabarovsk Krai": "Flag of Khabarovsk Krai.svg",
    "Khanty-Mansi Autonomous Okrug": "Flag of Yugra.svg",
    "Kirov": "Flag of Kirov Oblast.svg",
    "Komi Republic": "Flag of Komi.svg",
    "Kostroma": "Flag of Kostroma Oblast.svg",
    "Krasnodar Krai": "Flag of Krasnodar Krai.svg",
    "Krasnoyarsk Krai": "Flag of Krasnoyarsk Krai.svg",
    "Kurgan": "Flag of Kurgan Oblast.svg",
    "Kursk": "Flag of Kursk Oblast.svg",
    "Leningrad": "Flag of Leningrad Oblast.svg",
    "Lipetsk": "Flag of Lipetsk Oblast.svg",
    "Magadan": "Flag of Magadan Oblast.svg",
    "Mari El Republic": "Flag of Mari El.svg",
    # Moscow appears twice in the atlas (federal city + oblast) — indistinguishable
    # by name, so both resolve to the city flag (the entity a user is far more
    # likely to click); the oblast's own Saint-George flag can't be targeted
    # without an area hint, so we accept the city flag over showing nothing.
    "Moscow": "Flag of Moscow, Russia.svg",
    "Murmansk": "Flag of Murmansk Oblast.svg",
    "Nenets Autonomous Okrug": "Flag of Nenets Autonomous Okrug.svg",
    "Nizhny Novgorod": "Flag of Nizhny Novgorod Oblast.svg",
    "Novgorod": "Flag of Novgorod Oblast.svg",
    "Novosibirsk": "Flag of Novosibirsk oblast.svg",
    "Omsk": "Flag of Omsk Oblast.svg",
    "Orenburg": "Flag of Orenburg Oblast.svg",
    "Oryol": "Flag of Oryol Oblast.svg",
    "Penza": "Flag of Penza Oblast.svg",
    "Perm Krai": "Flag of Perm Krai.svg",
    "Primorsky Krai": "Flag of Primorsky Krai.svg",
    "Pskov": "Flag of Pskov Oblast.svg",
    "Republic of Adygea": "Flag of Adygea.svg",
    "Republic of Buryatia": "Flag of Buryatia.svg",
    "Republic of Dagestan": "Flag of Dagestan.svg",
    "Republic of Ingushetia": "Flag of Ingushetia.svg",
    "Republic of Kalmykia": "Flag of Kalmykia.svg",
    "Republic of Khakassia": "Flag of Khakassia.svg",
    "Republic of Mordovia": "Flag of Mordovia.svg",
    "Republic of North Ossetia-Alania": "Flag of North Ossetia.svg",
    "Republic of Tatarstan": "Flag of Tatarstan.svg",
    "Rostov": "Flag of Rostov Oblast.svg",
    "Ryazan": "Flag of Ryazan Oblast.svg",
    "Saint Petersburg": "Flag of Saint Petersburg.svg",
    "Sakha Republic": "Flag of Sakha.svg",
    "Sakhalin": "Flag of Sakhalin Oblast.svg",
    "Samara": "Flag of Samara Oblast.svg",
    "Saratov": "Flag of Saratov Oblast.svg",
    "Sevastopol": "Flag of Sevastopol.svg",
    "Smolensk": "Flag of Smolensk Oblast.svg",
    "Stavropol Krai": "Flag of Stavropol Krai.svg",
    "Sverdlovsk": "Flag of Sverdlovsk Oblast.svg",
    "Tambov": "Flag of Tambov Oblast.svg",
    "Tomsk": "Flag of Tomsk Oblast.svg",
    "Tula": "Flag of Tula Oblast.svg",
    "Tuva Republic": "Flag of Tuva.svg",
    "Tver": "Flag of Tver Oblast.svg",
    "Tyumen": "Flag of Tyumen Oblast.svg",
    "Udmurt Republic": "Flag of Udmurtia.svg",
    "Ulyanovsk": "Flag of Ulyanovsk Oblast.svg",
    "Vladimir": "Flag of Vladimir Oblast.svg",
    "Volgograd": "Flag of Volgograd Oblast.svg",
    "Vologda": "Flag of Vologda Oblast.svg",
    "Voronezh": "Flag of Voronezh Oblast.svg",
    "Yamalo-Nenets Autonomous Okrug": "Flag of Yamal-Nenets Autonomous Okrug.svg",
    "Yaroslavl": "Flag of Yaroslavl Oblast.svg",
    "Zabaykalsky Krai": "Flag of Zabaykalsky Krai.svg",
}
for _n, _f in _RUS_SUBJECT_FLAGS.items():
    CURATED[(_n, "RUS")] = _f

# v8.13.4 — countries whose first-level subdivisions must NOT get the blind
# "Flag of {name}.svg" guess (owner: "dont use fake flags or proposed flags for
# india, such as the proposed telangana flag"). India has NO official state
# flags at all — every "Flag of <state>.svg" on Commons is a proposed / former /
# party emblem, i.e. fake — so ALL Indian states resolve to the national flag.
# Pakistan is mixed: the four provinces with real flags are CURATED above, and
# everything else here falls to the national flag instead of a wrong guess.
# v8.13.6 — China added (owner: "Tibet uses old flag … fake ladakh flag"): PRC
# provinces have no official flags, and the Tibetan snow-lion flag is a banned
# pro-independence symbol, NOT an official flag — so all Chinese provinces
# (incl. Tibet/Xizang) resolve to the national flag.
# v8.16 — Iran, Turkey, Syria, Iraq and Azerbaijan added (owner: "flags like
# the khuzestan flag, kurdistan flag, and south azerbaijan flag should NOT
# appear — official flags only"). None of these states' first-level divisions
# carry an official flag, and the blind "Flag of {name}.svg" guess resolves to
# separatist/ethnic-movement flags there (Khuzestan, the Kurdish regions,
# "South Azerbaijan") — exactly the class the owner banned. Iraq's Kurdistan
# REGION flag is official but is rendered by the autonomous-zone layer, not
# the per-governorate guess.
NO_SUBDIVISION_FLAGS = {"IND", "PAK", "CHN", "IRN", "TUR", "SYR", "IRQ", "AZE"}

# Subdivision names that collide with a sovereign state name — suppress the blind
# guess (fall through to a generated seal) unless CURATED has an entry.
COLLISION_BLOCK = {
    "georgia", "luxembourg", "jersey", "guernsey", "monaco", "san marino",
    "malta", "singapore", "kuwait", "qatar", "bahrain", "brunei",
}


def _flag_filename(name, iso3):
    """The Commons filename this unit's flag should live under, or None when the
    unit has no real flag (suppressed countries / uncurated collisions)."""
    if not name:
        return None
    iso3u = (iso3 or "").upper()
    key = (name.strip(), iso3u)
    if key in CURATED:                       # a hand-verified correct flag
        return CURATED[key]
    if iso3u in NO_SUBDIVISION_FLAGS:        # no real subdivision flags
        return None
    if name.strip().lower() in COLLISION_BLOCK:
        return None
    return f"Flag of {name.strip()}.svg"


def flag_url(name, iso3, iso2=None):
    """Primary flag image URL for an administrative unit, or None when it has no
    real flag of its own.

    v8.14.0 — back to Special:FilePath as the PRIMARY (v8.13.8's direct
    md5-thumb URL broke real browsers wholesale: US states, Canadian provinces,
    German Länder all lost their flags — and the direct path 404s BY DESIGN for
    any file that only exists as a Commons redirect, e.g. "Flag of Bavaria.svg"
    → "Flag of Bavaria (lozengy).svg", because only Special:FilePath follows
    redirects). FilePath is the URL form that demonstrably loaded these flags
    in-browser for every release before v8.13.8; its only weakness is bulk
    rate-limiting, which the frontend now absorbs by retrying a failed load
    against flag_url_alt() (the direct CDN thumb) instead of giving up."""
    fname = _flag_filename(name, iso3)
    if not fname:
        return None
    return _BASE.format(f=urllib.parse.quote(fname))


def flag_url_alt(name, iso3, iso2=None):
    """Secondary candidate for the same flag: the direct Wikimedia CDN thumbnail
    (md5-path form). No redirect endpoint involved, so it is never throttled —
    the frontend retries a failed primary load against this before showing
    nothing. Correct for canonically-named files; a redirect-only name 404s
    here, which is fine because the primary already handles those."""
    fname = _flag_filename(name, iso3)
    if not fname:
        return None
    return _commons_thumb(fname)
