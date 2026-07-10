"""v8.13 — climate + altitude map-mode data (owner: "add climate and altitude
maps, adapted to divisions of all levels").

Two curated knowledge layers over the atlas, in the same shape as
admin_thematic (a country floor + a sub-national override table for the big
heterogeneous countries, resolved by (iso3, atlas ADM1 name)):

- CLIMATE: a Köppen main-group per country/unit — Tropical / Arid / Temperate /
  Continental / Polar / Highland. Explicit for the majors; a latitude-band
  default (from the country centroid) covers everyone else honestly.
- ELEVATION: mean elevation in metres, curated for the majors (numeric mode).

Sub-national overrides let, e.g., the US resolve arid south-west vs continental
north, Russia continental vs polar, India tropical south vs highland Himalaya,
China arid west vs temperate east — the same heterogeneity the religion/sect/
dialect layers carry.
"""

# --- country climate floor (Köppen main group) ---------------------------------
CLIMATE_BY_ISO = {
    # Tropical
    "BRA": "Tropical", "IDN": "Tropical", "COD": "Tropical", "NGA": "Tropical",
    "COL": "Tropical", "VEN": "Tropical", "PHL": "Tropical", "THA": "Tropical",
    "VNM": "Tropical", "MYS": "Tropical", "KHM": "Tropical", "LAO": "Tropical",
    "MMR": "Tropical", "BGD": "Tropical", "LKA": "Tropical", "KEN": "Tropical",
    "TZA": "Tropical", "UGA": "Tropical", "GHA": "Tropical", "CIV": "Tropical",
    "CMR": "Tropical", "AGO": "Tropical", "MOZ": "Tropical", "MDG": "Tropical",
    "ECU": "Tropical", "PER": "Tropical", "BOL": "Tropical", "PAN": "Tropical",
    "CRI": "Tropical", "NIC": "Tropical", "HND": "Tropical", "GTM": "Tropical",
    "CUB": "Tropical", "DOM": "Tropical", "HTI": "Tropical", "PNG": "Tropical",
    "FJI": "Tropical", "SGP": "Tropical", "BRN": "Tropical", "ETH": "Tropical",
    # Arid / desert
    "SAU": "Arid", "ARE": "Arid", "QAT": "Arid", "KWT": "Arid", "OMN": "Arid",
    "BHR": "Arid", "EGY": "Arid", "LBY": "Arid", "DZA": "Arid", "TUN": "Arid",
    "MAR": "Arid", "MRT": "Arid", "MLI": "Arid", "NER": "Arid", "TCD": "Arid",
    "SDN": "Arid", "SOM": "Arid", "DJI": "Arid", "ERI": "Arid", "YEM": "Arid",
    "JOR": "Arid", "IRQ": "Arid", "ISR": "Arid", "TKM": "Arid", "UZB": "Arid",
    "NAM": "Arid", "BWA": "Arid", "IRN": "Arid",
    # Temperate
    "GBR": "Temperate", "FRA": "Temperate", "ESP": "Temperate", "ITA": "Temperate",
    "PRT": "Temperate", "DEU": "Temperate", "NLD": "Temperate", "BEL": "Temperate",
    "IRL": "Temperate", "CHE": "Temperate", "AUT": "Temperate", "GRC": "Temperate",
    "TUR": "Temperate", "JPN": "Temperate", "KOR": "Temperate", "NZL": "Temperate",
    "URY": "Temperate", "ZAF": "Temperate", "CHL": "Temperate", "AUS": "Arid",
    "MEX": "Arid", "PAK": "Arid", "AFG": "Continental", "SYR": "Arid",
    # Continental
    "RUS": "Continental", "CAN": "Continental", "KAZ": "Continental",
    "MNG": "Continental", "POL": "Continental", "UKR": "Continental",
    "BLR": "Continental", "ROU": "Continental", "CZE": "Continental",
    "SVK": "Continental", "HUN": "Continental", "FIN": "Continental",
    "SWE": "Continental", "NOR": "Continental", "EST": "Continental",
    "LVA": "Continental", "LTU": "Continental", "USA": "Temperate",
    "CHN": "Temperate", "IND": "Tropical", "ARG": "Temperate",
    # Polar / highland
    "ISL": "Polar", "GRL": "Polar", "NPL": "Highland", "BTN": "Highland",
    "TJK": "Highland", "KGZ": "Highland", "ARM": "Highland", "GEO": "Highland",
    "AND": "Highland", "LSO": "Highland",
}

# --- mean elevation (m), curated for the majors --------------------------------
ELEV_BY_ISO = {
    "NPL": 3265, "BTN": 3280, "TJK": 3186, "KGZ": 2988, "AFG": 1884, "LSO": 2161,
    "AND": 1996, "BOL": 1192, "ETH": 1330, "IRN": 1305, "MNG": 1528, "CHE": 1350,
    "AUT": 910, "ZWE": 961, "ZMB": 1138, "NAM": 1141, "ZAF": 1034, "TUR": 1132,
    "MEX": 1111, "PER": 1555, "CHL": 1871, "COL": 593, "ESP": 660, "USA": 760,
    "CHN": 1840, "IND": 621, "RUS": 600, "CAN": 487, "BRA": 320, "AUS": 330,
    "FRA": 375, "DEU": 263, "GBR": 162, "ITA": 538, "JPN": 438, "PAK": 900,
    "KAZ": 387, "SAU": 665, "EGY": 321, "DZA": 800, "KEN": 762, "COD": 726,
    "ARG": 595, "SWE": 320, "NOR": 460, "FIN": 164, "POL": 173, "UKR": 175,
    "NLD": 30, "BGD": 85, "GRL": 1792, "ISL": 557, "NZL": 388, "IDN": 367,
    "PHL": 442, "VNM": 398, "THA": 287, "MMR": 702, "YEM": 999, "OMN": 310,
    "MAR": 909, "TUN": 246, "LBY": 423, "SDN": 568, "TCD": 543, "NER": 474,
    "MLI": 343, "AGO": 1112, "MOZ": 345, "MDG": 615, "GHA": 190, "NGA": 380,
}

# --- sub-national climate overrides (iso3, lowercased atlas ADM1 name) ----------
_SUB = {
    # United States — atlas ADM1 = states
    ("USA", "arizona"): "Arid", ("USA", "nevada"): "Arid", ("USA", "new mexico"): "Arid",
    ("USA", "utah"): "Arid", ("USA", "alaska"): "Polar", ("USA", "hawaii"): "Tropical",
    ("USA", "florida"): "Tropical", ("USA", "colorado"): "Highland",
    ("USA", "montana"): "Continental", ("USA", "north dakota"): "Continental",
    ("USA", "minnesota"): "Continental", ("USA", "maine"): "Continental",
    ("USA", "california"): "Arid", ("USA", "texas"): "Arid",
    # Russia
    ("RUS", "sakha"): "Polar", ("RUS", "chukotka"): "Polar",
    ("RUS", "yamalo-nenets"): "Polar", ("RUS", "murmansk"): "Polar",
    ("RUS", "krasnodar"): "Temperate", ("RUS", "republic of dagestan"): "Arid",
    # China
    ("CHN", "xinjiang"): "Arid", ("CHN", "tibet"): "Highland",
    ("CHN", "qinghai"): "Highland", ("CHN", "inner mongolia"): "Arid",
    ("CHN", "hainan"): "Tropical", ("CHN", "guangdong"): "Tropical",
    ("CHN", "heilongjiang"): "Continental",
    # India
    ("IND", "kerala"): "Tropical", ("IND", "tamil nadu"): "Tropical",
    ("IND", "rajasthan"): "Arid", ("IND", "jammu and kashmir"): "Highland",
    ("IND", "ladakh"): "Highland", ("IND", "himachal pradesh"): "Highland",
    ("IND", "uttarakhand"): "Highland", ("IND", "sikkim"): "Highland",
    # Canada
    ("CAN", "nunavut"): "Polar", ("CAN", "northwest territories"): "Polar",
    ("CAN", "yukon"): "Polar", ("CAN", "british columbia"): "Temperate",
    # Australia
    ("AUS", "queensland"): "Tropical", ("AUS", "northern territory"): "Tropical",
    ("AUS", "tasmania"): "Temperate", ("AUS", "victoria"): "Temperate",
    ("AUS", "western australia"): "Arid", ("AUS", "south australia"): "Arid",
    # Argentina / Brazil / Chile
    ("ARG", "tierra del fuego"): "Polar", ("ARG", "santa cruz"): "Continental",
    ("BRA", "amazonas"): "Tropical", ("BRA", "rio grande do sul"): "Temperate",
    ("CHL", "antofagasta"): "Arid", ("CHL", "magallanes"): "Polar",
}


def _lat_default(lat):
    """Honest latitude-band climate fallback for a country with no explicit entry."""
    if lat is None:
        return "Temperate"
    a = abs(lat)
    if a < 23.5:
        return "Tropical"
    if a < 35:
        return "Arid"          # subtropical belt skews arid worldwide
    if a < 55:
        return "Temperate"
    if a < 66:
        return "Continental"
    return "Polar"


_LAT_BY_ISO = None


def _country_lat(iso3):
    """Capital/centroid latitude from the seed table (index 5 of each tuple)."""
    global _LAT_BY_ISO
    if _LAT_BY_ISO is None:
        from .seed_data import COUNTRIES
        _LAT_BY_ISO = {row[0]: row[5] for row in COUNTRIES if len(row) > 5}
    return _LAT_BY_ISO.get(iso3)


def country_climate(iso3, lat=None):
    if lat is None:
        lat = _country_lat(iso3)
    return CLIMATE_BY_ISO.get(iso3) or _lat_default(lat)


def country_elevation(iso3):
    return ELEV_BY_ISO.get(iso3)


def unit_climate(iso3, unit_name, country_value):
    """Sub-national override → the country value."""
    if unit_name:
        v = _SUB.get((iso3, unit_name.lower()))
        if v:
            return v
    return country_value
