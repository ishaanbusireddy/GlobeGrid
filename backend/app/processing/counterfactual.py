"""v7 §2 — the Counterfactual Engine: a geopolitical what-if sandbox.

The user perturbs the world ("What if the Strait of Hormuz closes tomorrow?")
and the engine walks the causal graph FORWARD: it grounds the scenario in
GlobeGrid's own fact chain (related tracked stories + historical analogues
found by FTS over the permanent archive) and the curated world-knowledge
layer, then asks the LLM for a BRANCHING consequence tree — each branch a
concrete mechanism (who → what → why), time-offset from the perturbation,
domain-tagged, probability-scored, and listing the countries it touches so
the map can fly along the branch.

Plausibility is disciplined two ways: the prompt requires each branch to name
its causal mechanism and any historical precedent, and the engine annotates
every branch with how many REAL tracked/historical analogues its keywords hit
in GlobeGrid's own archive (`chain_support`). No provider → a transparent
structural fallback tree derived from the alignment/alliance graph, clearly
labeled as non-AI.

Scenarios cache in app_meta (`cfx:{hash}`); the last N are listed for reopen.
"""

import hashlib
import json
import re

from ..db.models import meta_get, meta_set, now_iso
from ..db.session import query
from . import llm

CFX_PROMPT = """You are GlobeGrid's counterfactual engine — a rigorous
geopolitical simulation analyst. The user proposes a PERTURBATION to the
current world state. Using the provided grounding (tracked stories, historical
analogues from the fact chain, world-knowledge dossiers) plus your general
knowledge of geopolitics, economics, markets, military affairs and history,
produce a BRANCHING consequence tree.

Rules:
- 8-14 branches over 2-3 levels. Level-1 branches are direct consequences;
  deeper branches chain from a parent via a stated mechanism.
- Every branch MUST name its causal mechanism (who does what, why it follows)
  and, where one exists, a historical precedent.
- Honest probabilities (0.05-0.95). Competing branches may sum past 1 — they
  are conditional paths, not a partition.
- Time offsets: "hours", "days", "weeks", "months" from the perturbation.
- domain: one of military, economic, diplomatic, humanitarian, energy, tech.
- affected: ISO3 codes of the countries most affected by THAT branch.
Return ONLY JSON:
{"scenario_summary": "2-3 sentence framing of the perturbation and the world
  state it lands in",
 "branches": [{"id":"b1","parent":null,"t_offset":"days","domain":"economic",
   "title":"...", "mechanism":"...", "precedent":"... or null",
   "probability":0.6, "affected":["USA","CHN"]}],
 "key_indicators": ["3-6 concrete observables that would confirm which branch
   is unfolding"]}"""


def _key(perturbation):
    return "cfx:" + hashlib.sha1(perturbation.strip().lower()
                                 .encode("utf-8")).hexdigest()[:20]


def _grounding(perturbation):
    """Tracked stories + historical analogues from OUR archive, via FTS."""
    words = [w for w in re.findall(r"[A-Za-z]{4,}", perturbation)][:6]
    stories, analogues = [], []
    if words:
        fts = " OR ".join(words)
        try:
            stories = [dict(r) for r in query(
                "SELECT s.id, s.headline, s.summary FROM fts_stories f"
                " JOIN stories s ON s.id = f.id WHERE fts_stories MATCH ?"
                " ORDER BY rank LIMIT 6", (fts,))]
        except Exception:  # noqa: BLE001 — FTS syntax edge, degrade
            stories = []
        try:
            analogues = [dict(r) for r in query(
                "SELECT f.what AS title, x.when_occurred AS occurred_at"
                " FROM fts_facts f JOIN extracted_facts x ON x.id = f.id"
                " WHERE fts_facts MATCH ? ORDER BY rank LIMIT 8", (fts,))]
        except Exception:  # noqa: BLE001
            analogues = []
    return stories, analogues, words


def _chain_support(branch, words):
    """How many REAL archive events echo this branch's keywords — the
    provenance-trail plausibility annotation nothing else on the market has."""
    terms = [w for w in re.findall(r"[A-Za-z]{4,}",
                                   f"{branch.get('title','')} "
                                   f"{branch.get('mechanism','')}")][:5]
    terms = terms or words
    if not terms:
        return 0
    try:
        row = query("SELECT COUNT(*) AS n FROM fts_facts WHERE fts_facts"
                    " MATCH ?", (" OR ".join(terms),))
        return int(row[0]["n"]) if row else 0
    except Exception:  # noqa: BLE001
        return 0


def _fallback_tree(perturbation):
    """No-provider structural tree from the alignment graph: named countries'
    rivals/allies react. Transparent about being non-AI."""
    from ..geopolitics.country_extra import derive_alignments
    iso = None
    rows = query("SELECT id, name FROM countries")
    low = perturbation.lower()
    for r in rows:
        if r["name"] and r["name"].lower() in low:
            iso = r["id"]
            break
    branches = []
    if iso:
        al = derive_alignments(iso) or {}
        rivals = list(al.get("rival") or [])[:3]
        allies = list(al.get("strong") or [])[:3]
        if rivals:
            branches.append({"id": "b1", "parent": None, "t_offset": "days",
                             "domain": "diplomatic", "probability": 0.6,
                             "title": f"Rivals of {iso} move to exploit the shock",
                             "mechanism": "Structural rivalry: adversaries probe "
                                          "weakness after a disruption.",
                             "precedent": None, "affected": rivals})
        if allies:
            branches.append({"id": "b2", "parent": None, "t_offset": "days",
                             "domain": "military", "probability": 0.55,
                             "title": f"Allies of {iso} coordinate a response",
                             "mechanism": "Alliance commitments trigger "
                                          "consultations and posture changes.",
                             "precedent": None, "affected": allies})
    branches.append({"id": "b3", "parent": None, "t_offset": "hours",
                     "domain": "economic", "probability": 0.7,
                     "title": "Markets reprice risk immediately",
                     "mechanism": "Uncertainty premium: energy, shipping and "
                                  "safe-haven assets move first.",
                     "precedent": "Every major geopolitical shock since 1973.",
                     "affected": ["USA", "CHN", "DEU", "JPN"]})
    return {"scenario_summary": f"Structural (non-AI) projection for: "
                                f"{perturbation}. Configure an AI provider for "
                                f"the full branching simulation.",
            "branches": branches, "key_indicators": [],
            "ai": False}


def run_scenario(perturbation, force=False):
    """Main entry: cached scenario for a perturbation, generating if needed."""
    perturbation = (perturbation or "").strip()[:300]
    if not perturbation:
        return {"error": "empty perturbation"}
    key = _key(perturbation)
    if not force:
        cached = meta_get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
    stories, analogues, words = _grounding(perturbation)
    scenario = None
    if llm.available():
        from ..geopolitics.world_knowledge import CONFLICT_BRIEFS
        # attach at most one relevant conflict brief as grounding
        kb = next((b for n, b in CONFLICT_BRIEFS.items()
                   if any(w.lower() in n.lower() for w in words)), None)
        user = json.dumps({
            "perturbation": perturbation,
            "tracked_stories": [{"headline": s["headline"],
                                 "summary": (s.get("summary") or "")[:200]}
                                for s in stories],
            "historical_analogues_from_chain":
                [a["title"] for a in analogues],
            "world_knowledge": kb,
        }, ensure_ascii=False)
        raw = None
        try:
            raw = llm.complete(CFX_PROMPT, [{"role": "user", "content": user}],
                               max_tokens=1800, timeout=60, json_mode=True,
                               interactive=True)
        except Exception:  # noqa: BLE001
            raw = None
        if raw:
            try:
                t = raw.strip()
                b, e = t.find("{"), t.rfind("}")
                scenario = json.loads(t[b:e + 1])
                scenario["ai"] = True
            except (json.JSONDecodeError, ValueError):
                scenario = None
    if not scenario or not isinstance(scenario.get("branches"), list):
        scenario = _fallback_tree(perturbation)
    # plausibility trail: annotate each branch with real-archive support
    for br in scenario.get("branches", []):
        br["chain_support"] = _chain_support(br, words)
    scenario.update({
        "perturbation": perturbation,
        "generated_at": now_iso(),
        "grounding": {"stories": [{"id": s["id"], "headline": s["headline"]}
                                  for s in stories],
                      "analogues": [a["title"] for a in analogues[:6]]},
    })
    meta_set(key, json.dumps(scenario, ensure_ascii=False))
    # maintain the recent-scenarios index
    try:
        recent = json.loads(meta_get("cfx:recent") or "[]")
    except json.JSONDecodeError:
        recent = []
    recent = ([{"perturbation": perturbation, "key": key,
                "generated_at": scenario["generated_at"]}]
              + [r for r in recent if r.get("key") != key])[:12]
    meta_set("cfx:recent", json.dumps(recent))
    return scenario


def recent_scenarios():
    try:
        return json.loads(meta_get("cfx:recent") or "[]")
    except json.JSONDecodeError:
        return []


def clear_recent():
    """v8.13 — owner's "clear history" button. Drops the recent-scenarios index
    (the cached scenario bodies themselves expire naturally / are keyed by
    perturbation, so only the visible history list is reset)."""
    meta_set("cfx:recent", "[]")
    return {"cleared": True}


_EXPAND_PROMPT = """You are GlobeGrid's counterfactual engine. Within an
existing what-if scenario, the user wants to drill into ONE branch and see what
follows from IT specifically. Given the original perturbation and the branch to
deepen, produce 2-4 CHILD consequences that chain directly from that branch —
each a concrete mechanism (who does what, why it follows from the parent), a
honest probability (0.05-0.95, conditional on the parent happening), a time
offset ("hours"/"days"/"weeks"/"months") LATER than the parent, a domain
(military/economic/diplomatic/humanitarian/energy/tech), and the ISO3 codes of
countries it most affects.
Return ONLY JSON: {"children":[{"t_offset":"weeks","domain":"economic",
  "title":"...","mechanism":"...","precedent":"... or null","probability":0.5,
  "affected":["USA"]}]}"""


def expand_branch(perturbation, branch, force=False):
    """v7.1 §2 — deepen ONE branch into 2-4 grounded child consequences. Cached
    per (perturbation, branch id) so re-opening is instant."""
    perturbation = (perturbation or "").strip()[:300]
    bid = str((branch or {}).get("id") or "")
    if not perturbation or not bid:
        return {"error": "need perturbation + branch"}
    key = _key(perturbation) + ":exp:" + hashlib.sha1(bid.encode()).hexdigest()[:8]
    if not force:
        cached = meta_get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
    _, _, words = _grounding(perturbation)
    children = []
    if llm.available():
        user = json.dumps({"perturbation": perturbation,
                           "branch_to_deepen": {k: branch.get(k) for k in
                                                ("title", "mechanism", "domain",
                                                 "t_offset", "affected")}},
                          ensure_ascii=False)
        raw = None
        try:
            raw = llm.complete(_EXPAND_PROMPT,
                               [{"role": "user", "content": user}],
                               max_tokens=900, timeout=45, json_mode=True,
                               interactive=True)
        except Exception:  # noqa: BLE001
            raw = None
        if raw:
            try:
                t = raw.strip()
                b, e = t.find("{"), t.rfind("}")
                data = json.loads(t[b:e + 1])
                children = data.get("children") or []
            except (json.JSONDecodeError, ValueError):
                children = []
    # id + parent link + plausibility trail on each child
    out = []
    for i, c in enumerate(children[:4]):
        if not isinstance(c, dict) or not c.get("title"):
            continue
        c["id"] = f"{bid}.{i + 1}"
        c["parent"] = bid
        c["chain_support"] = _chain_support(c, words)
        out.append(c)
    result = {"parent": bid, "children": out, "ai": bool(out),
              "generated_at": now_iso()}
    if out:
        meta_set(key, json.dumps(result, ensure_ascii=False))
    return result
