"""v6.6.8 — site-wide translation backend (clean-slate rebuild).

The old translation stack (/api/translate, /api/translate/content,
processing/translate.py, content_translations cache) translated only feed/story
summaries. This replaces it with ONE primitive the frontend DOM translator uses:
translate a batch of visible strings into a target language, cache-first.

Design (owner's spec): the UI is authored in English. When the user picks a
language, the frontend collects every visible text string and sends it here;
we return each string translated into the target language (already-target
strings pass through the model unchanged). Results are cached per (lang, text)
so the finite UI vocabulary is translated once and thereafter served instantly.
"""

import hashlib
import json

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

TRANSLATE_PROMPT = """You are a professional UI/news localizer. Translate each
string in the JSON array from English into {language}. Rules:
- Return ONLY a JSON array of the SAME length, in the SAME order.
- Translate naturally and concisely, as UI labels / news text.
- If a string is already in {language}, a proper noun, a number, a code, an
  emoji, or has no translatable words, return it UNCHANGED.
- Preserve leading/trailing punctuation and symbols (▸ · ⚔ →, digits, %).
- Never add explanations, quotes, or extra items."""


def available():
    return llm.available()


def _key(lang, text):
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
    return f"i18n:{lang}:{h}"


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

    if misses and llm.available():
        language = LANG_NAMES.get(lang, lang)
        # batch in chunks so one call isn't unboundedly large
        for i in range(0, len(misses), 40):
            chunk = misses[i:i + 40]
            translated = _translate_chunk(chunk, language)
            for src, dst in zip(chunk, translated):
                out[src] = dst
                meta_set(_key(lang, src), dst)
    # anything still unresolved (no provider / model failure) passes through
    for t in texts:
        out.setdefault(t, t)
    return out


def _translate_chunk(chunk, language):
    """One model call translating a list of strings; returns a same-length list.
    On any problem, returns the originals so nothing breaks."""
    try:
        raw = llm.complete(
            TRANSLATE_PROMPT.format(language=language),
            [{"role": "user", "content": json.dumps(chunk, ensure_ascii=False)}],
            max_tokens=2000, timeout=45, json_mode=True, interactive=True)
    except Exception:  # noqa: BLE001
        return list(chunk)
    if not raw:
        return list(chunk)
    t = raw.strip()
    if t.startswith("```"):
        t = t.strip("`").removeprefix("json").strip()
    # json_mode may wrap the array in an object; pull the first array out
    b, e = t.find("["), t.rfind("]")
    if b != -1 and e != -1:
        t = t[b:e + 1]
    try:
        arr = json.loads(t)
    except json.JSONDecodeError:
        return list(chunk)
    if not isinstance(arr, list) or len(arr) != len(chunk):
        return list(chunk)
    return [str(x) if x is not None else src for x, src in zip(arr, chunk)]
