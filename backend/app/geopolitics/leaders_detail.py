"""v6.6.5 — curated comprehensive profiles for major world leaders, so the
leader page is rich even when live Wikipedia AND an AI provider are both
unavailable (owner: the al-Sharaa page was blank). Live Wikipedia bio + AI
synthesis still layer on top and win when present; this is the guaranteed
floor. Keyed by a normalized lowercased name. Fields mirror the AI synthesis
shape (summary/ideology/career_history/party_history/key_policies) plus a
bio paragraph. Not exhaustive — the most-viewed leaders."""

# name_key -> dict
LEADER_DETAIL = {
    "ahmed al-sharaa": {
        "summary": "Ahmed al-Sharaa (formerly known by the nom de guerre Abu "
        "Mohammad al-Julani) is the president of Syria's transitional government, "
        "having led the offensive that toppled Bashar al-Assad in December 2024. "
        "He was named head of state in January 2025.",
        "ideology": "Sunni Islamist turned pragmatic nationalist; has publicly "
        "moderated toward inclusive, state-building governance.",
        "career_history": [
            "Joined the insurgency against US forces in Iraq in the mid-2000s; "
            "detained by US forces for several years.",
            "Founded Jabhat al-Nusra (al-Qaeda's Syrian affiliate) in 2012.",
            "Broke with al-Qaeda and rebranded the group as Hayat Tahrir al-Sham "
            "(HTS) in 2016-2017, consolidating control of Idlib.",
            "Led the lightning offensive that captured Damascus and ended the "
            "Assad government in December 2024.",
            "Appointed head of Syria's transitional state on 29 January 2025.",
        ],
        "party_history": [
            "Al-Qaeda in Iraq / Islamic State of Iraq (2000s)",
            "Jabhat al-Nusra, founder (2012-2016)",
            "Hayat Tahrir al-Sham, leader (2017-present)",
        ],
        "key_policies": [
            "Managing a transitional government and drafting a new constitutional order.",
            "Seeking sanctions relief and international recognition for the new Syria.",
            "Signaling protection for minorities and a pluralist transition (contested by critics).",
            "Reintegrating armed factions into a unified national army.",
            "Rebuilding state institutions after 13 years of civil war.",
        ],
        "bio_extract": "Ahmed Hussein al-Sharaa is a Syrian politician and former "
        "insurgent leader who became the de facto ruler of Syria after leading the "
        "December 2024 offensive that overthrew Bashar al-Assad. Long known by the "
        "alias Abu Mohammad al-Julani, he built Hayat Tahrir al-Sham into the "
        "dominant force in northwest Syria before seizing Damascus.",
    },
    "volodymyr zelenskyy": {
        # v6.6.7 — a professional (non-military) headshot: the official 2019
        # presidential portrait. Special:FilePath resolves the file by name
        # without needing the CDN hash, so the link stays valid.
        "portrait_url": "https://commons.wikimedia.org/wiki/Special:FilePath/"
                        "Volodymyr_Zelensky_Official_portrait.jpg?width=480",
        "summary": "Volodymyr Zelenskyy is the president of Ukraine, in office "
        "since 2019, who has led the country's defense against Russia's full-scale "
        "invasion since February 2022.",
        "ideology": "Liberal, pro-European, anti-corruption; wartime national unity.",
        "career_history": [
            "Comedian and actor; starred in the TV series 'Servant of the People'.",
            "Founded the Kvartal 95 entertainment studio.",
            "Elected president of Ukraine in a 2019 landslide.",
            "Became a wartime leader after Russia's 2022 invasion.",
        ],
        "party_history": ["Servant of the People party, founder (2018-present)"],
        "key_policies": [
            "Total mobilization and defense against the Russian invasion.",
            "EU and NATO accession bids.",
            "Anti-corruption and judicial reform.",
            "Securing Western military and financial aid.",
        ],
        "bio_extract": "Volodymyr Oleksandrovych Zelenskyy is a Ukrainian "
        "politician and former entertainer serving as the sixth president of "
        "Ukraine since 2019. He became a globally prominent wartime leader "
        "following Russia's full-scale invasion in 2022.",
    },
    "vladimir putin": {
        "summary": "Vladimir Putin is the president of Russia, the country's "
        "paramount leader since 2000 (as president or prime minister).",
        "ideology": "Authoritarian statism, Russian nationalism, sovereign-power politics.",
        "career_history": [
            "KGB foreign-intelligence officer, stationed in Dresden.",
            "Head of the FSB in the late 1990s.",
            "Prime minister, then acting president in 1999-2000.",
            "President of Russia (2000-2008, 2012-present); PM 2008-2012.",
        ],
        "party_history": ["United Russia (affiliated)"],
        "key_policies": [
            "Centralized 'power vertical' and control of media and elections.",
            "Annexation of Crimea (2014) and the invasion of Ukraine (2022).",
            "Energy geopolitics and confrontation with the West.",
        ],
        "bio_extract": "Vladimir Vladimirovich Putin is a Russian politician and "
        "former intelligence officer who has served as president of Russia since "
        "2012, and previously from 2000 to 2008.",
    },
    "xi jinping": {
        "summary": "Xi Jinping is China's paramount leader — General Secretary of "
        "the Chinese Communist Party, President, and chair of the Central Military "
        "Commission.",
        "ideology": "Marxism-Leninism, Chinese nationalism, 'Xi Jinping Thought'.",
        "career_history": [
            "Provincial party posts in Fujian, Zhejiang and Shanghai.",
            "Joined the Politburo Standing Committee in 2007.",
            "CCP General Secretary since 2012; President since 2013.",
            "Removed presidential term limits in 2018.",
        ],
        "party_history": ["Chinese Communist Party, General Secretary (2012-present)"],
        "key_policies": [
            "Anti-corruption campaign and party discipline.",
            "Belt and Road Initiative.",
            "'Common prosperity' and tighter state control of the economy.",
            "Assertive foreign policy over Taiwan and the South China Sea.",
        ],
        "bio_extract": "Xi Jinping is a Chinese politician who has been the "
        "paramount leader of China since 2012, serving as general secretary of the "
        "Chinese Communist Party, president, and chairman of the Central Military "
        "Commission.",
    },
    "donald trump": {
        "summary": "Donald Trump is the president of the United States, serving a "
        "second, non-consecutive term after winning the 2024 election.",
        "ideology": "Right-wing populism, economic nationalism, 'America First'.",
        "career_history": [
            "Real-estate developer and businessman (The Trump Organization).",
            "Television personality ('The Apprentice').",
            "45th US president (2017-2021).",
            "47th US president (2025-present).",
        ],
        "party_history": ["Republican Party"],
        "key_policies": [
            "Tariffs and protectionist trade policy.",
            "Restrictive immigration and border enforcement.",
            "Deregulation and tax cuts.",
            "Skepticism of multilateral alliances and foreign aid.",
        ],
        "bio_extract": "Donald John Trump is an American politician, media "
        "personality and businessman serving as the 47th president of the United "
        "States. He previously served as the 45th president from 2017 to 2021.",
    },
    "narendra modi": {
        "summary": "Narendra Modi is the prime minister of India, in office since "
        "2014 and leader of the Bharatiya Janata Party.",
        "ideology": "Hindu nationalism (Hindutva), economic liberalization, populism.",
        "career_history": [
            "Full-time RSS worker from a young age.",
            "Chief minister of Gujarat (2001-2014).",
            "Prime minister of India since 2014 (three terms).",
        ],
        "party_history": ["Rashtriya Swayamsevak Sangh (RSS)", "Bharatiya Janata Party (BJP)"],
        "key_policies": [
            "'Make in India' manufacturing and infrastructure push.",
            "Digital India and welfare-delivery reforms.",
            "Revocation of Article 370 in Jammu & Kashmir (2019).",
            "Strategic alignment with the US and the Quad.",
        ],
        "bio_extract": "Narendra Damodardas Modi is an Indian politician serving "
        "as the 14th prime minister of India since 2014. He was the chief minister "
        "of Gujarat from 2001 to 2014 and is a member of the BJP.",
    },
    "benjamin netanyahu": {
        "summary": "Benjamin Netanyahu is the prime minister of Israel and the "
        "longest-serving leader in the country's history.",
        "ideology": "National conservatism, security-first Zionism, economic liberalism.",
        "career_history": [
            "Israeli special-forces officer and diplomat (ambassador to the UN).",
            "Leader of Likud since the 1990s.",
            "Prime minister 1996-1999, 2009-2021, and 2022-present.",
        ],
        "party_history": ["Likud, leader"],
        "key_policies": [
            "Hardline security policy and the war in Gaza.",
            "Opposition to a nuclear Iran.",
            "Normalization with Arab states (Abraham Accords).",
            "Contested judicial-overhaul push.",
        ],
        "bio_extract": "Benjamin Netanyahu is an Israeli politician serving as the "
        "prime minister of Israel. He is the longest-tenured PM in the country's "
        "history and the leader of the Likud party.",
    },
    "keir starmer": {
        "summary": "Keir Starmer is the prime minister of the United Kingdom and "
        "leader of the Labour Party, in office since the 2024 election.",
        "ideology": "Social democracy, centre-left pragmatism.",
        "career_history": [
            "Human-rights barrister; King's Counsel.",
            "Director of Public Prosecutions (2008-2013).",
            "MP since 2015; Labour leader since 2020.",
            "Prime minister since July 2024.",
        ],
        "party_history": ["Labour Party, leader (2020-present)"],
        "key_policies": [
            "Economic growth and planning reform.",
            "NHS investment and public-service renewal.",
            "Closer, pragmatic ties with the EU.",
        ],
        "bio_extract": "Sir Keir Rodney Starmer is a British politician and former "
        "barrister serving as prime minister of the United Kingdom and leader of "
        "the Labour Party since 2024.",
    },
    "emmanuel macron": {
        "summary": "Emmanuel Macron is the president of France, in office since 2017.",
        "ideology": "Liberal centrism, pro-European integration.",
        "career_history": [
            "Investment banker at Rothschild & Co.",
            "Economy minister under François Hollande.",
            "Founded En Marche (now Renaissance) in 2016.",
            "President of France since 2017.",
        ],
        "party_history": ["Renaissance (formerly La République En Marche), founder"],
        "key_policies": [
            "Pension and labour-market reform.",
            "European strategic autonomy and defense.",
            "Pro-business tax and investment policy.",
        ],
        "bio_extract": "Emmanuel Jean-Michel Frédéric Macron is a French politician "
        "who has served as president of France since 2017.",
    },
}


def leader_detail(name):
    if not name:
        return None
    return LEADER_DETAIL.get(name.split("(")[0].strip().lower())
