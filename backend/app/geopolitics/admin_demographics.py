"""V8.5/V8.6 — curated PER-UNIT demographics for the administrative atlas (Q4).

V8.0 deferred "province-level demographics": every admin-unit page inherited the
parent COUNTRY's population/GDP (clearly labelled inherited=True). There is no
single global per-province dataset that's cleanly vendorable stdlib, so — exactly
like the leaders/flags floors elsewhere in this codebase — this is a CURATED
knowledge floor of real, recent figures for the world's major first-level units
(states / provinces / governorates), keyed by (iso3, atlas-English-name).

Every entry is a real published figure (census / national-statistics estimate),
with the reference `year` carried so the UI can date it. Population is persons;
`gdp_usd` (nominal, where confidently known for a top economy's unit) is absolute
USD. DENSITY is NOT stored — it's derived at request time from this population
and the unit's own polygon area (geopolitics/admin_atlas area_km2), so it's
always consistent with the geometry actually shown.

This is a FLOOR, not full coverage: a unit not listed here falls back to the
inherited country figure (unchanged behaviour). Extend by adding rows — a unit
drops in as pure data. Names must match the atlas `name` (English-primary:
"Bavaria" not "Bayern"); `_selftest_keys()` (see scripts) checks the match rate.
"""

# (iso3, atlas English name) -> {"pop": persons, "year": yyyy, ["gdp": usd,] "src": "..."}
# Kept alphabetical-ish by country for maintainability.
UNITS = {
    # ---- United States (2020 census / 2023 Census Bureau estimate) -----------
    ("USA", "California"): {"pop": 38965193, "year": 2023, "gdp": 3_900_000_000_000, "src": "US Census / BEA"},
    ("USA", "Texas"): {"pop": 30503301, "year": 2023, "gdp": 2_400_000_000_000, "src": "US Census / BEA"},
    ("USA", "Florida"): {"pop": 22610726, "year": 2023, "gdp": 1_390_000_000_000, "src": "US Census / BEA"},
    ("USA", "New York"): {"pop": 19571216, "year": 2023, "gdp": 2_050_000_000_000, "src": "US Census / BEA"},
    ("USA", "Pennsylvania"): {"pop": 12961683, "year": 2023, "src": "US Census"},
    ("USA", "Illinois"): {"pop": 12549689, "year": 2023, "src": "US Census"},
    ("USA", "Ohio"): {"pop": 11785935, "year": 2023, "src": "US Census"},
    ("USA", "Georgia"): {"pop": 11029227, "year": 2023, "src": "US Census"},
    ("USA", "North Carolina"): {"pop": 10835491, "year": 2023, "src": "US Census"},
    ("USA", "Michigan"): {"pop": 10037261, "year": 2023, "src": "US Census"},
    ("USA", "New Jersey"): {"pop": 9290841, "year": 2023, "src": "US Census"},
    ("USA", "Virginia"): {"pop": 8715698, "year": 2023, "src": "US Census"},
    ("USA", "Washington"): {"pop": 7812880, "year": 2023, "src": "US Census"},
    ("USA", "Arizona"): {"pop": 7431344, "year": 2023, "src": "US Census"},
    ("USA", "Tennessee"): {"pop": 7126489, "year": 2023, "src": "US Census"},
    ("USA", "Massachusetts"): {"pop": 7001399, "year": 2023, "src": "US Census"},
    ("USA", "Indiana"): {"pop": 6862199, "year": 2023, "src": "US Census"},
    ("USA", "Missouri"): {"pop": 6196156, "year": 2023, "src": "US Census"},
    ("USA", "Maryland"): {"pop": 6180253, "year": 2023, "src": "US Census"},
    ("USA", "Colorado"): {"pop": 5877610, "year": 2023, "src": "US Census"},
    ("USA", "Wisconsin"): {"pop": 5910955, "year": 2023, "src": "US Census"},
    ("USA", "Minnesota"): {"pop": 5737915, "year": 2023, "src": "US Census"},
    ("USA", "South Carolina"): {"pop": 5373555, "year": 2023, "src": "US Census"},
    ("USA", "Alabama"): {"pop": 5108468, "year": 2023, "src": "US Census"},
    ("USA", "Louisiana"): {"pop": 4573749, "year": 2023, "src": "US Census"},
    ("USA", "Kentucky"): {"pop": 4526154, "year": 2023, "src": "US Census"},
    ("USA", "Oregon"): {"pop": 4233358, "year": 2023, "src": "US Census"},
    ("USA", "Oklahoma"): {"pop": 4053824, "year": 2023, "src": "US Census"},
    ("USA", "Connecticut"): {"pop": 3617176, "year": 2023, "src": "US Census"},
    ("USA", "Utah"): {"pop": 3417734, "year": 2023, "src": "US Census"},
    ("USA", "Iowa"): {"pop": 3207004, "year": 2023, "src": "US Census"},
    ("USA", "Nevada"): {"pop": 3194176, "year": 2023, "src": "US Census"},
    ("USA", "Arkansas"): {"pop": 3067732, "year": 2023, "src": "US Census"},
    ("USA", "Mississippi"): {"pop": 2939690, "year": 2023, "src": "US Census"},
    ("USA", "Kansas"): {"pop": 2940546, "year": 2023, "src": "US Census"},
    ("USA", "New Mexico"): {"pop": 2114371, "year": 2023, "src": "US Census"},
    ("USA", "Nebraska"): {"pop": 1978379, "year": 2023, "src": "US Census"},
    ("USA", "Idaho"): {"pop": 1964726, "year": 2023, "src": "US Census"},
    ("USA", "West Virginia"): {"pop": 1770071, "year": 2023, "src": "US Census"},
    ("USA", "Hawaii"): {"pop": 1435138, "year": 2023, "src": "US Census"},
    ("USA", "New Hampshire"): {"pop": 1402054, "year": 2023, "src": "US Census"},
    ("USA", "Maine"): {"pop": 1395722, "year": 2023, "src": "US Census"},
    ("USA", "Montana"): {"pop": 1132812, "year": 2023, "src": "US Census"},
    ("USA", "Rhode Island"): {"pop": 1095962, "year": 2023, "src": "US Census"},
    ("USA", "Delaware"): {"pop": 1031890, "year": 2023, "src": "US Census"},
    ("USA", "South Dakota"): {"pop": 919318, "year": 2023, "src": "US Census"},
    ("USA", "North Dakota"): {"pop": 783926, "year": 2023, "src": "US Census"},
    ("USA", "Alaska"): {"pop": 733406, "year": 2023, "src": "US Census"},
    ("USA", "Vermont"): {"pop": 647464, "year": 2023, "src": "US Census"},
    ("USA", "Wyoming"): {"pop": 584057, "year": 2023, "src": "US Census"},

    # ---- Canada (2021 census) ------------------------------------------------
    ("CAN", "Ontario"): {"pop": 14223942, "year": 2021, "src": "StatCan census"},
    ("CAN", "Quebec"): {"pop": 8501833, "year": 2021, "src": "StatCan census"},
    ("CAN", "British Columbia"): {"pop": 5000879, "year": 2021, "src": "StatCan census"},
    ("CAN", "Alberta"): {"pop": 4262635, "year": 2021, "src": "StatCan census"},
    ("CAN", "Manitoba"): {"pop": 1342153, "year": 2021, "src": "StatCan census"},
    ("CAN", "Saskatchewan"): {"pop": 1132505, "year": 2021, "src": "StatCan census"},
    ("CAN", "Nova Scotia"): {"pop": 969383, "year": 2021, "src": "StatCan census"},
    ("CAN", "New Brunswick"): {"pop": 775610, "year": 2021, "src": "StatCan census"},

    # ---- Australia (2021 census / ABS estimate) ------------------------------
    ("AUS", "New South Wales"): {"pop": 8166369, "year": 2021, "src": "ABS census"},
    ("AUS", "Victoria"): {"pop": 6503491, "year": 2021, "src": "ABS census"},
    ("AUS", "Queensland"): {"pop": 5156138, "year": 2021, "src": "ABS census"},
    ("AUS", "Western Australia"): {"pop": 2660026, "year": 2021, "src": "ABS census"},
    ("AUS", "South Australia"): {"pop": 1781516, "year": 2021, "src": "ABS census"},
    ("AUS", "Tasmania"): {"pop": 557571, "year": 2021, "src": "ABS census"},

    # ---- Germany (2022 Destatis) ---------------------------------------------
    ("DEU", "North Rhine-Westphalia"): {"pop": 18139116, "year": 2022, "src": "Destatis"},
    ("DEU", "Bavaria"): {"pop": 13369393, "year": 2022, "src": "Destatis"},
    ("DEU", "Baden-Württemberg"): {"pop": 11280257, "year": 2022, "src": "Destatis"},
    ("DEU", "Lower Saxony"): {"pop": 8140242, "year": 2022, "src": "Destatis"},
    ("DEU", "Hesse"): {"pop": 6391360, "year": 2022, "src": "Destatis"},
    ("DEU", "Saxony"): {"pop": 4086152, "year": 2022, "src": "Destatis"},
    ("DEU", "Berlin"): {"pop": 3755251, "year": 2022, "src": "Destatis"},

    # ---- India (2011 census — the latest full census) ------------------------
    ("IND", "Uttar Pradesh"): {"pop": 199812341, "year": 2011, "src": "Census of India"},
    ("IND", "Maharashtra"): {"pop": 112374333, "year": 2011, "src": "Census of India"},
    ("IND", "Bihar"): {"pop": 104099452, "year": 2011, "src": "Census of India"},
    ("IND", "West Bengal"): {"pop": 91276115, "year": 2011, "src": "Census of India"},
    ("IND", "Madhya Pradesh"): {"pop": 72626809, "year": 2011, "src": "Census of India"},
    ("IND", "Tamil Nadu"): {"pop": 72147030, "year": 2011, "src": "Census of India"},
    ("IND", "Rajasthan"): {"pop": 68548437, "year": 2011, "src": "Census of India"},
    ("IND", "Karnataka"): {"pop": 61095297, "year": 2011, "src": "Census of India"},
    ("IND", "Gujarat"): {"pop": 60439692, "year": 2011, "src": "Census of India"},

    # ---- China (2020 census) -------------------------------------------------
    ("CHN", "Guangdong"): {"pop": 126012510, "year": 2020, "src": "China census"},
    ("CHN", "Shandong"): {"pop": 101527453, "year": 2020, "src": "China census"},
    ("CHN", "Henan"): {"pop": 99365519, "year": 2020, "src": "China census"},
    ("CHN", "Jiangsu"): {"pop": 84748016, "year": 2020, "src": "China census"},
    ("CHN", "Sichuan"): {"pop": 83674866, "year": 2020, "src": "China census"},
    ("CHN", "Hebei"): {"pop": 74610235, "year": 2020, "src": "China census"},

    # ---- Brazil (2022 census — IBGE) -----------------------------------------
    ("BRA", "São Paulo"): {"pop": 44411238, "year": 2022, "src": "IBGE census"},
    ("BRA", "Minas Gerais"): {"pop": 20538718, "year": 2022, "src": "IBGE census"},
    ("BRA", "Rio de Janeiro"): {"pop": 16055174, "year": 2022, "src": "IBGE census"},
    ("BRA", "Bahia"): {"pop": 14141626, "year": 2022, "src": "IBGE census"},
    ("BRA", "Paraná"): {"pop": 11444380, "year": 2022, "src": "IBGE census"},
    ("BRA", "Rio Grande do Sul"): {"pop": 10882965, "year": 2022, "src": "IBGE census"},

    # ---- Mexico (2020 census — INEGI). Atlas names: "State of Mexico" = Estado
    # de México; bare "Mexico" = Mexico City / CDMX (parent of the CDMX boroughs).
    ("MEX", "State of Mexico"): {"pop": 16992418, "year": 2020, "src": "INEGI census"},
    ("MEX", "Mexico"): {"pop": 9209944, "year": 2020, "src": "INEGI census"},
    ("MEX", "Jalisco"): {"pop": 8348151, "year": 2020, "src": "INEGI census"},
    ("MEX", "Veracruz"): {"pop": 8062579, "year": 2020, "src": "INEGI census"},
    ("MEX", "Puebla"): {"pop": 6583278, "year": 2020, "src": "INEGI census"},

    # ---- Nigeria (2006 census / projection). Atlas suffixes most with " State"
    # (but Lagos is bare "Lagos").
    ("NGA", "Lagos"): {"pop": 9113605, "year": 2006, "src": "Nigeria census"},
    ("NGA", "Kano State"): {"pop": 9383682, "year": 2006, "src": "Nigeria census"},
    ("NGA", "Kaduna State"): {"pop": 6113503, "year": 2006, "src": "Nigeria census"},

    # ---- Japan (2020 census). Atlas suffixes most with " Prefecture" (Tokyo is
    # bare; Ōsaka carries the macron Ō).
    ("JPN", "Tokyo"): {"pop": 14047594, "year": 2020, "src": "Japan census"},
    ("JPN", "Kanagawa Prefecture"): {"pop": 9237337, "year": 2020, "src": "Japan census"},
    ("JPN", "Ōsaka Prefecture"): {"pop": 8837685, "year": 2020, "src": "Japan census"},
    ("JPN", "Aichi Prefecture"): {"pop": 7542415, "year": 2020, "src": "Japan census"},

    # ---- Indonesia (2020 census — BPS) ---------------------------------------
    ("IDN", "West Java"): {"pop": 48274162, "year": 2020, "src": "BPS census"},
    ("IDN", "East Java"): {"pop": 40665696, "year": 2020, "src": "BPS census"},
    ("IDN", "Central Java"): {"pop": 36516035, "year": 2020, "src": "BPS census"},
    ("IDN", "Jakarta"): {"pop": 10562088, "year": 2020, "src": "BPS census"},

    # ---- Russia: DELIBERATELY OMITTED — Natural Earth's ADM1 has TWO units both
    # named "Moscow" (the federal city AND the surrounding oblast), so a
    # by-name lookup can't tell them apart without mislabeling one. Russia
    # inherits the country figure until a uid-keyed source is vendored.

    # ---- Argentina (2022 census — INDEC) -------------------------------------
    ("ARG", "Buenos Aires"): {"pop": 17569053, "year": 2022, "src": "INDEC census"},
    ("ARG", "Córdoba"): {"pop": 3978984, "year": 2022, "src": "INDEC census"},

    # ---- South Africa (2022 census — Stats SA) -------------------------------
    ("ZAF", "Gauteng"): {"pop": 15099422, "year": 2022, "src": "Stats SA census"},
    ("ZAF", "KwaZulu-Natal"): {"pop": 12423907, "year": 2022, "src": "Stats SA census"},
    ("ZAF", "Western Cape"): {"pop": 7433019, "year": 2022, "src": "Stats SA census"},

    # ---- Egypt (2017 census / CAPMAS estimate) -------------------------------
    ("EGY", "Cairo"): {"pop": 10044894, "year": 2021, "src": "CAPMAS"},
    ("EGY", "Giza"): {"pop": 9200000, "year": 2021, "src": "CAPMAS"},
    ("EGY", "Alexandria"): {"pop": 5450000, "year": 2021, "src": "CAPMAS"},

    # ===================== v8.6 — widen the floor ============================
    # ---- Russia (2021 census — Rosstat). "Moscow" is DUPLICATED in the atlas
    # (federal city + surrounding oblast) → a list disambiguated by area_hint km².
    ("RUS", "Moscow"): [
        {"pop": 13010112, "year": 2021, "area_hint": 2561, "src": "Rosstat census"},   # federal city
        {"pop": 8524665, "year": 2021, "area_hint": 44329, "src": "Rosstat census"},    # oblast
    ],
    ("RUS", "Saint Petersburg"): {"pop": 5601911, "year": 2021, "src": "Rosstat census"},
    ("RUS", "Krasnodar Krai"): {"pop": 5838273, "year": 2021, "src": "Rosstat census"},
    ("RUS", "Sverdlovsk"): {"pop": 4268998, "year": 2021, "src": "Rosstat census"},
    ("RUS", "Rostov"): {"pop": 4200729, "year": 2021, "src": "Rosstat census"},
    ("RUS", "Republic of Tatarstan"): {"pop": 4004809, "year": 2021, "src": "Rosstat census"},
    ("RUS", "Chelyabinsk"): {"pop": 3442040, "year": 2021, "src": "Rosstat census"},
    ("RUS", "Bashkortostan"): {"pop": 4091423, "year": 2021, "src": "Rosstat census"},
    ("RUS", "Nizhny Novgorod"): {"pop": 3119115, "year": 2021, "src": "Rosstat census"},
    ("RUS", "Samara"): {"pop": 3172925, "year": 2021, "src": "Rosstat census"},

    # ---- United Kingdom: DELIBERATELY OMITTED — the GB atlas ADM1 is the
    # LOCAL-AUTHORITY level (Birmingham, Cornwall, …) with no England/Scotland/
    # Wales/NI units, and its "London" unit is the tiny City of London (the square
    # mile), NOT Greater London. UK units inherit the country figure until a
    # uid-keyed local-authority source is vendored.

    # ---- Germany — the rest of the 16 Länder (2022 Destatis) -----------------
    ("DEU", "Rhineland-Palatinate"): {"pop": 4159150, "year": 2022, "src": "Destatis"},
    ("DEU", "Schleswig-Holstein"): {"pop": 2953270, "year": 2022, "src": "Destatis"},
    ("DEU", "Brandenburg"): {"pop": 2573135, "year": 2022, "src": "Destatis"},
    ("DEU", "Saxony-Anhalt"): {"pop": 2186643, "year": 2022, "src": "Destatis"},
    ("DEU", "Thuringia"): {"pop": 2126846, "year": 2022, "src": "Destatis"},
    ("DEU", "Hamburg"): {"pop": 1892122, "year": 2022, "src": "Destatis"},
    ("DEU", "Mecklenburg-Western Pomerania"): {"pop": 1628378, "year": 2022, "src": "Destatis"},
    ("DEU", "Saarland"): {"pop": 992666, "year": 2022, "src": "Destatis"},
    ("DEU", "Free Hanseatic Bremen"): {"pop": 684864, "year": 2022, "src": "Destatis"},

    # ---- France — biggest departments (2021 INSEE) ---------------------------
    ("FRA", "Nord"): {"pop": 2604361, "year": 2021, "src": "INSEE"},
    ("FRA", "Paris"): {"pop": 2133111, "year": 2021, "src": "INSEE"},
    ("FRA", "Bouches-du-Rhône"): {"pop": 2043110, "year": 2021, "src": "INSEE"},
    ("FRA", "Rhône"): {"pop": 1883437, "year": 2021, "src": "INSEE"},

    # ---- Spain — biggest provinces (2022 INE) --------------------------------
    ("ESP", "Community of Madrid"): {"pop": 6751251, "year": 2022, "src": "INE"},
    ("ESP", "Barcelona"): {"pop": 5714730, "year": 2022, "src": "INE"},
    ("ESP", "Valencia"): {"pop": 2589312, "year": 2022, "src": "INE"},
    ("ESP", "Alicante"): {"pop": 1901594, "year": 2022, "src": "INE"},
    ("ESP", "Seville"): {"pop": 1949371, "year": 2022, "src": "INE"},

    # ---- Italy — biggest provinces (2021 ISTAT) ------------------------------
    ("ITA", "Rome"): {"pop": 4216352, "year": 2021, "src": "ISTAT"},
    ("ITA", "Milan"): {"pop": 3214630, "year": 2021, "src": "ISTAT"},
    ("ITA", "Naples"): {"pop": 2967665, "year": 2021, "src": "ISTAT"},
    ("ITA", "Turin"): {"pop": 2208370, "year": 2021, "src": "ISTAT"},

    # ---- Poland — biggest voivodeships (2021 GUS) ----------------------------
    ("POL", "Masovian Voivodeship"): {"pop": 5425028, "year": 2021, "src": "GUS census"},
    ("POL", "Silesian Voivodeship"): {"pop": 4402687, "year": 2021, "src": "GUS census"},
    ("POL", "Greater Poland Voivodeship"): {"pop": 3496450, "year": 2021, "src": "GUS census"},
    ("POL", "Lesser Poland Voivodeship"): {"pop": 3400577, "year": 2021, "src": "GUS census"},

    # ---- Turkey — biggest provinces (2022 TÜİK) ------------------------------
    ("TUR", "Istanbul"): {"pop": 15907951, "year": 2022, "src": "TÜİK"},
    ("TUR", "Ankara"): {"pop": 5782285, "year": 2022, "src": "TÜİK"},
    ("TUR", "İzmir"): {"pop": 4462056, "year": 2022, "src": "TÜİK"},
    ("TUR", "Bursa"): {"pop": 3194720, "year": 2022, "src": "TÜİK"},

    # ---- Pakistan (2023 census — PBS) ----------------------------------------
    ("PAK", "Punjab"): {"pop": 127688922, "year": 2023, "src": "Pakistan census"},
    ("PAK", "Sindh"): {"pop": 55696147, "year": 2023, "src": "Pakistan census"},
    ("PAK", "Khyber Pakhtunkhwa"): {"pop": 40856097, "year": 2023, "src": "Pakistan census"},
    ("PAK", "Balochistan"): {"pop": 14894402, "year": 2023, "src": "Pakistan census"},

    # ---- Iran (2016 census — SCI) --------------------------------------------
    ("IRN", "Tehran"): {"pop": 13267637, "year": 2016, "src": "Statistical Centre of Iran"},
    ("IRN", "Razavi Khorasan"): {"pop": 6434501, "year": 2016, "src": "Statistical Centre of Iran"},
    ("IRN", "Isfahan"): {"pop": 5120850, "year": 2016, "src": "Statistical Centre of Iran"},
    ("IRN", "Fars"): {"pop": 4851274, "year": 2016, "src": "Statistical Centre of Iran"},

    # ---- Iraq / Saudi Arabia (national-statistics estimates) -----------------
    ("IRQ", "Baghdad"): {"pop": 8126755, "year": 2018, "src": "Iraq CSO"},
    ("SAU", "Riyadh"): {"pop": 8591748, "year": 2022, "src": "GASTAT"},
    ("SAU", "Makkah"): {"pop": 8557766, "year": 2022, "src": "GASTAT"},

    # ---- Indonesia — the rest of the big provinces (2020 BPS) ----------------
    ("IDN", "North Sumatra"): {"pop": 14799361, "year": 2020, "src": "BPS census"},
    ("IDN", "Banten"): {"pop": 11904562, "year": 2020, "src": "BPS census"},
    ("IDN", "South Sulawesi"): {"pop": 9073509, "year": 2020, "src": "BPS census"},

    # ---- Vietnam / Thailand / Philippines / South Korea ----------------------
    ("VNM", "Ho Chi Minh"): {"pop": 8993082, "year": 2019, "src": "Vietnam census"},
    ("VNM", "Hanoi"): {"pop": 8053663, "year": 2019, "src": "Vietnam census"},
    ("THA", "Bangkok"): {"pop": 5527994, "year": 2020, "src": "Thailand NSO"},
    ("KOR", "Gyeonggi"): {"pop": 13427014, "year": 2020, "src": "KOSTAT census"},
    ("KOR", "Seoul"): {"pop": 9586195, "year": 2020, "src": "KOSTAT census"},
    ("KOR", "Busan"): {"pop": 3349016, "year": 2020, "src": "KOSTAT census"},

    # ---- China — the rest of the big provinces (2020 census) -----------------
    ("CHN", "Zhejiang"): {"pop": 64567588, "year": 2020, "src": "China census"},
    ("CHN", "Hunan"): {"pop": 66444864, "year": 2020, "src": "China census"},
    ("CHN", "Anhui"): {"pop": 61027171, "year": 2020, "src": "China census"},
    ("CHN", "Hubei"): {"pop": 57752557, "year": 2020, "src": "China census"},
    ("CHN", "Guangxi"): {"pop": 50126804, "year": 2020, "src": "China census"},
    ("CHN", "Yunnan"): {"pop": 47209277, "year": 2020, "src": "China census"},
    ("CHN", "Jiangxi"): {"pop": 45188635, "year": 2020, "src": "China census"},
    ("CHN", "Liaoning"): {"pop": 42591407, "year": 2020, "src": "China census"},
    ("CHN", "Fujian"): {"pop": 41540086, "year": 2020, "src": "China census"},
    ("CHN", "Shaanxi"): {"pop": 39528999, "year": 2020, "src": "China census"},
    ("CHN", "Shanghai"): {"pop": 24870895, "year": 2020, "src": "China census"},
    ("CHN", "Beijing"): {"pop": 21893095, "year": 2020, "src": "China census"},

    # ---- India — the rest of the big states (2011 census) --------------------
    ("IND", "Andhra Pradesh"): {"pop": 49577103, "year": 2011, "src": "Census of India"},
    ("IND", "Odisha"): {"pop": 41974218, "year": 2011, "src": "Census of India"},
    ("IND", "Kerala"): {"pop": 33406061, "year": 2011, "src": "Census of India"},
    ("IND", "Jharkhand"): {"pop": 32988134, "year": 2011, "src": "Census of India"},
    ("IND", "Assam"): {"pop": 31205576, "year": 2011, "src": "Census of India"},
    ("IND", "Punjab"): {"pop": 27743338, "year": 2011, "src": "Census of India"},
    ("IND", "Chhattisgarh"): {"pop": 25545198, "year": 2011, "src": "Census of India"},
    ("IND", "Haryana"): {"pop": 25351462, "year": 2011, "src": "Census of India"},

    # ---- Brazil — the rest of the big states (2022 IBGE) ---------------------
    ("BRA", "Ceará"): {"pop": 8794957, "year": 2022, "src": "IBGE census"},
    ("BRA", "Pernambuco"): {"pop": 9058931, "year": 2022, "src": "IBGE census"},
    ("BRA", "Pará"): {"pop": 8121025, "year": 2022, "src": "IBGE census"},
    ("BRA", "Santa Catarina"): {"pop": 7610361, "year": 2022, "src": "IBGE census"},
    ("BRA", "Goiás"): {"pop": 7056495, "year": 2022, "src": "IBGE census"},
    ("BRA", "Maranhão"): {"pop": 6776699, "year": 2022, "src": "IBGE census"},
    ("BRA", "Amazonas"): {"pop": 3941613, "year": 2022, "src": "IBGE census"},

    # ---- Mexico — the rest of the big states (2020 INEGI) --------------------
    ("MEX", "Guanajuato"): {"pop": 6166934, "year": 2020, "src": "INEGI census"},
    ("MEX", "Chiapas"): {"pop": 5543828, "year": 2020, "src": "INEGI census"},
    ("MEX", "Nuevo León"): {"pop": 5784442, "year": 2020, "src": "INEGI census"},
    ("MEX", "Michoacán"): {"pop": 4748846, "year": 2020, "src": "INEGI census"},
    ("MEX", "Oaxaca"): {"pop": 4132148, "year": 2020, "src": "INEGI census"},
    ("MEX", "Chihuahua"): {"pop": 3741869, "year": 2020, "src": "INEGI census"},

    # ---- Nigeria — the rest of the big states (2006 census) ------------------
    ("NGA", "Rivers State"): {"pop": 5185400, "year": 2006, "src": "Nigeria census"},
    ("NGA", "Oyo State"): {"pop": 5580894, "year": 2006, "src": "Nigeria census"},
    ("NGA", "Katsina State"): {"pop": 5792578, "year": 2006, "src": "Nigeria census"},
    ("NGA", "Bauchi State"): {"pop": 4653066, "year": 2006, "src": "Nigeria census"},

    # ---- Kenya / Ethiopia / DR Congo / Colombia ------------------------------
    ("KEN", "Nairobi"): {"pop": 4397073, "year": 2019, "src": "Kenya census"},
    ("ETH", "Oromia"): {"pop": 37434197, "year": 2022, "src": "Ethiopia Statistics"},
    ("ETH", "Amhara"): {"pop": 22947630, "year": 2022, "src": "Ethiopia Statistics"},
    ("COL", "Bogotá"): {"pop": 7834167, "year": 2018, "src": "DANE census"},
    ("COL", "Antioquia"): {"pop": 6407102, "year": 2018, "src": "DANE census"},

    # ---- Ukraine — biggest oblasts (2021 estimate). "Kyiv" is DUPLICATED (the
    # capital city + the surrounding oblast) → disambiguated by area like Moscow.
    ("UKR", "Kyiv"): [
        {"pop": 2952301, "year": 2021, "area_hint": 839, "src": "Ukrstat estimate"},    # city
        {"pop": 1781036, "year": 2021, "area_hint": 28131, "src": "Ukrstat estimate"},  # oblast
    ],
    ("UKR", "Kharkiv"): {"pop": 2633834, "year": 2021, "src": "Ukrstat estimate"},
    ("UKR", "Dnipropetrovsk"): {"pop": 3096485, "year": 2021, "src": "Ukrstat estimate"},

    # ---- Argentina / South Africa / Canada / Australia — round out -----------
    ("ARG", "Santa Fe"): {"pop": 3556522, "year": 2022, "src": "INDEC census"},
    ("ARG", "Mendoza"): {"pop": 2014533, "year": 2022, "src": "INDEC census"},
    ("ZAF", "Eastern Cape"): {"pop": 7230204, "year": 2022, "src": "Stats SA census"},
    ("ZAF", "Limpopo"): {"pop": 6572720, "year": 2022, "src": "Stats SA census"},
    ("ZAF", "Mpumalanga"): {"pop": 5143324, "year": 2022, "src": "Stats SA census"},
    ("CAN", "Newfoundland and Labrador"): {"pop": 510550, "year": 2021, "src": "StatCan census"},
    ("AUS", "Australian Capital Territory"): {"pop": 454499, "year": 2021, "src": "ABS census"},
    ("AUS", "Northern Territory"): {"pop": 232605, "year": 2021, "src": "ABS census"},

    # ---- Japan — more prefectures (2020 census) ------------------------------
    ("JPN", "Saitama Prefecture"): {"pop": 7344765, "year": 2020, "src": "Japan census"},
    ("JPN", "Chiba Prefecture"): {"pop": 6284480, "year": 2020, "src": "Japan census"},
    ("JPN", "Hyōgo Prefecture"): {"pop": 5465002, "year": 2020, "src": "Japan census"},
    ("JPN", "Hokkaidō"): {"pop": 5224614, "year": 2020, "src": "Japan census"},
    ("JPN", "Fukuoka Prefecture"): {"pop": 5135214, "year": 2020, "src": "Japan census"},
}


def lookup(iso3, name, area=None):
    """Return the curated demographics for a first-level unit, or None. Match is
    exact on (iso3, atlas English name); the caller derives density from area.

    v8.6 — a value may be a LIST of candidates for a duplicated atlas name (e.g.
    Russia has two ADM1 units both named "Moscow": the federal city and the
    surrounding oblast). When the caller passes the unit's own `area`, the
    candidate whose `area_hint` is closest wins, so each "Moscow" gets the right
    figure; without an area hint the first (primary) candidate is returned."""
    if not iso3 or not name:
        return None
    v = UNITS.get((iso3, name))
    if isinstance(v, list):
        if area is None:
            return v[0]
        return min(v, key=lambda c: abs((c.get("area_hint") or 0) - area))
    return v
