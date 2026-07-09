"""v8.9 — sub-national thematic values for the tier-aware map modes.

The base map modes colour whole countries (routes_geo.MAP_MODES). When an
administrative-division tier is enabled, the same modes redraw per admin unit.
Two new, finer categorical modes ride alongside the broad ones:

  religion  → the broad tradition   (Islam / Christianity / Hinduism / …)
  religious_sect → the specific sect (Sunni / Twelver Shia / Ismaili Shia /
                   Zaydi Shia / Ibadi / Catholic / Protestant / Orthodox / …)
  language  → the broad language     (Arabic / English / Hindi / …)
  dialect   → the specific dialect   (Egyptian Arabic / American English / …)

There is NO vendorable dataset that assigns a religion/sect/language/dialect to
each of the 60k administrative units, so this is an HONEST curated layer:

  * every unit inherits its country's value (the broad map is always right); and
  * a curated SUBNATIONAL table overrides the units that genuinely differ from
    their country's dominant value (Kerala vs the Hindi belt, Iraq's Shia south
    vs Sunni west, Nigeria's Muslim north vs Christian south, Quebec's French,
    Kurdish-Sorani belts, etc.).

Country-level broad religion/language come from the `countries` table
(dominant_religion / dominant_language). Country-level SECT and DIALECT are
curated here (COUNTRY_SECT / COUNTRY_DIALECT). New majors drop in as data.
"""

# --- country-level dominant SECT (within the country's dominant religion) -----
# Keyed by iso3. Islam-majority states carry their madhhab/branch; Christian
# states their communion; others their major school where meaningful.
COUNTRY_SECT = {
    # Sunni-majority
    "SAU": "Sunni", "EGY": "Sunni", "TUR": "Sunni", "PAK": "Sunni",
    "IDN": "Sunni", "MYS": "Sunni", "BGD": "Sunni", "AFG": "Sunni",
    "JOR": "Sunni", "PSE": "Sunni", "QAT": "Sunni", "KWT": "Sunni",
    "ARE": "Sunni", "MAR": "Sunni", "DZA": "Sunni", "TUN": "Sunni",
    "LBY": "Sunni", "SDN": "Sunni", "SOM": "Sunni", "YEM": "Sunni",
    "SEN": "Sunni", "MLI": "Sunni", "NER": "Sunni", "TCD": "Sunni",
    "MRT": "Sunni", "GMB": "Sunni", "GIN": "Sunni", "SYR": "Sunni",
    "UZB": "Sunni", "TKM": "Sunni", "KAZ": "Sunni", "KGZ": "Sunni",
    "TJK": "Sunni", "ALB": "Sunni", "KOS": "Sunni", "BRN": "Sunni",
    "MDV": "Sunni", "DJI": "Sunni", "COM": "Sunni", "BFA": "Sunni",
    # Shia-majority
    "IRN": "Twelver Shia", "IRQ": "Twelver Shia", "BHR": "Twelver Shia",
    "AZE": "Twelver Shia",
    # Ibadi-majority
    "OMN": "Ibadi",
    # Christian communions
    "USA": "Protestant", "GBR": "Protestant", "DEU": "Protestant",
    "NLD": "Protestant", "DNK": "Protestant", "SWE": "Protestant",
    "NOR": "Protestant", "FIN": "Protestant", "ISL": "Protestant",
    "AUS": "Protestant", "NZL": "Protestant", "ZAF": "Protestant",
    "KEN": "Protestant", "NGA": "Protestant", "GHA": "Protestant",
    "UGA": "Protestant", "ZMB": "Protestant", "ZWE": "Protestant",
    "CHE": "Protestant",
    "FRA": "Catholic", "ITA": "Catholic", "ESP": "Catholic",
    "PRT": "Catholic", "IRL": "Catholic", "POL": "Catholic",
    "BEL": "Catholic", "AUT": "Catholic", "HRV": "Catholic",
    "SVN": "Catholic", "SVK": "Catholic", "CZE": "Catholic",
    "HUN": "Catholic", "LTU": "Catholic", "PHL": "Catholic",
    "MEX": "Catholic", "BRA": "Catholic", "ARG": "Catholic",
    "CHL": "Catholic", "COL": "Catholic", "PER": "Catholic",
    "VEN": "Catholic", "ECU": "Catholic", "BOL": "Catholic",
    "PRY": "Catholic", "URY": "Catholic", "CUB": "Catholic",
    "DOM": "Catholic", "GTM": "Catholic", "HND": "Catholic",
    "NIC": "Catholic", "CRI": "Catholic", "PAN": "Catholic",
    "AGO": "Catholic", "COD": "Catholic", "RWA": "Catholic",
    "CAN": "Catholic",
    "RUS": "Orthodox", "UKR": "Orthodox", "BLR": "Orthodox",
    "GRC": "Orthodox", "SRB": "Orthodox", "BGR": "Orthodox",
    "ROU": "Orthodox", "MDA": "Orthodox", "GEO": "Orthodox",
    "MKD": "Orthodox", "MNE": "Orthodox", "CYP": "Orthodox",
    "ARM": "Oriental Orthodox", "ETH": "Oriental Orthodox",
    "ERI": "Oriental Orthodox",
    # non-Christian / non-Muslim majors
    "IND": "Hindu (Shaivite/Vaishnavite)", "NPL": "Hindu (Shaivite/Vaishnavite)",
    "THA": "Theravada Buddhist", "MMR": "Theravada Buddhist",
    "KHM": "Theravada Buddhist", "LKA": "Theravada Buddhist",
    "LAO": "Theravada Buddhist", "BTN": "Vajrayana Buddhist",
    "MNG": "Vajrayana Buddhist", "JPN": "Mahayana Buddhist",
    "ISR": "Judaism (Rabbinic)",
    "CHN": "Chinese folk / Buddhist", "VNM": "Mahayana Buddhist",
    "KOR": "Protestant", "PRK": "Irreligious",
}

# --- country-level dominant DIALECT (of the country's dominant language) -------
COUNTRY_DIALECT = {
    # English
    "USA": "American English", "CAN": "Canadian English",
    "GBR": "British English", "IRL": "Hiberno-English",
    "AUS": "Australian English", "NZL": "New Zealand English",
    "ZAF": "South African English", "IND": "Indian English",
    "NGA": "Nigerian English", "GHA": "Ghanaian English",
    "KEN": "Kenyan English", "JAM": "Jamaican Patois",
    # Arabic
    "EGY": "Egyptian Arabic", "SAU": "Gulf Arabic", "ARE": "Gulf Arabic",
    "QAT": "Gulf Arabic", "KWT": "Gulf Arabic", "BHR": "Gulf Arabic",
    "OMN": "Gulf Arabic", "YEM": "Yemeni Arabic", "IRQ": "Mesopotamian Arabic",
    "SYR": "Levantine Arabic", "JOR": "Levantine Arabic",
    "LBN": "Levantine Arabic", "PSE": "Levantine Arabic",
    "MAR": "Moroccan Arabic (Darija)", "DZA": "Algerian Arabic",
    "TUN": "Tunisian Arabic", "LBY": "Libyan Arabic",
    "SDN": "Sudanese Arabic",
    # Spanish
    "ESP": "Castilian Spanish", "MEX": "Mexican Spanish",
    "ARG": "Rioplatense Spanish", "URY": "Rioplatense Spanish",
    "COL": "Colombian Spanish", "CHL": "Chilean Spanish",
    "PER": "Andean Spanish", "VEN": "Venezuelan Spanish",
    "CUB": "Caribbean Spanish", "DOM": "Caribbean Spanish",
    # Portuguese / French / German / Chinese
    "BRA": "Brazilian Portuguese", "PRT": "European Portuguese",
    "FRA": "Metropolitan French", "CAN_FR": "Quebec French",
    "BEL": "Belgian French", "CHE": "Swiss German",
    "AUT": "Austrian German", "DEU": "Standard German",
    "CHN": "Mandarin (Putonghua)", "TWN": "Taiwanese Mandarin",
    "HKG": "Cantonese (Hong Kong)",
    # others where the country name IS the dialect distinction
    "IRN": "Western Persian (Farsi)", "AFG": "Dari Persian",
    "TJK": "Tajik Persian", "BRA_": "Brazilian Portuguese",
}

# --- curated SUB-NATIONAL overrides -------------------------------------------
# Keyed by (iso3, unit_english_name.lower()). Only the units that genuinely
# differ from their country's dominant value. Any field may be omitted (falls
# back to the country value). This is the honest heterogeneity layer.
def _S(religion=None, sect=None, language=None, dialect=None):
    d = {}
    if religion:
        d["religion"] = religion
    if sect:
        d["sect"] = sect
    if language:
        d["language"] = language
    if dialect:
        d["dialect"] = dialect
    return d


SUBNATIONAL = {
    # --- India: the classic heterogeneity showcase --------------------------
    ("IND", "kerala"): _S(language="Malayalam", dialect="Malayalam",
                          religion="Hinduism", sect="Hindu (mixed, ~45% non-Hindu)"),
    ("IND", "jammu and kashmir"): _S(religion="Islam", sect="Sunni",
                                     language="Kashmiri", dialect="Kashmiri"),
    ("IND", "ladakh"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                          language="Ladakhi", dialect="Ladakhi"),
    ("IND", "punjab"): _S(religion="Sikhism", sect="Sikh (Khalsa)",
                          language="Punjabi", dialect="Punjabi (Majhi)"),
    ("IND", "nagaland"): _S(religion="Christianity", sect="Protestant (Baptist)",
                            language="English", dialect="Nagamese"),
    ("IND", "mizoram"): _S(religion="Christianity", sect="Protestant (Presbyterian)",
                           language="Mizo", dialect="Mizo"),
    ("IND", "meghalaya"): _S(religion="Christianity", sect="Protestant",
                             language="Khasi", dialect="Khasi"),
    ("IND", "manipur"): _S(religion="Hinduism", sect="Hindu / Christian mix",
                           language="Meitei", dialect="Meitei"),
    ("IND", "tamil nadu"): _S(language="Tamil", dialect="Tamil"),
    ("IND", "west bengal"): _S(language="Bengali", dialect="Bengali (Rarhi)"),
    ("IND", "assam"): _S(language="Assamese", dialect="Assamese"),
    ("IND", "karnataka"): _S(language="Kannada", dialect="Kannada"),
    ("IND", "andhra pradesh"): _S(language="Telugu", dialect="Telugu"),
    ("IND", "telangana"): _S(language="Telugu", dialect="Telangana Telugu"),
    ("IND", "maharashtra"): _S(language="Marathi", dialect="Marathi"),
    ("IND", "gujarat"): _S(language="Gujarati", dialect="Gujarati"),
    ("IND", "odisha"): _S(language="Odia", dialect="Odia"),
    ("IND", "goa"): _S(religion="Hinduism", sect="Hindu / Catholic mix",
                       language="Konkani", dialect="Konkani"),
    ("IND", "sikkim"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                          language="Nepali", dialect="Sikkimese"),
    ("IND", "arunachal pradesh"): _S(religion="Christianity",
                                     sect="Protestant / Donyi-Polo",
                                     language="English"),
    # --- Iraq: Shia south / Sunni west / Kurdish north ----------------------
    ("IRQ", "basra"): _S(sect="Twelver Shia"),
    ("IRQ", "najaf"): _S(sect="Twelver Shia"),
    ("IRQ", "karbala"): _S(sect="Twelver Shia"),
    ("IRQ", "al-anbar"): _S(sect="Sunni"),
    ("IRQ", "anbar"): _S(sect="Sunni"),
    ("IRQ", "salah al-din"): _S(sect="Sunni"),
    ("IRQ", "ninawa"): _S(sect="Sunni", language="Arabic"),
    ("IRQ", "erbil"): _S(sect="Sunni", language="Kurdish", dialect="Sorani Kurdish"),
    ("IRQ", "duhok"): _S(sect="Sunni", language="Kurdish", dialect="Kurmanji Kurdish"),
    ("IRQ", "as-sulaymaniyah"): _S(sect="Sunni", language="Kurdish",
                                   dialect="Sorani Kurdish"),
    ("IRQ", "sulaymaniyah"): _S(sect="Sunni", language="Kurdish",
                                dialect="Sorani Kurdish"),
    # --- Nigeria: Muslim north / Christian south ----------------------------
    ("NGA", "kano"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "sokoto"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "kaduna"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "borno"): _S(religion="Islam", sect="Sunni", language="Kanuri"),
    ("NGA", "lagos"): _S(religion="Christianity", sect="Protestant", language="Yoruba"),
    ("NGA", "oyo"): _S(religion="Christianity", sect="Protestant", language="Yoruba"),
    ("NGA", "rivers"): _S(religion="Christianity", sect="Protestant"),
    ("NGA", "anambra"): _S(religion="Christianity", sect="Catholic", language="Igbo"),
    ("NGA", "enugu"): _S(religion="Christianity", sect="Catholic", language="Igbo"),
    # --- Lebanon / Syria ----------------------------------------------------
    ("LBN", "mount lebanon"): _S(religion="Christianity", sect="Maronite Catholic"),
    ("LBN", "nabatieh"): _S(religion="Islam", sect="Twelver Shia"),
    ("LBN", "south lebanon"): _S(religion="Islam", sect="Twelver Shia"),
    ("SYR", "latakia"): _S(sect="Alawite Shia"),
    ("SYR", "tartus"): _S(sect="Alawite Shia"),
    ("SYR", "al-hasakah"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    # --- Pakistan: Sindhi / Pashto / Balochi / Shia Gilgit ------------------
    ("PAK", "sindh"): _S(language="Sindhi", dialect="Sindhi"),
    ("PAK", "balochistan"): _S(language="Balochi", dialect="Balochi"),
    ("PAK", "khyber pakhtunkhwa"): _S(language="Pashto", dialect="Pashto"),
    ("PAK", "gilgit-baltistan"): _S(sect="Twelver/Ismaili Shia"),
    # --- China: Xinjiang / Tibet / Ningxia ----------------------------------
    ("CHN", "xinjiang"): _S(religion="Islam", sect="Sunni",
                            language="Uyghur", dialect="Uyghur"),
    ("CHN", "tibet"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                         language="Tibetan", dialect="Tibetan"),
    ("CHN", "ningxia"): _S(religion="Islam", sect="Sunni (Hui)"),
    ("CHN", "inner mongolia"): _S(language="Mongolian", dialect="Mongolian"),
    ("CHN", "guangdong"): _S(dialect="Cantonese (Yue)"),
    ("CHN", "guangxi"): _S(language="Zhuang", dialect="Cantonese/Zhuang"),
    # --- Canada: Quebec French ----------------------------------------------
    ("CAN", "quebec"): _S(language="French", dialect="Quebec French"),
    ("CAN", "québec"): _S(language="French", dialect="Quebec French"),
    ("CAN", "new brunswick"): _S(dialect="Acadian French / English"),
    # --- Spain: regional languages ------------------------------------------
    ("ESP", "catalonia"): _S(language="Catalan", dialect="Catalan"),
    ("ESP", "cataluña"): _S(language="Catalan", dialect="Catalan"),
    ("ESP", "basque country"): _S(language="Basque", dialect="Basque"),
    ("ESP", "país vasco"): _S(language="Basque", dialect="Basque"),
    ("ESP", "galicia"): _S(language="Galician", dialect="Galician"),
    ("ESP", "valencia"): _S(language="Catalan", dialect="Valencian"),
    # --- Belgium / Switzerland ----------------------------------------------
    ("BEL", "flanders"): _S(language="Dutch", dialect="Flemish"),
    ("BEL", "wallonia"): _S(language="French", dialect="Belgian French"),
    ("CHE", "geneva"): _S(language="French", dialect="Swiss French"),
    ("CHE", "vaud"): _S(language="French", dialect="Swiss French"),
    ("CHE", "ticino"): _S(language="Italian", dialect="Swiss Italian"),
    # --- Russia: Muslim & Buddhist republics --------------------------------
    ("RUS", "chechnya"): _S(religion="Islam", sect="Sunni", language="Chechen"),
    ("RUS", "dagestan"): _S(religion="Islam", sect="Sunni", language="Avar"),
    ("RUS", "ingushetia"): _S(religion="Islam", sect="Sunni", language="Ingush"),
    ("RUS", "tatarstan"): _S(religion="Islam", sect="Sunni", language="Tatar"),
    ("RUS", "bashkortostan"): _S(religion="Islam", sect="Sunni", language="Bashkir"),
    ("RUS", "kalmykia"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                            language="Kalmyk"),
    ("RUS", "buryatia"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                            language="Buryat"),
    ("RUS", "tuva"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                        language="Tuvan"),
    # --- Ethiopia / Tanzania / Philippines Muslim south ---------------------
    ("ETH", "somali"): _S(religion="Islam", sect="Sunni", language="Somali"),
    ("ETH", "afar"): _S(religion="Islam", sect="Sunni", language="Afar"),
    ("TZA", "zanzibar urban/west"): _S(religion="Islam", sect="Sunni"),
    ("PHL", "maguindanao"): _S(religion="Islam", sect="Sunni"),
    ("PHL", "lanao del sur"): _S(religion="Islam", sect="Sunni"),
    ("PHL", "sulu"): _S(religion="Islam", sect="Sunni"),
    # --- Bosnia: the three constituent peoples ------------------------------
    ("BIH", "republika srpska"): _S(religion="Christianity", sect="Orthodox",
                                    language="Serbian"),
    # --- USA: no religious split, but Louisiana/Utah flavour ----------------
    ("USA", "utah"): _S(sect="Latter-day Saint (LDS)"),
    ("USA", "louisiana"): _S(sect="Catholic"),
    ("USA", "rhode island"): _S(sect="Catholic"),
}


def country_sect(iso3):
    return COUNTRY_SECT.get(iso3)


def country_dialect(iso3):
    return COUNTRY_DIALECT.get(iso3)


def unit_value(iso3, unit_name, field, country_religion, country_language):
    """Return the categorical value for one admin unit and one field
    ('religion' | 'sect' | 'language' | 'dialect'), applying the curated
    sub-national override, then falling back to the country value.
    """
    override = SUBNATIONAL.get((iso3, (unit_name or "").strip().lower()))
    if override and field in override:
        return override[field]
    if field == "religion":
        return country_religion
    if field == "language":
        return country_language
    if field == "sect":
        return COUNTRY_SECT.get(iso3) or country_religion
    if field == "dialect":
        return COUNTRY_DIALECT.get(iso3) or country_language
    return None
