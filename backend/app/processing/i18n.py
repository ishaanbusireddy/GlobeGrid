"""Site-wide translation backend.

v6.6.12 — REWRITTEN to the technique dedicated local-LLM translators (e.g.
LibreTranslate's LTEngine) actually use, after the JSON-object protocol kept
failing on real local models:

  * NO `format:"json"`. Forcing JSON on a translation task makes small local
    models (llama3.1 etc.) echo the English input back inside the JSON instead
    of translating — the "everything stays English" bug. We ask for PLAIN TEXT.
  * A "professional translator" ROLE system prompt that says: output ONLY the
    translation, nothing else.
  * Small NUMBERED-LINE batches (fast) with a robust line parser, and a
    PER-STRING fallback (one call, whole reply = the translation) for anything a
    batch didn't translate. Per-string is the most reliable shape for a small
    model, so it's the safety net.

The frontend DOM translator calls translate_strings via POST /api/i18n/translate.
Results are cached per (lang, text) so the finite UI vocabulary is translated
once and thereafter served instantly.
"""

import hashlib
import re

from ..db.models import meta_get, meta_set
from . import llm

# language code -> English name for the model prompt (mirrors frontend LANGUAGES)
LANG_NAMES = {
    "en": "English", "bg": "Bulgarian", "hr": "Croatian", "cs": "Czech",
    "da": "Danish", "nl": "Dutch", "et": "Estonian", "fi": "Finnish",
    "fr": "French", "de": "German", "el": "Greek", "hu": "Hungarian",
    "ga": "Irish", "it": "Italian", "lv": "Latvian", "lt": "Lithuanian",
    "mt": "Maltese", "pl": "Polish", "pt": "Portuguese", "ro": "Romanian",
    "sk": "Slovak", "sl": "Slovenian", "es": "Spanish", "sv": "Swedish",
    "no": "Norwegian", "is": "Icelandic", "sq": "Albanian", "sr": "Serbian",
    "mk": "Macedonian", "bs": "Bosnian", "uk": "Ukrainian", "ru": "Russian",
    "be": "Belarusian", "tr": "Turkish", "ka": "Georgian", "hy": "Armenian",
    "az": "Azerbaijani", "kk": "Kazakh", "uz": "Uzbek", "he": "Hebrew",
    "ar": "Arabic", "fa": "Persian", "ur": "Urdu", "hi": "Hindi",
    "bn": "Bengali", "ta": "Tamil", "th": "Thai", "vi": "Vietnamese",
    "id": "Indonesian", "ms": "Malay", "tl": "Filipino", "zh": "Simplified Chinese",
    "zh-Hant": "Traditional Chinese", "ja": "Japanese", "ko": "Korean",
    "sw": "Swahili", "am": "Amharic", "ha": "Hausa", "yo": "Yoruba",
    "zu": "Zulu", "af": "Afrikaans",
}

# ── prompts ──────────────────────────────────────────────────────────────────
# Plain text, role-based, "output only the translation". No JSON, no fences.
_ONE_SYS = (
    "You are a professional translator. Translate the user's text into "
    "{language}. Output ONLY the {language} translation as plain text — no "
    "quotes, no notes, no explanations, and do NOT repeat the English. Keep any "
    "numbers, %, URLs and proper nouns. If the text is a single symbol or has "
    "nothing to translate, output it unchanged.")

_BATCH_SYS = (
    "You are a professional translator. Translate each numbered English line "
    "into {language}. Reply with the SAME numbered lines, each followed by only "
    "its {language} translation, like:\n"
    "1. <{language} translation of line 1>\n"
    "2. <{language} translation of line 2>\n"
    "Rules: translate the MEANING naturally (these are website labels and short "
    "news phrases); never output the English; never merge, skip or renumber "
    "lines; keep numbers/%/proper nouns; output ONLY the numbered lines, nothing "
    "else.")

_LINE_RE = re.compile(r'^\s*(\d+)\s*[.)\]:\-]\s*(.*\S)\s*$')


def available():
    return llm.available()


# Cache namespace. Bumped across the broken JSON-era builds so their cached
# English passthrough is never served; translate_strings never writes a
# passthrough, so poisoning can't recur.
_CACHE_NS = "i18n3"


def _key(lang, text):
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
    return f"{_CACHE_NS}:{lang}:{h}"


def _norm(s):
    """Collapse internal whitespace so a value is a single clean line for the
    numbered-line protocol (HTML renders whitespace the same way)."""
    return re.sub(r"\s+", " ", s).strip()


def translate_strings(texts, lang):
    """Return {original: translated} for every string in `texts`, translated to
    `lang`. Cache-first; only cache-misses hit the model. Never raises — on any
    failure the untranslated string passes through so the UI still renders."""
    out = {}
    misses = []
    for t in texts:
        if not t or not t.strip():
            out[t] = t
            continue
        cached = meta_get(_key(lang, t))
        if cached is not None:
            out[t] = cached
        else:
            misses.append(t)

    if misses and lang != "en" and llm.available():
        language = LANG_NAMES.get(lang, lang)
        resolved = _translate_many(misses, language)
        for src in misses:
            dst = resolved.get(src)
            if dst and dst.strip() and dst != src:
                out[src] = dst
                meta_set(_key(lang, src), dst)   # cache only genuine translations

    for t in texts:
        out.setdefault(t, t)
    return out


def _translate_many(strings, language):
    """Translate a list of strings → {original: translated}. Batch first (fast),
    then a per-string pass for anything the batch left untranslated."""
    result = {}
    # Batch in small groups; a numbered-line reply is easy for a small model.
    for i in range(0, len(strings), 8):
        group = strings[i:i + 8]
        for src, dst in _translate_batch(group, language).items():
            result[src] = dst
    # Per-string fallback for stragglers (batch dropped/echoed them). One call
    # each, whole reply = the translation — the most reliable shape.
    pending = [s for s in strings if s not in result]
    for s in pending:
        dst = _translate_one(s, language)
        if dst:
            result[s] = dst
    return result


def _translate_batch(group, language):
    """One numbered-line call for a small group → {original: translated} for the
    lines that came back genuinely translated."""
    norm = [_norm(s) for s in group]
    user = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(norm))
    raw = _complete(_BATCH_SYS.format(language=language), user, max_tokens=1200)
    if not raw:
        return {}
    lines = _parse_numbered(raw, len(group))
    out = {}
    for idx, src in enumerate(group):
        val = lines.get(idx)
        if val and val.strip() and _norm(val) != norm[idx]:
            out[src] = val.strip()
    return out


def _translate_one(s, language):
    """Single plain-text call; the whole reply is the translation."""
    raw = _complete(_ONE_SYS.format(language=language), _norm(s), max_tokens=400)
    if not raw:
        return None
    val = _clean_one(raw)
    if not val or _norm(val) == _norm(s):
        return None
    return val


def _complete(system, user, max_tokens):
    """One plain-text (NO json_mode) provider call; never raises."""
    try:
        return llm.complete(system, [{"role": "user", "content": user}],
                            max_tokens=max_tokens, timeout=45, interactive=True)
    except Exception:  # noqa: BLE001
        return None


def _parse_numbered(raw, n):
    """Parse '1. text' lines → {index0: text}. If the model didn't number but
    produced exactly n non-empty lines, map them positionally."""
    out = {}
    plain = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        m = _LINE_RE.match(line)
        if m:
            num = int(m.group(1)) - 1
            if 0 <= num < n:
                out[num] = m.group(2).strip()
        else:
            plain.append(line)
    if not out and len(plain) == n:
        for i, t in enumerate(plain):
            out[i] = t
    return out


def _clean_one(raw):
    """Strip the wrapping a chatty model adds around a single translation."""
    t = raw.strip()
    if t.startswith("```"):
        t = t.strip("`").strip()
    # pick the first CONTENT line, skipping preamble lines that end in ':'
    # ("Here is the translation:", "Translation:") which a chatty model prepends
    # on their own line.
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    content = [ln for ln in lines if not ln.endswith(":")]
    pick = content[0] if content else (lines[0] if lines else t)
    # drop an inline "Translation: X" / "Përkthimi - X" prefix
    pick = re.sub(r'^\s*[A-Za-zÀ-ÿ]{3,15}\s*[:\-]\s+', "", pick, count=1)
    return pick.strip().strip('"').strip("'").strip()


def diagnostics(lang="sq", samples=None):
    """Live self-test the user can run on THEIR machine: shows the exact prompt,
    the model's RAW reply and the parsed result for a few strings, so 'is my
    Ollama actually translating?' is answerable without any faking."""
    samples = samples or ["Live feed", "stories", "conflicts", "Settings"]
    language = LANG_NAMES.get(lang, lang)
    norm = [_norm(s) for s in samples]
    user = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(norm))
    raw = _complete(_BATCH_SYS.format(language=language), user, max_tokens=1200)
    parsed = _translate_batch(samples, language) if raw else {}
    # per-string too, for the single most reliable path
    one_raw = _complete(_ONE_SYS.format(language=language), norm[0], max_tokens=200)
    return {
        "lang": lang, "language": language,
        "available": llm.available(),
        "provider_error": llm.last_error(),
        "batch_prompt": _BATCH_SYS.format(language=language),
        "batch_input": user,
        "batch_raw_reply": raw,
        "batch_parsed": parsed,
        "one_input": norm[0],
        "one_raw_reply": one_raw,
        "one_parsed": _clean_one(one_raw) if one_raw else None,
    }
