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

Current status: **Phase 1 in progress.**

## Key constraints to remember

- Every rendered fact/event/story must trace back to a non-nullable `source_id` — schema-enforced (Section 6.8), not just a UI convention.
- All tunable thresholds/intervals/weights live in `backend/config.yaml` (Section 7.2) — never hardcoded inline.
- `extracted_facts` rows are never deleted or expired.
- License is AGPL-3.0; `.gitignore` and `LICENSE` were committed before any application code (Section 14).
