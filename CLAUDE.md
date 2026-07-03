# CLAUDE.md

## Project

GlobeGrid (TalkDiplomacy Live) is a real-time global event intelligence
system: it ingests news, structured event data, disasters, market data,
and social signal; extracts structured facts from every item into a
permanent fact chain; detects cross-stream correlation (a market move, a
news story, and a social spike describing the same event, or a new event
linking to something months old); and generates AI causal storylines,
presented via a live feed, an interactive 3D/2D/light-tier world map, and
story pages. Single user, local machine, Windows native, no containers,
no accounts. v1 scope only — see Appendix A of the manual for deliberately
out-of-scope future multi-user notes.

## Full spec

The complete, authoritative build spec is `docs/talkdiplomacy_live_v1_build_manual.pdf`
(REV 1.2). It is the source of truth for schema, config defaults, API
contract, prompt templates, and every locked decision — read it (or the
relevant section) before making decisions this file doesn't cover. Do not
invent field names, thresholds, or endpoints not present in that document.

## Build sequence (Section 15)

Work proceeds in phases. Do not start a phase until the prior one is
explicitly confirmed working by the project owner.

| Phase | Scope |
|---|---|
| 1 | Data layer — schema, migrations, ingestion for all Section 4 sources, extraction (5.1-5.3, 5.9), fact-chain storage in `extracted_facts` |
| 2 | Correlation + causal engine — Section 5.4 / 5.5 / 9, tested against real Phase 1 data |
| 3 | API layer — Section 8 REST routes + WebSocket feed |
| 4 | Tier 1 graphics — built against the Section 12 synthetic dataset, independent of Phases 1-3 timing |
| 5 | Wire graphics to the real API from Phase 3; purge `_synthetic` rows |
| 6 | Remaining features + Tiers 2/3 — instability index, bias view, multi-language, resilience hardening |

Current status: **Phase 1, Phase 2, and Phase 3 implemented and verified locally.**

Phase 1 — schema/migrations/ingestion/extraction/embedding, verified against
real Postgres 16 + PostGIS + pgvector: migration applies cleanly,
`db_bootstrap.sql` extension creation, per-source-type extraction into
`events`/`extracted_facts`, pgvector `vector(384)` storage round-trip all
confirmed. Live network calls to the actual RSS/GDELT/USGS/Alpha
Vantage/Reddit endpoints and the sentence-transformers model download were
not exercised in the build sandbox (network policy), so a first run on the
real machine should be watched once for source-specific surprises.

Phase 2 — `backend/app/processing/correlate.py` (Stage 4, Section 5.4) and
`causal_link.py` (Stage 5, Section 5.5/9), verified against real Phase 1
schema with hand-seeded fixtures (real semantic embeddings weren't available
in the sandbox either, same network constraint as Phase 1's model download —
fixtures used deterministic vectors instead): confirmed a same-window
cross-source match (two independently-sourced events describing one
earthquake correctly merge into one story, including their extracted_facts),
a historical-chain match (two facts ~120 days apart, well beyond
same_window_max_gap_hours, correctly linked only via the historical path),
and correct non-clustering of an unrelated item. One correctness bug was
found and fixed during testing: an event and its own extracted_fact (same
underlying raw item) were being matched against each other as if they were
independent cross-stream evidence — correlate.py now explicitly excludes an
item from matching its own parent/child record. The causal-linker's JSON
shape validation, malformed-output retry, and low-confidence/null-narrative
fallback (Section 9) were verified with a mocked Claude response, since no
live CLAUDE_API_KEY/network was available in the sandbox — the real
end-to-end LLM call needs a first supervised run on the real machine.

Phase 3 — `backend/app/main.py` (FastAPI entrypoint), `backend/app/api/
routes_{stories,events,map,status}.py` (Section 8.1), and `backend/app/
websocket/feed_socket.py` (Section 8.2), verified against a real running
server (uvicorn) backed by real Postgres with Phase 1/2 data: every REST
endpoint hit with curl and returning correct data (bbox filtering on
`/api/events` correctly narrowed 3 events to the 2 within a Chile bounding
box; `/api/map/clusters` correctly returns individual pins below the
15-pin/300km threshold; `/api/stories/{id}` correctly resolves outbound
links per Section 6.8 by reading them back out of `raw_items.raw_content`,
since that link isn't preserved on `events`/`extracted_facts` themselves).
The WS `/ws/feed` envelope was verified end-to-end with a real WebSocket
client: connected, triggered a new Phase 2 correlation pass in a separate
process, and confirmed a `story_created` message arrived matching the exact
Section 8.2 envelope shape. Two real bugs were found and fixed during this
testing: (1) `correlate.py`'s match-logging call crashed on numpy
`float32` values, since pgvector returns embeddings as numpy arrays, not
plain Python floats — embeddings are now cast to `float` on load; (2) the
WebSocket broadcaster was silently dropping every connection on its first
send, because `WebSocket.send_json()` uses plain `json.dumps` (unlike
FastAPI's HTTP responses, which run through `jsonable_encoder`
automatically) and story payloads contain raw `datetime` objects —
`ConnectionManager.broadcast()` now runs `jsonable_encoder` explicitly and
logs (rather than silently swallows) any send failure. `GET /api/instability`
is wired and correctly returns an empty result for now, since
`instability_scores` isn't populated until Phase 6.

Phase 4 — `scripts/generate_synthetic_data.py` (Section 12: 300 events /
40 population centers / 60 stories / 7 days of hourly instability scores,
all flagged `_synthetic`, written to both the DB and
`frontend/src/data/syntheticDataset.js`) and the Tier 1 frontend:
`Tier1Globe.jsx` (procedural three.js globe — no texture assets — with
pulsing category-colored event points, animated correlation threads between
story members, drag/zoom/hover/click, atmosphere glow), `TierDetector.js`
(Section 11.2 rules + localStorage override), `LiveFeed.jsx`,
`StoryPage.jsx` (all Section 5.3 elements including the connected-history
panel), wired through a provider abstraction
(`src/data/dataProvider.js`) so Phase 5 swaps data sources without touching
rendering code. Verified in a real Chromium via Playwright at the 500-event
Section 11.3 stress level: 1.7s to interactive (budget <4s), tier override
switches live and persists across reload, story page renders from feed and
map clicks. The 60fps budget could not be validated in the sandbox — no
GPU, SwiftShader software rendering caps ~15fps — needs a check on the real
machine's GPU.

Phase 5 — frontend wired to the real API: `src/api/client.js` (Section 8.1
endpoints), `src/api/socket.js` (full Section 8.2 client contract:
exponential-backoff reconnect, fallback to 15s REST polling of
`/api/stories?since=` if the socket isn't back within 60s, polling stops on
first successful reconnect), `src/api/liveProvider.js` swapped in as the
active `dataProvider`. Verified end-to-end in a real browser against the
real backend: feed/globe/story pages render from live `/api/*` data; a new
story created by a real Phase 2 correlation pass appeared in the open feed
via WS push (61→62 cards); and the resilience path was physically tested —
backend killed → `reconnecting` at t≈0, `polling` at exactly t=60s, backend
restarted → recovered to `websocket` at t=62s. `scripts/purge_synthetic.py`
then purged all `_synthetic` rows in one transaction (verified: 60 stories /
300 events / 234 members / 169 scores removed; real rows and
`extracted_facts` untouched). On the real machine, run
`generate_synthetic_data.py` only if you want the Phase 4 demo data, and
`purge_synthetic.py` after confirming real wiring.

Phase 6 — remaining features + lighter tiers, all verified in-browser
against the real backend: `backend/app/processing/instability.py`
(Section 5.6 weighted formula, all weights/window/interval from
config.yaml, transparent component_breakdown, registered on the scheduler
at recompute_interval_seconds) with the trend line rendered on the
homepage; the scheduler now also runs the full Stage 2-5 pipeline job
(interval derived as the minimum configured ingestion interval) and is
started by the FastAPI lifespan (disable with SCHEDULER_ENABLED=0);
bias/blindspot view (Section 5.7) on story pages grouping member coverage
by outlet with the curated leaning labels; POST /api/translate
(Section 5.8 — display-time only, original always preserved, graceful 503
without CLAUDE_API_KEY) with a translate/show-original toggle on story
summaries; the Section 5.10 system-status panel in the UI; Tier 2
(Leaflet flat map, category/severity pins, Section 5.2 cluster collapse
via /api/map/clusters, click-to-expand) and Tier 3 (instant list view).
The Section 10.2 failure-isolation policy was deliberately tested: a
simulated dead source degraded to `down` with backoff 120→240→480→960→
1800s (capped), never blocked the healthy source's writes, and reset to
its base interval + `ok` on first success. Outstanding items needing the
real machine: live end-to-end runs of every Section 4 source, the real
Claude causal-link/translation calls, sentence-transformers model
download, the Tier 1 60fps check on real GPU, and OSM tile loading for
Tier 2 (all blocked by sandbox network policy / lack of GPU — the
sandbox-testable behavior around each is verified).

## Key constraints to remember

- Every rendered fact/event/story must trace back to a non-nullable `source_id` — schema-enforced (Section 6.8), not just a UI convention.
- All tunable thresholds/intervals/weights live in `backend/config.yaml` (Section 7.2) — never hardcoded inline.
- `extracted_facts` rows are never deleted or expired.
- License is AGPL-3.0; `.gitignore` and `LICENSE` were committed before any application code (Section 14).
