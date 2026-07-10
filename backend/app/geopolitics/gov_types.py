"""v8.13.6 — government / regime type per country, for the "Government type"
world map mode (owner: "democracy, partial democracy, constitutional monarchy,
monarchy, autocracy, etc").

A curated classification that blends government FORM (monarchies split into
ceremonial constitutional vs ruling absolute) with regime QUALITY for republics
(democracy / partial democracy / authoritarian), plus one-party, theocratic and
military/transitional buckets. Draws on the standard regime typologies
(Economist Democracy Index bands, V-Dem, Freedom House) as of early-mid 2026.
Uncurated countries fall back to a parse of the seeded `government_type` string.
"""

# The eight display categories (ordered most→least open) — the legend groups by
# these, coloured in data/families.js `govInfo`.
CATEGORIES = [
    "Democracy",
    "Partial democracy",
    "Constitutional monarchy",
    "Absolute monarchy",
    "Authoritarian",
    "One-party state",
    "Theocracy",
    "Military / transitional",
]

# iso3 -> category. Constitutional (ceremonial-monarch) monarchies are their own
# bucket even when they are also full democracies, per the owner's category list.
GOV = {
    # Full / strong democracies (republics)
    "USA": "Democracy", "FRA": "Democracy", "DEU": "Democracy", "IRL": "Democracy",
    "FIN": "Democracy", "ISL": "Democracy", "AUT": "Democracy", "CHE": "Democracy",
    "PRT": "Democracy", "ITA": "Democracy", "GRC": "Democracy", "CZE": "Democracy",
    "EST": "Democracy", "LVA": "Democracy", "LTU": "Democracy", "SVN": "Democracy",
    "SVK": "Democracy", "URY": "Democracy", "CRI": "Democracy", "CHL": "Democracy",
    "KOR": "Democracy", "TWN": "Democracy", "ISR": "Democracy", "IND": "Partial democracy",
    "MLT": "Democracy", "CYP": "Democracy",
    # Constitutional (ceremonial-monarch) monarchies
    "GBR": "Constitutional monarchy", "JPN": "Constitutional monarchy",
    "ESP": "Constitutional monarchy", "NLD": "Constitutional monarchy",
    "BEL": "Constitutional monarchy", "LUX": "Constitutional monarchy",
    "DNK": "Constitutional monarchy", "SWE": "Constitutional monarchy",
    "NOR": "Constitutional monarchy", "CAN": "Constitutional monarchy",
    "AUS": "Constitutional monarchy", "NZL": "Constitutional monarchy",
    "THA": "Constitutional monarchy", "MYS": "Constitutional monarchy",
    "BHU": "Constitutional monarchy", "LSO": "Constitutional monarchy",
    "JAM": "Constitutional monarchy", "BHS": "Constitutional monarchy",
    "TON": "Constitutional monarchy", "KHM": "Authoritarian",  # nominal monarchy, one-party in practice
    "LIE": "Constitutional monarchy", "MCO": "Constitutional monarchy",
    "AND": "Constitutional monarchy",
    # Ruling / absolute monarchies
    "SAU": "Absolute monarchy", "OMN": "Absolute monarchy", "BRN": "Absolute monarchy",
    "QAT": "Absolute monarchy", "ARE": "Absolute monarchy", "KWT": "Absolute monarchy",
    "BHR": "Absolute monarchy", "SWZ": "Absolute monarchy", "JOR": "Absolute monarchy",
    "MAR": "Absolute monarchy",
    # Partial / flawed democracies & hybrid regimes (republics)
    "POL": "Partial democracy", "HUN": "Partial democracy", "ROU": "Partial democracy",
    "BGR": "Partial democracy", "HRV": "Partial democracy", "SRB": "Partial democracy",
    "MNE": "Partial democracy", "MKD": "Partial democracy", "ALB": "Partial democracy",
    "BIH": "Partial democracy", "MDA": "Partial democracy", "UKR": "Partial democracy",
    "GEO": "Partial democracy", "ARM": "Partial democracy", "MEX": "Partial democracy",
    "BRA": "Partial democracy", "ARG": "Partial democracy", "COL": "Partial democracy",
    "PER": "Partial democracy", "ECU": "Partial democracy", "PRY": "Partial democracy",
    "BOL": "Partial democracy", "PAN": "Partial democracy", "DOM": "Partial democracy",
    "ZAF": "Partial democracy", "NAM": "Partial democracy", "BWA": "Partial democracy",
    "GHA": "Partial democracy", "SEN": "Partial democracy", "KEN": "Partial democracy",
    "NGA": "Partial democracy", "TZA": "Partial democracy", "ZMB": "Partial democracy",
    "MWI": "Partial democracy", "IDN": "Partial democracy", "PHL": "Partial democracy",
    "MNG": "Partial democracy", "NPL": "Partial democracy", "LKA": "Partial democracy",
    "BGD": "Partial democracy", "PAK": "Partial democracy", "TUN": "Partial democracy",
    "IRQ": "Partial democracy", "LBN": "Partial democracy", "PNG": "Partial democracy",
    "FJI": "Partial democracy", "TLS": "Partial democracy", "SUR": "Partial democracy",
    "GTM": "Partial democracy", "HND": "Partial democracy", "SLV": "Partial democracy",
    # Authoritarian republics
    "RUS": "Authoritarian", "BLR": "Authoritarian", "AZE": "Authoritarian",
    "KAZ": "Authoritarian", "UZB": "Authoritarian", "TKM": "Authoritarian",
    "TJK": "Authoritarian", "KGZ": "Authoritarian", "TUR": "Authoritarian",
    "EGY": "Authoritarian", "DZA": "Authoritarian", "LBY": "Military / transitional",
    "VEN": "Authoritarian", "NIC": "Authoritarian", "CUB": "One-party state",
    "ZWE": "Authoritarian", "UGA": "Authoritarian", "RWA": "Authoritarian",
    "CMR": "Authoritarian", "TCD": "Military / transitional", "COD": "Authoritarian",
    "COG": "Authoritarian", "GAB": "Authoritarian", "GNQ": "Authoritarian",
    "AGO": "Authoritarian", "MOZ": "Authoritarian", "ETH": "Authoritarian",
    "ERI": "Authoritarian", "DJI": "Authoritarian", "SSD": "Authoritarian",
    "BDI": "Authoritarian", "CAF": "Authoritarian", "SOM": "Military / transitional",
    "YEM": "Military / transitional", "VNM": "One-party state", "LAO": "One-party state",
    "PRK": "One-party state", "CHN": "One-party state", "SYR": "Military / transitional",
    "IRN": "Theocracy", "AFG": "Theocracy", "VAT": "Theocracy",
    "MMR": "Military / transitional", "SDN": "Military / transitional",
    "MLI": "Military / transitional", "BFA": "Military / transitional",
    "GIN": "Military / transitional", "NER": "Military / transitional",
    "SGP": "Authoritarian",  # dominant-party
}


def _parse(gt):
    g = (gt or "").lower()
    if not g:
        return None
    if "absolute monarchy" in g:
        return "Absolute monarchy"
    if "theo" in g:
        return "Theocracy"
    if "one-party" in g or "communist" in g:
        return "One-party state"
    if "military" in g or "transitional" in g or "provisional" in g:
        return "Military / transitional"
    if "monarchy" in g:
        return "Constitutional monarchy"
    if "republic" in g or "presidential" in g or "parliamentary" in g:
        return "Partial democracy"
    return None


def government_category(iso3, government_type=None):
    if iso3 in GOV:
        return GOV[iso3]
    return _parse(government_type) or "Partial democracy"
