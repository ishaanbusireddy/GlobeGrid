"""v6 §28 — UN M49 sub-region assignment.

countries.region values were hand-assigned in v3/v4 and drifted (South Asia
was missing Nepal/Bhutan/Sri Lanka/Maldives; 'Eastern Europe' had only 8
countries). This module is the authoritative iso3 → M49 sub-region table,
transcribed from the UN Statistics Division M49 standard (unstats.un.org/
unsd/methodology/m49) for every seeded entity. The startup completeness
check (seed.check_completeness) verifies each sub-region's expected count
against what's actually in the DB — the same pattern v4 §5.1 uses for the
total country count — so a future hand-edit that drops a country out of its
sub-region fails loudly instead of silently shrinking a region.

De-facto states are assigned to the sub-region of their territory (TWN →
Eastern Asia, XKX → Southern Europe, SOL → Eastern Africa, CYN → Western
Asia); that's a pragmatic placement for region queries, not a recognition
statement (countries.status carries that).
"""

M49_SUBREGION = {
    # --- Northern Africa (6) ---
    **dict.fromkeys(["DZA", "EGY", "LBY", "MAR", "SDN", "TUN"], "Northern Africa"),
    # --- Eastern Africa (19 incl. SOL) ---
    **dict.fromkeys(["BDI", "COM", "DJI", "ERI", "ETH", "KEN", "MDG", "MWI",
                     "MUS", "MOZ", "RWA", "SYC", "SOM", "SSD", "UGA", "TZA",
                     "ZMB", "ZWE", "SOL"], "Eastern Africa"),
    # --- Middle Africa (9) ---
    **dict.fromkeys(["AGO", "CMR", "CAF", "TCD", "COG", "COD", "GNQ", "GAB",
                     "STP"], "Middle Africa"),
    # --- Southern Africa (5) ---
    **dict.fromkeys(["BWA", "SWZ", "LSO", "NAM", "ZAF"], "Southern Africa"),
    # --- Western Africa (16) ---
    **dict.fromkeys(["BEN", "BFA", "CPV", "CIV", "GMB", "GHA", "GIN", "GNB",
                     "LBR", "MLI", "MRT", "NER", "NGA", "SEN", "SLE", "TGO"],
                    "Western Africa"),
    # --- Caribbean (13) ---
    **dict.fromkeys(["ATG", "BHS", "BRB", "CUB", "DMA", "DOM", "GRD", "HTI",
                     "JAM", "KNA", "LCA", "VCT", "TTO"], "Caribbean"),
    # --- Central America (8) ---
    **dict.fromkeys(["BLZ", "CRI", "SLV", "GTM", "HND", "MEX", "NIC", "PAN"],
                    "Central America"),
    # --- South America (12) ---
    **dict.fromkeys(["ARG", "BOL", "BRA", "CHL", "COL", "ECU", "GUY", "PRY",
                     "PER", "SUR", "URY", "VEN"], "South America"),
    # --- Northern America (2) ---
    **dict.fromkeys(["CAN", "USA"], "Northern America"),
    # --- Central Asia (5) ---
    **dict.fromkeys(["KAZ", "KGZ", "TJK", "TKM", "UZB"], "Central Asia"),
    # --- Eastern Asia (6 incl. TWN) ---
    **dict.fromkeys(["CHN", "JPN", "KOR", "PRK", "MNG", "TWN"], "Eastern Asia"),
    # --- South-Eastern Asia (11 incl. TLS) ---
    **dict.fromkeys(["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP",
                     "THA", "TLS", "VNM"], "South-Eastern Asia"),
    # --- Southern Asia (9 — the fixed grouping: incl. NPL/BTN/LKA/MDV) ---
    **dict.fromkeys(["AFG", "BGD", "BTN", "IND", "IRN", "LKA", "MDV", "NPL",
                     "PAK"], "Southern Asia"),
    # --- Western Asia (19 incl. PSE, CYN) ---
    **dict.fromkeys(["ARM", "AZE", "BHR", "CYP", "GEO", "IRQ", "ISR", "JOR",
                     "KWT", "LBN", "OMN", "PSE", "QAT", "SAU", "SYR", "TUR",
                     "ARE", "YEM", "CYN"], "Western Asia"),
    # --- Eastern Europe (10 — the fixed grouping) ---
    **dict.fromkeys(["BLR", "BGR", "CZE", "HUN", "MDA", "POL", "ROU", "RUS",
                     "SVK", "UKR"], "Eastern Europe"),
    # --- Northern Europe (10) ---
    **dict.fromkeys(["DNK", "EST", "FIN", "ISL", "IRL", "LVA", "LTU", "NOR",
                     "SWE", "GBR"], "Northern Europe"),
    # --- Southern Europe (16 incl. VAT, XKX) ---
    **dict.fromkeys(["ALB", "AND", "BIH", "HRV", "GRC", "ITA", "MLT", "MNE",
                     "MKD", "PRT", "SMR", "SRB", "SVN", "ESP", "VAT", "XKX"],
                    "Southern Europe"),
    # --- Western Europe (9) ---
    **dict.fromkeys(["AUT", "BEL", "FRA", "DEU", "LIE", "LUX", "MCO", "NLD",
                     "CHE"], "Western Europe"),
    # --- Australia and New Zealand (2) ---
    **dict.fromkeys(["AUS", "NZL"], "Australia and New Zealand"),
    # --- Melanesia (4) ---
    **dict.fromkeys(["FJI", "PNG", "SLB", "VUT"], "Melanesia"),
    # --- Micronesia (5) ---
    **dict.fromkeys(["KIR", "MHL", "FSM", "NRU", "PLW"], "Micronesia"),
    # --- Polynesia (3) ---
    **dict.fromkeys(["WSM", "TON", "TUV"], "Polynesia"),
    # --- v6 §14 major territories (each under its M49 sub-region) ---
    "GRL": "Northern America", "PRI": "Caribbean", "NCL": "Melanesia",
    "PYF": "Polynesia", "GUM": "Micronesia", "BMU": "Northern America",
    "FRO": "Northern Europe", "HKG": "Eastern Asia", "MAC": "Eastern Asia",
    "ASM": "Polynesia", "VIR": "Caribbean", "CUW": "Caribbean",
    "ABW": "Caribbean", "CYM": "Caribbean", "FLK": "South America",
}


def expected_counts(statuses_by_iso3: dict[str, str] | None = None) -> dict[str, int]:
    """Expected country count per sub-region, derived from the mapping itself
    (so the check can never drift from the table it validates). Territories
    are optionally excluded by passing the DB's status map."""
    counts: dict[str, int] = {}
    for iso3, sub in M49_SUBREGION.items():
        if statuses_by_iso3 is not None and \
                statuses_by_iso3.get(iso3) in (None, "territory"):
            continue
        counts[sub] = counts.get(sub, 0) + 1
    return counts


# Colloquial / macro region names → the M49 sub-regions they cover, for
# region-level queries ("what's happening in the Middle East?", v5 §20 /
# v6 §29). Names are matched case-insensitively by the analyst.
REGION_GROUPS = {
    "Europe": ["Eastern Europe", "Northern Europe", "Southern Europe",
               "Western Europe"],
    "Africa": ["Northern Africa", "Eastern Africa", "Middle Africa",
               "Southern Africa", "Western Africa"],
    "Asia": ["Central Asia", "Eastern Asia", "South-Eastern Asia",
             "Southern Asia", "Western Asia"],
    "Americas": ["Caribbean", "Central America", "South America",
                 "Northern America"],
    "Latin America": ["Caribbean", "Central America", "South America"],
    "Oceania": ["Australia and New Zealand", "Melanesia", "Micronesia",
                "Polynesia"],
    # colloquial Middle East ≈ Western Asia + Egypt + Iran; Iran sits in
    # M49 Southern Asia and Egypt in Northern Africa, so the group carries
    # explicit extras below
    "Middle East": ["Western Asia"],
    "Balkans": ["Southern Europe"],
    "Sub-Saharan Africa": ["Eastern Africa", "Middle Africa",
                           "Southern Africa", "Western Africa"],
}

# individual countries pulled INTO a colloquial group beyond its sub-regions
REGION_GROUP_EXTRAS = {
    "Middle East": ["EGY", "IRN"],
}
