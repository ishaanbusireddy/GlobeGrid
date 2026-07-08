"""v7.4.1 — diplomatic RECOGNITION data for the recognition map mode (owner:
"a way to see which countries recognize a state, e.g. Kosovo, Taiwan, Israel,
Palestine"). For each partially-recognized subject we store EITHER the set of
recognizers (when only some states recognize it) OR the set of non-recognizers
(when it is near-universally recognized) — whichever is the shorter, more
maintainable list. `recognition_view()` normalizes to explicit recognizer /
non-recognizer sets over the seeded country universe so the map can color every
country. Curated from the public record through early 2026; approximate counts.
"""

# subject_iso3 -> {name, mode: "recognizers"|"non_recognizers", isos: [...], note}
RECOGNITION = {
    # Kosovo: recognized by ~100 UN members; store recognizers (the shorter,
    # more-contested list).
    "XKX": {"name": "Kosovo", "mode": "recognizers", "note":
            "Recognized by ~100 UN members since 2008; not by Serbia, Russia, "
            "China, Spain, Greece, or five EU states. Some recognitions withdrawn.",
        "isos": [
            "USA", "GBR", "FRA", "DEU", "ITA", "CAN", "TUR", "JPN", "AUS", "AUT",
            "BEL", "BGR", "HRV", "CZE", "DNK", "EST", "FIN", "HUN", "IRL", "LVA",
            "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "SVN", "SWE", "NOR", "ISL",
            "CHE", "ALB", "MKD", "MNE", "SAU", "ARE", "QAT", "KWT", "BHR", "OMN",
            "JOR", "EGY", "MAR", "AFG", "PAK", "KOR", "COL", "PAN", "CRI", "HND",
            "PER", "DOM", "NZL", "SGP", "MYS", "SEN", "GMB", "SLE", "LBR", "BFA",
            "DJI", "COM", "MRT", "SOM", "TCD", "GAB", "GNB", "MWI", "BEN", "TGO"]},
    # Taiwan (ROC): recognized by ~12 states after several 2023-24 switches.
    "TWN": {"name": "Taiwan (Republic of China)", "mode": "recognizers", "note":
            "Formal diplomatic recognition by ~12 states; most others maintain "
            "unofficial ties under a One-China policy. Recognitions have steadily "
            "shifted to Beijing (Honduras 2023, Nauru 2024).",
        "isos": ["GTM", "BLZ", "HTI", "PRY", "VAT", "SWZ", "MHL", "PLW", "TUV",
                 "KNA", "LCA", "VCT"]},
    # Northern Cyprus: recognized only by Türkiye.
    "CYN": {"name": "Northern Cyprus (TRNC)", "mode": "recognizers",
            "note": "Recognized only by Türkiye since 1983.", "isos": ["TUR"]},
    # Abkhazia / South Ossetia: recognized by Russia + a handful.
    "ABK": {"name": "Abkhazia", "mode": "recognizers", "note":
            "Recognized by Russia, Nicaragua, Venezuela, Nauru, Syria.",
        "isos": ["RUS", "NIC", "VEN", "NRU", "SYR"]},
    "OST": {"name": "South Ossetia", "mode": "recognizers", "note":
            "Recognized by Russia, Nicaragua, Venezuela, Nauru, Syria.",
        "isos": ["RUS", "NIC", "VEN", "NRU", "SYR"]},
    # Western Sahara (SADR): recognized by ~40+ states, many suspended/withdrawn.
    "ESH": {"name": "Western Sahara (SADR)", "mode": "recognizers", "note":
            "Recognized by ~40 states (many African/Latin American), with several "
            "recognitions frozen or withdrawn; claimed and largely controlled by "
            "Morocco, whose sovereignty the US and others back.",
        "isos": ["DZA", "ZAF", "NGA", "AGO", "MOZ", "ZWE", "ETH", "KEN", "TZA",
                 "UGA", "RWA", "BWA", "NAM", "LSO", "SLE", "GNB", "MLI", "MRT",
                 "VEN", "BOL", "CUB", "NIC", "PRK", "IRN", "SYR", "VNM", "LAO",
                 "TLS", "PAN", "ECU", "URY", "MEX", "SLV"]},
    # Palestine: recognized by ~145 UN members; store the NON-recognizers (short).
    "PSE": {"name": "State of Palestine", "mode": "non_recognizers", "note":
            "Recognized by ~145 UN members. Most Western states had NOT recognized "
            "it, though Spain, Ireland, Norway and Slovenia did in 2024.",
        "isos": ["USA", "CAN", "GBR", "DEU", "ITA", "JPN", "KOR", "AUS", "NZL",
                 "NLD", "BEL", "AUT", "CHE", "DNK", "FIN", "GRC", "PRT", "LUX",
                 "ISR", "PAN", "CMR", "MEX", "COL", "SGP", "ETH"]},
    # Israel: recognized by ~165 UN members; store the NON-recognizers (short).
    "ISR": {"name": "Israel", "mode": "non_recognizers", "note":
            "Recognized by ~165 UN members. A bloc of mostly Arab/Muslim-majority "
            "states does not recognize it, though the Abraham Accords (2020-21) "
            "added the UAE, Bahrain, Morocco and Sudan.",
        "isos": ["DZA", "AFG", "BGD", "BRN", "COM", "CUB", "DJI", "IRN", "IRQ",
                 "KWT", "LBN", "LBY", "MYS", "MDV", "MLI", "NER", "PRK", "OMN",
                 "PAK", "QAT", "SAU", "SOM", "SYR", "TUN", "YEM"]},
}


def recognition_subjects():
    """List of subjects the map mode offers (id + name + note)."""
    return [{"id": k, "name": v["name"], "note": v["note"]}
            for k, v in RECOGNITION.items()]


def recognition_view(subject_iso3, all_isos):
    """Normalize a subject to explicit recognizer / non-recognizer sets over the
    given country universe, so the map can color every country. Returns None for
    an unknown subject."""
    subject_iso3 = (subject_iso3 or "").upper()
    rec = RECOGNITION.get(subject_iso3)
    if not rec:
        return None
    universe = [i for i in all_isos if i and i != subject_iso3]
    listed = set(rec["isos"])
    if rec["mode"] == "recognizers":
        recognizers = [i for i in universe if i in listed]
        non = [i for i in universe if i not in listed]
    else:  # non_recognizers listed
        non = [i for i in universe if i in listed]
        recognizers = [i for i in universe if i not in listed]
    return {"subject": subject_iso3, "name": rec["name"], "note": rec["note"],
            "mode": rec["mode"], "recognizers": recognizers,
            "non_recognizers": non,
            "recognizer_count": len(recognizers)}
