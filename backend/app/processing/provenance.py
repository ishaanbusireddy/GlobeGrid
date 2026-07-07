"""v3 §11 — hash-chained fact provenance.

Append-only SHA-256 chain over extracted_facts and (separately) over
predictions: each row's hash covers its own canonical content plus the
previous row's hash, so altering any historical row breaks every hash
after it. Pure stdlib hashlib — no blockchain, no external service.

Scope (stated plainly wherever this is surfaced, per the manual): this
proves the chain wasn't altered after being written by THIS system. It
does not prove the underlying source data was true.

Rows written before v3 have NULL hashes; each chain's genesis is its
first hashed row. Chain heads are cached in app_meta for O(1) appends.
The embedding blob is excluded from the fact hash — the chain guards the
claim content (who/what/where/when/source), and embeddings are legally
regenerated whenever the embedder changes (v1 ensure_embedder_consistency).
"""

import hashlib
import json
import logging
import threading

from ..config import cfg
from ..db.models import meta_get, meta_set
from ..db.session import query

log = logging.getLogger("provenance")

FACT_FIELDS = ("id", "event_id", "source_id", "who", "what", "where",
               "when_occurred", "created_at")
PREDICTION_FIELDS = ("id", "story_id", "consequence_text", "predicted_at",
                     "kind", "horizon_hours", "region")

_lock = threading.Lock()


def enabled() -> bool:
    return bool(cfg("provenance", "hash_chain_enabled"))


def _canonical(content: dict, fields) -> str:
    return json.dumps({k: content.get(k) for k in fields},
                      sort_keys=True, ensure_ascii=False, default=str)


def _row_hash(content: dict, fields, prev_hash: str) -> str:
    return hashlib.sha256((_canonical(content, fields) + "|" + prev_hash).encode()).hexdigest()


def _head_key(table: str) -> str:
    return f"prov_head:{table}"


def _load_head(table: str) -> str:
    head = meta_get(_head_key(table))
    if head is not None:
        return head
    row = query(f"SELECT row_hash FROM {table} WHERE row_hash IS NOT NULL"
                " ORDER BY rowid DESC LIMIT 1")
    return row[0]["row_hash"] if row else ""


def next_hashes(table: str, content: dict) -> tuple[str | None, str | None]:
    """Compute (row_hash, prev_hash) for an insert and advance the head.
    Call while holding the insert path — appends are serialized here."""
    if not enabled():
        return None, None
    fields = FACT_FIELDS if table == "extracted_facts" else PREDICTION_FIELDS
    with _lock:
        prev = _load_head(table)
        row_hash = _row_hash(content, fields, prev)
        meta_set(_head_key(table), row_hash)
        return row_hash, prev


def verify_chain(table: str) -> dict:
    """Walk one table's chain in insertion order, recomputing every hash."""
    fields = FACT_FIELDS if table == "extracted_facts" else PREDICTION_FIELDS
    cols = ", ".join(f'"{f}"' for f in fields)
    rows = query(f'SELECT rowid, {cols}, row_hash, prev_hash FROM {table}'
                 " WHERE row_hash IS NOT NULL ORDER BY rowid")
    prev = ""
    checked = 0
    for r in rows:
        content = {f: r[f] for f in fields}
        expected = _row_hash(content, fields, prev)
        if r["prev_hash"] != prev or r["row_hash"] != expected:
            return {"table": table, "ok": False, "checked": checked,
                    "broken_at_rowid": r["rowid"]}
        prev = r["row_hash"]
        checked += 1
    return {"table": table, "ok": True, "checked": checked, "head": prev}


def verify_all() -> dict:
    facts = verify_chain("extracted_facts")
    preds = verify_chain("predictions")
    return {
        "ok": facts["ok"] and preds["ok"],
        "chains": [facts, preds],
        "scope_note": "Verifies this system's records were not altered after being"
                      " written. It does not, by itself, prove the underlying source"
                      " data was true.",
    }
