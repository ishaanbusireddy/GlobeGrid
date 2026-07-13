"""v8.15 (Roadmap Update 3) — live AI translation, rebuilt from the root-cause
retrospective of the five scrapped attempts (v6.6.8 → v7.0).

Design rules, each pinned to the prior failure it prevents (roadmap §3.1/§3.2):

1. NEVER json_mode. The v6.6.12 finding was structural, not a parsing bug:
   JSON-shape compliance and the translation instruction compete for a small
   local model's attention and JSON wins, producing echoed English inside a
   valid object. Plain text, always — `llm.complete(..., json_mode=False)`.
2. Batches bounded by COUNT and CHARACTERS (v6.6.11: one long welcome-popup
   paragraph in a big batch broke parsing for the whole batch).
3. Line-oriented, per-line-tolerant parsing (v6.6.11): a malformed line 7
   never costs lines 1–6 or 8–20. Numbering-style drift (`1.` `1)` `1:`),
   code fences, quote wrapping, and even a JSON-object reply the model emits
   despite instructions are all salvaged per line.
4. Missing/echoed lines become STRAGGLERS retried one-at-a-time; after that,
   the string stays English and the caller is TOLD (the honesty guarantee —
   the direct fix for v6.6.10's silent full-English passthrough that looked
   like success).
5. Fresh cache namespace `i18n_v2` (v6.6.10: the old `i18n` namespace was
   poisoned with cached English passthroughs even after the bug was fixed);
   ONLY genuine translations are ever cached, so a transient failure is
   retried next request instead of frozen forever.

Verification contract (roadmap §3.5): the adversarial simulator suite in
backend/tests/test_i18n.py is NECESSARY, NOT SUFFICIENT. No changelog entry
may call this feature "working" until scripts/verify_translation_live.py has
passed against a REAL model — every prior attempt shipped "verified" on
simulators alone and every one was broken on the owner's machine.
"""

import hashlib
import json
import logging
import re
import threading
import time

from ..db.models import meta_get, meta_set
from ..i18n_names import LANGUAGE_NAMES
from . import llm

log = logging.getLogger("i18n2")

# from v6.6.11's fix: bound by BOTH count and characters
MAX_BATCH_COUNT = 20
MAX_BATCH_CHARS = 900

# v8.15.1 — THE FLOOD FIX. Translation may never have more than ONE real
# generation chain in flight, period. Without this gate, a page with ~100
# unique strings unfolded into 5+ sequential LLM calls per request, and the
# MutationObserver's rescans stacked overlapping requests on top — starving
# every other LLM feature (the analyst timed out waiting behind the pile).
# Semantics, mirroring llm.py's proven v6.4.2 interactive/background split
# one layer up:
#   - interactive (the user's own explicit language switch): WAITS its turn,
#     bounded by _GATE_WAIT_INTERACTIVE.
#   - background (an observer-triggered rescan): try-acquire; if translation
#     is already running, SKIP — the strings come back as `deferred` and the
#     next pass picks them up. Nothing is lost, nothing piles up.
_GATE = threading.Lock()
_GATE_WAIT_INTERACTIVE = 20.0
# Wall-clock budget per call: once spent, no NEW batch is started — what's
# done is returned, the rest comes back as `deferred` so the frontend fills
# the page progressively instead of one call monopolizing the model for the
# whole page. At least one batch always runs when the gate was acquired, so
# every call makes progress (no livelock).
_BUDGET_INTERACTIVE = 10.0
_BUDGET_BACKGROUND = 6.0

_SYSTEM = (
    "You are a professional translator. You will receive a numbered list of "
    "English strings. Reply with the SAME numbers, each followed by ONLY the "
    "translation into {lang} — never the English original, never an "
    "explanation, never a preamble. If a string is a proper noun or already "
    "in {lang}, output it unchanged."
)

# tolerant line matcher: "1. text" / "1) text" / "1: text" / "1 text"
_LINE_RE = re.compile(r"^\s*[>\-\*\s]*(\d+)\s*[.):\-]?\s+(.+?)\s*$", re.MULTILINE)
# salvage for the "model emitted JSON anyway" case: "1": "text" pairs
_JSON_PAIR_RE = re.compile(r'"(\d+)"\s*:\s*"((?:[^"\\]|\\.)*)"')
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*$", re.MULTILINE)


def _cache_key(lang: str, text: str) -> str:
    # versioned namespace so a future protocol change can't collide with this
    # rebuild's cache (and this rebuild can't touch any pre-v7.0 poisoned row)
    return f"i18n_v2:{lang}:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def _clean_line(text: str) -> str:
    t = text.strip()
    # strip symmetric quote wrapping the model sometimes adds
    for a, b in (('"', '"'), ("'", "'"), ("«", "»"), ("„", "“")):
        if len(t) > 1 and t.startswith(a) and t.endswith(b):
            t = t[1:-1].strip()
    return t


def parse_reply(raw: str, expected_count: int) -> dict[int, str]:
    """Extract {1-based index: translation} from a model reply, per line —
    tolerant of numbering drift, fences, preambles, trailing notes, quote
    wrapping, and a JSON-object reply emitted despite instructions. A broken
    line only loses ITSELF; everything parseable is kept."""
    if not raw:
        return {}
    body = _FENCE_RE.sub("", raw)
    out: dict[int, str] = {}
    for m in _LINE_RE.finditer(body):
        idx = int(m.group(1))
        if 1 <= idx <= expected_count and idx not in out:
            val = _clean_line(m.group(2))
            if val:
                out[idx] = val
    if len(out) < expected_count:
        # JSON-salvage pass: models don't always follow "never JSON" (§3.5's
        # 5%-of-calls adversarial case); pull "N": "text" pairs individually.
        for m in _JSON_PAIR_RE.finditer(body):
            idx = int(m.group(1))
            if 1 <= idx <= expected_count and idx not in out:
                try:
                    val = _clean_line(json.loads(f'"{m.group(2)}"'))
                except json.JSONDecodeError:
                    val = _clean_line(m.group(2))
                if val:
                    out[idx] = val
    if len(out) == 0 and expected_count == 1:
        # single-string call with an un-numbered reply: take the first
        # non-empty, non-preamble line positionally
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        lines = [ln for ln in lines if not ln.lower().startswith(
            ("here", "sure", "translation", "the translation"))]
        if lines:
            out[1] = _clean_line(lines[0])
    return out


def _batches(strings: list[str]) -> list[list[int]]:
    """Greedy batching bounded by BOTH count and character length: a batch of
    3 long paragraphs splits into 3 batches of 1 even though its count is far
    under MAX_BATCH_COUNT (the v6.6.11 long-string failure class)."""
    batches, cur, chars = [], [], 0
    for i, s in enumerate(strings):
        if cur and (len(cur) >= MAX_BATCH_COUNT or chars + len(s) > MAX_BATCH_CHARS):
            batches.append(cur)
            cur, chars = [], 0
        cur.append(i)
        chars += len(s)
    if cur:
        batches.append(cur)
    return batches


def _numbered(strings: list[str]) -> str:
    return "\n".join(f"{n + 1}. {s}" for n, s in enumerate(strings))


def _looks_echoed(src: str, dst: str) -> bool:
    """An 'echo' is the model returning the English input as the translation
    (the deepest v6.6.12 failure mode). Only meaningful for multi-word
    strings — a single word / proper noun legitimately survives translation
    unchanged, which the prompt explicitly allows."""
    return len(src.split()) >= 3 and src.strip().lower() == dst.strip().lower()


def translate_strings(lang: str, texts: list[str], interactive: bool = True,
                      budget_seconds: float | None = None) -> dict:
    """Translate `texts` into `lang`. Returns
    {"translations": [...], "untranslated": [indices], "deferred": [indices]}.

    The two failure lists mean DIFFERENT things and the caller must treat
    them differently:
      - `untranslated` (the honesty guarantee): the string WAS attempted this
        call and the model failed/echoed — it stays English, is never cached,
        and the UI marks it visibly. Not auto-retried in a tight loop.
      - `deferred` (v8.15.1): the string was NOT attempted this call — the
        gate was busy or the wall-clock budget ran out first. The caller
        should simply try again shortly; the frontend's progressive-fill
        pass does exactly that.

    Never raises; with no provider up, every attempted index lands in
    `untranslated`. Only one caller at a time ever reaches the model (see
    _GATE above) — an interactive call waits its turn, a background call
    defers instantly."""
    lang_name = LANGUAGE_NAMES.get(lang, lang)
    if lang == "en" or not texts:
        return {"translations": list(texts), "untranslated": [], "deferred": []}
    system = _SYSTEM.format(lang=lang_name)
    result: dict[int, str] = {}

    # cache-first (only genuine translations were ever written) — needs no
    # gate and no model, so a fully-cached request returns instantly even
    # while another translation is running.
    misses: list[int] = []
    for i, s in enumerate(texts):
        cached = meta_get(_cache_key(lang, s))
        if cached:
            result[i] = cached
        else:
            misses.append(i)

    deferred: set[int] = set()
    if misses:
        budget = budget_seconds if budget_seconds is not None else (
            _BUDGET_INTERACTIVE if interactive else _BUDGET_BACKGROUND)
        acquired = (_GATE.acquire(timeout=_GATE_WAIT_INTERACTIVE) if interactive
                    else _GATE.acquire(blocking=False))
        if not acquired:
            deferred.update(misses)
        else:
            try:
                start = time.monotonic()
                # batch pass — batch 0 ALWAYS runs (guaranteed progress);
                # later batches only start while budget remains.
                groups = _batches([texts[i] for i in misses])
                for bn, group in enumerate(groups):
                    idxs = [misses[j] for j in group]
                    if bn > 0 and time.monotonic() - start >= budget:
                        deferred.update(idxs)
                        continue
                    strs = [texts[i] for i in idxs]
                    raw = llm.complete(
                        system,
                        [{"role": "user", "content": _numbered(strs)}],
                        max_tokens=220 + 3 * sum(len(s) for s in strs),
                        timeout=40, json_mode=False,   # NEVER True (§3.2)
                        interactive=interactive)
                    parsed = parse_reply(raw or "", len(strs))
                    for local_n, translated in parsed.items():
                        src = strs[local_n - 1]
                        if _looks_echoed(src, translated):
                            continue   # an echo is a failure — retry below
                        result[idxs[local_n - 1]] = translated

                # straggler pass — one at a time (small isolated calls are
                # reliable per the v6.6.11 finding). Out of budget → the
                # straggler is DEFERRED (never attempted solo this call),
                # not marked as a model failure.
                for i in misses:
                    if i in result or i in deferred:
                        continue
                    if time.monotonic() - start >= budget:
                        deferred.add(i)
                        continue
                    raw = llm.complete(
                        system,
                        [{"role": "user", "content": f"1. {texts[i]}"}],
                        max_tokens=120 + 3 * len(texts[i]),
                        timeout=30, json_mode=False,
                        interactive=interactive)
                    single = parse_reply(raw or "", 1).get(1)
                    if single and not _looks_echoed(texts[i], single):
                        result[i] = single
            finally:
                _GATE.release()

    # persist ONLY genuine translations; assemble the honest response
    untranslated: list[int] = []
    out: list[str] = []
    for i, s in enumerate(texts):
        dst = result.get(i)
        if dst is None:
            out.append(s)              # last resort: keep English…
            if i not in deferred:
                untranslated.append(i)  # …attempted and failed — SAY SO
        else:
            out.append(dst)
            if dst != s:
                try:
                    meta_set(_cache_key(lang, s), dst)
                except Exception:  # noqa: BLE001 — cache write is best-effort
                    log.exception("i18n_cache_write_failed")
    if untranslated or deferred:
        log.info("i18n_partial", extra={"data": {
            "lang": lang, "total": len(texts),
            "untranslated": len(untranslated), "deferred": len(deferred)}})
    return {"translations": out, "untranslated": untranslated,
            "deferred": sorted(deferred)}


def diagnostics(lang: str = "sq") -> dict:
    """v6.6.12's proven pattern, rebuilt: run the REAL batch + per-string
    paths against whatever model is configured and return the exact prompt,
    the model's RAW reply, and the parsed result — the owner runs this
    against their own Ollama and reads the output (roadmap §3.5 Layer 2's
    'a human reads the raw output' rule, as an endpoint).

    DELIBERATELY not behind _GATE: this is the ground-truth probe, and it
    must answer even while a translation chain is running (or stuck) — it
    was exactly this endpoint that diagnosed the v8.15.0 flood, precisely
    because it bypassed the congested path. Its cost is two small bounded
    calls, owner-triggered."""
    lang_name = LANGUAGE_NAMES.get(lang, lang)
    system = _SYSTEM.format(lang=lang_name)
    sample = ["Live feed", "Settings",
              "How to navigate the globe",
              "Rotate the globe by dragging; scroll to zoom."]
    user = _numbered(sample)
    raw_batch = llm.complete(system, [{"role": "user", "content": user}],
                             max_tokens=400, timeout=40, json_mode=False,
                             interactive=True)
    parsed = parse_reply(raw_batch or "", len(sample))
    single_raw = llm.complete(system, [{"role": "user", "content": "1. Conflicts"}],
                              max_tokens=80, timeout=30, json_mode=False,
                              interactive=True)
    return {
        "lang": lang, "language_name": lang_name,
        "ai_available": llm.available(),
        "last_error": llm.last_error(),
        "system_prompt": system,
        "batch": {"user_message": user, "raw_reply": raw_batch,
                  "parsed": {str(k): v for k, v in parsed.items()},
                  "parsed_count": len(parsed), "expected": len(sample)},
        "single": {"user_message": "1. Conflicts", "raw_reply": single_raw,
                   "parsed": parse_reply(single_raw or "", 1).get(1)},
        "note": ("Run this on the machine with the real model. If raw_reply "
                 "is null, no provider is reachable; if parsed_count < "
                 "expected, paste this JSON into an issue — it contains "
                 "everything needed to diagnose."),
    }
