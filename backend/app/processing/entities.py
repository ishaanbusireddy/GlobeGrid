"""v2 addendum §3.1 — entity canonicalization.

'Central Bank of Arcadia' and 'Arcadia central bank' must resolve to one
canonical entity so correlation can boost on genuine entity overlap.

Resolution per entity string:
  1. exact hit in entity_aliases (case-insensitive via normalized alias),
  2. fuzzy match (token-set ratio blended with edit-distance ratio) against
     existing canonical names above entity_alias_fuzzy_match_floor,
  3. else a new canonical entity is created.
Every resolution writes the alias row so step 1 gets faster over time.
"""

import difflib
import json
import logging
import re
import threading

from ..config import cfg
from ..db.models import new_id
from ..db.session import query, query_one, write_tx

log = logging.getLogger("entities")

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset("the of and for in at a an".split())
_lock = threading.Lock()
_alias_cache: dict[str, str] = {}   # normalized alias -> canonical_id
_names_cache: list[tuple[str, frozenset, str]] | None = None  # (name_lower, tokens, id)


def _norm(s: str) -> str:
    return " ".join(_WORD_RE.findall(s.lower()))


def _tokens(s: str) -> frozenset:
    return frozenset(w for w in _WORD_RE.findall(s.lower()) if w not in _STOP)


def _similarity(a: str, b: str, ta: frozenset, tb: frozenset) -> float:
    """Token-set overlap blended with edit-distance ratio (§3.1)."""
    if not ta or not tb:
        return 0.0
    token_score = len(ta & tb) / len(ta | tb)
    edit_score = difflib.SequenceMatcher(None, a, b).ratio()
    return 0.6 * token_score + 0.4 * edit_score


def _load_caches() -> None:
    global _names_cache
    if _names_cache is None:
        _names_cache = [(r["canonical_name"].lower(), _tokens(r["canonical_name"]), r["id"])
                        for r in query("SELECT id, canonical_name FROM canonical_entities")]
        for r in query("SELECT alias, canonical_id FROM entity_aliases"):
            _alias_cache[r["alias"]] = r["canonical_id"]


def resolve_entity(name: str) -> str | None:
    """Resolve one raw entity string to a canonical_entities.id."""
    norm = _norm(name)
    if len(norm) < 3:
        return None
    with _lock:
        _load_caches()
        if norm in _alias_cache:
            return _alias_cache[norm]
        floor = float(cfg("correlation", "entity_alias_fuzzy_match_floor"))
        toks = _tokens(name)
        best_id, best_score = None, floor
        for cname, ctoks, cid in _names_cache:
            score = _similarity(norm, cname, toks, ctoks)
            if score >= best_score:
                best_id, best_score = cid, score
        if best_id is None:
            best_id = new_id()
            canonical = name.strip()
            with write_tx() as conn:
                conn.execute("INSERT OR IGNORE INTO canonical_entities (id, canonical_name)"
                             " VALUES (?, ?)", (best_id, canonical))
            existing = query_one("SELECT id FROM canonical_entities WHERE canonical_name = ?",
                                 (canonical,))
            best_id = existing["id"]
            _names_cache.append((canonical.lower(), toks, best_id))
        with write_tx() as conn:
            conn.execute("INSERT OR IGNORE INTO entity_aliases (alias, canonical_id)"
                         " VALUES (?, ?)", (norm, best_id))
        _alias_cache[norm] = best_id
        return best_id


def resolve_entities(names: list[str]) -> list[str]:
    """Resolve a list of raw entity strings to unique canonical IDs.
    Never raises — a failure on one entity skips it (pipeline isolation)."""
    out: list[str] = []
    for name in names:
        try:
            cid = resolve_entity(name)
            if cid and cid not in out:
                out.append(cid)
        except Exception:  # noqa: BLE001
            log.exception("entity_resolve_failed", extra={"data": {"entity": name}})
    return out


def canonical_ids_json(names: list[str]) -> str | None:
    ids = resolve_entities(names)
    return json.dumps(ids) if ids else None


def entity_names(ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    return {r["id"]: r["canonical_name"] for r in query(
        f"SELECT id, canonical_name FROM canonical_entities WHERE id IN ({marks})", ids)}
