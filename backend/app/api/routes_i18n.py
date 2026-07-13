"""v8.15 (Roadmap Update 3) — the rebuilt live-translation API.

Exactly one primitive plus one diagnostics view:

  POST /api/i18n/translate {lang, texts:[…], interactive:bool}
      → {lang, translations:[…], untranslated:[indices], deferred:[indices]}
      `untranslated` is the honesty guarantee made visible on the wire
      (roadmap §3.2): those indices were ATTEMPTED and are still English —
      the frontend marks them and the cache skips them. `deferred` (v8.15.1)
      means NOT attempted this call (the single-flight gate was busy or the
      per-call budget ran out) — the frontend simply retries them shortly,
      filling the page progressively. A response with both lists empty is a
      genuine full success; nothing is ever silently passed through.

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
    # v8.15.1 — the caller says whether a human is actively waiting (their
    # explicit language switch) or this is an observer-triggered background
    # rescan. Background calls yield instantly when translation is already
    # running or a provider cooldown is open, instead of stampeding the
    # model and starving the analyst (the v8.15.0 regression).
    interactive = bool(body.get("interactive", True))
    res = i18n2.translate_strings(lang, texts, interactive=interactive)
    return 200, {"lang": lang, **res}


@route("GET", "/api/i18n/diagnostics")
def i18n_diagnostics(params, q, body):
    return 200, i18n2.diagnostics((q.get("lang") or "sq").strip())
