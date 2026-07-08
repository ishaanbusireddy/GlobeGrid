"""v4 routes — manual §4.3 (city labels), §5.3 (border disputes), §6.2
(wiki entities), §7 (background content), §8 (stories directory), §11.2
(deep summaries), §14 (API key onboarding), §19 (annotations), §20
(reasoning trace), §21 (bookmarks), §22 (credits)."""

import json
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

from ..config import CLAUDE_MODEL, REPO_ROOT, cfg, env
from ..db.models import meta_get, new_id, now_iso, unpack_embedding
from ..db.session import query, query_one, write_tx
from ..processing import llm
from .router import route

log = logging.getLogger("routes_v4")


# ---------- §4.3 city labels (GeoNames gazetteer already vendored) ----------

@route("GET", "/api/cities")
def cities(params, q, body):
    """Population-tiered city list for the Paradox-style label layer.
    Data: GeoNames via the v2 gazetteer import (CC BY 4.0, credited)."""
    min_pop = int(q.get("min_population", 500000))
    limit = min(int(q.get("limit", 4000)), 12000)
    rows = query(
        "SELECT name, lat, lon, country_code, population FROM gazetteer_places"
        " WHERE population >= ? ORDER BY population DESC LIMIT ?", (min_pop, limit))
    return 200, {"cities": [dict(r) for r in rows],
                 "attribution": "Geocoding data © GeoNames (geonames.org), CC BY 4.0"}


# ---------- §5.3 border disputes ----------

@route("GET", "/api/border-disputes")
def border_disputes(params, q, body):
    rows = query(
        "SELECT bd.*, ca.name AS claimant_a_name, cb.name AS claimant_b_name"
        " FROM border_disputes bd"
        " JOIN countries ca ON ca.id = bd.claimant_a_id"
        " LEFT JOIN countries cb ON cb.id = bd.claimant_b_id"
        " ORDER BY CASE bd.status WHEN 'active' THEN 0 WHEN 'frozen' THEN 1 ELSE 2 END,"
        " bd.territory_name")
    return 200, {"disputes": [dict(r) for r in rows]}


# ---------- §6.2 wiki entities: parties + unified directory ----------

@route("GET", "/api/parties")
def parties(params, q, body):
    rows = query("SELECT p.*, c.name AS country_name FROM political_parties p"
                 " LEFT JOIN countries c ON c.id = p.country_id ORDER BY p.name")
    return 200, {"parties": [dict(r) for r in rows]}


@route("GET", "/api/parties/{id}")
def party_detail(params, q, body):
    row = query_one("SELECT p.*, c.name AS country_name FROM political_parties p"
                    " LEFT JOIN countries c ON c.id = p.country_id WHERE p.id = ?",
                    (params["id"],))
    if not row:
        return 404, {"error": "party not registered"}
    d = dict(row)
    d["leaders"] = [dict(r) for r in query(
        "SELECT country_id, role, name, since_date FROM country_leadership"
        " WHERE party = ? OR party LIKE ?",
        (row["name"], row["name"].split(" (")[0] + "%"))]
    d["background"] = _background("party", row["id"])
    d["recent_stories"] = _stories_mentioning(row["name"].split(" (")[0])
    d["synthesis"], d["synth_pending"] = _party_synthesis(row)   # v6.6.5/6.6.6
    # v7.4.2 — curated professional dossier floor (AI synthesis merges over it)
    from ..geopolitics.party_dossier import dossier_for
    d["dossier"] = dossier_for(row["name"], row.get("country_id"))
    return 200, d


@route("GET", "/api/party-dossier")
def party_dossier(params, q, body):
    """v7.4.2 — a party dossier BY NAME, so every party shown in a parliament
    seat-arc (which may not have a political_parties row) is still clickable and
    opens a full professional profile. Returns the curated dossier (or a floor)
    plus any registered political_parties row and its AI synthesis."""
    name = (q.get("name") or "").strip()
    if not name:
        return 400, {"error": "name required"}
    country = q.get("country")
    from ..geopolitics.party_dossier import dossier_for
    out = {"name": name, "dossier": dossier_for(name, country)}
    # attach a registered party row + its AI synthesis if we happen to have one
    row = query_one(
        "SELECT p.*, c.name AS country_name FROM political_parties p"
        " LEFT JOIN countries c ON c.id = p.country_id"
        " WHERE lower(p.name) = lower(?) LIMIT 1", (name,))
    if row:
        out["party"] = dict(row)
        out["synthesis"], out["synth_pending"] = _party_synthesis(row)
    else:
        out["recent_stories"] = _stories_mentioning(name.split(" (")[0])
    return 200, out


PARTY_PROFILE_PROMPT = """You are a political analyst. From the CONTEXT (a political
party's name, its country, ideology tags and founding date) write a
comprehensive, neutral structured profile of this specific real party.

Return ONLY valid JSON:
{
  "summary": string,                 // 2-4 sentences: what the party is and its current standing
  "ideology": string,                // its political ideology / position, one line
  "history": [string, ...],          // 4-7 bullets: founding, key eras, notable leaders and elections
  "positions": [string, ...],        // 4-7 bullets: signature policy positions and platform
  "electoral": string                // 1-2 sentences: its recent electoral performance / role (govt or opposition)
}
Draw on your general knowledge of this well-known party — a description may not
be provided and you should still write a full, accurate profile. Be factual and
neutral; give a genuinely informative, detailed profile. If you truly don't
recognize the party, keep fields short rather than fabricating."""


def _party_synthesis(row):
    """v6.6.5/6.6.6 — cached AI-synthesized comprehensive party profile. Returns
    (synthesis_or_None, pending_bool). NON-BLOCKING: the generation runs in a
    background thread so the party pane opens instantly instead of hanging on a
    20-60s local-Ollama call (the 'can't open political parties' bug); the
    frontend re-fetches once to pick up the result."""
    import json as _json
    from ..db.models import meta_get
    from ..processing import llm
    key = f"partyprof:{row['id']}"
    cached = meta_get(key)
    if cached:
        try:
            return _json.loads(cached), False
        except _json.JSONDecodeError:
            return None, False
    if not llm.available():
        return None, False
    from ..processing.bg_synth import kick
    ctx = {"name": row["name"], "country": row.get("country_name"),
           "ideology_tags": row.get("ideology_tags"), "founded": row.get("founded_date")}
    pending = kick(key, lambda: _generate_party_synth(key, ctx))
    return None, pending


def _generate_party_synth(key, ctx):
    """v6.6.6 — background party synthesis generation + cache."""
    import json as _json
    from ..db.models import meta_set
    from ..processing import llm
    text = llm.complete(PARTY_PROFILE_PROMPT,
                        [{"role": "user", "content": _json.dumps(ctx)}],
                        max_tokens=800, timeout=90, json_mode=True)
    if not text:
        return
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").removeprefix("json").strip()
    b = t.find("{")
    if b != -1:
        t = t[b:t.rfind("}") + 1]
    try:
        synth = _json.loads(t)
    except _json.JSONDecodeError:
        return
    meta_set(key, _json.dumps(synth))


@route("GET", "/api/persons/{id}")
def person_detail(params, q, body):
    row = query_one(
        "SELECT np.*, c.name AS country_name, o.name AS org_name, n.name AS nsa_name"
        " FROM notable_persons np"
        " LEFT JOIN countries c ON c.id = np.affiliated_country_id"
        " LEFT JOIN international_organizations o ON o.id = np.affiliated_org_id"
        " LEFT JOIN non_state_actors n ON n.id = np.affiliated_non_state_actor_id"
        " WHERE np.id = ?", (params["id"],))
    if not row:
        return 404, {"error": "person not registered"}
    d = dict(row)
    d["background"] = _background("person", row["id"])
    d["recent_stories"] = _stories_mentioning(row["name"])
    return 200, d


@route("GET", "/api/wiki/directory")
def wiki_directory(params, q, body):
    """Ordered id/name lists per entity type — powers the prev/next
    arrows (§6.2) without a round trip per step."""
    return 200, {
        "country": [dict(r) for r in query(
            "SELECT id, name, status FROM countries ORDER BY name")],
        "party": [dict(r) for r in query(
            "SELECT id, name FROM political_parties ORDER BY name")],
        "person": [dict(r) for r in query(
            "SELECT id, name FROM notable_persons ORDER BY name")],
        "non_state_actor": [dict(r) for r in query(
            "SELECT id, name FROM non_state_actors ORDER BY name")],
        "org": [dict(r) for r in query(
            "SELECT id, name FROM international_organizations ORDER BY name")],
        "alliance": [dict(r) for r in query(
            "SELECT id, name FROM alliances ORDER BY name")],
        "conflict": [dict(r) for r in query(
            "SELECT id, name FROM conflicts ORDER BY name")],
    }


def _background(entity_type: str, entity_id: str):
    """§7.2 — background content stays clearly attributed by origin."""
    return [dict(r) for r in query(
        "SELECT origin, title, extract, url, fetched_at FROM entity_background"
        " WHERE entity_type = ? AND entity_id = ?", (entity_type, entity_id))]


def _stories_mentioning(name: str, limit: int = 6):
    like = f"%{name}%"
    return [dict(r) for r in query(
        "SELECT DISTINCT s.id, s.headline, s.last_updated_at FROM stories s"
        " JOIN story_members m ON m.story_id = s.id"
        " JOIN extracted_facts f ON (f.id = m.fact_id OR f.event_id = m.event_id)"
        " WHERE s.is_synthetic = 0 AND (f.who LIKE ? OR f.what LIKE ?)"
        " ORDER BY s.last_updated_at DESC LIMIT ?", (like, like, limit))]


@route("GET", "/api/background/{entity_type}/{entity_id}")
def background(params, q, body):
    etype, eid = params["entity_type"], params["entity_id"]
    rows = _background(etype, eid)
    # v6.2 — INSTANT wiki: if nothing is cached yet, fetch this entity's
    # Wikipedia summary on demand right now instead of waiting for the slow
    # weekly reference cadence. Best-effort; degrades to [] when offline.
    if not rows:
        try:
            from ..geopolitics.sync import fetch_background_now
            fetched = fetch_background_now(etype, eid)
            if fetched:
                rows = _background(etype, eid)
        except Exception:  # noqa: BLE001 — on-demand fetch is best-effort
            pass
    return 200, {"background": rows}


# ---------- §8 story taxonomy + browsing directory ----------

@route("GET", "/api/stories-directory")
def stories_directory(params, q, body):
    """The browsing surface for slower-moving story types that never rise
    in a recency feed. acute_event entries are ordinary stories; the other
    types are backed by the entity layer, per the §8.1 taxonomy.

    v6 §27 — Story Threads are the PRIMARY browsing unit: the payload leads
    with threads (each carrying its member stories, still individually
    visible), followed by the type-filtered entries. Paginated (limit/offset)
    and backed by idx_stories_type_updated instead of a table scan."""
    want = q.get("type")
    limit = min(int(q.get("limit", 40)), 120)
    offset = max(int(q.get("offset", 0)), 0)
    out = []

    # v6 §27 — threads first (the primary unit)
    threads = []
    if not want or want == "thread":
        for t in query("SELECT id, name, description, first_seen_at, last_updated_at"
                       " FROM story_threads ORDER BY last_updated_at DESC LIMIT 30"):
            members = [dict(m) for m in query(
                "SELECT s.id, s.headline, s.story_type, s.last_updated_at"
                " FROM story_thread_members tm JOIN stories s ON s.id = tm.story_id"
                " WHERE tm.thread_id = ? ORDER BY s.last_updated_at DESC LIMIT 8",
                (t["id"],))]
            threads.append({**dict(t), "story_count": query_one(
                "SELECT COUNT(*) AS n FROM story_thread_members WHERE thread_id = ?",
                (t["id"],))["n"], "members": members})

    def add(story_type, ref_type, ref_id, title, subtitle, updated_at, extra=None):
        if want and want != story_type:
            return
        out.append({"story_type": story_type, "ref_type": ref_type, "ref_id": ref_id,
                    "title": title, "subtitle": (subtitle or "")[:220],
                    "updated_at": updated_at, **(extra or {})})

    story_sql = ("SELECT id, headline, summary, last_updated_at, story_type"
                 " FROM stories WHERE is_synthetic = 0")
    story_args: list = []
    if want and want not in (None, "", "thread"):
        # uses idx_stories_type_updated (v6 §27 directory performance)
        story_sql += " AND story_type = ?"
        story_args.append(want)
    story_sql += " ORDER BY last_updated_at DESC LIMIT ? OFFSET ?"
    story_args += [limit, offset]
    for r in query(story_sql, story_args):
        add(r["story_type"] or "acute_event", "story", r["id"], r["headline"],
            r["summary"], r["last_updated_at"])

    for r in query("SELECT c.*, (SELECT COUNT(*) FROM stories s WHERE s.conflict_id = c.id"
                   "  AND s.is_synthetic = 0) AS story_count FROM conflicts c"
                   " ORDER BY story_count DESC"):
        add("ongoing_conflict", "conflict", r["id"], r["name"], r["summary"],
            r["last_updated_at"],
            {"status": r["status"], "story_count": r["story_count"],
             "region": r["region"]})

    for r in query("SELECT a.*, (SELECT COUNT(*) FROM alliance_memberships m"
                   "  WHERE m.alliance_id = a.id) AS member_count FROM alliances a"):
        add("alliance_development", "alliance", r["id"], r["name"], r["description"],
            r["last_updated_at"], {"member_count": r["member_count"]})

    # recurring patterns: lineage-rich chains + second-order links (§8.1)
    for r in query(
            "SELECT l.id, l.narrative, l.created_at, sa.headline AS a_head,"
            " sb.headline AS b_head, l.story_a_id, l.story_b_id"
            " FROM second_order_links l"
            " JOIN stories sa ON sa.id = l.story_a_id"
            " JOIN stories sb ON sb.id = l.story_b_id"
            " ORDER BY l.created_at DESC LIMIT 15"):
        narrative = r["narrative"]
        try:
            narrative = (json.loads(narrative) or {}).get("narrative", narrative)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
        add("recurring_pattern", "second_order", r["id"],
            f"{r['a_head'][:60]} ↔ {r['b_head'][:60]}",
            narrative if isinstance(narrative, str) else None, r["created_at"],
            {"story_a_id": r["story_a_id"], "story_b_id": r["story_b_id"]})

    for r in query(
            "SELECT a.country_id, c.name, a.geopolitical_agenda, a.economic_agenda,"
            " a.generated_at FROM country_agenda_synthesis a"
            " JOIN countries c ON c.id = a.country_id"):
        if r["geopolitical_agenda"]:
            add("diplomatic_push", "country", r["country_id"],
                f"{r['name']} — diplomatic agenda", r["geopolitical_agenda"],
                r["generated_at"])
        if r["economic_agenda"]:
            add("economic_push", "country", r["country_id"],
                f"{r['name']} — economic agenda", r["economic_agenda"],
                r["generated_at"])

    out.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return 200, {"threads": threads, "entries": out[:120],
                 "limit": limit, "offset": offset}


@route("GET", "/api/threads/{id}")
def thread_detail(params, q, body):
    """v6 §27 — one thread with its full member story list."""
    t = query_one("SELECT * FROM story_threads WHERE id = ?", (params["id"],))
    if not t:
        return 404, {"error": "thread not found"}
    members = [dict(m) for m in query(
        "SELECT s.id, s.headline, s.summary, s.story_type, s.confidence,"
        " s.last_updated_at FROM story_thread_members tm"
        " JOIN stories s ON s.id = tm.story_id WHERE tm.thread_id = ?"
        " ORDER BY s.last_updated_at DESC LIMIT 60", (params["id"],))]
    return 200, {**dict(t), "members": members}


# ---------- §20 correlation reasoning trace ----------

@route("GET", "/api/stories/{id}/trace")
def story_trace(params, q, body):
    """'Show your work': which link type fired for each member, the actual
    pairwise similarity (recomputed from the stored embeddings), and the
    thresholds in force for the story's category — plus the debate
    disagreement score, all in one place."""
    story = query_one("SELECT id, disagreement_score, conflict_id FROM stories"
                      " WHERE id = ?", (params["id"],))
    if not story:
        return 404, {"error": "story not found"}
    members = query(
        "SELECT m.event_id, m.fact_id, m.linked_via, m.linked_at, e.title,"
        " e.category, e.embedding, e.occurred_at FROM story_members m"
        " LEFT JOIN events e ON e.id = m.event_id"
        " WHERE m.story_id = ? ORDER BY m.linked_at", (params["id"],))
    from ..processing.embed import cosine, embedder_id
    from ..processing.correlate import effective_thresholds
    cat_row = query_one(
        "SELECT e.category, COUNT(*) AS n FROM story_members m JOIN events e"
        " ON e.id = m.event_id WHERE m.story_id = ? GROUP BY e.category"
        " ORDER BY n DESC LIMIT 1", (params["id"],))
    category = cat_row["category"] if cat_row else "other"
    same_w, hist = effective_thresholds(category)
    trace, prev_vec, prev_title = [], None, None
    for m in members:
        entry = {"event_id": m["event_id"], "fact_id": m["fact_id"],
                 "title": m["title"], "linked_via": m["linked_via"],
                 "linked_at": m["linked_at"], "occurred_at": m["occurred_at"],
                 "similarity_to_previous": None, "compared_with": prev_title}
        if m["embedding"] and prev_vec is not None:
            entry["similarity_to_previous"] = round(
                cosine(unpack_embedding(m["embedding"]), prev_vec), 4)
        if m["embedding"]:
            prev_vec = unpack_embedding(m["embedding"])
            prev_title = m["title"]
        trace.append(entry)
    return 200, {
        "story_id": params["id"],
        "category": category,
        "thresholds": {"same_window": same_w, "historical_chain": hist,
                       "entity_overlap_boost": cfg("correlation", "entity_overlap_boost")},
        "embedder": embedder_id(),
        "members": trace,
        "disagreement_score": story["disagreement_score"],
        "note": ("Similarities are recomputed from the stored embeddings; linked_via"
                 " records which correlation pass admitted each member (v1 §5.4)."),
    }


# ---------- §11.2 deep summaries ----------

@route("POST", "/api/stories/{id}/deep_summary")
def deep_summary_route(params, q, body):
    from ..processing.textquality import deep_summary
    return deep_summary(params["id"], expand=bool(isinstance(body, dict) and body.get("expand")))


# ---------- §19 annotations ----------

ANNOT_TYPES = ("story", "country", "conflict", "non_state_actor", "alliance",
               "person", "party", "org")


@route("GET", "/api/annotations")
def annotations_list(params, q, body):
    conditions, args = ["1=1"], []
    if q.get("target_type"):
        conditions.append("target_type = ?")
        args.append(q["target_type"])
    if q.get("target_id"):
        conditions.append("target_id = ?")
        args.append(q["target_id"])
    rows = query(f"SELECT * FROM annotations WHERE {' AND '.join(conditions)}"
                 " ORDER BY updated_at DESC LIMIT 500", args)
    return 200, {"annotations": [dict(r) for r in rows]}


@route("POST", "/api/annotations")
def annotations_save(params, q, body):
    if not cfg("annotations", "enabled"):
        return 503, {"error": "annotations disabled in config"}
    if not isinstance(body, dict) or body.get("target_type") not in ANNOT_TYPES \
            or not body.get("target_id") or not (body.get("note_text") or "").strip():
        return 400, {"error": "body must be {target_type, target_id, note_text, id?}"}
    now = now_iso()
    with write_tx() as conn:
        if body.get("id"):
            conn.execute("UPDATE annotations SET note_text = ?, updated_at = ?"
                         " WHERE id = ?", (body["note_text"].strip(), now, body["id"]))
            aid = body["id"]
        else:
            aid = new_id()
            conn.execute(
                "INSERT INTO annotations (id, target_type, target_id, note_text,"
                " created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (aid, body["target_type"], body["target_id"],
                 body["note_text"].strip(), now, now))
    return 200, {"ok": True, "id": aid}


@route("POST", "/api/annotations/delete")
def annotations_delete(params, q, body):
    if not isinstance(body, dict) or not body.get("id"):
        return 400, {"error": "body must be {id}"}
    with write_tx() as conn:
        conn.execute("DELETE FROM annotations WHERE id = ?", (body["id"],))
    return 200, {"ok": True}


# ---------- §21 bookmarks ----------

BOOKMARK_TYPES = ("story", "country", "conflict", "non_state_actor", "alliance",
                  "notable_person", "party", "org")

_BOOKMARK_LABEL_SQL = {
    "story": "SELECT headline AS label FROM stories WHERE id = ?",
    "country": "SELECT name AS label FROM countries WHERE id = ?",
    "conflict": "SELECT name AS label FROM conflicts WHERE id = ?",
    "non_state_actor": "SELECT name AS label FROM non_state_actors WHERE id = ?",
    "alliance": "SELECT name AS label FROM alliances WHERE id = ?",
    "notable_person": "SELECT name AS label FROM notable_persons WHERE id = ?",
    "party": "SELECT name AS label FROM political_parties WHERE id = ?",
    "org": "SELECT name AS label FROM international_organizations WHERE id = ?",
}


@route("GET", "/api/bookmarks")
def bookmarks_list(params, q, body):
    rows = query("SELECT * FROM bookmarks ORDER BY bookmarked_at DESC LIMIT 500")
    out = []
    for r in rows:
        d = dict(r)
        label_row = query_one(_BOOKMARK_LABEL_SQL[r["target_type"]], (r["target_id"],))
        d["label"] = label_row["label"] if label_row else r["target_id"]
        out.append(d)
    return 200, {"bookmarks": out}


@route("POST", "/api/bookmarks")
def bookmarks_toggle(params, q, body):
    """Toggle semantics: one endpoint serves the single bookmark icon that
    appears on every profile/wiki/story page (§21)."""
    if not isinstance(body, dict) or body.get("target_type") not in BOOKMARK_TYPES \
            or not body.get("target_id"):
        return 400, {"error": "body must be {target_type, target_id}"}
    existing = query_one("SELECT id FROM bookmarks WHERE target_type = ?"
                         " AND target_id = ?", (body["target_type"], body["target_id"]))
    with write_tx() as conn:
        if existing:
            conn.execute("DELETE FROM bookmarks WHERE id = ?", (existing["id"],))
            return 200, {"ok": True, "bookmarked": False}
        conn.execute("INSERT INTO bookmarks (id, target_type, target_id, bookmarked_at)"
                     " VALUES (?,?,?,?)",
                     (new_id(), body["target_type"], body["target_id"], now_iso()))
    return 200, {"ok": True, "bookmarked": True}


# ---------- §22 sources & credits ----------

# per-source-type attribution metadata (§22 — not hardcoded page prose)
TYPE_ATTRIBUTION = {
    "rss": ("News & official RSS feeds", "Content remains © its publishers;"
            " every story links back to the original article."),
    # v6 §2 — GDELT retired as a live source; attribution entries stay because
    # historical fact-chain rows sourced from it remain visible and credited
    "gdelt": ("GDELT Project (historical)", "Open data, gdeltproject.org — source"
              " retired in v6; pre-v6 facts retain this attribution."),
    "gdelt_events": ("GDELT Project (historical)", "Open data, gdeltproject.org —"
                     " source retired in v6; pre-v6 facts retain this attribution."),
    "usgs": ("USGS Earthquake Hazards Program", "Public domain, earthquake.usgs.gov."),
    "market": ("Alpha Vantage", "Market data via the Alpha Vantage free API."),
    "reddit": ("Reddit", "Social signal via the Reddit API; content © its authors."),
    "firms": ("NASA FIRMS", "Fire Information for Resource Management System, public data."),
    "volcano": ("Smithsonian Global Volcanism Program", "volcano.si.edu weekly reports."),
    "wikipedia": ("Wikipedia", "CC BY-SA — current events portal."),
    "wiki_views": ("Wikimedia pageviews", "Open data, wikimedia.org."),
    "mastodon": ("Mastodon", "Public federated timeline; content © its authors."),
    "bluesky": ("Bluesky", "Public firehose; content © its authors."),
    "opensky": ("OpenSky Network", "Open air-traffic data for research, opensky-network.org."),
    "acled": ("ACLED", "Armed Conflict Location & Event Data (pending access approval)."),
}

DATA_PROVIDERS = [
    ("GeoNames", "Geocoding data © GeoNames (geonames.org), CC BY 4.0",
     "https://www.geonames.org"),
    ("Natural Earth", "Country boundaries, coastlines, disputed lines and populated"
     " places — public domain", "https://www.naturalearthdata.com"),
    ("Wikidata", "Leadership, membership and sovereign-state reference data — CC0",
     "https://www.wikidata.org"),
    ("Wikipedia", "Background summaries via the MediaWiki REST API — CC BY-SA",
     "https://en.wikipedia.org"),
    ("World Bank Open Data", "GDP snapshots — CC BY 4.0", "https://data.worldbank.org"),
    ("CelesTrak", "Satellite TLEs", "https://celestrak.org"),
    ("Wikimedia Commons", "Country flag images (v5 §7) — public domain / CC-BY / CC0,"
     " cached locally with attribution", "https://commons.wikimedia.org"),
    ("Anthropic Claude", "Causal narratives, debate, briefings, analyst answers"
     " (requires your own API key)", "https://www.anthropic.com"),
]


@route("GET", "/api/credits")
def credits(params, q, body):
    by_category: dict = {}
    for r in query("SELECT name, type, url, kind, attribution FROM sources"
                   " WHERE type != 'synthetic' ORDER BY type, name"):
        meta = TYPE_ATTRIBUTION.get(r["type"], (r["type"], ""))
        group = by_category.setdefault(r["type"], {
            "provider": meta[0], "attribution": r["attribution"] or meta[1],
            "sources": []})
        group["sources"].append({"name": r["name"], "url": r["url"], "kind": r["kind"]})
    return 200, {
        "source_groups": by_category,
        "data_providers": [{"name": n, "attribution": a, "url": u}
                           for n, a, u in DATA_PROVIDERS],
        "license": "GlobeGrid itself is AGPL-3.0.",
    }


# ---------- §14 API key onboarding ----------

# v5.1 — Groq is the configured llm_provider.primary (free, no card,
# ~14,400 req/day), so its key is listed first; Claude becomes an optional
# upgrade rather than the required door to AI features. Order here mirrors
# llm_provider.fallback_order in config.yaml.
MANAGED_KEYS = {
    "GROQ_API_KEY": {
        "label": "Groq key (cloud fallback — optional)", "required": False,
        "enables": "Cloud AI whenever local Ollama isn't running — Llama 3.3 70B,"
                   " very fast, free tier capped at ~100k tokens/day",
        "signup": "https://console.groq.com/keys — free, no card.",
    },
    "OPENROUTER_API_KEY": {
        "label": "OpenRouter key (free tier, fallback)", "required": False,
        "enables": "Backup AI provider if Groq's daily quota is hit — aggregates"
                   " many free-tier models behind one API",
        "signup": "https://openrouter.ai/keys — free account, no card for free models.",
    },
    "CEREBRAS_API_KEY": {
        "label": "Cerebras key (free)", "required": False,
        "enables": "Alternate AI provider — Llama 3.1 70B, ~1M tokens/day, very fast inference",
        "signup": "https://cloud.cerebras.ai/ — free, no card.",
    },
    "GEMINI_API_KEY": {
        "label": "Google Gemini key (free)", "required": False,
        "enables": "Alternate AI provider — Gemini 2.5 Flash, 1,500 requests/day, no card",
        "signup": "https://aistudio.google.com/app/apikey — free, instant.",
    },
    "CLAUDE_API_KEY": {
        "label": "Claude API key (optional upgrade)", "required": False,
        "enables": "Same AI features on Claude instead of the free default — higher"
                   " quality prose, no daily-quota ceiling, costs per request",
        "signup": "https://console.anthropic.com/ — create an account, then API Keys →"
                  " Create Key. Paste the value starting with sk-ant-…",
    },
    "ALPHAVANTAGE_API_KEY": {
        "label": "Alpha Vantage key", "required": False,
        "enables": "Market-move events (free tier)",
        "signup": "https://www.alphavantage.co/support/#api-key — instant free key.",
    },
    "REDDIT_CLIENT_ID": {
        "label": "Reddit client ID", "required": False,
        "enables": "Social signal from Reddit",
        "signup": "https://www.reddit.com/prefs/apps — create a 'script' app;"
                  " the ID appears under the app name.",
    },
    "REDDIT_CLIENT_SECRET": {
        "label": "Reddit client secret", "required": False,
        "enables": "Social signal from Reddit (paired with the client ID)",
        "signup": "Shown alongside the client ID at reddit.com/prefs/apps.",
    },
}


def _mask(value: str) -> str:
    return value[:6] + "…" + value[-3:] if len(value) > 10 else "set"


@route("GET", "/api/settings/keys")
def keys_status(params, q, body):
    out = []
    for name, meta in MANAGED_KEYS.items():
        value = env(name)
        out.append({"name": name, **meta, "configured": bool(value),
                    "masked": _mask(value) if value else None})
    # v6.5 — Ollama (the keyless PRIMARY provider) gets a live status block so
    # Settings can show "local AI: running (llama3.1)" instead of key rows only
    tags = llm.ollama_tags()
    ollama = {"host": llm.ollama_host(), "model": llm.ollama_model(),
              "reachable": tags is not None, "installed_models": tags or [],
              "model_pulled": bool(tags) and any(
                  t == llm.ollama_model() or t.startswith(llm.ollama_model() + ":")
                  for t in tags)}
    return 200, {"keys": out,
                 "env_path": str(REPO_ROOT / ".env"),
                 "ollama": ollama,
                 # v5.1 — true once any configured provider in llm_provider's
                 # order actually has a usable key (or Ollama is available),
                 # so onboarding no longer waits on Claude specifically.
                 "ai_available": llm.available(),
                 "require_ai_key_before_first_run":
                     cfg("onboarding", "require_ai_key_before_first_run")}


def _write_env_key(name: str, value: str) -> None:
    """Update or append KEY=VALUE in the repo-root .env, preserving
    everything else — the user never has to hand-edit the file (§14)."""
    path = REPO_ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*=")
    replaced = False
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{name}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{name}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _apply_key_live(name: str, value: str) -> None:
    """Make the key effective without a restart: os.environ, the config
    module, and every already-imported module that bound it by name."""
    import sys
    os.environ[name] = value
    from .. import config as config_module
    if hasattr(config_module, name):
        setattr(config_module, name, value)
    for mod in list(sys.modules.values()):
        if mod and getattr(mod, "__name__", "").startswith("backend.app") \
                and hasattr(mod, name):
            setattr(mod, name, value)


def _provider_error_detail(exc: urllib.error.HTTPError) -> str:
    """Anthropic, Groq/OpenRouter/Cerebras (OpenAI-compatible) and Gemini all
    shape their error bodies as {"error": {"message": ...}} — surface that
    message instead of a bare status code, so a real rejection reason (bad
    model access, malformed request, etc.) is actionable rather than guessed
    at. (Was Anthropic-only; generalized in v5.1 when Groq became primary.)
    v5.1.1 — a 403 can also come from a WAF/CDN edge in front of the real API
    (blocking on User-Agent, IP reputation, etc.) that returns an HTML page,
    not JSON; show a snippet of that raw body instead of silently falling
    back to a bare, useless status code."""
    raw = b""
    try:
        raw = exc.read()
        msg = json.loads(raw).get("error", {}).get("message")
        if msg:
            return msg
    except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
        pass
    text = raw.decode("utf-8", errors="replace").strip()
    if text:
        return f"HTTP {exc.code}: {text[:200]}"
    return f"HTTP {exc.code} from provider (empty response body)"


# v5.1 — OpenAI-compatible free providers, same request/response shape as
# each other; only the URL and model differ. Mirrors llm.py's PROVIDERS.
_OPENAI_COMPATIBLE_TEST = {
    "GROQ_API_KEY": (llm.GROQ_URL, lambda: env("GROQ_MODEL", "llama-3.3-70b-versatile")),
    "OPENROUTER_API_KEY": (llm.OPENROUTER_URL,
                            lambda: env("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")),
    "CEREBRAS_API_KEY": (llm.CEREBRAS_URL, lambda: env("CEREBRAS_MODEL", "llama3.1-70b")),
}


def _test_key(name: str, value: str) -> tuple[bool, str]:
    """§14 — a visible working/not-working check, not accepted-and-hoped-for."""
    try:
        if name == "CLAUDE_API_KEY":
            # Test with the SAME model the app actually calls (CLAUDE_MODEL),
            # not a separately hardcoded one — a mismatched test model can
            # 400 (e.g. an account without access to that specific dated
            # snapshot) even though the key works fine for the app's real
            # calls, which reads as "my key doesn't work" when it does.
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({"model": CLAUDE_MODEL, "max_tokens": 1,
                                 "messages": [{"role": "user", "content": "ping"}]}).encode(),
                method="POST",
                headers={"content-type": "application/json", "x-api-key": value,
                         "anthropic-version": "2023-06-01", "user-agent": llm.USER_AGENT})
            with urllib.request.urlopen(req, timeout=20):
                return True, "key accepted by the Anthropic API"
        if name in _OPENAI_COMPATIBLE_TEST:
            url, model_fn = _OPENAI_COMPATIBLE_TEST[name]
            req = urllib.request.Request(
                url,
                data=json.dumps({"model": model_fn(), "max_tokens": 1,
                                 "messages": [{"role": "user", "content": "ping"}]}).encode(),
                method="POST",
                headers={"content-type": "application/json",
                         "authorization": f"Bearer {value}", "user-agent": llm.USER_AGENT})
            with urllib.request.urlopen(req, timeout=20):
                return True, "key accepted by the provider"
        if name == "GEMINI_API_KEY":
            req = urllib.request.Request(
                f"{llm.GEMINI_URL}?key={urllib.parse.quote(value)}",
                data=json.dumps({"contents": [{"parts": [{"text": "ping"}]}],
                                 "generationConfig": {"maxOutputTokens": 1}}).encode(),
                method="POST", headers={"content-type": "application/json",
                                        "user-agent": llm.USER_AGENT})
            with urllib.request.urlopen(req, timeout=20):
                return True, "key accepted by the Gemini API"
        if name == "ALPHAVANTAGE_API_KEY":
            req = urllib.request.Request(
                "https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
                f"&symbol=IBM&apikey={urllib.parse.quote(value)}",
                headers={"user-agent": llm.USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
            if "Global Quote" in data or "Note" in data:
                return True, "key accepted by Alpha Vantage"
            return False, str(data)[:140]
        return True, "saved — validated on the next fetch cycle"
    except urllib.error.HTTPError as exc:
        # Surface the provider's actual rejection reason instead of a bare
        # "check the key" — a 401/403 can mean an invalid key, but it can
        # also mean an unverified account, a region block, or a decommissioned
        # model, and collapsing all of those into one message just reproduces
        # the "HTTP 400 from Provider" bug already fixed once for Claude
        # (v4.2) for every other provider.
        return False, _provider_error_detail(exc)
    except OSError as exc:
        return False, f"could not reach provider: {exc}"


@route("POST", "/api/settings/keys")
def keys_save(params, q, body):
    if not isinstance(body, dict) or body.get("name") not in MANAGED_KEYS \
            or not (body.get("value") or "").strip():
        return 400, {"error": "body must be {name: <managed key>, value}"}
    name, value = body["name"], body["value"].strip()
    ok, detail = _test_key(name, value)
    if ok:
        _write_env_key(name, value)
        _apply_key_live(name, value)
        log.info("api_key_saved", extra={"data": {"key": name}})
        # v6.2 — INSTANT PING: the moment a working AI key lands, warm up every
        # AI feature in the background so the whole system lights up on the
        # user's very next click instead of waiting for scheduler ticks.
        _kick_ai_warmup(name)
    return 200, {"ok": ok, "detail": detail, "configured": ok}


# key env-var names that unlock the LLM features (Alpha Vantage etc. don't)
_AI_KEY_NAMES = {"GROQ_API_KEY", "OPENROUTER_API_KEY", "CEREBRAS_API_KEY",
                 "GEMINI_API_KEY", "CLAUDE_API_KEY"}


def _kick_ai_warmup(key_name: str) -> None:
    """v6.2 — one-shot background warm-up after an AI key is saved: generate
    causal narratives for pending stories, synthesize country agendas,
    translate recent content into any active language, and refresh leadership
    so portraits/roles populate. Each step is best-effort and isolated; the
    whole thing runs off the request thread so the save returns instantly."""
    if key_name not in _AI_KEY_NAMES:
        return

    def _run():
        import time as _time
        from ..processing import llm
        if not llm.available():
            return
        # v6.3.3 — GENTLE warmup. The old version fired ~35 sequential LLM
        # calls the instant the key was saved (25 causal narratives + agendas +
        # translation + leadership). On a free tier (Groq: tokens/requests per
        # minute) that BURST blows the rate limit, and the question the user
        # asks a few seconds later then competes for exhausted quota — which is
        # exactly the "works before the key, stalls/errors after the key"
        # report. Now it's a small, throttled trickle: one tiny step, a couple
        # of items, spaced out, so it can never monopolize the rate limit.
        steps = []
        try:
            from ..processing.causal_link import refresh_pending
            steps.append(("causal_narratives", lambda: refresh_pending(limit=2)))
        except Exception:  # noqa: BLE001
            pass
        # v6.6.8 — display translation is on-demand (site-wide DOM translator);
        # no arrival-time translation warmup step anymore.
        for label, fn in steps:
            try:
                fn()
                log.info("ai_warmup_step", extra={"data": {"step": label}})
            except Exception as exc:  # noqa: BLE001 — never let warmup crash
                log.warning("ai_warmup_failed",
                            extra={"data": {"step": label, "error": str(exc)[:120]}})
            _time.sleep(3)   # throttle: leave the rate limit for the user's own calls

    threading.Thread(target=_run, daemon=True, name="ai-warmup").start()


# ---------- §5.1 completeness status (surfaced, not silent) ----------

@route("GET", "/api/completeness")
def completeness(params, q, body):
    raw = meta_get("entity_completeness")
    return 200, json.loads(raw) if raw else {"countries": None, "problems": []}
