"""v7.2 — DEEP HISTORICAL BACKFILL (1945 → present).

An extreme-depth curated timeline of the landmark events that made the modern
world, seeded ONCE into the permanent fact chain (offline, dated in the past,
attributed to the historical archive). This gives correlation, story threads,
the counterfactual engine's historical-analogue search, and the analyst a
seven-decade spine of ground truth to reason from — so "GlobeGrid knows the
whole world" is backed by the actual record, not just the last news cycle.

Each row: (date, title, summary, category, lat, lon, place, severity).
Categories reuse the live taxonomy (conflict/military/diplomacy/geopolitics/
disaster/finance/technology). Seeded via `raw_items.external_id = "deep:..."`
so it is idempotent and never double-inserts.
"""

# (date, title, summary, category, lat, lon, place, severity)
DEEP_HISTORY = [
    # ── 1945–1949: the postwar order is built ───────────────────────────────
    ("1945-05-08", "Victory in Europe: Nazi Germany surrenders",
     "The Third Reich's unconditional surrender ended WWII in Europe, leaving a "
     "devastated continent to be divided between Western and Soviet spheres.",
     "conflict", 52.52, 13.40, "Berlin", 5),
    ("1945-08-06", "Atomic bomb destroys Hiroshima",
     "The first wartime use of a nuclear weapon killed ~140,000; Nagasaki "
     "followed on Aug 9, opening the atomic age and forcing Japan's surrender.",
     "military", 34.39, 132.45, "Hiroshima", 5),
    ("1945-10-24", "United Nations founded",
     "51 states ratified the UN Charter, creating the Security Council, General "
     "Assembly and the postwar system of collective security and diplomacy.",
     "diplomacy", 40.75, -73.97, "New York", 4),
    ("1947-08-15", "Partition of India creates India and Pakistan",
     "British India split into two states; up to 2 million died and ~15 million "
     "were displaced in one of history's largest migrations, seeding the Kashmir "
     "conflict.", "geopolitics", 28.61, 77.21, "New Delhi", 5),
    ("1948-05-14", "State of Israel declared; first Arab-Israeli war",
     "Israel's independence and the surrounding war produced the Palestinian "
     "Nakba and the century-defining Israeli-Palestinian conflict.",
     "conflict", 32.08, 34.78, "Tel Aviv", 5),
    ("1948-06-24", "Berlin Blockade and Airlift begin",
     "The USSR cut off West Berlin; a Western airlift sustained the city for "
     "nearly a year — the first great Cold War confrontation.",
     "geopolitics", 52.52, 13.40, "Berlin", 4),
    ("1949-04-04", "NATO founded",
     "Twelve Western states signed the North Atlantic Treaty, binding North "
     "America and Western Europe in collective defense against the USSR.",
     "diplomacy", 38.90, -77.04, "Washington", 4),
    ("1949-10-01", "Mao proclaims the People's Republic of China",
     "Communist victory in the civil war founded the PRC; the Nationalists fled "
     "to Taiwan, setting up the cross-strait division that endures today.",
     "geopolitics", 39.90, 116.40, "Beijing", 5),
    ("1949-08-29", "Soviet Union tests its first atomic bomb",
     "The USSR broke the US nuclear monopoly, launching the arms race that "
     "defined the Cold War's balance of terror.",
     "military", 50.07, 78.43, "Semipalatinsk", 4),
    # ── 1950s: Cold War hardens, decolonization begins ──────────────────────
    ("1950-06-25", "Korean War begins",
     "North Korea's invasion of the South drew in the US-led UN and China; the "
     "1953 armistice froze a still-unresolved division at the 38th parallel.",
     "conflict", 37.57, 126.98, "Seoul", 5),
    ("1953-03-05", "Death of Stalin",
     "The Soviet dictator's death opened a succession struggle won by Khrushchev, "
     "whose 'secret speech' (1956) began de-Stalinization.",
     "geopolitics", 55.75, 37.62, "Moscow", 4),
    ("1954-05-07", "French defeat at Dien Bien Phu",
     "Viet Minh victory ended French Indochina and split Vietnam at the 17th "
     "parallel, setting the stage for American involvement.",
     "conflict", 21.39, 103.02, "Dien Bien Phu", 4),
    ("1955-04-18", "Bandung Conference launches Non-Aligned Movement",
     "29 Asian and African states charted a path independent of both Cold War "
     "blocs, giving the decolonizing Global South a collective voice.",
     "diplomacy", -6.91, 107.61, "Bandung", 3),
    ("1956-10-29", "Suez Crisis",
     "Britain, France and Israel attacked Egypt after Nasser nationalized the "
     "canal; US and Soviet pressure forced withdrawal, marking the end of "
     "European imperial dominance.", "conflict", 30.05, 32.55, "Suez", 4),
    ("1956-11-04", "Soviets crush the Hungarian Revolution",
     "Red Army tanks ended Hungary's anti-communist uprising, killing thousands "
     "and showing the limits of the Soviet bloc.",
     "conflict", 47.50, 19.04, "Budapest", 4),
    ("1957-10-04", "Sputnik launches the Space Age",
     "The first artificial satellite stunned the West and opened the space race, "
     "which peaked with the Moon landing.",
     "technology", 45.92, 63.34, "Baikonur", 4),
    ("1957-03-25", "Treaty of Rome creates the European Economic Community",
     "Six nations began the economic integration that became the European Union, "
     "binding former enemies France and Germany.",
     "diplomacy", 41.90, 12.50, "Rome", 3),
    ("1959-01-01", "Cuban Revolution: Castro takes power",
     "Fidel Castro's victory produced a communist state 90 miles from Florida, a "
     "Cold War flashpoint for six decades.",
     "geopolitics", 23.11, -82.37, "Havana", 4),
    # ── 1960s: peak Cold War, African independence, upheaval ────────────────
    ("1960-06-30", "Year of Africa: wave of independence",
     "Seventeen African nations gained independence in 1960 alone as the colonial "
     "empires unwound, redrawing the political map of a continent.",
     "geopolitics", 4.06, 9.79, "Sub-Saharan Africa", 4),
    ("1961-08-13", "Berlin Wall erected",
     "East Germany sealed off West Berlin to stop the exodus westward; the Wall "
     "became the Cold War's defining symbol for 28 years.",
     "geopolitics", 52.52, 13.40, "Berlin", 4),
    ("1962-10-16", "Cuban Missile Crisis",
     "The discovery of Soviet nuclear missiles in Cuba brought the world closer "
     "to nuclear war than ever before; a 13-day standoff ended in withdrawal and "
     "a hotline.", "military", 23.11, -82.37, "Havana", 5),
    ("1963-11-22", "Assassination of John F. Kennedy",
     "The US president's killing in Dallas traumatized America and remains its "
     "most scrutinized political murder.",
     "geopolitics", 32.78, -96.80, "Dallas", 4),
    ("1965-03-08", "US combat troops land in Vietnam",
     "American escalation turned Vietnam into a decade-long war that killed "
     "millions, split US society and ended in defeat.",
     "conflict", 16.05, 108.22, "Da Nang", 5),
    ("1967-06-05", "Six-Day War reshapes the Middle East",
     "Israel's lightning victory over Egypt, Jordan and Syria seized the West "
     "Bank, Gaza, Sinai and Golan — the occupation still central today.",
     "conflict", 31.78, 35.22, "Jerusalem", 5),
    ("1968-08-20", "Warsaw Pact crushes the Prague Spring",
     "Soviet-led forces ended Czechoslovakia's liberal reforms, entrenching the "
     "'Brezhnev Doctrine' of limited sovereignty in the bloc.",
     "conflict", 50.09, 14.42, "Prague", 4),
    ("1969-07-20", "Apollo 11: humans land on the Moon",
     "The US won the space race as Armstrong and Aldrin walked on the Moon, a "
     "landmark of the 20th century and the Cold War.",
     "technology", 0.67, 23.47, "Sea of Tranquility", 4),
    ("1967-07-06", "Nigerian Civil War (Biafra) begins",
     "The Biafran secession war killed ~1-3 million, largely by famine, and "
     "became a defining postcolonial African tragedy.",
     "conflict", 6.45, 7.51, "Enugu", 4),
    # ── 1970s: détente, oil shocks, revolutions ─────────────────────────────
    ("1971-12-16", "Bangladesh Liberation War; India-Pakistan war",
     "East Pakistan won independence as Bangladesh after genocide and Indian "
     "intervention, permanently altering South Asia's balance.",
     "conflict", 23.81, 90.41, "Dhaka", 4),
    ("1972-02-21", "Nixon goes to China",
     "The US president's visit to Mao reopened relations after 25 years, "
     "realigning the Cold War against the USSR.",
     "diplomacy", 39.90, 116.40, "Beijing", 4),
    ("1973-10-06", "Yom Kippur War and the oil embargo",
     "Egypt and Syria's surprise attack on Israel triggered an Arab oil embargo "
     "that quadrupled prices and reshaped the global economy.",
     "conflict", 30.05, 32.55, "Suez", 5),
    ("1974-08-09", "Watergate: Nixon resigns",
     "The only US presidential resignation, over a cover-up, reshaped American "
     "trust in government.", "geopolitics", 38.90, -77.04, "Washington", 3),
    ("1975-04-30", "Fall of Saigon ends the Vietnam War",
     "North Vietnamese tanks entered Saigon, unifying Vietnam under communism "
     "and cementing America's first major military defeat.",
     "conflict", 10.82, 106.63, "Saigon", 5),
    ("1975-04-17", "Khmer Rouge take Cambodia; genocide begins",
     "Pol Pot's regime emptied the cities and killed ~1.7 million in the "
     "20th century's most extreme social experiment.",
     "conflict", 11.56, 104.92, "Phnom Penh", 5),
    ("1978-09-17", "Camp David Accords",
     "US-brokered peace between Egypt and Israel — the first Arab recognition of "
     "Israel — reset Middle East diplomacy.",
     "diplomacy", 39.65, -77.47, "Camp David", 4),
    ("1979-02-11", "Iranian Revolution topples the Shah",
     "Ayatollah Khomeini's Islamic Republic overthrew a US ally, birthing the "
     "Iran-US enmity and Shia revolutionary politics that persist.",
     "geopolitics", 35.69, 51.39, "Tehran", 5),
    ("1979-12-24", "Soviet invasion of Afghanistan",
     "The USSR's decade-long war fueled a US-backed mujahideen insurgency, "
     "bankrupted Moscow and incubated global jihadism.",
     "conflict", 34.53, 69.17, "Kabul", 5),
    ("1978-12-18", "Deng Xiaoping launches China's 'reform and opening'",
     "Market reforms began China's transformation into an economic superpower, "
     "lifting hundreds of millions out of poverty.",
     "finance", 39.90, 116.40, "Beijing", 4),
    # ── 1980s: late Cold War, its collapse ──────────────────────────────────
    ("1980-09-22", "Iran-Iraq War begins",
     "Saddam Hussein's invasion started an eight-year war that killed ~1 million "
     "and drew in the Gulf and the superpowers.",
     "conflict", 30.50, 47.82, "Basra", 5),
    ("1982-04-02", "Falklands War",
     "Argentina's invasion of the British islands ended in defeat, toppling its "
     "junta and boosting Thatcher's Britain.",
     "conflict", -51.70, -57.85, "Falkland Islands", 3),
    ("1986-04-26", "Chernobyl nuclear disaster",
     "The world's worst nuclear accident spread fallout across Europe and became "
     "a symbol of Soviet decay.",
     "disaster", 51.39, 30.10, "Chernobyl", 5),
    ("1989-06-04", "Tiananmen Square massacre",
     "China's army crushed pro-democracy protests in Beijing, entrenching "
     "one-party rule as the bloc crumbled elsewhere.",
     "conflict", 39.90, 116.39, "Beijing", 4),
    ("1989-11-09", "Fall of the Berlin Wall",
     "East Germans breached the Wall, triggering the collapse of communism "
     "across Eastern Europe and German reunification.",
     "geopolitics", 52.52, 13.40, "Berlin", 5),
    ("1988-08-20", "Iran-Iraq War ceasefire",
     "A UN-brokered truce ended the decade's bloodiest interstate war with no "
     "border changes, leaving Iraq armed and indebted.",
     "diplomacy", 33.31, 44.36, "Baghdad", 3),
    # ── 1990s: post-Cold-War order, new wars ────────────────────────────────
    ("1990-08-02", "Iraq invades Kuwait",
     "Saddam's seizure of Kuwait triggered the US-led Gulf War coalition and a "
     "new era of American military primacy.",
     "conflict", 29.38, 47.99, "Kuwait City", 4),
    ("1991-01-17", "Gulf War: Operation Desert Storm",
     "A 35-nation coalition expelled Iraq from Kuwait in six weeks, showcasing "
     "US precision warfare and the post-Cold-War order.",
     "military", 29.38, 47.99, "Kuwait City", 4),
    ("1991-12-26", "Dissolution of the Soviet Union",
     "The USSR formally dissolved into 15 states, ending the Cold War and "
     "leaving the US the sole superpower.",
     "geopolitics", 55.75, 37.62, "Moscow", 5),
    ("1994-04-07", "Rwandan Genocide",
     "Hutu extremists murdered ~800,000 Tutsi in 100 days while the world stood "
     "by — a defining failure of humanitarian response.",
     "conflict", -1.94, 30.06, "Kigali", 5),
    ("1994-05-10", "Mandela elected; apartheid ends in South Africa",
     "The first multiracial election made Nelson Mandela president, ending "
     "decades of white-minority rule.",
     "geopolitics", -25.75, 28.19, "Pretoria", 4),
    ("1995-07-11", "Srebrenica massacre",
     "Bosnian Serb forces murdered ~8,000 Muslim men and boys, Europe's worst "
     "atrocity since WWII, spurring NATO intervention and the Dayton peace.",
     "conflict", 44.10, 19.30, "Srebrenica", 5),
    ("1997-07-01", "Hong Kong returns to China",
     "Britain handed its last major colony to Beijing under 'one country, two "
     "systems', a formula strained ever since.",
     "geopolitics", 22.32, 114.17, "Hong Kong", 3),
    ("1998-05-11", "India and Pakistan conduct nuclear tests",
     "Tit-for-tat tests made South Asia's rivalry overtly nuclear, raising the "
     "stakes of every Kashmir crisis since.",
     "military", 27.08, 71.72, "Pokhran", 4),
    ("1999-01-01", "The euro is launched",
     "Eleven European states adopted a single currency, deepening integration "
     "and creating a rival to the dollar.",
     "finance", 50.11, 8.68, "Frankfurt", 3),
    # ── 2000s: 9/11, the War on Terror, a crash ─────────────────────────────
    ("2001-09-11", "September 11 attacks",
     "Al-Qaeda's hijackings killed ~3,000 and launched the two-decade US 'War on "
     "Terror', reshaping global security and civil liberties.",
     "conflict", 40.71, -74.01, "New York", 5),
    ("2001-10-07", "US invades Afghanistan",
     "The US-led response to 9/11 toppled the Taliban in weeks but began a "
     "20-year nation-building war that ended in the Taliban's return.",
     "conflict", 34.53, 69.17, "Kabul", 5),
    ("2003-03-20", "US-led invasion of Iraq",
     "Justified by never-found WMD, the war destroyed the Iraqi state, empowered "
     "Iran, and incubated the insurgency that became ISIS.",
     "conflict", 33.31, 44.36, "Baghdad", 5),
    ("2004-12-26", "Indian Ocean tsunami kills ~230,000",
     "A magnitude-9.1 quake off Sumatra unleashed waves across 14 countries in "
     "one of the deadliest natural disasters in recorded history.",
     "disaster", 3.32, 95.85, "Aceh", 5),
    ("2008-09-15", "Lehman Brothers collapses; global financial crisis",
     "The bank's failure triggered the worst financial crisis since 1929, a "
     "global recession, bailouts, and a decade of populist backlash.",
     "finance", 40.71, -74.01, "New York", 5),
    ("2008-08-08", "Russia-Georgia War",
     "Moscow's five-day war over South Ossetia and Abkhazia was the first "
     "post-Soviet armed rebuff to NATO enlargement — a template for 2014/2022.",
     "conflict", 41.72, 44.83, "Tbilisi", 3),
    ("2007-01-09", "Apple unveils the iPhone",
     "The smartphone reshaped communication, media, politics and the global "
     "economy within a decade.",
     "technology", 37.33, -122.03, "Cupertino", 3),
    # ── 2010s: Arab Spring, a resurgent Russia, populism ────────────────────
    ("2010-12-17", "Arab Spring begins in Tunisia",
     "A street vendor's self-immolation sparked uprisings that toppled leaders "
     "across the Arab world and unleashed a decade of upheaval.",
     "geopolitics", 34.74, 10.76, "Sidi Bouzid", 5),
    ("2011-03-15", "Syrian civil war begins",
     "Assad's crackdown on protests spiraled into a war that killed ~500,000, "
     "displaced millions, birthed ISIS and drew in global powers.",
     "conflict", 33.51, 36.29, "Damascus", 5),
    ("2011-05-02", "US kills Osama bin Laden",
     "A Navy SEAL raid in Pakistan ended a decade-long manhunt for the 9/11 "
     "mastermind.", "military", 34.17, 73.24, "Abbottabad", 4),
    ("2014-02-20", "Russia annexes Crimea; war in Donbas",
     "Moscow seized Crimea after Ukraine's Maidan revolution and fueled a Donbas "
     "proxy war — the prologue to the 2022 full invasion.",
     "conflict", 44.95, 34.10, "Simferopol", 5),
    ("2014-06-29", "ISIS declares its caliphate",
     "The jihadist group seized a third of Iraq and Syria, drawing a global "
     "coalition into years of war and inspiring worldwide attacks.",
     "conflict", 36.34, 43.13, "Mosul", 5),
    ("2015-09-01", "European migration crisis peaks",
     "Over a million refugees, mostly Syrians, reached Europe, straining the EU "
     "and fueling a populist-right surge.",
     "geopolitics", 48.14, 17.11, "Central Europe", 4),
    ("2016-06-23", "United Kingdom votes for Brexit",
     "Britons voted to leave the EU, the bloc's first exit, reshaping European "
     "politics and Britain's global role.",
     "geopolitics", 51.51, -0.13, "London", 4),
    ("2016-11-08", "Donald Trump elected US president (first term)",
     "A populist outsider won the White House, upending trade, alliances and "
     "American politics.", "geopolitics", 38.90, -77.04, "Washington", 4),
    ("2015-12-12", "Paris Agreement on climate change adopted",
     "Nearly 200 nations agreed to limit warming to well below 2°C, the "
     "cornerstone of global climate diplomacy.",
     "diplomacy", 48.86, 2.35, "Paris", 3),
    ("2019-06-09", "Hong Kong pro-democracy protests erupt",
     "Millions marched against an extradition bill; Beijing's 2020 security law "
     "crushed the movement and the city's autonomy.",
     "geopolitics", 22.32, 114.17, "Hong Kong", 4),
    # ── 2020s: pandemic, and the return of great-power war ──────────────────
    ("2020-03-11", "WHO declares COVID-19 a pandemic",
     "The coronavirus killed millions, locked down the planet, crashed and "
     "reshaped economies, and accelerated remote work and vaccine science.",
     "disaster", 30.59, 114.31, "Wuhan", 5),
    ("2020-05-25", "George Floyd's murder sparks global protests",
     "His killing by Minneapolis police ignited the largest US protest movement "
     "in decades and a worldwide racial-justice reckoning.",
     "geopolitics", 44.98, -93.27, "Minneapolis", 3),
    ("2021-01-06", "US Capitol attack",
     "A pro-Trump mob stormed Congress to overturn the 2020 election, the "
     "gravest assault on the US transfer of power in modern times.",
     "geopolitics", 38.89, -77.01, "Washington", 4),
    ("2021-08-15", "Taliban retake Kabul as the US withdraws",
     "Afghanistan's government collapsed in eleven days, ending America's "
     "longest war in a chaotic evacuation.",
     "conflict", 34.53, 69.17, "Kabul", 5),
    ("2022-02-24", "Russia launches full-scale invasion of Ukraine",
     "Europe's largest war since 1945 began, remaking the continent's security, "
     "energy and alliances and killing hundreds of thousands.",
     "conflict", 50.45, 30.52, "Kyiv", 5),
    ("2023-10-07", "Hamas attacks Israel; Gaza war begins",
     "The deadliest day for Jews since the Holocaust triggered a devastating "
     "Gaza war, a regional escalation and a global rupture.",
     "conflict", 31.50, 34.47, "Gaza", 5),
    ("2024-12-08", "Assad regime falls in Syria",
     "A lightning rebel offensive ended 53 years of Assad family rule, "
     "collapsing Iran and Russia's western anchor.",
     "conflict", 33.51, 36.29, "Damascus", 5),
]


# Second wave — economic, technological, regional and humanitarian depth so the
# chain isn't only great-power politics. Same tuple shape; concatenated below.
DEEP_HISTORY += [
    # decolonization + Africa
    ("1957-03-06", "Ghana becomes first sub-Saharan colony to gain independence",
     "Kwame Nkrumah's Ghana inspired a wave of African liberation and "
     "pan-Africanism.", "geopolitics", 5.60, -0.19, "Accra", 3),
    ("1960-07-05", "Congo Crisis begins",
     "Independence from Belgium collapsed into secession, UN intervention and "
     "Lumumba's murder — a Cold War proxy tragedy.",
     "conflict", -4.32, 15.31, "Kinshasa", 4),
    ("1962-07-05", "Algeria wins independence from France",
     "A brutal eight-year war (~1 million dead) ended 132 years of French rule "
     "and scarred both nations.", "conflict", 36.75, 3.06, "Algiers", 4),
    ("1971-08-15", "Nixon ends the gold standard",
     "The US closed the gold window, ending Bretton Woods and ushering in the era "
     "of floating fiat currencies.", "finance", 38.90, -77.04, "Washington", 4),
    ("1973-09-11", "Chile: Pinochet's coup topples Allende",
     "A US-backed military coup killed the elected socialist president and began "
     "17 years of dictatorship — a Cold War Latin American template.",
     "geopolitics", -33.44, -70.65, "Santiago", 4),
    ("1975-04-13", "Lebanese Civil War begins",
     "Fifteen years of sectarian war devastated Beirut, drew in Syria and Israel, "
     "and shaped the modern Levant.", "conflict", 33.89, 35.50, "Beirut", 4),
    ("1976-03-24", "Argentina's 'Dirty War' junta seizes power",
     "The military disappeared ~30,000 people, a defining Latin American "
     "state-terror episode.", "conflict", -34.60, -58.38, "Buenos Aires", 4),
    ("1979-03-26", "Egypt-Israel peace treaty signed",
     "The Camp David follow-through made Egypt the first Arab state to recognize "
     "Israel, costing Sadat his life in 1981.",
     "diplomacy", 30.04, 31.24, "Cairo", 3),
    ("1984-12-03", "Bhopal gas disaster",
     "A Union Carbide leak in India killed thousands overnight — the world's "
     "worst industrial catastrophe.", "disaster", 23.26, 77.41, "Bhopal", 5),
    ("1985-03-11", "Gorbachev launches perestroika and glasnost",
     "Soviet reforms meant to save communism instead accelerated its collapse.",
     "geopolitics", 55.75, 37.62, "Moscow", 4),
    ("1987-10-19", "Black Monday stock market crash",
     "Global markets fell ~22% in a day, the largest one-day percentage drop in "
     "history, testing the new era of electronic trading.",
     "finance", 40.71, -74.01, "New York", 4),
    ("1988-12-21", "Lockerbie bombing",
     "The bombing of Pan Am 103 killed 270, a landmark of state-sponsored "
     "terrorism that isolated Libya.", "conflict", 55.12, -3.36, "Lockerbie", 3),
    ("1989-12-20", "US invades Panama; captures Noriega",
     "Operation Just Cause removed the dictator, a post-Cold-War assertion of US "
     "power in its hemisphere.", "military", 8.98, -79.52, "Panama City", 3),
    ("1990-02-11", "Nelson Mandela freed after 27 years",
     "His release began the negotiated end of apartheid and made him a global "
     "moral icon.", "geopolitics", -33.92, 18.42, "Cape Town", 4),
    ("1991-08-06", "The World Wide Web goes public",
     "Tim Berners-Lee's invention at CERN opened the internet to everyone, "
     "reshaping every domain of human life.",
     "technology", 46.23, 6.05, "Geneva", 4),
    ("1993-09-13", "Oslo Accords signed",
     "The Rabin-Arafat handshake created the Palestinian Authority and a "
     "framework for peace that later collapsed.",
     "diplomacy", 38.90, -77.04, "Washington", 4),
    ("1994-01-01", "NAFTA takes effect; Zapatista uprising",
     "North American free trade launched as Mexico's Zapatistas rebelled, "
     "framing the globalization debate.", "finance", 19.43, -99.13, "Mexico City", 3),
    ("1997-07-02", "Asian Financial Crisis begins",
     "A Thai baht collapse cascaded across East Asia, forcing IMF bailouts and "
     "reshaping emerging-market finance.", "finance", 13.76, 100.50, "Bangkok", 4),
    ("2000-03-10", "Dot-com bubble bursts",
     "The Nasdaq peaked then crashed, wiping out trillions and ending the first "
     "internet mania.", "finance", 37.33, -122.03, "Silicon Valley", 4),
    ("2002-01-01", "Euro banknotes and coins enter circulation",
     "300 million Europeans began using a shared currency, the boldest step of "
     "European integration.", "finance", 50.11, 8.68, "Frankfurt", 3),
    ("2004-05-01", "EU's 'big bang' enlargement",
     "Ten mostly ex-communist states joined the EU, reunifying Europe after the "
     "Cold War division.", "diplomacy", 50.85, 4.35, "Brussels", 3),
    ("2010-01-12", "Haiti earthquake kills ~230,000",
     "A magnitude-7.0 quake flattened Port-au-Prince, one of the deadliest "
     "disasters of the century.", "disaster", 18.54, -72.34, "Port-au-Prince", 5),
    ("2011-03-11", "Fukushima: quake, tsunami and nuclear meltdown",
     "Japan's triple disaster killed ~18,000 and triggered a global nuclear-energy "
     "retreat.", "disaster", 37.42, 141.03, "Fukushima", 5),
    ("2011-10-20", "Gaddafi killed as Libya's uprising ends his rule",
     "NATO-backed rebels toppled the 42-year dictator, but Libya fractured into "
     "lasting civil war.", "conflict", 32.76, 12.72, "Sirte", 4),
    ("2011-05-01", "Osama bin Laden era ends; Arab Spring reshapes region",
     "The convergence of bin Laden's death and the Arab uprisings marked a "
     "turning point in the War on Terror.",
     "geopolitics", 30.04, 31.24, "Cairo", 3),
    ("2014-03-08", "MH370 vanishes",
     "The disappearance of a Malaysian airliner with 239 aboard became aviation's "
     "greatest unsolved mystery.", "disaster", 2.75, 101.71, "Kuala Lumpur", 3),
    ("2014-08-01", "West African Ebola epidemic explodes",
     "The largest Ebola outbreak killed ~11,000 and exposed gaps in global health "
     "security.", "disaster", 8.48, -13.23, "Freetown", 4),
    ("2015-11-13", "Paris terror attacks",
     "Coordinated ISIS attacks killed 130, the deadliest in France since WWII, "
     "hardening Europe's security posture.",
     "conflict", 48.86, 2.35, "Paris", 4),
    ("2017-08-25", "Rohingya genocide: mass exodus from Myanmar",
     "A military campaign drove ~750,000 Rohingya into Bangladesh, ruled a "
     "genocide by the UN and later the US.",
     "conflict", 20.85, 92.30, "Cox's Bazar", 5),
    ("2018-06-12", "First Trump-Kim summit",
     "The historic Singapore meeting was the first between sitting US and North "
     "Korean leaders, though denuclearization stalled.",
     "diplomacy", 1.35, 103.82, "Singapore", 3),
    ("2019-04-21", "Sri Lanka Easter bombings",
     "ISIS-linked suicide attacks killed ~270, a landmark of the group's global "
     "reach after its territorial defeat.", "conflict", 6.93, 79.85, "Colombo", 3),
    ("2020-01-03", "US kills Iran's Qasem Soleimani",
     "A US drone strike killed Iran's top general in Baghdad, bringing Washington "
     "and Tehran to the brink.", "military", 33.31, 44.36, "Baghdad", 4),
    ("2021-02-01", "Myanmar military coup",
     "The army's seizure of power ended a decade of democratization and ignited a "
     "nationwide civil war.", "geopolitics", 19.75, 96.10, "Naypyidaw", 4),
    ("2022-11-30", "ChatGPT launches, igniting the generative-AI boom",
     "OpenAI's chatbot reached 100 million users in two months, triggering a "
     "global AI race and investment wave.",
     "technology", 37.77, -122.42, "San Francisco", 4),
    ("2023-04-15", "Sudan war erupts between the army and RSF",
     "Two generals' power struggle became the world's largest displacement "
     "crisis, with famine and Darfur atrocities.",
     "conflict", 15.50, 32.56, "Khartoum", 5),
    ("2023-02-06", "Turkey-Syria earthquakes kill ~60,000",
     "Massive quakes devastated the border region, one of the deadliest disasters "
     "of the decade.", "disaster", 37.17, 37.03, "Gaziantep", 5),
    ("1970-11-12", "Bhola cyclone kills ~500,000 in East Pakistan",
     "The deadliest tropical cyclone on record, whose mishandling fueled the "
     "Bangladesh independence movement.", "disaster", 22.70, 91.10, "Bhola", 5),
    ("1965-09-30", "Indonesian mass killings",
     "An anti-communist purge killed ~500,000-1,000,000 and brought Suharto to "
     "power for three decades.", "conflict", -6.20, 106.85, "Jakarta", 4),
    ("1979-07-19", "Sandinista revolution triumphs in Nicaragua",
     "The overthrow of Somoza launched a Cold War proxy struggle with the "
     "US-backed Contras.", "conflict", 12.11, -86.24, "Managua", 3),
    ("1982-09-16", "Sabra and Shatila massacre",
     "The killing of Palestinian refugees during Israel's Lebanon war became a "
     "defining atrocity of the conflict.", "conflict", 33.86, 35.49, "Beirut", 4),
    ("1987-12-08", "First Palestinian Intifada begins",
     "A grassroots uprising in the occupied territories reshaped the "
     "Israeli-Palestinian struggle and led toward Oslo.",
     "conflict", 31.50, 34.47, "Gaza", 3),
    ("2000-09-28", "Second Intifada erupts",
     "Years of suicide bombings and Israeli reoccupation destroyed the Oslo peace "
     "process.", "conflict", 31.78, 35.22, "Jerusalem", 4),
    ("2005-10-08", "Kashmir earthquake kills ~86,000",
     "A magnitude-7.6 quake devastated Pakistani Kashmir, a landmark South Asian "
     "disaster.", "disaster", 34.49, 73.63, "Muzaffarabad", 4),
    ("2008-11-26", "Mumbai terror attacks",
     "Pakistan-based militants killed 166 over three days, straining India-Pakistan "
     "relations to the brink.", "conflict", 18.92, 72.83, "Mumbai", 4),
    ("2013-06-05", "Snowden leaks expose global mass surveillance",
     "The NSA disclosures reshaped debates over privacy, security and US "
     "alliances.", "technology", 22.32, 114.17, "Hong Kong", 3),
    ("2016-07-15", "Failed coup in Turkey",
     "A botched military takeover let Erdoğan purge the state and consolidate "
     "sweeping powers.", "geopolitics", 39.93, 32.86, "Ankara", 4),
    ("2019-10-23", "Global protest wave: Chile, Lebanon, Iraq, Hong Kong",
     "A worldwide surge of anti-government protests over inequality and corruption "
     "marked the pre-pandemic mood.", "geopolitics", -33.44, -70.65, "Santiago", 3),
    ("2020-08-04", "Beirut port explosion",
     "A massive ammonium-nitrate blast killed ~220 and devastated the capital, "
     "symbol of Lebanon's state collapse.", "disaster", 33.90, 35.52, "Beirut", 4),
    ("2023-02-03", "US-China balloon incident",
     "A Chinese surveillance balloon shot down over the US crystallized the new "
     "great-power tech-and-spying rivalry.",
     "geopolitics", 33.86, -78.68, "South Carolina", 2),
    ("1994-12-11", "First Chechen War begins",
     "Russia's brutal wars to hold Chechnya killed tens of thousands and shaped "
     "Putin's rise.", "conflict", 43.32, 45.69, "Grozny", 4),
    ("1998-08-07", "Al-Qaeda bombs US embassies in East Africa",
     "Simultaneous attacks in Kenya and Tanzania killed ~224, announcing bin "
     "Laden's global campaign.", "conflict", -1.29, 36.82, "Nairobi", 3),
    ("2003-04-09", "Fall of Baghdad; Saddam's statue toppled",
     "US forces took the Iraqi capital, beginning a chaotic occupation and "
     "insurgency.", "conflict", 33.31, 44.36, "Baghdad", 4),
    ("2006-07-12", "Israel-Hezbollah war (2006)",
     "A month-long war in Lebanon killed over a thousand and cemented Hezbollah "
     "as a regional force.", "conflict", 33.27, 35.20, "South Lebanon", 3),
]
