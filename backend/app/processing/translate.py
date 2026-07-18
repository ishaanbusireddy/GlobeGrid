"""v6 §10/§11 — the two-sided translation pipeline, Groq-first (§1).

§11 (display side): site-wide instant translation. Every translated string
is cached per (content_id, language, field) in content_translations, so a
re-render is instant after the first translation. New content translates on
ARRIVAL for every language a client has actually selected (tracked in
app_meta 'active_languages'), via the scheduler's translate_recent job —
not on first view.

§10 (ingestion side): local-language reporting is translated to English at
extraction time so the cross-lingual correlation/synthesis path (v3 §4)
compares meaning, not scripts. Separate concern from display translation.

Both sides route through processing.llm (Groq primary) and degrade cleanly:
no provider → no translation, original text flows through untouched.
"""

import json
import logging
import re

from . import llm
from ..config import cfg
from ..db.models import meta_get, meta_set, now_iso
from ..db.session import query, write_tx
from ..i18n_names import LANGUAGE_NAMES

log = logging.getLogger("translate")


def _lang_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


# ---------- §11 display-time cache ----------

def get_cached(content_id: str, language: str, fields: tuple[str, ...]) -> dict:
    rows = query(
        "SELECT field, translated_text FROM content_translations"
        " WHERE content_id = ? AND language = ?", (content_id, language))
    have = {r["field"]: r["translated_text"] for r in rows}
    return {f: have[f] for f in fields if f in have}


def _store(content_id: str, language: str, values: dict) -> None:
    with write_tx() as conn:
        for field, text in values.items():
            conn.execute(
                "INSERT INTO content_translations (content_id, language, field,"
                " translated_text, created_at) VALUES (?,?,?,?,?)"
                " ON CONFLICT(content_id, language, field) DO UPDATE SET"
                " translated_text = excluded.translated_text",
                (content_id, language, field, text, now_iso()))


def _extract_json_array(text: str):
    """v6.1 — Llama/Groq don't reliably return bare JSON: they wrap it in
    ```json fences, add a "Here is the translation:" preamble, or trail a
    note. Strip fences, then bracket-match the first balanced [...] (ignoring
    brackets inside strings) so a chatty model still parses. Returns the
    decoded list or None."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        # drop an optional leading "json" language tag
        nl = text.find("\n")
        if nl != -1 and text[:nl].strip().lower() in ("json", ""):
            text = text[nl + 1:]
        text = text.strip("`").strip()
    # fast path
    try:
        val = json.loads(text)
        return val if isinstance(val, list) else None
    except json.JSONDecodeError:
        pass
    # bracket-match the first top-level array
    start = text.find("[")
    if start == -1:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    val = json.loads(text[start:i + 1])
                    return val if isinstance(val, list) else None
                except json.JSONDecodeError:
                    return None
    return None


def translate_batch(items: list[dict], language: str,
                    interactive: bool = False) -> dict[str, dict]:
    """Translate a batch of {id, headline?, summary?} items into `language`,
    reading the cache first and translating only the misses in ONE model
    call (one retry on a malformed reply). Returns {content_id: {field: text}}
    for everything it has. v6.4.2 — `interactive=True` (the display route: a
    user switched language and is looking at the feed) rides out short Groq
    rate-limit windows; the on-arrival scheduler job stays background."""
    out: dict[str, dict] = {}
    misses = []
    for item in items:
        fields = tuple(f for f in ("headline", "summary") if item.get(f))
        cached = get_cached(item["id"], language, fields)
        out[item["id"]] = cached
        missing = {f: item[f] for f in fields if f not in cached}
        if missing:
            misses.append({"id": item["id"], **missing})
    if not misses or not llm.available():
        return out
    lang = _lang_name(language)
    prompt = (
        "You are a professional news translator. Translate every 'headline' and"
        f" 'summary' value in the JSON below into {lang}. Return ONLY a JSON"
        " array — one object per input, same 'id', same keys, values translated"
        " into " + lang + ". Preserve proper nouns, numbers and dates. Do not"
        " add, drop, reorder, or comment. Output must start with '[' and end"
        " with ']'.")
    payload = json.dumps(misses, ensure_ascii=False)
    translated = None
    # v6.2/v6.4.1 — the per-call timeout MUST leave room for BOTH attempts plus
    # the transport's hard-deadline buffer inside the client's 60s ceiling
    # (client.js translateContent timeout: 60000): 2 × (22s + 6s buffer) = 56s.
    # The old 90s (then 40s) budgets let a slow batch outlive the browser abort
    # even when the server eventually finished.
    for attempt in range(2):   # v6.1 — one retry; models occasionally chatter
        text = llm.complete(prompt, [{"role": "user", "content": payload}],
                            max_tokens=2600, timeout=22, interactive=interactive)
        if not text:
            log.warning("translate_batch_no_provider_response",
                        extra={"data": {"lang": language, "attempt": attempt}})
            continue
        translated = _extract_json_array(text)
        if translated is not None:
            break
        log.warning("translate_batch_malformed", extra={"data": {
            "lang": language, "attempt": attempt, "sample": text[:120]}})
    if not isinstance(translated, list):
        return out
    for t in translated:
        if not isinstance(t, dict) or "id" not in t:
            continue
        values = {f: t[f] for f in ("headline", "summary")
                  if isinstance(t.get(f), str) and t[f].strip()}
        if values:
            _store(str(t["id"]), language, values)
            out.setdefault(str(t["id"]), {}).update(values)
    return out


# ---------- §11 active-language tracking + on-arrival job ----------

def note_active_language(code: str) -> None:
    """Called when a client sets a UI language — makes the on-arrival job
    translate new content into it without waiting for a view."""
    if not code or code == "en":
        return
    active = set(json.loads(meta_get("active_languages") or "[]"))
    if code not in active:
        active.add(code)
        meta_set("active_languages", json.dumps(sorted(active)))


def translate_recent(batch_size: int = 15) -> int:
    """Scheduler job (§11 instant_translate_on_arrival): translate recently
    updated stories into every active language that doesn't have them yet."""
    if not cfg("translation", "instant_translate_on_arrival"):
        return 0
    if not llm.available():
        return 0
    active = json.loads(meta_get("active_languages") or "[]")
    if not active:
        return 0
    done = 0
    for lang in active:
        rows = query(
            "SELECT id, headline, summary FROM stories s WHERE is_synthetic = 0"
            " AND last_updated_at >= datetime('now', '-1 day')"
            " AND NOT EXISTS (SELECT 1 FROM content_translations t WHERE"
            "   t.content_id = s.id AND t.language = ? AND t.field = 'headline')"
            " ORDER BY last_updated_at DESC LIMIT ?", (lang, batch_size))
        if rows:
            translate_batch([dict(r) for r in rows], lang)
            done += len(rows)
    if done:
        log.info("translated_on_arrival", extra={"data": {"items": done,
                                                          "languages": active}})
    return done


def translate_recent_to_english(batch_size: int = 15) -> int:
    """v8.18 — reverse translation (owner: "when English is selected, translate
    non-English CONTENT into English — Russian/Ukrainian/Japanese feed items").

    Recent stories whose HEADLINE reads as non-English get an English rendering
    stored under language='en' in content_translations, so the feed can show the
    English version to an English UI while keeping the original available. Reuses
    translate_batch (which targets any language, English included). Best-effort:
    no provider → nothing translated, the original flows through untouched (the
    standing honest-degradation rule; real output needs the configured model)."""
    if not llm.available():
        return 0
    rows = query(
        "SELECT id, headline, summary FROM stories s WHERE is_synthetic = 0"
        " AND last_updated_at >= datetime('now', '-2 day')"
        " AND NOT EXISTS (SELECT 1 FROM content_translations t WHERE"
        "   t.content_id = s.id AND t.language = 'en' AND t.field = 'headline')"
        " ORDER BY last_updated_at DESC LIMIT ?", (batch_size * 3,))
    todo = [dict(r) for r in rows if looks_non_english(r["headline"] or "")][:batch_size]
    if not todo:
        return 0
    translate_batch(todo, "en")
    log.info("reverse_translated_to_english", extra={"data": {"items": len(todo)}})
    return len(todo)


# ---------- §10 ingestion-time translation for correlation ----------

_NON_LATIN = re.compile(r"[Ѐ-ӿ֐-׿؀-ۿऀ-ॿ"
                        r"฀-๿က-႟一-鿿぀-ヿ"
                        r"가-힯]")


def looks_non_english(text: str) -> bool:
    """Cheap script-based heuristic: enough non-Latin characters means the
    text needs translating before it can correlate against English coverage."""
    if not text:
        return False
    hits = len(_NON_LATIN.findall(text))
    return hits >= max(3, len(text) * 0.2)


def to_english_for_correlation(text: str) -> str:
    """§10 — best-effort English rendering used ONLY for embeddings and
    correlation; the original text stays on the fact for citation. Returns
    the input unchanged when no provider is configured or the text already
    reads as English/Latin script."""
    if not text or not looks_non_english(text) or not llm.available():
        return text
    out = llm.complete(
        "Translate this news headline/snippet to English. Return only the"
        " translation, nothing else.",
        [{"role": "user", "content": text[:600]}], max_tokens=300, timeout=30)
    return out.strip() if out else text
