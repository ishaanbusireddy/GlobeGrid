"""V8 §Q3 — the border & sovereignty history layer (1950 → present).

The owner asked that map/administrative history "go back at least until 1950 if
possible, estimate based on historical maps and knowledge and treaties if not
available as data (only if you have to), but the second data gets available like
in the past two decades, switch to real data."

Full province-level historical GEOMETRY for every unit back to 1950 is a large
GIS-vendoring effort (CShapes / historical boundary sets). What this module
delivers NOW — with the temporal machinery already live in the schema
(administrative_units.effective_from/effective_to) and the API (?as_of=) — is a
curated, knowledge-based TIMELINE of the major sovereignty and administrative
changes since 1950: dissolutions, independences, unifications, partitions,
annexations and renamings. It is honest about being curated ("estimated" where
no boundary dataset backs it), and it is structured so each entry can later be
upgraded to a real dated boundary epoch without any code change.

Every entry names the modern iso3(s) it touches so a country/unit page can show
"what happened here since 1950", and `as_of` reads the record valid at a date.

Attribution: compiled from the public historical record (treaties, UN
membership dates, national constitutions). Estimated where marked.
"""

# Each: (year, iso3s_touched, kind, title, detail)
# iso3s_touched uses MODERN iso3 codes so a present-day country page can surface
# its own lineage. kind ∈ {independence, dissolution, unification, partition,
# annexation, secession, renaming, autonomy, transfer}.
HISTORY = [
    (1954, ["IND", "PRT"], "transfer", "France cedes its Indian enclaves",
     "Chandernagore and the other French comptoirs de l'Inde are transferred to India (finalised 1954-62)."),
    (1957, ["GHA"], "independence", "Ghana independence",
     "The Gold Coast becomes Ghana — the first sub-Saharan African colony to gain independence from Britain."),
    (1960, ["COD", "NGA", "SEN", "MLI", "MDG", "SOM", "BEN", "BFA", "CIV", "TCD", "CAF", "COG", "GAB", "CMR", "TGO", "NER"],
     "independence", "The Year of Africa",
     "Seventeen African colonies gain independence in 1960, redrawing the continent's political map at the country level."),
    (1961, ["IND", "PRT"], "annexation", "India annexes Goa",
     "Indian forces end 451 years of Portuguese rule over Goa, Daman and Diu, incorporating them as Indian territory."),
    (1963, ["MYS", "SGP"], "unification", "Formation of Malaysia",
     "Malaya, Singapore, Sabah and Sarawak federate as Malaysia (Singapore separates two years later)."),
    (1965, ["SGP"], "secession", "Singapore leaves Malaysia",
     "Singapore is expelled from the Malaysian federation and becomes a sovereign city-state."),
    (1971, ["BGD", "PAK"], "secession", "Bangladesh independence",
     "East Pakistan secedes after the Liberation War, becoming Bangladesh; Pakistan's two wings are permanently divided."),
    (1975, ["AGO", "MOZ", "TLS", "PNG"], "independence", "End of the Portuguese empire",
     "Angola, Mozambique, Cape Verde, Guinea-Bissau and São Tomé gain independence; Portuguese Timor is soon annexed by Indonesia."),
    (1975, ["VNM"], "unification", "Reunification of Vietnam",
     "The fall of Saigon ends the war; North and South Vietnam formally reunify as one state in 1976."),
    (1976, ["TLS", "IDN"], "annexation", "Indonesia annexes East Timor",
     "Indonesia invades and annexes Portuguese Timor as its 27th province (reversed in 1999-2002). Estimated boundary."),
    (1990, ["DEU"], "unification", "German reunification",
     "The German Democratic Republic accedes to the Federal Republic; East and West Germany reunite, restoring the eastern Länder."),
    (1990, ["YEM"], "unification", "Unification of Yemen",
     "North Yemen (YAR) and South Yemen (PDRY) merge into the single Republic of Yemen."),
    (1990, ["NAM"], "independence", "Namibia independence",
     "Namibia gains independence from South African administration after decades of UN dispute over South West Africa."),
    (1991, ["RUS", "UKR", "BLR", "KAZ", "UZB", "TKM", "KGZ", "TJK", "ARM", "AZE", "GEO", "MDA", "LTU", "LVA", "EST"],
     "dissolution", "Dissolution of the Soviet Union",
     "The USSR dissolves into 15 independent republics — the single largest redrawing of the world's internal borders since 1945."),
    (1991, ["HRV", "SVN", "MKD", "BIH", "SRB", "MNE"], "dissolution", "Breakup of Yugoslavia begins",
     "Slovenia and Croatia declare independence, beginning the decade-long fragmentation of the SFR Yugoslavia."),
    (1993, ["CZE", "SVK"], "partition", "Velvet Divorce",
     "Czechoslovakia peacefully splits into the Czech Republic and Slovakia on 1 January 1993."),
    (1993, ["ERI", "ETH"], "secession", "Eritrea independence",
     "Eritrea secedes from Ethiopia after a referendum, leaving Ethiopia landlocked."),
    (1994, ["PLW"], "independence", "Palau independence",
     "Palau becomes independent from the US-administered Trust Territory of the Pacific Islands."),
    (1997, ["HKG", "CHN"], "transfer", "Hong Kong handover",
     "The United Kingdom transfers sovereignty over Hong Kong to China, which becomes a Special Administrative Region."),
    (1999, ["MAC", "CHN"], "transfer", "Macau handover",
     "Portugal transfers Macau to China as a Special Administrative Region, ending the last European colony in Asia."),
    (2002, ["TLS"], "independence", "Timor-Leste independence",
     "East Timor becomes fully independent after a UN transitional administration — the first new sovereign state of the 21st century."),
    (2006, ["MNE", "SRB"], "partition", "Montenegro independence",
     "Montenegro votes to leave the State Union of Serbia and Montenegro; both become separate states."),
    (2008, ["XKX", "SRB"], "secession", "Kosovo declares independence",
     "Kosovo unilaterally declares independence from Serbia — recognised by ~100 states, disputed by Serbia and others."),
    (2011, ["SSD", "SDN"], "secession", "South Sudan independence",
     "After a referendum, South Sudan secedes from Sudan, becoming the world's newest UN member state."),
    (2014, ["UKR", "RUS"], "annexation", "Russia annexes Crimea",
     "Russia annexes Crimea and Sevastopol following an unrecognised referendum; the change is rejected by the UN General Assembly. Estimated control."),
    (2022, ["UKR", "RUS"], "annexation", "Russia claims four Ukrainian oblasts",
     "Russia announces annexation of Donetsk, Luhansk, Zaporizhzhia and Kherson oblasts amid the ongoing war; unrecognised internationally. Estimated control."),
    (2023, ["AZE", "ARM"], "transfer", "Azerbaijan retakes Nagorno-Karabakh",
     "Azerbaijan's offensive dissolves the self-declared Republic of Artsakh; the enclave's ethnic-Armenian population departs."),
]


def timeline():
    """The full curated timeline, newest first."""
    return [
        {"year": y, "countries": iso, "kind": k, "title": t, "detail": d}
        for (y, iso, k, t, d) in sorted(HISTORY, key=lambda e: -e[0])
    ]


def history_for(iso3):
    """Timeline entries that touch a given modern country (newest first)."""
    iso3 = (iso3 or "").upper()
    return [e for e in timeline() if iso3 in e["countries"]]


def history_as_of(as_of_year):
    """Entries that had already happened by a given year (for the as_of capsule)."""
    try:
        yr = int(str(as_of_year)[:4])
    except (TypeError, ValueError):
        return timeline()
    return [e for e in timeline() if e["year"] <= yr]
