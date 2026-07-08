"""v7.4.1 — autonomous regions / self-governing zones as a first-class entity
type (owner: "add autonomous zones as a new type of entity, e.g. Iraqi
Kurdistan"). These are NOT disputed territories and NOT sovereign states: they
are recognized sub-national entities with a real degree of self-rule inside a
sovereign parent. Each carries its parent state, capital, the basis of its
autonomy, and a context paragraph so clicking it opens a real breakdown, plus
an approximate centroid for a map marker.
"""

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
]


def zones_list():
    return [{"id": z[0], "name": z[1], "parent": z[2], "capital": z[3],
             "autonomy_basis": z[4], "lat": z[5], "lon": z[6], "context": z[7]}
            for z in AUTONOMOUS_ZONES]


def zone_by_id(zid):
    for z in AUTONOMOUS_ZONES:
        if z[0] == zid:
            return {"id": z[0], "name": z[1], "parent": z[2], "capital": z[3],
                    "autonomy_basis": z[4], "lat": z[5], "lon": z[6], "context": z[7]}
    return None
