"""Stage 3 — embedding generation (Section 2.1, 5.4 step 2).

Preferred path: sentence-transformers all-MiniLM-L6-v2 (384-dim), the
manual's locked choice, used automatically when the package is importable.

Zero-install fallback: a deterministic 384-dim feature-hashing embedder
(word + bigram + character-trigram hashing, L2-normalized). This is the
same class of fallback the manual already sanctions for pgvector
("computing cosine similarity in Python at query time", Section 3.2),
extended to the embedding itself so `python run.py` works with no
downloads. Cosine similarity over hashed features tracks token overlap of
the *normalized* event descriptions — and Section 5.4 step 1's
normalization (entities + location + action) is what carries the semantic
weight in this scheme.

Embeddings are comparable only within one embedder. A marker row in the
DB records which embedder produced the stored vectors; switching embedders
triggers a transparent re-embed of the chain at startup (cheap for the
hashing embedder; one-time cost for MiniLM).
"""

import hashlib
import logging
import math
import re

from ..config import EMBEDDING_MODEL_NAME
from ..db.models import EMBEDDING_DIM

log = logging.getLogger("embed")

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have in is it its of on or "
    "that the to was were will with says say said after over amid new".split()
)

_st_model = None
_st_tried = False


def _sentence_transformer():
    global _st_model, _st_tried
    if not _st_tried:
        _st_tried = True
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            _st_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            log.info("embedder", extra={"data": {"backend": "sentence-transformers",
                                                 "model": EMBEDDING_MODEL_NAME}})
        except Exception:
            _st_model = None
            log.info("embedder", extra={"data": {"backend": "hashing-384 (stdlib fallback)"}})
    return _st_model


def embedder_id() -> str:
    return f"st:{EMBEDDING_MODEL_NAME}" if _sentence_transformer() else "hash384:v1"


def _tokens(text: str) -> list[str]:
    words = [w for w in _TOKEN_RE.findall(text.lower()) if w not in _STOPWORDS]
    feats = list(words)
    feats += [f"{a}_{b}" for a, b in zip(words, words[1:])]
    for w in words:
        if len(w) > 4:
            feats += [w[i:i + 3] for i in range(len(w) - 2)]
    return feats


def _hash_embed(text: str) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    for feat in _tokens(text):
        h = int.from_bytes(hashlib.md5(feat.encode()).digest()[:8], "little")
        idx = h % EMBEDDING_DIM
        sign = 1.0 if (h >> 62) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def embed_text(text: str) -> list[float]:
    model = _sentence_transformer()
    if model is not None:
        return [float(x) for x in model.encode(text, normalize_embeddings=True)]
    return _hash_embed(text)


def cosine(a, b) -> float:
    # vectors are stored L2-normalized, so cosine == dot product
    return sum(x * y for x, y in zip(a, b))


def ensure_embedder_consistency() -> None:
    """Embeddings are only comparable within one embedder. app_meta records
    which embedder produced the stored vectors; on mismatch (e.g. the owner
    installed sentence-transformers after running with the hashing fallback)
    every event/fact is re-embedded once at startup."""
    from ..db.models import pack_embedding
    from ..db.session import query, query_one, write_tx

    current = embedder_id()
    row = query_one("SELECT value FROM app_meta WHERE key = 'embedder_id'")
    stored = row["value"] if row else None
    if stored == current:
        return
    if stored is not None:
        log.info("re_embedding_chain", extra={"data": {"from": stored, "to": current}})
        events = query("SELECT id, description FROM events")
        for e in events:
            with write_tx() as conn:
                conn.execute("UPDATE events SET embedding = ? WHERE id = ?",
                             (pack_embedding(embed_text(e["description"])), e["id"]))
        facts = query(
            'SELECT f.id, f.who, f.what, f."where" AS where_text, e.description'
            " FROM extracted_facts f LEFT JOIN events e ON e.id = f.event_id")
        for f in facts:
            text = f["description"] or " | ".join(
                p for p in (f["who"], f["where_text"] or "", f["what"]) if p)
            with write_tx() as conn:
                conn.execute("UPDATE extracted_facts SET embedding = ? WHERE id = ?",
                             (pack_embedding(embed_text(text)), f["id"]))
        log.info("re_embedded", extra={"data": {"events": len(events), "facts": len(facts)}})
    with write_tx() as conn:
        conn.execute("INSERT INTO app_meta (key, value) VALUES ('embedder_id', ?)"
                     " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (current,))
