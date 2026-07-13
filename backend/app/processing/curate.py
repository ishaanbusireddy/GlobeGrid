"""v8.16 — the LLM "wire editor": event TITLE review + CATEGORY review.

Owner: "use the llm to review the titles of events to make them more readable
— fix grammar, translate to English, punctuation and capitalization, remove
links or hashtags, truncate if too long, make more specific if too vague" and
"internally define categories strongly … so it has context when classifying".

This runs as a bounded background pass (same shape as geoplace.correct_recent):
a few recent unreviewed events per tick, one LLM call per event batch. The
prompt carries the full normative category definitions from
geopolitics/category_defs.py, so the model reviews the keyword classifier's
verdict against the same contract a human would read. Deterministic cleanups
(link/hashtag strip, whitespace, sentence-casing ALL-CAPS) happen in code
BEFORE the LLM ever sees the title — the model only does what code can't
(grammar, translation, specificity).

Every change is conservative:
  - a category is only changed to one of the KNOWN categories, and only when
    the model's verdict differs from the current one;
  - a title is only replaced when the model returns a non-empty English title
    that isn't just an echo; length is clamped to 140 chars at a word boundary
    (the v6 §20 rule);
  - each event is marked reviewed (title_reviewed=1) whether or not the model
    was reachable-and-useful, so nothing loops forever.
"""

import json as _json
import re

from ..db.session import query, write_tx
from ..geopolitics.category_defs import CATEGORY_DEFINITIONS, definitions_prompt_block
from . import llm
from .textquality import strip_links

VALID_CATEGORIES = tuple(CATEGORY_DEFINITIONS.keys())

REVIEW_PROMPT = """You are a wire-desk copy editor for a global event tracker.
For EACH numbered news item you receive, return the corrected title and the
correct category.

TITLE rules: clear English (translate if needed), proper capitalization and
punctuation, no links/hashtags/handles, no ALL CAPS, no trailing site names,
under 140 characters, and if the title is vague ("Big news from the region"),
make it specific using the description. If the title is already good, return
it unchanged.

CATEGORY rules — assign exactly one, by these definitions:
{defs}

Return ONLY valid JSON, an object keyed by the item numbers:
{{"1": {{"title": "...", "category": "..."}}, "2": {{...}}}}"""

_HASHTAG_RE = re.compile(r"[#@][\w_]+")
_WS_RE = re.compile(r"\s+")


def _pre_clean(title: str) -> str:
    """Deterministic cleanups that never need a model."""
    t = strip_links(title or "")
    t = _HASHTAG_RE.sub("", t)
    t = _WS_RE.sub(" ", t).strip(" -–|:")
    # sentence-case an ALL-CAPS headline (v6 §20 rule, applied here too)
    letters = [c for c in t if c.isalpha()]
    if letters and sum(1 for c in letters if c.isupper()) / len(letters) > 0.85:
        t = t.capitalize()
    return t.strip()


def _clamp(title: str, limit: int = 140) -> str:
    if len(title) <= limit:
        return title
    cut = title[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-") + "…"


def review_recent(limit: int = 6) -> int:
    """Review a small batch of recent unreviewed events. Returns how many rows
    were changed (title or category). Best-effort; never raises."""
    rows = query(
        "SELECT id, title, description, category FROM events"
        " WHERE is_synthetic = 0 AND (title_reviewed IS NULL OR title_reviewed = 0)"
        " ORDER BY occurred_at DESC LIMIT ?", (limit,))
    if not rows:
        return 0
    # deterministic pass first — it applies even with no model
    pre = {r["id"]: _pre_clean(r["title"]) for r in rows}
    verdicts = {}
    if llm.available():
        items = []
        for i, r in enumerate(rows, 1):
            items.append(f"{i}. title: {pre[r['id']][:200]}\n"
                         f"   current category: {r['category']}\n"
                         f"   description: {(r['description'] or '')[:280]}")
        try:
            text = llm.complete(
                REVIEW_PROMPT.format(defs=definitions_prompt_block()),
                [{"role": "user", "content": "\n".join(items)}],
                max_tokens=90 * len(rows) + 120, timeout=45, json_mode=True)
        except Exception:  # noqa: BLE001
            text = None
        if text:
            t = text.strip()
            if t.startswith("```"):
                t = t.strip("`").removeprefix("json").strip()
            b = t.find("{")
            if b != -1:
                t = t[b:t.rfind("}") + 1]
            try:
                d = _json.loads(t)
                if isinstance(d, dict):
                    for i, r in enumerate(rows, 1):
                        v = d.get(str(i))
                        if isinstance(v, dict):
                            verdicts[r["id"]] = v
            except (_json.JSONDecodeError, TypeError, ValueError):
                pass
    changed = 0
    for r in rows:
        new_title = pre[r["id"]]
        new_cat = r["category"]
        v = verdicts.get(r["id"])
        if v:
            mt = _WS_RE.sub(" ", str(v.get("title") or "")).strip()
            if mt and len(mt) >= 8:
                new_title = mt
            mc = str(v.get("category") or "").strip().lower()
            if mc in VALID_CATEGORIES and mc != r["category"]:
                new_cat = mc
        new_title = _clamp(new_title)
        try:
            with write_tx() as conn:
                if new_title != r["title"] or new_cat != r["category"]:
                    conn.execute(
                        "UPDATE events SET title = ?, category = ?,"
                        " title_reviewed = 1 WHERE id = ?",
                        (new_title, new_cat, r["id"]))
                    # keep a single-member story's headline in step (multi-
                    # member stories keep their own synthesized headline)
                    conn.execute(
                        "UPDATE stories SET headline = ? WHERE id IN ("
                        "  SELECT m.story_id FROM story_members m"
                        "  WHERE m.event_id = ?"
                        "  GROUP BY m.story_id HAVING COUNT(*) = 1)"
                        " AND headline = ?",
                        (new_title, r["id"], r["title"]))
                    changed += 1
                else:
                    conn.execute("UPDATE events SET title_reviewed = 1"
                                 " WHERE id = ?", (r["id"],))
        except Exception:  # noqa: BLE001
            continue
    return changed


def ensure_column():
    """Add the title_reviewed flag column if missing (additive, idempotent —
    the same pattern as geoplace.llm_geoplaced)."""
    try:
        with write_tx() as conn:
            cols = [c[1] for c in conn.execute("PRAGMA table_info(events)").fetchall()]
            if "title_reviewed" not in cols:
                conn.execute("ALTER TABLE events ADD COLUMN title_reviewed"
                             " INTEGER DEFAULT 0")
    except Exception:  # noqa: BLE001
        pass
