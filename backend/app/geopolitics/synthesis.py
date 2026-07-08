"""v3 §13.2/§15/§16/§18/§19 — AI-synthesized entity summaries.

Country agendas, bilateral relations, conflict summaries and org postures
all reuse the daily-briefing pattern (v2 §6.1): aggregate that entity's
recently tagged facts/stories via the canonical-entity link and generate
a fresh synthesis with one LLM call routed through the v5 §18 provider
fallback — a view over existing data, never a new ingestion source. Every
synthesis stores the source story IDs it drew from (attribution, not just
assertion). Graceful no-op without a configured AI provider.
"""

import json
import logging

from ..processing import llm
from ..db.models import new_id, now_iso
from ..db.session import query, write_tx
from ..processing.entities import resolve_entity

log = logging.getLogger("geo_synthesis")

AGENDA_PROMPT = """You are synthesizing a country profile from tracked news stories. Given
recent story headlines/summaries mentioning this country, return ONLY
valid JSON:
{
  "geopolitical_agenda": string,   // what this country appears to be pursuing right now
  "economic_agenda": string,
  "stance_summary": string         // its apparent public positions on active situations
}
Rules: synthesize only from the provided stories; state uncertainty
honestly; 2-3 sentences per field; never invent facts not present."""

RELATION_PROMPT = """You are assessing the current state of one bilateral relationship from
tracked news stories mentioning both countries. Return ONLY valid JSON:
{
  "status": "allied" | "cooperative" | "neutral" | "tense" | "hostile" | "conflict",
  "synthesis": string   // 2-3 sentences, grounded only in the provided stories
}"""


def _call(system: str, payload: dict, max_tokens: int = 700):
    text = llm.complete(system,
                        [{"role": "user", "content": json.dumps(payload)}],
                        max_tokens=max_tokens, timeout=60)
    if text is None:
        raise ValueError("no AI provider available")
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text)


def stories_mentioning(name: str, days: int = 7, limit: int = 12) -> list[dict]:
    """Recent stories whose member facts mention the entity (canonical id
    or plain-name match on who/where)."""
    cent = resolve_entity(name)
    rows = query(
        "SELECT DISTINCT s.id, s.headline, s.summary FROM stories s"
        " JOIN story_members m ON m.story_id = s.id"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE s.is_synthetic = 0 AND s.last_updated_at >= datetime('now', ?)"
        " AND (f.canonical_entity_ids LIKE ? OR f.who LIKE ? OR f.\"where\" LIKE ?)"
        " ORDER BY s.last_updated_at DESC LIMIT ?",
        (f"-{days} day", f"%{cent}%" if cent else "%__none__%",
         f"%{name}%", f"%{name}%", limit))
    return [dict(r) for r in rows]


def curated_agenda(iso3, profile=None):
    """v7.4.1 — a curated strategic-agenda FLOOR for EVERY country (owner:
    "the agendas should be filled and updated for each country"). Composed
    offline from the country's alignment camp, rivalries/friendships, region
    and brief — so a profile always shows a real agenda even with no AI provider
    and no recent coverage. The AI synthesis (when available) overrides it."""
    iso3 = (iso3 or "").upper()
    try:
        from .country_extra import (COUNTRY_CAMP, RIVALRIES, FRIENDSHIPS,
                                    derive_alignments)
        from .world_knowledge import country_knowledge
    except Exception:  # noqa: BLE001
        return None
    name = (profile or {}).get("name") or iso3
    camp = COUNTRY_CAMP.get(iso3)
    camp_line = {
        "west": "aligns with the US-led Western bloc (NATO/EU orbit), prioritizing "
                "security ties, sanctions coordination and market integration with the West",
        "east": "sits in the Russia-aligned camp, deepening ties with Moscow and "
                "fellow revisionist states while resisting Western pressure",
        "china": "leans toward Beijing — Belt-and-Road investment, technology and "
                 "diplomatic cover — while hedging its other relationships",
        "nonaligned": "hedges between the major powers, courting investment and arms "
                      "from all sides while avoiding a hard bloc commitment",
    }.get(camp, "pursues a pragmatic, interest-driven foreign policy without a fixed bloc")
    al = derive_alignments(iso3) or {}
    rivals = (al.get("rival") or [])[:4]
    friends = (al.get("strong") or [])[:4]
    geo = f"{name} {camp_line}."
    if friends:
        geo += f" Its closest partners include {', '.join(friends)}."
    if rivals:
        geo += f" Its principal frictions are with {', '.join(rivals)}."
    kn = country_knowledge(iso3, profile) or {}
    if kn.get("region_brief"):
        geo += f" Regionally, it operates in this context: {kn['region_brief'][:280].rstrip()}…"
    gdp = (profile or {}).get("gdp_usd")
    econ = (f"{name}'s economic agenda centers on growth, investment and trade access")
    if gdp:
        econ += f" (GDP ≈ ${gdp/1e9:,.0f}B)"
    econ += ", diversifying partners and shoring up the sectors that anchor its budget and employment."
    stance = (f"{name} {camp_line.split(',')[0]}, managing its rivalries and "
              "leaning on its partners to advance national interests.")
    return {"geopolitical_agenda": geo, "economic_agenda": econ,
            "stance_summary": stance, "curated": True}


def synthesize_country_agendas(limit_countries: int = 5) -> int:
    """Periodic agenda synthesis for the countries with the most recent
    coverage (config: agenda_synthesis_interval_hours)."""
    if not llm.available():
        return 0
    countries = query("SELECT id, name FROM countries")
    scored = []
    for c in countries:
        stories = stories_mentioning(c["name"], days=7)
        if len(stories) >= 2:
            scored.append((len(stories), c, stories))
    scored.sort(key=lambda x: -x[0])
    done = 0
    for _, c, stories in scored[:limit_countries]:
        try:
            out = _call(AGENDA_PROMPT, {"country": c["name"], "stories": stories})
            if not isinstance(out, dict):
                continue
            with write_tx() as conn:
                conn.execute(
                    "INSERT INTO country_agenda_synthesis (country_id, geopolitical_agenda,"
                    " economic_agenda, stance_summary, source_story_ids, generated_at)"
                    " VALUES (?,?,?,?,?,?)"
                    " ON CONFLICT(country_id) DO UPDATE SET"
                    "   geopolitical_agenda = excluded.geopolitical_agenda,"
                    "   economic_agenda = excluded.economic_agenda,"
                    "   stance_summary = excluded.stance_summary,"
                    "   source_story_ids = excluded.source_story_ids,"
                    "   generated_at = excluded.generated_at",
                    (c["id"], out.get("geopolitical_agenda"), out.get("economic_agenda"),
                     out.get("stance_summary"),
                     json.dumps([s["id"] for s in stories]), now_iso()))
            done += 1
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("agenda_synthesis_failed", extra={"data": {
                "country": c["id"], "error": str(exc)}})
    return done


def synthesize_bilateral_relations(max_pairs: int = 5) -> int:
    """§19 — scan recent stories for country pairs co-tagged on the same
    story; synthesize/update the pair's relationship."""
    if not llm.available():
        return 0
    countries = {c["name"]: c["id"] for c in query("SELECT id, name FROM countries")}
    pair_stories: dict[tuple, list] = {}
    rows = query(
        "SELECT s.id, s.headline, s.summary, GROUP_CONCAT(f.who, ' | ') AS whos,"
        " GROUP_CONCAT(COALESCE(f.\"where\", ''), ' | ') AS wheres"
        " FROM stories s JOIN story_members m ON m.story_id = s.id"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE s.is_synthetic = 0 AND s.last_updated_at >= datetime('now', '-7 day')"
        " GROUP BY s.id LIMIT 100")
    for r in rows:
        text = f"{r['headline']} {r['whos'] or ''} {r['wheres'] or ''}"
        mentioned = [iso for name, iso in countries.items() if name in text]
        for i, a in enumerate(mentioned):
            for b in mentioned[i + 1:]:
                pair = tuple(sorted((a, b)))
                pair_stories.setdefault(pair, []).append(
                    {"id": r["id"], "headline": r["headline"], "summary": r["summary"]})
    ranked = sorted(pair_stories.items(), key=lambda kv: -len(kv[1]))
    done = 0
    for (a, b), stories in ranked[:max_pairs]:
        if len(stories) < 2:
            continue
        try:
            out = _call(RELATION_PROMPT, {"country_a": a, "country_b": b,
                                          "stories": stories[:10]})
            status = out.get("status")
            if status not in ("allied", "cooperative", "neutral", "tense",
                              "hostile", "conflict"):
                continue
            with write_tx() as conn:
                conn.execute(
                    "INSERT INTO bilateral_relations (id, country_a_id, country_b_id,"
                    " status, synthesis, source_story_ids, last_updated_at)"
                    " VALUES (?,?,?,?,?,?,?)"
                    " ON CONFLICT(country_a_id, country_b_id) DO UPDATE SET"
                    "   status = excluded.status, synthesis = excluded.synthesis,"
                    "   source_story_ids = excluded.source_story_ids,"
                    "   last_updated_at = excluded.last_updated_at",
                    (new_id(), a, b, status, out.get("synthesis"),
                     json.dumps([s["id"] for s in stories[:10]]), now_iso()))
            done += 1
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("relation_synthesis_failed", extra={"data": {
                "pair": f"{a}-{b}", "error": str(exc)}})
    return done
