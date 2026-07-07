"""v6.1 — United Nations reference data: Security Council composition and a
set of notable, well-documented resolutions with their recorded vote tallies.

Accuracy note: tallies below are the officially recorded results of real,
widely-reported votes (UN Digital Library / press releases). Per-country
"notable_votes" list the permanent members plus a few significant positions,
not the full roll-call. The aggregate {yes, no, abstain} drives the hemicycle
vote graphic. This is the seed snapshot; the ordinary accuracy/sync path is
how it stays current.
"""

UNSC_PERMANENT = ["USA", "GBR", "FRA", "RUS", "CHN"]

# elected (non-permanent) members with their 2-year term (2025 snapshot)
UNSC_ELECTED = [
    ("ALG", "Algeria", "2024-2025"), ("GUY", "Guyana", "2024-2025"),
    ("KOR", "South Korea", "2024-2025"), ("SLE", "Sierra Leone", "2024-2025"),
    ("SVN", "Slovenia", "2024-2025"), ("DNK", "Denmark", "2025-2026"),
    ("GRC", "Greece", "2025-2026"), ("PAK", "Pakistan", "2025-2026"),
    ("PAN", "Panama", "2025-2026"), ("SOM", "Somalia", "2025-2026"),
]
# note: a couple of iso3s above use common (non-ISO) forms for display only;
# the route maps them back to real ISO3 where a profile exists.
ELECTED_ISO_FIX = {"ALG": "DZA"}

# Councils beyond the UNSC that the panel surfaces at a summary level
OTHER_COUNCILS = [
    ("General Assembly", "All 193 member states; one country, one vote."),
    ("Economic and Social Council (ECOSOC)", "54 members elected for 3-year terms."),
    ("Human Rights Council", "47 members elected by the General Assembly."),
]

# id, body, title, date, summary, result, tally{yes,no,abstain},
# notable_votes{iso3: yes|no|abstain}
RESOLUTIONS = [
    {"id": "ES-11/1", "body": "General Assembly (Emergency Special Session)",
     "title": "Aggression against Ukraine",
     "date": "2022-03-02",
     "summary": "Deplored Russia's invasion of Ukraine and demanded immediate "
                "withdrawal. One of the most-supported GA resolutions on record.",
     "result": "Adopted",
     "tally": {"yes": 141, "no": 5, "abstain": 35},
     "notable_votes": {"USA": "yes", "GBR": "yes", "FRA": "yes", "UKR": "yes",
                       "DEU": "yes", "JPN": "yes", "RUS": "no", "BLR": "no",
                       "PRK": "no", "SYR": "no", "ERI": "no",
                       "CHN": "abstain", "IND": "abstain", "IRN": "abstain",
                       "ZAF": "abstain"}},
    {"id": "ES-10/21", "body": "General Assembly (Emergency Special Session)",
     "title": "Protection of civilians and humanitarian truce in Gaza",
     "date": "2023-12-12",
     "summary": "Demanded an immediate humanitarian ceasefire in Gaza.",
     "result": "Adopted",
     "tally": {"yes": 153, "no": 10, "abstain": 23},
     "notable_votes": {"USA": "no", "ISR": "no", "GBR": "abstain",
                       "FRA": "yes", "CHN": "yes", "RUS": "yes",
                       "DEU": "abstain", "EGY": "yes", "QAT": "yes"}},
    {"id": "S/RES/2728", "body": "Security Council",
     "title": "Demand for an immediate ceasefire in Gaza (Ramadan 2024)",
     "date": "2024-03-25",
     "summary": "First Security Council resolution demanding an immediate "
                "ceasefire in Gaza; the US abstained rather than vetoing.",
     "result": "Adopted",
     "tally": {"yes": 14, "no": 0, "abstain": 1},
     "notable_votes": {"USA": "abstain", "GBR": "yes", "FRA": "yes",
                       "RUS": "yes", "CHN": "yes", "KOR": "yes",
                       "SVN": "yes", "ALG": "yes"}},
    {"id": "S/RES/2735", "body": "Security Council",
     "title": "Gaza ceasefire framework (three-phase plan)",
     "date": "2024-06-10",
     "summary": "Endorsed a three-phase ceasefire-and-hostage-release framework.",
     "result": "Adopted",
     "tally": {"yes": 14, "no": 0, "abstain": 1},
     "notable_votes": {"USA": "yes", "GBR": "yes", "FRA": "yes",
                       "CHN": "yes", "RUS": "abstain"}},
]


# v6.6 — major UN organs / specialized agencies for the UN panel subtabs
UN_SUB_ORGS = [
    {"name": "General Assembly (UNGA)", "hq": "New York", "head": "PGA (rotating)",
     "role": "All 193 members, one vote each; resolutions are non-binding but carry political weight.",
     "members": "All 193 UN member states"},
    {"name": "Security Council (UNSC)", "hq": "New York", "head": "Rotating presidency",
     "role": "Peace & security; binding resolutions; P5 veto (US, UK, France, Russia, China).",
     "members": "P5 + 10 elected members"},
    {"name": "International Court of Justice (ICJ)", "hq": "The Hague",
     "head": "President Nawaf Salam (until 2025) / successor", "role": "Inter-state disputes and advisory opinions.",
     "members": "All UN members are parties to the Statute"},
    {"name": "WHO", "hq": "Geneva", "head": "Tedros Adhanom Ghebreyesus",
     "role": "International public health; outbreak response; health regulations.", "members": "194 member states"},
    {"name": "UNESCO", "hq": "Paris", "head": "Khaled El-Enany (2025–)",
     "role": "Education, science, culture; World Heritage.", "members": "194 members"},
    {"name": "UNICEF", "hq": "New York", "head": "Catherine Russell",
     "role": "Children's welfare, vaccination, emergency relief.", "members": "Operates in 190+ countries"},
    {"name": "UNHCR", "hq": "Geneva", "head": "Filippo Grandi",
     "role": "Refugee protection and displacement response.", "members": "UN programme"},
    {"name": "WFP", "hq": "Rome", "head": "Cindy McCain",
     "role": "Food assistance; largest humanitarian agency; 2020 Nobel Peace Prize.", "members": "UN programme"},
    {"name": "IAEA", "hq": "Vienna", "head": "Rafael Grossi",
     "role": "Nuclear safeguards & verification (incl. Iran, Zaporizhzhia plant).", "members": "180 member states"},
    {"name": "ILO", "hq": "Geneva", "head": "Gilbert Houngbo",
     "role": "Labour standards and workers' rights.", "members": "187 member states"},
]
