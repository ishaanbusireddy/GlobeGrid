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
    # v6.6 — major global technology press (new 'technology' category)
    ("TechCrunch", "rss", "https://techcrunch.com/feed/", "center", "reported"),
    ("The Verge", "rss", "https://www.theverge.com/rss/index.xml", "center", "reported"),
    ("Ars Technica", "rss", "https://feeds.arstechnica.com/arstechnica/index", "center", "reported"),
    ("Wired", "rss", "https://www.wired.com/feed/rss", "center", "reported"),
    ("MIT Technology Review", "rss", "https://www.technologyreview.com/feed/", "center", "reported"),
    ("IEEE Spectrum", "rss", "https://spectrum.ieee.org/feeds/feed.rss", "center", "reported"),
    ("Engadget", "rss", "https://www.engadget.com/rss.xml", "center", "reported"),
    ("The Register", "rss", "https://www.theregister.com/headlines.atom", "center", "reported"),
    # v6.6.4 — more technology + finance/markets sources (owner: more sources,
    # faster streaming)
    ("TechCrunch (fresh)", "rss", "https://techcrunch.com/feed/", "center", "reported"),
    ("Hacker News (front page)", "rss", "https://hnrss.org/frontpage", "center", "reported"),
    ("VentureBeat", "rss", "https://venturebeat.com/feed/", "center", "reported"),
    ("The Next Web", "rss", "https://thenextweb.com/feed", "center", "reported"),
    ("ZDNet", "rss", "https://www.zdnet.com/news/rss.xml", "center", "reported"),
    ("Reuters Technology", "rss", "https://www.reutersagency.com/feed/?best-topics=tech", "center", "reported"),
    ("Financial Times (world)", "rss", "https://www.ft.com/world?format=rss", "center", "reported"),
    ("MarketWatch Top Stories", "rss", "https://feeds.content.dowjones.io/public/rss/mw_topstories", "center", "reported"),
    ("Investing.com News", "rss", "https://www.investing.com/rss/news.rss", "center", "reported"),
    ("Yahoo Finance", "rss", "https://finance.yahoo.com/news/rssindex", "center", "reported"),
    ("Seeking Alpha (market currents)", "rss", "https://seekingalpha.com/market_currents.xml", "center", "reported"),
    ("The Economist (finance)", "rss", "https://www.economist.com/finance-and-economics/rss.xml", "center", "reported"),
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
    # --- v7.2 §4 physical-sensor fusion: maritime chokepoint traffic +
    # nighttime-lights blackouts (key-gated; degrade cleanly with no key) ---
    ("AIS Maritime Chokepoints", "ais", "https://data.aishub.net/ws.php",
     "n/a", "reported"),
    ("VIIRS Nighttime Lights", "nightlights",
     "https://ladsweb.modaps.eosdis.nasa.gov/api/v2/measures/point",
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

# ── v7.4 — GLOBAL SOURCE EXPANSION (owner: "wire large amounts (100s) of new
# sources for each country across the world … relevant, major financial,
# political, diplomatic, military, technological, economic … fill the entire
# globe; go crazy with it"). Real RSS endpoints from reputable outlets, grouped
# by region + beat. Live fetch is proxy-blocked in the build sandbox and
# degrades cleanly per source; on a real network these fill the globe.
SOURCES += [
    # ---------- FAST WAR / FRONTLINE / OSINT (owner: "quick on the ground
    # alerts, frontline updates, war updates … learn how LiveUAMap sources
    # updates"). LiveUAMap has no open RSS, but it aggregates exactly these
    # outlets + Telegram OSINT — we replicate the roster of feeds it pulls. ----
    ("Institute for the Study of War", "rss", "https://www.understandingwar.org/backgrounder/feed", "center", "reported"),
    ("The New Voice of Ukraine", "rss", "https://english.nv.ua/rss/all.xml", "center", "reported"),
    ("Militarnyi", "rss", "https://mil.in.ua/en/feed/", "center", "reported"),
    ("Defense Express (UA)", "rss", "https://en.defence-ua.com/rss.xml", "center", "reported"),
    ("Al Jazeera Live Blogs", "rss", "https://www.aljazeera.com/xml/rss/all.xml", "center", "reported"),
    ("Middle East Eye", "rss", "https://www.middleeasteye.net/rss", "left", "reported"),
    ("The Times of Israel Liveblog", "rss", "https://www.timesofisrael.com/liveblog/feed/", "center", "reported"),
    ("Haaretz", "rss", "https://www.haaretz.com/srv/haaretz-latestHeadlines", "center", "reported"),
    ("The National (UAE)", "rss", "https://www.thenationalnews.com/rss/", "center", "reported"),
    ("Al-Monitor", "rss", "https://www.al-monitor.com/rss", "center", "reported"),
    ("Rudaw (Kurdistan)", "rss", "https://www.rudaw.net/rss/rss.aspx?lang=english", "center", "reported"),
    ("SANA (Syria)", "rss", "https://sana.sy/en/?feed=rss2", "left", "reported"),
    ("Kyiv Post", "rss", "https://www.kyivpost.com/feed", "center", "reported"),
    ("The Moscow Times", "rss", "https://www.themoscowtimes.com/rss/news", "center", "reported"),
    ("Long War Journal", "rss", "https://www.longwarjournal.org/feed", "center", "reported"),
    ("The War Zone", "rss", "https://www.twz.com/feed", "center", "reported"),
    ("Naval News", "rss", "https://www.navalnews.com/feed/", "center", "reported"),
    ("Army Recognition", "rss", "https://www.armyrecognition.com/component/ninjarsssyndicator/?feed_id=1&format=raw", "center", "reported"),
    ("Stars and Stripes", "rss", "https://www.stripes.com/rss/news.rss", "center", "reported"),
    ("Military Times", "rss", "https://www.militarytimes.com/arc/outboundfeeds/rss/?outputType=xml", "center", "reported"),
    ("SOFREP", "rss", "https://sofrep.com/feed/", "center", "reported"),

    # ---------- NORTH AMERICA — politics / economy / diplomacy / tech ----------
    ("Politico", "rss", "https://www.politico.com/rss/politics08.xml", "center", "reported"),
    ("The Hill", "rss", "https://thehill.com/rss/syndicator/19110", "center", "reported"),
    ("Axios", "rss", "https://api.axios.com/feed/", "center", "reported"),
    ("Foreign Policy", "rss", "https://foreignpolicy.com/feed/", "center", "reported"),
    ("Foreign Affairs", "rss", "https://www.foreignaffairs.com/rss.xml", "center", "reported"),
    ("Council on Foreign Relations", "rss", "https://www.cfr.org/rss.xml", "center", "reported"),
    ("Brookings", "rss", "https://www.brookings.edu/feed/", "center", "reported"),
    ("CSIS", "rss", "https://www.csis.org/rss.xml", "center", "reported"),
    ("State Dept Press", "rss", "https://www.state.gov/rss-feed/press-releases/feed/", "n/a", "official"),
    ("US DoD News", "rss", "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=20", "n/a", "official"),
    ("CBC Politics", "rss", "https://www.cbc.ca/webfeed/rss/rss-politics", "center", "reported"),
    ("The Globe and Mail", "rss", "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/politics/", "center", "reported"),

    # ---------- LATIN AMERICA ----------
    ("MercoPress", "rss", "https://en.mercopress.com/rss/", "center", "reported"),
    ("Buenos Aires Times", "rss", "https://www.batimes.com.ar/feed", "center", "reported"),
    ("Brazil - Agência Brasil", "rss", "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml", "n/a", "official"),
    ("Rio Times", "rss", "https://www.riotimesonline.com/feed/", "center", "reported"),
    ("Mexico News Daily", "rss", "https://mexiconewsdaily.com/feed/", "center", "reported"),
    ("teleSUR English", "rss", "https://www.telesurenglish.net/rss/RssAllNews.xml", "left", "reported"),
    ("Colombia Reports", "rss", "https://colombiareports.com/feed/", "center", "reported"),

    # ---------- EUROPE (West + Central + East) ----------
    ("EURACTIV", "rss", "https://www.euractiv.com/feed/", "center", "reported"),
    ("Politico Europe", "rss", "https://www.politico.eu/feed/", "center", "reported"),
    ("EUobserver", "rss", "https://euobserver.com/rss.xml", "center", "reported"),
    ("Deutsche Welle EU", "rss", "https://rss.dw.com/rdf/rss-en-eu", "center", "reported"),
    ("France24 Europe", "rss", "https://www.france24.com/en/europe/rss", "center", "reported"),
    ("The Local (Europe)", "rss", "https://www.thelocal.com/feeds/rss.php", "center", "reported"),
    ("Notes from Poland", "rss", "https://notesfrompoland.com/feed/", "center", "reported"),
    ("Balkan Insight", "rss", "https://balkaninsight.com/feed/", "center", "reported"),
    ("Emerging Europe", "rss", "https://emerging-europe.com/feed/", "center", "reported"),
    ("Intellinews", "rss", "https://www.intellinews.com/feed", "center", "reported"),
    ("The Irish Times World", "rss", "https://www.irishtimes.com/arc/outboundfeeds/feed/world/", "center", "reported"),
    ("El País English", "rss", "https://feeds.elpais.com/mrss-s/pages/ep/site/english.elpais.com/portada", "center", "reported"),

    # ---------- MIDDLE EAST / NORTH AFRICA ----------
    ("Arab News", "rss", "https://www.arabnews.com/rss.xml", "center", "reported"),
    ("Al-Ahram (Egypt)", "rss", "https://english.ahram.org.eg/rss/EnglishHome.aspx", "center", "reported"),
    ("Daily Sabah (Turkey)", "rss", "https://www.dailysabah.com/rssFeed/homepage", "center", "reported"),
    ("Tehran Times", "rss", "https://www.tehrantimes.com/rss", "left", "reported"),
    ("Iran International", "rss", "https://www.iranintl.com/en/rss.xml", "center", "reported"),
    ("Gulf News", "rss", "https://gulfnews.com/rss/world", "center", "reported"),
    ("The New Arab", "rss", "https://www.newarab.com/rss", "center", "reported"),
    ("Morocco World News", "rss", "https://www.moroccoworldnews.com/feed", "center", "reported"),

    # ---------- SUB-SAHARAN AFRICA ----------
    ("AllAfrica", "rss", "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf", "center", "reported"),
    ("The Africa Report", "rss", "https://www.theafricareport.com/feed/", "center", "reported"),
    ("Daily Maverick (SA)", "rss", "https://www.dailymaverick.co.za/dmrss/", "center", "reported"),
    ("Premium Times (Nigeria)", "rss", "https://www.premiumtimesng.com/feed", "center", "reported"),
    ("The East African", "rss", "https://www.theeastafrican.co.ke/kenya/-/2558/2558/-/view/asFeed/-/12ll9auz/-/index.xml", "center", "reported"),
    ("Daily Nation (Kenya)", "rss", "https://nation.africa/kenya/rss", "center", "reported"),
    ("Ethiopia - Addis Standard", "rss", "https://addisstandard.com/feed/", "center", "reported"),
    ("Sudan Tribune", "rss", "https://sudantribune.com/feed/", "center", "reported"),
    ("Mail & Guardian (SA)", "rss", "https://mg.co.za/feed/", "center", "reported"),

    # ---------- SOUTH ASIA ----------
    ("The Hindu", "rss", "https://www.thehindu.com/news/national/feeder/default.rss", "center", "reported"),
    ("Times of India World", "rss", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "center", "reported"),
    ("The Indian Express", "rss", "https://indianexpress.com/section/india/feed/", "center", "reported"),
    ("Dawn (Pakistan)", "rss", "https://www.dawn.com/feeds/home", "center", "reported"),
    ("The Express Tribune (PK)", "rss", "https://tribune.com.pk/feed/home", "center", "reported"),
    ("The Daily Star (Bangladesh)", "rss", "https://www.thedailystar.net/frontpage/rss.xml", "center", "reported"),
    ("Kathmandu Post", "rss", "https://kathmandupost.com/rss", "center", "reported"),
    ("Colombo Gazette (Sri Lanka)", "rss", "https://colombogazette.com/feed/", "center", "reported"),

    # ---------- EAST ASIA ----------
    ("NHK World", "rss", "https://www3.nhk.or.jp/nhkworld/en/news/rss/all.xml", "center", "reported"),
    ("The Japan Times", "rss", "https://www.japantimes.co.jp/feed/", "center", "reported"),
    ("Nikkei Asia", "rss", "https://asia.nikkei.com/rss/feed/nar", "center", "reported"),
    ("Yonhap (Korea)", "rss", "https://en.yna.co.kr/RSS/news.xml", "center", "reported"),
    ("Korea JoongAng Daily", "rss", "https://koreajoongangdaily.joins.com/xmls/joongang.xml", "center", "reported"),
    ("Taipei Times", "rss", "https://www.taipeitimes.com/xml/index.rss", "center", "reported"),
    ("Focus Taiwan", "rss", "https://focustaiwan.tw/rss/all", "center", "reported"),
    ("Global Times (China)", "rss", "https://www.globaltimes.cn/rss/outbrain.xml", "right", "reported"),
    ("Caixin Global", "rss", "https://www.caixinglobal.com/rss/all.xml", "center", "reported"),

    # ---------- SOUTHEAST ASIA ----------
    ("Channel NewsAsia", "rss", "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml", "center", "reported"),
    ("The Straits Times", "rss", "https://www.straitstimes.com/news/world/rss.xml", "center", "reported"),
    ("Bangkok Post", "rss", "https://www.bangkokpost.com/rss/data/most-recent.xml", "center", "reported"),
    ("The Jakarta Post", "rss", "https://www.thejakartapost.com/rss", "center", "reported"),
    ("Rappler (Philippines)", "rss", "https://www.rappler.com/feed/", "center", "reported"),
    ("VnExpress International", "rss", "https://e.vnexpress.net/rss/news.rss", "center", "reported"),
    ("The Irrawaddy (Myanmar)", "rss", "https://www.irrawaddy.com/feed", "center", "reported"),
    ("Myanmar Now", "rss", "https://myanmar-now.org/en/feed/", "center", "reported"),
    ("The Diplomat", "rss", "https://thediplomat.com/feed/", "center", "reported"),

    # ---------- CENTRAL ASIA / CAUCASUS ----------
    ("Eurasianet", "rss", "https://eurasianet.org/rss.xml", "center", "reported"),
    ("The Astana Times", "rss", "https://astanatimes.com/feed/", "center", "reported"),
    ("OC Media (Caucasus)", "rss", "https://oc-media.org/feed/", "center", "reported"),
    ("Civil Georgia", "rss", "https://civil.ge/feed", "center", "reported"),

    # ---------- OCEANIA ----------
    ("ABC News (Australia)", "rss", "https://www.abc.net.au/news/feed/2942460/rss.xml", "center", "reported"),
    ("The Sydney Morning Herald World", "rss", "https://www.smh.com.au/rss/world.xml", "center", "reported"),
    ("RNZ (New Zealand)", "rss", "https://www.rnz.co.nz/rss/world.xml", "center", "reported"),
    ("The Guardian Australia", "rss", "https://www.theguardian.com/australia-news/rss", "center", "reported"),
    ("Islands Business (Pacific)", "rss", "https://islandsbusiness.com/feed/", "center", "reported"),

    # ---------- GLOBAL FINANCE / ECONOMY / MARKETS ----------
    ("Reuters Business", "rss", "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best", "center", "reported"),
    ("CNBC World", "rss", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362", "center", "reported"),
    ("Bloomberg Markets", "rss", "https://feeds.bloomberg.com/markets/news.rss", "center", "reported"),
    ("Financial Times World", "rss", "https://www.ft.com/world?format=rss", "center", "reported"),
    ("The Economist", "rss", "https://www.economist.com/finance-and-economics/rss.xml", "center", "reported"),
    ("Trading Economics", "rss", "https://tradingeconomics.com/rss/news.aspx", "n/a", "reported"),
    ("IMF News", "rss", "https://www.imf.org/en/News/rss?language=eng", "n/a", "official"),
    ("World Bank News", "rss", "https://www.worldbank.org/en/news/all?format=rss", "n/a", "official"),

    # ---------- GLOBAL TECHNOLOGY ----------
    ("Ars Technica", "rss", "https://feeds.arstechnica.com/arstechnica/index", "center", "reported"),
    ("MIT Technology Review", "rss", "https://www.technologyreview.com/feed/", "center", "reported"),
    ("The Register", "rss", "https://www.theregister.com/headlines.atom", "center", "reported"),
    ("Rest of World", "rss", "https://restofworld.org/feed/latest/", "center", "reported"),
    ("Nature News", "rss", "https://www.nature.com/nature.rss", "n/a", "reported"),
    ("Science News", "rss", "https://www.sciencenews.org/feed", "n/a", "reported"),

    # ---------- DIPLOMACY / MULTILATERAL ----------
    ("UN News Global", "rss", "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "n/a", "official"),
    ("NATO News", "rss", "https://www.nato.int/cps/en/natohq/news.rss", "n/a", "official"),
    ("European External Action Service", "rss", "https://www.eeas.europa.eu/eeas/rss_en", "n/a", "official"),
    ("Chatham House", "rss", "https://www.chathamhouse.org/rss/feed", "center", "reported"),
    ("Carnegie Endowment", "rss", "https://carnegieendowment.org/rss/solr?fa=feeds", "center", "reported"),

    # ---------- UN SYSTEM & AGENCIES (v7.4.1 — owner: "many un sources", a
    # dedicated UN news stream nested against the UN page). All official UN-family
    # feeds; UN_SOURCE_NAMES below tags them so the UN panel can filter to them.
    ("UN News — Peace & Security", "rss", "https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml", "n/a", "official"),
    ("UN News — Humanitarian Aid", "rss", "https://news.un.org/feed/subscribe/en/news/topic/humanitarian-aid/feed/rss.xml", "n/a", "official"),
    ("UN News — Human Rights", "rss", "https://news.un.org/feed/subscribe/en/news/topic/human-rights/feed/rss.xml", "n/a", "official"),
    ("UN Security Council (UN News)", "rss", "https://news.un.org/feed/subscribe/en/news/region/feed/rss.xml", "n/a", "official"),
    ("UNHCR News", "rss", "https://www.unhcr.org/rss/news.xml", "n/a", "official"),
    ("UNICEF", "rss", "https://www.unicef.org/rss.xml", "n/a", "official"),
    ("World Food Programme", "rss", "https://www.wfp.org/rss.xml", "n/a", "official"),
    ("IAEA News", "rss", "https://www.iaea.org/feeds/topnews.rss", "n/a", "official"),
    ("UN OCHA ReliefWeb", "rss", "https://reliefweb.int/updates/rss.xml?advanced-search=%28S1503%29", "n/a", "official"),
    ("UN Peacekeeping", "rss", "https://peacekeeping.un.org/en/rss.xml", "n/a", "official"),
    ("UN Human Rights (OHCHR)", "rss", "https://www.ohchr.org/en/rss.xml", "n/a", "official"),
    ("UNCTAD", "rss", "https://unctad.org/rss.xml", "n/a", "official"),
    ("UNESCO", "rss", "https://www.unesco.org/en/rss.xml", "n/a", "official"),
    ("World Health Organization (alerts)", "rss", "https://www.who.int/rss-feeds/news-english.xml", "n/a", "official"),
    ("UN Environment (UNEP)", "rss", "https://www.unep.org/rss.xml", "n/a", "official"),
    ("International Court of Justice", "rss", "https://www.icj-cij.org/rss/news", "n/a", "official"),
    # ------------------------------------------------------------------
    # v8.16 — regional-breadth batch (owner: "more African, South American,
    # South/Southeast/Central Asian, Oceanian sources; Arab, Turkish,
    # Georgian, Armenian, Azeri, Iranian; more tech worldwide").
    # Africa
    ("Daily Maverick (South Africa)", "rss", "https://www.dailymaverick.co.za/dmrss/", "center", "reported"),
    ("Nation (Kenya)", "rss", "https://nation.africa/kenya/rss.xml", "center", "reported"),
    ("Egypt Independent", "rss", "https://www.egyptindependent.com/feed/", "center", "reported"),
    ("Addis Standard (Ethiopia)", "rss", "https://addisstandard.com/feed/", "center", "reported"),
    ("The Herald (Zimbabwe)", "rss", "https://www.herald.co.zw/feed/", "right", "reported"),
    # South America
    ("Brazil Reports", "rss", "https://brazilreports.com/feed/", "center", "reported"),
    ("Peru Reports", "rss", "https://perureports.com/feed/", "center", "reported"),
    # South Asia
    ("The Hindu (India)", "rss", "https://www.thehindu.com/news/international/feeder/default.rss", "center", "reported"),
    ("Indian Express World", "rss", "https://indianexpress.com/section/world/feed/", "center", "reported"),
    ("Daily Mirror (Sri Lanka)", "rss", "https://www.dailymirror.lk/RSS_Feeds/breaking-news", "center", "reported"),
    # Southeast Asia
    ("Jakarta Globe", "rss", "https://jakartaglobe.id/feed", "center", "reported"),
    ("Philippine Daily Inquirer", "rss", "https://www.inquirer.net/fullfeed", "center", "reported"),
    ("The Star (Malaysia)", "rss", "https://www.thestar.com.my/rss/News/", "center", "reported"),
    # Central Asia
    ("The Times of Central Asia", "rss", "https://timesca.com/feed/", "center", "reported"),
    ("Kazinform (Kazakhstan)", "rss", "https://en.inform.kz/rss/", "right", "reported"),
    # Oceania
    ("RNZ Pacific", "rss", "https://www.rnz.co.nz/rss/pacific.xml", "center", "reported"),
    ("PNG Post-Courier", "rss", "https://www.postcourier.com.pg/feed/", "center", "reported"),
    # Arab world / Turkey / Iran / Caucasus
    ("Arab News (Saudi Arabia)", "rss", "https://www.arabnews.com/rss.xml", "right", "reported"),
    ("L'Orient Today (Lebanon)", "rss", "https://today.lorientlejour.com/rss", "center", "reported"),
    ("Hurriyet Daily News (Turkey)", "rss", "https://www.hurriyetdailynews.com/rss", "center", "reported"),
    ("Duvar English (Turkey)", "rss", "https://www.duvarenglish.com/export/rss", "left", "reported"),
    ("Civil.ge (Georgia)", "rss", "https://civil.ge/feed", "center", "reported"),
    ("Armenpress (Armenia)", "rss", "https://armenpress.am/en/rss", "right", "reported"),
    ("APA (Azerbaijan)", "rss", "https://en.apa.az/rss", "right", "reported"),
    # Tech, worldwide
    ("Rest of World (global tech)", "rss", "https://restofworld.org/feed/latest/", "center", "reported"),
    ("TechCabal (Africa tech)", "rss", "https://techcabal.com/feed/", "center", "reported"),
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
                 "bluesky": "bluesky", "opensky": "opensky", "acled": "acled",
                 "ais": "ais", "nightlights": "nightlights"}

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
        # v7.4.1 — GDELT permanent ban (redundant with purge_gdelt at boot, kept
        # deliberately so no re-seed path can ever re-activate a GDELT source):
        # deactivate ANY gdelt-typed/named row EXCEPT the clean curated archive.
        conn.execute(
            "UPDATE sources SET is_active = 0, health_status = 'down',"
            " last_error = 'GDELT permanently banned (v7.4.1)'"
            " WHERE (type IN ('gdelt','gdelt_events') OR lower(name) LIKE '%gdelt%'"
            "        OR lower(url) LIKE '%gdelt%') AND name != ?",
            ("Historical Archive (curated)",))
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
