"""v7 §3 — the Multi-Agent Situation Room.

A persistent cast of four AI analysts with FIXED doctrines reads the same
tracked source chain for a conflict and argues in a threaded war-room panel:

  • VECTOR   — the Realist:            power, deterrence, spheres of influence
  • LEDGER   — the Economist:          markets, sanctions, supply chains, costs
  • CANDLE   — the Humanitarian:       civilians, displacement, law, aid access
  • BULWARK  — the Military Strategist: force posture, logistics, terrain, ORBAT

Round 1: each persona reads the conflict's recent stories + the curated
world-knowledge brief and produces its take (citing story ids). Round 2: each
persona writes ONE short rebuttal to the take it most disagrees with — the
v3 'AI argues with itself' machinery promoted to the product's centerpiece.

Threads cache per (conflict, latest-story fingerprint) so they regenerate only
when the situation actually moves; generation is interactive-priority when a
user opens the panel and never runs without a provider (an honest empty state
explains instead).
"""

import hashlib
import json

from ..db.models import meta_get, meta_set, now_iso
from ..db.session import query
from . import llm

PERSONAS = [
    {"id": "vector", "name": "VECTOR", "school": "Realist",
     "color": "#57a8e8", "emoji": "♟",
     "doctrine": ("You are VECTOR, a structural realist. You read every event "
                  "through power: relative capability, deterrence credibility, "
                  "spheres of influence, alliance burden-sharing. Human costs "
                  "matter to you only as they affect state behavior. You are "
                  "skeptical of norms and institutions as restraints.")},
    {"id": "ledger", "name": "LEDGER", "school": "Economist",
     "color": "#e8b445", "emoji": "⚖",
     "doctrine": ("You are LEDGER, a political economist. You read every event "
                  "through markets and material flows: energy, shipping lanes, "
                  "sanctions leakage, reconstruction costs, fiscal endurance, "
                  "who is paying for the war and how long they can. You think "
                  "wars end when the money does.")},
    {"id": "candle", "name": "CANDLE", "school": "Humanitarian",
     "color": "#58c98b", "emoji": "🕯",
     "doctrine": ("You are CANDLE, a humanitarian-law analyst. You read every "
                  "event through civilian impact: displacement, famine risk, "
                  "protection of medical/aid corridors, IHL violations and "
                  "accountability. You refuse to let 'strategic' framing erase "
                  "the people under the map pins.")},
    {"id": "bulwark", "name": "BULWARK", "school": "Military Strategist",
     "color": "#e0564f", "emoji": "🛡",
     "doctrine": ("You are BULWARK, an operational military analyst. You read "
                  "every event through the battlefield: force generation, "
                  "logistics, terrain, drone/EW balance, air defense depletion, "
                  "operational tempo. Politics is downstream of what armies can "
                  "actually do.")},
]

_TAKE_PROMPT = """{doctrine}

You sit in GlobeGrid's Situation Room watching the "{conflict}" conflict.
Below are the same tracked stories every analyst sees (with ids) and a
background dossier. Write YOUR reading of where this conflict stands and what
matters most RIGHT NOW through your doctrine — 90-150 words, sharp, concrete,
first person. Cite the stories you lean on.
Return ONLY JSON: {{"take": "...", "cited_story_ids": ["..."]}}"""

_REBUTTAL_PROMPT = """{doctrine}

In GlobeGrid's Situation Room on "{conflict}", your colleagues just said:
{others}

Write ONE pointed rebuttal (40-80 words, first person) to the single take you
most disagree with, naming the analyst. Disagree on substance, not tone.
Return ONLY JSON: {{"rebuts": "<analyst name>", "text": "..."}}"""


def _fingerprint(cid):
    row = query("SELECT id FROM stories WHERE conflict_id = ?"
                " ORDER BY last_updated_at DESC LIMIT 1", (cid,))
    latest = row[0]["id"] if row else "none"
    return hashlib.sha1(f"{cid}:{latest}".encode()).hexdigest()[:16]


def _conflict_stories(cid, limit=8):
    return [dict(r) for r in query(
        "SELECT id, headline, summary FROM stories WHERE conflict_id = ?"
        " ORDER BY last_updated_at DESC LIMIT ?", (cid, limit))]


def _parse(raw):
    try:
        t = raw.strip()
        b, e = t.find("{"), t.rfind("}")
        return json.loads(t[b:e + 1])
    except (json.JSONDecodeError, ValueError, AttributeError):
        return None


def get_thread(cid, force=False):
    """The threaded Situation Room for a conflict — cached until the situation
    moves (new latest story) or force=True."""
    crow = query("SELECT id, name FROM conflicts WHERE id = ?", (cid,))
    if not crow:
        return {"error": "conflict not registered"}
    cname = crow[0]["name"]
    fp = _fingerprint(cid)
    key = f"sitroom:{cid}"
    if not force:
        cached = meta_get(key)
        if cached:
            try:
                data = json.loads(cached)
                if data.get("fingerprint") == fp:
                    return data
            except json.JSONDecodeError:
                pass
    personas_meta = [{k: p[k] for k in ("id", "name", "school", "color", "emoji")}
                     for p in PERSONAS]
    if not llm.available():
        return {"conflict_id": cid, "conflict": cname, "personas": personas_meta,
                "takes": [], "rebuttals": [], "fingerprint": fp,
                "ai_available": False,
                "note": "The Situation Room needs an AI provider — the four "
                        "analysts each generate a doctrine-true reading of the "
                        "live source chain. Configure Ollama or a key in "
                        "Settings."}
    from ..geopolitics.world_knowledge import CONFLICT_BRIEFS
    stories = _conflict_stories(cid)
    dossier = CONFLICT_BRIEFS.get(cname, "")
    ground = json.dumps({
        "stories": [{"id": s["id"], "headline": s["headline"],
                     "summary": (s.get("summary") or "")[:220]} for s in stories],
        "background_dossier": dossier[:1200],
    }, ensure_ascii=False)

    takes = []
    for p in PERSONAS:
        raw = None
        try:
            raw = llm.complete(
                _TAKE_PROMPT.format(doctrine=p["doctrine"], conflict=cname),
                [{"role": "user", "content": ground}],
                max_tokens=420, timeout=45, json_mode=True, interactive=True)
        except Exception:  # noqa: BLE001
            raw = None
        d = _parse(raw) if raw else None
        if d and d.get("take"):
            takes.append({"persona": p["id"], "take": str(d["take"]),
                          "cited_story_ids": [str(x) for x in
                                              (d.get("cited_story_ids") or [])][:5]})
    rebuttals = []
    if len(takes) >= 2:
        by_id = {p["id"]: p for p in PERSONAS}
        for t in takes:
            p = by_id[t["persona"]]
            others = "\n".join(
                f'- {by_id[o["persona"]]["name"]} ({by_id[o["persona"]]["school"]}): {o["take"]}'
                for o in takes if o["persona"] != t["persona"])
            raw = None
            try:
                raw = llm.complete(
                    _REBUTTAL_PROMPT.format(doctrine=p["doctrine"],
                                            conflict=cname, others=others),
                    [{"role": "user", "content": "Your rebuttal:"}],
                    max_tokens=200, timeout=35, json_mode=True, interactive=True)
            except Exception:  # noqa: BLE001
                raw = None
            d = _parse(raw) if raw else None
            if d and d.get("text"):
                rebuttals.append({"persona": t["persona"],
                                  "rebuts": str(d.get("rebuts") or ""),
                                  "text": str(d["text"])})
    data = {"conflict_id": cid, "conflict": cname, "personas": personas_meta,
            "takes": takes, "rebuttals": rebuttals, "fingerprint": fp,
            "ai_available": True, "generated_at": now_iso(),
            "stories": [{"id": s["id"], "headline": s["headline"]}
                        for s in stories]}
    if takes:   # only cache real content, never a transient failure
        meta_set(key, json.dumps(data, ensure_ascii=False))
    return data
