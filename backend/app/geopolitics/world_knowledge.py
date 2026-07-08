"""v7 Part 6 — All-Around Comprehensive Intelligence: the curated world-
knowledge layer.

Dense offline dossiers — written from the historical/geopolitical record
through EARLY 2026 — for countries, conflicts, alliances, non-state actors,
regions and the UN. Every panel renders its dossier INSTANTLY at start (no
LLM, no network), and the same text is injected into analyst/LLM prompts as
grounding so the AI can explain any topic in depth to a user who has never
heard of it.

Facts here are stable background (history, geography, structural politics,
economics, culture); anything fast-moving is framed "as of early 2026" and the
live feed + fact chain supply what happened since.
"""

# ── regional briefs (UN M49 subregions, condensed) ──────────────────────────
REGION_BRIEFS = {
    "Eastern Europe": (
        "Shaped by the Soviet collapse and NATO/EU eastward expansion, the region is the "
        "front line of Europe's post-Cold-War order. Russia's 2014 seizure of Crimea and "
        "2022 full-scale invasion of Ukraine turned it into the continent's principal war "
        "zone, driving Baltic and Central European rearmament, energy decoupling from "
        "Russian gas, and Finland's and Sweden's NATO accession (2023-24). Orthodoxy and "
        "Slavic languages dominate; economies range from EU-integrated Poland/Czechia to "
        "sanctioned, war-mobilized Russia."),
    "Western Asia": (
        "The Middle East's core: the Levant, Anatolia, Mesopotamia, the Gulf and the "
        "Caucasus. Defined by the Israeli-Palestinian conflict, the Iran-Saudi/Israel "
        "rivalry, hydrocarbon wealth (Saudi Arabia, UAE, Qatar, Iraq), and the aftershocks "
        "of the Arab Spring and Syria's war — including the December 2024 fall of the "
        "Assad dynasty. Sunni-Shia dynamics, Kurdish statelessness across four countries, "
        "and Turkish, Iranian and Gulf-Arab spheres of influence structure most disputes."),
    "Southern Asia": (
        "A quarter of humanity: India's rise as the world's most populous state and "
        "fifth-largest economy anchors the region, locked in nuclear-armed rivalry with "
        "Pakistan over Kashmir (open fighting recurred in May 2025) while Taliban-ruled "
        "Afghanistan, Iran and a debt-stressed Sri Lanka/Bangladesh/Nepal periphery orbit "
        "it. Hindu, Muslim and Buddhist civilizational currents intersect; the "
        "India-China Himalayan standoff and Indian Ocean sea lanes give it global weight."),
    "Eastern Asia": (
        "The world's manufacturing and technology heartland. China's party-state under Xi "
        "Jinping contests US primacy — over Taiwan above all — while Japan and South "
        "Korea, both US treaty allies, rearm; North Korea advances nuclear-armed missiles "
        "and now supplies troops and munitions to Russia. Semiconductors (Taiwan's TSMC, "
        "Korea's Samsung), aging populations, and disputed waters (East/South China Seas) "
        "define the strategic landscape."),
    "Northern Africa": (
        "Arab-Berber North Africa: Egypt's demographic weight and Suez chokepoint, "
        "Algeria-Morocco cold war over Western Sahara, Libya's fractured post-Gaddafi "
        "duopoly of governments, and Sudan's catastrophic 2023- civil war between army "
        "and RSF. Migration routes to Europe, Nile water politics (GERD dam), and "
        "hydrocarbons tie it to both Mediterranean Europe and the Sahel."),
    "Sub-Saharan Africa": (
        "The world's youngest, fastest-urbanizing region. Nigeria, Ethiopia, DR Congo and "
        "South Africa anchor sub-regional systems strained by jihadist insurgency across "
        "the Sahel (where juntas expelled French forces and courted Russia), the eastern "
        "Congo's mineral wars, and Horn-of-Africa fragmentation. Critical minerals "
        "(cobalt, lithium), Gulf/Chinese/Western competition for ports and mines, and the "
        "AU's halting integration set the strategic frame."),
    "South-eastern Asia": (
        "ASEAN's ten states balance between China and the US: South China Sea claims pit "
        "Vietnam, the Philippines, Malaysia and Brunei against Beijing's nine-dash line; "
        "Myanmar's post-2021-coup civil war is the region's bleeding wound; Indonesia, "
        "the world's largest Muslim-majority democracy, and Singapore's financial hub "
        "give the region economic heft along the Malacca Strait chokepoint."),
    "Latin America and the Caribbean": (
        "From Mexico's cartel wars and US-linked economy to Brazil's continental "
        "agriculture-and-Amazon power, the region oscillates between left and right "
        "'pink tide' cycles. Venezuela's authoritarian crisis (and 2025-26 US pressure "
        "campaign), Argentina's Milei-era shock liberalization, and Caribbean fragility "
        "(Haiti's state collapse) coexist with deep US, and growing Chinese, economic "
        "presence (lithium triangle, soy, copper)."),
    "Northern America": (
        "The United States — the system-setting superpower, in a second Trump term since "
        "January 2025 marked by tariff wars, immigration crackdowns and transactional "
        "alliance politics — plus Canada, its largest trading partner, increasingly "
        "pressured over trade and Arctic sovereignty."),
    "Western Europe / EU core": (
        "The EU's Franco-German engine plus Benelux: post-2022 rearmament, energy "
        "transition, and populist-right pressure (AfD, RN) strain the postwar consensus; "
        "the bloc navigates between US alliance dependence and 'strategic autonomy'."),
    "Oceania": (
        "Australia and New Zealand — AUKUS submarines, Five Eyes intelligence, China "
        "trade dependence — plus Pacific island microstates courted by Beijing and "
        "Washington for security pacts and facing existential sea-level rise."),
    # v7.3 — Central Asia was wrongly mapped to the Eastern Europe brief (owner:
    # "Kazakhstan is in Central Asia not eastern europe … wth").
    "Central Asia": (
        "The five post-Soviet 'stans' — Kazakhstan, Uzbekistan, Turkmenistan, "
        "Kyrgyzstan and Tajikistan — sit between Russia, China and the wider "
        "Islamic world. Rich in oil, gas, uranium and rare metals, they 'multi-"
        "vector': keeping old security ties to Moscow (CSTO, the Russian language, "
        "labour migration) while China's Belt and Road builds the pipelines, roads "
        "and rail that break their landlocked isolation, and the West and Türkiye "
        "court them for energy and as a sanctions-era transit corridor. Mostly "
        "secular, authoritarian, Turkic-speaking (Tajikistan is Persian-speaking); "
        "watch water disputes over the Amu Darya and Syr Darya, the Afghan border, "
        "and succession politics after decades of strongman rule."),
}

# ── conflict explainers — written for someone who has never heard of them ───
CONFLICT_BRIEFS = {
    "Russia–Ukraine War": (
        "Europe's largest war since 1945. Roots: Ukraine's post-Soviet drift toward the "
        "EU/NATO collided with Moscow's claim to a sphere of influence; after Kyiv's 2014 "
        "Maidan revolution Russia seized Crimea and fueled a Donbas proxy war. On 24 Feb "
        "2022 Putin launched a full invasion expecting days; Ukrainian resistance held "
        "Kyiv, then counter-offensives retook Kharkiv and Kherson (2022). Since 2023 the "
        "war ossified into attritional trench/drone warfare along a ~1,000 km front "
        "across Donetsk, Luhansk, Zaporizhzhia and Kherson oblasts (~18% of Ukraine "
        "occupied), with deep-strike drone campaigns on refineries and grids both ways. "
        "The West arms Kyiv and sanctions Moscow; North Korea sent troops, Iran drones. "
        "2025 US-brokered ceasefire probes failed to produce a settlement. Stakes: the "
        "European security order, nuclear signaling, global grain/energy flows."),
    "Israel–Palestine Conflict": (
        "A century-old contest between two national movements over the same land. Key "
        "layers: 1948 Israeli independence and Palestinian displacement (Nakba); 1967 "
        "occupation of the West Bank, Gaza and East Jerusalem; failed Oslo peace process "
        "(1990s); Hamas rule in Gaza since 2007 under blockade. Hamas's 7 Oct 2023 "
        "massacre (~1,200 killed, 250 hostages) triggered a devastating Israeli campaign "
        "that leveled much of Gaza (tens of thousands killed), spilled into a 2024 "
        "Israel-Hezbollah war in Lebanon, and direct Iran-Israel missile exchanges. A "
        "phased ceasefire/hostage deal took hold in January 2025, followed by a fragile, "
        "repeatedly-strained truce and reconstruction/governance struggle in Gaza through "
        "2025-26, while West Bank settlement expansion and settler violence accelerated. "
        "Core issues: statehood, Jerusalem, refugees, security architecture."),
    "U.S.–Iran War": (
        "The June 2025 direct clash between Israel/US and Iran — the first open "
        "state-on-state war between Washington and Tehran after decades of proxy "
        "conflict. Israel's 13 June 2025 'Rising Lion' strikes decapitated IRGC command "
        "and nuclear-program leadership; the US joined with B-2 'Midnight Hammer' strikes "
        "on the Fordow, Natanz and Isfahan nuclear sites (22 June); Iran answered with "
        "missile barrages on Israel and a signaled strike on al-Udeid airbase in Qatar. "
        "A US-brokered ceasefire on 24 June 2025 halted the 12-day war. Aftermath: "
        "Iran's air defenses and proxies (Hezbollah already mauled in 2024) degraded, "
        "nuclear program set back but intact in know-how, IAEA access contested, and the "
        "regime doubling down internally. Escalation risk persists around Hormuz transit "
        "and renewed enrichment."),
    "Sudan Civil War": (
        "Since April 2023, a war between two generals who jointly seized power in 2021: "
        "Abdel Fattah al-Burhan's Sudanese Armed Forces (SAF) vs Mohamed Hamdan Dagalo "
        "('Hemedti')'s paramilitary Rapid Support Forces (RSF, heir to the Janjaweed). "
        "Khartoum was shattered; the RSF overran Darfur (El Fasher fell in late 2025 "
        "amid massacres of Masalit and other communities — genocide determinations by "
        "the US) while the SAF recaptured the capital region in 2025. It is the world's "
        "largest displacement crisis (12M+ displaced, famine declared). External hands: "
        "UAE linked to RSF supply, Egypt/Saudi backing SAF, Russian interests in Red Sea "
        "basing and gold. The state has effectively partitioned along a west-east axis."),
    "Myanmar Civil War": (
        "The February 2021 military coup against Aung San Suu Kyi's elected government "
        "ignited a nationwide revolt: the exiled National Unity Government's People's "
        "Defence Forces allied with veteran ethnic armed organizations (Karen, Kachin, "
        "Karenni, Chin, Arakan Army, Ta'ang, MNDAA). Operation 1027 (Oct 2023) broke the "
        "junta's grip on the borderlands; by 2025-26 the regime held the central cities "
        "and little else, leaning on conscription, airstrikes, and Chinese/Russian "
        "support, while the Arakan Army neared full control of Rakhine. The March 2025 "
        "Sagaing earthquake compounded collapse. A junta-staged December 2025 election "
        "was widely dismissed. Stakes: China's corridors to the Indian Ocean, narcotics "
        "and scam-center economies, Rohingya persecution."),
    "Sahel Insurgency": (
        "A two-decade jihadist expansion across Mali, Burkina Faso and Niger by JNIM "
        "(al-Qaeda-aligned) and Islamic State Sahel Province, feeding on state weakness, "
        "pastoralist-farmer conflict and borders drawn without regard to communities. "
        "Military juntas (Mali 2020/21, Burkina 2022, Niger 2023) expelled French and UN "
        "forces, formed the Alliance of Sahel States (AES), left ECOWAS, and hired "
        "Russian (Wagner/Africa Corps) muscle — yet lost ground: by 2025 JNIM besieged "
        "cities and blockaded Bamako's fuel routes, Burkina controlled under half its "
        "territory, and violence spilled toward coastal West Africa (Benin, Togo). It is "
        "now the epicenter of global jihadist momentum."),
    "DRC–M23 Conflict": (
        "Eastern Congo's wars descend from the 1994 Rwandan genocide's aftershocks: "
        "Hutu génocidaire remnants (FDLR) in Congo, Rwanda-backed Tutsi rebellions, and "
        "a scramble for coltan/gold/tin. M23 ('March 23 Movement'), Tutsi-led and — per "
        "UN experts — directly supported by Rwandan troops, resurged in 2021; in early "
        "2025 it captured Goma and Bukavu, the east's two major cities, effectively "
        "annexing a Rwandan-influenced enclave. A US-brokered DRC-Rwanda framework and "
        "Doha tracks produced accords in 2025 but implementation stalls; dozens of other "
        "militias (ADF/ISCAP, Wazalendo) keep the region among the world's deadliest, "
        "with minerals-for-security deals drawing in US and Gulf interests."),
    "India–Pakistan Wars": (
        "Rival heirs of the 1947 Partition, both nuclear-armed since 1998, with four "
        "wars (1947, 1965, 1971 — which birthed Bangladesh — and Kargil 1999) and "
        "perpetual crisis over divided Kashmir. India revoked Kashmir's autonomy in "
        "2019. The April 2025 Pahalgam massacre of Hindu tourists triggered May 2025's "
        "'Operation Sindoor': four days of missile, drone and air combat deep into both "
        "countries — the worst fighting in decades — ended by a ceasefire both claim "
        "credit for. India suspended the Indus Waters Treaty, weaponizing river flows. "
        "China backs Pakistan (JF-17s, CPEC); the US courts India. Flashpoints: LoC "
        "skirmishes, cross-border militancy, water."),
    "Armenia–Azerbaijan Conflict": (
        "A South Caucasus territorial conflict over Nagorno-Karabakh, an ethnic-Armenian "
        "enclave inside Soviet-drawn Azerbaijan. Armenia won the 1990s war; Azerbaijan, "
        "oil-rich and Turkish-backed, reversed it in 2020 (44-day war) and in September "
        "2023 seized the whole enclave in a day — its ~100,000 Armenians fled en masse. "
        "Since then Baku holds all cards: an August 2025 Washington-brokered peace "
        "framework (including a US-operated 'Trump Route'/Zangezur transit corridor "
        "through Armenia's Syunik) advanced normalization, but the treaty remains "
        "unsigned amid Azerbaijani demands for Armenian constitutional changes. Russia's "
        "influence collapsed; Armenia pivots West/EU while Turkey-Azerbaijan integration "
        "deepens."),
    "Kurdish–Turkish Insurgency": (
        "Since 1984 the PKK (Kurdistan Workers' Party) fought Turkey for Kurdish rights/ "
        "autonomy — 40,000+ dead. Imprisoned founder Abdullah Öcalan called in February "
        "2025 for the PKK to dissolve; the group declared an end to armed struggle and "
        "began symbolic disarmament (May-July 2025), the most serious peace opening in a "
        "decade, entangled with Turkish politics (Erdoğan's term math, DEM party) and "
        "with the fate of Kurdish-led SDF in post-Assad Syria, which Ankara presses to "
        "integrate into Damascus's new army. Fragile: hardline PKK wings, Turkish "
        "operations in Iraq/Syria, and distrust could reignite it."),
    "Balochistan Insurgency": (
        "Ethnic-Baloch separatists (BLA, BLF) fight Pakistan over the province's "
        "resources (gas, Gwadar port) and decades of marginalization — the fifth "
        "insurgency wave since 1948, sharply escalated 2024-26: the March 2025 Jaffar "
        "Express train hijacking (400+ hostages) marked a new capability. Attacks "
        "target Chinese CPEC projects and personnel; Pakistan alleges Indian backing; "
        "enforced disappearances fuel the grievance cycle. Interlocks with TTP jihadist "
        "violence and Pakistan-Afghanistan (Taliban) border clashes of Oct 2025."),
    "Naxalite–Maoist Insurgency": (
        "India's Maoist ('Naxalite', from 1967 Naxalbari uprising) rural insurgency in "
        "the tribal 'Red Corridor' (Chhattisgarh-Jharkhand-Odisha), feeding on land "
        "dispossession and mining. Once 'India's greatest internal security threat' "
        "(Manmohan Singh), it has been ground down: massive paramilitary operations "
        "2024-26 (Kagar offensive) killed top leadership (Basavaraju, May 2025) and "
        "Delhi set a March 2026 elimination deadline — the movement is at its weakest "
        "in decades, though grievances persist."),
    "Cabo Delgado Insurgency": (
        "Since 2017, ISIS-Mozambique ('al-Shabaab', unrelated to Somalia's) terrorizes "
        "gas-rich northern Mozambique — beheadings, child abduction, the 2021 Palma "
        "attack that froze TotalEnergies' $20B LNG project. Rwandan troops and SADC "
        "forces clawed back towns; insurgents shifted to dispersed raids with 2024-25 "
        "resurgence waves displacing hundreds of thousands. Poverty, ruby/gas wealth "
        "captured by elites, and Tanzanian-border dynamics sustain it; TotalEnergies "
        "moved to restart the LNG project in 2025."),
    "ELN Insurgency (Colombia)": (
        "The National Liberation Army (ELN), a 1964 Marxist-Guevarist guerrilla now "
        "~6,000 fighters, outlived the FARC's 2016 peace. Petro's 'total peace' talks "
        "collapsed after the ELN's January 2025 Catatumbo offensive against FARC "
        "dissidents (100+ killed, 50,000 displaced) — the group functions increasingly "
        "as a binational cartel-insurgency astride the Venezuela border (cocaine, "
        "illegal gold), with sanctuary ties to Caracas. 2025-26 US strikes on alleged "
        "trafficking boats and pressure on Venezuela reshape its environment."),
    "West Papua Conflict": (
        "Melanesian West Papua was absorbed by Indonesia via the disputed 1969 'Act of "
        "Free Choice'. The OPM/TPNPB fights a low-grade guerrilla war for independence "
        "amid the world's largest gold mine (Grasberg), transmigration-driven "
        "demographic change, and reported military abuses; the 2023-25 hostage saga of "
        "NZ pilot Phillip Mehrtens (freed Sept 2024) drew rare attention. Jakarta's new "
        "provinces, special-autonomy money and security saturation contain but don't "
        "resolve it; ULMWP presses the Pacific Islands Forum for recognition."),
    "War in Afghanistan (2001–2021)": (
        "The US-led response to 9/11 toppled the Taliban's first emirate in weeks, then "
        "spent two decades attempting state-building against a Pakistan-sheltered "
        "insurgency. Peak 130k NATO troops; ~$2 trillion; Afghan forces collapsed in "
        "eleven days when the US withdrew under the 2020 Doha deal, and Kabul fell on "
        "15 Aug 2021. Legacy: Taliban emirate under Hibatullah Akhundzada — gender "
        "apartheid (girls barred from secondary school), ISIS-K terrorism exported "
        "abroad, frozen reserves, aid-dependent economy — and a cautionary tale about "
        "counterinsurgency and nation-building."),
    "Gulf Wars (1990–2011)": (
        "Two US-Iraq wars bracketing the sanctions decade: Desert Storm (1991) expelled "
        "Saddam from Kuwait with a half-million-strong coalition; the 2003 invasion — "
        "justified by never-found WMD — destroyed the Iraqi state, unleashed "
        "Sunni-Shia civil war, empowered Iran's militias, and incubated al-Qaeda in "
        "Iraq → ISIS. US withdrawal in 2011 preceded ISIS's 2014 caliphate. Legacy "
        "structures today's Iraq: Iran-aligned PMF militias vs sovereignty currents, "
        "Kurdish autonomy, and deep American ambivalence about Middle East wars."),
}

# ── country dossiers (majors; the composer covers everyone else) ─────────────
COUNTRY_BRIEFS = {
    "USA": ("Superpower anchor of the global order it now renegotiates. Federal "
        "presidential republic, ~335M people, world's largest economy ($28T+) and "
        "military (~$900B). Second Trump administration (Jan 2025-) pursues tariff-first "
        "trade policy, mass-deportation immigration enforcement, transactional alliances "
        "('burden-sharing'), and rivalry with China as organizing principle. Deep partisan "
        "polarization; dollar and Treasury markets remain the world's financial "
        "foundation. Key levers: Fed policy, semiconductor export controls, NATO Article "
        "5 credibility, Indo-Pacific alliance lattice (Japan/Korea/Australia/Philippines)."),
    "CHN": ("Party-state superpower challenger. Xi Jinping's CCP (third term, no "
        "successor) centralizes power over 1.4B people and the world's #2 economy — "
        "manufacturing colossus (EVs, batteries, solar, shipbuilding) fighting deflation, "
        "property-sector collapse and youth unemployment. Military buildup (world's "
        "largest navy) aims at Taiwan contingencies by late-2020s benchmarks; gray-zone "
        "pressure on Philippines and Taiwan daily. Tech war with US over chips; Belt & "
        "Road creditor to the Global South; 'no-limits' partnership with Russia short of "
        "open arms supply. Demographic decline is the long shadow."),
    "RUS": ("Revisionist nuclear power waging Europe's largest war since 1945. Putin's "
        "personalist regime (in power since 2000) survived sanctions by war-economy "
        "mobilization, Chinese/Indian oil purchases, and shadow-fleet exports; inflation "
        "and labor shortages bite. Occupies ~18% of Ukraine; hybrid operations (sabotage, "
        "cable-cutting, election interference) across Europe; North Korean troops and "
        "Iranian drones fill gaps. Wagner-successor Africa Corps projects power in Sahel/ "
        "Libya. World's largest nuclear arsenal is the regime's ultimate insurance."),
    "IND": ("Most populous country (1.43B), fifth-largest economy, aspiring pole in a "
        "multipolar order. Modi's BJP (third term, 2024, now coalition-dependent) blends "
        "Hindu-nationalist politics with infrastructure-led growth (~7%) and digital "
        "public goods. Strategic autonomy: Quad member buying Russian oil and S-400s; "
        "May 2025 armed clash with Pakistan; Himalayan standoff with China thawing "
        "slowly. Strengths: demographics, services, pharma; frictions: US tariffs, "
        "manufacturing depth, communal tensions, Kashmir."),
    "PAK": ("Nuclear-armed, army-dominated hybrid state of 240M in chronic crisis: "
        "IMF-dependent economy, TTP jihadist and Baloch separatist insurgencies, and "
        "the imprisonment of popular ex-PM Imran Khan. Field Marshal Asim Munir is the "
        "de facto power center behind a Sharif-family civilian façade. May 2025 war "
        "with India; October 2025 border fighting with Taliban Afghanistan; CPEC binds "
        "it to China while it courts Washington and Gulf financiers simultaneously."),
    "UKR": ("Invaded democracy fighting an existential war since Feb 2022 (Crimea/Donbas "
        "since 2014). Zelenskyy's wartime government fields Europe's most combat-"
        "experienced army and a world-leading drone industrial base; holds ~82% of "
        "territory, endures strikes on its grid, and depends on Western finance/arms "
        "amid US aid volatility. EU candidate (accession talks opened); Black Sea "
        "corridor exports grain despite the war. War aims: survival, security "
        "guarantees, eventual EU/NATO anchoring; manpower and air defense are the "
        "chronic constraints."),
    "ISR": ("High-tech regional military power in its most transformative and "
        "controversial period. Netanyahu's coalition fought the post-Oct-7 Gaza war, "
        "decapitated Hezbollah (2024), struck Iran directly (June 2025 with the US), "
        "and saw Assad's Syria collapse — regional military dominance alongside "
        "diplomatic isolation, ICC/ICJ proceedings, and internal rupture over the "
        "hostages, judiciary and Haredi conscription. Abraham Accords endure; Saudi "
        "normalization hinges on Palestinian statehood questions it rejects."),
    "PSE": ("Stateless nation of ~5.5M in the West Bank, Gaza and East Jerusalem (plus "
        "a large diaspora). The aging Fatah-run Palestinian Authority administers "
        "West Bank enclaves under occupation and settlement expansion; Hamas ruled Gaza "
        "2007-2023 and triggered the Oct 7 war that devastated it. 2025's ceasefire "
        "left Gaza's governance/reconstruction contested (Arab/US frameworks, "
        "stabilization forces). 140+ states recognize 'Palestine' (several G7 members "
        "added 2024-25); sovereignty remains aspirational."),
    "IRN": ("Revolutionary Shia theocracy under Supreme Leader authority (Khamenei, "
        "with succession looming), 90M people, wounded but unbowed after the June 2025 "
        "war: proxies mauled (Hezbollah, Assad gone), nuclear sites struck, air "
        "defenses exposed — yet enrichment know-how, missile forces and repression "
        "endure. Economy sanctions-strangled (oil to China at discount); water/energy "
        "crises and generational alienation simmer. Strategy: reconstitute deterrence, "
        "leverage Hormuz, deepen Russia/China alignment."),
    "SAU": ("G20 petrostate executing history's most ambitious economic pivot. Crown "
        "Prince Mohammed bin Salman's Vision 2030 (NEOM, tourism, sports/entertainment) "
        "spends oil wealth to escape oil; OPEC+ swing producer; détente with Iran "
        "(2023, Chinese-brokered) while edging toward US security treaty + possible "
        "Israel normalization contingent on Palestinian horizon. Hosts Gaza/Ukraine "
        "diplomacy; buys leverage across Global South. Social liberalization pairs "
        "with hard authoritarianism."),
    "TUR": ("NATO's second army straddling Europe/Asia under Erdoğan (in power since "
        "2003): drone-export power (Bayraktar), S-400 buyer, Black Sea gatekeeper "
        "(Montreux), power-broker in post-Assad Syria (its proxies won), Caucasus "
        "(Azerbaijan patron) and Horn of Africa. Hosted Ukraine talks. Economy scarred "
        "by lira crises; opposition mayor İmamoğlu's 2025 arrest signaled hardening "
        "authoritarianism. PKK dissolution process could close a 40-year war. Plays "
        "all sides; indispensable and difficult ally."),
    "SYR": ("Post-Assad transitional state. Ahmed al-Sharaa (ex-HTS leader) toppled the "
        "53-year Assad dynasty in Dec 2024 and became transitional president: sanctions "
        "relief (US/EU 2025), Gulf/Turkish reconstruction capital, and integration "
        "deals with the Kurdish-led SDF — against sectarian massacres (Alawite coast, "
        "Druze Suwayda 2025), Israeli strikes/buffer seizures, ISIS remnants and a "
        "shattered economy. The pivotal question: inclusive state or new Islamist "
        "authoritarianism; Turkey and Gulf states are the patrons, Iran/Russia the "
        "ejected (Moscow bargains to keep Tartus/Hmeimim bases)."),
    "EGY": ("Arab world's demographic anchor (110M) under Sisi's military-centric rule: "
        "IMF-backstopped economy (pound devaluations, Gulf bailouts, $35B UAE Ras "
        "el-Hekma deal), Suez Canal revenues halved by Houthi Red Sea attacks, GERD "
        "Nile dispute with Ethiopia unresolved. Gaza-war frontline mediator (with "
        "Qatar/US) refusing displacement of Palestinians into Sinai; buys wheat at "
        "world scale — food security is regime security."),
    "IRQ": ("Oil-rich (OPEC #2) federal state balancing the US and Iran two years after "
        "ISIS's territorial defeat: Iran-aligned Popular Mobilization militias embedded "
        "in the state contest sovereignty-first currents; Kurdistan region autonomy "
        "frictions (budget, oil exports via Turkey) persist. November 2025 elections "
        "reshuffled the same elite bargain. Water scarcity (Tigris-Euphrates), "
        "corruption and youth unemployment are the deeper crises."),
    "LBN": ("Collapsed-currency confessional republic rebuilding after the 2024 "
        "Israel-Hezbollah war shattered Hezbollah's leadership (Nasrallah killed) and "
        "strongholds. President Joseph Aoun and PM Nawaf Salam (2025) — the first real "
        "government in years — pursue Hezbollah disarmament south of the Litani under "
        "US/French-monitored ceasefire, banking-sector reform, and Gulf re-engagement. "
        "Sovereignty vs the weakened but armed 'state within a state' is the defining "
        "struggle."),
    "YEM": ("Fragmented state where the Iran-backed Houthi movement (Ansar Allah) rules "
        "the populous northwest (Sanaa) and the internationally recognized "
        "government/STC hold the south (Aden). The Houthis' Red Sea shipping campaign "
        "(2023-) — resumed in waves against 'Israel-linked' vessels — made them a "
        "global chokepoint actor drawing US/UK/Israeli strikes. World's worst "
        "protracted humanitarian crisis; Saudi-Houthi tracks frozen; de facto "
        "partition hardens."),
    "AFG": ("Taliban emirate (since Aug 2021) under reclusive emir Hibatullah "
        "Akhundzada: the world's only regime barring girls from secondary school; "
        "opium ban largely enforced; aid-dependent economy under sanctions with frozen "
        "reserves; ISIS-K exports terrorism (Moscow 2024). Russia recognized the "
        "government (2025); China mines. October 2025 border war with Pakistan over "
        "TTP sanctuaries. 6M+ refugees; returns forced from Iran/Pakistan strain "
        "collapse-adjacent services."),
    "PRK": ("Totalitarian nuclear dynasty. Kim Jong Un abandoned unification doctrine "
        "(2024), enshrined South Korea as 'principal enemy', and cashed in on Ukraine: "
        "~12,000+ troops to Russia's Kursk front plus millions of shells for food, "
        "fuel, and likely missile/submarine technology. ICBMs (Hwasong-19) credibly "
        "range the US; tactical nukes doctrine lowers use threshold. Sanctions regime "
        "eroded by Russian veto; markets and information controls tighten."),
    "KOR": ("Tech-industrial democracy (Samsung, SK Hynix, Hyundai; K-culture soft "
        "power) whiplashed by President Yoon's December 2024 martial-law attempt, "
        "impeachment, and the 2025 election of Lee Jae-myung — who balances the US "
        "alliance (28,500 troops, tariff/defense-cost friction) with China trade and "
        "北 deterrence. World-lowest fertility (~0.7) is the existential curve; "
        "nuclear-latency debate grows as North Korea's arsenal does."),
    "JPN": ("Third-largest developed economy executing its biggest defense shift since "
        "1945: 2% GDP defense spending, counterstrike missiles, US alliance "
        "integration; first female PM Takaichi (Oct 2025) leans security-hawk amid "
        "China friction (Senkakus, her Taiwan remarks triggering Beijing's economic "
        "coercion). Yen weakness, BOJ normalization, aging/shrinking population; "
        "quiet superpower in semiconductors materials, robotics, and Indo-Pacific "
        "diplomacy (Quad, Philippines/Australia pacts)."),
    "TWN": ("De facto state China vows to absorb — the world's most dangerous "
        "flashpoint. President Lai Ching-te (DPP, 2024) governs 23M with a "
        "KMT/TPP-controlled legislature; TSMC fabs make it indispensable (90%+ of "
        "leading-edge chips; new fabs in Arizona/Japan hedge). Faces daily PLA "
        "incursions, blockade-rehearsal exercises, undersea-cable sabotage, election "
        "interference. US 'strategic ambiguity' plus arms; most states (incl. US) "
        "recognize Beijing, not Taipei."),
    "GBR": ("Nuclear P5 power post-Brexit: Starmer's Labour government (2024-) resets "
        "EU ties (2025 defense pact), leads on Ukraine (Storm Shadow, training, "
        "'coalition of the willing' planning), AUKUS pillar. Economy: London finance "
        "vs stagnant productivity, high debt; Reform UK's rise scrambles politics. "
        "Carrier strike groups, GCHQ intelligence and finance/sanctions "
        "infrastructure are the real levers."),
    "FRA": ("EU's only nuclear power and UN P5 seat; Macron's weakened presidency "
        "(hung parliament, revolving PMs, pension/budget crises) still drives "
        "'strategic autonomy', Ukraine support (Caesar guns, Mirage jets, troops-"
        "debate), and Indo-Pacific presence. Post-coup expulsion from the Sahel "
        "gutted Françafrique; Rassemblement National awaits 2027. Nuclear energy "
        "(70% of power) and Airbus/defense industry anchor its heft."),
    "DEU": ("EU's economic core in industrial malaise (energy costs post-Russian gas, "
        "Chinese EV competition, two years of contraction) undergoing a defense "
        "revolution: Merz's CDU-SPD government (2025) unlocked constitutional debt "
        "brakes for a €500B+ rearmament/infrastructure surge, aiming at Europe's "
        "largest conventional army. Ukraine's #2 backer; AfD polling first in "
        "stretches reshapes politics. Rheinmetall boom symbolizes the Zeitenwende."),
    "POL": ("Front-line NATO heavyweight: ~4%+ GDP on defense (Europe's highest), "
        "500k-target army, Abrams/HIMARS/K2 arsenals; logistics hub for Ukraine and "
        "host to millions of refugees. Tusk's pro-EU coalition cohabits with "
        "nationalist President Nawrocki (2025). Confronts Belarus border hybrid "
        "pressure and Russian sabotage; historical memory (1939, Katyn) makes it "
        "Europe's most hawkish Russia voice."),
    "BLR": ("Lukashenko's police-state (since 1994), survived 2020 protests via "
        "Russian backing — now hosts Russian tactical nuclear weapons and Oreshnik "
        "missiles, staged the Wagner interlude (2023), weaponizes migrants against "
        "EU borders. Sovereignty increasingly subsumed into Union State integration; "
        "political prisoners (~1,200) include Nobel laureate Bialiatski; opposition "
        "exiled under Tsikhanouskaya."),
    "IDN": ("World's 4th most populous state (280M), largest Muslim-majority "
        "democracy, ASEAN anchor. President Prabowo (2024) — ex-general — pursues "
        "free-meals welfare, a sovereign-wealth push (Danantara), nickel-downstream "
        "industrial policy (EV batteries; dominant global supply), and non-aligned "
        "'thousand friends' diplomacy (BRICS entry 2025) while managing South China "
        "Sea friction at Natuna and Papua insurgency."),
    "VNM": ("Party-state manufacturing riser — 'China+1' winner (Samsung, Apple "
        "suppliers) targeting 8% growth under General Secretary Tô Lâm's streamlined "
        "apparatus. 'Bamboo diplomacy': comprehensive strategic partnerships with "
        "US, China, Russia simultaneously; South China Sea claimant fortifying "
        "Spratly outposts while absorbing US tariff pressure (transshipment "
        "scrutiny). Mekong delta climate stress and aging-before-rich loom."),
    "PHL": ("US treaty ally on the South China Sea front line: Marcos Jr. expanded "
        "EDCA base access (9 sites, several facing Taiwan/Scarborough), publicizes "
        "Chinese coast-guard water-cannon/ramming at Second Thomas and Scarborough "
        "Shoals, buys BrahMos missiles and hosts US Typhon launchers — Beijing's "
        "loudest regional adversary. Duterte-Marcos clan feud (VP impeachment saga, "
        "Duterte at the ICC) churns domestic politics; 10%-of-GDP remittances."),
    "MMR": ("Failed-state battleground since the 2021 coup (see Myanmar Civil War). "
        "Junta chief Min Aung Hlaing holds the Bamar core via airpower, conscription "
        "and Chinese/Russian backing; resistance and ethnic armies hold most "
        "borderlands. Sagaing earthquake (Mar 2025), scam-center economies (Myawaddy), "
        "world's top opium producer again; Rohingya still stateless. A staged Dec "
        "2025 election changed nothing."),
    "AUS": ("US ally turning itself into an Indo-Pacific porcupine: AUKUS nuclear "
        "submarines (Virginia purchases then SSN-AUKUS build), northern-base US "
        "force posture, Quad member — while China takes 30%+ of exports (iron ore, "
        "lithium; trade war thawed 2023-24). Albanese's Labor re-elected 2025. "
        "Pacific islands security contest with Beijing (Solomons precedent); "
        "critical-minerals strategy courts allied capital."),
    "BRA": ("Latin America's giant (215M; agriculture/energy superpower — soy, iron, "
        "pre-salt oil) under Lula's third act: Amazon deforestation down sharply, "
        "BRICS/COP30 (Belém) diplomacy, trade-bloc courtship (EU-Mercosur signed "
        "2024). Bolsonaro's 2025 coup-plot conviction split politics; 2026 election "
        "looms. US tariff clash (50% Trump tariffs, partially rolled back) tested "
        "sovereignty; China is the top trade partner."),
    "MEX": ("US-integrated manufacturing power (top US trade partner; nearshoring "
        "winner) under Claudia Sheinbaum (2024-), first female president: high "
        "approval, state-capacity Morena project, judicial elections controversy. "
        "Cartel violence (CJNG/Sinaloa civil war after El Mayo's capture) drives US "
        "pressure — tariff threats, terrorist designations, drone-strike talk — "
        "managed via fentanyl/migration cooperation. USMCA 2026 review is pivotal."),
    "ARG": ("Milei's libertarian shock laboratory: chainsaw austerity produced fiscal "
        "surplus, inflation collapse (211%→~30%), IMF/US Treasury lifelines ($20B "
        "swap, 2025 midterm-eve bailout), peso still fragile. Vaca Muerta shale and "
        "lithium exports are the growth bet; Mercosur skeptic, US/Israel-aligned "
        "foreign policy pivot. Poverty spiked then eased; 2025 midterms strengthened "
        "his bloc — the experiment continues."),
    "VEN": ("Authoritarian petrostate in showdown with Washington: Maduro claimed the "
        "stolen 2024 election (opposition's Edmundo González exiled; María Corina "
        "Machado, 2025 Nobel Peace laureate, underground); 2025-26 US 'narco-"
        "terrorism' pressure campaign — boat strikes, carrier deployment, bounty — "
        "aims at regime change or negotiation. World's largest oil reserves produce "
        "under 1M bpd; 7.7M emigrants; Chevron licenses toggle as leverage."),
    "COL": ("US's closest South American partner strained under leftist Petro: 'total "
        "peace' talks with ELN/FARC dissidents collapsed into multi-front rural "
        "violence; cocaine output at records; Trump-era decertification and tariff "
        "spats. 2026 elections decide continuity. Institutions remain robust by "
        "regional standards; Venezuela spillover (border, migration, ELN sanctuary) "
        "is chronic."),
    "CUB": ("Communist survivor state in its deepest crisis since 1991: grid "
        "collapses/blackouts, 10%+ population emigration wave, food/fuel scarcity, "
        "dollarization creep. US embargo re-tightened (SSOT relisting); Russia/China "
        "patronage modest. Díaz-Canel's party manages decline; hosting of Chinese "
        "SIGINT facilities irritates Washington."),
    "NGA": ("Africa's demographic giant (230M; 400M by 2050) under Tinubu's shock "
        "reforms: fuel-subsidy removal and naira float halved real incomes before "
        "stabilizing; Dangote mega-refinery ends fuel imports. Insecurity on three "
        "fronts: Boko Haram/ISWAP northeast, bandit kidnapping economies northwest, "
        "farmer-herder Middle Belt violence — plus separatist embers southeast. "
        "Afrobeats/Nollywood soft power; oil theft undermines the fiscal core."),
    "ETH": ("Horn hegemon (120M) that never quite stabilizes: Abiy's Ethiopia ended "
        "the Tigray war (2022 Pretoria deal) only to fight Amhara Fano militias and "
        "face Oromo insurgency; GERD dam completed (2025) over Egyptian objection; "
        "sea-access obsession (Somaliland MoU 2024) nearly ignited war with Somalia "
        "(Ankara-brokered détente), Eritrea tensions rebuilt toward the brink. "
        "Fast-growing, debt-restructured economy; BRICS member."),
    "COD": ("Sub-continental resource state (100M+; cobalt ~70% of world supply, "
        "copper belt) whose east bleeds: Rwanda-backed M23 took Goma/Bukavu (2025) "
        "— see DRC-M23 Conflict. Tshisekedi trades minerals-for-security with "
        "Washington (2025 accords) and fights ADF/ISCAP jihadists with Uganda. "
        "State weakness, kleptocratic legacies and 7M displaced define the "
        "world's most under-covered crisis."),
    "ZAF": ("Africa's most industrialized economy governed post-2024 by a fragile "
        "ANC-DA 'government of national unity' after the ANC lost its 30-year "
        "majority. Load-shedding eased but logistics/ports decay; 32% unemployment. "
        "Foreign policy: BRICS host, ICJ genocide case against Israel, G20 "
        "presidency (2025) boycotted by Trump amid Afrikaner-'genocide' claims and "
        "aid/tariff punishment. Zuma's MK and EFF flank the center."),
    "KEN": ("East Africa's hub economy and Western security partner (Haiti mission "
        "lead, non-NATO ally designation) under Ruto — rocked by 2024-25 Gen-Z "
        "protest waves against taxes and police brutality (dozens killed). Debt "
        "distress managed via IMF/China balancing; Nairobi is the region's tech/"
        "logistics/diplomacy capital (Sudan, DRC tracks)."),
    "SOM": ("Fragile federation fighting al-Shabaab — al-Qaeda's richest franchise — "
        "which taxes, courts and governs across the south and surged in 2025. "
        "Mogadishu's government (Hassan Sheikh Mohamud) leans on ATMIS-successor AU "
        "forces, Turkish drones/bases and US strikes; federal-state rifts (Jubaland, "
        "Puntland) and the Ethiopia-Somaliland port saga strain unity. Somaliland "
        "runs itself, unrecognized, courting US recognition via Berbera."),
    "DZA": ("Gas-rich military-backed republic (Europe's #3 supplier post-Russia): "
        "Tebboune re-elected 2024; cold war with Morocco (Western Sahara, severed "
        "ties), France relations in crisis (Sahara recognition, writer Sansal's "
        "jailing), Russia arms client yet Sahel-junta wary (Mali drone spat). "
        "Hirak-era repression persists; hydrocarbon rents fund social peace."),
    "MAR": ("Monarchical stabilizer and Africa-facing hub: Western Sahara autonomy "
        "plan won US/French/Spanish backing (UNSC 2025 resolution tilted its way) — "
        "its defining diplomatic victory over Algeria/Polisario. Abraham Accords "
        "member; phosphates (~70% of world reserves), autos/aerospace exports, "
        "2030 World Cup co-host; Gen-Z protests (2025) over health/education met "
        "royal social spending."),
    "KAZ": ("Central Asia's resource anchor (uranium #1, oil via Russian-pipeline "
        "dependence) multi-vectoring among Russia, China (BRI land bridge), and the "
        "West (Middle Corridor, C5+1): Tokayev consolidated post-2022-unrest, "
        "keeps sanctions-compliance while trade with Russia booms; Abraham Accords "
        "accession (2025) typified its hedging."),
    "UZB": ("Central Asia's demographic core (37M) under Mirziyoyev's authoritarian "
        "modernization: privatization, Gulf/Chinese capital, labor migration to "
        "Russia. Cautious opening; Afghan pragmatism (rail projects with the "
        "Taliban); the region's swing state as Russian leverage wanes."),
    "GEO": ("South Caucasus EU-aspirant captured by the Georgian Dream party of "
        "billionaire Ivanishvili: 'foreign agents' law, suspended EU accession, "
        "contested 2024 elections, nightly protests, Western sanctions on leaders — "
        "a democratic backslide toward Moscow-friendly 'neutrality' while 20% of "
        "territory (Abkhazia, South Ossetia) sits under Russian occupation."),
    "SRB": ("Balkan pivot playing all sides: Vučić's regime buys Russian gas and "
        "Chinese arms/FDI, arms Ukraine ammunition indirectly, refuses Kosovo "
        "recognition (2023 Banjska raid; EU-mediated dialogue stalled), courts "
        "Trump-family real estate. Largest anti-corruption protest movement in "
        "decades (post-Novi-Sad canopy collapse, 2024-25) besieges his rule; EU "
        "candidacy nominal."),
    "XKX": ("Europe's youngest state (2008 independence; ~100 recognitions) with a "
        "NATO/KFOR security blanket: Kurti's Pristina asserts control over Serb-"
        "majority north (dinar ban, mayors) against Belgrade's parallel structures "
        "and EU criticism; Serbia refuses recognition backed by Russia/China UN "
        "vetoes. Diaspora remittances, Trepča minerals and US ties (Bondsteel) are "
        "structural facts."),
}

# ── alliance/bloc briefs ─────────────────────────────────────────────────────
ALLIANCE_BRIEFS = {
    "NATO": ("The North Atlantic Treaty Organization (1949): 32-member collective-"
        "defense alliance whose Article 5 ('attack on one is an attack on all') has "
        "been invoked once (9/11). Revitalized by Russia's invasion of Ukraine — "
        "Finland (2023) and Sweden (2024) joined; a 2025 Hague summit pledge targets "
        "5% GDP defense/security spending under intense US burden-sharing pressure. "
        "Deters Russia on the eastern flank (battlegroups, air policing) while "
        "debating Ukraine's eventual membership; Secretary General Mark Rutte."),
    "European Union": ("27-state economic-political union — the world's largest "
        "single market, a regulatory superpower (GDPR, AI Act, carbon border tax) "
        "and, since 2022, a slow-waking geopolitical actor: joint arms funds, "
        "Russia sanctions (18+ packages), Ukraine candidacy/finance (€100B+), "
        "rearmament plans (ReArm/SAFE). Strains: populist-right "
        "surges, migration, competitiveness vs US/China (Draghi report) — though "
        "the 2026 Hungarian election (Péter Magyar's TISZA unseating Orbán's "
        "Fidesz) removed Budapest's habitual veto from the equation. Von der "
        "Leyen Commission II; Council president Costa."),
    "BRICS": ("Global-South coordination bloc (Brazil, Russia, India, China, South "
        "Africa + 2024-25 expansion: Egypt, Ethiopia, Iran, UAE, Indonesia...) "
        "representing ~45% of humanity. Agenda: de-dollarized trade, development "
        "finance (NDB), multipolar order symbolism. Internally divided (India-China "
        "rivalry, democracies vs autocracies) — more forum than alliance, but the "
        "premier vehicle of non-Western alignment."),
    "OPEC": ("Oil cartel (12 members + the wider OPEC+ with Russia) controlling "
        "~40% of production; Saudi-led output cuts/raises steer prices against US "
        "shale supply. 2025: unwinding cuts to defend market share, testing member "
        "compliance (UAE, Iraq, Kazakhstan overproduction)."),
    "CSTO": ("Russia-led security pact (Belarus, Armenia*, Kazakhstan, Kyrgyzstan, "
        "Tajikistan) — a NATO mirror that failed its test: no help for Armenia in "
        "2020-23, prompting Yerevan's de facto exit (*membership frozen). Kazakhstan "
        "intervention (Jan 2022) was its one success; increasingly hollow as "
        "Central Asia hedges."),
    "Shanghai Cooperation Organisation": ("China/Russia-anchored Eurasian forum "
        "(India, Pakistan, Iran, Belarus, Central Asia): counter-terrorism "
        "exercises, energy ties, anti-Western communiqués — limited by India-China "
        "and India-Pakistan rivalries inside the tent."),
    "African Union": ("55-member continental body: Agenda 2063 integration (AfCFTA "
        "free-trade area), peace operations (Somalia), G20 seat (2023). Chronically "
        "underfunded and coup-challenged (Sahel juntas suspended), yet the "
        "continent's single diplomatic voice."),
    "ASEAN": ("Ten Southeast Asian states practicing consensus 'centrality': hedging "
        "between the US and China, failed on Myanmar (Five-Point Consensus ignored), "
        "negotiating a South China Sea code of conduct for 20+ years. Economic "
        "integration (RCEP) outpaces political unity; Timor-Leste accession 2025."),
    "AUKUS": ("2021 Australia-UK-US pact: nuclear-powered submarines for Australia "
        "(Virginia-class sales 2030s, then SSN-AUKUS builds) + Pillar 2 tech "
        "(hypersonics, AI, undersea). The Indo-Pacific's sharpest deterrence "
        "signal to China; survived a 2025 Pentagon review with tweaks."),
    "QUAD": ("US-Japan-India-Australia 'diamond' — maritime-security dialogue "
        "(domain awareness, cables, vaccines) that stops short of alliance because "
        "of India's autonomy; meets at leader level, irritates Beijing."),
    "Five Eyes": ("The US-UK-Canada-Australia-NZ signals-intelligence pact born of "
        "WWII (UKUSA): the deepest intelligence-sharing arrangement on earth "
        "(NSA/GCHQ et al.), now central to China tech-security policy (Huawei "
        "bans) and Russia sanctions enforcement."),
    "G7": ("The advanced-democracy steering group (US, Japan, Germany, UK, France, "
        "Italy, Canada + EU): Russia sanctions/oil price cap architecture, Ukraine "
        "$50B loans from frozen-asset profits, China 'de-risking' language — "
        "strained by Trump-era tariffs against its own members."),
    "Arab League": ("22 Arab states; readmitted Assad (2023) then welcomed his "
        "fall; coordinates Gaza reconstruction plans and Palestinian statehood "
        "diplomacy — historically long on communiqués, short on enforcement."),
    "GCC": ("Gulf Cooperation Council (Saudi, UAE, Qatar, Kuwait, Bahrain, Oman): "
        "petro-wealth club turned rivalrous-then-reconciled (2021 Al-Ula ended the "
        "Qatar blockade); sovereign funds (PIF, ADIA, QIA) project global "
        "financial power; US security umbrella with hedging toward China/Russia."),
    "Mercosur": ("South American customs union (Brazil, Argentina, Uruguay, "
        "Paraguay; Venezuela suspended): EU trade deal signed 2024 after 25 years "
        "(ratification pending), strained by Milei's free-market unilateralism."),
    "OECD": ("38 rich-democracy club: policy benchmarking, global minimum tax "
        "(Pillar 2), anti-bribery norms — the technocratic backbone of the "
        "liberal economic order."),
    "AES (Alliance of Sahel States)": ("Mali-Burkina-Niger junta confederation "
        "(2023-): left ECOWAS (Jan 2025), expelled French/US forces, hired "
        "Russia's Africa Corps, pooled a joint force against jihadists they are "
        "collectively losing to; anti-colonial legitimacy narrative with "
        "deteriorating security reality."),
    "ECOWAS": ("West African bloc (12 remaining members) wounded by the Sahel "
        "exodus: sanctions-then-retreat on Niger's coup exposed its limits; still "
        "the region's trade/mobility framework and democratic-norms enforcer of "
        "last resort."),
}

# ── non-state actor briefs ───────────────────────────────────────────────────
NSA_BRIEFS = {
    "Hamas": ("Palestinian Islamist movement (1987, Muslim Brotherhood offshoot): won "
        "2006 elections, seized Gaza 2007, built a rocket/tunnel army with Iranian "
        "support, launched the Oct 7 2023 attack. Its military wing is shattered but "
        "insurgent; 2025 ceasefire diplomacy centers on its disarmament vs survival "
        "as a political force. Designated terrorist by US/EU; leadership "
        "(Sinwar killed 2024) partly exiled in Qatar/Turkey."),
    "Hezbollah": ("Lebanese Shia 'Party of God' (1982, Iranian creation): state-within-"
        "a-state with ministers in parliament AND a missile army. 2024 war with "
        "Israel killed Nasrallah and gutted its arsenal/command; under the ceasefire "
        "it resists disarmament south of the Litani while Lebanon's new government, "
        "the US and Gulf press for a state weapons monopoly. Iran's crown-jewel "
        "proxy, now the weakest since the 1990s."),
    "Houthi Movement (Ansar Allah)": ("Zaydi-Shia revivalist movement from Saada "
        "that took Sanaa (2014) and survived the Saudi coalition: rules 70-80% of "
        "Yemenis, runs a missile/drone complex with Iranian designs, and turned the "
        "Red Sea into a leverage theater (2023- shipping attacks, US/Israeli "
        "strikes). Slogan politics ('Death to America/Israel'); taxes and "
        "child-recruits its zone; the Gaza war made it the 'Axis' most active node."),
    "Islamic State Sahel Province": ("ISIS's Sahara franchise (ex-ISGS, 2015): "
        "massacres across the Mali-Niger-Burkina tri-border (Tillabéri), fights "
        "BOTH states and rival JNIM, thrives on junta-era chaos and Wagner "
        "brutality backlash. Among the deadliest IS branches globally."),
    "JNIM (al-Qaeda in the Sahel)": ("Jama'at Nusrat al-Islam wal-Muslimin (2017 "
        "merger under Iyad Ag Ghaly): al-Qaeda's most successful franchise — "
        "city blockades (Bamako fuel siege 2025), kidnap economies, shadow "
        "governance across Mali/Burkina and spilling to the Gulf of Guinea "
        "littoral. Positions itself as 'moderate' vs ISSP while strangling "
        "states."),
    "M23 Movement": ("Tutsi-led Congolese rebellion (Mouvement du 23 mars, 2012; "
        "resurgent 2021) — per UN experts an instrument of Rwandan forces/interests: "
        "took Goma & Bukavu (2025), administers eastern Congo territory, taxes "
        "coltan. The core of the Congo-Rwanda war-and-peace process (Washington/"
        "Doha accords)."),
    "People's Defence Forces (Myanmar)": ("The armed wing of Myanmar's parallel "
        "National Unity Government (2021-): hundreds of local units, drone-heavy "
        "tactics, allied with veteran ethnic armies; controls swaths of Sagaing/"
        "Magway. The democratic resistance's military expression."),
    "Rapid Support Forces": ("Sudanese paramilitary heir to the Janjaweed under "
        "Hemedti: fights the army for the state (2023-), perpetrated Darfur "
        "ethnic massacres (El Fasher 2025; US genocide determination), funded by "
        "gold and Gulf networks, armed via Libya/Chad routes. Declared a rival "
        "'government' in territory it holds."),
}

UN_BRIEF = (
    "The United Nations (1945, 193 members): the world's universal forum — Security "
    "Council (P5 veto: US, Russia, China, UK, France) for peace/security, General "
    "Assembly (one state one vote), plus the humanitarian/development system (WFP, "
    "UNHCR, WHO, UNDP). Post-2022 reality: P5 deadlock (Russia vetoes on Ukraine, US "
    "on Gaza) shifted action to the Assembly's symbolic supermajorities and to "
    "coalitions outside the building; funding crises (US cuts 2025) hollow agencies; "
    "peacekeeping shrinks (Mali expelled, DRC drawdown). Still indispensable for "
    "legitimacy, aid logistics, and small-state voice; reform (Council expansion) "
    "perennially stalled. Secretary-General António Guterres (term ends 2026).")


# ── composer: knowledge for ANY entity ──────────────────────────────────────
def _regions_for(iso3, m49_subregion):
    """Map a country to the closest REGION_BRIEFS key."""
    if m49_subregion in REGION_BRIEFS:
        return m49_subregion
    m = {
        "Northern Europe": "Western Europe / EU core",
        "Southern Europe": "Western Europe / EU core",
        "Western Europe": "Western Europe / EU core",
        "Middle Africa": "Sub-Saharan Africa", "Western Africa": "Sub-Saharan Africa",
        "Eastern Africa": "Sub-Saharan Africa", "Southern Africa": "Sub-Saharan Africa",
        "South America": "Latin America and the Caribbean",
        "Central America": "Latin America and the Caribbean",
        "Caribbean": "Latin America and the Caribbean",
        "Melanesia": "Oceania", "Micronesia": "Oceania", "Polynesia": "Oceania",
        "Australia and New Zealand": "Oceania",
    }
    return m.get(m49_subregion or "", None)


def country_knowledge(iso3, profile=None):
    """Dossier for ANY country: curated brief if we have one, otherwise a solid
    composed paragraph from the structured data (stats, region, alignments) —
    so no panel is ever empty. `profile` is the country profile dict if the
    caller already has it (saves a query)."""
    brief = COUNTRY_BRIEFS.get(iso3)
    sub = ((profile or {}).get("m49_subregion") or (profile or {}).get("subregion")
           or (profile or {}).get("region"))
    rkey = _regions_for(iso3, sub)
    out = {"brief": brief, "region": rkey,
           "region_brief": REGION_BRIEFS.get(rkey), "curated": bool(brief)}
    if not brief and profile:
        bits = []
        name = profile.get("name") or iso3
        gt = profile.get("government_type")
        pop = profile.get("population")
        gdp = profile.get("gdp_usd")
        lang = profile.get("languages")
        rel = profile.get("religion")
        if gt:
            bits.append(f"{name} is a {gt}".rstrip(".") + ".")
        if pop:
            bits.append(f"Population ≈ {pop:,}.")
        if gdp:
            bits.append(f"GDP ≈ ${gdp/1e9:,.0f}B.")
        if lang:
            bits.append(f"Main languages: {lang}.")
        if rel:
            bits.append(f"Predominant religion: {rel}.")
        if sub:
            bits.append(f"Region: {sub} — see the regional brief below for the "
                        "geopolitical context it moves in.")
        out["brief"] = " ".join(bits) or None
    return out


def conflict_knowledge(name):
    return {"brief": CONFLICT_BRIEFS.get(name), "curated": name in CONFLICT_BRIEFS}


def alliance_knowledge(name):
    # tolerate name variants ("NATO" vs "North Atlantic Treaty Organization")
    if name in ALLIANCE_BRIEFS:
        return {"brief": ALLIANCE_BRIEFS[name], "curated": True}
    for k, v in ALLIANCE_BRIEFS.items():
        if k.lower() in (name or "").lower() or (name or "").lower() in k.lower():
            return {"brief": v, "curated": True}
    return {"brief": None, "curated": False}


def nsa_knowledge(name):
    return {"brief": NSA_BRIEFS.get(name), "curated": name in NSA_BRIEFS}


def context_pack(kind, key, profile=None):
    """Compact text block injected into analyst/LLM prompts as world-knowledge
    grounding for the entity the user is looking at."""
    if kind == "country":
        k = country_knowledge(key, profile)
        parts = [p for p in [k.get("brief"), k.get("region_brief")] if p]
        return ("WORLD KNOWLEDGE — " + (profile or {}).get("name", key) + ":\n"
                + "\n".join(parts)) if parts else ""
    if kind == "conflict":
        b = CONFLICT_BRIEFS.get(key)
        return f"WORLD KNOWLEDGE — {key}:\n{b}" if b else ""
    if kind == "alliance":
        b = alliance_knowledge(key).get("brief")
        return f"WORLD KNOWLEDGE — {key}:\n{b}" if b else ""
    if kind in ("non_state_actor", "nsa"):
        b = NSA_BRIEFS.get(key)
        return f"WORLD KNOWLEDGE — {key}:\n{b}" if b else ""
    if kind == "un":
        return "WORLD KNOWLEDGE — United Nations:\n" + UN_BRIEF
    return ""


# ── v7.2 — historical ERA dossiers: the deep understanding of HOW we got here,
# injected into the analyst as general grounding so it can place any current
# event in its seven-decade arc for a total newcomer. ────────────────────────
ERA_BRIEFS = {
    "postwar_order": (
        "THE POSTWAR ORDER (1945-1991). WWII left the US and USSR as rival "
        "superpowers and birthed the institutions that still run the world: the "
        "UN (1945), Bretton Woods (IMF/World Bank, dollar-gold standard), NATO "
        "(1949) and its Warsaw Pact mirror. The Cold War was a 45-year global "
        "contest — never direct war between the superpowers (mutually assured "
        "nuclear destruction) but fought through proxies (Korea, Vietnam, "
        "Afghanistan, Angola, Nicaragua), coups, and an arms/space race. In "
        "parallel, European empires dissolved: dozens of new states emerged "
        "across Asia and Africa (1947 India, 1960 'Year of Africa'), many "
        "becoming Cold War battlegrounds or Non-Aligned. The era ended when "
        "Soviet reform (Gorbachev's perestroika/glasnost) accelerated collapse: "
        "the Berlin Wall fell in 1989 and the USSR dissolved in 1991."),
    "unipolar_moment": (
        "THE UNIPOLAR MOMENT (1991-2008). With the USSR gone, the US was the "
        "sole superpower and liberal democracy/market capitalism seemed "
        "triumphant ('end of history'). Globalization surged: NAFTA, the WTO, "
        "China's WTO entry (2001) and its factory boom, the euro (1999/2002), "
        "and the internet. But new disorders emerged — Yugoslavia's wars and "
        "genocides (Bosnia, Rwanda 1994), the 1997 Asian financial crisis — and "
        "9/11 (2001) launched the US 'War on Terror': invasions of Afghanistan "
        "(2001) and Iraq (2003), the latter destabilizing the Middle East and "
        "empowering Iran. The moment ended with two shocks: Russia's 2008 "
        "Georgia war (a rebuff to NATO expansion) and the 2008 global financial "
        "crisis, which discredited the Western economic model for many."),
    "multipolar_disorder": (
        "MULTIPOLAR DISORDER (2008-present). Power diffused: China rose to "
        "challenge US primacy, Russia turned revisionist, and populism surged in "
        "the West after 2008. The Arab Spring (2011) toppled dictators but bred "
        "civil wars (Syria, Libya, Yemen) and ISIS. Russia annexed Crimea "
        "(2014) then launched Europe's largest war since 1945 (Ukraine, 2022). "
        "Brexit (2016) and Trump (2016, 2024) signaled a retreat from the "
        "liberal order; US-China rivalry over trade, chips and Taiwan became the "
        "organizing axis. COVID-19 (2020) shocked the globe; Hamas's Oct 7 2023 "
        "attack reignited the Middle East (Gaza war, Israel-Iran strikes, "
        "Assad's fall). The through-line: the US-led 'rules-based order' is "
        "contested, institutions are gridlocked, and the world is renegotiating "
        "who sets the rules."),
    "cold_war_flashpoints": (
        "COLD WAR FLASHPOINTS. Berlin (blockade 1948, Wall 1961) was the "
        "European frontier; Cuba (1962 Missile Crisis) the closest brush with "
        "nuclear war; Korea (1950-53) froze into today's DMZ; Vietnam (US combat "
        "1965-73) ended in American defeat; Afghanistan (Soviet 1979-89) "
        "bankrupted Moscow and incubated jihadism. Many current conflicts are "
        "Cold War residue: the Korean division, Taiwan's status, the "
        "Israeli-Arab wars, and the arms-control architecture now unraveling."),
    "decolonization": (
        "DECOLONIZATION (1945-1975). European empires — British, French, "
        "Portuguese, Dutch, Belgian — dissolved into ~80 new states. Some "
        "transitions were peaceful (Ghana 1957, India 1947 minus Partition's "
        "bloodshed); others were brutal wars (Algeria, Vietnam, Angola, Kenya). "
        "Borders drawn by colonizers without regard to peoples seeded lasting "
        "conflicts (Kashmir, the Sahel, the Congo, Sudan, the Middle East "
        "mandates). The Non-Aligned Movement (Bandung 1955) gave the new Global "
        "South a voice between the blocs — an ancestor of today's BRICS-era "
        "multi-alignment."),
    "economic_shocks": (
        "THE GREAT ECONOMIC SHOCKS. Nixon ended dollar-gold convertibility "
        "(1971), creating today's floating-currency world. The 1973 oil embargo "
        "and 1979 Iranian revolution caused stagflation and enshrined energy as "
        "geopolitics. Black Monday (1987), the Asian crisis (1997) and the "
        "dot-com bust (2000) were rehearsals for 2008's global financial crisis "
        "— the Lehman collapse, the Great Recession, bailouts, austerity, and "
        "the populist backlash that reshaped politics. COVID (2020) then "
        "triggered the largest state interventions in history and the inflation "
        "wave that defined the early 2020s."),
}


def era_context():
    """Compact multi-era grounding block for the analyst — the 'how we got
    here' spine, so any current event can be placed in its historical arc."""
    return ("HISTORICAL ERAS (deep background for placing current events):\n"
            + "\n\n".join(ERA_BRIEFS[k] for k in
                          ("postwar_order", "unipolar_moment",
                           "multipolar_disorder")))
