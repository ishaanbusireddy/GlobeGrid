"""v6.1 — additional authoritative country reference data that the owner
flagged as missing gaps: every country's currency, and per-party legislative
seat composition for a parliamentary graphic.

Currencies: ISO 4217 code, common name, symbol — reference data, not
LLM-guessed. Legislatures: lower-house (or unicameral) seat counts by party
for major states, with hex colors for the seat-arc graphic; figures are the
build-time published composition and refresh through the ordinary sync path.
Countries without a detailed legislature entry fall back to the text
composition_summary already seeded.
"""

# iso3 -> (iso4217_code, name, symbol)
CURRENCIES = {
    "AFG": ("AFN", "Afghan afghani", "؋"), "ALB": ("ALL", "Albanian lek", "L"),
    "DZA": ("DZD", "Algerian dinar", "دج"), "AND": ("EUR", "Euro", "€"),
    "AGO": ("AOA", "Angolan kwanza", "Kz"), "ATG": ("XCD", "East Caribbean dollar", "$"),
    "ARG": ("ARS", "Argentine peso", "$"), "ARM": ("AMD", "Armenian dram", "֏"),
    "AUS": ("AUD", "Australian dollar", "$"), "AUT": ("EUR", "Euro", "€"),
    "AZE": ("AZN", "Azerbaijani manat", "₼"), "BHS": ("BSD", "Bahamian dollar", "$"),
    "BHR": ("BHD", "Bahraini dinar", ".د.ب"), "BGD": ("BDT", "Bangladeshi taka", "৳"),
    "BRB": ("BBD", "Barbadian dollar", "$"), "BLR": ("BYN", "Belarusian ruble", "Br"),
    "BEL": ("EUR", "Euro", "€"), "BLZ": ("BZD", "Belize dollar", "$"),
    "BEN": ("XOF", "West African CFA franc", "Fr"), "BTN": ("BTN", "Bhutanese ngultrum", "Nu."),
    "BOL": ("BOB", "Bolivian boliviano", "Bs."), "BIH": ("BAM", "Bosnia-Herzegovina mark", "KM"),
    "BWA": ("BWP", "Botswana pula", "P"), "BRA": ("BRL", "Brazilian real", "R$"),
    "BRN": ("BND", "Brunei dollar", "$"), "BGR": ("BGN", "Bulgarian lev", "лв"),
    "BFA": ("XOF", "West African CFA franc", "Fr"), "BDI": ("BIF", "Burundian franc", "Fr"),
    "KHM": ("KHR", "Cambodian riel", "៛"), "CMR": ("XAF", "Central African CFA franc", "Fr"),
    "CAN": ("CAD", "Canadian dollar", "$"), "CPV": ("CVE", "Cape Verdean escudo", "$"),
    "CAF": ("XAF", "Central African CFA franc", "Fr"), "TCD": ("XAF", "Central African CFA franc", "Fr"),
    "CHL": ("CLP", "Chilean peso", "$"), "CHN": ("CNY", "Chinese yuan (renminbi)", "¥"),
    "COL": ("COP", "Colombian peso", "$"), "COM": ("KMF", "Comorian franc", "Fr"),
    "COG": ("XAF", "Central African CFA franc", "Fr"), "COD": ("CDF", "Congolese franc", "Fr"),
    "CRI": ("CRC", "Costa Rican colón", "₡"), "CIV": ("XOF", "West African CFA franc", "Fr"),
    "HRV": ("EUR", "Euro", "€"), "CUB": ("CUP", "Cuban peso", "$"),
    "CYP": ("EUR", "Euro", "€"), "CZE": ("CZK", "Czech koruna", "Kč"),
    "DNK": ("DKK", "Danish krone", "kr"), "DJI": ("DJF", "Djiboutian franc", "Fr"),
    "DMA": ("XCD", "East Caribbean dollar", "$"), "DOM": ("DOP", "Dominican peso", "$"),
    "ECU": ("USD", "US dollar", "$"), "EGY": ("EGP", "Egyptian pound", "£"),
    "SLV": ("USD", "US dollar", "$"), "GNQ": ("XAF", "Central African CFA franc", "Fr"),
    "ERI": ("ERN", "Eritrean nakfa", "Nfk"), "EST": ("EUR", "Euro", "€"),
    "SWZ": ("SZL", "Swazi lilangeni", "L"), "ETH": ("ETB", "Ethiopian birr", "Br"),
    "FJI": ("FJD", "Fijian dollar", "$"), "FIN": ("EUR", "Euro", "€"),
    "FRA": ("EUR", "Euro", "€"), "GAB": ("XAF", "Central African CFA franc", "Fr"),
    "GMB": ("GMD", "Gambian dalasi", "D"), "GEO": ("GEL", "Georgian lari", "₾"),
    "DEU": ("EUR", "Euro", "€"), "GHA": ("GHS", "Ghanaian cedi", "₵"),
    "GRC": ("EUR", "Euro", "€"), "GRD": ("XCD", "East Caribbean dollar", "$"),
    "GTM": ("GTQ", "Guatemalan quetzal", "Q"), "GIN": ("GNF", "Guinean franc", "Fr"),
    "GNB": ("XOF", "West African CFA franc", "Fr"), "GUY": ("GYD", "Guyanese dollar", "$"),
    "HTI": ("HTG", "Haitian gourde", "G"), "HND": ("HNL", "Honduran lempira", "L"),
    "HUN": ("HUF", "Hungarian forint", "Ft"), "ISL": ("ISK", "Icelandic króna", "kr"),
    "IND": ("INR", "Indian rupee", "₹"), "IDN": ("IDR", "Indonesian rupiah", "Rp"),
    "IRN": ("IRR", "Iranian rial", "﷼"), "IRQ": ("IQD", "Iraqi dinar", "ع.د"),
    "IRL": ("EUR", "Euro", "€"), "ISR": ("ILS", "Israeli new shekel", "₪"),
    "ITA": ("EUR", "Euro", "€"), "JAM": ("JMD", "Jamaican dollar", "$"),
    "JPN": ("JPY", "Japanese yen", "¥"), "JOR": ("JOD", "Jordanian dinar", "د.ا"),
    "KAZ": ("KZT", "Kazakhstani tenge", "₸"), "KEN": ("KES", "Kenyan shilling", "Sh"),
    "KIR": ("AUD", "Australian dollar", "$"), "PRK": ("KPW", "North Korean won", "₩"),
    "KOR": ("KRW", "South Korean won", "₩"), "KWT": ("KWD", "Kuwaiti dinar", "د.ك"),
    "KGZ": ("KGS", "Kyrgyzstani som", "с"), "LAO": ("LAK", "Lao kip", "₭"),
    "LVA": ("EUR", "Euro", "€"), "LBN": ("LBP", "Lebanese pound", "ل.ل"),
    "LSO": ("LSL", "Lesotho loti", "L"), "LBR": ("LRD", "Liberian dollar", "$"),
    "LBY": ("LYD", "Libyan dinar", "ل.د"), "LIE": ("CHF", "Swiss franc", "Fr"),
    "LTU": ("EUR", "Euro", "€"), "LUX": ("EUR", "Euro", "€"),
    "MDG": ("MGA", "Malagasy ariary", "Ar"), "MWI": ("MWK", "Malawian kwacha", "MK"),
    "MYS": ("MYR", "Malaysian ringgit", "RM"), "MDV": ("MVR", "Maldivian rufiyaa", ".ރ"),
    "MLI": ("XOF", "West African CFA franc", "Fr"), "MLT": ("EUR", "Euro", "€"),
    "MHL": ("USD", "US dollar", "$"), "MRT": ("MRU", "Mauritanian ouguiya", "UM"),
    "MUS": ("MUR", "Mauritian rupee", "₨"), "MEX": ("MXN", "Mexican peso", "$"),
    "FSM": ("USD", "US dollar", "$"), "MDA": ("MDL", "Moldovan leu", "L"),
    "MCO": ("EUR", "Euro", "€"), "MNG": ("MNT", "Mongolian tögrög", "₮"),
    "MNE": ("EUR", "Euro", "€"), "MAR": ("MAD", "Moroccan dirham", "د.م."),
    "MOZ": ("MZN", "Mozambican metical", "MT"), "MMR": ("MMK", "Burmese kyat", "K"),
    "NAM": ("NAD", "Namibian dollar", "$"), "NRU": ("AUD", "Australian dollar", "$"),
    "NPL": ("NPR", "Nepalese rupee", "₨"), "NLD": ("EUR", "Euro", "€"),
    "NZL": ("NZD", "New Zealand dollar", "$"), "NIC": ("NIO", "Nicaraguan córdoba", "C$"),
    "NER": ("XOF", "West African CFA franc", "Fr"), "NGA": ("NGN", "Nigerian naira", "₦"),
    "MKD": ("MKD", "Macedonian denar", "ден"), "NOR": ("NOK", "Norwegian krone", "kr"),
    "OMN": ("OMR", "Omani rial", "ر.ع."), "PAK": ("PKR", "Pakistani rupee", "₨"),
    "PLW": ("USD", "US dollar", "$"), "PAN": ("PAB", "Panamanian balboa", "B/."),
    "PNG": ("PGK", "Papua New Guinean kina", "K"), "PRY": ("PYG", "Paraguayan guaraní", "₲"),
    "PER": ("PEN", "Peruvian sol", "S/"), "PHL": ("PHP", "Philippine peso", "₱"),
    "POL": ("PLN", "Polish złoty", "zł"), "PRT": ("EUR", "Euro", "€"),
    "QAT": ("QAR", "Qatari riyal", "ر.ق"), "ROU": ("RON", "Romanian leu", "lei"),
    "RUS": ("RUB", "Russian ruble", "₽"), "RWA": ("RWF", "Rwandan franc", "Fr"),
    "KNA": ("XCD", "East Caribbean dollar", "$"), "LCA": ("XCD", "East Caribbean dollar", "$"),
    "VCT": ("XCD", "East Caribbean dollar", "$"), "WSM": ("WST", "Samoan tālā", "T"),
    "SMR": ("EUR", "Euro", "€"), "STP": ("STN", "São Tomé and Príncipe dobra", "Db"),
    "SAU": ("SAR", "Saudi riyal", "ر.س"), "SEN": ("XOF", "West African CFA franc", "Fr"),
    "SRB": ("RSD", "Serbian dinar", "дин."), "SYC": ("SCR", "Seychellois rupee", "₨"),
    "SLE": ("SLE", "Sierra Leonean leone", "Le"), "SGP": ("SGD", "Singapore dollar", "$"),
    "SVK": ("EUR", "Euro", "€"), "SVN": ("EUR", "Euro", "€"),
    "SLB": ("SBD", "Solomon Islands dollar", "$"), "SOM": ("SOS", "Somali shilling", "Sh"),
    "ZAF": ("ZAR", "South African rand", "R"), "SSD": ("SSP", "South Sudanese pound", "£"),
    "ESP": ("EUR", "Euro", "€"), "LKA": ("LKR", "Sri Lankan rupee", "₨"),
    "SDN": ("SDG", "Sudanese pound", "ج.س."), "SUR": ("SRD", "Surinamese dollar", "$"),
    "SWE": ("SEK", "Swedish krona", "kr"), "CHE": ("CHF", "Swiss franc", "Fr"),
    "SYR": ("SYP", "Syrian pound", "£"), "TJK": ("TJS", "Tajikistani somoni", "ЅМ"),
    "TZA": ("TZS", "Tanzanian shilling", "Sh"), "THA": ("THB", "Thai baht", "฿"),
    "TLS": ("USD", "US dollar", "$"), "TGO": ("XOF", "West African CFA franc", "Fr"),
    "TON": ("TOP", "Tongan paʻanga", "T$"), "TTO": ("TTD", "Trinidad & Tobago dollar", "$"),
    "TUN": ("TND", "Tunisian dinar", "د.ت"), "TUR": ("TRY", "Turkish lira", "₺"),
    "TKM": ("TMT", "Turkmenistani manat", "m"), "TUV": ("AUD", "Australian dollar", "$"),
    "UGA": ("UGX", "Ugandan shilling", "Sh"), "UKR": ("UAH", "Ukrainian hryvnia", "₴"),
    "ARE": ("AED", "UAE dirham", "د.إ"), "GBR": ("GBP", "Pound sterling", "£"),
    "USA": ("USD", "US dollar", "$"), "URY": ("UYU", "Uruguayan peso", "$"),
    "UZB": ("UZS", "Uzbekistani som", "сўм"), "VUT": ("VUV", "Vanuatu vatu", "Vt"),
    "VAT": ("EUR", "Euro", "€"), "VEN": ("VES", "Venezuelan bolívar", "Bs."),
    "VNM": ("VND", "Vietnamese đồng", "₫"), "YEM": ("YER", "Yemeni rial", "﷼"),
    "ZMB": ("ZMW", "Zambian kwacha", "ZK"), "ZWE": ("ZWG", "Zimbabwe gold", "ZiG"),
    # de-facto / disputed states + territories
    "TWN": ("TWD", "New Taiwan dollar", "$"), "XKX": ("EUR", "Euro", "€"),
    "PSE": ("ILS", "Israeli new shekel / Jordanian dinar", "₪"),
    "SOL": ("SOS", "Somali shilling", "Sh"), "CYN": ("TRY", "Turkish lira", "₺"),
    "GRL": ("DKK", "Danish krone", "kr"), "PRI": ("USD", "US dollar", "$"),
    "HKG": ("HKD", "Hong Kong dollar", "$"), "MAC": ("MOP", "Macanese pataca", "MOP$"),
    "NCL": ("XPF", "CFP franc", "Fr"), "PYF": ("XPF", "CFP franc", "Fr"),
    "GUM": ("USD", "US dollar", "$"), "BMU": ("BMD", "Bermudian dollar", "$"),
    "FRO": ("DKK", "Danish krone", "kr"), "ASM": ("USD", "US dollar", "$"),
    "VIR": ("USD", "US dollar", "$"), "CUW": ("ANG", "Netherlands Antillean guilder", "ƒ"),
    "ABW": ("AWG", "Aruban florin", "ƒ"), "CYM": ("KYD", "Cayman Islands dollar", "$"),
    "FLK": ("FKP", "Falkland Islands pound", "£"),
}


# iso3 -> {"chamber": str, "total": int, "note": str,
#          "parties": [(name, seats, hex_color), ...]}  (lower/unicameral house)
# Colors are the parties' conventional political colors so the seat arc reads
# without a legend. Seat figures are the build-snapshot composition.
LEGISLATURES = {
    # v7.3 — Georgia & Armenia parliaments were missing (owner: "why georgia &
    # Armenia parliaments not showing?").
    "GEO": {"chamber": "Parliament of Georgia", "total": 150, "note": "2024 election",
            "parties": [("Georgian Dream", 89, "#1e5aa8"),
                        ("Coalition for Change", 19, "#e4003b"),
                        ("Unity–National Movement", 16, "#c8102e"),
                        ("Strong Georgia", 14, "#f39200"),
                        ("Gakharia for Georgia", 12, "#00a0a0")]},
    "ARM": {"chamber": "National Assembly of Armenia", "total": 107, "note": "2021 election",
            "parties": [("Civil Contract", 71, "#f5a623"),
                        ("Armenia Alliance", 29, "#c8102e"),
                        ("I Have Honor Alliance", 7, "#1e5aa8")]},
    "USA": {"chamber": "House of Representatives", "total": 435, "note": "119th Congress",
            "parties": [("Republican", 220, "#d63b3b"), ("Democratic", 213, "#3b6fd6"),
                        ("Vacant", 2, "#888888")],
            "upper": {"chamber": "Senate", "total": 100, "note": "119th Congress",
                      "parties": [("Republican", 53, "#d63b3b"), ("Democratic", 45, "#3b6fd6"),
                                  ("Independent (caucus D)", 2, "#8a8f98")]}},
    "GBR": {"chamber": "House of Commons", "total": 650, "note": "2024 election",
            "parties": [("Labour", 411, "#e4003b"), ("Conservative", 121, "#0087dc"),
                        ("Liberal Democrats", 72, "#faa61a"), ("SNP", 9, "#fdf38e"),
                        ("Reform UK", 5, "#12b6cf"), ("Greens", 4, "#02a95b"),
                        ("Other", 28, "#888888")],
            "upper": {"chamber": "House of Lords", "total": 805, "note": "appointed",
                      "parties": [("Conservative", 273, "#0087dc"), ("Crossbench", 184, "#888888"),
                                  ("Labour", 187, "#e4003b"), ("Liberal Democrats", 78, "#faa61a"),
                                  ("Other", 83, "#5a5a5a")]}},
    "FRA": {"chamber": "National Assembly", "total": 577, "note": "2024 election",
            "parties": [("New Popular Front (left)", 180, "#e4003b"),
                        ("Ensemble (centre)", 159, "#ffa500"),
                        ("National Rally + allies", 142, "#0d378a"),
                        ("The Republicans", 39, "#0087dc"), ("Other", 57, "#888888")],
            "upper": {"chamber": "Senate", "total": 348, "note": "2023 election",
                      "parties": [("The Republicans", 132, "#0087dc"), ("Socialist", 64, "#e4003b"),
                                  ("Centrist Union", 57, "#ffa500"), ("RDPI (Macron)", 23, "#ffcc00"),
                                  ("Communist/Left", 17, "#c8102e"), ("Other", 55, "#888888")]}},
    "DEU": {"chamber": "Bundestag", "total": 630, "note": "2025 election",
            "parties": [("CDU/CSU", 208, "#000000"), ("AfD", 152, "#009ee0"),
                        ("SPD", 120, "#e4003b"), ("Greens", 85, "#02a95b"),
                        ("The Left", 64, "#be3075"), ("Other", 1, "#888888")]},
    "IND": {"chamber": "Lok Sabha", "total": 543, "note": "2024 election",
            "parties": [("BJP", 240, "#ff9933"), ("INC", 99, "#19aaed"),
                        ("SP", 37, "#e30b5c"), ("TMC", 29, "#20c646"),
                        ("DMK", 22, "#e50000"), ("Other", 116, "#888888")],
            "upper": {"chamber": "Rajya Sabha", "total": 245, "note": "upper house",
                      "parties": [("BJP", 96, "#ff9933"), ("INC", 27, "#19aaed"),
                                  ("TMC", 13, "#20c646"), ("DMK", 10, "#e50000"),
                                  ("AAP", 10, "#0080ff"), ("Other", 89, "#888888")]}},
    "JPN": {"chamber": "House of Representatives", "total": 465, "note": "2024 election",
            "parties": [("LDP", 191, "#4caf50"), ("CDP", 148, "#184589"),
                        ("Ishin", 38, "#93c34b"), ("DPP", 28, "#f8bb2c"),
                        ("Komeito", 24, "#f55b8f"), ("Other", 36, "#888888")],
            "upper": {"chamber": "House of Councillors", "total": 248, "note": "2022 election",
                      "parties": [("LDP", 119, "#4caf50"), ("CDP", 39, "#184589"),
                                  ("Komeito", 27, "#f55b8f"), ("Ishin", 21, "#93c34b"),
                                  ("JCP", 11, "#db001c"), ("Other", 31, "#888888")]}},
    "ITA": {"chamber": "Chamber of Deputies", "total": 400, "note": "2022 election",
            "parties": [("Brothers of Italy", 119, "#1c2d6b"), ("Democratic Party", 69, "#ef1a2d"),
                        ("Five Star Movement", 52, "#ffeb3b"), ("Lega", 66, "#009a49"),
                        ("Forza Italia", 45, "#0087dc"), ("Other", 49, "#888888")],
            "upper": {"chamber": "Senate of the Republic", "total": 200, "note": "2022 election",
                      "parties": [("Brothers of Italy", 66, "#1c2d6b"), ("Democratic Party", 40, "#ef1a2d"),
                                  ("Lega", 30, "#009a49"), ("Five Star Movement", 28, "#ffeb3b"),
                                  ("Forza Italia", 18, "#0087dc"), ("Other", 18, "#888888")]}},
    "CAN": {"chamber": "House of Commons", "total": 343, "note": "2025 election",
            "parties": [("Liberal", 169, "#d71920"), ("Conservative", 144, "#1a4782"),
                        ("Bloc Québécois", 22, "#33b2cc"), ("NDP", 7, "#f37021"),
                        ("Green", 1, "#3d9b35")],
            "upper": {"chamber": "Senate", "total": 105, "note": "appointed",
                      "parties": [("Independent (ISG)", 40, "#3d9b8f"), ("CSG", 20, "#888888"),
                                  ("Conservative", 14, "#1a4782"), ("PSG", 12, "#d71920"),
                                  ("Non-affiliated", 19, "#5a5a5a")]}},
    "AUS": {"chamber": "House of Representatives", "total": 151, "note": "2025 election",
            "parties": [("Labor", 94, "#e13940"), ("Coalition", 43, "#1c4f9c"),
                        ("Greens", 1, "#10c25b"), ("Independent/Other", 13, "#888888")],
            "upper": {"chamber": "Senate", "total": 76, "note": "2025 election",
                      "parties": [("Labor", 28, "#e13940"), ("Coalition", 27, "#1c4f9c"),
                                  ("Greens", 11, "#10c25b"), ("Independent/Other", 10, "#888888")]}},
    "BRA": {"chamber": "Chamber of Deputies", "total": 513, "note": "2022 election",
            "parties": [("PL", 99, "#1f3d7a"), ("PT", 68, "#c4122e"),
                        ("União Brasil", 59, "#005dab"), ("PP", 47, "#2b5fb3"),
                        ("Other", 240, "#888888")],
            "upper": {"chamber": "Federal Senate", "total": 81, "note": "upper house",
                      "parties": [("PL", 15, "#1f3d7a"), ("PSD", 15, "#2b8fb3"),
                                  ("MDB", 12, "#00a34e"), ("União Brasil", 10, "#005dab"),
                                  ("PT", 9, "#c4122e"), ("Other", 20, "#888888")]}},
    "ESP": {"chamber": "Congress of Deputies", "total": 350, "note": "2023 election",
            "parties": [("PP", 137, "#1d84ce"), ("PSOE", 121, "#e30613"),
                        ("Vox", 33, "#63be21"), ("Sumar", 31, "#e51c55"),
                        ("Other", 28, "#888888")],
            "upper": {"chamber": "Senate", "total": 265, "note": "2023 election",
                      "parties": [("PP", 120, "#1d84ce"), ("PSOE", 113, "#e30613"),
                                  ("Other", 32, "#888888")]}},
    "POL": {"chamber": "Sejm", "total": 460, "note": "2023 election",
            "parties": [("PiS", 194, "#000080"), ("Civic Coalition", 157, "#f7941e"),
                        ("Third Way", 65, "#ffd700"), ("The Left", 26, "#e4003b"),
                        ("Confederation", 18, "#22409a")],
            "upper": {"chamber": "Senate", "total": 100, "note": "2023 election",
                      "parties": [("Civic Coalition + pact", 66, "#f7941e"),
                                  ("PiS", 34, "#000080")]}},
    "UKR": {"chamber": "Verkhovna Rada", "total": 450, "note": "2019 election (wartime)",
            "parties": [("Servant of the People", 237, "#00b04f"),
                        ("Opposition Platform", 44, "#1e3a8a"),
                        ("European Solidarity", 27, "#c8102e"),
                        ("Batkivshchyna", 24, "#e30613"), ("Other", 118, "#888888")]},
    "ISR": {"chamber": "Knesset", "total": 120, "note": "2022 election",
            "parties": [("Likud", 32, "#1d4e8f"), ("Yesh Atid", 24, "#00a2e0"),
                        ("Religious Zionism", 14, "#1f3864"), ("Shas", 11, "#000000"),
                        ("Other", 39, "#888888")]},
    "ZAF": {"chamber": "National Assembly", "total": 400, "note": "2024 election",
            "parties": [("ANC", 159, "#007749"), ("DA", 87, "#003f87"),
                        ("MK", 58, "#000000"), ("EFF", 39, "#ff0000"),
                        ("Other", 57, "#888888")]},
    "MEX": {"chamber": "Chamber of Deputies", "total": 500, "note": "2024 election",
            "parties": [("Morena", 253, "#b5261e"), ("PAN", 72, "#0055a5"),
                        ("PRI", 35, "#0f9d58"), ("PT", 51, "#e30613"),
                        ("PVEM", 77, "#4caf50"), ("Other", 12, "#888888")]},
    "KOR": {"chamber": "National Assembly", "total": 300, "note": "2024 election",
            "parties": [("Democratic Party", 170, "#004ea2"), ("People Power", 108, "#e61e2b"),
                        ("Rebuilding Korea", 12, "#00b5e2"), ("Other", 10, "#888888")]},
    "IDN": {"chamber": "People's Representative Council", "total": 580, "note": "2024 election",
            "parties": [("PDI-P", 110, "#e10a1e"), ("Golkar", 102, "#ffdd00"),
                        ("Gerindra", 86, "#8b4513"), ("PKB", 68, "#00913a"),
                        ("Other", 214, "#888888")]},

    # ---- v6.6 — every major legislature incl. one-party / managed systems ----
    "RUS": {"chamber": "State Duma", "total": 450, "note": "2021 election (managed)",
            "parties": [("United Russia", 324, "#005bbb"), ("CPRF", 57, "#cc0000"),
                        ("SRZP", 27, "#ff9900"), ("LDPR", 21, "#3399ff"),
                        ("New People", 13, "#00c2a0"), ("Other", 8, "#888888")],
            "upper": {"chamber": "Federation Council", "total": 178, "note": "appointed",
                      "parties": [("Appointed senators", 178, "#7a8a9a")]}},
    "CHN": {"chamber": "National People's Congress", "total": 2977, "note": "one-party (CCP-led)",
            "parties": [("Communist Party of China", 2091, "#de2910"),
                        ("United-front minor parties", 689, "#f4a460"),
                        ("Independents (approved)", 197, "#888888")]},
    "PRK": {"chamber": "Supreme People's Assembly", "total": 687, "note": "single-list (WPK-led)",
            "parties": [("Workers' Party of Korea", 607, "#cc0000"),
                        ("Social Democratic Party", 50, "#3366cc"),
                        ("Chondoist Chongu Party", 22, "#996633"), ("Other", 8, "#888888")]},
    "IRN": {"chamber": "Islamic Consultative Assembly (Majlis)", "total": 290,
            "note": "2024 election (vetted candidates)",
            "parties": [("Principlists", 233, "#006633"), ("Independents", 41, "#888888"),
                        ("Reformists", 16, "#66cc66")]},
    "CUB": {"chamber": "National Assembly of People's Power", "total": 470,
            "note": "one-party (PCC)",
            "parties": [("Communist Party of Cuba (approved list)", 470, "#cc0000")]},
    "VNM": {"chamber": "National Assembly", "total": 500, "note": "one-party (CPV-led)",
            "parties": [("Communist Party of Vietnam", 462, "#cc0000"),
                        ("Non-party (approved)", 38, "#888888")]},
    "BLR": {"chamber": "House of Representatives", "total": 110, "note": "2024 (managed)",
            "parties": [("Belaya Rus", 51, "#cc0000"), ("Pro-government others", 59, "#888888")]},
    "SYR": {"chamber": "People's Assembly", "total": 250, "note": "transitional (2025)",
            "parties": [("Transitional appointees", 250, "#4a7a4a")]},
    "EGY": {"chamber": "House of Representatives", "total": 596, "note": "2020 election",
            "parties": [("Nation's Future", 316, "#1c4587"), ("Republican People's", 50, "#cc9900"),
                        ("New Wafd", 26, "#009933"), ("Other/Appointed", 204, "#888888")]},
    "SAU": {"chamber": "Consultative Assembly (Shura)", "total": 150, "note": "appointed",
            "parties": [("Appointed members", 150, "#006c35")]},
    "PAK": {"chamber": "National Assembly", "total": 336, "note": "2024 election",
            "parties": [("PTI-backed independents (SIC)", 102, "#00a86b"),
                        ("PML-N", 75, "#008000"), ("PPP", 54, "#000000"),
                        ("MQM-P", 17, "#8b0000"), ("Other", 88, "#888888")]},
    "BGD": {"chamber": "Jatiya Sangsad", "total": 350, "note": "interim period (2024–)",
            "parties": [("Caretaker/vacant (post-2024)", 350, "#7a8a9a")]},
    "NGA": {"chamber": "House of Representatives", "total": 360, "note": "2023 election",
            "parties": [("APC", 175, "#1c4587"), ("PDP", 118, "#00923f"),
                        ("LP", 35, "#d71920"), ("Other", 32, "#888888")]},
    "ETH": {"chamber": "House of Peoples' Representatives", "total": 547, "note": "2021 election",
            "parties": [("Prosperity Party", 454, "#0f47af"), ("NAMA", 5, "#cc9900"),
                        ("Other/vacant", 88, "#888888")]},
    "THA": {"chamber": "House of Representatives", "total": 500, "note": "2023 election",
            "parties": [("Move Forward (People's)", 151, "#f47b20"),
                        ("Pheu Thai", 141, "#cc0000"), ("Bhumjaithai", 71, "#003399"),
                        ("Palang Pracharath", 40, "#1c4587"), ("Other", 97, "#888888")]},
    "PHL": {"chamber": "House of Representatives", "total": 316, "note": "2025 election",
            "parties": [("Lakas–CMD", 105, "#0038a8"), ("NPC", 38, "#fcd116"),
                        ("NUP", 32, "#1c4587"), ("Liberal", 6, "#ce1126"),
                        ("Other/party-list", 135, "#888888")]},
    "MYS": {"chamber": "Dewan Rakyat", "total": 222, "note": "2022 election",
            "parties": [("Pakatan Harapan", 81, "#e21118"), ("Perikatan Nasional", 74, "#003152"),
                        ("Barisan Nasional", 30, "#000080"), ("GPS", 23, "#ffcc00"),
                        ("Other", 14, "#888888")]},
    "ARG": {"chamber": "Chamber of Deputies", "total": 257, "note": "2023 composition",
            "parties": [("Unión por la Patria", 108, "#009fe3"),
                        ("La Libertad Avanza", 38, "#5c2d91"), ("PRO", 37, "#ffd700"),
                        ("UCR", 34, "#e10019"), ("Other", 40, "#888888")]},
    "COL": {"chamber": "Chamber of Representatives", "total": 188, "note": "2022 election",
            "parties": [("Liberal", 32, "#e10019"), ("Historic Pact", 28, "#7b2d8b"),
                        ("Conservative", 27, "#0038a8"), ("La U", 16, "#ff6600"),
                        ("Other", 85, "#888888")]},
    "VEN": {"chamber": "National Assembly", "total": 277, "note": "2020 (disputed)",
            "parties": [("PSUV (GPP)", 253, "#cc0000"), ("Opposition (participating)", 24, "#0038a8")]},
    "NLD": {"chamber": "House of Representatives", "total": 150, "note": "2023 election",
            "parties": [("PVV", 37, "#ffcc00"), ("GL-PvdA", 25, "#cc0000"),
                        ("VVD", 24, "#ff6600"), ("NSC", 20, "#1c4587"),
                        ("D66", 9, "#00b13c"), ("Other", 35, "#888888")]},
    "SWE": {"chamber": "Riksdag", "total": 349, "note": "2022 election",
            "parties": [("Social Democrats", 107, "#e10019"), ("Sweden Democrats", 73, "#005ea1"),
                        ("Moderates", 68, "#52bdec"), ("Left", 24, "#cc0000"),
                        ("Other", 77, "#888888")]},
    "CHE": {"chamber": "National Council", "total": 200, "note": "2023 election",
            "parties": [("SVP", 62, "#008000"), ("SP", 41, "#e10019"),
                        ("FDP", 28, "#0038a8"), ("Centre", 29, "#ff9900"),
                        ("Greens", 23, "#84b414"), ("Other", 17, "#888888")]},
    "GRC": {"chamber": "Hellenic Parliament", "total": 300, "note": "2023 election",
            "parties": [("New Democracy", 158, "#0038a8"), ("SYRIZA", 47, "#e75294"),
                        ("PASOK", 32, "#009150"), ("KKE", 21, "#cc0000"),
                        ("Other", 42, "#888888")]},
    # 2026 election — TISZA (Péter Magyar) ends 16 years of Fidesz government.
    "HUN": {"chamber": "National Assembly", "total": 199, "note": "2026 election",
            "parties": [("TISZA", 120, "#0a5c9e"), ("Fidesz–KDNP", 63, "#ff6600"),
                        ("Mi Hazánk", 10, "#00694e"), ("DK / opposition", 6, "#0038a8")]},
    "CZE": {"chamber": "Chamber of Deputies", "total": 200, "note": "2021 election",
            "parties": [("SPOLU", 71, "#0038a8"), ("ANO", 72, "#00c2e8"),
                        ("PirStan", 37, "#000000"), ("SPD", 20, "#1c4587")]},
    "KAZ": {"chamber": "Mäjilis", "total": 98, "note": "2023 election",
            "parties": [("Amanat", 62, "#00afca"), ("Auyl", 8, "#008000"),
                        ("Ak Zhol", 6, "#ffcc00"), ("Other", 22, "#888888")]},
    "IRQ": {"chamber": "Council of Representatives", "total": 329, "note": "2021 election",
            "parties": [("Sadrist (resigned 2022)", 73, "#000000"),
                        ("SoL/Coordination Framework", 130, "#006633"),
                        ("Taqaddum", 37, "#1c4587"), ("KDP", 31, "#ffcc00"),
                        ("Other", 58, "#888888")]},
    "AFG": {"chamber": "No elected legislature", "total": 0,
            "note": "Islamic Emirate — parliament dissolved 2021", "parties": []},
    "TUR": {"chamber": "Grand National Assembly", "total": 600, "note": "2023 election",
            "parties": [("AKP", 268, "#e5941b"), ("CHP", 169, "#e30613"),
                        ("DEM Party", 61, "#8a2be2"), ("MHP", 50, "#c8102e"),
                        ("Other", 52, "#888888")]},
    # v6.6.2 — democracies the owner flagged as still blank (Mongolia, Finland)
    # plus other common omissions, so their legislature graphic renders too.
    "MNG": {"chamber": "State Great Khural", "total": 126, "note": "2024 election",
            "parties": [("MPP", 68, "#d21f26"), ("Democratic Party", 42, "#25a0da"),
                        ("HUN Party", 8, "#2e7d32"), ("Other", 8, "#888888")]},
    "FIN": {"chamber": "Eduskunta", "total": 200, "note": "2023 election",
            "parties": [("National Coalition", 48, "#006288"), ("Finns Party", 46, "#ffd700"),
                        ("SDP", 43, "#e11931"), ("Centre", 23, "#01954b"),
                        ("Greens", 13, "#61bf1a"), ("Left Alliance", 11, "#f0463c"),
                        ("Other", 16, "#888888")]},
    "NOR": {"chamber": "Storting", "total": 169, "note": "2021 election",
            "parties": [("Labour", 48, "#e4003b"), ("Conservative", 36, "#0087dc"),
                        ("Centre", 28, "#01954b"), ("Progress", 21, "#004f9f"),
                        ("SV", 13, "#e30613"), ("Other", 23, "#888888")]},
    "DNK": {"chamber": "Folketing", "total": 179, "note": "2022 election",
            "parties": [("Social Democrats", 50, "#e4003b"), ("Liberals (V)", 23, "#0057b8"),
                        ("Moderates", 16, "#7b3f99"), ("SF", 15, "#e30613"),
                        ("Other", 75, "#888888")]},
    "AUT": {"chamber": "National Council", "total": 183, "note": "2024 election",
            "parties": [("FPÖ", 57, "#0d3b82"), ("ÖVP", 51, "#63c3d0"),
                        ("SPÖ", 41, "#e4003b"), ("NEOS", 18, "#e84188"),
                        ("Greens", 16, "#88b626")]},
    "BEL": {"chamber": "Chamber of Representatives", "total": 150, "note": "2024 election",
            "parties": [("N-VA", 24, "#ffcd00"), ("Vlaams Belang", 20, "#ffe500"),
                        ("MR", 20, "#1560bd"), ("PS", 16, "#e4003b"),
                        ("Other", 70, "#888888")]},
    "PRT": {"chamber": "Assembly of the Republic", "total": 230, "note": "2024 election",
            "parties": [("PSD (AD)", 80, "#f57e20"), ("PS", 78, "#e4003b"),
                        ("Chega", 50, "#202056"), ("IL", 8, "#00adef"),
                        ("Other", 14, "#888888")]},
    "IRL": {"chamber": "Dáil Éireann", "total": 174, "note": "2024 election",
            "parties": [("Fianna Fáil", 48, "#66bb66"), ("Sinn Féin", 39, "#326760"),
                        ("Fine Gael", 38, "#6699ff"), ("Other", 49, "#888888")]},
    "NZL": {"chamber": "House of Representatives", "total": 123, "note": "2023 election",
            "parties": [("National", 49, "#00529f"), ("Labour", 34, "#d82c20"),
                        ("Green", 15, "#098137"), ("ACT", 11, "#ffd700"),
                        ("NZ First", 8, "#000000"), ("Other", 6, "#888888")]},
    # v8.14 — Update-2 legislature batch: the countries whose latest elections
    # (2021-2025) had no seat-arc at all. Each composition is the certified
    # result of the election named in `note`.
    "LKA": {"chamber": "Parliament of Sri Lanka", "total": 225, "note": "2024 election",
            "parties": [("NPP", 159, "#c4022b"), ("SJB", 40, "#0f7a3d"),
                        ("ITAK", 8, "#f2c500"), ("NDF", 5, "#1560bd"),
                        ("Other", 13, "#888888")]},
    "ROU": {"chamber": "Chamber of Deputies", "total": 331, "note": "2024 election",
            "parties": [("PSD", 86, "#e4003b"), ("AUR", 63, "#f5b800"),
                        ("PNL", 49, "#f5d000"), ("USR", 40, "#00aeef"),
                        ("SOS", 28, "#7a1f7a"), ("POT", 24, "#5a3fbf"),
                        ("UDMR", 22, "#0f7a3d"), ("Minorities", 19, "#888888")]},
    "BGR": {"chamber": "National Assembly", "total": 240, "note": "Oct 2024 election",
            "parties": [("GERB-SDS", 69, "#1560bd"), ("PP-DB", 37, "#00aeef"),
                        ("Vazrazhdane", 35, "#0d3b2e"), ("DPS-New Beginning", 30, "#7b3f99"),
                        ("BSP", 20, "#e4003b"), ("APS", 19, "#9060c0"),
                        ("ITN", 18, "#00b5ad"), ("MECH", 12, "#888888")]},
    "TWN": {"chamber": "Legislative Yuan", "total": 113, "note": "2024 election",
            "parties": [("KMT", 52, "#000095"), ("DPP", 51, "#1b9431"),
                        ("TPP", 8, "#28c8c8"), ("Independent", 2, "#888888")]},
    # v8.16 — limited-recognition states with real elected legislatures get the
    # graphic too (owner: "if taiwan or another limited recognition state has a
    # legislature, the graphic should be shown"). Each sums to its total.
    "XKX": {"chamber": "Assembly of Kosovo", "total": 120, "note": "Feb 2025 election",
            "parties": [("Vet\u00ebvendosje", 48, "#d52b1e"), ("PDK", 24, "#1560bd"),
                        ("LDK", 20, "#003893"), ("AAK\u2013Nisma", 8, "#e2001a"),
                        ("Srpska Lista", 10, "#c00000"), ("Other minorities", 10, "#888888")]},
    "CYN": {"chamber": "Assembly of the Republic", "total": 50, "note": "2022 election",
            "parties": [("UBP", 24, "#e30a17"), ("CTP", 18, "#ef7d00"),
                        ("DP", 3, "#0f7bc4"), ("YDP", 3, "#00a651"),
                        ("HP", 2, "#5b2d8e")]},
    "SOL": {"chamber": "House of Representatives", "total": 82, "note": "2021 election",
            "parties": [("Waddani", 31, "#f7a800"), ("Kulmiye", 30, "#009a44"),
                        ("UCID", 21, "#0072c6")]},
    "SGP": {"chamber": "Parliament of Singapore", "total": 97, "note": "2025 election (elected seats)",
            "parties": [("PAP", 87, "#0032a0"), ("Workers' Party", 10, "#00a5e5")]},
    "SRB": {"chamber": "National Assembly", "total": 250, "note": "Dec 2023 election",
            "parties": [("SNS-led coalition", 129, "#2054a6"), ("SPN (opposition)", 65, "#e05020"),
                        ("SPS-led", 18, "#e4003b"), ("Other", 38, "#888888")]},
    "HRV": {"chamber": "Sabor", "total": 151, "note": "2024 election",
            "parties": [("HDZ-led", 61, "#1560bd"), ("SDP-led (Rivers of Justice)", 42, "#e4003b"),
                        ("Homeland Movement", 14, "#101a4a"), ("Most", 11, "#0d6a9e"),
                        ("Možemo!", 10, "#3dbf3d"), ("Other", 13, "#888888")]},
    "UZB": {"chamber": "Legislative Chamber", "total": 150, "note": "2024 election",
            "parties": [("UzLiDeP", 64, "#1560bd"), ("Milliy Tiklanish", 29, "#0d8a4a"),
                        ("Adolat SDP", 21, "#e4a000"), ("PDP", 20, "#c43a2b"),
                        ("Ecological Party", 16, "#3dbf3d")]},
    "AZE": {"chamber": "Milli Majlis", "total": 125, "note": "2024 election",
            "parties": [("New Azerbaijan Party", 68, "#1560bd"),
                        ("Independents", 44, "#888888"), ("Other", 13, "#aaaaaa")]},
    "JOR": {"chamber": "House of Representatives", "total": 138, "note": "Sept 2024 election",
            "parties": [("Islamic Action Front", 31, "#0d7a3d"), ("Mithaq", 21, "#1560bd"),
                        ("Eradah", 19, "#7b3f99"), ("Other/centrist lists", 67, "#888888")]},
    "PER": {"chamber": "Congress of the Republic", "total": 130, "note": "2021 election",
            "parties": [("Perú Libre", 37, "#c4022b"), ("Fuerza Popular", 24, "#f57e20"),
                        ("Acción Popular", 16, "#000000"), ("APP", 15, "#00aeef"),
                        ("Other", 38, "#888888")]},
}

# v6.6.2 — countries WITHOUT an ordinary elected legislature (or with an
# appointed/advisory body): explain what governs law-making and why, instead of
# leaving the panel blank (owner: "explain to the user why the country doesn't
# have one and if it used to ever have one and why it was abolished").
LEGISLATURE_NOTES = {
    # v8.16 — limited-recognition states without a functioning party graphic
    "PSE": "The Palestinian Legislative Council has been suspended since 2007; "
           "no functioning elected legislature to chart.",
    "ABK": "35-seat People's Assembly — elections are largely non-partisan "
           "(single-member districts), so there is no party seat-arc to chart.",
    "OST": "34-seat Parliament — recognized by very few states; recent "
           "compositions are contested, so no seat-arc is charted.",
    "SAU": "No elected legislature. The appointed Consultative Assembly (Majlis "
           "al-Shura, 150 members) advises the King but cannot pass laws; Saudi "
           "Arabia is an absolute monarchy where the King and Council of "
           "Ministers hold legislative authority by royal decree.",
    "ARE": "The Federal National Council (40 members, half elected by a limited "
           "electoral college since 2006) is consultative only. The UAE is a "
           "federation of absolute monarchies; binding legislation rests with "
           "the Federal Supreme Council of rulers.",
    "QAT": "The Shura Council (45 members) became partly elected in 2021, but "
           "the Emir retains veto and appoints a third of members; real "
           "legislative power remains with the ruling Al Thani monarchy.",
    "OMN": "The Council of Oman is bicameral but largely advisory: the elected "
           "Consultative Assembly (Majlis al-Shura) and appointed State Council "
           "advise the Sultan, who legislates by royal decree.",
    "BRN": "Brunei's Legislative Council (33 members) is entirely appointed by "
           "the Sultan and advisory only. The elected body was suspended in "
           "1984; Brunei is an absolute monarchy under a state of emergency in "
           "force since 1962.",
    "VAT": "Vatican City is an absolute elective monarchy. Legislative power is "
           "held by the Pope and exercised through the Pontifical Commission; "
           "there is no popularly elected legislature.",
    "AFG": "Afghanistan's bicameral National Assembly was dissolved when the "
           "Taliban took power in August 2021. There is currently no "
           "functioning legislature; rule is by decree from the Taliban's "
           "supreme leadership pending an undefined future structure.",
    "PRK": "The Supreme People's Assembly nominally legislates but is a "
           "single-party rubber-stamp body that meets briefly and ratifies "
           "decisions of the ruling Workers' Party under the Kim leadership.",
    "ERI": "Eritrea's National Assembly has not convened since 2002. No "
           "national elections have been held since independence (1993); the "
           "PFDJ one-party state governs by executive authority.",
    # v8.14 — parliaments in suspension/transition, explained instead of shown
    # with a stale seat arc.
    "KWT": "Kuwait's National Assembly — historically the Gulf's most "
           "assertive elected parliament — was dissolved by the Emir in May "
           "2024, with parts of the constitution suspended for up to four "
           "years. Legislation currently proceeds by decree through the Emir "
           "and Council of Ministers.",
    "MMR": "Myanmar's elected Assembly of the Union was overthrown in the "
           "February 2021 military coup. The junta's State Administration "
           "Council rules by decree; the ousted legislators' NUG operates in "
           "exile and no internationally recognized parliament is seated.",
    "NPL": "Nepal's House of Representatives was dissolved in September 2025 "
           "amid the youth-led protest movement that brought down the "
           "government; an interim administration under Sushila Karki was "
           "appointed and fresh elections were scheduled for March 2026. A "
           "new seat composition will be shown once certified results are "
           "vendored.",
}


# v7.4.1 — the FULL language picture per country (owner: "after the language,
# add other languages and list ALL of the languages in that country"). These are
# the significant languages actually spoken — national, regional, minority and
# major immigrant/lingua-franca tongues — beyond the one or two official ones in
# COUNTRY_STATS. Curated from Ethnologue / national census summaries. Countries
# not listed fall back (in the route) to the remaining COUNTRY_STATS languages,
# so the "other languages" row is never empty.
COUNTRY_OTHER_LANGUAGES = {
    "IND": ["Hindi", "English", "Bengali", "Marathi", "Telugu", "Tamil", "Gujarati",
            "Urdu", "Kannada", "Odia", "Malayalam", "Punjabi", "Assamese", "Maithili",
            "Santali", "Kashmiri", "Nepali", "Konkani", "Sindhi", "Manipuri"],
    "CHN": ["Mandarin Chinese", "Yue (Cantonese)", "Wu (Shanghainese)", "Min", "Hakka",
            "Xiang", "Gan", "Uyghur", "Tibetan", "Mongolian", "Zhuang", "Korean"],
    "USA": ["English", "Spanish", "Chinese", "Tagalog", "Vietnamese", "Arabic", "French",
            "Korean", "Russian", "German", "Haitian Creole", "Hindi", "Portuguese", "Navajo"],
    "NGA": ["English", "Hausa", "Yoruba", "Igbo", "Fulfulde", "Ibibio", "Kanuri",
            "Tiv", "Nigerian Pidgin"],
    "ZAF": ["Zulu", "Xhosa", "Afrikaans", "English", "Northern Sotho", "Tswana", "Sotho",
            "Tsonga", "Swazi", "Venda", "Ndebele"],
    "RUS": ["Russian", "Tatar", "Chechen", "Bashkir", "Chuvash", "Avar", "Ukrainian",
            "Armenian", "Yakut", "Ossetian", "Buryat", "Kabardian"],
    "PAK": ["Urdu", "Punjabi", "Pashto", "Sindhi", "Saraiki", "Balochi", "Hindko",
            "Brahui", "English"],
    "IDN": ["Indonesian", "Javanese", "Sundanese", "Madurese", "Minangkabau", "Buginese",
            "Balinese", "Acehnese", "Batak", "Betawi"],
    "PHL": ["Filipino (Tagalog)", "English", "Cebuano", "Ilocano", "Hiligaynon", "Waray",
            "Kapampangan", "Bikol", "Pangasinan", "Maranao"],
    "ETH": ["Amharic", "Oromo", "Somali", "Tigrinya", "Sidamo", "Wolaytta", "Afar",
            "Gurage", "English"],
    "COD": ["French", "Lingala", "Swahili", "Kikongo", "Tshiluba"],
    "MEX": ["Spanish", "Nahuatl", "Yucatec Maya", "Mixtec", "Zapotec", "Otomí", "Tzeltal",
            "Tzotzil"],
    "CAN": ["English", "French", "Punjabi", "Mandarin", "Cantonese", "Spanish", "Tagalog",
            "Arabic", "Italian", "Cree", "Inuktitut"],
    "AUS": ["English", "Mandarin", "Arabic", "Vietnamese", "Cantonese", "Punjabi", "Greek",
            "Italian", "Australian Aboriginal languages"],
    "GBR": ["English", "Welsh", "Scots", "Scottish Gaelic", "Irish", "Polish", "Punjabi",
            "Urdu", "Bengali"],
    "FRA": ["French", "Occitan", "Alsatian", "Breton", "Corsican", "Basque", "Catalan",
            "Arabic", "Portuguese"],
    "ESP": ["Spanish (Castilian)", "Catalan", "Galician", "Basque", "Valencian", "Aranese"],
    "DEU": ["German", "Turkish", "Russian", "Polish", "Kurdish", "Arabic", "Low German",
            "Sorbian"],
    "AFG": ["Dari (Persian)", "Pashto", "Uzbek", "Turkmen", "Balochi", "Nuristani", "Pashai"],
    "IRN": ["Persian (Farsi)", "Azerbaijani", "Kurdish", "Gilaki", "Mazandarani", "Luri",
            "Arabic", "Balochi", "Turkmen"],
    "IRQ": ["Arabic", "Kurdish", "Turkmen", "Assyrian Neo-Aramaic", "Persian"],
    "TUR": ["Turkish", "Kurdish (Kurmanji)", "Zazaki", "Arabic", "Circassian", "Laz"],
    "KEN": ["Swahili", "English", "Kikuyu", "Luhya", "Luo", "Kalenjin", "Kamba", "Somali"],
    "TZA": ["Swahili", "English", "Sukuma", "Chagga", "Nyamwezi", "Haya", "Makonde"],
    "UGA": ["English", "Swahili", "Luganda", "Runyankole", "Acholi", "Lango", "Lugbara"],
    "SDN": ["Arabic", "English", "Beja", "Fur", "Nubian", "Zaghawa"],
    "MAR": ["Arabic", "Berber (Tamazight)", "French", "Hassaniya Arabic", "Spanish"],
    "DZA": ["Arabic", "Berber (Tamazight)", "French", "Kabyle"],
    "EGY": ["Arabic", "Egyptian Arabic", "Coptic", "Nubian", "Beja", "English"],
    "BRA": ["Portuguese", "German (Hunsrückisch)", "Italian (Talian)", "Japanese", "Guarani",
            "Tikuna", "indigenous Amazonian languages"],
    "PER": ["Spanish", "Quechua", "Aymara", "Asháninka", "indigenous Amazonian languages"],
    "BOL": ["Spanish", "Quechua", "Aymara", "Guaraní", "36 recognized indigenous languages"],
    "SWZ": ["Swazi (siSwati)", "English"],
    "NPL": ["Nepali", "Maithili", "Bhojpuri", "Tharu", "Tamang", "Newar", "Magar"],
    "MMR": ["Burmese", "Shan", "Karen", "Rakhine", "Mon", "Kachin", "Chin"],
    "VNM": ["Vietnamese", "Tày", "Mường", "Khmer", "Hmong", "Chinese", "Cham"],
    "THA": ["Thai", "Isan (Lao)", "Northern Thai", "Malay", "Khmer", "Karen"],
    "UKR": ["Ukrainian", "Russian", "Crimean Tatar", "Hungarian", "Romanian", "Polish"],
    "CHE": ["German", "French", "Italian", "Romansh"],
    "BEL": ["Dutch (Flemish)", "French", "German"],
    "SGP": ["English", "Mandarin", "Malay", "Tamil"],
    "LKA": ["Sinhala", "Tamil", "English"],
    "BGD": ["Bengali", "Chittagonian", "Sylheti", "Chakma", "English"],
    "GHA": ["English", "Akan (Twi)", "Ewe", "Ga", "Dagbani", "Hausa"],
    "CMR": ["French", "English", "Fulfulde", "Ewondo", "Duala", "Cameroonian Pidgin"],
    "AGO": ["Portuguese", "Umbundu", "Kimbundu", "Kikongo", "Chokwe"],
}

# v6.6 — current bloc secretaries-general / presidents for the bloc panels
ALLIANCE_LEADERS = {
    "NATO": ("Mark Rutte", "Secretary General", "2024-10-01"),
    "European Union": ("Ursula von der Leyen", "Commission President", "2019-12-01"),
    "CSTO": ("Imangali Tasmagambetov", "Secretary General", "2023-01-01"),
    "Arab League": ("Ahmed Aboul Gheit", "Secretary-General", "2016-07-03"),
    "ASEAN": ("Kao Kim Hourn", "Secretary-General", "2023-01-01"),
    "African Union": ("Mahmoud Ali Youssouf", "Commission Chairperson", "2025-02-15"),
    "OPEC": ("Haitham al-Ghais", "Secretary General", "2022-08-01"),
    "SCO": ("Nurlan Yermekbayev", "Secretary-General", "2025-01-01"),
    "UN": ("António Guterres", "Secretary-General", "2017-01-01"),
}

# v7.6 — real bloc flags/emblems (owner: "use real flags and logos for bloc
# panels"). Wikimedia Special:FilePath resolves the current image; a missing one
# degrades to the placeholder. Keyed by the alliances-table `name`.
def _alliance_emblem(fname: str) -> str:
    from urllib.parse import quote
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(fname)

ALLIANCE_EMBLEMS = {
    "NATO": _alliance_emblem("Flag of NATO.svg"),
    "European Union": _alliance_emblem("Flag of Europe.svg"),
    "African Union": _alliance_emblem("Flag of the African Union.svg"),
    "ASEAN": _alliance_emblem("Flag of ASEAN.svg"),
    "Arab League": _alliance_emblem("Flag of the Arab League.svg"),
    "CSTO": _alliance_emblem("Collective Security Treaty Organization (orthographic projection).svg"),
    "SCO": _alliance_emblem("Flag of the Shanghai Cooperation Organisation.svg"),
    "BRICS": _alliance_emblem("Flag of BRICS.svg"),
    "OPEC": _alliance_emblem("Flag of OPEC.svg"),
    "Mercosur": _alliance_emblem("Mercosur logo.svg"),
    "GCC": _alliance_emblem("Flag of the Cooperation Council for the Arab States of the Gulf.svg"),
    "Gulf Cooperation Council": _alliance_emblem("Flag of the Cooperation Council for the Arab States of the Gulf.svg"),
    "ECOWAS": _alliance_emblem("Flag of ECOWAS.svg"),
    "Arab League ": _alliance_emblem("Flag of the Arab League.svg"),
    "Commonwealth": _alliance_emblem("Flag of the Commonwealth of Nations.svg"),
    "Commonwealth of Nations": _alliance_emblem("Flag of the Commonwealth of Nations.svg"),
    "OECD": _alliance_emblem("OECD logo.svg"),
    "G7": _alliance_emblem("G7 flag.svg"),
    "G20": _alliance_emblem("G20 logo.svg"),
    "QUAD": _alliance_emblem("Flag of India.svg"),   # no official emblem; omitted-safe
    "European Parliament": _alliance_emblem("Flag of Europe.svg"),
    "AES": _alliance_emblem("Flag of the Alliance of Sahel States.svg"),
    "Alliance of Sahel States": _alliance_emblem("Flag of the Alliance of Sahel States.svg"),
}

# v6.6 — diplomatic alignments for the experimental country-alignment map mode
# (strong ally / partner / rival, from the aligned country's perspective).
# Hand-authored for the three power centres; every OTHER country is derived
# from its geopolitical camp below (v6.6.2 — owner: "expand alignments to every
# country … Argentina should be US allies").
ALIGNMENTS = {
    "USA": {"strong": ["GBR","CAN","AUS","NZL","JPN","KOR","ISR","DEU","FRA","ITA","POL","NLD","NOR","DNK","ESP","PRT","BEL","CZE","ROU","LTU","LVA","EST","FIN","SWE","PHL","TWN"],
            "partner": ["IND","VNM","SAU","ARE","QAT","JOR","EGY","MAR","SGP","THA","IDN","MEX","BRA","COL","CHL","ARG","KEN","NGA","UKR"],
            "rival": ["RUS","CHN","IRN","PRK","CUB","VEN","BLR","NIC"]},
    "RUS": {"strong": ["BLR","PRK","IRN","CUB","NIC","VEN","ERI","MLI","BFA","NER"],
            "partner": ["CHN","IND","KAZ","ARM","AZE","UZB","TJK","KGZ","SRB","HUN","MMR","DZA","EGY","ZAF","BRA","SAU","ARE","TUR"],
            "rival": ["USA","GBR","UKR","POL","DEU","FRA","CZE","EST","LVA","LTU","FIN","SWE","NOR","DNK","NLD","CAN","AUS","JPN","KOR"]},
    "CHN": {"strong": ["PRK","PAK","RUS","BLR","KHM","LAO","MMR","IRN"],
            "partner": ["KAZ","UZB","THA","IDN","MYS","BGD","LKA","ETH","EGY","DZA","ZAF","NGA","BRA","ARG","VEN","CUB","SRB","HUN","SAU","ARE"],
            "rival": ["USA","JPN","IND","AUS","GBR","CAN","PHL","KOR","TWN","LTU","CZE","NLD"]},
}

# v6.6.2 — geopolitical camp for each country. "west" leans US/NATO/EU;
# "east" leans Russia; "china" leans Beijing; "nonaligned" hedges. Alignments
# for any country without an explicit entry above are derived from these camps
# by derive_alignments(): fellow-camp members are strong allies, the opposing
# bloc's core are rivals, and neutrals become partners. Not exhaustive-perfect,
# but a coherent, data-driven picture for every country.
COUNTRY_CAMP = {
    # --- West (US/NATO/EU-aligned) ---
    "USA":"west","GBR":"west","CAN":"west","AUS":"west","NZL":"west","JPN":"west",
    "KOR":"west","ISR":"west","DEU":"west","FRA":"west","ITA":"west","ESP":"west",
    "PRT":"west","NLD":"west","BEL":"west","LUX":"west","IRL":"west","NOR":"west",
    "DNK":"west","SWE":"west","FIN":"west","ISL":"west","POL":"west","CZE":"west",
    "SVK":"west","HUN":"west","ROU":"west","BGR":"west","GRC":"west","HRV":"west",
    "SVN":"west","LTU":"west","LVA":"west","EST":"west","AUT":"west","CHE":"west",
    "ALB":"west","MNE":"west","MKD":"west","UKR":"west","GEO":"west","MDA":"west",
    "PHL":"west","TWN":"west","COL":"west","CHL":"west","ARG":"west","PAN":"west",
    "CRI":"west","DOM":"west","GTM":"west","ECU":"west","PRY":"west","URY":"west",
    "JOR":"west","KWT":"west","BHR":"west","MAR":"west","XKX":"west",
    # --- Russia-aligned (east) ---
    "RUS":"east","BLR":"east","PRK":"east","CUB":"east","NIC":"east",
    "VEN":"east","ERI":"east","MLI":"east","BFA":"east","NER":"east","IRN":"east",
    # v6.6.6 — Syria realigned: the al-Sharaa (HTS-led) government that toppled
    # Assad in Dec 2024 is hostile to Assad's backers (Russia, Iran) and warming
    # to Türkiye/Qatar/Gulf and cautiously the West → nonaligned, not east.
    "SYR":"nonaligned",
    # v8.16 — ARM moved east→nonaligned (owner: "armenia is moving away from
    # russia/csto after the artsakh betrayal" — CSTO participation frozen,
    # 2025 EU-accession law; a hard Russia-bloc label is no longer honest)
    "ARM":"nonaligned","SSD":"east","CAF":"east",
    # --- China-aligned ---
    "CHN":"china","PAK":"china","KHM":"china","LAO":"china","MMR":"china",
    # --- Non-aligned / hedging ---
    "IND":"nonaligned","BRA":"nonaligned","ZAF":"nonaligned","IDN":"nonaligned",
    "SAU":"nonaligned","ARE":"nonaligned","QAT":"nonaligned","EGY":"nonaligned",
    "TUR":"nonaligned","VNM":"nonaligned","THA":"nonaligned","MYS":"nonaligned",
    "SGP":"nonaligned","MEX":"nonaligned","NGA":"nonaligned","KEN":"nonaligned",
    "ETH":"nonaligned","DZA":"nonaligned","KAZ":"nonaligned","UZB":"nonaligned",
    "AZE":"nonaligned","SRB":"nonaligned","BGD":"nonaligned","LKA":"nonaligned",
    "IRQ":"nonaligned","OMN":"nonaligned","TUN":"nonaligned","GHA":"nonaligned",
    "AGO":"nonaligned","TZA":"nonaligned","MOZ":"nonaligned","BOL":"nonaligned",
    "PER":"nonaligned","MNG":"nonaligned","LBN":"nonaligned","AFG":"nonaligned",
    "KGZ":"nonaligned","TJK":"nonaligned","TKM":"nonaligned",
    # v7.3 — added entities. Palestine leans to the Arab/nonaligned bloc; the
    # two Russia-backed Caucasus de-facto states sit in the east camp.
    "PSE":"nonaligned","ABK":"east","OST":"east",
    # v7.3 — a few more common-sense camp placements the map was missing.
    "YEM":"nonaligned","LBY":"nonaligned","SOM":"nonaligned","SEN":"nonaligned",
    "CIV":"nonaligned","CMR":"nonaligned","ZMB":"nonaligned","ZWE":"east",
    "CYN":"nonaligned","SOL":"nonaligned",
    # v7.4.1 — the remaining recognized states that had NO camp, so their
    # country profile was missing the alignment-map button entirely (owner:
    # "Libya and Chad and some others don't have the alignment button").
    # Placed by their broad contemporary orientation; every one now hedges/leans
    # somewhere so the map + button work for the WHOLE world.
    "TCD":"nonaligned","MRT":"nonaligned","GNQ":"nonaligned","GAB":"nonaligned",
    "COG":"nonaligned","DJI":"nonaligned","MDG":"nonaligned","LSO":"west",
    "SWZ":"nonaligned","BWA":"west","NAM":"nonaligned","MWI":"west",
    "GNB":"nonaligned","SLE":"west","LBR":"west","TGO":"nonaligned",
    "BEN":"nonaligned","GMB":"nonaligned","CPV":"west","STP":"nonaligned",
    "COM":"nonaligned","SYC":"nonaligned","MUS":"west","BDI":"nonaligned",
    "RWA":"nonaligned","UGA":"nonaligned","GIN":"nonaligned","BTN":"nonaligned",
    "NPL":"nonaligned","MDV":"nonaligned","BRN":"nonaligned","TLS":"nonaligned",
    "PNG":"nonaligned","FJI":"nonaligned","GUY":"west","SUR":"nonaligned",
    "TTO":"west","JAM":"west","HTI":"west","HND":"west","SLV":"west",
    "BLZ":"west","BHS":"west","BRB":"west","SDN":"nonaligned",
}

# camp-level cores used to build derived alignments
_WEST_CORE = ["USA","GBR","DEU","FRA","CAN","JPN","AUS","ITA","POL","NLD"]
_EAST_CORE = ["RUS","BLR","IRN","PRK"]   # v6.6.6 — Syria dropped (al-Sharaa regime)
_CHINA_CORE = ["CHN","PRK","PAK","RUS"]

# v6.6.6 — the 32 NATO members. Every member is a US ally and a mutual ally of
# every other member; a NATO pair that is a genuine, active dispute (Greece–
# Türkiye over the Aegean/Cyprus) stays a rival, per owner ("unless there is
# actually a massive dispute"); any other tension downgrades to a partner
# ("tentative ally") rather than strong.
NATO_MEMBERS = {
    "USA","GBR","CAN","FRA","DEU","ITA","ESP","PRT","NLD","BEL","LUX","NOR",
    "DNK","ISL","POL","CZE","SVK","HUN","ROU","BGR","GRC","HRV","SVN","LTU",
    "LVA","EST","ALB","MNE","MKD","TUR","FIN","SWE",
}


def _camp_members(camp, exclude=None):
    return [c for c, v in COUNTRY_CAMP.items() if v == camp and c != exclude]


# v6.6.4 — explicit common-sense rivalries and friendships, layered on top of
# the camp derivation (owner: "add common sense enemy relationships to all
# countries where appropriate — Israel and Iran should obviously hate each
# other"). Symmetric: listing A→B also makes B→A. RIVALRIES force each other
# into 'rival' (and out of strong/partner); FRIENDSHIPS force 'strong' (and out
# of rival). Applied to the hand-authored powers too.
# v7.3 — comprehensive, corrected rivalry table (owner: "go over and in detail,
# correct all relations in alignments for every country"). Symmetric.
# Saudi–Iran restored diplomatic ties in the 2023 China-brokered détente but
# remain strategic rivals (Yemen, regional influence), so the rivalry stays;
# new de-facto states point at Georgia; Palestine at Israel; GERD drives the
# Egypt–Ethiopia and Nile-basin rivalry.
RIVALRIES = {
    # South & Central Asia
    "IND": ["PAK", "CHN"], "PAK": ["IND", "AFG"], "AFG": ["PAK"],
    # Caucasus
    "ARM": ["AZE", "TUR"], "AZE": ["ARM"], "GEO": ["RUS", "ABK", "OST"],
    "ABK": ["GEO"], "OST": ["GEO"],
    # Middle East
    "ISR": ["IRN", "SYR", "LBN", "PSE", "YEM"], "IRN": ["ISR", "USA", "SAU"],
    "PSE": ["ISR"], "SAU": ["YEM"], "YEM": ["SAU", "ISR"], "SYR": ["ISR"],
    "QAT": [], "ARE": ["YEM"],
    # East Asia
    "PRK": ["KOR", "USA", "JPN"], "KOR": ["PRK"], "JPN": ["PRK", "CHN"],
    "CHN": ["TWN", "IND", "JPN", "PHL", "USA"], "TWN": ["CHN"], "PHL": ["CHN"],
    # Europe / Eurasia
    "GRC": ["TUR"], "TUR": ["GRC", "ARM"], "UKR": ["RUS"],
    "RUS": ["UKR", "USA", "GEO"], "USA": ["RUS", "CHN", "IRN", "PRK"],
    "SRB": ["XKX"], "XKX": ["SRB"], "GBR": ["ARG"], "ARG": ["GBR"],
    # Africa
    "ETH": ["ERI", "EGY"], "ERI": ["ETH"], "EGY": ["ETH"],
    "DZA": ["MAR"], "MAR": ["DZA"], "SDN": ["SSD"], "SSD": ["SDN"],
    # Americas
    "VEN": ["USA", "GUY"], "GUY": ["VEN"], "CUB": ["USA"], "NIC": ["USA"],
}
# v7.3 — comprehensive friendship / strong-ally table. Symmetric.
FRIENDSHIPS = {
    "IND": ["ARM", "RUS", "ISR", "FRA"], "ARM": ["IND", "IRN", "FRA", "USA"],
    "USA": ["ISR", "GBR", "PAK", "AUS", "JPN", "KOR", "PHL"],
    "ISR": ["USA", "IND"], "PAK": ["CHN", "TUR", "SAU", "USA"],
    "AZE": ["TUR", "ISR", "PAK"], "TUR": ["AZE", "PAK", "QAT"],
    "GRC": ["CYP"], "CYP": ["GRC"], "RUS": ["BLR", "IND", "ABK", "OST", "IRN"],
    "SYR": ["TUR", "QAT"], "ABK": ["RUS"], "OST": ["RUS"],
    # Palestine's backers: the Arab world, plus Iran/Turkey/Qatar diplomatically.
    "PSE": ["JOR", "EGY", "QAT", "TUR", "IRN", "DZA", "SAU"],
    # Gulf reconciliation (2021 Al-Ula) — Qatar back in the GCC fold.
    "SAU": ["ARE", "BHR", "QAT", "EGY", "PAK"], "QAT": ["TUR", "SAU"],
    "PRK": ["RUS", "CHN"], "KOR": ["USA", "JPN"],
    "ETH": ["CHN"], "EGY": ["SAU", "ARE"],
}


def _apply_overrides(iso3, res):
    """v6.6.4 — force explicit rivalries/friendships into a derived alignment."""
    strong = list(res.get("strong", []))
    partner = list(res.get("partner", []))
    rival = list(res.get("rival", []))
    # symmetric rivalries (A lists B, or B lists A)
    rivals = set(RIVALRIES.get(iso3, []))
    for a, bs in RIVALRIES.items():
        if iso3 in bs:
            rivals.add(a)
    friends = set(FRIENDSHIPS.get(iso3, []))
    for a, bs in FRIENDSHIPS.items():
        if iso3 in bs:
            friends.add(a)
    friends -= rivals   # a rivalry wins over a stale friendship
    for r in rivals:
        if r == iso3:
            continue
        strong = [c for c in strong if c != r]
        partner = [c for c in partner if c != r]
        if r not in rival:
            rival.append(r)
    for f in friends:
        if f == iso3:
            continue
        rival = [c for c in rival if c != f]
        partner = [c for c in partner if c != f]
        if f not in strong:
            strong.insert(0, f)
    # v6.6.6 — NATO members are mutual allies. A fellow member becomes a strong
    # ally UNLESS it is already a genuine active dispute (kept as a rival, e.g.
    # Greece–Türkiye); such a member is never demoted to a plain partner here.
    if iso3 in NATO_MEMBERS:
        for m in NATO_MEMBERS:
            if m == iso3 or m in rival:
                continue
            partner = [c for c in partner if c != m]
            if m not in strong:
                strong.append(m)
    return {"strong": strong, "partner": [p for p in partner if p not in strong and p not in rival],
            "rival": rival}


def derive_alignments(iso3):
    """v6.6.2/v6.6.4 — build a {strong, partner, rival} alignment view for any
    country from its camp, then apply explicit common-sense rivalries and
    friendships. Explicit ALIGNMENTS entries seed the powers; everyone else is
    derived so the alignment map works for every country."""
    iso3 = (iso3 or "").upper()
    base = None
    if iso3 in ALIGNMENTS:
        base = ALIGNMENTS[iso3]
    else:
        camp = COUNTRY_CAMP.get(iso3)
        if camp == "west":
            base = {"strong": [c for c in _WEST_CORE if c != iso3][:9],
                    "partner": ["UKR","ISR","KOR","TWN","ARG","COL","JOR","SGP"],
                    "rival": _EAST_CORE + ["CHN"]}
        elif camp == "east":
            base = {"strong": ([c for c in _EAST_CORE if c != iso3] + ["RUS"]) if iso3 != "RUS" else _EAST_CORE,
                    "partner": ["CHN","IND","SRB","HUN","VEN","DZA"],
                    "rival": [c for c in _WEST_CORE if c != iso3][:8] + ["UKR"]}
        elif camp == "china":
            base = {"strong": [c for c in _CHINA_CORE if c != iso3][:6],
                    "partner": ["KAZ","THA","IDN","ETH","ZAF","SRB","SAU"],
                    "rival": ["USA","JPN","IND","AUS","TWN","PHL"]}
        elif camp == "nonaligned":
            base = {"strong": [], "partner": ["USA","CHN","RUS","IND","BRA","SAU"], "rival": []}
    # even a country with no camp gets an alignment if it appears in the
    # rivalry/friendship tables (so e.g. every listed pair renders)
    if base is None:
        # v7.4.1 — NEVER return None for a real 3-letter country code: every
        # country must get the alignment-map button (owner). A country with no
        # camp and no explicit rivalry falls back to a neutral nonaligned view
        # (hedges between the major powers) rather than vanishing.
        if len(iso3) == 3 and iso3.isalpha():
            base = {"strong": [], "partner": ["USA", "CHN", "RUS", "EU"], "rival": []}
        else:
            return None
    return _apply_overrides(iso3, base)


# v6.6.2 — rich bloc-profile metadata for the full bloc panels (owner wanted
# NATO/CSTO/EU/Arab League/etc. to open pages like the UN: purpose, HQ,
# policies/strategies, notable measures). Keyed by alliance NAME. Missing blocs
# still render from their DB description + members; this just deepens the majors.
ALLIANCE_PROFILES = {
    "NATO": {"hq": "Brussels, Belgium",
             "purpose": "Collective defense (Article 5): an attack on one member is an attack on all.",
             "policies": ["Article 5 collective defense", "Eastern-flank enhanced Forward Presence",
                          "2% GDP defense-spending target", "Open Door enlargement policy",
                          "Support to Ukraine via the NATO-Ukraine Council"],
             "measures": [("Finland accession", "2023-04-04"), ("Sweden accession", "2024-03-07"),
                          ("Washington Summit pledge to Ukraine", "2024-07-10")]},
    "European Union": {"hq": "Brussels, Belgium",
           "purpose": "Political and economic union: single market, customs union, common policies.",
           "policies": ["Single market & free movement", "Common Agricultural Policy",
                        "European Green Deal (climate neutrality by 2050)", "Common Foreign & Security Policy",
                        "Enlargement negotiations (Ukraine, Moldova, Western Balkans)"],
           "measures": [("14th sanctions package on Russia", "2024-06-24"),
                        ("Ukraine accession talks opened", "2024-06-25"),
                        ("AI Act entered into force", "2024-08-01")]},
    "CSTO": {"hq": "Moscow, Russia",
             "purpose": "Russia-led collective-security treaty organization.",
             "policies": ["Collective defense (Article 4)", "Rapid Reaction Collective Forces",
                          "Joint air-defense system"],
             "measures": [("Kazakhstan peacekeeping deployment", "2022-01-06"),
                          ("Armenia freezes participation", "2024-02-23")]},
    "Arab League": {"hq": "Cairo, Egypt",
                    "purpose": "Regional bloc coordinating political, economic and cultural affairs of Arab states.",
                    "policies": ["Joint Arab position on Palestine", "Arab Peace Initiative",
                                 "Greater Arab Free Trade Area"],
                    "measures": [("Syria readmitted", "2023-05-07"),
                                 ("Joint statement on Gaza ceasefire", "2023-10-21")]},
    "ASEAN": {"hq": "Jakarta, Indonesia",
              "purpose": "Southeast Asian political-economic bloc promoting integration and stability.",
              "policies": ["ASEAN Free Trade Area", "Non-interference principle",
                           "ASEAN Outlook on the Indo-Pacific", "Five-Point Consensus on Myanmar"],
              "measures": [("Timor-Leste in-principle membership", "2022-11-11")]},
    "African Union": {"hq": "Addis Ababa, Ethiopia",
                      "purpose": "Continental union of all 55 African states.",
                      "policies": ["Agenda 2063", "African Continental Free Trade Area (AfCFTA)",
                                   "Silencing the Guns", "Peace & Security Council operations"],
                      "measures": [("AU joins the G20", "2023-09-09")]},
    "BRICS": {"hq": "(rotating chair)",
              "purpose": "Bloc of major emerging economies coordinating on finance and multipolar reform.",
              "policies": ["New Development Bank", "Local-currency trade settlement",
                           "Expansion of membership"],
              "measures": [("Bloc expansion (Egypt, Ethiopia, Iran, UAE join)", "2024-01-01")]},
    "OPEC": {"hq": "Vienna, Austria",
             "purpose": "Coordinates petroleum policy among major oil-exporting nations.",
             "policies": ["Production quotas to stabilize prices", "OPEC+ cooperation with Russia"],
             "measures": [("Voluntary output cuts extended", "2024-06-02")]},
    "Five Eyes": {"hq": "(distributed)",
                  "purpose": "Anglophone signals-intelligence sharing alliance.",
                  "policies": ["Intelligence sharing (SIGINT)", "Joint threat assessments"],
                  "measures": []},
    "QUAD": {"hq": "(distributed)",
             "purpose": "Indo-Pacific strategic dialogue (US, Japan, India, Australia).",
             "policies": ["Free and open Indo-Pacific", "Maritime domain awareness",
                          "Critical & emerging technology cooperation"],
             "measures": []},
    "AUKUS": {"hq": "(distributed)",
              "purpose": "Trilateral security pact (Australia, UK, US) — nuclear submarines & advanced tech.",
              "policies": ["Pillar 1: nuclear-powered submarines for Australia",
                           "Pillar 2: advanced capabilities (AI, hypersonics, quantum)"],
              "measures": []},
}

# v6.6.2 — European Parliament composition (political groups), for the EU bloc
# panel's parliament breakdown. Seats out of 720 (2024-2029 term). Colors for
# the hemicycle graphic.
EU_PARLIAMENT = {
    "total": 720,
    "groups": [
        ("EPP", "European People's Party", 188, "#3399ff"),
        ("S&D", "Socialists & Democrats", 136, "#f0001c"),
        ("PfE", "Patriots for Europe", 84, "#183a63"),
        ("ECR", "European Conservatives & Reformists", 78, "#0a6cbf"),
        ("Renew", "Renew Europe", 77, "#ffd700"),
        ("Greens/EFA", "Greens / EFA", 53, "#57b45f"),
        ("The Left", "The Left", 46, "#af1e2d"),
        ("ESN", "Europe of Sovereign Nations", 25, "#2b2b6b"),
        ("NI", "Non-Inscrits", 33, "#999999"),
    ],
}
