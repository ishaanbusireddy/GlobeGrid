"""v6.6.2 — individually-named disputed territories for the disputed-mode map
layer. Each zone carries its controller, claimants, status and a context
paragraph so clicking it opens a real breakdown (owner: "each disputed zone
should have an individual breakdown w context when clicked on"; and explicitly
add Zaporizhzhia and Kherson as their own zones). Approximate centroid lat/lon
place the clickable marker; not a precise control polygon (that lives in the
conflict subfactions layer)."""

# id, name, controller, claimants, status, lat, lon, context
DISPUTED_ZONES = [
    ("crimea", "Crimea", "Russia (de facto)", ["Ukraine", "Russia"],
     "Annexed by Russia in 2014; internationally recognized as Ukrainian.",
     45.3, 34.4,
     "The Crimean Peninsula was annexed by Russia in March 2014 following an "
     "unrecognized referendum. Ukraine and the overwhelming majority of UN "
     "members consider it occupied Ukrainian territory (UNGA 68/262). Russia "
     "administers it as two federal subjects. Home to the Black Sea Fleet at "
     "Sevastopol."),
    ("donetsk", "Donetsk Oblast", "Contested (partial Russian occupation)",
     ["Ukraine", "Russia"],
     "Partially occupied; claimed-annexed by Russia in 2022, recognized as Ukrainian.",
     48.0, 37.8,
     "One of four oblasts Russia declared annexed in September 2022 after "
     "unrecognized referendums. Front lines run through the oblast; Ukraine "
     "controls significant territory. The 2014 'DPR' proxy statelet was folded "
     "into the Russian claim. No state besides Russia recognizes the annexation."),
    ("luhansk", "Luhansk Oblast", "Russia (de facto, near-full)",
     ["Ukraine", "Russia"],
     "Near-fully occupied; claimed-annexed 2022, recognized as Ukrainian.",
     48.6, 39.3,
     "The most fully occupied of the four claimed-annexed oblasts. The 2014 "
     "'LPR' proxy entity preceded the 2022 annexation claim, which no state but "
     "Russia recognizes. Ukraine continues counter-offensive operations along "
     "its western edge."),
    ("zaporizhzhia", "Zaporizhzhia Oblast", "Contested (partial Russian occupation)",
     ["Ukraine", "Russia"],
     "Southern half occupied incl. the nuclear plant; claimed-annexed 2022.",
     47.2, 35.4,
     "Russia occupies the southern half including Europe's largest nuclear "
     "plant (Zaporizhzhia NPP, under IAEA concern), but NOT the oblast capital "
     "Zaporizhzhia city, which Ukraine holds. Declared annexed by Russia in "
     "2022 despite not controlling all of it — recognized internationally as "
     "Ukrainian."),
    ("kherson", "Kherson Oblast", "Contested (Dnipro front)",
     ["Ukraine", "Russia"],
     "Split along the Dnipro; Kherson city liberated Nov 2022; claimed-annexed.",
     46.6, 33.4,
     "Ukraine liberated the right-bank oblast including Kherson city in November "
     "2022; Russia holds the left (east) bank across the Dnipro. Part of the "
     "four-oblast 2022 annexation claim recognized by no state but Russia. The "
     "river is now the front line."),
    ("kashmir", "Kashmir", "Divided (India / Pakistan / China)",
     ["India", "Pakistan", "China"],
     "Divided by the Line of Control and Line of Actual Control since 1947/1962.",
     34.0, 76.0,
     "Claimed in full by both India and Pakistan and administered in parts by "
     "India, Pakistan and China (Aksai Chin). Three wars and ongoing skirmishes "
     "along the Line of Control. India revoked Article 370 autonomy in 2019."),
    ("taiwan", "Taiwan", "Republic of China (self-governed)",
     ["Taiwan (ROC)", "China (PRC)"],
     "Self-governed democracy; claimed by the PRC as a province.",
     23.7, 121.0,
     "Governed independently by the Republic of China since 1949; the PRC "
     "claims it under the One China principle and has not renounced force. Most "
     "states maintain unofficial ties. A major flashpoint in US-China relations."),
    ("western_sahara", "Western Sahara", "Morocco (most) / SADR (Polisario)",
     ["Morocco", "SADR (Polisario)"],
     "Largely Moroccan-controlled; a UN non-self-governing territory.",
     24.5, -13.0,
     "A former Spanish colony claimed by Morocco and by the Sahrawi Arab "
     "Democratic Republic (Polisario Front). Morocco controls ~80% west of a "
     "sand berm; the UN lists it as a non-self-governing territory pending a "
     "long-delayed self-determination referendum."),
    ("kosovo", "Kosovo", "Republic of Kosovo (partial recognition)",
     ["Kosovo", "Serbia"],
     "Declared independence 2008; recognized by ~100 states, not by Serbia.",
     42.6, 20.9,
     "Declared independence from Serbia in 2008; recognized by roughly half of "
     "UN members (including most of the West) but not by Serbia, Russia or "
     "China. EU-facilitated normalization talks continue amid periodic tension "
     "in the Serb-majority north."),
    ("falklands", "Falkland Islands / Malvinas", "United Kingdom (de facto)",
     ["United Kingdom", "Argentina"],
     "British Overseas Territory since 1833; claimed by Argentina as Las Malvinas.",
     -51.75, -59.0,
     "A British Overseas Territory in the South Atlantic, self-governing under "
     "UK sovereignty since 1833. Argentina claims the islands as Las Malvinas; "
     "the two fought a war over them in 1982 (Argentina defeated). A 2013 "
     "referendum saw islanders vote 99.8% to remain British. Argentina "
     "continues to press the claim diplomatically at the UN."),
    # v6.6.6 — Antarctica: seven states maintain territorial claims (all frozen
    # by the 1959 Antarctic Treaty, in force 1961). Three overlap in the
    # Antarctic Peninsula (UK / Argentina / Chile). Marié Byrd Land is unclaimed.
    ("antarctica_uk", "British Antarctic Territory", "Claim frozen (Antarctic Treaty)",
     ["United Kingdom", "Argentina", "Chile"],
     "20°W–80°W sector; overlaps the Argentine and Chilean claims.",
     -75.0, -50.0,
     "The British Antarctic Territory (20°W to 80°W) is the UK's Antarctic claim, "
     "dating to 1908. It overlaps almost entirely with the Argentine and Chilean "
     "claims on the Antarctic Peninsula. Like all Antarctic claims it is held in "
     "abeyance by the 1959 Antarctic Treaty, which reserves the continent for "
     "peaceful and scientific use and neither recognizes nor disputes claims."),
    ("antarctica_arg", "Argentine Antarctica", "Claim frozen (Antarctic Treaty)",
     ["Argentina", "United Kingdom", "Chile"],
     "25°W–74°W sector; overlaps the British and Chilean claims.",
     -75.0, -49.0,
     "Argentina claims the sector between 25°W and 74°W as part of Tierra del "
     "Fuego province, overlapping the British and Chilean claims. Argentina "
     "operates several year-round bases and stresses its permanent presence. "
     "The claim is frozen under the Antarctic Treaty."),
    ("antarctica_chile", "Chilean Antarctic Territory", "Claim frozen (Antarctic Treaty)",
     ["Chile", "United Kingdom", "Argentina"],
     "53°W–90°W sector; overlaps the British and Argentine claims.",
     -75.0, -70.0,
     "Chile claims the sector between 53°W and 90°W as the Antarctic Chilean "
     "Province, overlapping the British and Argentine claims on the Peninsula. "
     "Chile maintains bases and even a civilian settlement (Villa Las Estrellas). "
     "The claim is suspended under the Antarctic Treaty."),
    ("antarctica_aus", "Australian Antarctic Territory", "Claim frozen (Antarctic Treaty)",
     ["Australia"],
     "The largest single claim: ~42% of Antarctica (two sectors).",
     -75.0, 100.0,
     "The Australian Antarctic Territory is the largest of the seven claims, "
     "covering roughly 42% of the continent in two sectors (45°E–136°E and "
     "142°E–160°E). Australia runs major research stations (Davis, Mawson, "
     "Casey). The claim is frozen under the Antarctic Treaty."),
    ("antarctica_nzl", "Ross Dependency", "Claim frozen (Antarctic Treaty)",
     ["New Zealand"],
     "160°E–150°W sector, including the Ross Ice Shelf.",
     -80.0, 175.0,
     "New Zealand's Ross Dependency (160°E to 150°W) includes the Ross Ice Shelf "
     "and Ross Island, home to Scott Base and (nearby) the US McMurdo Station. "
     "The claim dates to 1923 and is held in abeyance by the Antarctic Treaty."),
    ("antarctica_nor", "Queen Maud Land", "Claim frozen (Antarctic Treaty)",
     ["Norway"],
     "20°W–45°E sector on the Atlantic-facing coast.",
     -72.0, 10.0,
     "Norway claims Queen Maud Land (Dronning Maud Land), the sector roughly "
     "20°W to 45°E, plus Peter I Island. Norway runs the Troll research station. "
     "The claim is frozen under the Antarctic Treaty."),
    ("antarctica_fra", "Adélie Land", "Claim frozen (Antarctic Treaty)",
     ["France"],
     "136°E–142°E sector, enclosed by the Australian claim.",
     -75.0, 139.0,
     "France's Adélie Land (Terre Adélie, 136°E to 142°E) is a narrow sector "
     "enclosed within the Australian claim, administered as part of the French "
     "Southern and Antarctic Lands. France runs Dumont d'Urville station. The "
     "claim is frozen under the Antarctic Treaty."),
]

def zones_list():
    return [{"id": z[0], "name": z[1], "controller": z[2], "claimants": z[3],
             "status": z[4], "lat": z[5], "lon": z[6], "context": z[7]}
            for z in DISPUTED_ZONES]


def zone_by_id(zid):
    for z in DISPUTED_ZONES:
        if z[0] == zid:
            return {"id": z[0], "name": z[1], "controller": z[2], "claimants": z[3],
                    "status": z[4], "lat": z[5], "lon": z[6], "context": z[7]}
    return None
