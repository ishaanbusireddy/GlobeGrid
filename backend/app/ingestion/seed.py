"""Seeds the sources table — v1 Section 4 list plus every v2 addendum §1
addition. Idempotent: matches on name.

Leaning labels (Section 5.7) are a small manually-curated table following
the commonly published media-bias chart placements for these outlets —
editable here, nowhere else. v2: sources carry kind='official' when they
are primary-source government/institution feeds (§1.2), so the UI can
show 'official statement' vs 'reported'.
"""

from ..config import cfg
from ..db.models import new_id
from ..db.session import query_one, write_tx

# (name, type, url, leaning, kind)
SOURCES = [
    # --- v1 Section 4.1 news RSS ---
    ("BBC World", "rss", "https://feeds.bbci.co.uk/news/world/rss.xml", "center", "reported"),
    ("Al Jazeera", "rss", "https://www.aljazeera.com/xml/rss/all.xml", "left", "reported"),
    ("NYT World", "rss", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "left", "reported"),
    ("Washington Post", "rss", "https://feeds.washingtonpost.com/rss/national", "left", "reported"),
    ("CNN World", "rss", "http://rss.cnn.com/rss/edition_world.rss", "left", "reported"),
    ("NPR", "rss", "https://feeds.npr.org/1001/rss.xml", "center", "reported"),
    ("Reuters (via Google News)", "rss",
     "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com", "center", "reported"),
    # --- v2 §1.2 regional / non-English outlets (display-time translation path) ---
    ("Xinhua World", "rss", "https://english.news.cn/rss/worldrss.xml", "center", "reported"),
    ("TASS", "rss", "https://tass.com/rss/v2.xml", "center", "reported"),
    ("Le Monde International", "rss",
     "https://www.lemonde.fr/international/rss_full.xml", "left", "reported"),
    ("Haaretz", "rss", "https://www.haaretz.com/srv/haaretz-latest-headlines", "left", "reported"),
    ("Times of India World", "rss",
     "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "center", "reported"),
    # --- v2 §1.2 primary sources (official statements) ---
    ("White House", "rss", "https://www.whitehouse.gov/feed/", "n/a", "official"),
    ("EU Commission", "rss",
     "https://ec.europa.eu/commission/presscorner/api/rss?search=&language=en&pagesize=25",
     "n/a", "official"),
    ("UN News", "rss", "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
     "n/a", "official"),
    # --- v1 Section 4.2 + v2 §1.1 structured event data (GDELT removed v6 §2) ---
    ("ACLED Conflict Data", "acled", "https://api.acleddata.com/acled/read", "n/a", "reported"),
    # --- v1 Section 4.3 + v2 §1.1 physical hazards ---
    ("USGS Earthquakes", "usgs",
     "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
     "n/a", "reported"),
    ("NASA FIRMS Wildfires", "firms",
     "https://firms.modaps.eosdis.nasa.gov/api/area/", "n/a", "reported"),
    ("Smithsonian Volcanism", "volcano",
     "https://volcano.si.edu/news/WeeklyVolcanoRSS.xml", "n/a", "reported"),
    # --- v1 Section 4.4 markets ---
    ("Alpha Vantage", "market", "https://www.alphavantage.co/query", "n/a", "reported"),
    # --- v1 Section 4.5 + v2 §1.3 social / attention ---
    ("Reddit", "reddit", "https://oauth.reddit.com/r/worldnews+geopolitics+economics/hot",
     "n/a", "reported"),
    ("Wikipedia Current Events", "wikipedia",
     "https://api.wikimedia.org/feed/v1/wikipedia/en/featured", "n/a", "reported"),
    ("Wikipedia Pageview Spikes", "wiki_views",
     "https://wikimedia.org/api/rest_v1/metrics/pageviews", "n/a", "reported"),
    ("Mastodon", "mastodon", "https://mastodon.social/api/v1/timelines", "n/a", "reported"),
    ("Bluesky", "bluesky", "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
     "n/a", "reported"),
    # --- v2 §1.4 transport ---
    ("OpenSky Air Traffic", "opensky", "https://opensky-network.org/api/states/all",
     "n/a", "reported"),
    # --- v4 §13.2 economic/market breadth: central-bank statements and
    # institutional economic releases are structurally different from both
    # news articles and price ticks — tracked as their own official feeds ---
    ("US Federal Reserve", "rss",
     "https://www.federalreserve.gov/feeds/press_all.xml", "n/a", "official"),
    ("European Central Bank", "rss",
     "https://www.ecb.europa.eu/rss/press.html", "n/a", "official"),
    ("Bank of England", "rss",
     "https://www.bankofengland.co.uk/rss/news", "n/a", "official"),
    ("IMF Press", "rss",
     "https://www.imf.org/en/News/RSS?Language=ENG", "n/a", "official"),
    ("World Bank News", "rss",
     "https://www.worldbank.org/en/news/all?format=atom", "n/a", "official"),
    ("US BLS Economic Releases", "rss",
     "https://www.bls.gov/feed/news_release.rss", "n/a", "official"),
    # --- v4 §13.1 per-country breadth: pan-regional outlets covering the
    # regions the majors structurally under-cover ---
    ("AllAfrica Headlines", "rss",
     "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
     "center", "reported"),
    ("France24 Africa", "rss",
     "https://www.france24.com/en/africa/rss", "center", "reported"),
    ("MercoPress South Atlantic", "rss",
     "https://en.mercopress.com/rss/", "center", "reported"),
    ("Channel NewsAsia", "rss",
     "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml",
     "center", "reported"),
    ("Arab News", "rss", "https://www.arabnews.com/rss.xml", "center", "reported"),
    ("Kyiv Independent", "rss",
     "https://kyivindependent.com/feed/rss", "center", "reported"),
    # --- v5 §4 TalkDiplomacy.com (owner-operated; standard RSS source, no
    # special-casing). If the feed 404s the source degrades like any other. ---
    ("TalkDiplomacy", "rss", "https://talkdiplomacy.com/feed/", "center", "reported"),
    # --- v5 §5 higher-signal outlets beyond the original six (first-tier
    # wire/broadcast), demoting raw GDELT Events to a backup role ---
    ("AP Top News", "rss", "https://apnews.com/hub/ap-top-news/rss", "center", "reported"),
    ("AFP (via Google News)", "rss",
     "https://news.google.com/rss/search?q=when:24h+allinurl:afp.com", "center", "reported"),
    ("Reuters World (Google News)", "rss",
     "https://news.google.com/rss/search?q=when:24h+world+allinurl:reuters.com",
     "center", "reported"),
    ("The Guardian World", "rss", "https://www.theguardian.com/world/rss", "left", "reported"),
    ("Deutsche Welle", "rss", "https://rss.dw.com/rdf/rss-en-world", "center", "reported"),
    ("France 24", "rss", "https://www.france24.com/en/rss", "center", "reported"),
    ("NHK World", "rss", "https://www3.nhk.or.jp/nhkworld/en/news/feeds/", "center", "reported"),
    # --- v5 §5 government / military communications (per-country official
    # press, same pattern as v3 §18 org sourcing) ---
    ("US Dept of Defense", "rss",
     "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945",
     "n/a", "official"),
    ("US State Department", "rss",
     "https://www.state.gov/rss-feed/press-releases/feed/", "n/a", "official"),
    ("UK Government", "rss",
     "https://www.gov.uk/search/news-and-communications.atom", "n/a", "official"),
    ("NATO News", "rss", "https://www.nato.int/cps/en/natohq/news_rss.htm", "n/a", "official"),
    ("Russia MFA", "rss", "https://mid.ru/en/rss/", "n/a", "official"),
    ("Ukraine MFA", "rss", "https://mfa.gov.ua/en/rss.xml", "n/a", "official"),
    ("Israel MFA", "rss",
     "https://www.gov.il/en/api/DynamicCollector?rss=true&collectorType=news", "n/a", "official"),
    # --- v5 §5 curated OSINT (LiveUAMap model — vetted fast ground reporting,
    # NOT a generic keyword firehose; Reddit stays separate/unchanged) ---
    ("Liveuamap", "rss", "https://liveuamap.com/rss", "n/a", "reported"),
    ("ISW Ukraine Updates", "rss",
     "https://www.understandingwar.org/backgrounder/russian-offensive-campaign-assessment/feed",
     "n/a", "reported"),
    # --- v6 §2 — GDELT replacement coverage: broader reputable outlets,
    # defense/gov-mil press, curated policy desks. Ships together with the
    # GDELT removal so no coverage gap opens. ---
    ("Politico Europe", "rss", "https://www.politico.eu/feed/", "center", "reported"),
    ("The Diplomat", "rss", "https://thediplomat.com/feed/", "center", "reported"),
    ("South China Morning Post", "rss", "https://www.scmp.com/rss/91/feed",
     "center", "reported"),
    ("RFE/RL", "rss", "https://www.rferl.org/api/zrqiteuuir", "center", "reported"),
    ("Meduza (EN)", "rss", "https://meduza.io/rss/en", "center", "reported"),
    ("Anadolu Agency", "rss", "https://www.aa.com.tr/en/rss/default?cat=live",
     "center", "reported"),
    ("Defense News", "rss",
     "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml",
     "center", "reported"),
    ("Breaking Defense", "rss", "https://breakingdefense.com/feed/", "center", "reported"),
    ("ReliefWeb Updates", "rss", "https://reliefweb.int/updates/rss.xml",
     "n/a", "official"),
    ("Korea Herald", "rss", "https://www.koreaherald.com/rss/newsAll",
     "center", "reported"),
    # v6 §10 — faster-polling reputable local-language outlets for tracked
    # conflicts, so local reporting lands before Western wire coverage.
    # Ingestion-time translation (Groq) feeds the cross-lingual correlation.
    ("Ukrainska Pravda", "rss", "https://www.pravda.com.ua/rss/", "center", "reported"),
    ("Suspilne Ukraine", "rss", "https://suspilne.media/rss/all.rss", "center", "reported"),
    ("Meduza (RU)", "rss", "https://meduza.io/rss/all", "center", "reported"),
    ("Times of Israel", "rss", "https://www.timesofisrael.com/feed/", "center", "reported"),
    ("Ynet News", "rss", "https://www.ynetnews.com/Integration/StoryRss3082.xml",
     "center", "reported"),
    ("Al Mayadeen (EN)", "rss", "https://english.almayadeen.net/rss", "left", "reported"),
]

# v6.2 — ~100 more fast-updating global news RSS feeds (owner: broad, always-
# streaming coverage). A failing feed just backs off (v1 §10), never blocks;
# breadth is the point. Grouped by region for maintainability.
SOURCES += [
    # --- global wires / majors ---
    ("Al Jazeera English", "rss", "https://www.aljazeera.com/xml/rss/all.xml", "center", "reported"),
    ("Guardian World", "rss", "https://www.theguardian.com/world/rss", "left", "reported"),
    ("NYT World", "rss", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "left", "reported"),
    ("CNN World", "rss", "http://rss.cnn.com/rss/edition_world.rss", "left", "reported"),
    ("NPR World", "rss", "https://feeds.npr.org/1004/rss.xml", "center", "reported"),
    ("Euronews", "rss", "https://www.euronews.com/rss?level=theme&name=news", "center", "reported"),
    ("Sky News World", "rss", "https://feeds.skynews.com/feeds/rss/world.xml", "center", "reported"),
    ("CBC World", "rss", "https://www.cbc.ca/webfeed/rss/rss-world", "center", "reported"),
    ("CBS News World", "rss", "https://www.cbsnews.com/latest/rss/world", "center", "reported"),
    ("NBC News World", "rss", "https://feeds.nbcnews.com/nbcnews/public/world", "center", "reported"),
    ("ABC News (US) Intl", "rss", "https://abcnews.go.com/abcnews/internationalheadlines", "center", "reported"),
    ("The Hill", "rss", "https://thehill.com/rss/syndicator/19110", "center", "reported"),
    ("Axios World", "rss", "https://api.axios.com/feed/world", "center", "reported"),
    ("Time", "rss", "https://time.com/feed/", "center", "reported"),
    ("Newsweek World", "rss", "https://www.newsweek.com/rss", "center", "reported"),
    ("Vox", "rss", "https://www.vox.com/rss/index.xml", "left", "reported"),
    ("The Atlantic Global", "rss", "https://www.theatlantic.com/feed/channel/international/", "left", "reported"),
    ("Foreign Policy", "rss", "https://foreignpolicy.com/feed/", "center", "reported"),
    ("The National Interest", "rss", "https://nationalinterest.org/feed", "right", "reported"),
    ("UN News", "rss", "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "n/a", "official"),
    # --- Europe ---
    ("Deutsche Welle", "rss", "https://rss.dw.com/rdf/rss-en-world", "center", "reported"),
    ("France 24", "rss", "https://www.france24.com/en/rss", "center", "reported"),
    ("El País (EN)", "rss", "https://english.elpais.com/rss/elpais/inenglish.xml", "left", "reported"),
    ("Le Monde (EN)", "rss", "https://www.lemonde.fr/en/rss/une.xml", "left", "reported"),
    ("The Local Europe", "rss", "https://www.thelocal.com/feeds/rss.php", "center", "reported"),
    ("EUobserver", "rss", "https://euobserver.com/rss.xml", "center", "reported"),
    ("Balkan Insight", "rss", "https://balkaninsight.com/feed/", "center", "reported"),
    ("The Irish Times World", "rss", "https://www.irishtimes.com/cmlink/news-1.1319192", "center", "reported"),
    ("The Guardian Europe", "rss", "https://www.theguardian.com/world/europe-news/rss", "left", "reported"),
    ("Notes from Poland", "rss", "https://notesfrompoland.com/feed/", "center", "reported"),
    ("Swissinfo", "rss", "https://www.swissinfo.ch/eng/rss", "center", "reported"),
    ("The Moscow Times", "rss", "https://www.themoscowtimes.com/rss/news", "center", "reported"),
    ("Novaya Gazeta Europe", "rss", "https://novayagazeta.eu/feed/rss", "center", "reported"),
    # --- Middle East / North Africa ---
    ("Middle East Eye", "rss", "https://www.middleeasteye.net/rss", "left", "reported"),
    ("Al-Monitor", "rss", "https://www.al-monitor.com/rss", "center", "reported"),
    ("The Jerusalem Post", "rss", "https://www.jpost.com/rss/rssfeedsheadlines.aspx", "center", "reported"),
    ("The New Arab", "rss", "https://www.newarab.com/rss", "left", "reported"),
    ("Arab News", "rss", "https://www.arabnews.com/rss.xml", "center", "reported"),
    ("Al-Ahram Weekly", "rss", "https://english.ahram.org.eg/rss/1.aspx", "center", "reported"),
    ("Tehran Times", "rss", "https://www.tehrantimes.com/rss", "n/a", "reported"),
    ("Rudaw (Kurdistan)", "rss", "https://www.rudaw.net/rss/english", "center", "reported"),
    ("Middle East Monitor", "rss", "https://www.middleeastmonitor.com/feed/", "left", "reported"),
    # --- Africa ---
    ("Africanews", "rss", "https://www.africanews.com/feed/rss", "center", "reported"),
    ("Daily Maverick", "rss", "https://www.dailymaverick.co.za/dmrss/", "center", "reported"),
    ("The East African", "rss", "https://www.theeastafrican.co.ke/rss", "center", "reported"),
    ("Premium Times (Nigeria)", "rss", "https://www.premiumtimesng.com/feed", "center", "reported"),
    ("Mail & Guardian (SA)", "rss", "https://mg.co.za/feed/", "center", "reported"),
    ("The Citizen (Tanzania)", "rss", "https://www.thecitizen.co.tz/tanzania/rss", "center", "reported"),
    ("Nation Africa (Kenya)", "rss", "https://nation.africa/kenya/rss", "center", "reported"),
    ("News24 (SA)", "rss", "https://feeds.24.com/articles/news24/TopStories/rss", "center", "reported"),
    ("Ethiopia Reporter", "rss", "https://www.thereporterethiopia.com/feed/", "center", "reported"),
    ("Sudan Tribune", "rss", "https://sudantribune.com/feed/", "center", "reported"),
    # --- South & Central Asia ---
    ("The Hindu Intl", "rss", "https://www.thehindu.com/news/international/feeder/default.rss", "center", "reported"),
    ("Hindustan Times World", "rss", "https://www.hindustantimes.com/feeds/rss/world-news/rssfeed.xml", "center", "reported"),
    ("Dawn (Pakistan)", "rss", "https://www.dawn.com/feeds/home", "center", "reported"),
    ("The Express Tribune", "rss", "https://tribune.com.pk/feed/home", "center", "reported"),
    ("The Daily Star (Bangladesh)", "rss", "https://www.thedailystar.net/frontpage/rss.xml", "center", "reported"),
    ("Kathmandu Post", "rss", "https://kathmandupost.com/rss", "center", "reported"),
    ("The Diplomat (Asia)", "rss", "https://thediplomat.com/feed/", "center", "reported"),
    ("Eurasianet", "rss", "https://eurasianet.org/rss.xml", "center", "reported"),
    # --- East & Southeast Asia ---
    ("NHK World", "rss", "https://www3.nhk.or.jp/nhkworld/en/news/feeds/", "center", "reported"),
    ("Japan Times", "rss", "https://www.japantimes.co.jp/feed/", "center", "reported"),
    ("The Straits Times World", "rss", "https://www.straitstimes.com/news/world/rss.xml", "center", "reported"),
    ("Channel NewsAsia", "rss", "https://www.channelnewsasia.com/rssfeeds/8395986", "center", "reported"),
    ("The Jakarta Post", "rss", "https://www.thejakartapost.com/rss", "center", "reported"),
    ("Bangkok Post", "rss", "https://www.bangkokpost.com/rss/data/topstories.xml", "center", "reported"),
    ("Nikkei Asia", "rss", "https://asia.nikkei.com/rss/feed/nar", "center", "reported"),
    ("Taipei Times", "rss", "https://www.taipeitimes.com/xml/index.rss", "center", "reported"),
    ("Global Times (China)", "rss", "https://www.globaltimes.cn/rss/outbrain.xml", "right", "reported"),
    ("The Korea Times", "rss", "https://www.koreatimes.co.kr/www/rss/world.xml", "center", "reported"),
    ("Manila Bulletin", "rss", "https://mb.com.ph/feed", "center", "reported"),
    ("VnExpress International", "rss", "https://e.vnexpress.net/rss/news.rss", "center", "reported"),
    # --- Americas (Latin) ---
    ("MercoPress", "rss", "https://en.mercopress.com/rss/", "center", "reported"),
    ("Buenos Aires Times", "rss", "https://www.batimes.com.ar/feed", "center", "reported"),
    ("The Rio Times", "rss", "https://www.riotimesonline.com/feed/", "center", "reported"),
    ("Mexico News Daily", "rss", "https://mexiconewsdaily.com/feed/", "center", "reported"),
    ("Colombia Reports", "rss", "https://colombiareports.com/feed/", "center", "reported"),
    ("teleSUR English", "rss", "https://www.telesurenglish.net/rss/RssAllContent.xml", "left", "reported"),
    ("Buenos Aires Herald", "rss", "https://buenosairesherald.com/feed", "center", "reported"),
    # --- Oceania ---
    ("ABC News (Australia)", "rss", "https://www.abc.net.au/news/feed/2942460/rss.xml", "center", "reported"),
    ("The Sydney Morning Herald World", "rss", "https://www.smh.com.au/rss/world.xml", "center", "reported"),
    ("RNZ (New Zealand) World", "rss", "https://www.rnz.co.nz/rss/world.xml", "center", "reported"),
    ("The Guardian Australia", "rss", "https://www.theguardian.com/australia-news/rss", "left", "reported"),
    # --- defense / security / OSINT / economics ---
    ("War on the Rocks", "rss", "https://warontherocks.com/feed/", "center", "reported"),
    ("Defense One", "rss", "https://www.defenseone.com/rss/all/", "center", "reported"),
    ("Janes Defence", "rss", "https://www.janes.com/feeds/news", "center", "reported"),
    ("The War Zone", "rss", "https://www.twz.com/feed", "center", "reported"),
    ("Naval News", "rss", "https://www.navalnews.com/feed/", "center", "reported"),
    ("Bellingcat", "rss", "https://www.bellingcat.com/feed/", "center", "reported"),
    ("Council on Foreign Relations", "rss", "https://www.cfr.org/rss-feeds", "center", "reported"),
    ("Carnegie Endowment", "rss", "https://carnegieendowment.org/rss/solr?maxrows=20", "center", "reported"),
    ("Reuters Markets (proxy)", "rss", "https://feeds.marketwatch.com/marketwatch/topstories/", "center", "reported"),
    ("CNBC World", "rss", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362", "center", "reported"),
    ("Financial Times World (proxy)", "rss", "https://www.ft.com/world?format=rss", "center", "reported"),
    ("Bloomberg Politics (proxy)", "rss", "https://feeds.bloomberg.com/politics/news.rss", "center", "reported"),
    ("OilPrice", "rss", "https://oilprice.com/rss/main", "center", "reported"),
    ("The Kyiv Independent (dup-safe)", "rss", "https://kyivindependent.com/feed/", "center", "reported"),
    ("ReliefWeb Headlines", "rss", "https://reliefweb.int/headlines/rss.xml", "n/a", "official"),
    ("ACLED Blog", "rss", "https://acleddata.com/feed/", "n/a", "reported"),
    ("Crisis Group", "rss", "https://www.crisisgroup.org/rss.xml", "center", "reported"),
    ("OCHA", "rss", "https://www.unocha.org/rss.xml", "n/a", "official"),
    ("WHO News", "rss", "https://www.who.int/rss-feeds/news-english.xml", "n/a", "official"),
    ("NASA Earth", "rss", "https://www.nasa.gov/rss/dyn/earth.rss", "n/a", "official"),
]

# v6 §2 — sources removed from the product entirely. Their rows persist for
# fact-chain attribution (v1 §5.9: history is never deleted) but are flagged
# is_active=0 so no polling thread ever starts for them again.
RETIRED_SOURCES = {"GDELT DOC 2.0", "GDELT Cloud", "GDELT Events (CAMEO)"}

# v5 §5 — reliability tiers so low-tier volume (raw GDELT Events) never drowns
# out high-tier signal in correlation clustering / instability. By name where
# it matters; default by type otherwise (see _reliability_tier).
SOURCE_TIER_BY_NAME = {
    # high: first-tier wires, national broadcasters, official primary sources,
    # vetted OSINT
    "BBC World": "high", "AP Top News": "high", "AFP (via Google News)": "high",
    "Reuters (via Google News)": "high", "Reuters World (Google News)": "high",
    "NPR": "high", "The Guardian World": "high", "Deutsche Welle": "high",
    "France 24": "high", "France24 Africa": "high", "NHK World": "high",
    "Al Jazeera": "high", "Le Monde International": "high",
    "White House": "high", "EU Commission": "high", "UN News": "high",
    "US Dept of Defense": "high", "US State Department": "high",
    "UK Government": "high", "NATO News": "high", "Russia MFA": "high",
    "Ukraine MFA": "high", "Israel MFA": "high",
    "US Federal Reserve": "high", "European Central Bank": "high",
    "Bank of England": "high", "IMF Press": "high", "World Bank News": "high",
    "US BLS Economic Releases": "high", "USGS Earthquakes": "high",
    "NASA FIRMS Wildfires": "high", "Smithsonian Volcanism": "high",
    "ISW Ukraine Updates": "high", "Liveuamap": "high",
    # v6 §2 replacement coverage
    "Politico Europe": "high", "The Diplomat": "high", "Defense News": "high",
    "Breaking Defense": "high", "ReliefWeb Updates": "high", "RFE/RL": "high",
    "Meduza (EN)": "high", "Ukrainska Pravda": "high", "Times of Israel": "high",
    # low: structurally noisy / unvetted-at-scale
    "Mastodon": "low", "Bluesky": "low", "Reddit": "low",
    "Wikipedia Pageview Spikes": "low",
    # medium: everything else (regional wires, state outlets) via default
}


def _reliability_tier(name: str, stype: str) -> str:
    """v5 §5 — resolve a source's reliability tier: explicit by name, else a
    type-based default (structured hazards high, social low, rest medium)."""
    if name in SOURCE_TIER_BY_NAME:
        return SOURCE_TIER_BY_NAME[name]
    if stype in ("usgs", "firms", "volcano"):
        return "high"
    if stype in ("mastodon", "bluesky", "reddit"):
        return "low"
    return "medium"

_INTERVAL_KEY = {"rss": "rss",
                 "usgs": "usgs", "market": "market", "reddit": "reddit",
                 "firms": "firms", "volcano": "volcano", "wikipedia": "wikipedia",
                 "wiki_views": "wiki_views", "mastodon": "mastodon",
                 "bluesky": "bluesky", "opensky": "opensky", "acled": "acled"}

# v6 §10 — conflict-relevant local-language outlets poll on a faster cadence
# than the default rss interval so local reporting lands first
FAST_POLL_SOURCES = {"Ukrainska Pravda": 180, "Suspilne Ukraine": 180,
                     "Meduza (RU)": 300, "Times of Israel": 180,
                     "Ynet News": 300, "Al Mayadeen (EN)": 300,
                     "Kyiv Independent": 180, "Liveuamap": 180}


def interval_for(source_type: str) -> int:
    return int(cfg("ingestion_intervals_seconds", _INTERVAL_KEY[source_type]))


def seed_sources() -> int:
    added = 0
    # v4 §22 — per-source-type attribution metadata lives on the row, so the
    # credits page never needs a hand-edit when a source is added
    from ..api.routes_v4 import TYPE_ATTRIBUTION
    with write_tx() as conn:
        for name, stype, url, leaning, kind in SOURCES:
            # v6 §10 — conflict-relevant local outlets poll faster than default
            interval = FAST_POLL_SOURCES.get(name, interval_for(stype))
            attribution = TYPE_ATTRIBUTION.get(stype, ("", ""))[1] or None
            tier = _reliability_tier(name, stype)   # v5 §5
            existing = conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE sources SET url = ?, leaning = ?, poll_interval_seconds = ?,"
                    " kind = ?, attribution = ?, reliability_tier = ?, is_active = 1"
                    " WHERE id = ?",
                    (url, leaning, interval, kind, attribution, tier, existing["id"]))
            else:
                conn.execute(
                    "INSERT INTO sources (id, name, type, url, leaning, poll_interval_seconds,"
                    " kind, attribution, reliability_tier) VALUES (?,?,?,?,?,?,?,?,?)",
                    (new_id(), name, stype, url, leaning, interval, kind, attribution, tier))
                added += 1
        # v6 §2 — retire removed sources in place: rows (and their facts) stay,
        # polling stops permanently
        for name in RETIRED_SOURCES:
            conn.execute("UPDATE sources SET is_active = 0, health_status = 'down',"
                         " last_error = 'retired (v6 §2 — source removed)'"
                         " WHERE name = ?", (name,))
    return added


def get_synthetic_source_id() -> str:
    """Attribution is schema-enforced even for synthetic rows (Section 12)."""
    row = query_one("SELECT id FROM sources WHERE type = 'synthetic'")
    if row:
        return row["id"]
    sid = new_id()
    with write_tx() as conn:
        conn.execute(
            "INSERT INTO sources (id, name, type, url, leaning, poll_interval_seconds,"
            " health_status) VALUES (?,?,?,?,?,?, 'ok')",
            (sid, "Synthetic Dataset Generator", "synthetic",
             "https://github.com/ishaanbusireddy/GlobeGrid", "n/a", 0))
    return sid
