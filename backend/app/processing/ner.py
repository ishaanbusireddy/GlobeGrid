"""v2 addendum §3.2 — named entity recognition.

Preferred path: spaCy (en_core_web_sm), auto-detected at import exactly
like the sentence-transformers pattern in embed.py — optional but
recommended, upgrades automatically when installed
(`pip install spacy && python -m spacy download en_core_web_sm`).

Zero-install fallback: the v1 capitalized-word regex extractor. Weaker on
lowercase entities, non-English names, and uncapitalized organizations —
which is exactly why §3.2 calls spaCy the single biggest quality lift.
"""

import logging
import re

log = logging.getLogger("ner")

_ENTITY_RE = re.compile(
    r"\b([A-Z][a-zA-Z'’.-]+(?:\s+(?:of|the|and|for|al|el|de|von|van)?\s*[A-Z][a-zA-Z'’.-]+){0,4})")
_KEEP_LABELS = {"PERSON", "ORG", "GPE", "LOC", "NORP", "FAC", "EVENT", "PRODUCT"}

_nlp = None
_tried = False


def _spacy_model():
    global _nlp, _tried
    if not _tried:
        _tried = True
        try:
            import spacy  # type: ignore
            _nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
            log.info("ner_backend", extra={"data": {"backend": "spacy:en_core_web_sm"}})
        except Exception:  # noqa: BLE001 — not installed / model missing
            _nlp = None
            log.info("ner_backend", extra={"data": {"backend": "regex (stdlib fallback)"}})
    return _nlp


def ner_backend() -> str:
    return "spacy" if _spacy_model() else "regex"


def _regex_entities(text: str, limit: int) -> list[str]:
    seen, out = set(), []
    for m in _ENTITY_RE.finditer(text or ""):
        ent = m.group(1).strip()
        if len(ent) < 3 or ent.lower() in ("the", "new", "this", "that"):
            continue
        if ent.lower() not in seen:
            seen.add(ent.lower())
            out.append(ent)
        if len(out) >= limit:
            break
    return out


def extract_entities(text: str, limit: int = 6) -> list[str]:
    nlp = _spacy_model()
    if nlp is None:
        return _regex_entities(text, limit)
    seen, out = set(), []
    for ent in nlp(text[:4000]).ents:
        if ent.label_ not in _KEEP_LABELS:
            continue
        name = ent.text.strip(" '’\".,")
        if len(name) < 3 or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append(name)
        if len(out) >= limit:
            break
    return out or _regex_entities(text, limit)
