# GlobeGrid / TalkDiplomacy Live — agent context

## What this is

A real-time global event intelligence system: ingests news (RSS), USGS
earthquakes, market data, and Reddit (GDELT retired in v6 — historical facts
kept with "(historical)" attribution); extracts who/what/where/when facts into
a **permanent fact chain**; correlates events across streams AND across time
(same-window at 0.78 cosine similarity, historical chain at 0.85, no time
gate); generates causal storylines via a pluggable LLM provider (Groq by
default, Claude/Gemini/Cerebras/OpenRouter/Ollama as alternatives); serves a live feed,
tiered world map (WebGL2 globe / 2D canvas / list), War Mode conflict
dashboards, thematic choropleth map modes, story pages with bias view and
connected history, and a 0-100 instability index.

**Full specification:** `docs/talkdiplomacy_live_v1_build_manual.pdf` (REV 1.2).
Section numbers referenced throughout the code comments refer to that manual.
Read it before making non-trivial changes; every threshold, schema field, API
route, and prompt is specified there.

## Status (v6.6.2)

**v6.6.2 (2026-07-08, owner's post-6.6.1 fix list):** ~20 items. **Themes
recolored:** `new_order` → cyan/teal on near-black steel; `fire_rises` →
violet/magenta on near-black (both per owner screenshots); the original orange
ember look kept as a new **`ember`** theme (list re-alphabetized). **Settings
tabs actually split now:** every `.hidden` rule was ID-scoped, so
`.settings-tab-ai.hidden` did nothing — added the scoped rule; Display|AI now
truly separate. **Bloc panels open + are rich (the thrice-reported bug):** the
bloc dropdown rows were inert `<label>`s with no click-through — added a
clickable name that opens a new UN-style `/api/alliance/{id}` panel (leader +
portrait, purpose/HQ, policies & strategies, aggregate stats [members, combined
pop/GDP], member flag grid with click-through, conflicts members are party to,
recent stories, notable measures, and — for the EU — a European Parliament
hemicycle); bloc chips on country profiles now open it too (added `alliance_id`
to memberships; ALLIANCE_PROFILES/ALLIANCE_LEADERS keyed as "European Union").
**Alignments** derived for EVERY country from a camp model (`COUNTRY_CAMP` +
`derive_alignments`) — Argentina now reads US-aligned; the button moved into the
header row (no more thin-coverage collision), toggles off on re-click, and
re-targets when you open another country. **UN vote graphic fixed:** `voteArc`
read `tally.for/.against` (always 0) while the data uses `yes/no` — the "for 0,
against 0" bug; now clickable **full breakdown** per resolution (all named
yes/no/abstain grouped + residual counts). **UN sub-orgs** are now horizontal
navigable **tabs** (Overview + each organ as its own page) instead of inline
accordions. **Leader profiles** enriched (fuller Wikipedia intro + cached AI
synthesis: ideology / career / party history / key policies, large portrait),
reachable from portraits, bloc leaders and country panels. **Screenshot fixed:**
WebGL context now `preserveDrawingBuffer:true` (was a black/garbage capture).
**Market briefing tab** (right-aligned) — dynamic global-markets overview +
tentative story-grounded forecasts (`generate_market_briefing`, hourly cache,
"not financial advice"). **Legislatures:** added MNG/FIN/NOR/DNK/AUT/BEL/PRT/
IRL/NZL; `LEGISLATURE_NOTES` explains absence (SAU/ARE/QAT/OMN/BRN/VAT/AFG/PRK/
ERI) instead of blank. **Shortcuts:** F feed · L next language · C last/random
country · G globe · M map. **Feed:** the all/military/conflict dev-filter is now
War-Mode-only; **technology** is a first-class category (chip color + filter +
map colors, next to finance); conflict-tagged cards show a clickable **⚔
conflict chip** → War Mode. **War Mode** feed preservation fixed for real
(`feed.currentIds` never existed → snapshot was a silent no-op; now
`feed.snapshot()` of real story objects). **Alerts** pop even when the feed is
closed (separate host) + a Settings toggle. **Softer alert sound** (the mass-
update "screech" → a gentle rising perfect-fifth chime). **Bullets** in AI text
render one-per-line with spacing (line-based `_md`, broadened bullet markers).
**Disputed territories:** Crimea/Donetsk/Luhansk/**Zaporizhzhia**/**Kherson**/
Kashmir/Taiwan/Western Sahara/Kosovo as individual zones (`/api/disputed-zones`)
— disputed mode opens a clickable directory, each with a context breakdown.
Verified: boot clean; `/api/alliance/NATO` (32 members, $51.7T, 5 conflicts),
EU parliament 720, ARG alignment US-aligned, FIN legislature seats, disputed
zones incl. Zaporizhzhia/Kherson, market briefing fallback, UN tally 141/5/35 +
10 sub-org tabs; headless Chromium 0 JS errors (only sandbox-blocked flag
images). Whole-UI translation still deferred (owner: fix dedicatedly next
patch). Live Wikipedia/AI paths degrade cleanly behind the sandbox proxy.

## Status (v6.6.1)

**v6.6.1 (2026-07-07):** the four items v6.6 deferred. **Bloc panels
enriched:** `/api/alliances` attaches `leader` from `ALLIANCE_LEADERS` (7
blocs); `renderAlliance` shows a Leadership block (portrait via
leader-portrait), the member flag grid, and a "Recent related stories"
section via FTS search with click-through. **Whole-system translation
reaches story pages:** on open with a non-English language active, the
headline + summary swap to the cached `translateContent` result. **Briefing
non-AI fallback structured:** "### Top developments" (top 5, bolded, with
linkage counts) + "### Also tracking" instead of a flat list. **War Mode:**
"Backers / supporters" renamed to "Supporting states" (owner's sentence was
cut off — rename further on request). Verified: 7 blocs return leaders
(NATO → Mark Rutte), boot clean, JS/py parse.

## Status (v6.6)

**v6.6 (2026-07-07, owner's ~35-item list):** delivered across four areas. **AI
output:** analyst answers restructured (one-line takeaway + "### " section
headers + bullets, 150-300 words, `answer_max_tokens` 900, NO raw ids in prose
— ids only as clickable chips; `_md` renders headers/bullets/spacing); story
deep synthesis AUTO-generates on open; "full summary" button now forces an
EXPANDED regeneration (`deep_summary(expand=True)`, 8-14 bullets under
headers); briefing prompt rewritten to topic/region-sectioned bullets.
**Data:** legislatures for one-party/managed states (RUS Duma+FedCouncil, CHN
NPC, PRK SPA, IRN Majlis, CUB, VNM, BLR, SYR + ~20 more incl. EGY/PAK/THA/
NLD/SWE/CHE/GRC/HUN/CZE/KAZ/IRQ/VEN/ARG); **leaders for all 193 countries**
(`leaders_world.py`, INSERT OR IGNORE under curated entries, staleness-flagged);
Nagorno-Karabakh dispute → resolved (Armenia recognizes AZ control); UKR
dispute text covers 4 oblasts + Kharkiv strips + Crimea; **U.S.–Iran War**
conflict added + 4 past conflicts (Gulf Wars, Afghanistan 2001-21,
India–Pakistan Wars incl. 2025, Armenia–Azerbaijan) shown via status
'resolved'; **nuclear_arsenal map mode** (9 states, FAS/SIPRI estimates, ISR
90 included); blocs added (OPEC, Mercosur, G7, Five Eyes, QUAD, AUKUS, OECD)
+ `ALLIANCE_LEADERS`; UN panel gains 10 organs/agencies (`UN_SUB_ORGS`) as
expandable sections; **technology category** (color, keywords, 8 tech feeds →
174 sources) + finance keyword expansion (owner: too much landing in
'other'). **UI:** two new themes — **new_order** (TNO sepia/red austerity) and
**fire_rises** (TFR ember-on-black), theme list alphabetized; **Ctrl/Cmd+T (or
plain t) cycles themes** (Chrome may reserve Ctrl+T — plain t always works);
live feed panel closable (✕ + Esc last-in-stack) with an edge tab to restore;
Settings split into **Display | AI & keys tabs** (Display first); snapshot
button reads "screenshot"; UN button uses the real UN flag image; 2D-map A/D
inverted; entering War Mode snapshots the accumulated feed and restores it on
exit; "English (American)" label; Tier-3 region titles click through to the
region page. **Panels:** flags 96px, portraits 108px headshot-cropped
(`object-position: center 12%`; backend now prefers Wikipedia's infobox
THUMBNAIL — a professional headshot — over originalimage); **leader profile
pages** (`/api/leader-profile?name=` + `renderLeader`, opened by clicking the
portrait: roles, party, tenure, Wikipedia bio); **experimental diplomatic-
alignment overlay** (USA/RUS/CHN seeded in `ALIGNMENTS`; country-panel
"alignments" button colors allies green / partners light green / rivals red
via `setColoredRings`); UN vote hemicycles now fill column-first like the
parliament graphics. Partial/deferred: full bloc panels like the UN page
(leader data seeded, page enrichment pending), whole-UI translation beyond
feed+i18n chrome, briefing non-AI fallback structure. Verified: boot 174
sources, RUS Duma 450 + alignments, MDG leader resolves, nuclear mode 9
states, US-Iran + 4 past conflicts, leader-profile route, UN 10 sub-orgs,
analyst e2e on simulated Ollama; headless: only the UN-flag image blocked by
the sandbox proxy.

## Status (v6.5)

**v6.5 (2026-07-07, owner-requested — OLLAMA-FIRST):** after Groq's free tier
hit its 100k tokens/day ceiling (v6.4.2 diag table), the primary provider is
now the **local Ollama server** — free forever, no rate limits, fully
private — with Groq kept fully working as the first cloud fallback (key set +
Ollama down → everything transparently uses Groq as before).

- **Config:** `llm_provider.primary: ollama_local`; `ollama_model: llama3.1`
  (env `OLLAMA_MODEL` wins); `ollama_timeout_floor_seconds: 40` — feature
  call sites keep their Groq-tuned budgets, but a call that lands on local
  inference gets its timeout raised to the floor so laptop-speed generations
  aren't cut mid-answer. `analyst_panel.answer_timeout_seconds` 24→40 (outer
  deadline +12 still under the client's 60s abort).
- **llm.py:** `ollama_host()/ollama_model()/ollama_tags()` (installed-model
  list); the reachability probe is now **proxy-free** (`http.client` direct —
  urllib would route even localhost through an HTTP(S)_PROXY env var) and
  **cached** (8s up / 3s down) since it runs on every call as primary.
- **Settings:** a "Local AI — Ollama (primary)" status block above the key
  rows: ✅ running + model ready / ⚠ server up but model not pulled (with the
  exact `ollama pull` command) / ❌ not detected (with install steps). Key
  rows re-labeled as the optional cloud fallback. `/api/settings/keys` gained
  an `ollama` block {host, model, reachable, installed_models, model_pulled}.
- **Start-screen guide:** the welcome popup gained "Switch on the AI
  (one-time setup)" — install from ollama.com → `ollama pull llama3.1` →
  verify at /api/diagnostics; slow-PC tip (`llama3.2:3b`); Groq presented as
  the cloud alternative. First-run banner rewritten to match. `.env.example`
  leads with the Ollama steps; `OLLAMA_HOST`/`OLLAMA_MODEL` documented.
- **Diagnostics:** new first row **"Ollama server (local AI, primary)"** —
  answers 'is it running?' and 'is the model pulled?' in one line (lists
  installed models; failure text contains the exact fix command). Ping rows
  relabeled (they exercise the primary provider); per-test deadline 35→50s
  for local-inference headroom.

Verified against a **simulated Ollama server on localhost:11434** (real wire
format for /api/tags + /api/chat, honoring json-mode): with zero API keys,
`ai_available: true`; ALL 8 diagnostics rows ✅; the analyst answers end-to-end
from the local model (bullets + deep-dive, high confidence); translation
returns real Spanish through translate_batch. With the server killed:
`reachable/ai_available: false`, the diag row fails in 0ms with the setup
instructions, nothing hangs. Headless Chromium: 0 console errors.

## Status (v6.4.2)

**v6.4.2 (2026-07-07, owner's third diagnostics table — 6 of 7 green, the
transport rebuild CONFIRMED working):** DNS ✅ 9ms (AAAA records present,
validating the IPv6-sequential-connect diagnosis), ping ✅ 171ms, 4KB ping ✅
504ms, translation ✅ 410ms (real Spanish!), deep summary ✅, causal ✅. The one
❌ was no longer a hang but a fast, fully-diagnosed error: **Groq free-tier
429 — "TPM: Limit 12000, Used 11556 … try again in 1.31s"**. The now-working
background jobs (causal narratives, translation-on-arrival, agenda synthesis)
legitimately consume the tokens-per-minute quota; the analyst — the biggest
single request — tips over. Fix: rate-limit etiquette in `llm.complete`:

- **`interactive=True`** (a user is waiting: analyst, on-click deep summary,
  display translation `/api/translate*`, the diagnostics page) sleeps out a
  short cooldown (≤8s) and retries the SAME provider once after a 429, using
  the delay parsed from Groq's own "try again in N.NNs" message (or the
  Retry-After header; 15s fallback). Verified: a simulated 429 with "1.31s"
  retries and succeeds in 1.6s total.
- **Background calls** (scheduler jobs; the default) return None INSTANTLY
  during the cooldown window a 429 opens (`_note_rate_limit` /
  `rate_limited_for`), so they stop burning the quota the user needs. Every
  background caller already handles None gracefully (retry next cycle).
  Verified: 0ms skip, zero API calls, honest `last_error()`.
- `translate_batch(interactive=)` — the display route passes True; the
  on-arrival job stays background.

This is the free-tier contention pattern working as intended: bursty
background enrichment yields to the interactive user, and the user's own
calls ride out the sub-2s windows Groq actually asks for.

## Status (v6.4.1)

**v6.4.1 (2026-07-07, owner's second diagnostics table — the network layer,
convicted):** the v6.4 run DISPROVED the SQLite theory: deep-summary and
causal (pure `llm.complete`, zero DB access) — which passed in the v6.3.3 run
at 360/321ms — now ALSO hard-timed-out at 35s, while the tiny ping kept
passing (135ms). The only thing every hanging row shares that the ping dodges
by luck is **Python's HTTPS connection setup to Groq**, which stalls in layers
`urllib`'s `timeout=` does not bound: getaddrinfo (DNS) behind AV/VPN
interception; socket.create_connection trying resolved addresses
SEQUENTIALLY with the full timeout each (api.groq.com publishes AAAA records,
so a broken-IPv6 Windows machine burns 24s+ per IPv6 address before reaching
IPv4 — browsers do parallel Happy Eyeballs, Python does not — and resolver
answer order varies per query, explaining the intermittency); or a stale
Windows REGISTRY proxy that urllib silently honors. **Rebuilt the provider
transport** (`llm.py`):

- `_resolve()` — bounded (6s), cached (`network.dns_cache_ttl_seconds`),
  IPv4-preferred DNS; stale cache beats a hang; a stall raises a clear error.
- `_PinnedHTTPSConnection` — TLS to ONE pre-resolved address (no sequential
  multi-address connect), with SNI + certificate verification still against
  the real hostname. Stale-IP failures evict the cache and re-resolve.
- `_post()` — the whole request (DNS+connect+TLS+send+recv) runs on a daemon
  thread under a hard wall-clock deadline (call timeout +
  `network.request_deadline_buffer_seconds`); a socket-level timeout keeps its
  own accurate error, a true stall raises "exceeded the hard Ns deadline".
  Deliberately NOT a ThreadPoolExecutor (its workers are joined at interpreter
  exit, so one abandoned stalled request would block Ctrl+C shutdown).
- Windows registry proxies are deliberately bypassed (a stale Fiddler/VPN
  leftover blackholing POSTs is a classic cause of exactly this hang);
  explicit `HTTPS_PROXY`/`HTTP_PROXY` env vars are still honored via the
  legacy urllib path, itself under the same hard deadline. Plain-HTTP
  (Ollama localhost) skips pinning.
- Every provider (Groq/Gemini/Cerebras/OpenRouter/Anthropic/Ollama) goes
  through this one `_post`, so the fix covers ALL AI features at one point.
- `/api/diagnostics` gained two isolating probes: **DNS resolve** (shows
  address families — AAAA present + big-call hangs = the IPv6 story) and
  **large-payload ping (~4KB)** (small-OK + large-HANG = MTU/fragmentation).
- `translate_batch` per-call timeout 22s so both attempts + deadline buffers
  (2×28s) fit inside the client's 60s ceiling.

Verified: IPv4 preferred over AAAA-first answers; second resolve hits the
cache; real POST against a local HTTP server round-trips; a server that
accepts-but-never-responds errors at the socket timeout (3.0s, accurate
label); a worker stalled 300s errors at the hard deadline (8.0s) and the
process still exits instantly (daemon thread abandoned); diagnostics page
79ms total with all failures FAST; analyst route regression 200/6ms. Live
Groq/TLS pinning can't be exercised behind the sandbox proxy — the owner's
next /api/diagnostics table is the acceptance test.

## Status (v6.4)

**v6.4 (2026-07-07, owner-verified via the /api/diagnostics feature page — the
REAL root cause, found at last):** the self-test table was decisive. On the
owner's machine (with a working Groq key): Provider ping ✅ 123ms, Deep-summary
LLM call ✅ 360ms, Causal LLM call ✅ 321ms — but **Analyst ❌ HARD TIMEOUT 35s**
and **Translation ❌ HARD TIMEOUT 35s**. The three that passed are pure
`llm.complete` calls that touch NO database; the two that hung are the only two
that do **DB access around the LLM call**. So the hang was never the LLM/key/
model (all proven fine) — it was the **SQLite layer**, and it only bit
DB-touching features. Rebuilt `db/session.py`:

- **`journal_mode=WAL` is set ONCE at startup**, not on every new thread's
  connection. Re-asserting WAL per-connection while other threads are mid-write
  can block hard on Windows (mandatory file locking, unlike Linux — which is
  why it never reproduced in the build sandbox). A feature that opened its
  first DB connection on a fresh thread (analyst/translation, and the pool
  threads added in v6.3.2) hit exactly this. New connections now only set the
  cheap per-connection pragmas.
- **The global write lock is now a REENTRANT lock (`RLock`) acquired with a
  timeout.** A nested `write_tx` on one thread used to self-deadlock forever on
  the old non-reentrant `Lock` (verified: the old code hangs, the new returns
  in 5ms); genuine lock starvation now raises `WriteLockTimeout` (an `OSError`
  subclass the app's best-effort handlers already catch) instead of hanging.
- **Explicit `PRAGMA busy_timeout=8000`** on every connection so any file-lock
  wait is bounded (8s → clear error) rather than unbounded.

Verified: nested `write_tx` no longer deadlocks (5ms); 20 threads × 10
concurrent writes + reads all finish in 0.1s with zero errors and zero stuck
threads; the diagnostics page (which used to take ~70s with two 35s hangs) now
renders in 14ms with the DB-touching tests failing FAST (0ms, "no provider")
instead of hanging. The Windows-specific WAL hang can't be reproduced on the
Linux sandbox, but all three plausible DB-layer causes (per-connection WAL
contention, nested-write deadlock, unbounded lock waits) are now eliminated —
any residual contention converts to a bounded error, never an infinite stall.

## Status (v6.3.3)

**v6.3.3 (2026-07-07, owner — "NO AI feature has ever worked … tear it down"):**
the owner reported that the raw provider ping works (368ms, valid JSON) but
EVERY real feature (analyst, translation, summaries) fails, and that the
analyst specifically stalls only AFTER the key is configured. That split (the
isolated call works, the features don't) means the bug is in the shared
feature path, not the Groq call — and it couldn't be pinned down by reasoning
against an environment we can't reproduce. Two concrete changes:

- **`GET /api/diagnostics` — a live feature self-test PAGE (ground truth).**
  Runs each real path end-to-end (raw ping, analyst answer, translate_batch,
  deep-summary LLM call, causal LLM call) with a hard 35s per-test deadline and
  renders a table: ✅/❌, latency, and the actual reply OR the real error /
  "HARD TIMEOUT" for each. This is the definitive "what actually works on this
  machine" tool — screenshot it. (`routes_diag.py`; the handler learned to
  serve `_raw_html`.)
- **Warmup storm fixed (the "breaks after the key" trigger).** `_kick_ai_warmup`
  fired ~35 sequential LLM calls the instant a key was saved (25 causal
  narratives + agenda synthesis + translation + leadership). On a free tier
  (Groq requests/tokens-per-minute) that burst blows the rate limit, and the
  question the user asks seconds later competes for exhausted quota — matching
  the report exactly. Reduced to a small throttled trickle (2 causal + a small
  translate batch, 3s apart) so warmup can never monopolize the rate limit.

Diagnosed and ruled OUT (documented so they aren't re-investigated): no
network/LLM call is ever held inside the global `_write_lock` (causal
generation makes its LLM call BEFORE the write_tx); the provider abstraction,
key, model and JSON-mode are all proven working by the ping. The feature page
will show whether the remaining failures are server-side (real errors) or a
client/timing issue — that determines the precise next fix.

## Status (v6.3.2)

**v6.3.2 (2026-07-07, owner-verified real hang, found via
`/api/analyst/diagnostics`):** the diagnostics endpoint proved the owner's
Groq key/model were healthy (368ms live call, valid JSON) — yet a real
question still hung at "consulting the fact chain & web…" until the client's
60s abort. Since the raw provider call was proven fast, the hang had to be in
a part of the pipeline diagnostics doesn't exercise. Found TWO real causes:

- **Web search can hang past its own declared timeout.** `_web_search()`'s
  `urllib` call has `timeout=8`, but that only bounds the socket once
  connected — DNS resolution stalls (common behind certain Windows firewalls/
  antivirus/VPNs) aren't always covered by that parameter and can block far
  longer. This branch only fires when a question matches NO tracked entity or
  story (`thin`), which is exactly the failure the owner hit. Fixed with a
  HARD wall-clock deadline (`_bounded()`, 12s) around the call using a worker
  thread + `future.result(timeout=)`: if the call isn't done in time, the
  request gives up and continues with `web_results=[]` instead of ever
  blocking past that ceiling — the abandoned thread dies on its own later.
- **Self-inflicted regression in v6.3.1:** the "retry without JSON mode when a
  model rejects `response_format`" fallback reused the FULL timeout for the
  retry, so a slow first attempt + a slow retry could sum to 2x
  `answer_timeout_seconds` (48s) before the code even got a result — on top of
  any retrieval overhead, this could tip past the 60s client abort. Fixed:
  the retry now gets `timeout // 2`, and the ENTIRE `_answer_with_llm` call
  (both attempts together) is ALSO wrapped in a hard wall-clock deadline
  (`_bounded_or_raise()`, `answer_timeout_seconds + 12`) that raises a clear
  `ProviderError` ("took longer than Ns to respond") on timeout instead of
  ever blocking past it — so even a nested timeout that the OS/network layer
  fails to honor can't hang the request.
- `_bounded()` (best-effort, swallows failures → default) and
  `_bounded_or_raise()` (only intercepts the TIMEOUT; any real error, e.g. a
  `ProviderError` with the provider's actual message, still propagates
  unchanged) share one small `ThreadPoolExecutor` (`_IO_POOL`).

Verified with simulated hangs: a web search that sleeps 300s now returns in
12.3s (bundle falls back to no web results, answer still generates); an LLM
call that sleeps 300s now returns in 36.0s with a clear "took longer than 36s
to respond" message; the normal fast path is unaffected (5ms). This closes the
loop the owner traced: diagnostics proved the key/model/JSON-mode all work —
this fixes the two places nothing had ever bounded before.

## Status (v6.3.1)

**v6.3.1 (2026-07-07, owner — "the analyst is still broken, seriously fix
it"):** after v6.3 killed the query-time-embedding latency, the remaining
failure modes were about the LLM *reply*, not speed, and they were all being
hidden. Hardened the whole path and made it self-diagnosing:

- **Strict JSON mode (root fix for silent failures):** `llm.complete(...,
  json_mode=True)` now sets `response_format={"type":"json_object"}` on Groq
  (and `responseMimeType`/`format:json` on Gemini/Ollama). Llama returning
  prose-wrapped JSON that we then *discarded* was a prime "broken" cause — with
  json-mode Groq guarantees a valid object. Falls back to a plain call if a
  model rejects `response_format`.
- **Salvage instead of discard:** if a reply still isn't JSON, the analyst uses
  the model's prose AS the answer (medium confidence) instead of throwing the
  whole turn away and showing a canned fallback.
- **Real errors surface:** `llm.last_error()` captures the provider's actual
  message (parsed from the HTTP error body — "invalid api key", "model
  decommissioned", rate-limit, timeout). A configured-but-failing provider now
  tells the user the real reason + points at the key / `llm_provider.groq_model`
  config, instead of the misleading "no AI provider configured" copy.
- **`GET /api/analyst/diagnostics`:** one-click self-test — lists which
  providers are usable, the resolved groq_model, and does a live minimal call
  returning the raw reply or the real error + latency. This is how to see
  exactly what a key does.
- `complete()` now skips non-usable providers up front (no wasted timeouts) and
  Cerebras default model bumped to `llama-3.3-70b`.

Verified via simulated providers: json-mode reply parses; non-JSON prose is
salvaged (medium conf); a provider error (HTTP 401) surfaces its real message;
full route returns 200 in 2ms with nav resolved. The live Groq call is
proxy-blocked in the sandbox but the diagnostics endpoint exercises it on a
real key.

## Status (v6.3)

**v6.3 (2026-07-07, owner-requested — analyst timeout + graphics/data fixes):**
the analyst was STILL timing out ("the analyst took too long and was stopped")
even after v6.2 moved web-search/verification off the hot path. Root cause was
elsewhere and is now dead. Config gains
`analyst_panel.{embedding_retrieval_enabled,answer_max_tokens,answer_timeout_seconds}`;
no schema bump.

- **Analyst timeout — TRUE root cause found & fixed (top priority):** the
  remaining latency was **query-time embedding**. `_freeform_retrieval`
  re-encoded up to `embedding_scan_limit` recent headlines through
  sentence-transformers on EVERY question (`embed_text(r["headline"])` in a
  loop) — 10-30s of blocking CPU work with a real transformer installed,
  BEFORE the LLM call, which is what blew the 60s client abort. Fixed:
  query-time embedding is now OFF by default (`embedding_retrieval_enabled:
  false`); retrieval is FTS5 (fast, indexed) + a cheap recency top-up. The
  answer is a single Groq call bounded by `answer_max_tokens` (650) and
  `answer_timeout_seconds` (24, well under the client's 60s). Verified: full
  path with a simulated provider is **5ms, 1 LLM call, 0 embedding calls**
  (retrieval-only path 0.099s); entity match still resolves ("Russia–Ukraine
  War"). Embedding retrieval stays available behind the config flag for
  offline setups that want it.
- **Legislature graphics — column-first fill + bicameral:** seats now fill
  COLUMN-FIRST (sorted left→right by angular fraction across all rows) so each
  party occupies a clean angular wedge like a real chamber diagram, instead of
  horizontal bands per row. Bicameral bodies render BOTH chambers: `LEGISLATURES`
  entries gained an `"upper"` sub-dict (US Senate, UK Lords, FR Sénat, IN Rajya
  Sabha, JP Councillors, IT/ES/AU/BR/PL/CA upper houses); `oneChamber()` draws
  each, `parliamentGraphic()` stacks lower + upper.
- **Leader portraits that actually work:** the single REST-summary title guess
  silently missed whenever a leader's article title differed from the stored
  name. Now two-path: REST summary (follows redirects) THEN the action API's
  `pageimages` with a `list=search` step first, so a name that isn't the exact
  article title still resolves. Cached in `app_meta` + persisted onto
  `country_leadership.image_url`. (Wikipedia proxy-blocked in sandbox → null
  cleanly; works on a real network.)
- **Sub-minute news:** `ingestion_intervals_seconds.rss` 60→45, usgs 90→75,
  market 120→90; frontend safety-net feed poll 20s→12s. New stories surface
  within ~12s even if the socket misses a push.

## Status (v6.2)

**v6.2 (2026-07-07, owner-requested — "fulfill all objectives 1 shot"):** a
broad correctness/UX pass on top of v6.1.1. No schema bump; config gains a few
keys (`analyst_panel.embedding_scan_limit`, `.live_verify_on_hot_path`,
`ui.terrain_button_visible`) + faster ingestion intervals. Highlights:

- **Analyst speed FIX (top priority):** the analyst timed out even on covered
  queries ("the analyst took too long and was stopped"). Root cause: web
  search (~8s) AND live leadership verification (~30s: its own web search + LLM
  call) ran *synchronously before* the answer call, so a covered query took
  40-80s and blew the 60s client timeout. Both are now off the hot path
  (`live_verify_on_hot_path: false`, web search only when retrieval is truly
  thin); the answer is a single `llm.complete` (max_tokens 700, timeout 30);
  the embedding scan is capped (`embedding_scan_limit: 80`). One Groq call,
  ~sub-second with a simulated provider.
- **Bullet summaries:** `DEEP_SUMMARY_PROMPT` rewritten to big-picture
  process bullets ("explain the PROCESSES … 3-6 tight markdown bullets", do
  not re-narrate events); cleanup switched from `normalize_summary` (which
  collapsed newlines into a wall of text) to bullet-preserving `strip_links`;
  `StoryPage.bulletsToHtml` renders them as a real `<ul>`.
- **Live feed bugfix + by-the-minute ingestion:** `refreshStories` now renders
  the feed IMMEDIATELY and translates asynchronously in place (it used to
  await a possibly-hung translate call, leaving the feed blank — "the live
  feed sometimes doesn't come in"); a 20s safety-net poll backs up the socket.
  `ingestion_intervals_seconds` dropped (rss 300→60, usgs→90, market→120).
- **~100 more sources:** `seed.py` +103 fast global RSS feeds (Al Jazeera,
  Guardian/NYT/CNN/NPR/DW/France24/Euronews/MEE/Africanews/Dawn/NHK/Nikkei/
  MercoPress/War-on-the-Rocks/Bellingcat/UN-WHO-OCHA …) → 174 total, 166
  active (live fetch proxy-blocked in sandbox, degrades cleanly).
- **Instant translation debug (§10/§11):** the batch LLM timeout (90s)
  exceeded the client's 60s ceiling, so a slow batch was abandoned browser-side
  even though the server finished — dropped to 40s so it fits inside 60s.
- **Instant everything on Groq-key save:** `routes_v4._kick_ai_warmup` spawns
  a daemon thread on a successful AI-key save that runs causal-narrative
  backfill + country-agenda synthesis + recent-content translation +
  leadership refresh, so the whole system "pings" to life on the next click;
  `WikiPages` calls `ctx.onAiKeySaved()` which re-reads config + re-renders the
  feed at 0/6/15s.
- **Instant wiki config (§7):** `/api/background/{type}/{id}` now fetches that
  entity's Wikipedia summary ON DEMAND (`sync.fetch_background_now`) when the
  cache is empty, instead of waiting for the weekly reference cadence.
- **Leader portraits (§5):** `/api/leader-portrait?name=` fetches the
  Wikipedia REST thumbnail (cached in `app_meta`, persisted onto
  `country_leadership.image_url`); `WikiPages` swaps the placeholder for the
  real photo (Xi next to the China flag). Wikipedia proxy-blocked in sandbox →
  returns null cleanly.
- **Small countries exist & are reachable:** they were always in the data
  (MUS/COM profiles resolve, in boundaries) but too small to see/click. Globe
  draws a marker dot + name for sub-4° countries when zoomed; `onCountryClick`
  snaps to the nearest small country within 2.5° on an ocean miss.
- **Themes reach the whole UI incl. globe/map (owner: "even the globe and map
  coloring", NO font changes):** the v6 §23 themes were setting `--panel`/
  `--panel-2`, which *nothing consumes* — the layout reads `--bg-panel`/
  `--bg-card`, so every one of those themes left the panels the same default
  dark-blue and looked near-identical. Rewrote all of them to set the consumed
  names + per-theme category signal colours. `arctic_white` deleted →
  **`crimson_gold`** (deep-crimson panels, gold text). The globe sphere shader
  gained `uOcean`/`uRim` tint uniforms and the 2D map `landStroke`/`gridStroke`
  fields; `App.applyThemeToRenderer` reads the active theme's `--accent` and
  pushes a hue-matched ocean tint + atmosphere colour (globe) or accent
  coastline/graticule strokes (map). Removed the amber-terminal font override
  (no font changes). Verified: 0 console errors, crimson_gold resolves gold
  text on crimson panels.
- **Quick UI fixes:** A/D pan direction inverted (globe + 2D); VR button
  removed; terrain mode removed (config-hidden; the biome texture dropped most
  interior land and read as "North America blobs on Asia"); selected-entity
  outline changed teal→orange/gold (`[1.0,0.72,0.18]`); header timezone picker
  added; country-name toggle added (`names` button, persisted); tier-3 panels
  spaced off the UI chrome; story pages steer big-picture not event-rehash.

Live paths (Groq analyst/translation, Wikipedia portraits/background, live
RSS) are proxy-blocked in the build sandbox and degrade cleanly; all verified
through simulated providers / curl / headless Chromium where behaviour matters.

## Status (v6.1.1)

**v6.1.1 (2026-07-06):** built the seven items v6.1 had explicitly deferred.

- **Dynamic country labels** (globe + 2D): anchors from each country's largest
  boundary ring, revealed by APPARENT on-screen size (span° × px/°), so big
  countries label from far and small ones (Bhutan, Aruba) only when zoomed in.
- **Multi-alliance toggle:** the bloc dropdown became a checkbox popover;
  several alliances show at once, each its own colour, via the renderers'
  existing `setColoredRings`.
- **Language/religion family colours + hover tooltips:** map modes colour by
  FAMILY (`data/families.js`: 113 languages → 27 families → hues placed by
  genetic proximity, so Iranian ≈ Indo-Aryan warm reds, Slavic ≈ Baltic
  magentas); a hover tooltip names the country + exact value, so no colour key
  is needed (`countryAt` returns the boundary object → take `.i`).
- **Timezone + date settings:** `data/timefmt.js` (32 zones + ISO/US/EU date
  formats) applied to every rendered timestamp; changing it re-renders the
  feed.
- **Tier-3 geographic boxes:** the low-power tier bins events into continental
  panels (North America, Europe, Middle East, …) instead of a flat list.
- **Terrain removed (owner request):** the terrain toggle is hidden
  (`ui.terrain_button_visible: false`). Root cause found: the baked biome
  texture is rasterized from the sparse `worldCoastline.js` rings, whose
  scanline fill drops most interior land (Sahara/India/Siberia/Amazon sample
  as ocean — verified by reading the texture), so terrain read as stray
  misplaced blobs; a spurious `+0.5` in the sphere-shader UV (copied from the
  heatmap's different origin) also offset it 180°. The UV was fixed and a
  hillshaded elevation field (20 vendored ranges) was added, but the texture
  can't be trusted until it's rebuilt from the full boundary data, so the
  feature is off. Flip the config flag to revive it after that rebuild.
- **War-mode frontline + AI order-of-battle:** Russia-Ukraine occupied
  territory refined to a 24-vertex control polygon (front line + Crimea) +
  a contested zone, rendered as the shaded dot-field; a lazy
  `/api/conflicts/{id}/order_of_battle` returns an AI-generated (Groq)
  structured order of battle / offensives / tactics evolution / global
  ramifications, cached after first generation.

Still genuinely live-data-bound (not in this build): minute-to-minute
LiveUAMap frontline motion (needs a live conflict feed; the vendored polygon
is a labelled approximation).

## Status (v6.1)

**v6.1 (2026-07-06, owner-requested polish/usability pass on top of v6):** a
large batch of "make it fully usable" fixes. Highlights:

- **LLM reliability:** honest `ai_available` flag in `/api/config` drives all
  fallback copy — the causal-storyline and country-agenda panels no longer
  show a hardcoded "Set CLAUDE_API_KEY" string, they reflect the real
  provider (Groq). Translation JSON parsing hardened (`_extract_json_array`:
  fence-strip + balanced-bracket + one retry) so Groq/Llama replies that wrap
  or trail the JSON still land (fixes "translation only changes the title").
  Client-side request timeouts on every call + an analyst **Stop button**
  (AbortController) so a stuck provider call can't spin forever; analyst
  web-search/verify timeouts tightened.
- **Audio:** `hard_rock_metal` deleted. Ambient buzz fixed for real (drone
  raised out of the ~33 Hz sub-rumble band + a `softDrone` body filter; DC
  ≤0.00002, zero clipping in offline render). Music **autoplays on load**
  (`armAutoplay` resumes on first gesture). Three experimental glacial/chimey
  presets: `crystalline_chimes`, `deep_glacier`, `aurora_drift`.
- **Leaders:** country profiles feature the **paramount leader** (Xi Jinping
  for China, not Premier Li Qiang; Putin for Russia), derived from government
  type + explicit overrides (`_paramount_role`/`_PARAMOUNT_TITLE` in
  `routes_geo.py`); portraits populate from the first Wikidata sync tick and a
  bad URL degrades to the placeholder.
- **Country panels filled:** every country's **currency** (214-entry
  `country_extra.CURRENCIES`) in the stat grid; a **parliamentary seat-arc
  graphic** (party-colored hemicycle + legend) for 19 major legislatures
  (`country_extra.LEGISLATURES`, `country_legislature.seats_json`).
- **UN panel:** `/api/un` + `geopolitics/un_data.py` — Security Council (P5 +
  10 elected), other organs, and notable resolutions each with a hemicycle
  **vote graphic** (green for / red against / grey abstain) sized to the real
  recorded tally (UNGA ES-11/1 141-5-35, ES-10/21 153-10-23, UNSC 2728/2735)
  + clickable per-country votes. Header "🇺🇳 UN" button.
- **War Mode:** real **side names** ("Russia & allies" / "Ukraine & allies",
  server-derived `side_names`), belligerents listed first then a separate
  backers line; Ukraine's backer roster expanded (UK/France/Poland/Canada/
  Netherlands/Italy) and Russia's (North Korea/Iran alongside Belarus).
- **Navigation & UI:** **WASD** camera control on globe AND 2D map (A/D
  rotate/pan, W/S tilt/pan, Q/E zoom); modes bar docked to the **bottom**
  (EU5-style); heatmap toggle removed; green-coded **"military"** event
  category distinct from conflict; a welcome/how-to **popup** behind a header
  "?" (auto-shown once).
- **Briefings:** **weekly + monthly** briefings alongside daily
  (`briefing.generate_briefing(period=)`, period keys `YYYY-Www`/`YYYY-MM`),
  switchable in the overlay.
- **Map graphics:** NSA/partial-control zones render as a **pulsing techno
  dot-field** (globe + 2D) instead of outlined "rectangles"; choropleth
  shading rebuilt as a brighter 3-stop ramp at 0.72 opacity.

**Deferred to a later pass (documented, not silently dropped):** real
topographic terrain relief (still the baked biome texture, not elevation);
live LiveUAMap-style moving frontlines and an AI order-of-battle history
(both need live conflict data the sandbox can't reach); dynamic zoom-gated
country labels; simultaneous multi-alliance overlay toggling; language/
religion family-color hover tooltips; Tier-3 geographic-box layout; and
timezone/date settings. These are scoped but not in this build.

## Status (v6)

**The v6 build (docs/globegrid_v6_build_manual.pdf, REV 6.0, Sections 1-33,
build phases A6-L6) is built on top of v1-v5.2 (2026-07-06).** Schema v6
in-place migration (SCHEMA_VERSION=6, additive + a countries-table rebuild to
admit `status='territory'`; the upgrade re-runs idempotently so late-added
columns self-heal). New tables: conflict_subfactions, story_threads(+members),
content_translations, subnational_areas. Verified live: boot + curl on every
new route, headless Chromium (zero console errors) across war mode, ESC
stack, map modes, languages, rect select, terrain, and themes — screenshots
in the delivery zip notes. Highlights by manual section:

- **LLM routing (§1):** primary provider is canonical `groq` (model from
  `GROQ_MODEL` env or `llm_provider.groq_model`); `causal_link_override:
  anthropic` lets the causal engine prefer a stronger model when a Claude key
  exists while everything else stays free-tier. `complete(prefer=)` in
  `processing/llm.py`.
- **GDELT retired (§2):** fetchers/imports removed, source rows kept with
  `is_active=0` (health drawer hides them; old facts attribute as
  "(historical)"); 16 replacement RSS sources incl. fast-poll wires.
- **War Mode (§8) + Conflicts tab (§9):** `/api/warmode/{conflict}` returns
  belligerents with `side` (a/b), subfaction polygons, a camera frame bbox
  computed from belligerent countries only, and coverage stats. Frontend
  enters a themed war layout: side-colored country rings, subfaction zones
  (established vs contested), five war tabs (all/military/civilian/
  diplomatic/economic → `war_tab` story filter), exit restores prior state.
  The header Conflicts button opens a conflicts directory; the old per-story
  conflict-tab suggestion became a filter chip.
- **Site-wide instant translation (§10, §11):** header language selector;
  `processing/translate.py` batch-translates feed content through the
  provider abstraction into `content_translations` (cache-first, one call
  per batch of misses); non-English arrivals normalized to English for
  correlation; wordmark transliterates (`ui.wordmark_transliteration`).
- **Interaction (§6, §12, §13, §26):** ESC closes exactly one layer per
  press (palette → modes bar → drawers → panels → pane.back() → war mode);
  shift+drag rectangle select over globe AND 2D map opens a grouped events
  pane (capture-phase pointerup suppresses the click leak); **the
  random-panning bug is dead** — `autoRotate` starts false and autonomous
  motion exists ONLY inside the idle-tour gate (`idle_tour_seconds > 0` +
  real inactivity); selected countries get a pulsing highlight.
- **Entity depth (§5, §14, §15):** `geopolitics/country_stats.py` seeds
  authoritative stats (area, GDP, GDP/capita derived, HDI, languages,
  religion) for all 199 countries + 15 territories (GRL/PRI/HKG/… with
  `status='territory'` + sovereign link pages); party/person profiles gain
  founding history, electoral results, coalitions, portraits.
- **Thematic map modes (§16):** `/api/mapmodes` registry — population, area,
  density, GDP, GDP/capita, HDI (numeric, log-scale where appropriate) +
  religion/language (categorical) + subnational overlays (17 vendored area
  polygons: Nigeria N/S, Swiss language regions, Xinjiang/Tibet, …) — all
  from the authoritative dataset, never LLM-guessed; choropleth fills on
  both renderers with a legend.
- **Audio (§17):** `presets_active` trims the picker to 5; Ambient buzz
  fixed (symmetric odd-length WaveShaper curve kills the DC offset + a 26Hz
  master DC-block highpass); new `hard_rock_metal` preset (power chords,
  cabinet EQ, square-LFO chug gate) validated by offline render: DC ≤0.0002,
  zero clipped samples.
- **Tile-based 2D map (§18):** boundaries pre-chunked once into 30° Path2D
  tiles stroked under a canvas affine transform — **profiled 387ms → 2.9ms
  (133×) per frame at 10m detail**, per the manual's "confirm with the
  profiler" rule.
- **Real biome terrain (§19):** `scripts/build_biome_texture.py` bakes a
  stdlib-PNG equirect biome texture (coastline rasterization + latitude
  bands + desert noise) into `frontend/src/data/biomeTexture.js`; sphere
  shader samples it with facing occlusion — replaces the fbm blob look.
- **Accuracy pipeline (§30) + analyst (§29):** `processing/accuracy.py`
  (Brave key or keyless DDG) verifies stale leadership rows via
  search→LLM-extract→write with confidence gating; the analyst answers in
  bullets + expandable deep-dive, is screen-aware, does region deep-dives
  (countries/conflicts/threads/stories as linked chips), and triggers live
  verification when it cites stale leadership.
- **Story Threads (§27):** `processing/threads.py` clusters stories into
  named narrative threads (entity overlap + centroid cosine ≥0.5, pair
  ≥0.55 seeds); directory lists threads first with member chips; the
  directory got pagination + an indexed type query.
- **Data correctness (§21, §28, §7):** Taliban reclassified as de-facto
  government of AFG (leadership Akhundzada/Akhund; removed from NSA zones);
  UN M49 sub-regions (`geopolitics/m49.py`, 214 iso3) are the single region
  taxonomy with per-subregion completeness checks; SCO/GCC/Arab League/
  ECOWAS/AES alliances; UKR four-oblast dispute; conflicts carry per-party
  `side` + 7 subfactions.
- **Small items (§3, §20, §22-§26, §31):** story summaries render as
  bullets with a full-summary expander; emoji stripped + ALL-CAPS headlines
  sentence-cased + 140-char word-boundary truncation; flags/leader photos
  52px; instability recalibrated (`baseline_divisor: 3.2`); 10 new color
  themes (14 total); city-lights toggle; dateline geocoding (earliest
  mention + 15-char adjacency window — "TEHRAN —" beats a later "Beijing");
  VR button hidden behind `ui.vr_button_visible`.

Network-dependent paths (live RSS, flag downloads, Wikidata, live Groq/DDG
calls) stay proxy-blocked in the build sandbox and degrade cleanly; all were
exercised through simulated providers/fixtures where behavior mattered.

## Status (v5.2)

**v5.2 (2026-07-06, owner-requested — "make ALL the LLM features work with
Groq, and make the analyst a real smart chat"):** two problems. (1) v5's
provider abstraction (`processing/llm.py`) was only ever wired into
deep-summaries; **every other AI feature still hardcoded an Anthropic-only
`urllib` call gated on `CLAUDE_API_KEY`**, so on a Groq key they all silently
fell back to their no-AI paths (the "set CLAUDE_API_KEY" message in the
causal-storyline and analyst screenshots). Migrated all of them to route
through `llm.complete()` / `llm.available()`: `causal_link.py` (causal
narratives + devil's-advocate), `debate.py`, `predictions.py`,
`second_order.py`, `forecast.py` (forecast + prognosis), `briefing.py`,
`geopolitics/synthesis.py` (country agendas + bilateral relations), and the
`/api/translate` route. Removed the now-dead Anthropic imports/URLs from each;
none reference `CLAUDE_API_KEY` directly anymore (only `config.py`, `llm.py`,
and `routes_v4.py`'s key-management legitimately do).

(2) **Analyst rework (`api/routes_analyst.py`) into a genuine conversational
assistant** (config `analyst_panel.*`): now routes through the provider
abstraction (works on Groq); replays the last N conversation turns for real
multi-turn memory (`conversation_history_turns`, default 8); a greeting or
meta question ("hi", "what can you do?") gets a natural reply instead of
three unrelated story citations (`_SMALLTALK` guard); each retrieved story is
enriched with its **causal narrative + confidence** and its headline/summary
run through the v4 §11 link-strip so the model never sees tracker-URL/hashtag
junk (fixes the "Https:// A-di-palantir…" garbage citations); the global
instability index rides in the bundle; and a **keyless web search**
(DuckDuckGo HTML endpoint, `web_search_enabled`, default on) augments answers
when GlobeGrid's own coverage is thin, with web-sourced facts clearly labeled
vs tracked ones. The `_web_search` unwraps DDG's redirect to the real target
URL and degrades cleanly when offline (proxy-blocked in the sandbox). The
frontend `AnalystPanel.js` now renders a safe markdown subset (bold / italic /
code / links / line breaks) so prose and web links display properly.

Verified via curl + a simulated provider: greeting → conversational (no story
dump), data question → entity matched ("Sudan Civil War") with a full
bundle (entity + stories + web_results + instability) and accumulating
conversation turns; the DDG parser extracts title/snippet/real-URL from a
sample results page. Live Groq calls are proxy-blocked in the build sandbox
but exercised on the owner's machine.

## Status (v5.1.2)

**v5.1.2 (2026-07-06, follow-up fix):** the v5.1.1 fix surfaced
`_provider_error_detail`, but a live report came back as a bare "HTTP 403
from provider" with no message at all — meaning the response body wasn't
the provider's normal JSON error shape. Root cause: every outbound request
in `llm.py`/`routes_v4.py` used urllib's default User-Agent
(`Python-urllib/3.x`), which some providers' edge/WAF layer flags as a
bot/scraper and blocks before the request reaches real auth logic, returning
an HTML block page instead of JSON. Fixed by (1) setting a real
self-identifying User-Agent (`llm.USER_AGENT`) on every outbound provider
request, `_post()` in `llm.py` and the standalone `Request` objects in
`_test_key`, and (2) making `_provider_error_detail` fall back to a raw-body
text snippet instead of a bare status code when the response isn't
parseable JSON, so any future opaque rejection is still visible instead of
silently discarded.

## Status (v5.1.1)

**v5.1.1 (2026-07-06, follow-up fix):** the v5.1 `_test_key` reused the
Claude-era shortcut of collapsing every HTTP 401/403 into a flat "rejected —
check the key" for the new free providers too, which hid Groq's/OpenRouter's/
Cerebras's actual rejection reason behind a useless generic message — the
exact bug class the v5.1 changelog entry below claims was fixed, except it
wasn't applied to the error path, only the "unverified saved" path. Fixed by
always surfacing `_provider_error_detail(exc)` (the parsed `error.message`
from the provider's JSON body) instead of special-casing 401/403.

## Status (v5.1)

**v5.1 (2026-07-06, owner-requested, no manual section — a config/onboarding
change on top of v5's already-built provider abstraction):** the app's
*default* LLM provider changed from Claude to **Groq** (free, no card,
~14,400 req/day, Llama 3.3 70B), with **OpenRouter** as the first fallback —
picked because both offer a same-API paid upgrade path for when this becomes
a real multi-user deployment, unlike Ollama (which would mean self-hosting
GPU inference at scale) or Gemini Free (1,500 req/day, too tight even for
solo dev). Claude is now an optional upgrade, not a requirement. Concretely:
- `backend/config.yaml` `llm_provider.primary: "groq_free"`,
  `fallback_order: [openrouter, cerebras_free, gemini_free, anthropic,
  anthropic_open_source_grant, ollama_local]`.
- `MANAGED_KEYS` in `routes_v4.py` reordered (Groq/OpenRouter/Cerebras/Gemini
  first, Claude marked "optional upgrade", nothing marked `required` anymore)
  and given **real live-tested** save-and-test calls (was previously a silent
  "saved, unverified" no-op for every non-Claude/Alpha-Vantage key — the same
  silent-acceptance bug class already fixed once for Claude in v4.2).
- `onboarding.require_claude_key_before_first_run` renamed to
  `require_ai_key_before_first_run` (config, schema, `/api/config`,
  frontend) and the gate now reads a generic `ai_available` flag
  (`processing/llm.py` `available()`) instead of checking `CLAUDE_API_KEY`
  specifically — the first-run banner now says "add a free AI key (Groq
  recommended)".
- **Bug fix in `llm.available()`:** it previously returned `True` the moment
  `ollama_local` appeared anywhere in the fallback order, regardless of
  whether a local Ollama server was actually reachable — meaning the
  onboarding gate would silently report AI as "available" with zero working
  keys configured, and the app would degrade to no-AI without ever telling
  the user. Fixed with a short-timeout reachability probe
  (`_ollama_reachable()`, `GET {OLLAMA_HOST}/api/tags`).
- `backend/.env.example` reordered to put the free keys first with signup
  links; Claude demoted to "optional upgrade."

Verified via curl + headless Chromium: `/api/settings/keys` lists Groq first
with `ai_available: false` on a clean `.env`; the onboarding banner reads the
new free-key copy; Settings renders all four free-provider rows above
Claude, none marked required.

## Status (v5)

**The v5 build (docs/globegrid_v5_build_manual.pdf, REV 5.0, Phases
VV-DDD / Sections 1-22) is built on top of v1+v2+v3+v4 (2026-07-06).**
Schema v5 in-place migration (SCHEMA_VERSION=5, additive: events
.development_type, sources.reliability_tier, countries.flag_image_url,
new non_state_actor_zones table). Verified in this repo via curl +
headless Chromium:

- **Text quality (§1):** tracker/redirect links stripped from headlines &
  summaries (`processing/textquality.py` strip_links), plus a feed **sort**
  selector (newest / oldest / most active) and a **history / archive** pane
  (date + category filtered over the permanent fact chain).
- **54-locale UI (§2):** `frontend/src/i18n.js` — every EU language +
  neighbours, West/Central Asia, ASEAN, East Asia (Simplified/Traditional
  Chinese distinct); real RTL layout for fa/ur/he/ar (document `dir` flips,
  verified dir=rtl for Arabic).
- **Conflict vs military split (§3, §6):** extraction classifies
  `development_type`; a military development never populates a conflict tab —
  the §6 conflict-tag suggestion is gated on development_type='conflict'
  (verified: military-type story does not suggest).
- **Reliability tiers (§4, §5):** TalkDiplomacy + AP/AFP/Guardian/DW/gov-mil/
  OSINT sources seeded; every source carries a `reliability_tier`
  (high/medium/low, 36/17/5 observed; GDELT Events=low); the instability
  index weights volume/severity by tier.
- **Real flag images (§7):** iso3→Wikimedia "Flag of {X}" URLs
  (`geopolitics/flag_names.py`, 199 countries) surfaced on country profiles
  and member lists — **never emoji** (verified FRA URL); a `refresh_flags`
  sync downloads SVGs to `frontend/flags/` (proxy-blocked in sandbox,
  degrades cleanly).
- **Non-state-actor zones (§11):** 9 seeded territorial polygons (Taliban,
  Houthi, Sahel juntas, …) drawn as translucent overlays on both the WebGL2
  globe and the 2D map; `/api/nsa-zones`.
- **Graphics (§8, §9, §12, §16):** SDF beacon rendering with fwidth()
  anti-aliasing; deep-zoom procedural terrain (fbm, LOD-gated, config default
  **off**); cluster click → list pane; 2D-map viewport culling.
- **Panels & content (§10, §13, §14, §19, §20):** resizable left pane
  (persisted width); immediate content load; **4 color themes**
  (dark_teal_default / high_contrast / amber_terminal / colorblind_safe,
  CSS-variable swap on `body`); sources drawer closes by ✕ and Esc;
  region-aware analyst (`/api/region/{region}` — "Eastern Europe" → 8
  countries + Russia–Ukraine War).
- **Audio (§17):** engine overhaul with real DSP primitives — ConvolverNode
  reverb (synthesized impulse), WaveShaper (4× oversample), ADSR envelopes,
  fade-out teardown (fixes the switch-click that made every non-ambient
  preset "static"), unison detune, DynamicsCompressor limiter. Verified
  zero-clipping across all 11 presets via offline render.
- **LLM provider fallback (§18):** `processing/llm.py` abstraction tries
  primary + fallback order across anthropic / gemini / groq / cerebras /
  openrouter / ollama; deep summaries and translation route through it;
  never raises. The `_test_key` fix uses the real CLAUDE_MODEL and surfaces
  the provider's actual error (the v4.2 "HTTP 400" fix).
- **Data (§15):** IRN head_of_state → Mojtaba Khamenei (Supreme Leader,
  since 2026-03-09); leadership rows carry a staleness flag + reason until a
  live Wikidata sync overwrites them.

§21 lower-urgency extras (diff-on-refresh, conflict PDF export) fold in
where convenient. Network-dependent syncs (flags, Wikidata, live sources)
stay proxy-blocked in the build sandbox and degrade cleanly.

## Status (v4)

**The v4 polish/accuracy/depth pass (docs/globegrid_v4_build_manual.pdf,
REV 4.0, Phases BB-UU / Sections 2-26) is built on top of v1+v2+v3
(2026-07-06).** Verified in this repo: the three confirmed one-line bugs
fixed at their cited locations — globe hit-test occlusion now uses the
shader's facing computation instead of the NDC-depth threshold (§2.1),
SoundEngine master gain 0.06 → config 0.4 + a real volume slider (§12.1),
and the analyst focusedEntity lifecycle (cleared on pane close/empty
click, timestamped for staleness, question text always outranks focus,
conflict names match per-party aliases so "Palestine" reaches
Israel–Palestine Conflict — §16, verified via curl). Entity completeness
(§5): 199 countries seeded (193 UN + 2 observers + TWN/XKX/SOL/CYN de
facto with `countries.status`), full alliance rosters (NATO 32, ASEAN 10,
EU 27, AU 54, …), 24 border disputes, 30 political parties, and a startup
completeness check surfaced at /api/completeness; Wikidata country/roster
syncs are the ongoing refresh path. Boundaries upgraded to vendored
Natural Earth 10m/50m LOD (polyline-encoded via
scripts/build_boundaries.py; point-in-polygon is now antimeridian-safe
with smallest-bbox preference, so enclaves and Russia resolve correctly —
verified against 14 test points). Globe clustering with continuous
screen-space declustering and crisp overlay count circles (§2.2, NOT glow
sprites), decoupled hit radius (§2.2), tiered city labels (§4.3), Tier 2
map at full toggle parity with 3-tile east-west wraparound (§4). One
shared left-docked SlidePane (§17-18: nav stack, prev/next over the wiki
directory, fullscreen, bookmark star, prefers-reduced-motion) hosts story
pages, redesigned country profiles (flag/leader-photo/status header,
§6.1), party/person/NSA/org/alliance wiki pages (§6.2), compare view
(§24), stories directory (§8), credits (§22), API-key onboarding that
writes .env and live-tests keys (§14), bookmarks (§21) and personal
annotations (§19, visually distinct from AI output). geocode_confidence +
global_relevance_score computed at extraction (§3/§9 — dim/dashed
low-confidence markers, default-on relevance filter, shared continent
filter), correlation reasoning trace (§20), deterministic headline
normalization + on-demand cached deep summaries (§11), 11 generative
music presets incl. WebSocket-driven data sonification (§12.2-12.3),
in-app breaking alerts (§25), one-click snapshot export (§23),
thin-coverage badges, freshness stamps, colorblind-safe palette and
first-launch LOD calibration (§15). Long-horizon prognosis (§10) rides
the same graded predictions pathway and stays behind
forecasting.enabled=false. Wikipedia background content syncs on the
weekly reference cadence; Grokipedia stays OPEN/off per §7.1 (no official
API). Central-bank/economic + pan-regional sources added, GDELT conflict
backfill + activity-scaled dynamic polling config-gated (§13).
Network-dependent syncs remain proxy-blocked in the build sandbox and
degrade cleanly (retry per cycle).

## Status (v3)

**The v3 legendary tier (docs/globegrid_v3_legendary_manual.pdf, REV 3.3,
Phases J-AA / Sections 2-26) is built on top of v1+v2 (2026-07-06).**
Verified in this repo: schema v3 in-place migration; hash-chained
provenance on facts + predictions with a real tamper test (altered row →
chain breaks at that rowid, `scripts/verify_provenance.py` + status-panel
indicator); lineage_edges written on historical_chain links + butterfly
lineage view; devil's-advocate pass (downgrade-only) and multi-agent
debate wired as independently-failing layers after the primary causal
call; story version history + word-diff UI; per-category self-tuned
thresholds moving on real feedback votes (0.78→0.79 observed, clamped
band); z-score+CUSUM anomaly flags on the instability loop; entity layer
seeded (77 countries, 8 alliances, 6 conflicts w/ parties, 9 NSAs, 7 orgs,
5 treaties, 7 sanctions, 10 persons, 8 elections, 28 curated strategic
locations + capitals); click-a-country → profile (point-in-polygon over
vendored Natural Earth boundaries); conflict tabs = filtered feeds with
auto-suggested tags + one-click confirm (verified end-to-end on a live
Kyiv story); analyst orb/panel with two-path retrieval, citation chips,
forecast-question routing, empty-retrieval honesty, and auto-navigation
(ask about Ukraine → conflict tab opens, verified headless); satellites/
marked/bloc overlays; generative music engine; timelapse export;
WebXR entry (feature-detected — needs real hardware to exercise).
**forecasting.enabled ships FALSE** per §7 — do not flip it without
resolved scorecard history. Claude-dependent v3 paths (debate, devil's
advocate, agenda/bilateral synthesis, analyst prose) verified in their
graceful no-key fallbacks; Wikidata/World Bank/CelesTrak syncs are
proxy-blocked in the build sandbox and degrade cleanly (retry per cycle).
v3 deviations: timelapse uses MediaRecorder/webm (not a hand-rolled
WebCodecs MP4 muxer); satellite propagation is simplified two-body from
TLE elements (not full SGP4) — both documented at point of use.

## Status

**v1 (all phases 1-6) AND the v2 expansion addendum (Phases A-I, Sections
1-10) built and verified (2026-07-06), zero-install edition.** The v2 spec is
`docs/globegrid_v2_expansion_addendum.pdf` (REV 2.0) — §-references in code
comments cite it. Verified end-to-end in this repo on top of the v1 checks:
schema v2 migration upgrading a genuine v1 database in place (rows preserved);
`event_created` pushed over WS before correlation, then story upgrade;
near-duplicate wire-copy marked and excluded from counts; sentiment stored;
entity canonicalization feeding a correlation boost; gazetteer resolving 32k
GeoNames places; `as_of` time capsule on all read routes + scrubber UI; FTS5
search; entity graph; watchlist CRUD; CSV export; daily briefing (non-AI
fallback verified); uptime history; budget-aware skips; nightly backup
function; config validation failing loud; graphics v2 (standard/high/ultra:
day/night + city lights, starfield, fresnel halo, particle trails, bursts,
heatmap, ghost trail, bloom, fly-to, idle tour, palette, deep links,
bookmarks) screenshot-verified in headless Chromium. Claude-dependent paths
(causal narratives, prediction grading, second-order scan, briefing
synthesis, translation) need `CLAUDE_API_KEY`; all have verified graceful
fallbacks. Live-source ingestion still needs first-real-run verification via
the sources panel (build sandbox is proxy-blocked); ACLED is OPEN pending
access approval; shipping/maritime remains OPEN per the addendum.

## Phase plan (manual Section 15)

1. **Data layer** — schema, migrations, ingestion (Section 4 sources), extraction, fact chain — DONE
2. **Correlation + causal engine** — Sections 5.4/5.5/9 — DONE
3. **API layer** — Section 8 REST + WS contract — DONE
4. **Tier 1 graphics** — synthetic dataset (Section 12) — DONE
5. **Wire graphics to real API** — done; purge synthetic via `python scripts/generate_synthetic_data.py --purge`
6. **Remaining features + Tiers 2/3** — instability, bias view, translation, resilience, Tier 2/3 — DONE

## Zero-install adaptations (owner-requested; deviations from the manual)

The owner required: no PostgreSQL/PostGIS/pgvector, no pip install, no npm —
clone and `python run.py`. Swaps, each documented at the point of use:

| Manual | This build |
|---|---|
| PostgreSQL 16 + PostGIS | SQLite (stdlib), WAL mode; `location_lat`/`location_lon` + haversine in `processing/gazetteer.py` |
| pgvector `vector(384)` | `embedding BLOB` (float32[384]) + Python cosine — the manual's own sanctioned fallback (§3.2) |
| sentence-transformers MiniLM | Auto-used **if installed**; otherwise deterministic 384-dim hashing embedder (`processing/embed.py`). Cross-outlet matching is weaker with the fallback. Installing sentence-transformers later is safe: the whole chain is re-embedded automatically at next startup (`ensure_embedder_consistency`). |
| FastAPI + APScheduler | stdlib `http.server` + tiny router (`api/router.py`) + daemon-thread scheduler (`ingestion/scheduler.py`) |
| FastAPI WebSocket | hand-rolled RFC 6455 (`websocket/feed_socket.py`), envelope exactly per §8.2 |
| React + Vite (.jsx) | buildless ES modules (.js), same component layout under `frontend/src/` |
| three.js globe | self-contained WebGL2 renderer (`Tier1Globe.js`), coastlines vendored in `data/worldCoastline.js` |
| anthropic SDK | raw `urllib` calls (`processing/causal_link.py`), §9 prompt verbatim |
| Mapbox/Leaflet Tier 2 | 2D canvas renderer, no CDN |

Unchanged from the manual: the Section 6 schema (field names verbatim, incl.
quoted `"where"`), Section 7 config values, Section 8 API contract, Section 9
prompt (verbatim), Section 10 logging/backoff policy, Section 12 synthetic
spec, AGPL-3.0 + .gitignore (§14).

## Ground rules (from the manual — still binding)

- Every tunable lives in `backend/config.yaml` / `.env` — never hardcode
  thresholds, intervals, weights, or model names.
- `extracted_facts` rows are never deleted or expired (the fact chain).
- No content rendered without a resolvable, visible source link (§6.8 —
  `source_id` NOT NULL chains in the schema).
- One Claude call per new/updated cluster, cached on the story, regenerated
  only when members are added; malformed JSON → one retry → low/null fallback.
- A failing source degrades (backoff ×2 up to 1800s), never crashes or blocks.
- Synthetic rows always carry `is_synthetic=1` and must stay purgeable in one
  operation.

## v2 notes

- New tables: canonical_entities/entity_aliases, predictions,
  second_order_links, daily_briefings, watchlist_items,
  source_uptime_history, gazetteer_places(+aliases), FTS5 virtual tables.
- Optional upgrades, all auto-detected at startup (same pattern as
  sentence-transformers): `spacy` + `en_core_web_sm` (NER, §3.2),
  `vaderSentiment` (sentiment, §3.5).
- Gazetteer data is vendored (`backend/data/gazetteer_cities.tsv.gz`,
  GeoNames-derived via geonamescache) and imported once at startup.
  **Attribution required (CC BY 4.0)**: "Geocoding data © GeoNames" — shown
  in README, /api/config, and the sources panel. Do not remove.
- ANN indexing (§3.6) deliberately deferred per the addendum ("build when
  the linear scan is actually measured as slow"); the in-memory
  FactChainCache in correlate.py is the sanctioned intermediate and the
  swap point.

## Commands

```
python run.py                    # start everything (creates DB, seeds, ingests)
python run.py --synthetic        # with demo data
python scripts/generate_synthetic_data.py --purge
python scripts/seed_sources.py   # re-seed/refresh source list
python scripts/import_gazetteer.py [--force]   # re-import gazetteer
```

No test suite yet; verification is behavioral (see Status). Logs: `logs/app.log`
(JSON lines, rotating) + console. DB: `backend/data/talkdiplomacy_live.db`
(gitignored).
