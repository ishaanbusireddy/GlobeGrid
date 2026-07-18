"""v7.4.1 — autonomous regions / self-governing zones as a first-class entity
type (owner: "add autonomous zones as a new type of entity, e.g. Iraqi
Kurdistan"). These are NOT disputed territories and NOT sovereign states: they
are recognized sub-national entities with a real degree of self-rule inside a
sovereign parent. Each carries its parent state, capital, the basis of its
autonomy, and a context paragraph so clicking it opens a real breakdown, plus
an approximate centroid for a map marker.
"""

# v8.18 — zones that are historical / being dissolved (no longer a live
# self-governing entity). They keep their page (flagged), but are dropped from
# the live autonomous-zone MAP layer so they don't draw an active border.
# Rojava/AANES is integrating into the post-Assad Syrian state under the March
# 2025 SDF–Damascus agreement, so it is no longer treated as a live autonomous
# administration on the map (owner: "Rojava doesn't even exist anymore").
HISTORICAL_ZONES = {"rojava"}

# id, name, parent_state, capital, autonomy_basis, lat, lon, context
AUTONOMOUS_ZONES = [
    ("iraqi_kurdistan", "Kurdistan Region", "Iraq", "Erbil",
     "Constitutionally recognized federal region with its own parliament, "
     "presidency, security forces (Peshmerga) and budget.",
     36.19, 44.01,
     "The Kurdistan Region of Iraq (KRI) is the country's only constitutionally "
     "recognized federal region, self-governing since a 1991 no-fly zone and "
     "formalized in the 2005 constitution. It runs its own parliament and "
     "presidency in Erbil, fields the Peshmerga, and manages oil exports that "
     "are a recurring flashpoint with Baghdad. A 2017 independence referendum "
     "passed overwhelmingly but was rejected by Iraq and neighbors; the region "
     "remains inside Iraq. The KDP and PUK are its dominant rival parties."),
    ("rojava", "North and East Syria (AANES / Rojava)", "Syria", "Qamishli / Raqqa",
     "De-facto autonomous administration built during the Syrian civil war; "
     "Kurdish-led, multi-ethnic, not internationally recognized.",
     36.6, 40.7,
     "The Autonomous Administration of North and East Syria (AANES), often called "
     "Rojava, is a Kurdish-led, multi-ethnic self-government that emerged from the "
     "2012 collapse of Syrian state control. Its Syrian Democratic Forces (SDF) "
     "were the West's main partner against ISIS. It is autonomous in practice but "
     "recognized neither by Damascus nor internationally, and is under pressure "
     "from Türkiye, which regards its YPG core as tied to the PKK."),
    ("bougainville", "Autonomous Region of Bougainville", "Papua New Guinea", "Buka",
     "Autonomous region with a 2019 non-binding independence referendum (98% yes) "
     "on a path toward possible statehood.",
     -6.2, 155.4,
     "Bougainville is an autonomous region of Papua New Guinea whose 1988-98 civil "
     "war over the Panguna copper mine killed thousands. A 2001 peace deal granted "
     "autonomy and a referendum, held in 2019, in which 98% backed independence. "
     "The result is non-binding and subject to PNG parliamentary ratification; the "
     "two governments have discussed a target of independence, making Bougainville "
     "a live candidate to become a new state."),
    ("zanzibar", "Zanzibar", "Tanzania", "Zanzibar City",
     "Semi-autonomous archipelago with its own president, House of "
     "Representatives and legal system within the Tanzanian union.",
     -6.16, 39.20,
     "Zanzibar united with Tanganyika in 1964 to form Tanzania but retains wide "
     "autonomy: its own president, House of Representatives, courts and revenue. "
     "Its politics (CCM vs the opposition ACT-Wazalendo/CUF) are fiercely "
     "contested and elections have repeatedly been marred by disputes. A "
     "long-running movement seeks greater autonomy or a looser union."),
    ("gagauzia", "Gagauzia", "Moldova", "Comrat",
     "Autonomous territorial unit with guaranteed self-rule and the right to "
     "self-determination if Moldova unites with Romania.",
     46.3, 28.66,
     "Gagauzia is a Turkic-Orthodox autonomous region of southern Moldova, granted "
     "special status in 1994 to defuse a secession bid. It elects its own governor "
     "(Bashkan) and People's Assembly. Politically it leans pro-Russian, a "
     "recurring friction point with Moldova's pro-EU government, and holds a legal "
     "right to seek independence should Moldova ever merge with Romania."),
    ("aland", "Åland Islands", "Finland", "Mariehamn",
     "Demilitarized, Swedish-speaking autonomous region with its own parliament "
     "and guaranteed cultural protections under an international treaty.",
     60.18, 20.30,
     "The Åland Islands are an autonomous, demilitarized and unilingually "
     "Swedish-speaking region of Finland, a status set by a 1921 League of Nations "
     "decision and guaranteed by treaty. Åland runs its own parliament (Lagting) "
     "with control over most domestic affairs, holds a seat in Finland's "
     "arrangements with the EU, and is a textbook case of autonomy defusing an "
     "ethnic-territorial dispute."),
    ("nakhchivan", "Nakhchivan", "Azerbaijan", "Nakhchivan City",
     "Autonomous republic exclave of Azerbaijan, separated from the mainland by "
     "Armenian territory.",
     39.2, 45.4,
     "Nakhchivan is an autonomous republic of Azerbaijan, geographically cut off "
     "from the rest of the country by Armenia's Syunik province and bordering "
     "Türkiye and Iran. Its own Supreme Assembly governs local affairs. Access "
     "routes across Syunik (the proposed 'Zangezur corridor') are a central issue "
     "in post-2020 Armenia-Azerbaijan negotiations."),
    ("hong_kong", "Hong Kong SAR", "China", "Hong Kong",
     "Special Administrative Region under 'one country, two systems' with its own "
     "legal and economic system (autonomy sharply curtailed since 2020).",
     22.32, 114.17,
     "Hong Kong returned to China in 1997 as a Special Administrative Region under "
     "'one country, two systems', keeping its common-law courts, currency and "
     "civil liberties for a promised 50 years. The 2020 National Security Law and "
     "electoral overhaul sharply curtailed that autonomy after the 2019 protests, "
     "though Hong Kong retains a distinct legal and economic system from the "
     "mainland."),
    ("catalonia", "Catalonia", "Spain", "Barcelona",
     "Autonomous community with its own parliament, government and language; "
     "site of a contested 2017 independence bid.",
     41.6, 1.7,
     "Catalonia is one of Spain's autonomous communities, with its own parliament "
     "(Generalitat), police and co-official Catalan language. A 2017 unilateral "
     "independence referendum, ruled illegal by Spain, triggered a constitutional "
     "crisis, direct rule and prosecutions; a 2024 amnesty law sought to close "
     "that chapter. Pro-independence and unionist blocs remain closely balanced."),
    ("greenland", "Greenland (Kalaallit Nunaat)", "Denmark", "Nuuk",
     "Self-governing autonomous territory with control over most domestic affairs "
     "and a legal path to full independence.",
     64.18, -51.72,
     "Greenland is a self-governing autonomous territory of the Kingdom of Denmark. "
     "Under the 2009 Self-Government Act it controls most domestic affairs, its own "
     "premier and Inatsisartut parliament, and holds a recognized legal path to "
     "full independence by referendum. Denmark retains foreign and defense policy. "
     "Its rare-earth and strategic-Arctic value has made it a subject of great-"
     "power interest."),
    # v8.16 — the UK's devolved nations (owner: "add the autonomous zones of
    # the UK — Wales, Scotland, and Northern Ireland")
    ("scotland", "Scotland", "United Kingdom", "Edinburgh",
     "Devolved nation with its own parliament, government and legal system; "
     "independence remains a live political question.",
     56.5, -4.2,
     "Scotland has been part of the United Kingdom since the 1707 Acts of Union "
     "but kept its own legal system, church and education. Since 1999 it has a "
     "devolved Scottish Parliament at Holyrood with power over health, education, "
     "justice and (since 2016) significant taxation. The SNP has governed since "
     "2007; a 2014 independence referendum failed 45-55, and the constitutional "
     "question \u2014 sharpened by Brexit, which Scotland voted against \u2014 remains the "
     "central axis of its politics."),
    ("wales", "Wales (Cymru)", "United Kingdom", "Cardiff",
     "Devolved nation with its own Senedd and government; the Welsh language "
     "is co-official and resurgent.",
     52.3, -3.7,
     "Wales was annexed to England in the 16th century but retained a distinct "
     "language and identity. Devolution since 1999 built the Senedd (Welsh "
     "Parliament) and a Welsh Government responsible for health, education and "
     "the economy. Welsh Labour has led every administration; Plaid Cymru "
     "presses for independence, a minority but growing position. The Welsh "
     "language, spoken by ~18%, is co-official and a policy priority."),
    ("northern_ireland", "Northern Ireland", "United Kingdom", "Belfast",
     "Devolved power-sharing government under the Good Friday Agreement; "
     "constitutional status contested between unionism and Irish nationalism.",
     54.6, -6.7,
     "Northern Ireland was created in 1921 when Ireland was partitioned. Three "
     "decades of the Troubles ended with the 1998 Good Friday Agreement, which "
     "built mandatory power-sharing between unionists and nationalists in the "
     "Stormont Assembly and gives the population the right to vote on unifying "
     "with Ireland. Sinn F\u00e9in became the largest party in 2022; Brexit's sea "
     "border (the Windsor Framework) remains a unionist grievance, and a border "
     "poll is the long-horizon question."),
]


def _flag(name: str) -> str:
    # Wikimedia Special:FilePath resolves "Flag of X.svg" to the current image,
    # same pattern the country flag layer uses (degrades to a placeholder offline).
    from urllib.parse import quote
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(name)


# v7.6 — country-grade profile data so an autonomous zone renders EXACTLY like a
# territory panel (owner: "complete with everything a country would have — such
# as parliaments, agendas, leaders, flags, everything"). Each carries a real
# flag, its own head-of-government, a legislature seat breakdown, a strategic
# agenda, headline stats, and an approximate boundary ring ([lon,lat]) drawn as
# an always-on DOTTED border on the map (like territories, but dashed).
ZONE_EXTRA = {
    # v8.16 — UK devolved nations
    "scotland": {
        "official_name": "Scotland", "established": "1999 (devolution)",
        "flag_url": _flag("Flag of Scotland.svg"),
        "leader": {"name": "John Swinney", "title": "First Minister", "party": "SNP"},
        "legislature": {"chamber": "Scottish Parliament (Holyrood)", "total": 129,
                        "parties": [["SNP", 64, "#fdf38e"], ["Conservative", 31, "#0087dc"],
                                    ["Labour", 22, "#e4003b"], ["Green", 8, "#00b140"],
                                    ["Lib Dem", 4, "#faa61a"]]},
        "agenda": "Govern within devolution while keeping independence on the agenda, "
                  "contest fiscal transfers with Westminster, and position Scotland for "
                  "EU re-entry in any future constitutional change.",
        "stats": {"population": "~5.4 million", "area_km2": "~77,933",
                  "languages": "English, Scots, Scottish Gaelic",
                  "currency": "Pound sterling (GBP)"},
    },
    "wales": {
        "official_name": "Wales (Cymru)", "established": "1999 (devolution)",
        "flag_url": _flag("Flag of Wales.svg"),
        "leader": {"name": "Eluned Morgan", "title": "First Minister", "party": "Welsh Labour"},
        "legislature": {"chamber": "Senedd (Welsh Parliament)", "total": 60,
                        "parties": [["Labour", 30, "#e4003b"], ["Conservative", 16, "#0087dc"],
                                    ["Plaid Cymru", 13, "#008142"], ["Lib Dem", 1, "#faa61a"]]},
        "agenda": "Expand devolved powers (justice, broadcasting), revive the Welsh "
                  "language toward the 'Cymraeg 2050' million-speaker goal, and manage "
                  "post-industrial economic renewal.",
        "stats": {"population": "~3.1 million", "area_km2": "~20,779",
                  "languages": "English, Welsh (co-official)",
                  "currency": "Pound sterling (GBP)"},
    },
    "northern_ireland": {
        "official_name": "Northern Ireland", "established": "1998 (Good Friday Agreement)",
        # deliberately NO flag: Northern Ireland has no official flag of its own
        # (the Ulster Banner lapsed in 1972 and is a contested symbol) — the
        # owner's official-flags-only rule applies here too.
        "leader": {"name": "Michelle O'Neill", "title": "First Minister", "party": "Sinn F\u00e9in"},
        "leader2": {"name": "Emma Little-Pengelly", "title": "deputy First Minister", "party": "DUP"},
        "legislature": {"chamber": "Northern Ireland Assembly (Stormont)", "total": 90,
                        "parties": [["Sinn F\u00e9in", 27, "#326760"], ["DUP", 25, "#d46a4c"],
                                    ["Alliance", 17, "#f6cb2f"], ["UUP", 9, "#48a5ee"],
                                    ["SDLP", 8, "#2aa82c"], ["TUV", 1, "#0c3a6a"],
                                    ["Others", 3, "#888888"]]},
        "agenda": "Keep power-sharing functioning, manage the Windsor Framework's "
                  "sea-border economics, and navigate the long-horizon question of a "
                  "border poll on Irish unification.",
        "stats": {"population": "~1.9 million", "area_km2": "~14,130",
                  "languages": "English, Irish, Ulster Scots",
                  "currency": "Pound sterling (GBP)"},
    },

    "iraqi_kurdistan": {
        "official_name": "Kurdistan Region of Iraq", "established": "1970 / 2005 (federal region)",
        "flag_url": _flag("Flag of Kurdistan.svg"),
        "leader": {"name": "Masrour Barzani", "title": "Prime Minister", "party": "KDP"},
        "leader2": {"name": "Nechirvan Barzani", "title": "President", "party": "KDP"},
        "legislature": {"chamber": "Kurdistan Parliament", "total": 111,
                        "parties": [["KDP", 39, "#f2c200"], ["PUK", 23, "#009a44"],
                                    ["New Generation", 15, "#e4002b"],
                                    ["KIU / others", 34, "#888888"]]},
        "agenda": "Consolidate federal autonomy and oil-export revenue-sharing with Baghdad, "
                  "manage KDP–PUK power-sharing, and balance Türkiye, Iran and the US while "
                  "keeping the independence question frozen.",
        "stats": {"population": "~6.5 million", "area_km2": "~46,861", "languages": "Kurdish, Arabic",
                  "currency": "Iraqi dinar (IQD)"},
        "outline": [[42.3, 37.3], [45.9, 37.2], [46.4, 35.2], [44.7, 34.5], [42.4, 35.6], [42.3, 37.3]],
    },
    "rojava": {
        "official_name": "Autonomous Administration of North and East Syria (AANES)",
        "established": "2012 (de facto)", "flag_url": _flag("Flag of Rojava.svg"),
        "leader": {"name": "Executive Council (co-chairs)", "title": "Co-Presidency", "party": "TEV-DEM / SDC"},
        "legislature": {"chamber": "Syrian Democratic Council (general council)", "total": 0, "parties": []},
        "agenda": "Preserve Kurdish-led, multi-ethnic self-rule and the SDF against Turkish "
                  "pressure, negotiate the region's status with post-Assad Damascus, and secure "
                  "the ISIS detention camps.",
        "stats": {"population": "~2.5 million", "area_km2": "~50,000", "languages": "Kurdish, Arabic, Syriac",
                  "currency": "Syrian pound (SYP)"},
        "outline": [[37.0, 37.1], [42.4, 37.3], [42.2, 35.9], [38.4, 35.8], [37.0, 36.2], [37.0, 37.1]],
    },
    "bougainville": {
        "official_name": "Autonomous Region of Bougainville", "established": "2001 (peace agreement)",
        "flag_url": _flag("Flag of Bougainville.svg"),
        "leader": {"name": "Ishmael Toroama", "title": "President", "party": "Independent"},
        "legislature": {"chamber": "House of Representatives", "total": 40, "parties": []},
        "agenda": "Ratify the 2019 referendum's 98% independence vote through the PNG parliament "
                  "and build the institutions and finances of a prospective new state.",
        "stats": {"population": "~300,000", "area_km2": "~9,438", "languages": "Tok Pisin, English, ~25 local",
                  "currency": "PNG kina (PGK)"},
        "outline": [[154.5, -5.0], [155.9, -5.2], [156.1, -6.9], [155.1, -6.9], [154.6, -5.9], [154.5, -5.0]],
    },
    "zanzibar": {
        "official_name": "Zanzibar (within the United Republic of Tanzania)", "established": "1964 (union)",
        "flag_url": _flag("Flag of Zanzibar.svg"),
        "leader": {"name": "Hussein Mwinyi", "title": "President of Zanzibar", "party": "CCM"},
        "legislature": {"chamber": "House of Representatives", "total": 85, "parties": []},
        "agenda": "Widen fiscal and political autonomy within the Tanzanian union, manage the "
                  "CCM–ACT-Wazalendo rivalry after contested elections, and grow tourism/blue economy.",
        "stats": {"population": "~1.9 million", "area_km2": "~2,462", "languages": "Swahili, Arabic, English",
                  "currency": "Tanzanian shilling (TZS)"},
        "outline": [[39.15, -5.65], [39.55, -5.8], [39.6, -6.5], [39.18, -6.5], [39.1, -6.0], [39.15, -5.65]],
    },
    "gagauzia": {
        "official_name": "Autonomous Territorial Unit of Gagauzia", "established": "1994",
        "flag_url": _flag("Flag of Gagauzia.svg"),
        "leader": {"name": "Evghenia Guțul", "title": "Bashkan (Governor)", "party": "Șor-aligned"},
        "legislature": {"chamber": "People's Assembly", "total": 35, "parties": []},
        "agenda": "Defend guaranteed autonomy and its pro-Russian cultural orientation against "
                  "Chișinău's pro-EU government, and hold its treaty right to self-determination "
                  "should Moldova unite with Romania.",
        "stats": {"population": "~135,000", "area_km2": "~1,848", "languages": "Gagauz, Russian, Romanian",
                  "currency": "Moldovan leu (MDL)"},
        "outline": [[28.3, 46.5], [29.05, 46.5], [29.1, 45.85], [28.4, 45.85], [28.3, 46.5]],
    },
    "aland": {
        "official_name": "Åland Islands", "established": "1921 (League of Nations)",
        "flag_url": _flag("Flag of Åland.svg"),
        "leader": {"name": "Katrin Sjögren", "title": "Premier (Lantråd)", "party": "Liberals for Åland"},
        "legislature": {"chamber": "Lagting", "total": 30, "parties": []},
        "agenda": "Preserve demilitarized, Swedish-language autonomy and its special EU "
                  "arrangements, and keep influence over Finland's EU positions affecting Åland.",
        "stats": {"population": "~30,000", "area_km2": "~1,580", "languages": "Swedish",
                  "currency": "Euro (EUR)"},
        "outline": [[19.5, 60.45], [20.85, 60.45], [20.9, 59.9], [19.55, 59.9], [19.5, 60.45]],
    },
    "nakhchivan": {
        "official_name": "Nakhchivan Autonomous Republic", "established": "1924",
        "flag_url": _flag("Flag of Azerbaijan.svg"),
        "leader": {"name": "Chairman of the Supreme Assembly", "title": "Head of the Autonomous Republic", "party": "New Azerbaijan (YAP)"},
        "legislature": {"chamber": "Supreme Assembly (Ali Majlis)", "total": 45, "parties": []},
        "agenda": "Secure land access across Armenia's Syunik (the 'Zangezur corridor') as part of "
                  "the Armenia–Azerbaijan settlement, deepen integration with Türkiye.",
        "stats": {"population": "~460,000", "area_km2": "~5,500", "languages": "Azerbaijani",
                  "currency": "Azerbaijani manat (AZN)"},
        "outline": [[44.8, 39.8], [46.15, 39.6], [46.0, 38.85], [45.0, 39.0], [44.8, 39.8]],
    },
    "hong_kong": {
        "official_name": "Hong Kong Special Administrative Region", "established": "1997",
        "flag_url": _flag("Flag of Hong Kong.svg"),
        "leader": {"name": "John Lee", "title": "Chief Executive", "party": "Nonpartisan (pro-Beijing)"},
        "legislature": {"chamber": "Legislative Council (LegCo)", "total": 90,
                        "parties": [["Pro-establishment", 89, "#de2910"], ["Nonpartisan/other", 1, "#888888"]]},
        "agenda": "Operate 'one country, two systems' under the 2020 National Security Law and "
                  "electoral overhaul, restore Hong Kong's role as a global financial hub while "
                  "aligned with Beijing.",
        "stats": {"population": "~7.5 million", "area_km2": "~1,114", "languages": "Cantonese, English, Mandarin",
                  "currency": "Hong Kong dollar (HKD)"},
        "outline": [[113.83, 22.56], [114.45, 22.56], [114.45, 22.15], [113.83, 22.19], [113.83, 22.56]],
    },
    "catalonia": {
        "official_name": "Catalonia (Catalunya)", "established": "1979 (Statute of Autonomy)",
        "flag_url": _flag("Flag of Catalonia.svg"),
        "leader": {"name": "Salvador Illa", "title": "President of the Generalitat", "party": "PSC (Socialists)"},
        "legislature": {"chamber": "Parliament of Catalonia", "total": 135,
                        "parties": [["PSC", 42, "#e30613"], ["Junts", 35, "#00c3b2"],
                                    ["ERC", 20, "#ffb232"], ["PP", 15, "#0056a8"],
                                    ["Vox", 11, "#63be21"], ["others", 12, "#888888"]]},
        "agenda": "Stabilize post-2017 politics under a Socialist-led government and the 2024 "
                  "amnesty, balance a still-strong pro-independence bloc, and negotiate financing "
                  "and language rights with Madrid.",
        "stats": {"population": "~8.0 million", "area_km2": "~32,108", "languages": "Catalan, Spanish, Occitan (Aranese)",
                  "currency": "Euro (EUR)"},
        "outline": [[0.15, 42.85], [3.35, 42.45], [3.2, 40.55], [0.3, 40.6], [0.1, 41.95], [0.15, 42.85]],
    },
    "greenland": {
        "official_name": "Greenland (Kalaallit Nunaat)", "established": "1979 / 2009 (self-government)",
        "flag_url": _flag("Flag of Greenland.svg"),
        "leader": {"name": "Jens-Frederik Nielsen", "title": "Premier (Naalakkersuisut)", "party": "Demokraatit"},
        "legislature": {"chamber": "Inatsisartut", "total": 31,
                        "parties": [["Demokraatit", 10, "#e30613"], ["Naleraq", 8, "#00529b"],
                                    ["Inuit Ataqatigiit", 7, "#e4001b"], ["Siumut", 4, "#e30613"],
                                    ["others", 2, "#888888"]]},
        "agenda": "Weigh a recognized path to full independence from Denmark against economic "
                  "dependence, manage intense US/great-power interest in Arctic minerals and "
                  "security, and develop rare-earth and fisheries wealth.",
        "stats": {"population": "~56,000", "area_km2": "~2,166,086", "languages": "Greenlandic (Kalaallisut), Danish",
                  "currency": "Danish krone (DKK)"},
        "outline": None,   # already drawn as a territory boundary (GRL)
    },
}


def _zone_base(z):
    return {"id": z[0], "name": z[1], "parent": z[2], "capital": z[3],
            "autonomy_basis": z[4], "lat": z[5], "lon": z[6], "context": z[7]}


def zones_list(include_historical: bool = True):
    out = []
    for z in AUTONOMOUS_ZONES:
        d = _zone_base(z)
        ex = ZONE_EXTRA.get(z[0], {})
        d["flag_url"] = ex.get("flag_url")
        d["outline"] = ex.get("outline")
        d["official_name"] = ex.get("official_name")
        d["historical"] = z[0] in HISTORICAL_ZONES
        if d["historical"] and not include_historical:
            continue
        out.append(d)
    return out


def zone_by_id(zid):
    for z in AUTONOMOUS_ZONES:
        if z[0] == zid:
            d = _zone_base(z)
            d.update(ZONE_EXTRA.get(zid, {}))
            d["historical"] = zid in HISTORICAL_ZONES
            return d
    return None
