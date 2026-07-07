"""v4 §11 — display-text normalization and deeper summaries.

§11.1: a lightweight, deterministic normalization pass applied ONLY to the
system's own generated headline/summary text at display-generation time —
the raw stored source text is never modified and stays available for exact
citation. Handles the bulk of wire-service capitalization/punctuation
noise without a model call; only genuinely malformed input would need one.

§11.2: the one-paragraph summary is a floor, not a ceiling — a 'read more'
deep summary is generated on demand (cached on stories.deep_summary),
still source-linked per the attribution requirement.
"""

import json
import logging
import re

from ..db.session import query, query_one, write_tx

log = logging.getLogger("textquality")

# words kept lowercase in title case (unless first/last)
_SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "of",
          "on", "or", "the", "to", "via", "vs", "with", "from", "into", "over"}
# tokens whose casing is meaningful — never re-cased
_KEEP = re.compile(r"^(?:[A-Z]{2,6}s?|[A-Za-z]*[0-9][A-Za-z0-9.%$-]*|"
                   r"[a-z]+[A-Z][A-Za-z]*|Mc[A-Z][a-z]+|.*'.*)$")

_WS = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?%)])")
_SPACE_AFTER_OPEN = re.compile(r"([(\[])\s+")
_MULTI_PUNCT = re.compile(r"([!?.])\1{1,}")
# v5 §1 — raw URLs must never appear inline in a generated title/summary;
# they live only in the citation/attribution area. Matches http(s):// and
# bare www./domain-style links, plus a trailing "(source: ...)" tail.
_URL = re.compile(r"\(?\s*(?:source:?\s*)?(?:https?://|www\.)\S+\)?"
                  r"|\b\S+\.(?:com|org|net|gov|io|co|news|info)/\S*", re.I)


def strip_links(text: str) -> str:
    """v5 §1 — remove any URL from generated display text. The original
    source text and its link are untouched in the citation area; this only
    cleans the system's own synthesized headline/summary string."""
    from ..config import cfg
    try:
        if not cfg("content", "strip_links_from_titles"):
            return text
    except KeyError:
        pass
    if not text:
        return text
    return _WS.sub(" ", _URL.sub(" ", text)).strip(" -–—|·")


# v6 §3 — emoji and pictographs are stripped from titles unless factually
# part of the story (rare enough that the rule is simply: strip them)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF"
                    "\U0001F1E6-\U0001F1FF\u2b00-\u2bff\ufe0f]")
HEADLINE_MAX_CHARS = 140


def _sentence_case_allcaps(words: list[str]) -> list[str]:
    """v6 §3 — re-case a degenerate ALL-CAPS headline to sentence case.
    Only short caps runs (2-4 letters: UN, EU, USA, NATO, KYIV) survive as-is
    — in an all-caps line a 5+-letter 'acronym' is almost never one."""
    out = []
    for i, w in enumerate(words):
        bare = w.strip(".,;:!?()[]\"'")
        if any(c.isdigit() for c in bare) or \
                (bare.isupper() and 2 <= len(bare) <= 4
                 and bare.lower() not in _SMALL):
            out.append(w)
        elif i == 0:
            out.append(w[:1].upper() + w[1:].lower() if w else w)
        else:
            out.append(w.lower())
    return out


def normalize_headline(text: str) -> str:
    """Deterministic title standardization (v4 §11.1, extended v6 §3):
    sentence case, no emoji, no raw links, no unfinished trailing
    fragments, hard length cap with clean word-boundary truncation.
    Meaning untouched; the raw stored source text is never modified."""
    if not text:
        return text
    t = strip_links(text)                # v5 §1 — no raw links in titles
    t = _EMOJI.sub("", t)                # v6 §3 — no emoji in titles
    t = _WS.sub(" ", t).strip()
    t = _SPACE_BEFORE_PUNCT.sub(r"\1", t)
    t = _SPACE_AFTER_OPEN.sub(r"\1", t)
    t = _MULTI_PUNCT.sub(r"\1", t)
    t = t.rstrip(" -–—|,;:")             # v6 §3 — no unfinished trailing bits
    words = t.split(" ")
    # v6 §3 sentence case: only a degenerate ALL-CAPS headline is fully
    # re-cased — any headline with ordinary mixed casing already IS sentence
    # case apart from its first word, and lowercasing its interior would
    # destroy proper nouns ('Fed' → 'fed', 'Rostov' → 'rostov')
    letters = [c for c in t if c.isalpha()]
    upper_ratio = sum(1 for c in letters if c.isupper()) / max(1, len(letters))
    if upper_ratio >= 0.85:
        t = " ".join(_sentence_case_allcaps(words))
    else:
        if words and words[0] and words[0][0].islower() and not _KEEP.match(words[0]):
            words[0] = words[0][0].upper() + words[0][1:]
        t = " ".join(words)
    # v6 §3 — hard cap with clean truncation at a word boundary
    if len(t) > HEADLINE_MAX_CHARS:
        cut = t[:HEADLINE_MAX_CHARS]
        if " " in cut:
            cut = cut[:cut.rfind(" ")]
        t = cut.rstrip(" ,;:-–—") + "…"
    return t


def normalize_summary(text: str) -> str:
    """Sentence-level cleanup for generated summaries (§11.1)."""
    if not text:
        return text
    t = strip_links(text)                # v5 §1
    t = _WS.sub(" ", t).strip()
    t = _SPACE_BEFORE_PUNCT.sub(r"\1", t)
    t = _MULTI_PUNCT.sub(r"\1", t)
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    if t and t[-1] not in ".!?\"”":
        t += "."
    return t


DEEP_SUMMARY_PROMPT = """You are writing the BIG-PICTURE analytical brief for a correlated
story cluster, grounded ONLY in the provided facts (every fact carries its
source). The reader already sees the headline, the summary and the event
timeline — so DO NOT re-narrate what happened. Instead explain the PROCESSES
and dynamics underneath it, as 3-6 tight markdown bullet points:
- the structural forces / underlying drivers at work,
- the key actors and what each is actually trying to achieve,
- how the pieces connect across sources and time (the mechanism, not the play-by-play),
- what is materially at stake, and
- where this plausibly heads next.
Each bullet one or two sentences, sharp and analytical. Name outlets only when
attributing a specific contested claim. No speculation beyond the provided
facts. Output ONLY the markdown bullets — no headers, no intro, no paragraphs."""


def deep_summary(story_id: str, expand: bool = False) -> tuple[int, dict]:
    """§11.2 — generate-and-cache the expanded summary for one story."""
    story = query_one("SELECT id, headline, summary, deep_summary FROM stories"
                      " WHERE id = ?", (story_id,))
    if not story:
        return 404, {"error": "story not found"}
    if story["deep_summary"] and not expand:
        return 200, {"deep_summary": story["deep_summary"], "cached": True}
    # v5 §18 — route through the provider abstraction: works with Claude, a
    # free tier (Gemini/Groq/…), or local Ollama, whichever is configured
    from .llm import complete, available
    if not available():
        return 200, {"deep_summary": None,
                     "note": "Deep synthesis needs an LLM provider (Claude key, a "
                             "free tier, or local Ollama — see Settings); the standard "
                             "summary and full source list remain available."}
    from .causal_link import _cluster_facts
    facts = _cluster_facts(story_id)
    if not facts:
        return 200, {"deep_summary": None, "note": "no member facts yet"}
    # v6.4.2 — interactive: the user just clicked "deep summary" and is waiting
    # v6.6 — 'full summary' = force a LONGER regeneration with more detail
    prompt = DEEP_SUMMARY_PROMPT if not expand else (DEEP_SUMMARY_PROMPT +
        "\n\nEXPANDED MODE: the user asked for the full picture. Write 8-14 "
        "bullets organized under 2-4 short '### ' headers, covering every "
        "significant thread, actor, cause and consequence in the cluster — "
        "detailed enough that no source article needs opening.")
    text = complete(prompt, [{"role": "user", "content": json.dumps(
        {"headline": story["headline"], "summary": story["summary"],
         "cluster_facts": facts})}], max_tokens=650 if not expand else 1200,
             timeout=30, interactive=True)
    if not text:
        return 502, {"error": "deep summary generation failed (no provider succeeded)"}
    # v6.2 — bullet-preserving cleanup: strip tracker junk but KEEP the newlines
    # so the markdown bullets render as bullets (normalize_summary collapses
    # all whitespace and would fuse them into one wall of text — the exact
    # thing the owner asked us to stop doing).
    text = strip_links(text).strip()
    with write_tx() as conn:
        conn.execute("UPDATE stories SET deep_summary = ? WHERE id = ?",
                     (text, story_id))
    return 200, {"deep_summary": text, "cached": False}
