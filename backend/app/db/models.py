"""Section 6 schema (v1 manual) + v2 addendum additions — SQLite, field
names preserved verbatim.

Deviations from the PostgreSQL original (documented in CLAUDE.md):
  - geography(Point,4326)  -> location_lat / location_lon REAL columns;
    radius math is done in Python (haversine) instead of PostGIS.
  - vector(384)            -> embedding BLOB (packed float32[384]);
    cosine similarity computed in Python — the manual's own sanctioned
    fallback path (Section 3.2).
  - jsonb                  -> TEXT holding JSON.
  - uuid                   -> TEXT (uuid4 hex).
  - `where` is a SQL keyword; the column keeps the manual's exact name and
    is always double-quoted in SQL.
  - is_synthetic INTEGER flag implements the Section 12.2 `_synthetic`
    marker so synthetic rows can be purged in a single operation.

v2 additions (expansion addendum):
  - sources.kind ('reported'|'official') — addendum §1.2 official-statement tag
  - extracted_facts: canonical_entity_ids (§3.1), duplicate_of_fact_id (§3.3),
    sentiment (§3.5)
  - canonical_entities / entity_aliases (§3.1)
  - predictions (§3.4), daily_briefings (§6.1), watchlist_items (§6.2),
    source_uptime_history (§7.1), gazetteer_places (§10.2),
    second_order_links (§3.7)
  - FTS5 full-text index over stories + facts (§6.4), trigger-maintained,
    skipped gracefully if this Python's SQLite lacks FTS5.

Attribution is schema-enforced (Section 6.8): extracted_facts.source_id and
raw_items.source_id are NOT NULL; events reach a source via raw_item_id.
Fresh installs get the full v2 schema; existing v1 databases are upgraded
in place by migrate().
"""

import json
import struct
import uuid
from datetime import datetime, timezone

from .session import get_conn, write_tx

SCHEMA_VERSION = 8

# 'gdelt'/'gdelt_events' stay valid CHECK values only so any leftover row on
# an un-migrated DB can still be read long enough for purge_gdelt() to delete
# it (db.session import is a startup-order edge case); GDELT is PERMANENTLY
# BANNED as of v7.4.1 — no fetcher, no seeder, and no code path may ever
# create a row of either type again (see ingestion/backfill.py purge_gdelt,
# ingestion/scheduler.py _is_gdelt, processing/extract.py process_pending).
# v7.4.1 — 'archive' is the curated-history source type (was mislabeled
# 'gdelt' purely for CHECK-constraint compatibility, which conflated real
# GDELT junk with our own hand-curated historical packs).
SOURCE_TYPES = ("rss", "gdelt", "gdelt_events", "usgs", "market", "reddit",
                "firms", "volcano", "wikipedia", "wiki_views", "mastodon",
                "bluesky", "opensky", "acled", "ais", "nightlights",
                "archive", "synthetic")

DDL = f"""
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- 6.1 sources (+ v2: kind, expanded type list)
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN {SOURCE_TYPES!r}),
  url TEXT NOT NULL,
  leaning TEXT NOT NULL DEFAULT 'n/a' CHECK (leaning IN ('left','center','right','n/a')),
  poll_interval_seconds INTEGER NOT NULL,
  health_status TEXT NOT NULL DEFAULT 'ok' CHECK (health_status IN ('ok','degraded','down')),
  last_fetched_at TEXT,
  last_error TEXT,
  kind TEXT NOT NULL DEFAULT 'reported' CHECK (kind IN ('reported','official')),
  attribution TEXT,
  reliability_tier TEXT NOT NULL DEFAULT 'medium'
    CHECK (reliability_tier IN ('high','medium','low')),
  is_active INTEGER NOT NULL DEFAULT 1   -- v6 §2: retired sources (GDELT) keep
                                         -- their rows for fact-chain attribution
                                         -- but stop polling
);

-- 6.2 raw_items
CREATE TABLE IF NOT EXISTS raw_items (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  raw_content TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  processed INTEGER NOT NULL DEFAULT 0,
  processing_error TEXT,
  external_id TEXT,
  UNIQUE (source_id, external_id)
);

-- 6.3 events
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  raw_item_id TEXT NOT NULL REFERENCES raw_items(id),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  location_lat REAL,
  location_lon REAL,
  location_name TEXT,
  -- v8.13 — widened taxonomy (owner: "redo the categorization engine … come up
  -- with new types"). 'technology' finally storable (it was in the classifier +
  -- UI since v6.6 but the CHECK rejected it, so tech news fell into finance/
  -- geopolitics/other); 'domestic' = internal politics/crime/civil unrest that
  -- isn't international geopolitics; 'health' = disease/pandemic/public-health.
  category TEXT NOT NULL CHECK (category IN ('geopolitics','finance','disaster','conflict','technology','domestic','health','other')),
  severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
  occurred_at TEXT NOT NULL,
  embedding BLOB,
  is_synthetic INTEGER NOT NULL DEFAULT 0,
  conflict_id TEXT,
  geocode_confidence REAL,
  global_relevance_score REAL,
  development_type TEXT CHECK (development_type IN ('conflict','military')),
  admin_uid INTEGER  -- v8 §4: the ADM1 unit this event lands in (admin_atlas)
);
CREATE INDEX IF NOT EXISTS idx_events_occurred ON events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_admin_uid ON events(admin_uid);

-- 6.3b v8 §4 — the Administrative Atlas: a variable-depth hierarchy of
-- administrative units (ADM1 provinces/states now; districts/precincts as the
-- deeper-tier data lands). Boundaries themselves are vendored + rendered from
-- geopolitics/admin_atlas.py; THIS table is the queryable registry (ancestry,
-- children, temporal validity, event linkage). adm_level is the depth (1 = the
-- province tier), parent_uid the tree edge (NULL at ADM1, will point at a
-- country/ADM0 node once deeper tiers exist), path a materialized "USA/CA/…"
-- ancestry string for cheap prefix queries. effective_from/effective_to give
-- every unit temporal validity (Q3): a unit real only 1991→present carries
-- effective_from='1991-…'; the time-capsule (as_of) reads the epoch valid at a
-- date. NULL effective_to = still current.
CREATE TABLE IF NOT EXISTS administrative_units (
  admin_uid INTEGER PRIMARY KEY,
  country_id TEXT,            -- iso3 (adm0_a3) the unit belongs to
  adm_level INTEGER NOT NULL DEFAULT 1,
  parent_uid INTEGER,        -- tree edge to the enclosing unit (NULL at top)
  path TEXT,                 -- materialized ancestry, e.g. 'USA/California'
  name TEXT NOT NULL,
  name_local TEXT,           -- endonym / local-script name when known
  unit_type TEXT,            -- 'State','Province','Region',… (source type_en)
  centroid_lat REAL,
  centroid_lon REAL,
  bbox_json TEXT,            -- [minLon,minLat,maxLon,maxLat] for pan/zoom
  source TEXT,               -- provenance: 'naturalearth-10m','geoboundaries',…
  effective_from TEXT,       -- ISO date the unit became valid (NULL = always)
  effective_to TEXT          -- ISO date it ceased (NULL = still current)
);
CREATE INDEX IF NOT EXISTS idx_admin_parent ON administrative_units(parent_uid);
CREATE INDEX IF NOT EXISTS idx_admin_country_level
  ON administrative_units(country_id, adm_level);

-- 6.4 extracted_facts (the fact chain — never deleted, never expired)
-- v2: canonical_entity_ids, duplicate_of_fact_id, sentiment
CREATE TABLE IF NOT EXISTS extracted_facts (
  id TEXT PRIMARY KEY,
  event_id TEXT REFERENCES events(id),
  source_id TEXT NOT NULL REFERENCES sources(id),
  who TEXT NOT NULL,
  what TEXT NOT NULL,
  "where" TEXT,
  when_occurred TEXT NOT NULL,
  embedding BLOB,
  created_at TEXT NOT NULL,
  is_synthetic INTEGER NOT NULL DEFAULT 0,
  canonical_entity_ids TEXT,
  duplicate_of_fact_id TEXT REFERENCES extracted_facts(id),
  sentiment REAL,
  row_hash TEXT,
  prev_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_facts_created ON extracted_facts(created_at);

-- 6.5 stories (+ v3: debate §2, devil's advocate §3, conflicts §15)
CREATE TABLE IF NOT EXISTS stories (
  id TEXT PRIMARY KEY,
  headline TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  causal_narrative TEXT,
  confidence TEXT NOT NULL DEFAULT 'low' CHECK (confidence IN ('high','medium','low')),
  first_seen_at TEXT NOT NULL,
  last_updated_at TEXT NOT NULL,
  needs_causal_refresh INTEGER NOT NULL DEFAULT 1,
  is_synthetic INTEGER NOT NULL DEFAULT 0,
  disagreement_score REAL,
  debate_generated_at TEXT,
  counter_argument TEXT,
  confidence_pre_devil_advocate TEXT,
  conflict_id TEXT,
  suggested_conflict_id TEXT,
  story_type TEXT NOT NULL DEFAULT 'acute_event',
  deep_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_stories_updated ON stories(last_updated_at);

-- 6.6 story_members
CREATE TABLE IF NOT EXISTS story_members (
  story_id TEXT NOT NULL REFERENCES stories(id),
  event_id TEXT REFERENCES events(id),
  fact_id TEXT REFERENCES extracted_facts(id),
  linked_via TEXT NOT NULL CHECK (linked_via IN ('same_window','historical_chain')),
  linked_at TEXT NOT NULL,
  is_synthetic INTEGER NOT NULL DEFAULT 0,
  UNIQUE (story_id, event_id, fact_id)
);
CREATE INDEX IF NOT EXISTS idx_members_story ON story_members(story_id);
CREATE INDEX IF NOT EXISTS idx_members_event ON story_members(event_id);

-- 6.7 instability_scores
CREATE TABLE IF NOT EXISTS instability_scores (
  id TEXT PRIMARY KEY,
  score REAL NOT NULL,
  computed_at TEXT NOT NULL,
  component_breakdown TEXT NOT NULL,
  is_synthetic INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_instability_time ON instability_scores(computed_at);

-- v2 §3.1 entity canonicalization
CREATE TABLE IF NOT EXISTS canonical_entities (
  id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS entity_aliases (
  alias TEXT PRIMARY KEY,
  canonical_id TEXT NOT NULL REFERENCES canonical_entities(id)
);

-- v2 §3.4 prediction tracking
CREATE TABLE IF NOT EXISTS predictions (
  id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL REFERENCES stories(id),
  consequence_text TEXT NOT NULL,
  predicted_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','confirmed','refuted')),
  resolved_at TEXT,
  confirming_fact_id TEXT REFERENCES extracted_facts(id),
  kind TEXT NOT NULL DEFAULT 'retrospective_consequence'
    CHECK (kind IN ('retrospective_consequence','forward_forecast')),
  horizon_hours INTEGER,
  region TEXT,
  row_hash TEXT,
  prev_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_predictions_story ON predictions(story_id);
CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(status);

-- v2 §3.7 second-order causal links
CREATE TABLE IF NOT EXISTS second_order_links (
  id TEXT PRIMARY KEY,
  story_a_id TEXT NOT NULL REFERENCES stories(id),
  story_b_id TEXT NOT NULL REFERENCES stories(id),
  narrative TEXT,
  confidence TEXT NOT NULL DEFAULT 'low' CHECK (confidence IN ('high','medium','low')),
  created_at TEXT NOT NULL,
  UNIQUE (story_a_id, story_b_id)
);

-- v2 §6.1 daily briefings
CREATE TABLE IF NOT EXISTS daily_briefings (
  id TEXT PRIMARY KEY,
  briefing_date TEXT NOT NULL UNIQUE,
  content TEXT NOT NULL,
  generated_at TEXT NOT NULL
);

-- v2 §6.2 watchlists
CREATE TABLE IF NOT EXISTS watchlist_items (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('entity','region','category')),
  value TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (kind, value)
);

-- v2 §7.1 source uptime history
CREATE TABLE IF NOT EXISTS source_uptime_history (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id),
  checked_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ok','degraded','down'))
);
CREATE INDEX IF NOT EXISTS idx_uptime_source ON source_uptime_history(source_id, checked_at);

-- v3 §2 multi-agent debate
CREATE TABLE IF NOT EXISTS causal_debate (
  id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL REFERENCES stories(id),
  persona TEXT NOT NULL CHECK (persona IN ('skeptic','historian','optimist')),
  narrative TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  UNIQUE (story_id, persona)
);

-- v3 §5 self-tuning thresholds
CREATE TABLE IF NOT EXISTS correlation_feedback (
  id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL REFERENCES stories(id),
  category TEXT NOT NULL,
  vote TEXT NOT NULL CHECK (vote IN ('correct','incorrect')),
  voted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS category_thresholds (
  category TEXT PRIMARY KEY,
  same_window_threshold REAL NOT NULL,
  historical_threshold REAL NOT NULL,
  last_adjusted_at TEXT
);

-- v3 §6 anomaly / changepoint detection
CREATE TABLE IF NOT EXISTS anomaly_flags (
  id TEXT PRIMARY KEY,
  detected_at TEXT NOT NULL,
  method TEXT NOT NULL CHECK (method IN ('zscore','cusum')),
  score_value REAL NOT NULL,
  z_or_cusum_value REAL NOT NULL
);

-- v3 §8 butterfly-effect lineage
CREATE TABLE IF NOT EXISTS lineage_edges (
  id TEXT PRIMARY KEY,
  from_fact_id TEXT NOT NULL REFERENCES extracted_facts(id),
  to_fact_id TEXT NOT NULL REFERENCES extracted_facts(id),
  via_story_id TEXT NOT NULL REFERENCES stories(id),
  created_at TEXT NOT NULL,
  UNIQUE (from_fact_id, to_fact_id, via_story_id)
);
CREATE INDEX IF NOT EXISTS idx_lineage_from ON lineage_edges(from_fact_id);

-- v3 §12 story version history
CREATE TABLE IF NOT EXISTS story_narrative_versions (
  id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL REFERENCES stories(id),
  causal_narrative TEXT,
  confidence TEXT NOT NULL,
  superseded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_versions_story ON story_narrative_versions(story_id);

-- v3 §13 country profiles (+ v4 §5.2 status, iso2/flags, freshness)
CREATE TABLE IF NOT EXISTS countries (
  id TEXT PRIMARY KEY,               -- ISO 3166-1 alpha-3
  name TEXT NOT NULL,
  capital TEXT,
  region TEXT,
  government_type TEXT,
  boundary_ref TEXT,
  status TEXT NOT NULL DEFAULT 'un_member' CHECK (status IN
    ('un_member','observer_state','de_facto','disputed_territory','territory')),
  iso2 TEXT,
  population INTEGER,
  last_updated_at TEXT,
  flag_image_url TEXT,
  -- v6 §14/§15/§16 — territory linkage + profile depth + thematic-map data.
  -- Demographic figures are seeded from authoritative published datasets
  -- (World Bank / UNDP / UN M49 / Pew) and refreshed by the accuracy
  -- pipeline (v6 §30) — never LLM-guessed.
  official_name TEXT,
  languages TEXT,                    -- JSON array of official/major languages
  gdp_usd REAL,
  hdi REAL,
  gdp_per_capita_usd REAL,
  area_km2 REAL,
  sovereign_id TEXT REFERENCES countries(id),   -- territories -> overlord
  dominant_religion TEXT,
  dominant_language TEXT
);
CREATE TABLE IF NOT EXISTS country_leadership (
  country_id TEXT NOT NULL REFERENCES countries(id),
  role TEXT NOT NULL CHECK (role IN ('head_of_state','head_of_government')),
  name TEXT NOT NULL,
  party TEXT,
  since_date TEXT,
  last_refreshed_at TEXT,
  image_url TEXT,
  PRIMARY KEY (country_id, role)
);
CREATE TABLE IF NOT EXISTS country_legislature (
  country_id TEXT PRIMARY KEY REFERENCES countries(id),
  chamber_name TEXT,
  ruling_coalition TEXT,
  composition_summary TEXT,
  last_refreshed_at TEXT
);
CREATE TABLE IF NOT EXISTS country_agenda_synthesis (
  country_id TEXT PRIMARY KEY REFERENCES countries(id),
  geopolitical_agenda TEXT,
  economic_agenda TEXT,
  stance_summary TEXT,
  source_story_ids TEXT,
  generated_at TEXT
);
CREATE TABLE IF NOT EXISTS country_trade_stats (
  country_id TEXT PRIMARY KEY REFERENCES countries(id),
  gdp_usd REAL,
  major_trade_partners TEXT,
  key_exports TEXT,
  as_of_date TEXT
);

-- v3 §14 alliances & blocs
CREATE TABLE IF NOT EXISTS alliances (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL CHECK (type IN ('military','economic','political','regional')),
  founded_date TEXT,
  description TEXT,
  last_updated_at TEXT
);
CREATE TABLE IF NOT EXISTS alliance_memberships (
  alliance_id TEXT NOT NULL REFERENCES alliances(id),
  country_id TEXT NOT NULL REFERENCES countries(id),
  status TEXT NOT NULL DEFAULT 'member' CHECK (status IN ('member','observer','candidate')),
  joined_date TEXT,
  PRIMARY KEY (alliance_id, country_id)
);

-- v3 §15 ongoing conflicts
CREATE TABLE IF NOT EXISTS conflicts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  region TEXT,
  started_at TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','ceasefire','frozen','resolved')),
  summary TEXT,
  last_updated_at TEXT
);
CREATE TABLE IF NOT EXISTS conflict_parties (
  conflict_id TEXT NOT NULL REFERENCES conflicts(id),
  party_type TEXT NOT NULL CHECK (party_type IN ('country','non_state_actor')),
  country_id TEXT REFERENCES countries(id),
  non_state_actor_id TEXT,
  role TEXT NOT NULL DEFAULT 'belligerent'
    CHECK (role IN ('belligerent','mediator','backer')),
  side TEXT,   -- v6 §8 War Mode: parties on one side share one color ('a'/'b'/NULL)
  UNIQUE (conflict_id, party_type, country_id, non_state_actor_id)
);

-- v3 §16 non-state actors
CREATE TABLE IF NOT EXISTS non_state_actors (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  actor_type TEXT NOT NULL CHECK (actor_type IN
    ('militant','terrorist','insurgent','cartel','political_movement','other')),
  primary_region TEXT,
  affiliated_state_id TEXT REFERENCES countries(id),
  active_since TEXT,
  canonical_entity_id TEXT,
  description_synthesis TEXT,
  source_story_ids TEXT,
  last_updated_at TEXT,
  base_lat REAL,
  base_lon REAL
);

-- v5 §11 non-state-actor rough territory/zone shading (deliberately coarse,
-- descriptive geopolitical context — not precise operational boundaries)
CREATE TABLE IF NOT EXISTS non_state_actor_zones (
  id TEXT PRIMARY KEY,
  non_state_actor_id TEXT NOT NULL REFERENCES non_state_actors(id),
  zone_geojson TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'reported'
    CHECK (confidence IN ('established','contested','reported')),
  last_updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_nsa_zones_actor ON non_state_actor_zones(non_state_actor_id);

-- v6 §8 — War Mode sub-national factions, scoped to conflicts (NOT the global
-- countries table): minor factions and internal control areas that only render
-- inside a conflict's dedicated layout (e.g. Tuareg-controlled Azawad in Mali)
CREATE TABLE IF NOT EXISTS conflict_subfactions (
  id TEXT PRIMARY KEY,
  conflict_id TEXT NOT NULL REFERENCES conflicts(id),
  name TEXT NOT NULL,
  zone_geojson TEXT,                 -- rough area, same style as NSA zones (§21)
  side TEXT,                         -- which side this faction aligns with, if any
  UNIQUE (conflict_id, name)
);
CREATE INDEX IF NOT EXISTS idx_subfactions_conflict ON conflict_subfactions(conflict_id);

-- v6 §27 — Story Threads: macro-trend grouping layer ABOVE individual stories
-- ('Strait of Hormuz Developments'), the primary browsing unit in the Stories
-- directory. Individual stories stay visible within a thread — presentation
-- reorganization, not a taxonomy replacement.
CREATE TABLE IF NOT EXISTS story_threads (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,                  -- AI-synthesized overview of the trend
  first_seen_at TEXT NOT NULL,
  last_updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS story_thread_members (
  thread_id TEXT NOT NULL REFERENCES story_threads(id),
  story_id TEXT NOT NULL REFERENCES stories(id),
  PRIMARY KEY (thread_id, story_id)
);
CREATE INDEX IF NOT EXISTS idx_thread_members_story ON story_thread_members(story_id);
-- v6 §27 directory performance: the Stories directory filters by story_type
-- and orders by recency — give that query a real index instead of a scan
CREATE INDEX IF NOT EXISTS idx_stories_type_updated ON stories(story_type, last_updated_at);

-- v6 §11 — site-wide instant translation cache: one row per
-- (content_id, language, field), so re-rendering is instant after the first
-- translation and new content translates once on arrival, not on every view
CREATE TABLE IF NOT EXISTS content_translations (
  content_id TEXT NOT NULL,          -- story/event/thread id
  language TEXT NOT NULL,            -- v5 §2 locale code
  field TEXT NOT NULL,               -- 'headline' | 'summary' | ...
  translated_text TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (content_id, language, field)
);

-- v6 §16 — sub-national areas for area-level thematic map modes (dominant
-- religion/language by region). Seeded from published demographic surveys for
-- the large multi-region countries where country-level dominance is misleading.
CREATE TABLE IF NOT EXISTS subnational_areas (
  id TEXT PRIMARY KEY,
  country_id TEXT NOT NULL REFERENCES countries(id),
  name TEXT NOT NULL,
  zone_geojson TEXT,
  dominant_religion TEXT,
  dominant_language TEXT,
  population INTEGER,
  UNIQUE (country_id, name)
);
CREATE INDEX IF NOT EXISTS idx_subnational_country ON subnational_areas(country_id);

-- v3 §17 marked cities/locations + critical infrastructure
CREATE TABLE IF NOT EXISTS marked_locations (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  category TEXT NOT NULL CHECK (category IN
    ('capital','conflict_zone','strategic_chokepoint','contested_territory','other',
     'semiconductor_fab','rare_earth_site','undersea_cable','energy_pipeline','lng_terminal')),
  country_id TEXT REFERENCES countries(id),
  conflict_id TEXT REFERENCES conflicts(id),
  description TEXT
);

-- v3 §18 international organizations
CREATE TABLE IF NOT EXISTS international_organizations (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  org_type TEXT NOT NULL CHECK (org_type IN
    ('intergovernmental','financial','health','judicial','other')),
  mandate_summary TEXT,
  hq_location TEXT,
  canonical_entity_id TEXT,
  founded_date TEXT,
  posture_synthesis TEXT,
  source_story_ids TEXT,
  last_updated_at TEXT
);

-- v3 §19 bilateral relations
CREATE TABLE IF NOT EXISTS bilateral_relations (
  id TEXT PRIMARY KEY,
  country_a_id TEXT NOT NULL REFERENCES countries(id),
  country_b_id TEXT NOT NULL REFERENCES countries(id),
  status TEXT NOT NULL DEFAULT 'neutral'
    CHECK (status IN ('allied','cooperative','neutral','tense','hostile','conflict')),
  synthesis TEXT,
  source_story_ids TEXT,
  last_updated_at TEXT,
  UNIQUE (country_a_id, country_b_id)
);

-- v3 §20 sanctions regimes
CREATE TABLE IF NOT EXISTS sanctions (
  id TEXT PRIMARY KEY,
  imposing_party_type TEXT NOT NULL
    CHECK (imposing_party_type IN ('country','alliance','international_organization')),
  imposing_party_id TEXT NOT NULL,
  target_country_id TEXT REFERENCES countries(id),
  target_non_state_actor_id TEXT REFERENCES non_state_actors(id),
  reason TEXT,
  imposed_at TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','lifted')),
  source_story_ids TEXT
);

-- v3 §21 treaties & agreements
CREATE TABLE IF NOT EXISTS treaties (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  treaty_type TEXT NOT NULL CHECK (treaty_type IN
    ('trade','nuclear_nonproliferation','peace_accord','environmental','other')),
  signed_at TEXT,
  status TEXT NOT NULL DEFAULT 'in_force'
    CHECK (status IN ('in_force','signed_not_ratified','withdrawn','expired')),
  summary TEXT
);
CREATE TABLE IF NOT EXISTS treaty_signatories (
  treaty_id TEXT NOT NULL REFERENCES treaties(id),
  country_id TEXT NOT NULL REFERENCES countries(id),
  ratified INTEGER NOT NULL DEFAULT 0,
  ratified_date TEXT,
  PRIMARY KEY (treaty_id, country_id)
);

-- v3 §22 notable persons
CREATE TABLE IF NOT EXISTS notable_persons (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role_title TEXT,
  affiliated_country_id TEXT REFERENCES countries(id),
  affiliated_org_id TEXT REFERENCES international_organizations(id),
  affiliated_non_state_actor_id TEXT REFERENCES non_state_actors(id),
  canonical_entity_id TEXT,
  bio_summary TEXT,
  source_story_ids TEXT
);

-- v3 §23 elections tracker
CREATE TABLE IF NOT EXISTS elections (
  id TEXT PRIMARY KEY,
  country_id TEXT NOT NULL REFERENCES countries(id),
  election_type TEXT NOT NULL CHECK (election_type IN
    ('presidential','parliamentary','referendum','other')),
  scheduled_date TEXT,
  status TEXT NOT NULL DEFAULT 'upcoming'
    CHECK (status IN ('upcoming','completed','disputed')),
  result_summary TEXT,
  leadership_refreshed INTEGER NOT NULL DEFAULT 0
);

-- v3 §24 analyst panel
CREATE TABLE IF NOT EXISTS analyst_sessions (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  last_message_at TEXT
);
CREATE TABLE IF NOT EXISTS analyst_messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES analyst_sessions(id),
  role TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content TEXT NOT NULL,
  cited_story_ids TEXT,
  focused_entity_context TEXT,
  suggested_navigation TEXT,
  created_at TEXT NOT NULL
);

-- v4 §5.3 border disputes (claimant_b nullable: non-state claimants, e.g.
-- Polisario for Western Sahara, are described in summary instead)
CREATE TABLE IF NOT EXISTS border_disputes (
  id TEXT PRIMARY KEY,
  claimant_a_id TEXT NOT NULL REFERENCES countries(id),
  claimant_b_id TEXT REFERENCES countries(id),
  territory_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','frozen','resolved')),
  boundary_ref TEXT,
  summary TEXT,
  UNIQUE (claimant_a_id, territory_name)
);

-- v4 §6.2 political parties as first-class linkable entities
CREATE TABLE IF NOT EXISTS political_parties (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  country_id TEXT REFERENCES countries(id),
  ideology_tags TEXT,
  founded_date TEXT,
  canonical_entity_id TEXT,
  last_updated_at TEXT,
  UNIQUE (name, country_id)
);

-- v4 §19 personal annotations (user's own layer, never blended with AI output)
CREATE TABLE IF NOT EXISTS annotations (
  id TEXT PRIMARY KEY,
  target_type TEXT NOT NULL CHECK (target_type IN
    ('story','country','conflict','non_state_actor','alliance','person','party','org')),
  target_id TEXT NOT NULL,
  note_text TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_annotations_target ON annotations(target_type, target_id);

-- v4 §21 bookmarks / reading list (curation, distinct from watchlists)
CREATE TABLE IF NOT EXISTS bookmarks (
  id TEXT PRIMARY KEY,
  target_type TEXT NOT NULL CHECK (target_type IN
    ('story','country','conflict','non_state_actor','alliance','notable_person','party','org')),
  target_id TEXT NOT NULL,
  bookmarked_at TEXT NOT NULL,
  UNIQUE (target_type, target_id)
);

-- v4 §7 external background content (Wikipedia primary; Grokipedia OPEN,
-- behind its own flag) — cached per entity, clearly attributed by origin
CREATE TABLE IF NOT EXISTS entity_background (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  origin TEXT NOT NULL CHECK (origin IN ('wikipedia','grokipedia')),
  title TEXT,
  extract TEXT,
  url TEXT,
  fetched_at TEXT NOT NULL,
  UNIQUE (entity_type, entity_id, origin)
);

-- v2 §10.2 gazetteer
CREATE TABLE IF NOT EXISTS gazetteer_places (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  ascii_name TEXT NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  country_code TEXT,
  admin1_code TEXT,
  population INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_gazetteer_ascii ON gazetteer_places(ascii_name COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS gazetteer_aliases (
  alias TEXT NOT NULL COLLATE NOCASE,
  place_id INTEGER NOT NULL REFERENCES gazetteer_places(id),
  PRIMARY KEY (alias, place_id)
);
"""

FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_stories USING fts5(id UNINDEXED, headline, summary);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_facts USING fts5(id UNINDEXED, who, what, place);
CREATE TRIGGER IF NOT EXISTS trg_fts_stories_ins AFTER INSERT ON stories BEGIN
  INSERT INTO fts_stories (id, headline, summary) VALUES (new.id, new.headline, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS trg_fts_stories_upd AFTER UPDATE OF headline, summary ON stories BEGIN
  DELETE FROM fts_stories WHERE id = old.id;
  INSERT INTO fts_stories (id, headline, summary) VALUES (new.id, new.headline, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS trg_fts_stories_del AFTER DELETE ON stories BEGIN
  DELETE FROM fts_stories WHERE id = old.id;
END;
CREATE TRIGGER IF NOT EXISTS trg_fts_facts_ins AFTER INSERT ON extracted_facts BEGIN
  INSERT INTO fts_facts (id, who, what, place)
  VALUES (new.id, new.who, new.what, COALESCE(new."where", ''));
END;
"""


def fts_available() -> bool:
    try:
        conn = get_conn()
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts_probe USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS _fts_probe")
        conn.commit()
        return True
    except Exception:  # noqa: BLE001 — sqlite build without FTS5
        return False


def _columns(conn, table: str) -> set:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def _upgrade_v1_to_v2() -> None:
    """In-place upgrade of a live v1 database. Additive only — the fact
    chain is never rewritten, only extended. Runs on a dedicated
    connection: the sources-table rebuild needs foreign_keys=OFF and
    legacy_alter_table=ON (so RENAME doesn't rewrite child FK clauses to
    point at the temp name), and PRAGMAs are no-ops inside an open
    transaction on the shared connection."""
    import sqlite3
    from ..config import sqlite_path
    conn = sqlite3.connect(str(sqlite_path()), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # explicit BEGIN/COMMIT — DDL stays atomic
    cols = "id, name, type, url, leaning, poll_interval_seconds, health_status," \
           " last_fetched_at, last_error"
    create_sources_sql = DDL[DDL.index("CREATE TABLE IF NOT EXISTS sources"):
                             DDL.index("-- 6.2")].strip().rstrip(";") + ";"
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("PRAGMA legacy_alter_table=ON")
        conn.execute("BEGIN IMMEDIATE")
        # new columns on extracted_facts
        have = {r["name"] for r in conn.execute("PRAGMA table_info(extracted_facts)")}
        for col, decl in (("canonical_entity_ids", "TEXT"),
                          ("duplicate_of_fact_id", "TEXT REFERENCES extracted_facts(id)"),
                          ("sentiment", "REAL")):
            if col not in have:
                conn.execute(f'ALTER TABLE extracted_facts ADD COLUMN {col} {decl}')
        # recover from a previously interrupted rebuild: restore rows that
        # were stranded in sources_v1
        leftover = conn.execute("SELECT name FROM sqlite_master WHERE type='table'"
                                " AND name='sources_v1'").fetchone()
        if leftover:
            conn.execute(create_sources_sql)
            conn.execute(f"INSERT OR IGNORE INTO sources ({cols}, kind)"
                         f" SELECT {cols}, 'reported' FROM sources_v1")
            conn.execute("DROP TABLE sources_v1")
        # sources: an older CHECK constraint doesn't admit newer types
        # (v2 added 'firms'…; v7.2 adds 'ais'/'nightlights'; v7.4.1 adds
        # 'archive') -> rebuild. Trigger on the newest sentinel so
        # already-migrated DBs still upgrade.
        src_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='sources'"
        ).fetchone()
        if src_sql and "'archive'" not in (src_sql["sql"] or ""):
            conn.execute("ALTER TABLE sources RENAME TO sources_v1")
            conn.execute(create_sources_sql)
            # preserve `kind` if the old table already had it (v2+); an
            # ancient v1 table predates the column, so default it.
            kind_expr = ("kind" if "kind" in _columns(conn, "sources_v1")
                         else "'reported'")
            conn.execute(f"INSERT INTO sources ({cols}, kind)"
                         f" SELECT {cols}, {kind_expr} FROM sources_v1")
            conn.execute("DROP TABLE sources_v1")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def _upgrade_v2_to_v3() -> None:
    """Additive v3 upgrade: new columns on existing tables. New tables come
    from the main DDL executescript (all CREATE IF NOT EXISTS)."""
    import sqlite3
    from ..config import sqlite_path
    conn = sqlite3.connect(str(sqlite_path()), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        additions = {
            "stories": [("disagreement_score", "REAL"),
                        ("debate_generated_at", "TEXT"),
                        ("counter_argument", "TEXT"),
                        ("confidence_pre_devil_advocate", "TEXT"),
                        ("conflict_id", "TEXT"),
                        ("suggested_conflict_id", "TEXT")],
            "events": [("conflict_id", "TEXT")],
            "extracted_facts": [("row_hash", "TEXT"), ("prev_hash", "TEXT")],
            "predictions": [("kind", "TEXT NOT NULL DEFAULT 'retrospective_consequence'"),
                            ("horizon_hours", "INTEGER"), ("region", "TEXT"),
                            ("row_hash", "TEXT"), ("prev_hash", "TEXT")],
        }
        for table, cols in additions.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for col, decl in cols:
                if col not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        conn.commit()
    finally:
        conn.close()


def _upgrade_v3_to_v4() -> None:
    """Additive v4 upgrade (v4 manual §5/§8/§3/§9.1/§22): new columns on
    existing tables. New tables come from the DDL executescript."""
    import sqlite3
    from ..config import sqlite_path
    conn = sqlite3.connect(str(sqlite_path()), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        additions = {
            "countries": [("status", "TEXT NOT NULL DEFAULT 'un_member'"),
                          ("iso2", "TEXT"), ("population", "INTEGER"),
                          ("last_updated_at", "TEXT")],
            "events": [("geocode_confidence", "REAL"),
                       ("global_relevance_score", "REAL")],
            "stories": [("story_type", "TEXT NOT NULL DEFAULT 'acute_event'"),
                        ("deep_summary", "TEXT")],
            "sources": [("attribution", "TEXT")],
            "non_state_actors": [("base_lat", "REAL"), ("base_lon", "REAL")],
            "country_leadership": [("image_url", "TEXT")],
            "alliances": [("last_updated_at", "TEXT")],
        }
        for table, cols in additions.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for col, decl in cols:
                if col not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        conn.commit()
    finally:
        conn.close()


def _upgrade_v4_to_v5() -> None:
    """Additive v5 upgrade (v5 manual §3/§5/§7/§11): new columns on existing
    tables. non_state_actor_zones is a new table from the DDL executescript."""
    import sqlite3
    from ..config import sqlite_path
    conn = sqlite3.connect(str(sqlite_path()), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        additions = {
            "events": [("development_type", "TEXT")],            # §3
            "sources": [("reliability_tier", "TEXT NOT NULL DEFAULT 'medium'")],  # §5
            "countries": [("flag_image_url", "TEXT")],           # §7
        }
        for table, cols in additions.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for col, decl in cols:
                if col not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        conn.commit()
    finally:
        conn.close()


def _upgrade_v5_to_v6() -> None:
    """Additive v6 upgrade (v6 manual §2/§5/§14/§15/§16): new columns on
    existing tables, plus a countries-table rebuild when its status CHECK
    predates the 'territory' value (§14). New tables come from the DDL
    executescript. The rebuild uses the same foreign_keys=OFF +
    legacy_alter_table=ON pattern as the v1→v2 sources rebuild so child FK
    clauses survive the rename."""
    import sqlite3
    from ..config import sqlite_path
    conn = sqlite3.connect(str(sqlite_path()), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("PRAGMA legacy_alter_table=ON")
        conn.execute("BEGIN IMMEDIATE")
        additions = {
            "sources": [("is_active", "INTEGER NOT NULL DEFAULT 1")],          # §2
            "countries": [("official_name", "TEXT"), ("languages", "TEXT"),    # §15
                          ("gdp_usd", "REAL"), ("hdi", "REAL"),
                          ("gdp_per_capita_usd", "REAL"), ("area_km2", "REAL"),
                          ("sovereign_id", "TEXT"),                            # §14
                          ("dominant_religion", "TEXT"),                       # §16
                          ("dominant_language", "TEXT"),
                          ("currency_code", "TEXT"), ("currency_name", "TEXT"),  # v6.1
                          ("currency_symbol", "TEXT")],
            "political_parties": [("electoral_history", "TEXT"),               # §5
                                  ("coalition_partners", "TEXT"),
                                  ("logo_image_url", "TEXT"),
                                  ("founding_history", "TEXT")],
            "notable_persons": [("electoral_history", "TEXT"),                 # §5
                                ("portrait_image_url", "TEXT")],
            "conflict_parties": [("side", "TEXT")],                            # §8
            # v6.1 — per-party seat composition for the parliamentary graphic
            "country_legislature": [("seats_json", "TEXT")],
        }
        for table, cols in additions.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for col, decl in cols:
                if col not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        # §14 — a fresh-v4/v5 DB has a status CHECK without 'territory';
        # rebuild countries from the current DDL and copy the column
        # intersection (all v6 columns now exist on the old table via the
        # ALTERs above, so the intersection is the full v6 column list)
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'"
                           " AND name='countries'").fetchone()
        if row and "CHECK" in (row["sql"] or "") and "'territory'" not in row["sql"]:
            create_countries_sql = DDL[
                DDL.index("CREATE TABLE IF NOT EXISTS countries"):
                DDL.index("CREATE TABLE IF NOT EXISTS country_leadership")
            ].strip().rstrip(";") + ";"
            conn.execute("ALTER TABLE countries RENAME TO countries_v5")
            conn.execute(create_countries_sql)
            new_cols = [r["name"] for r in conn.execute("PRAGMA table_info(countries)")]
            old_cols = {r["name"] for r in conn.execute("PRAGMA table_info(countries_v5)")}
            copy = ", ".join(c for c in new_cols if c in old_cols)
            conn.execute(f"INSERT INTO countries ({copy}) SELECT {copy} FROM countries_v5")
            conn.execute("DROP TABLE countries_v5")
        # v7.2 §4 — an existing DB's sources CHECK predates 'ais'/'nightlights'
        # (the type list only grows), so seeding the new physical-sensor rows
        # would fail the constraint. Rebuild from the current DDL when the
        # newest sentinel is absent; the column-intersection copy preserves
        # every existing column. Runs here (not in _upgrade_v1_to_v2) because
        # that path only fires for a v1 DB — a v6+ DB reaches only this fn.
        # v7.4.1 — sentinel bumped to 'archive' (the new curated-history type
        # that replaces the old 'gdelt' mislabeling) so a DB already migrated
        # through the v7.2 'ais' rebuild still gets rebuilt one more time here.
        srow = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'"
                            " AND name='sources'").fetchone()
        if srow and "'archive'" not in (srow["sql"] or ""):
            create_sources_sql = DDL[
                DDL.index("CREATE TABLE IF NOT EXISTS sources"):
                DDL.index("-- 6.2")
            ].strip().rstrip(";") + ";"
            conn.execute("ALTER TABLE sources RENAME TO sources_v6")
            conn.execute(create_sources_sql)
            new_cols = [r["name"] for r in conn.execute("PRAGMA table_info(sources)")]
            old_cols = {r["name"] for r in conn.execute("PRAGMA table_info(sources_v6)")}
            copy = ", ".join(c for c in new_cols if c in old_cols)
            conn.execute(f"INSERT INTO sources ({copy}) SELECT {copy} FROM sources_v6")
            conn.execute("DROP TABLE sources_v6")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def _upgrade_v6_to_v8() -> None:
    """Additive v8 upgrade (V8 §4 — the Administrative Atlas). The
    administrative_units table itself is created by the idempotent DDL
    executescript in migrate(); the only in-place change an existing DB needs is
    the nullable events.admin_uid column (the ADM1 unit an event lands in,
    populated at ingestion). PRAGMA-checked so re-running is a no-op. (No v7
    schema step existed — v7.x were data/feature releases on the v6 schema, so
    v6→v8 is one hop.)"""
    import sqlite3
    from ..config import sqlite_path
    conn = sqlite3.connect(str(sqlite_path()), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        additions = {
            "events": [("admin_uid", "INTEGER")],
        }
        for table, cols in additions.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for col, decl in cols:
                if col not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def _upgrade_events_category_check() -> None:
    """v8.13 — widen events.category from the original 5 values to the v8.13
    taxonomy (adds 'technology','domestic','health'). SQLite can't ALTER a CHECK,
    so rebuild the events table from the current DDL when its CHECK predates
    'technology'. Same foreign_keys=OFF + legacy_alter_table=ON pattern as the
    countries/sources rebuilds so extracted_facts' FK to events survives the
    rename. Idempotent: a table whose CHECK already lists 'technology' is skipped.
    (This is why 'technology' events — classified since v6.6 — never actually
    stored: the insert violated the old CHECK and the pipeline rolled back.)"""
    import sqlite3
    from ..config import sqlite_path
    conn = sqlite3.connect(str(sqlite_path()), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'"
                           " AND name='events'").fetchone()
        if not row or "'technology'" in (row["sql"] or ""):
            return   # fresh DDL or already-widened — nothing to do
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("PRAGMA legacy_alter_table=ON")
        conn.execute("BEGIN IMMEDIATE")
        create_events_sql = DDL[
            DDL.index("CREATE TABLE IF NOT EXISTS events"):
            DDL.index("CREATE INDEX IF NOT EXISTS idx_events_occurred")
        ].strip().rstrip(";") + ";"
        conn.execute("ALTER TABLE events RENAME TO events_v8")
        conn.execute(create_events_sql)
        new_cols = [r["name"] for r in conn.execute("PRAGMA table_info(events)")]
        old_cols = {r["name"] for r in conn.execute("PRAGMA table_info(events_v8)")}
        copy = ", ".join(c for c in new_cols if c in old_cols)
        conn.execute(f"INSERT INTO events ({copy}) SELECT {copy} FROM events_v8")
        conn.execute("DROP TABLE events_v8")
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        conn.close()


def _backfill_fts(conn) -> None:
    if conn.execute("SELECT COUNT(*) AS n FROM fts_stories").fetchone()["n"] == 0:
        conn.execute("INSERT INTO fts_stories (id, headline, summary)"
                     " SELECT id, headline, summary FROM stories")
    if conn.execute("SELECT COUNT(*) AS n FROM fts_facts").fetchone()["n"] == 0:
        conn.execute('INSERT INTO fts_facts (id, who, what, place)'
                     ' SELECT id, who, what, COALESCE("where", \'\') FROM extracted_facts')


def migrate() -> None:
    """Idempotent schema bootstrap + versioned in-place upgrades."""
    prior_version = 0
    with write_tx() as conn:
        has_migrations_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if has_migrations_table:
            prior = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()
            prior_version = prior["v"] or 0
    if prior_version == 1:
        _upgrade_v1_to_v2()
    if 1 <= prior_version <= 2:
        _upgrade_v2_to_v3()
    if 1 <= prior_version <= 3:
        _upgrade_v3_to_v4()
    if 1 <= prior_version <= 4:
        _upgrade_v4_to_v5()
    # <= 6 (not <= 5): the v6 upgrade is idempotent and cheap, and re-running
    # it on an already-v6 DB heals any column added late in the v6 cycle
    if 1 <= prior_version <= 6:
        _upgrade_v5_to_v6()
    # <= 7: the v8 upgrade is idempotent (PRAGMA-checked ALTER) — re-running on
    # an already-v8 DB is a no-op; v7 shipped no schema change so v6→v8 is one hop
    if 1 <= prior_version <= 7:
        _upgrade_v6_to_v8()
    # v8.13 — widen events.category (adds technology/domestic/health). Runs on any
    # existing DB regardless of version; idempotent (skips an already-widened
    # table). MUST run before the DDL executescript so the rename→recreate isn't
    # confused by a fresh `CREATE TABLE IF NOT EXISTS events` re-adding indexes.
    if prior_version >= 1:
        _upgrade_events_category_check()
    with write_tx() as conn:
        conn.executescript(DDL)
        if prior_version < SCHEMA_VERSION:
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, now_iso()))
    # v8 — a genuinely FRESH DB (prior_version == 0) skipped every version-gated
    # upgrade above, but several columns the seeds/routes rely on (the v6.1
    # currency_* columns, events.admin_uid, …) are ALTER-only — they live in the
    # upgrade functions, not the base DDL. Re-run the additive v6/v8 upgrades now
    # that the DDL has created the base tables; both are idempotent
    # (PRAGMA-checked ALTERs) and their table-rebuild branches are guarded (a
    # fresh DDL already carries the newest CHECK values), so this is a no-op on
    # any already-migrated DB and makes a clean `python run.py` clone work.
    if prior_version == 0:
        _upgrade_v5_to_v6()
        _upgrade_v6_to_v8()
    if fts_available():
        with write_tx() as conn:
            conn.executescript(FTS_DDL)
            _backfill_fts(conn)
            conn.execute("INSERT INTO app_meta (key, value) VALUES ('fts_enabled','1')"
                         " ON CONFLICT(key) DO UPDATE SET value='1'")
    else:
        with write_tx() as conn:
            conn.execute("INSERT INTO app_meta (key, value) VALUES ('fts_enabled','0')"
                         " ON CONFLICT(key) DO UPDATE SET value='0'")


def new_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --- embedding pack/unpack (vector(384) adaptation) ---

EMBEDDING_DIM = 384


def pack_embedding(vec) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack_embedding(blob: bytes):
    return struct.unpack(f"<{len(blob) // 4}f", blob)


def row_to_dict(row, json_fields=(), drop=("embedding",)) -> dict:
    d = {k: row[k] for k in row.keys() if k not in drop}
    for f in json_fields:
        if d.get(f):
            try:
                d[f] = json.loads(d[f])
            except (json.JSONDecodeError, TypeError):
                pass
    if "location_lat" in d:
        lat, lon = d.pop("location_lat"), d.pop("location_lon")
        d["location"] = {"lat": lat, "lon": lon} if lat is not None and lon is not None else None
    if "is_synthetic" in d:
        d["_synthetic"] = bool(d.pop("is_synthetic"))
    return d


def meta_get(key: str, default: str | None = None):
    row = get_conn().execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def meta_set(key: str, value: str) -> None:
    with write_tx() as conn:
        conn.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)"
                     " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))


def get_conn_for_scripts():
    """Convenience for scripts/ so they share the same path resolution."""
    return get_conn()
