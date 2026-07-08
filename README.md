# GlobeGrid — TalkDiplomacy Live

Cross-stream global event correlation engine with a live 3D map and AI-generated
causal storylines. Ingests news, structured event data, disasters, markets, and
social signal; extracts structured facts into a **permanent fact chain**; detects
when events across different streams — and different points in time — are
connected; and explains what happened and why, with every fact traceable to a
visible, linked source.

Built to the [v1 build manual](docs/talkdiplomacy_live_v1_build_manual.pdf),
[v2 expansion addendum](docs/globegrid_v2_expansion_addendum.pdf),
[v3 legendary-tier manual](docs/globegrid_v3_legendary_manual.pdf),
[v4 polish/accuracy/depth manual](docs/globegrid_v4_build_manual.pdf),
[v5 build manual](docs/globegrid_v5_build_manual.pdf) and
[v6 build manual](docs/globegrid_v6_build_manual.pdf) as a
**zero-install build**: Python standard library only. No PostgreSQL, no pip
install, no npm, no Docker.

**v6.6.6 highlights (current):** a correctness + responsiveness patch.
**Leader, party and country-stat pages no longer hang** — the AI profile is
generated in the background and the page fills instantly (with a curated floor
for major leaders, then AI enrichment merged on top). **Syria's alignments**
now reflect the al-Sharaa government (allies Türkiye/Qatar; rivals Iran, Russia
and Israel). **Pakistan** is now a US ally, and **all NATO members are mutual
allies** (Greece–Türkiye stays a rivalry — a real dispute). **Nagorno-Karabakh**
is gone from disputed territories (resolved), and **Antarctica** is now
clickable — a full page with the Antarctic Treaty and the seven frozen claims.
Two **new audio tracks** (nocturne / storm front) finally show in the picker,
the **live-feed buzz** is fixed, the **globe no longer drifts when idle** (with
an explicit **⟳ spin** toggle instead), **War Mode** gets a themed edge-glow and
auto-exits when you navigate away, the **UNSC page** shows its resolutions, and
an LLM pass corrects mis-placed events on the map.

**v6.6.5 highlights:** comprehensive people & data pages.
**Leader profiles** are now rich even offline — a full biography, ideology,
career and key-policies synthesis is generated from the model's general
knowledge (no Wikipedia extract required), with a robust portrait fallback and
a curated data floor for major figures (al-Sharaa, Zelenskyy, Putin, Xi,
Trump, Modi, Netanyahu, Starmer, Macron), so a leader page is never blank.
**Major political parties** get the same AI-synthesized treatment (ideology,
history, positions, electoral record). The **conflicts directory** splits into
⚔ Conflicts and 🔥 Insurgencies tabs (Balochistan, Kurdish–PKK, Naxalite,
West Papua, Cabo Delgado, ELN Colombia, Sahel). **Country stat cells**
(population, GDP, GDP/capita, HDI, area) are now **clickable** → a drill-down
of distribution, sector composition and growth trajectory. The **UN panel**
gained more landmark resolutions (JCPOA, DPRK sanctions, Libya no-fly), and
two new **audio tracks** (a calm *nocturne* and an aggressive *storm front*)
join the buzz-free preset set.

**v6.6.4 highlights:** a quality-of-life pass. **Disputed
territories** (Crimea, Donetsk, Luhansk, Zaporizhzhia, Kherson, Kashmir,
Taiwan, Western Sahara, Kosovo, **Falklands**) now render as **clickable
markers on the globe** in disputed mode, each opening a context breakdown.
**Diplomatic alignments** gained common-sense rivalries and friendships
(India⇄Pakistan, Armenia⇄Azerbaijan, Israel⇄Iran hostile; India⇄Armenia
friendly, US⇄Armenia no longer hostile). A clean **light mode** joins the
theme set; **Fire Rises** and **New Order** were recolored to mostly-black
neon looks. The **analyst** bursts open from its orb (with open/close sound
cues) and gives more detailed, bullet-heavy answers. The live feed can no
longer be blanked by any map/view mode, constitutional monarchs are no longer
mislabeled as a country's leader (Denmark → the PM, not King Frederik X), US
sports and obscure local news are filtered out, +12 tech/finance sources feed
in faster, and Settings adds a **font-style** selector.

**v6.6.2 highlights:** AI now runs **Ollama-first** — install once,
`ollama pull llama3.1`, and every AI feature (analyst, translation, causal
storylines, briefings, leader-profile synthesis) is free, unlimited and fully
local, with Groq/Gemini/Cerebras/OpenRouter/Claude as automatic cloud
fallbacks if you'd rather use a key. Blocs (NATO, EU, CSTO, Arab League, ASEAN,
African Union, BRICS, OPEC, Five Eyes, QUAD, AUKUS…) now open **full profile
pages** — leader + portrait, purpose & HQ, policies & strategies, aggregate
stats, the full member flag grid, conflicts members are party to, recent
stories, and a **European Parliament hemicycle** for the EU. The **🇺🇳 UN
page** is tabbed (General Assembly, Security Council, WHO, UNESCO… each its
own page) and every resolution's vote can expand to the **full** yes/no/
abstain breakdown, not just the notable names. World leaders get **rich
personal profile pages** (ideology, career history, party history, key
policies — AI-synthesized from Wikipedia, cached) reachable from any portrait
or name chip. An experimental **diplomatic-alignment map** colors every
country's allies/partners/rivals. **Disputed territories** — Crimea, Donetsk,
Luhansk, Zaporizhzhia, Kherson, Kashmir, Taiwan, Western Sahara, Kosovo — are
individually named zones with their own context breakdown. Thematic map modes
now include a **nuclear-arsenal** choropleth (9 nuclear states). A **dynamic
market briefing** tab covers global markets and tentatively forecasts specific
moves grounded in tracked stories ("not financial advice"). Parliamentary
seat-arc graphics cover ~60 legislatures (including one-party/managed states
like Russia's Duma and China's NPC), and countries genuinely without an
elected legislature (Saudi Arabia, UAE, Vatican, post-2021 Afghanistan…)
explain why instead of showing blank. New single-key shortcuts — **F** feed,
**L** language, **C** last-viewed country, **G** globe, **M** 2D map — join
**Ctrl/Cmd+T** theme cycling across 17 themes (including the TNO/HOI4-mod-
style **New Order** and **Fire Rises**). Conflict-tagged stories carry a
clickable **⚔ chip** straight into War Mode, which now genuinely preserves
your accumulated feed on exit; breaking-story pop-ups fire even with the feed
panel closed (togglable in Settings).

**v6.1.1 highlights:** the seven things v6.1 had deferred, now built. The map
labels **countries dynamically** — big ones from orbit, small ones (Bhutan!)
as you zoom in. You can toggle
**several alliances at once**, language/religion map modes now colour by
**family** (Iranian and Indo-Aryan read as related warm reds) with a **hover
tooltip** that names each country's language/religion so no colour key is
needed. There's a **timezone + date-format** setting applied to every
timestamp, the low-power **Tier-3 view groups events into continental boxes**,
and **War Mode** gains a refined shaded frontline (front line + Crimea, not a
rectangle) plus an AI **order-of-battle** — forces, offensives, tactics
evolution and global ramifications.

**v6.1 highlights:** a usability pass on top of v6. Country panels are now
**filled in** — every nation lists its **currency**, and major democracies
get a **parliamentary seat-arc graphic** (party-colored hemicycle). Profiles
feature the **actual leader in charge** (Xi Jinping for China, not the
premier; Putin for Russia). A new **🇺🇳 UN panel** shows the Security Council
and how countries voted on landmark resolutions, drawn as a green/red/grey
**vote hemicycle**. **War Mode** names its sides for real ("Russia & allies"
vs "Ukraine & allies") and lists belligerents then backers (EU, Canada,
NATO members). You can now fly the globe and 2D map with **WASD** (Q/E to
zoom), the thematic **modes bar moved to the bottom** with much brighter
shading, non-state-actor zones render as a **pulsing techno dot-field**
instead of rectangles, and there's a **weekly + monthly briefing** beside the
daily one. The music **plays from the start** (buzz-free ambient, new glacial/
chimey experimental presets; the broken hard-rock preset is gone), the
**analyst has a Stop button** and can't stall forever, translation is far more
robust, and a first-run **"?" help popup** explains the whole thing. A green
**"military"** event category joins the map.

**v6 highlights:** **War Mode** — click any conflict (or the new header
Conflicts directory) and the whole app reframes around it: the camera flies
to a bounding box of the belligerents, countries ring up in side colors,
subfaction control zones draw as established-vs-contested overlays, and the
feed splits into military / civilian / diplomatic / economic tabs. **Thematic
map modes** paint CIA-Factbook-style choropleths — population, area, density,
GDP, GDP per capita, HDI, dominant religion and language — from an
authoritative vendored dataset (never AI-guessed), with subnational overlays
(northern/southern Nigeria, Swiss language regions, Xinjiang, Québec…).
**Site-wide instant translation**: pick a language in the header and feed
content translates on arrival (cached, batched), the wordmark transliterates,
and non-English sources are normalized to English for correlation. Every
country page now carries real stats (area, GDP, GDP/capita, HDI, languages,
religion) and **15 territories** (Greenland, Puerto Rico, Hong Kong…) get
their own pages linked to their sovereign. Stories cluster into named
**narrative threads**; the analyst answers in bullets with an expandable deep
dive, does region deep-dives with linked chips, and can live-verify stale
leadership data via keyless web search. The 2D map was rebuilt on
pre-chunked path tiles (**387ms → 2.9ms per frame, profiled**), the globe
gets a real baked biome terrain texture, the globe never moves on its own
anymore (idle tour stays opt-in), ESC unwinds the UI one layer at a time,
shift+drag selects a region's events, selected countries pulse, GDELT is
retired in favor of 16 higher-quality feeds, regions follow the UN M49
taxonomy, Afghanistan is honestly labeled Taliban-governed, ten new color
themes arrive (14 total), and a **hard rock / metal** audio preset joins a
buzz-free ambient engine.

**v5.1:** the default AI provider is now **Groq** (free, no card required,
~14,400 requests/day) instead of Claude — get a key in seconds at
[console.groq.com/keys](https://console.groq.com/keys) and every AI feature
(causal storylines, debate, briefings, the analyst, translation) works at
zero cost. OpenRouter, Cerebras and Gemini are also wired in as free
alternatives/fallbacks; Claude remains available as a paid upgrade for
higher-quality prose with no daily cap. See `backend/.env.example`.

**v5 highlights:** the interface now speaks **54 languages** with real
right-to-left layout for Arabic, Persian, Urdu and Hebrew (the whole panel
system flips, not just the strings), and ships **four color themes**
(default teal, high-contrast, amber-terminal, colorblind-safe). Sources now
carry an honest **reliability tier** (high / medium / low) that both shows on
every story's source rows and weights the instability index, and new
higher-signal feeds — AP, AFP, Guardian, Deutsche Welle, government/military
and OSINT desks — join the mix. Country flags are now **real images**
(Wikimedia SVGs), never emoji. **Non-state-actor territorial zones** — the
Taliban, the Houthis, Sahel juntas and more — render as translucent overlays
on both the globe and the 2D map. Headlines get tracker/redirect links
stripped, the feed gains sort (newest / oldest / most active) and a
conflict-vs-military development filter, and a **history/archive** view
browses the full permanent fact chain by date and category. The globe gains
crisp SDF beacons and optional deep-zoom procedural terrain; the left pane is
resizable; the analyst answers **region-level** questions ("what's happening
in Eastern Europe?"). The music engine was rebuilt on real Web-Audio DSP
(convolution reverb, ADSR, oversampled waveshaping, click-free preset
switching). And the Claude integration became a **multi-provider fallback**
(Anthropic → Gemini → Groq → Cerebras → OpenRouter → local Ollama) so the
AI features keep working on whatever key you have.

**v4 highlights:** every country on Earth is now represented (193 UN members
+ observers + de facto states like Taiwan, Kosovo and Somaliland, each
status-labeled honestly) with complete alliance rosters — NATO has all 32
members, ASEAN all 10 — kept fresh by Wikidata syncs. Boundaries upgraded to
Natural Earth 10m with zoom-dependent LOD on both the globe and the
overhauled 2D map, which now wraps seamlessly across the Pacific and carries
every globe toggle. Population-tiered city labels reveal as you zoom,
Paradox-style. Events cluster at low zoom and split continuously as you close
in, click areas match the solid dot (not the glow), and far-side orbs are no
longer clickable through the planet. A single left-docked sliding pane — one
consistent motion language, reduced-motion aware — serves story pages,
redesigned country profiles (flag, leader photo, ruling party), wiki-style
pages for parties, people, non-state actors, orgs and alliances with
prev/next browsing, side-by-side country compare, a stories directory
organized by type (wars, alliance developments, recurring patterns,
diplomatic/economic pushes), a sources & credits page, bookmarks, and your
own annotations layer (always visually distinct from AI output). Every event
carries a geocode-confidence score (approximate locations render dimmer,
never faked as exact) and a global-relevance score with a default-on
local-noise filter. Story pages gain a "show your work" correlation trace,
deeper on-demand summaries, and normalized headlines. The music engine got
its volume fixed (it was at 6%), a slider, and ten new presets from
numbers-station to war-room orchestral — including one that sonifies the
live ingestion stream itself. Plus in-app breaking alerts, one-click snapshot
export, an API-key setup page that writes your `.env` and live-tests each
key, border disputes as their own dashed map layer, thin-coverage honesty
badges, visible freshness stamps, and a colorblind-safe palette.

**v3 highlights:** an AI that argues with itself (three-persona debate +
devil's-advocate pass that can only *lower* confidence), hash-chained
tamper-evident provenance on every fact and prediction, the butterfly-effect
lineage view, story version history with diffs, self-tuning correlation
thresholds fed by your feedback, anomaly flags on the instability index, a
full geopolitical entity layer (country profiles, alliances, conflicts,
non-state actors, strategic locations & infrastructure, sanctions, treaties,
elections), a grounded analyst Q&A orb with citations and auto-navigation,
satellite overlay, generative reactive music, timelapse export, and
feature-detected WebXR. Forward forecasting ships **disabled** until the
prediction scorecard earns a track record — by design, per the manual.

## Run it

```
python run.py
```

That's it. Requires Python 3.10+ (Windows/macOS/Linux). The SQLite database is
created automatically, the Section 4 sources are seeded, ingestion starts, and
your browser opens to `http://localhost:8000`.

Useful variants:

```
python run.py --synthetic                          # seed the demo dataset first
python scripts/generate_synthetic_data.py --purge  # remove all demo rows
python run.py --no-browser
```

### AI — no key needed (recommended)

Every AI feature (causal storylines, the analyst, translation, briefings,
leader-profile synthesis) runs **free and local** via [Ollama](https://ollama.com):

```
1. install Ollama (Windows/Mac/Linux) from https://ollama.com
2. ollama pull llama3.1        # ~4.9 GB, one time
```

GlobeGrid finds the running server automatically — nothing to configure.
Slower machine? `ollama pull llama3.2:3b` and set `OLLAMA_MODEL=llama3.2:3b`.
Check it's working at `http://localhost:8000/api/diagnostics`.

### Optional keys (`.env` at repo root — copy `backend/.env.example`)

| Key | Enables |
|---|---|
| `GROQ_API_KEY` | Free cloud fallback if you'd rather not run Ollama (or Ollama isn't reachable) — [console.groq.com/keys](https://console.groq.com/keys), no card required. |
| `OPENROUTER_API_KEY` / `CEREBRAS_API_KEY` / `GEMINI_API_KEY` | Additional free-tier cloud fallbacks, tried in order if Ollama and Groq are both unavailable. |
| `CLAUDE_API_KEY` | Optional paid upgrade for higher-quality prose with no daily-quota ceiling. |
| `ALPHAVANTAGE_API_KEY` | Market-move events (Alpha Vantage free tier). |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Social signal from Reddit. |

None of this is required to run GlobeGrid — every feature works with zero
keys via local Ollama. Sources without keys simply show as `degraded` in the
status panel — nothing blocks (Section 10.2 failure isolation).

## What you get

- **Live feed** of correlated story clusters (never raw articles), pushed over
  WebSocket with an automatic 15-second REST-polling fallback — v2: raw events
  now appear on the map the instant they're ingested (`event_created`), as dim
  pins that light up when correlated.
- **World map**, three graphics tiers with auto-detection and a manual
  override, plus a v2 quality setting (standard / high / ultra):
  - Tier 1 — WebGL2 3D globe: day/night terminator with real city lights,
    animated correlation threads with particle trails, pulsing event
    particles, starfield + atmosphere halo, burst animations on live
    stories, heatmap + instability ghost-trail overlays, cinematic fly-to
    camera and idle tour mode, and bloom post-processing on ultra
  - Tier 2 — flat 2D canvas map with clustered pins + heatmap
  - Tier 3 — instant list/card view
- **Story pages** — causal storyline (cause / affected / consequences /
  confidence), **prediction scorecard** (the AI's stated consequences get
  graded against later facts), timeline of which source lit up when (with
  official-statement badges and wire-copy markers), bias/blindspot view with
  computed tone, connected-history fact-chain panel, possibly-connected
  clusters via shared root cause, full source list with outbound links.
- **Time capsule** — scrub to any past moment and the entire feed / map /
  instability UI reconstructs what it looked like then; press play for an
  hour-by-hour replay.
- **174 data sources** across news (incl. Xinhua/TASS/Le Monde/Haaretz/Times
  of India, Al Jazeera/Guardian/NYT/CNN/NPR/DW/France24/Euronews, Politico
  Europe, The Diplomat, SCMP, RFE/RL, Meduza, Anadolu, Defense News,
  ReliefWeb, ~8 technology feeds, and fast-polling local outlets for tracked
  conflicts — Ukrainska Pravda, Suspilne, Times of Israel, Ynet, Al
  Mayadeen), official statements (White House/EU/UN), USGS, NASA FIRMS
  wildfires, Smithsonian volcanism, Wikipedia current events + pageview
  spikes, Mastodon, Bluesky, markets + crypto, OpenSky air-traffic disruption
  (ACLED ready, pending access; GDELT retired in v6, its historical facts
  preserved).
- **Geopolitical entity layer** — every country (with leaders, currencies,
  and parliamentary seat-arc graphics for ~60 legislatures), full alliance
  rosters with rich clickable **bloc panels** (NATO, EU, CSTO, Arab League,
  ASEAN, African Union, BRICS, OPEC, Five Eyes, QUAD, AUKUS…), a tabbed
  **UN page** (Security Council, General Assembly, WHO, UNESCO… with full
  resolution vote breakdowns), **leader profile pages** (ideology, career,
  party history, AI-synthesized), an experimental diplomatic-**alignment
  map**, and individually-named **disputed territories** (Crimea, Donetsk,
  Luhansk, Zaporizhzhia, Kherson, Kashmir, Taiwan, Western Sahara, Kosovo)
  each with its own context breakdown.
- **War Mode** — click any conflict and the whole app reframes around it:
  camera flies to the belligerents, sides get real names and colored rings,
  the feed splits into military/civilian/diplomatic/economic tabs, and an
  AI **order-of-battle** covers forces, offensives, tactics evolution and
  global ramifications. Your general feed is preserved and restored on exit.
- **Briefings** — daily, weekly, monthly digests plus a **market briefing**
  (global overview + tentative, story-grounded forecasts, clearly labeled
  speculative), all AI-synthesized with a structured non-AI fallback.
- **17 color themes** (Ctrl/Cmd+T or the header picker to cycle), including
  the HOI4/TNO-mod-inspired **New Order** and **Fire Rises**, reaching the
  globe/map coloring, not just panels.
- **Power tools** — Ctrl/Cmd+K command palette, full-text search (FTS5),
  entity graph explorer, watchlists, daily AI briefing, CSV export,
  shareable /story/{id} deep links, camera bookmarks, per-source uptime
  history, ambient sound that tracks the instability index.
- **Instability index** — 0-100 composite (volume/severity/spread) trend line,
  wire-copy duplicates excluded.
- **Fact chain** — every extracted fact persists forever and every new event is
  checked against the entire chain (no time window) for long-horizon links,
  boosted by shared canonical entities.

Optional quality upgrades, auto-detected if installed (never required):
`pip install sentence-transformers` (semantic embeddings), `pip install spacy
&& python -m spacy download en_core_web_sm` (real NER), `pip install
vaderSentiment` (better tone scoring).

## Tuning

All thresholds/intervals/weights live in `backend/config.yaml` (Section 7.2) —
similarity thresholds, ingestion intervals, instability weights, cluster radii,
backoff policy. Secrets and connection info live in `.env`.

## Architecture

Seven-stage pipeline (Section 2): ingestion → extraction → embedding →
correlation → causal linking → serving → presentation. Backend is stdlib-only
Python (http.server + a hand-rolled RFC 6455 WebSocket, sqlite3 in WAL mode,
threaded per-source ingestion with exponential backoff). Frontend is buildless
ES modules with a self-contained WebGL2 globe renderer (no CDN, coastlines
vendored). See [CLAUDE.md](CLAUDE.md) for the full deviation log from the
original PostgreSQL/FastAPI/React plan and why each swap was made.

## License & attribution

[AGPL-3.0](LICENSE). Third-party data sources retain their own terms.
Geocoding data © [GeoNames](https://www.geonames.org), licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Coastlines:
Natural Earth (public domain).
