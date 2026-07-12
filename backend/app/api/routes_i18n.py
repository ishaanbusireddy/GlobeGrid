"""v8.15 (Roadmap Update 3) — the rebuilt live-translation API.

Exactly one primitive plus one diagnostics view:

  POST /api/i18n/translate {lang, texts:[…]}
      → {lang, translations:[…], untranslated:[indices]}
      The `untranslated` list is the honesty guarantee made visible on the
      wire (roadmap §3.2): those indices are STILL ENGLISH after both the
      batch attempt and the per-string retry — the frontend marks them, the
      cache skips them, and the next request retries them. A response with
      untranslated=[] is a genuine full success; nothing is ever silently
      passed through as translated.

  GET /api/i18n/diagnostics?lang=sq
      → the exact prompt, the model's RAW reply, and the parsed result for
      the real batch + per-string paths — the owner's Phase-B ground-truth
      view against their own model (roadmap §3.5 Layer 2).
"""

from ..processing import i18n2
from .router import route


@route("POST", "/api/i18n/translate")
def i18n_translate(params, q, body):
    body = body or {}
    lang = (body.get("lang") or "en").strip()
    texts = body.get("texts") or []
    if not isinstance(texts, list) or any(not isinstance(t, str) for t in texts):
        return 400, {"error": "texts must be a list of strings"}
    if len(texts) > 400:
        return 400, {"error": "at most 400 strings per request"}
    res = i18n2.translate_strings(lang, texts, interactive=True)
    return 200, {"lang": lang, **res}


@route("GET", "/api/i18n/diagnostics")
def i18n_diagnostics(params, q, body):
    return 200, i18n2.diagnostics((q.get("lang") or "sq").strip())
