"""v8.16 — ruling-party ideology per country, for the Ideology map mode.

One coarse, curated ideology label for the governing party/coalition/regime
of each country (mid-2026 vintage — the same currency bar as the leaders
seed). Labels are a small fixed vocabulary so the map legend stays readable;
`ideologyInfo` in frontend/src/data/families.js colors them. Coalition
governments are labelled by the dominant partner. Non-party regimes get
regime-type labels (military junta, absolute monarchy, theocracy) rather
than pretending a party ideology exists.
"""

IDEOLOGY = {
    # vocabulary: Social democracy, Conservatism, Liberalism, Nationalism,
    # Right-wing populism, Left-wing populism, Socialism, Communism (one-party),
    # Centrism, Christian democracy, Islamism, Theocracy, Military rule,
    # Absolute monarchy, Personalist authoritarian, Green politics
    "USA": "Right-wing populism", "CAN": "Liberalism", "MEX": "Left-wing populism",
    "BRA": "Left-wing populism", "ARG": "Right-wing populism", "CHL": "Right-wing populism",
    "COL": "Left-wing populism", "PER": "Centrism", "VEN": "Personalist authoritarian",
    "BOL": "Socialism", "ECU": "Conservatism", "URY": "Social democracy",
    "PRY": "Conservatism", "CUB": "Communism (one-party)", "NIC": "Personalist authoritarian",
    "GBR": "Social democracy", "FRA": "Centrism", "DEU": "Christian democracy",
    "ITA": "Right-wing populism", "ESP": "Social democracy", "PRT": "Social democracy",
    "NLD": "Right-wing populism", "BEL": "Centrism", "AUT": "Christian democracy",
    "CHE": "Centrism", "IRL": "Centrism", "SWE": "Conservatism", "NOR": "Social democracy",
    "DNK": "Social democracy", "FIN": "Conservatism", "ISL": "Centrism",
    "POL": "Liberalism", "CZE": "Right-wing populism", "SVK": "Left-wing populism",
    "HUN": "Liberalism", "ROU": "Social democracy", "BGR": "Conservatism",
    "GRC": "Conservatism", "HRV": "Christian democracy", "SRB": "Nationalism",
    "UKR": "Liberalism", "MDA": "Liberalism", "BLR": "Personalist authoritarian",
    "RUS": "Personalist authoritarian", "GEO": "Conservatism", "ARM": "Liberalism",
    "AZE": "Personalist authoritarian", "TUR": "Islamism", "EST": "Liberalism",
    "LVA": "Centrism", "LTU": "Social democracy", "ALB": "Social democracy",
    "MKD": "Nationalism", "BIH": "Nationalism", "MNE": "Centrism", "XKX": "Left-wing populism",
    "CHN": "Communism (one-party)", "PRK": "Communism (one-party)", "VNM": "Communism (one-party)",
    "LAO": "Communism (one-party)", "JPN": "Conservatism", "KOR": "Liberalism",
    "TWN": "Liberalism", "MNG": "Social democracy", "IND": "Nationalism",
    "PAK": "Centrism", "BGD": "Centrism", "LKA": "Left-wing populism",
    "NPL": "Centrism", "AFG": "Theocracy", "IRN": "Theocracy",
    "IRQ": "Islamism", "SYR": "Islamism", "SAU": "Absolute monarchy",
    "ARE": "Absolute monarchy", "QAT": "Absolute monarchy", "KWT": "Absolute monarchy",
    "BHR": "Absolute monarchy", "OMN": "Absolute monarchy", "JOR": "Conservatism",
    "ISR": "Nationalism", "LBN": "Centrism", "YEM": "Military rule",
    "EGY": "Military rule", "LBY": "Military rule", "TUN": "Personalist authoritarian",
    "DZA": "Nationalism", "MAR": "Liberalism", "SDN": "Military rule",
    "ETH": "Nationalism", "KEN": "Conservatism", "TZA": "Nationalism",
    "UGA": "Personalist authoritarian", "RWA": "Personalist authoritarian",
    "NGA": "Conservatism", "GHA": "Social democracy", "CIV": "Liberalism",
    "SEN": "Left-wing populism", "MLI": "Military rule", "BFA": "Military rule",
    "NER": "Military rule", "TCD": "Military rule", "GIN": "Military rule",
    "GAB": "Military rule", "CMR": "Personalist authoritarian", "COD": "Centrism",
    "AGO": "Socialism", "MOZ": "Socialism", "ZWE": "Nationalism",
    "ZMB": "Liberalism", "ZAF": "Social democracy", "BWA": "Social democracy",
    "NAM": "Socialism", "ERI": "Personalist authoritarian", "SOM": "Centrism",
    "SSD": "Personalist authoritarian", "IDN": "Nationalism", "MYS": "Centrism",
    "SGP": "Conservatism", "THA": "Conservatism", "PHL": "Personalist authoritarian",
    "MMR": "Military rule", "KHM": "Personalist authoritarian", "AUS": "Social democracy",
    "NZL": "Conservatism", "PNG": "Centrism", "FJI": "Centrism",
    "KAZ": "Personalist authoritarian", "UZB": "Personalist authoritarian",
    "TKM": "Personalist authoritarian", "TJK": "Personalist authoritarian",
    "KGZ": "Nationalism", "CRI": "Social democracy", "PAN": "Right-wing populism",
    "DOM": "Liberalism", "GTM": "Social democracy", "HND": "Left-wing populism",
    "SLV": "Right-wing populism", "JAM": "Social democracy", "TTO": "Social democracy",
    "PSE": "Nationalism", "VAT": "Theocracy",
}

DEFAULT = "Centrism"


def ideology_for(iso3: str) -> str:
    return IDEOLOGY.get(iso3, DEFAULT)


def all_values() -> dict:
    return dict(IDEOLOGY)
