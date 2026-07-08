"""v7.4.2 — professional political-party DOSSIERS (owner: "add everything you'd
want to know about political parties … a full professional dossier on EVERYTHING
about them; seed it all, but write notes for later dynamic adaptation").

Each dossier is a structured, neutral profile: ideology, economic + social
position, EU stance (where relevant), current/former coalitions, past electoral
results, current leader + key officeholders, signature stances, and geopolitical
ramifications. Curated from the public record through early 2026.

DYNAMIC ADAPTATION NOTES (for a later pass):
  * These are the OFFLINE FLOOR. The existing AI path (routes_v4._party_synthesis
    / PARTY_PROFILE_PROMPT) still runs and should be MERGED OVER this floor when a
    provider is up, exactly like leader profiles (leaders_detail) do.
  * Election results, leaders and coalition membership go stale — the §30
    web-search accuracy pipeline (processing/accuracy.py) is the natural place to
    refresh `leader`, `electoral` and `coalitions` on a cadence; add a
    party-verification job mirroring refresh_stale_leadership().
  * Keyed by the EXACT party name used in country_extra.LEGISLATURES so the
    seat-arc chips resolve directly; `dossier_for()` also tries a loose match.
"""

# name -> dossier dict. Fields are all optional; the renderer shows what's present.
PARTY_DOSSIERS = {
    # ---------------- United States ----------------
    "Democratic": {
        "country": "USA", "full_name": "Democratic Party", "ideology": "Center-left / liberal",
        "economic_position": "Mixed economy with an active state: social insurance, progressive "
            "taxation, labor protections, climate investment (Inflation Reduction Act).",
        "social_position": "Socially liberal — abortion rights, LGBTQ+ rights, voting access, "
            "immigration reform, gun regulation.",
        "coalitions": "Big-tent coalition of urban professionals, minorities, unions, youth and "
            "college-educated suburbanites.",
        "electoral": "Won the presidency 2020 (Biden); lost it 2024 to Trump; competitive House/"
            "Senate margins throughout the 2020s.",
        "leader": "Leadership is diffuse post-2024; congressional leaders Hakeem Jeffries (House) "
            "and Chuck Schumer (Senate).",
        "stances": ["Abortion rights (post-Dobbs restoration)", "Climate action & clean energy",
            "Expanded health coverage (ACA)", "Union and labor rights", "Ukraine aid",
            "Gun-safety legislation"],
        "geopolitical": "Alliance-first foreign policy: NATO, Ukraine support, Indo-Pacific "
            "coalitions, re-engagement with multilateral climate/health institutions.",
    },
    "Republican": {
        "country": "USA", "full_name": "Republican Party (GOP)", "ideology": "Center-right to "
            "right; increasingly national-populist under Trump (MAGA).",
        "economic_position": "Tax cuts, deregulation, tariffs and protectionism under Trump, "
            "spending restraint on social programs, energy production.",
        "social_position": "Socially conservative — abortion restriction, gun rights, tighter "
            "immigration and border enforcement, skepticism of DEI.",
        "coalitions": "Working-class and rural whites, evangelicals, business conservatives, and "
            "a growing share of non-college and some minority voters.",
        "electoral": "Won the presidency 2024 (Trump) with Senate control and the House; realigned "
            "toward populism since 2016.",
        "leader": "Donald Trump (de facto leader / 47th President).",
        "stances": ["Border security & reduced immigration", "Tariffs / 'America First' trade",
            "Tax cuts & deregulation", "Gun rights", "Abortion restriction (states)",
            "Skepticism of open-ended foreign aid"],
        "geopolitical": "'America First': transactional alliances, pressure on allies to spend, "
            "tariffs on rivals and partners alike, harder line on China, wary of open-ended Ukraine aid.",
    },
    # ---------------- United Kingdom ----------------
    "Labour": {
        "country": "GBR", "full_name": "Labour Party", "ideology": "Center-left; social democratic",
        "economic_position": "Pro-growth center-left under Starmer: fiscal discipline, public-"
            "service investment, workers' rights, GB Energy public power company.",
        "social_position": "Socially liberal, internationalist; tough-on-crime framing.",
        "eu_stance": "Pro-European but not seeking to rejoin the EU/single market; closer alignment.",
        "coalitions": "Governs with a large single-party majority (no coalition).",
        "electoral": "Landslide 2024 general-election win (411 seats), ending 14 years of "
            "Conservative government.",
        "leader": "Keir Starmer (Prime Minister since July 2024).",
        "stances": ["NHS investment", "Workers' rights (New Deal for Working People)",
            "Clean-energy transition (GB Energy)", "Closer UK-EU ties", "Ukraine support"],
        "geopolitical": "Atlanticist and pro-NATO; steadfast Ukraine backing; seeks a reset with "
            "the EU while keeping the US alliance central.",
    },
    "Conservative": {
        "country": "GBR", "full_name": "Conservative and Unionist Party (Tories)",
        "ideology": "Center-right; conservative", "economic_position": "Free-market, lower-tax, "
            "fiscally conservative; business-friendly.",
        "social_position": "Traditionalist-leaning; tough on immigration and crime.",
        "eu_stance": "Delivered Brexit (2016-2020); Eurosceptic.",
        "coalitions": "In opposition since 2024 after a historic defeat.",
        "electoral": "Reduced to 121 seats in 2024, their worst result ever, after the Johnson/"
            "Truss/Sunak years.", "leader": "Kemi Badenoch (Leader of the Opposition since Nov 2024).",
        "stances": ["Lower taxes & deregulation", "Immigration control", "Brexit defence",
            "Strong defence spending"],
        "geopolitical": "Atlanticist, pro-NATO, Ukraine-supporting; post-Brexit 'Global Britain' "
            "trade posture.",
    },
    "Liberal Democrats": {
        "country": "GBR", "full_name": "Liberal Democrats", "ideology": "Centre / liberal",
        "economic_position": "Market economy with strong public services and environmental focus.",
        "social_position": "Socially liberal, strongly pro-civil-liberties.",
        "eu_stance": "The most pro-EU major party; favours rejoining the single market.",
        "coalitions": "Governed in coalition with the Conservatives 2010-2015; now the third party.",
        "electoral": "Surged to 72 seats in 2024, their best modern result.",
        "leader": "Ed Davey.", "stances": ["Rejoin EU single market", "NHS & social care",
            "Electoral reform (PR)", "Environment"],
        "geopolitical": "Pro-EU, pro-NATO, internationalist.",
    },
    "Reform UK": {
        "country": "GBR", "full_name": "Reform UK", "ideology": "Right-wing populist / national-conservative",
        "economic_position": "Low-tax, anti-net-zero, deregulation, cut immigration to cut public "
            "spending pressure.",
        "social_position": "Socially conservative; anti-mass-immigration is the core issue.",
        "eu_stance": "Hard-Eurosceptic (successor to the Brexit Party / UKIP tradition).",
        "coalitions": "No coalitions; an insurgent challenger party.",
        "electoral": "Won 5 seats in 2024 but ~14% of the vote, and has led some 2025 polls.",
        "leader": "Nigel Farage.", "stances": ["Sharp immigration cuts", "Scrap net-zero targets",
            "Lower taxes", "Anti-establishment reform"],
        "geopolitical": "Sovereigntist, Eurosceptic; ambivalent on Ukraine aid; close to the "
            "US national-populist right.",
    },
    "SNP": {
        "country": "GBR", "full_name": "Scottish National Party", "ideology": "Centre-left; "
            "Scottish independence / social democratic",
        "economic_position": "Social-democratic, pro-public-services.", "social_position": "Socially liberal.",
        "eu_stance": "Strongly pro-EU; wants an independent Scotland to rejoin.",
        "coalitions": "Governs the Scottish Parliament; had a Bute House deal with the Scottish Greens.",
        "electoral": "Fell to 9 Westminster seats in 2024 after long dominance.",
        "leader": "John Swinney (Scottish First Minister).",
        "stances": ["Scottish independence", "Rejoin the EU", "Social democracy"],
        "geopolitical": "Pro-EU, anti-Trident (nuclear), internationalist.",
    },
    # ---------------- Germany ----------------
    "CDU/CSU": {
        "country": "DEU", "full_name": "Christian Democratic Union / Christian Social Union",
        "ideology": "Centre-right; Christian democratic / conservative",
        "economic_position": "Social market economy, fiscal discipline (debt brake), business-friendly.",
        "social_position": "Moderately conservative; the CSU (Bavaria) is more so.",
        "eu_stance": "Firmly pro-EU and pro-integration (the party of Adenauer, Kohl, Merkel).",
        "coalitions": "Historically governs in 'grand coalitions' with the SPD; led by Merkel 2005-21.",
        "electoral": "Won the Feb 2025 federal election; Friedrich Merz became Chancellor.",
        "leader": "Friedrich Merz (Chancellor / CDU leader).",
        "stances": ["Fiscal discipline", "Stronger migration control", "Pro-EU & pro-NATO",
            "Support for Ukraine", "Competitive industry / energy"],
        "geopolitical": "Anchor of the pro-EU, pro-NATO, transatlantic mainstream; strong Ukraine backing.",
    },
    "SPD": {
        "country": "DEU", "full_name": "Social Democratic Party of Germany", "ideology": "Centre-left; "
            "social democratic", "economic_position": "Social market with a stronger welfare state, "
            "minimum wage, labor protections.", "social_position": "Socially progressive.",
        "eu_stance": "Strongly pro-EU.", "coalitions": "Led the 2021-25 'traffic-light' coalition "
            "(with Greens + FDP) under Scholz; now a junior partner / opposition.",
        "electoral": "Fell to a historic low in Feb 2025 after leading the previous government.",
        "leader": "Lars Klingbeil (co-leader).", "stances": ["Welfare state & pensions",
            "Minimum wage", "Pro-EU", "Ukraine support (with caution on escalation)"],
        "geopolitical": "Pro-EU, pro-NATO; historically Ostpolitik-inflected caution toward Russia.",
    },
    "AfD": {
        "country": "DEU", "full_name": "Alternative for Germany", "ideology": "Right-wing populist / "
            "far-right nationalist", "economic_position": "Economically liberal to protectionist; "
            "anti-carbon-tax, anti-EU-transfers.", "social_position": "Nationalist, anti-immigration, "
            "socially conservative; parts monitored by domestic intelligence as extremist.",
        "eu_stance": "Hard-Eurosceptic; has flirted with 'Dexit'.",
        "coalitions": "Shunned by all others under a 'firewall' (Brandmauer) — no coalitions.",
        "electoral": "Came SECOND in the Feb 2025 federal election (~20%), its best-ever result.",
        "leader": "Alice Weidel (co-leader).", "stances": ["Sharp immigration restriction",
            "Anti-EU / sovereigntist", "Anti-green-transition", "Rapprochement with Russia"],
        "geopolitical": "Sovereigntist and Eurosceptic; sympathetic to Moscow, opposed to Ukraine "
            "arms — a sharp break with the German mainstream.",
    },
    "Greens": {
        "country": "DEU", "full_name": "Alliance 90/The Greens", "ideology": "Green politics; "
            "progressive / centre-left", "economic_position": "Eco-social market, aggressive "
            "climate transition, green industry.", "social_position": "Progressive, pro-immigration, "
            "pro-civil-rights.", "eu_stance": "Strongly pro-EU and federalist.",
        "coalitions": "Junior partner in the 2021-25 traffic-light coalition.",
        "electoral": "~12% in Feb 2025.", "leader": "Franziska Brantner / Felix Banaszak (co-leaders).",
        "stances": ["Climate neutrality", "Renewables & coal phase-out", "Pro-EU",
            "Robust Ukraine support (a hawkish shift for a green party)", "Human rights in foreign policy"],
        "geopolitical": "Value-based, pro-EU, notably firm on Ukraine and critical of China/Russia.",
    },
    "The Left": {
        "country": "DEU", "full_name": "The Left (Die Linke)", "ideology": "Left-wing / democratic socialist",
        "economic_position": "Strong welfare state, wealth taxes, nationalization, anti-austerity.",
        "social_position": "Progressive, pro-immigration.", "eu_stance": "EU-critical from the left "
            "(reform, not exit).", "coalitions": "Occasional state-level coalitions with SPD/Greens.",
        "electoral": "Rebounded past the 5% threshold in Feb 2025 after the Wagenknecht split (BSW).",
        "leader": "Ines Schwerdtner / Jan van Aken (co-leaders).",
        "stances": ["Wealth redistribution", "Rent controls", "Anti-militarism / skeptical of arms to Ukraine",
            "Peace-oriented foreign policy"],
        "geopolitical": "Pacifist-leaning, skeptical of NATO and arms transfers.",
    },
    # ---------------- France ----------------
    "National Rally + allies": {
        "country": "FRA", "full_name": "National Rally (Rassemblement National)",
        "ideology": "Right-wing populist / national-conservative", "economic_position": "Economic "
            "nationalism, welfare chauvinism (generous for citizens), protectionism.",
        "social_position": "Anti-immigration, nationalist, secularist-nativist.",
        "eu_stance": "Eurosceptic and sovereigntist (no longer seeking 'Frexit' but wants to gut EU powers).",
        "coalitions": "Long shunned by a 'republican front'; now the largest single party bloc.",
        "electoral": "Won the most seats of any single party in the 2024 snap election before the "
            "left/centre blocked it from a majority.", "leader": "Jordan Bardella (president); "
            "Marine Le Pen (parliamentary leader).",
        "stances": ["Sharp immigration cuts", "Sovereigntism vs Brussels", "Purchasing power / welfare",
            "Law and order"],
        "geopolitical": "Sovereigntist, historically Moscow-friendly, wary of NATO integration and EU "
            "enlargement.",
    },
    "Ensemble (centre)": {
        "country": "FRA", "full_name": "Ensemble (Macron's centrist coalition, incl. Renaissance)",
        "ideology": "Centre / liberal", "economic_position": "Pro-market, pro-business reform "
            "(pension reform, labor flexibility), fiscal consolidation.", "social_position": "Socially "
            "liberal, centrist.", "eu_stance": "Strongly pro-EU and federalist (the pro-integration pole).",
        "coalitions": "Governed 2017-2024; now leads a fragile minority/technical arrangement after 2024.",
        "electoral": "Lost its majority in the 2024 snap election, forcing cohabitation-style bargaining.",
        "leader": "Emmanuel Macron (President); Gabriel Attal (party).",
        "stances": ["Pro-EU integration", "Market reform", "Strategic autonomy for Europe",
            "Ukraine support"], "geopolitical": "Pro-EU, pro-NATO, champion of European 'strategic autonomy'.",
    },
    "New Popular Front (left)": {
        "country": "FRA", "full_name": "New Popular Front (NFP — LFI, PS, Greens, Communists)",
        "ideology": "Left-wing alliance (from social-democratic to left-populist)",
        "economic_position": "Anti-austerity, wealth taxes, minimum-wage and pension boosts, price controls.",
        "social_position": "Progressive, pro-immigration, ecological.", "eu_stance": "Mixed — PS/Greens "
            "pro-EU, LFI EU-critical from the left.", "coalitions": "An electoral alliance formed to "
            "block the far right in 2024.", "electoral": "Won the most seats in the 2024 snap election "
            "but short of a majority.", "leader": "No single leader; Jean-Luc Mélenchon (LFI) is the "
            "most prominent figure.", "stances": ["Repeal pension reform", "Wealth redistribution",
            "Ecological planning", "Public services"],
        "geopolitical": "Divided: pro-EU social democrats vs a sovereigntist, NATO-skeptic left populism.",
    },
    "The Republicans": {
        "country": "FRA", "full_name": "The Republicans (Les Républicains)", "ideology": "Centre-right; "
            "Gaullist conservative", "economic_position": "Free-market, lower-tax, fiscally conservative.",
        "social_position": "Conservative, tough on immigration and security.",
        "eu_stance": "Pro-EU but sovereignty-minded.", "coalitions": "Split in 2024 over whether to ally "
            "with the National Rally.", "electoral": "Much diminished from its Gaullist heyday.",
        "leader": "Bruno Retailleau / Laurent Wauquiez (factions).",
        "stances": ["Lower taxes", "Immigration control", "Law and order", "Pro-business"],
        "geopolitical": "Atlanticist and pro-EU centre-right.",
    },
    # ---------------- Italy ----------------
    "Brothers of Italy": {
        "country": "ITA", "full_name": "Brothers of Italy (Fratelli d'Italia)", "ideology": "Right-wing "
            "/ national-conservative (post-fascist roots)", "economic_position": "Conservative, "
            "pro-business, welfare for families, moderate on EU fiscal rules in office.",
        "social_position": "Socially conservative, nationalist, tough on immigration.",
        "eu_stance": "Once Eurosceptic, now pragmatically pro-EU/Atlanticist in government.",
        "coalitions": "Leads a right-wing coalition with Lega and Forza Italia since 2022.",
        "electoral": "Won the 2022 election; Meloni became Italy's first woman PM.",
        "leader": "Giorgia Meloni (Prime Minister).",
        "stances": ["Immigration control", "Family & natalist policy", "Atlanticism / Ukraine support",
            "Pragmatic EU engagement"], "geopolitical": "Firmly pro-NATO and pro-Ukraine, constructive "
            "with Brussels — more moderate in office than its rhetoric.",
    },
    "Democratic Party": {
        "country": "ITA", "full_name": "Democratic Party (Partito Democratico)", "ideology": "Centre-left; "
            "social democratic", "economic_position": "Social-market, pro-EU fiscal engagement, labor "
            "protections.", "social_position": "Progressive.", "eu_stance": "Strongly pro-EU.",
        "coalitions": "Main opposition; seeks a 'broad field' with the Five Star Movement.",
        "electoral": "Lost 2022; in opposition.", "leader": "Elly Schlein.",
        "stances": ["Minimum wage", "Civil rights", "Pro-EU", "Ukraine support"],
        "geopolitical": "Pro-EU, pro-NATO, Atlanticist centre-left.",
    },
    "Five Star Movement": {
        "country": "ITA", "full_name": "Five Star Movement (Movimento 5 Stelle)", "ideology": "Big-tent "
            "populist, now centre-left / left-leaning", "economic_position": "Welfare (citizens' income), "
            "anti-corruption, environmentalism.", "social_position": "Mixed; increasingly progressive.",
        "eu_stance": "Formerly Eurosceptic, now moderated.", "coalitions": "Has governed with both right "
            "and left; now leans toward a centre-left field.", "electoral": "Peaked in 2018; reduced but "
            "significant.", "leader": "Giuseppe Conte.", "stances": ["Citizens' income / welfare",
            "Anti-corruption", "Environment", "Skeptical of arms to Ukraine"],
        "geopolitical": "Peace-oriented, more skeptical of NATO arms transfers than the mainstream.",
    },
    "Lega": {
        "country": "ITA", "full_name": "Lega (League)", "ideology": "Right-wing populist / regionalist",
        "economic_position": "Flat-tax advocacy, small-business focus, once northern-autonomist.",
        "social_position": "Anti-immigration, nationalist.", "eu_stance": "Eurosceptic and "
            "Russia-sympathetic wing within the governing coalition.",
        "coalitions": "Junior partner in Meloni's coalition.", "electoral": "Declined from its 2019 peak.",
        "leader": "Matteo Salvini (Deputy PM).", "stances": ["Immigration control", "Flat tax",
            "Autonomy for northern regions", "EU-skeptic"], "geopolitical": "The coalition's most "
            "Eurosceptic and historically Moscow-friendly voice.",
    },
    "Forza Italia": {
        "country": "ITA", "full_name": "Forza Italia", "ideology": "Centre-right; liberal-conservative",
        "economic_position": "Pro-business, liberal, lower-tax.", "social_position": "Moderate conservative.",
        "eu_stance": "Firmly pro-EU and pro-NATO (the coalition's Atlanticist anchor).",
        "coalitions": "Junior partner in Meloni's coalition.", "electoral": "Steady mid-single-digits.",
        "leader": "Antonio Tajani (Foreign Minister).", "stances": ["Pro-business", "Pro-EU / pro-NATO",
            "Moderate immigration policy"], "geopolitical": "The EPP-aligned, staunchly pro-Western pole "
            "of the Italian right.",
    },
    # ---------------- Spain ----------------
    "PSOE": {
        "country": "ESP", "full_name": "Spanish Socialist Workers' Party", "ideology": "Centre-left; "
            "social democratic", "economic_position": "Social-market, welfare expansion, labor reform.",
        "social_position": "Progressive.", "eu_stance": "Strongly pro-EU.",
        "coalitions": "Leads a left minority government with Sumar and regional-nationalist support.",
        "electoral": "Held power after 2023 via a complex investiture deal.", "leader": "Pedro Sánchez (PM).",
        "stances": ["Welfare & labor rights", "Catalan amnesty / dialogue", "Pro-EU", "Ukraine support"],
        "geopolitical": "Pro-EU, pro-NATO.",
    },
    "PP": {
        "country": "ESP", "full_name": "People's Party (Partido Popular)", "ideology": "Centre-right; "
            "conservative / Christian-democratic", "economic_position": "Free-market, lower-tax, fiscal "
            "discipline.", "social_position": "Moderately conservative.", "eu_stance": "Firmly pro-EU (EPP).",
        "coalitions": "Main opposition; governs some regions with Vox support.",
        "electoral": "Won the most seats in 2023 but could not form a government.", "leader": "Alberto Núñez Feijóo.",
        "stances": ["Lower taxes", "Territorial unity (anti-secession)", "Pro-EU"],
        "geopolitical": "Pro-EU, pro-NATO, Atlanticist.",
    },
    "Vox": {
        "country": "ESP", "full_name": "Vox", "ideology": "Right-wing populist / national-conservative",
        "economic_position": "Economically liberal, anti-regionalism.", "social_position": "Nationalist, "
            "socially conservative, anti-immigration.", "eu_stance": "Eurosceptic / sovereigntist.",
        "coalitions": "Supports/joins some PP regional governments.", "electoral": "Third force nationally.",
        "leader": "Santiago Abascal.", "stances": ["Spanish unity (abolish regional autonomy)",
            "Immigration control", "Anti-'globalism'"], "geopolitical": "Sovereigntist, part of Europe's "
            "national-conservative bloc.",
    },
    "Sumar": {
        "country": "ESP", "full_name": "Sumar", "ideology": "Left-wing / eco-socialist alliance",
        "economic_position": "Anti-austerity, welfare, labor rights, green transition.",
        "social_position": "Progressive.", "eu_stance": "EU-reformist.", "coalitions": "Junior partner "
            "in the PSOE-led government.", "electoral": "Formed 2023 as a broad left platform.",
        "leader": "Yolanda Díaz.", "stances": ["Labor rights", "Housing", "Green transition", "Feminism"],
        "geopolitical": "Left-internationalist, more critical of NATO/arms than PSOE.",
    },
    # ---------------- India ----------------
    "BJP": {
        "country": "IND", "full_name": "Bharatiya Janata Party", "ideology": "Right-wing; Hindu "
            "nationalist (Hindutva) / national-conservative", "economic_position": "Pro-market reform, "
            "infrastructure, welfare delivery, economic nationalism (Make in India).",
        "social_position": "Hindu-nationalist, culturally conservative.", "coalitions": "Leads the "
            "National Democratic Alliance (NDA).", "electoral": "Won a third term in 2024 but lost its "
            "single-party majority, now reliant on NDA allies.", "leader": "Narendra Modi (Prime Minister).",
        "stances": ["Hindutva / cultural nationalism", "Infrastructure & digital economy",
            "Muscular national security", "Welfare delivery"], "geopolitical": "Non-aligned "
            "'multi-alignment': Quad partner with the US/Japan/Australia, strategic autonomy, energy "
            "ties with Russia, rivalry with China and Pakistan.",
    },
    "INC": {
        "country": "IND", "full_name": "Indian National Congress", "ideology": "Centre to centre-left; "
            "social-liberal / secular", "economic_position": "Welfare, social justice, mixed economy.",
        "social_position": "Secular, pluralist.", "coalitions": "Leads the INDIA opposition bloc.",
        "electoral": "Recovered strongly in 2024, nearly doubling its seats.", "leader": "Mallikarjun Kharge "
            "(president); Rahul Gandhi (Leader of the Opposition).", "stances": ["Secularism & pluralism",
            "Welfare / social justice", "Federalism", "Institutional checks"],
        "geopolitical": "Non-aligned tradition; broadly continuity on strategic autonomy.",
    },
}

# loose alias map so common short/alt names resolve to a dossier key
_ALIASES = {
    "democrats": "Democratic", "democratic party (us)": "Democratic",
    "republicans": "Republican", "gop": "Republican", "tories": "Conservative",
    "conservatives": "Conservative", "lib dems": "Liberal Democrats",
    "reform": "Reform UK", "cdu": "CDU/CSU", "csu": "CDU/CSU", "die linke": "The Left",
    "national rally": "National Rally + allies", "rassemblement national": "National Rally + allies",
    "renaissance": "Ensemble (centre)", "ensemble": "Ensemble (centre)",
    "fratelli d'italia": "Brothers of Italy", "pd": "Democratic Party",
    "m5s": "Five Star Movement", "league": "Lega", "partido popular": "PP",
    "bharatiya janata party": "BJP", "indian national congress": "INC", "congress": "INC",
}


def dossier_for(name, country_iso3=None):
    """Return the curated dossier for a party name, else a structured FLOOR so
    every party page shows something. `country_iso3` is used only for the floor."""
    if not name:
        return None
    key = name.strip()
    if key in PARTY_DOSSIERS:
        return {**PARTY_DOSSIERS[key], "curated": True, "name": key}
    al = _ALIASES.get(key.lower())
    if al and al in PARTY_DOSSIERS:
        return {**PARTY_DOSSIERS[al], "curated": True, "name": al}
    # floor: a real, if thin, dossier scaffold (AI synthesis merges over this)
    return {"name": key, "country": country_iso3, "curated": False,
            "ideology": None,
            "note": "A detailed dossier for this party has not been curated yet; "
                    "the AI profile (when a provider is configured) fills it in, "
                    "and a future data pass will seed it fully."}
