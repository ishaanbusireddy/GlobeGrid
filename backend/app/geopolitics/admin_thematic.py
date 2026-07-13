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
    "MNG": "Vajrayana Buddhist", "JPN": "Shinto",  # v8.16 — owner: Japan reads Shinto
    "ISR": "Judaism (Rabbinic)",
    "CHN": "Chinese folk / Buddhist", "VNM": "Mahayana Buddhist",
    "KOR": "Mahayana Buddhist", "PRK": "Irreligious",  # v8.16 — Korea's Buddhist tradition
    # v8.12 — fill the NA / Europe / Middle East gaps.
    "SLV": "Catholic", "HTI": "Catholic", "LUX": "Catholic",
    "JAM": "Protestant", "BHS": "Protestant", "BRB": "Protestant",
    "TTO": "Catholic", "BLZ": "Catholic",
    "LVA": "Protestant", "EST": "Protestant",   # Lutheran heritage (largely secular)
    "BIH": "Sunni",                              # plurality Bosniak Muslim
    "LBN": "Twelver Shia",                       # largest single community (Christian/Sunni close)
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
    # v8.12 — dialect names for the rest of NA / Europe / ME / Central Asia so
    # the Dialect mode has a value for every target-region country.
    # Central-American / Caribbean Spanish & creoles:
    "GTM": "Central American Spanish", "HND": "Central American Spanish",
    "NIC": "Central American Spanish", "CRI": "Central American Spanish",
    "PAN": "Panamanian Spanish", "SLV": "Central American Spanish",
    "BLZ": "Belizean Kriol / English", "HTI": "Haitian Creole",
    "BHS": "Bahamian English", "TTO": "Trinidadian English", "BRB": "Bajan English",
    # Europe — the standard national variety of each language:
    "ITA": "Standard Italian", "NLD": "Standard Dutch (Netherlandic)",
    "LUX": "Luxembourgish", "POL": "Standard Polish", "CZE": "Standard Czech",
    "SVK": "Standard Slovak", "HUN": "Standard Hungarian", "SVN": "Standard Slovene",
    "HRV": "Croatian (Shtokavian)", "BIH": "Bosnian (Shtokavian)",
    "SRB": "Serbian (Shtokavian)", "MNE": "Montenegrin", "MKD": "Standard Macedonian",
    "ALB": "Tosk Albanian", "KOS": "Gheg Albanian", "BGR": "Standard Bulgarian",
    "ROU": "Standard Romanian", "MDA": "Moldovan Romanian", "UKR": "Standard Ukrainian",
    "BLR": "Standard Belarusian", "LTU": "Standard Lithuanian", "LVA": "Standard Latvian",
    "EST": "Standard Estonian", "FIN": "Standard Finnish", "SWE": "Standard Swedish",
    "NOR": "Bokmål Norwegian", "DNK": "Standard Danish", "ISL": "Standard Icelandic",
    "RUS": "Standard Russian", "GRC": "Standard Modern Greek",
    # Middle East / Central Asia:
    "TUR": "Istanbul Turkish", "ISR": "Modern Hebrew", "KAZ": "Standard Kazakh",
    "UZB": "Standard Uzbek", "TKM": "Standard Turkmen", "KGZ": "Standard Kyrgyz",
    "MNG": "Khalkha Mongolian",
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
    # --- Iraq: Shia south / Sunni west / Kurdish north (keys = atlas names) --
    ("IRQ", "basra"): _S(sect="Twelver Shia"),
    ("IRQ", "najaf"): _S(sect="Twelver Shia"),
    ("IRQ", "karbala"): _S(sect="Twelver Shia"),
    ("IRQ", "al muthanna"): _S(sect="Twelver Shia"),
    ("IRQ", "al-qādisiyyah"): _S(sect="Twelver Shia"),
    ("IRQ", "dhi qar"): _S(sect="Twelver Shia"),
    ("IRQ", "maysan"): _S(sect="Twelver Shia"),
    ("IRQ", "wasit"): _S(sect="Twelver Shia"),
    ("IRQ", "babylon"): _S(sect="Twelver Shia"),
    ("IRQ", "al anbar"): _S(sect="Sunni"),
    ("IRQ", "saladin"): _S(sect="Sunni"),
    ("IRQ", "nineveh"): _S(sect="Sunni", language="Arabic"),
    ("IRQ", "erbil"): _S(sect="Sunni", language="Kurdish", dialect="Sorani Kurdish"),
    ("IRQ", "duhok"): _S(sect="Sunni", language="Kurdish", dialect="Kurmanji Kurdish"),
    ("IRQ", "sulaymaniyah"): _S(sect="Sunni", language="Kurdish",
                                dialect="Sorani Kurdish"),
    ("IRQ", "kirkuk"): _S(sect="Sunni", language="Kurdish", dialect="Sorani Kurdish"),
    # --- Nigeria: Muslim north (Sunni/Hausa) / Christian south (SE Catholic-Igbo,
    # SS Protestant); the Yoruba south-west is religiously mixed. All 36 states +
    # FCT, keyed to the atlas's "{name} State" (Lagos & FCT are the exceptions).
    # Far/near north — Hausa-Fulani Muslim:
    ("NGA", "sokoto state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "kebbi state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "zamfara state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "katsina state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "kano state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "jigawa state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "bauchi state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "gombe state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "yobe state"): _S(religion="Islam", sect="Sunni", language="Kanuri"),
    ("NGA", "borno state"): _S(religion="Islam", sect="Sunni", language="Kanuri"),
    ("NGA", "niger state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    # Middle Belt — mixed / Christian-plurality:
    ("NGA", "kaduna state"): _S(religion="Islam", sect="Sunni", language="Hausa"),
    ("NGA", "plateau state"): _S(religion="Christianity", sect="Protestant"),
    ("NGA", "benue state"): _S(religion="Christianity", sect="Catholic", language="Tiv"),
    ("NGA", "nasarawa state"): _S(religion="Christianity", sect="Protestant"),
    ("NGA", "kogi state"): _S(religion="Christianity", sect="Catholic"),
    ("NGA", "kwara state"): _S(religion="Islam", sect="Sunni", language="Yoruba"),
    ("NGA", "adamawa state"): _S(religion="Islam", sect="Sunni"),
    ("NGA", "taraba state"): _S(religion="Christianity", sect="Protestant"),
    ("NGA", "federal capital territory"): _S(religion="Christianity", sect="Catholic"),
    # South-West — Yoruba, Christian/Muslim mix:
    ("NGA", "lagos"): _S(language="Yoruba"),
    ("NGA", "ogun state"): _S(language="Yoruba"),
    ("NGA", "oyo state"): _S(language="Yoruba"),
    ("NGA", "osun state"): _S(language="Yoruba"),
    ("NGA", "ondo state"): _S(religion="Christianity", sect="Protestant", language="Yoruba"),
    ("NGA", "ekiti state"): _S(religion="Christianity", sect="Protestant", language="Yoruba"),
    # South-East — Igbo, Christian (Catholic-heavy):
    ("NGA", "anambra state"): _S(religion="Christianity", sect="Catholic", language="Igbo"),
    ("NGA", "enugu state"): _S(religion="Christianity", sect="Catholic", language="Igbo"),
    ("NGA", "imo state"): _S(religion="Christianity", sect="Catholic", language="Igbo"),
    ("NGA", "abia state"): _S(religion="Christianity", sect="Protestant", language="Igbo"),
    ("NGA", "ebonyi state"): _S(religion="Christianity", sect="Catholic", language="Igbo"),
    # South-South (Niger Delta) — Christian:
    ("NGA", "rivers state"): _S(religion="Christianity", sect="Protestant"),
    ("NGA", "bayelsa state"): _S(religion="Christianity", sect="Protestant"),
    ("NGA", "delta state"): _S(religion="Christianity", sect="Catholic"),
    ("NGA", "edo state"): _S(religion="Christianity", sect="Protestant", language="Edo"),
    ("NGA", "cross river state"): _S(religion="Christianity", sect="Protestant"),
    ("NGA", "akwa ibom state"): _S(religion="Christianity", sect="Protestant"),
    # --- Lebanon / Syria ----------------------------------------------------
    ("LBN", "mount lebanon"): _S(religion="Christianity", sect="Maronite Catholic"),
    ("LBN", "nabatieh"): _S(religion="Islam", sect="Twelver Shia"),
    ("LBN", "south"): _S(religion="Islam", sect="Twelver Shia"),
    ("LBN", "beqaa"): _S(religion="Islam", sect="Twelver Shia"),
    ("SYR", "latakia"): _S(sect="Alawite"),   # v8.16 — distinct sect, not a Shia shade
    ("SYR", "tartus"): _S(sect="Alawite"),
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
    ("CAN", "new brunswick"): _S(dialect="Acadian French / English"),
    # --- Spain: NE 10m ADM1 is PROVINCES, so key the regional languages by the
    # provinces of each autonomous community (Catalonia, Basque Country, Galicia,
    # Valencian Community). ------------------------------------------------------
    ("ESP", "barcelona"): _S(language="Catalan", dialect="Catalan"),
    ("ESP", "girona"): _S(language="Catalan", dialect="Catalan"),
    ("ESP", "lleida"): _S(language="Catalan", dialect="Catalan"),
    ("ESP", "tarragona"): _S(language="Catalan", dialect="Catalan"),
    ("ESP", "biscay"): _S(language="Basque", dialect="Basque"),
    ("ESP", "gipuzkoa"): _S(language="Basque", dialect="Basque"),
    ("ESP", "araba / álava"): _S(language="Basque", dialect="Basque"),
    ("ESP", "a coruña"): _S(language="Galician", dialect="Galician"),
    ("ESP", "lugo"): _S(language="Galician", dialect="Galician"),
    ("ESP", "ourense"): _S(language="Galician", dialect="Galician"),
    ("ESP", "pontevedra"): _S(language="Galician", dialect="Galician"),
    ("ESP", "valencia"): _S(language="Catalan", dialect="Valencian"),
    ("ESP", "castellón"): _S(language="Catalan", dialect="Valencian"),
    ("ESP", "alicante"): _S(language="Catalan", dialect="Valencian"),
    # --- Belgium: NE ADM1 is PROVINCES. Flemish provinces speak Dutch (Flemish);
    # Walloon provinces French; Brussels is bilingual. --------------------------
    ("BEL", "antwerp"): _S(language="Dutch", dialect="Flemish"),
    ("BEL", "east flanders"): _S(language="Dutch", dialect="Flemish"),
    ("BEL", "west flanders"): _S(language="Dutch", dialect="Flemish"),
    ("BEL", "flemish brabant"): _S(language="Dutch", dialect="Flemish"),
    ("BEL", "limburg"): _S(language="Dutch", dialect="Flemish"),
    ("BEL", "hainaut"): _S(language="French", dialect="Belgian French"),
    ("BEL", "liège"): _S(language="French", dialect="Belgian French"),
    ("BEL", "namur"): _S(language="French", dialect="Belgian French"),
    ("BEL", "luxembourg"): _S(language="French", dialect="Belgian French"),
    ("BEL", "walloon brabant"): _S(language="French", dialect="Belgian French"),
    ("BEL", "brussels capital"): _S(language="French", dialect="Belgian French"),
    # --- Switzerland --------------------------------------------------------
    ("CHE", "geneva"): _S(language="French", dialect="Swiss French"),
    ("CHE", "vaud"): _S(language="French", dialect="Swiss French"),
    ("CHE", "ticino"): _S(language="Italian", dialect="Swiss Italian"),
    # --- Russia: Muslim & Buddhist republics (keys are the atlas ADM1 English
    # names, e.g. "Chechen Republic", not "chechnya"). Muslim republics of the
    # North Caucasus + the Volga; the three Buddhist republics.
    ("RUS", "chechen republic"): _S(religion="Islam", sect="Sunni", language="Chechen"),
    ("RUS", "republic of dagestan"): _S(religion="Islam", sect="Sunni", language="Avar"),
    ("RUS", "republic of ingushetia"): _S(religion="Islam", sect="Sunni", language="Ingush"),
    ("RUS", "kabardino-balkaria"): _S(religion="Islam", sect="Sunni", language="Kabardian"),
    ("RUS", "karachay-cherkess republic"): _S(religion="Islam", sect="Sunni",
                                              language="Karachay"),
    ("RUS", "republic of north ossetia-alania"): _S(religion="Christianity",
                                                    sect="Orthodox", language="Ossetian"),
    ("RUS", "republic of tatarstan"): _S(religion="Islam", sect="Sunni", language="Tatar"),
    ("RUS", "bashkortostan"): _S(religion="Islam", sect="Sunni", language="Bashkir"),
    ("RUS", "republic of kalmykia"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                                        language="Kalmyk"),
    ("RUS", "republic of buryatia"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                                        language="Buryat"),
    ("RUS", "tuva republic"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                                 language="Tuvan"),
    ("RUS", "chuvash republic"): _S(language="Chuvash"),
    ("RUS", "sakha republic"): _S(language="Yakut"),
    ("RUS", "mari el republic"): _S(language="Mari"),
    ("RUS", "udmurt republic"): _S(language="Udmurt"),
    ("RUS", "republic of mordovia"): _S(language="Erzya"),
    ("RUS", "komi republic"): _S(language="Komi"),
    ("RUS", "altai republic"): _S(language="Altai"),
    ("RUS", "republic of khakassia"): _S(language="Khakas"),
    ("RUS", "republic of adygea"): _S(religion="Islam", sect="Sunni", language="Adyghe"),
    # --- Ethiopia / Tanzania / Philippines Muslim south ---------------------
    ("ETH", "somali"): _S(religion="Islam", sect="Sunni", language="Somali"),
    ("ETH", "afar"): _S(religion="Islam", sect="Sunni", language="Afar"),
    ("TZA", "mjini magharibi"): _S(religion="Islam", sect="Sunni"),
    ("TZA", "unguja north"): _S(religion="Islam", sect="Sunni"),
    ("TZA", "unguja south"): _S(religion="Islam", sect="Sunni"),
    ("TZA", "north pemba"): _S(religion="Islam", sect="Sunni"),
    ("TZA", "south pemba"): _S(religion="Islam", sect="Sunni"),
    ("PHL", "maguindanao"): _S(religion="Islam", sect="Sunni"),
    ("PHL", "lanao del sur"): _S(religion="Islam", sect="Sunni"),
    ("PHL", "sulu"): _S(religion="Islam", sect="Sunni"),
    # --- Bosnia: NE ADM1 splits into Republika Srpska regions (Serb/Orthodox),
    # Federation cantons (Bosniak/Muslim), and the Croat-majority cantons
    # (Catholic). Keyed to the atlas unit names. --------------------------------
    ("BIH", "banja luka"): _S(religion="Christianity", sect="Orthodox", language="Serbian"),
    ("BIH", "bijeljina"): _S(religion="Christianity", sect="Orthodox", language="Serbian"),
    ("BIH", "doboj"): _S(religion="Christianity", sect="Orthodox", language="Serbian"),
    ("BIH", "foča"): _S(religion="Christianity", sect="Orthodox", language="Serbian"),
    ("BIH", "trebinje"): _S(religion="Christianity", sect="Orthodox", language="Serbian"),
    ("BIH", "vlasenica"): _S(religion="Christianity", sect="Orthodox", language="Serbian"),
    ("BIH", "sarajevo-romanija"): _S(religion="Christianity", sect="Orthodox",
                                     language="Serbian"),
    ("BIH", "sarajevo canton"): _S(religion="Islam", sect="Sunni", language="Bosnian"),
    ("BIH", "tuzla canton"): _S(religion="Islam", sect="Sunni", language="Bosnian"),
    ("BIH", "zenica-doboj canton"): _S(religion="Islam", sect="Sunni", language="Bosnian"),
    ("BIH", "una-sana canton"): _S(religion="Islam", sect="Sunni", language="Bosnian"),
    ("BIH", "bosnian podrinje canton"): _S(religion="Islam", sect="Sunni",
                                           language="Bosnian"),
    ("BIH", "west herzegovina canton"): _S(religion="Christianity", sect="Catholic",
                                           language="Croatian"),
    ("BIH", "posavina canton"): _S(religion="Christianity", sect="Catholic",
                                   language="Croatian"),
    ("BIH", "livno"): _S(religion="Christianity", sect="Catholic", language="Croatian"),
    # --- USA: no religious split, but Louisiana/Utah flavour ----------------
    ("USA", "utah"): _S(sect="Latter-day Saint (LDS)"),
    ("USA", "louisiana"): _S(sect="Catholic"),
    ("USA", "rhode island"): _S(sect="Catholic"),
    # --- v8.12: heterogeneity for the target regions -----------------------
    # Turkey — Kurdish (Kurmanji) south-east; Tunceli is Zaza/Alevi.
    ("TUR", "diyarbakır"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "şırnak"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "mardin"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "van"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "batman"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "siirt"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "muş"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "ağrı"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "bitlis"): _S(language="Kurdish", dialect="Kurmanji Kurdish"),
    ("TUR", "tunceli"): _S(sect="Alevi", language="Kurdish", dialect="Zazaki"),
    # Ukraine — the east/south are predominantly Russian-speaking in daily life.
    ("UKR", "donetsk"): _S(dialect="Russian"),
    ("UKR", "luhansk"): _S(dialect="Russian"),
    ("UKR", "kharkiv"): _S(dialect="Russian / Surzhyk"),
    ("UKR", "zaporizhzhia"): _S(dialect="Russian / Surzhyk"),
    ("UKR", "kherson"): _S(dialect="Russian / Surzhyk"),
    ("UKR", "dnipropetrovsk"): _S(dialect="Russian / Surzhyk"),
    ("UKR", "odessa"): _S(dialect="Russian"),
    # Finland — Ostrobothnia has a large Swedish-speaking minority.
    ("FIN", "ostrobothnia"): _S(language="Swedish", dialect="Finland Swedish"),
    # Kazakhstan — the northern oblasts are Russophone.
    ("KAZ", "north kazakhstan"): _S(language="Russian", dialect="Standard Russian"),
    ("KAZ", "kostanay"): _S(language="Russian", dialect="Standard Russian"),
    ("KAZ", "pavlodar"): _S(language="Russian", dialect="Standard Russian"),
    ("KAZ", "akmola"): _S(language="Russian", dialect="Standard Russian"),
    ("KAZ", "east kazakhstan"): _S(language="Russian", dialect="Standard Russian"),
    # ======================================================================
    # v8.13.7 — a much wider curated sub-national layer (owner: "you might have
    # to add lots of new religions, sects, and languages"). New traditions
    # introduced here: Hinduism outside India (Bali), Theravada Buddhist belts,
    # Ismaili/Alawite/Hazara Shia pockets, Druze, folk/animist traditions, and a
    # long tail of minority languages. All ADM1-keyed, so they now also flow down
    # to div2/div3 via the parent-ADM1 inheritance in routes_geo._unit_level_values.
    # ---------------------------------------------------------------------------
    # Indonesia — Bali is Hindu (a whole new tradition on the map), Aceh strict
    # Sunni, the east (Papua / NTT / N. Sulawesi) Christian, W. Kalimantan mixed.
    ("IDN", "bali"): _S(religion="Hinduism", sect="Balinese Hindu",
                        language="Balinese", dialect="Balinese"),
    ("IDN", "aceh"): _S(religion="Islam", sect="Sunni (Shafi'i, Sharia)",
                        language="Acehnese", dialect="Acehnese"),
    ("IDN", "papua"): _S(religion="Christianity", sect="Protestant", language="Papuan"),
    ("IDN", "west papua"): _S(religion="Christianity", sect="Protestant", language="Papuan"),
    ("IDN", "east nusa tenggara"): _S(religion="Christianity", sect="Catholic"),
    ("IDN", "north sulawesi"): _S(religion="Christianity", sect="Protestant",
                                  language="Minahasan"),
    ("IDN", "north sumatra"): _S(religion="Christianity", sect="Protestant (Batak)",
                                 language="Batak"),
    ("IDN", "west sumatra"): _S(religion="Islam", sect="Sunni", language="Minangkabau"),
    ("IDN", "yogyakarta"): _S(language="Javanese", dialect="Javanese"),
    ("IDN", "central java"): _S(language="Javanese", dialect="Javanese"),
    ("IDN", "west java"): _S(language="Sundanese", dialect="Sundanese"),
    # Myanmar — Buddhist Bamar core, Christian highlands, Muslim Rakhine coast.
    # (v8.14 — keys carry the atlas's " state" suffix; the bare names were dead.)
    ("MMR", "kachin state"): _S(religion="Christianity", sect="Protestant (Baptist)",
                                language="Kachin (Jingpho)"),
    ("MMR", "chin state"): _S(religion="Christianity", sect="Protestant (Baptist)",
                              language="Chin"),
    ("MMR", "kayah state"): _S(religion="Christianity", sect="Catholic",
                               language="Karenni"),
    ("MMR", "kayin state"): _S(religion="Buddhism", sect="Theravada Buddhist",
                               language="Karen"),
    ("MMR", "shan state"): _S(religion="Buddhism", sect="Theravada Buddhist",
                              language="Shan"),
    ("MMR", "rakhine state"): _S(religion="Buddhism", sect="Theravada Buddhist",
                                 language="Rakhine"),
    ("MMR", "mon state"): _S(religion="Buddhism", sect="Theravada Buddhist",
                             language="Mon"),
    # Thailand — the deep south is Malay-Muslim (Sunni), the north-east Isan/Lao.
    ("THA", "pattani"): _S(religion="Islam", sect="Sunni", language="Malay",
                           dialect="Pattani Malay"),
    ("THA", "yala"): _S(religion="Islam", sect="Sunni", language="Malay",
                        dialect="Pattani Malay"),
    ("THA", "narathiwat"): _S(religion="Islam", sect="Sunni", language="Malay",
                              dialect="Pattani Malay"),
    ("THA", "satun"): _S(religion="Islam", sect="Sunni", language="Malay"),
    ("THA", "udon thani"): _S(language="Thai", dialect="Isan (Lao)"),
    ("THA", "khon kaen"): _S(language="Thai", dialect="Isan (Lao)"),
    ("THA", "chiang mai"): _S(language="Thai", dialect="Northern Thai (Lanna)"),
    # China — deeper: Yunnan Dai Theravada, Qinghai Tibetan, Gansu/Ningxia Hui.
    ("CHN", "yunnan"): _S(language="Yi", dialect="Southwestern Mandarin"),
    ("CHN", "qinghai"): _S(religion="Buddhism", sect="Vajrayana Buddhist",
                           language="Tibetan"),
    ("CHN", "gansu"): _S(religion="Islam", sect="Sunni (Hui)"),
    # (v8.14 — Hong Kong / Macau removed: they are NOT CHN ADM1 units in the
    #  atlas — they render as territories with their own pages, so a CHN-keyed
    #  override could never fire. Guangdong's Cantonese entry already exists
    #  above.)
    ("CHN", "fujian"): _S(dialect="Hokkien (Min)"),
    ("CHN", "shanghai"): _S(dialect="Wu (Shanghainese)"),
    ("CHN", "zhejiang"): _S(dialect="Wu"),
    # Iran — Sunni Kurdish west, Sunni Baloch south-east, Arab Khuzestan.
    ("IRN", "kurdistan"): _S(sect="Sunni", language="Kurdish", dialect="Sorani Kurdish"),
    ("IRN", "sistan and baluchestan"): _S(sect="Sunni", language="Balochi",
                                          dialect="Balochi"),
    ("IRN", "khuzestan"): _S(language="Arabic", dialect="Khuzestani Arabic"),
    ("IRN", "west azerbaijan"): _S(language="Azerbaijani", dialect="Azerbaijani"),
    ("IRN", "east azerbaijan"): _S(language="Azerbaijani", dialect="Azerbaijani"),
    ("IRN", "golestan"): _S(sect="Sunni", language="Turkmen"),
    # Afghanistan — the Hazarajat is Twelver Shia (Hazara); north Tajik/Uzbek.
    # (v8.14 — Daykundi removed: Natural Earth's AFG ADM1 layer predates the
    #  province's 2004 split from Urozgan, so the atlas has no such unit and
    #  the key could never fire; Bamyan carries the Hazarajat override.)
    ("AFG", "bamyan"): _S(sect="Twelver Shia", language="Hazaragi"),
    ("AFG", "balkh"): _S(language="Dari", dialect="Dari"),
    ("AFG", "herat"): _S(language="Dari", dialect="Herati Dari"),
    ("AFG", "kandahar"): _S(language="Pashto", dialect="Kandahari Pashto"),
    # Saudi Arabia / Bahrain — Twelver Shia pockets on the Gulf coast.
    ("SAU", "eastern"): _S(sect="Sunni / Twelver Shia (east)"),
    # Sri Lanka — Tamil Hindu north, Muslim east, Sinhala Buddhist south.
    # (v8.14 — LKA's atlas ADM1 is DISTRICTS, not provinces: key the Northern
    #  Province's five districts + the Eastern Province's three individually.)
    ("LKA", "jaffna"): _S(religion="Hinduism", sect="Tamil Hindu",
                          language="Tamil", dialect="Sri Lankan Tamil"),
    ("LKA", "kilinochchi"): _S(religion="Hinduism", sect="Tamil Hindu",
                               language="Tamil", dialect="Sri Lankan Tamil"),
    ("LKA", "mannar"): _S(religion="Hinduism", sect="Tamil Hindu",
                          language="Tamil", dialect="Sri Lankan Tamil"),
    ("LKA", "mullaitivu"): _S(religion="Hinduism", sect="Tamil Hindu",
                              language="Tamil", dialect="Sri Lankan Tamil"),
    ("LKA", "vavuniya"): _S(religion="Hinduism", sect="Tamil Hindu",
                            language="Tamil", dialect="Sri Lankan Tamil"),
    ("LKA", "trincomalee"): _S(religion="Islam", sect="Sunni", language="Tamil"),
    ("LKA", "batticaloa"): _S(religion="Islam", sect="Sunni", language="Tamil"),
    ("LKA", "ampara"): _S(religion="Islam", sect="Sunni", language="Tamil"),
    # India — fill the Hindi belt + more state languages so div2 is dense.
    ("IND", "uttar pradesh"): _S(language="Hindi", dialect="Awadhi / Braj"),
    ("IND", "bihar"): _S(language="Hindi", dialect="Bhojpuri / Maithili"),
    ("IND", "rajasthan"): _S(language="Hindi", dialect="Rajasthani (Marwari)"),
    ("IND", "madhya pradesh"): _S(language="Hindi", dialect="Malvi / Bundeli"),
    ("IND", "chhattisgarh"): _S(language="Hindi", dialect="Chhattisgarhi"),
    ("IND", "jharkhand"): _S(language="Hindi", dialect="Nagpuri"),
    ("IND", "haryana"): _S(language="Hindi", dialect="Haryanvi"),
    ("IND", "himachal pradesh"): _S(language="Hindi", dialect="Pahari"),
    ("IND", "uttarakhand"): _S(language="Hindi", dialect="Garhwali / Kumaoni"),
    ("IND", "tripura"): _S(language="Bengali", dialect="Kokborok / Bengali"),
    # Israel — the north has a large Arab (Muslim/Christian/Druze) population.
    ("ISR", "northern"): _S(religion="Islam", sect="Sunni / Druze",
                            language="Arabic"),
    # Lebanon — add the Druze heartland (Chouf sits in Mount Lebanon already).
    ("SYR", "as-suwayda"): _S(religion="Druze", sect="Druze", language="Arabic"),
    # United Kingdom / France / Italy / Kenya — regions that span MANY atlas
    # ADM1 units (the GB atlas is local authorities, FRA is departments, ITA is
    # provinces, KEN is the former provinces): expanded to every member unit by
    # the _REGION_ALIASES block below the table, so the values live once here.
    # France — the regional/minority languages (Corsica via _REGION_ALIASES).
    # Italy — German South Tyrol, French Aosta, Sardinian Sardinia.
    ("ITA", "trentino-south tyrol"): _S(language="German",
                                        dialect="South Tyrolean German"),
    ("ITA", "aosta"): _S(language="French", dialect="Valdôtain"),
    ("ITA", "sassari"): _S(language="Sardinian", dialect="Sassarese"),
    ("ITA", "cagliari"): _S(language="Sardinian", dialect="Campidanese"),
    ("ITA", "nuoro"): _S(language="Sardinian", dialect="Logudorese"),
    # Ethiopia — the big ethnolinguistic regions + Orthodox/Muslim split.
    ("ETH", "tigray"): _S(religion="Christianity", sect="Oriental Orthodox",
                          language="Tigrinya"),
    ("ETH", "amhara"): _S(religion="Christianity", sect="Oriental Orthodox",
                          language="Amharic"),
    ("ETH", "oromia"): _S(language="Oromo", dialect="Oromo"),
    ("ETH", "harari"): _S(religion="Islam", sect="Sunni", language="Harari"),
    # South Africa — provincial home languages.
    ("ZAF", "kwazulu-natal"): _S(language="Zulu", dialect="Zulu"),
    ("ZAF", "eastern cape"): _S(language="Xhosa", dialect="Xhosa"),
    ("ZAF", "western cape"): _S(language="Afrikaans", dialect="Afrikaans"),
    ("ZAF", "limpopo"): _S(language="Northern Sotho", dialect="Sepedi"),
    ("ZAF", "free state"): _S(language="Southern Sotho", dialect="Sesotho"),
    # Kenya — the coast is Muslim/Swahili; the north-east Somali. (v8.14 — the
    # KEN atlas ADM1 is the eight FORMER PROVINCES, not counties: key those.)
    ("KEN", "coast"): _S(religion="Islam", sect="Sunni", language="Swahili"),
    ("KEN", "north eastern"): _S(religion="Islam", sect="Sunni", language="Somali"),
    # Georgia — Adjara has a large Muslim minority; the south-east is Azeri.
    ("GEO", "adjara"): _S(religion="Islam", sect="Sunni", language="Georgian"),
    # Tanzania mainland vs Zanzibar covered above; add the Swahili coast label.
    # Nepal — the mountainous north is Tibetan-Buddhist. (Atlas uses the old
    # zone names, so Karnali keys "karnali zone".)
    ("NPL", "karnali zone"): _S(religion="Hinduism", sect="Hindu / Tibetan Buddhist"),
    # Vietnam — the Central Highlands host Christian minorities.
    ("VNM", "gia lai"): _S(religion="Christianity", sect="Protestant", language="Jarai"),
    ("VNM", "kon tum"): _S(religion="Christianity", sect="Protestant"),
}

# v8.14 — region → atlas-unit expansion. Some cultural regions span MANY atlas
# ADM1 units under a different naming scheme (the GB atlas is ~220 local
# authorities, France is departments, Italy is provinces), so a single
# "wales"/"scotland"/"corsica" key could never match anything (the exact
# silently-dead-override bug class found in v8.11, reintroduced by v8.13.7 and
# now caught by backend/tests/test_admin_data.py). Each region's value is
# defined ONCE here and expanded onto every member unit; setdefault so a more
# specific per-unit entry above always wins.
_REGION_ALIASES = [
    ("GBR", _S(language="Welsh", dialect="Welsh"), [
        "anglesey", "blaenau gwent", "bridgend", "caerphilly", "cardiff",
        "carmarthenshire", "ceredigion", "conwy", "denbighshire", "flintshire",
        "gwynedd", "merthyr tydfil", "monmouthshire", "neath port talbot",
        "newport", "pembrokeshire", "powys", "rhondda cynon taf", "swansea",
        "torfaen", "vale of glamorgan", "wrexham"]),                 # Wales
    ("GBR", _S(dialect="Scots / Scottish English"), [
        "aberdeen", "aberdeenshire", "angus", "argyll and bute",
        "clackmannanshire", "dumfries and galloway", "dundee", "east ayrshire",
        "east dunbartonshire", "east lothian", "east renfrewshire", "edinburgh",
        "falkirk", "fife", "glasgow", "highland", "inverclyde", "midlothian",
        "moray", "north ayrshire", "north lanarkshire", "orkney islands",
        "outer hebrides", "perth and kinross", "renfrewshire",
        "scottish borders", "shetland islands", "south ayrshire",
        "south lanarkshire", "stirling", "west dunbartonshire",
        "west lothian"]),                                            # Scotland
    ("GBR", _S(sect="Catholic / Protestant (split)"), [
        "antrim", "ards", "armagh", "ballymena", "ballymoney", "banbridge",
        "belfast", "carrickfergus", "castlereagh", "coleraine", "craigavon",
        "derry", "down", "dungannon and south tyrone", "fermanagh", "larne",
        "limavady", "lisburn", "magherafelt", "mid ulster", "moyle",
        "newry and mourne", "newtownabbey", "north down", "omagh",
        "strabane"]),                                                # N. Ireland
    ("FRA", _S(language="Corsican", dialect="Corsican"), [
        "corse-du-sud", "haute-corse"]),                             # Corsica
    ("ITA", _S(language="Sardinian", dialect="Sardinian"), [
        "oristano", "olbia-tempio", "ogliastra", "carbonia-iglesias",
        "medio campidano"]),                                         # Sardinia
]
for _iso3, _val, _names in _REGION_ALIASES:
    for _n in _names:
        SUBNATIONAL.setdefault((_iso3, _n), _val)


# v8.16 — Telugu dialect regions (owner request): the Andhra districts split
# into the three classic dialect belts, Telangana keeps its own variety. Keyed
# by the atlas's district names (div2), which unit_value tries before the ADM1
# parent, so the dialect map paints them at the district tier.
_TELUGU_DIALECTS = [
    ("Uttarandhra Telugu", ["srikakulam", "vizianagaram", "visakhapatnam"]),
    ("Kosta (Coastal) Telugu", ["east godavari", "west godavari", "krishna",
                                "guntur", "prakasam",
                                "sri potti sriramulu nellore"]),
    ("Rayalaseema Telugu", ["chittoor", "kadapa(ysr)", "anantapur", "kurnool"]),
]
for _dia, _districts in _TELUGU_DIALECTS:
    for _d in _districts:
        SUBNATIONAL.setdefault(("IND", _d), _S(language="Telugu", dialect=_dia))
SUBNATIONAL.setdefault(("IND", "telangana"),
                       _S(language="Telugu", dialect="Telangana Telugu"))


# v8.16 — majority-share table for the RELATIVE-percentage shading of the
# religion/sect map modes (owner: "shade by relative percentage"): the share
# of the population the DOMINANT tradition holds (Pew Global Religious
# Landscape / national censuses, rounded). The fill opacity on the map IS this
# share; countries not listed default to 0.85 (a clear majority).
RELIGION_SHARE = {
    # near-uniform
    "SAU": 0.97, "SOM": 0.99, "AFG": 0.99, "IRN": 0.99, "MAR": 0.99,
    "DZA": 0.98, "TUN": 0.99, "YEM": 0.99, "MDV": 0.99, "PAK": 0.96,
    "TUR": 0.98, "AZE": 0.97, "IRQ": 0.96, "JOR": 0.97, "EGY": 0.90,
    "POL": 0.85, "ROU": 0.99, "GRC": 0.90, "ARM": 0.93, "GEO": 0.89,
    "PHL": 0.92, "MEX": 0.94, "BRA": 0.88, "COL": 0.92, "PER": 0.95,
    "ITA": 0.83, "ESP": 0.78, "PRT": 0.85, "IRL": 0.78, "HRV": 0.86,
    "RUS": 0.71, "UKR": 0.78, "SRB": 0.85, "BGR": 0.77, "ISR": 0.74,
    "IND": 0.79, "NPL": 0.81, "THA": 0.93, "MMR": 0.88, "KHM": 0.97,
    "LKA": 0.70, "IDN": 0.87, "MYS": 0.61, "BGD": 0.90,
    # plural / contested landscapes (the map fades accordingly)
    "USA": 0.63, "GBR": 0.46, "FRA": 0.47, "DEU": 0.52, "NLD": 0.41,
    "CAN": 0.53, "AUS": 0.44, "NZL": 0.37, "CHE": 0.62, "AUT": 0.64,
    "CZE": 0.34, "EST": 0.28, "SWE": 0.57, "NOR": 0.68, "DNK": 0.72,
    "JPN": 0.62, "KOR": 0.44, "CHN": 0.52, "TWN": 0.44, "VNM": 0.45,
    "HKG": 0.49, "SGP": 0.31, "PRK": 0.71, "CUB": 0.59, "URY": 0.42,
    "NGA": 0.53, "TZA": 0.61, "ETH": 0.67, "CIV": 0.42, "GHA": 0.71,
    "BIH": 0.51, "LBN": 0.32, "ALB": 0.59, "KAZ": 0.70, "KGZ": 0.88,
    "CMR": 0.69, "TGO": 0.48, "BEN": 0.53, "MUS": 0.49, "SUR": 0.48,
    "GUY": 0.63, "TTO": 0.55, "FJI": 0.64, "MKD": 0.65, "MNE": 0.72,
    "LVA": 0.36, "LTU": 0.77, "HUN": 0.54, "SVK": 0.66, "SVN": 0.73,
    "BLR": 0.73, "MDA": 0.92, "FIN": 0.67, "ISL": 0.67, "BEL": 0.57,
    "LUX": 0.70, "ARG": 0.66, "CHL": 0.55, "VEN": 0.79, "ECU": 0.80,
    "BOL": 0.77, "PRY": 0.89, "ZAF": 0.81, "KEN": 0.85, "UGA": 0.84,
    "ZWE": 0.87, "ZMB": 0.95, "MOZ": 0.57, "AGO": 0.90, "COD": 0.93,
}
_DEFAULT_SHARE = 0.85


def religion_share(iso3):
    return RELIGION_SHARE.get(iso3, _DEFAULT_SHARE)


def country_sect(iso3):
    return COUNTRY_SECT.get(iso3)


def country_dialect(iso3):
    return COUNTRY_DIALECT.get(iso3)


def unit_value(iso3, unit_name, field, country_religion, country_language,
               adm1_name=None):
    """Return the categorical value for one admin unit and one field
    ('religion' | 'sect' | 'language' | 'dialect'), applying the curated
    sub-national override, then falling back to the country value.

    v8.13.7 — `adm1_name` lets a DEEPER-tier unit (div2 district / div3 ward)
    inherit its parent ADM1's override. The SUBNATIONAL table is keyed by ADM1
    name, so without this a div2 district would never pick up "Kerala →
    Malayalam" / "Basra → Twelver Shia" and the sub-national heterogeneity
    vanished the moment you switched from div1 to div2. The unit's OWN name is
    tried first (a rare div2-specific entry wins), then its ADM1 parent.
    """
    override = SUBNATIONAL.get((iso3, (unit_name or "").strip().lower()))
    if not (override and field in override) and adm1_name:
        parent = SUBNATIONAL.get((iso3, (adm1_name or "").strip().lower()))
        if parent and field in parent:
            override = parent
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
