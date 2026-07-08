"""v6.3.3 — live AI feature self-test.

The owner reported that NO AI feature works (analyst, translation, summaries)
while the raw /api/analyst/diagnostics ping succeeds (368ms, valid JSON). That
split — the isolated provider call works but every real feature fails — means
the bug is NOT the Groq call itself but something in the shared feature path.
Guessing across an environment we can't reproduce has failed repeatedly, so
this page runs EACH real feature end-to-end, live, and shows exactly what
happens: latency, the actual reply (or the real error), for every path. Open
/api/diagnostics in the browser and read the table — it is the ground truth.

Every test is hard-bounded by a wall-clock deadline so the page itself can
never hang, no matter what's stuck underneath.
"""

import concurrent.futures as cf
import html as _html
import json
import time

from .router import route

_POOL = cf.ThreadPoolExecutor(max_workers=4, thread_name_prefix="diag")


def _timed(fn, timeout_s=50):   # v6.5 — headroom for local Ollama inference
    """Run fn() with a hard deadline. Returns (ok, ms, preview, error)."""
    t0 = time.time()
    fut = _POOL.submit(fn)
    try:
        preview = fut.result(timeout=timeout_s)
        return True, int((time.time() - t0) * 1000), str(preview)[:400], None
    except cf.TimeoutError:
        return False, int((time.time() - t0) * 1000), None, \
            f"HARD TIMEOUT after {timeout_s}s — this call hung (the real bug)"
    except Exception as exc:  # noqa: BLE001
        return False, int((time.time() - t0) * 1000), None, \
            f"{type(exc).__name__}: {exc}"


# ---- each feature's REAL code path, exercised live ----

def _test_provider_ping():
    from ..processing import llm
    return llm.complete("Reply with JSON {\"ok\":true}.",
                        [{"role": "user", "content": "ping"}],
                        max_tokens=20, timeout=25, json_mode=True, interactive=True)


def _test_ollama_server():
    """v6.5 — the PRIMARY provider is now local Ollama: is the server up, and
    is the configured model actually pulled? This row alone answers the two
    setup questions ('is Ollama running?' / 'did I pull the model?')."""
    from ..processing import llm
    tags = llm.ollama_tags()
    if tags is None:
        raise RuntimeError(
            f"no Ollama server at {llm.ollama_host()} — install from ollama.com, "
            f"then run:  ollama pull {llm.ollama_model()}   (the app uses it "
            "automatically; no key needed)")
    want = llm.ollama_model()
    pulled = any(t == want or t.startswith(want + ":") for t in tags)
    listing = ", ".join(tags) if tags else "(none pulled yet)"
    if not pulled:
        raise RuntimeError(
            f"server running but model '{want}' not pulled — run: ollama pull {want}"
            f"  · installed: {listing}")
    return f"running · model '{want}' ready · installed: {listing}"


def _test_dns():
    """v6.4.1 — raw OS resolution for the Groq host, showing address families.
    AAAA (IPv6) records here + hangs on the bigger calls = the classic
    sequential-connect-on-broken-IPv6 stall the transport rebuild pins away.
    (Only relevant when the cloud fallback is in use — local Ollama needs no DNS.)"""
    import socket as s
    infos = s.getaddrinfo("api.groq.com", 443, proto=s.IPPROTO_TCP)
    fams = [("IPv6 " if i[0] == s.AF_INET6 else "IPv4 ") + i[4][0] for i in infos]
    return " · ".join(dict.fromkeys(fams))


def _test_large_ping():
    """v6.4.1 — same trivial call as the ping but with ~4KB of context, the
    size class of a real analyst/translation request. Small-ping-OK +
    large-ping-HANG would indicate MTU/fragmentation (VPN) rather than DNS."""
    from ..processing import llm
    filler = ("Background context block. " * 160)[:4000]
    return llm.complete(
        "Ignore the context. Reply with JSON {\"ok\":true}.",
        [{"role": "user", "content": filler + "\nping"}],
        max_tokens=20, timeout=25, json_mode=True, interactive=True)


def _test_analyst():
    from . import routes_analyst as ra
    sid = ra._session(None)
    out = ra._answer_with_llm(
        "Give me a one-line status of the Russia-Ukraine war.",
        {"entity": None, "stories": [], "web_results": [],
         "global_instability_index": 50}, sid)
    return out.get("answer")


def _test_deep_summary():
    from ..processing import llm
    return llm.complete(
        "Summarize in 2 markdown bullets.",
        [{"role": "user", "content": json.dumps(
            {"headline": "Test event", "summary": "Something happened in a region."})}],
        max_tokens=200, timeout=30, interactive=True)


def _test_causal():
    from ..processing import llm
    return llm.complete(
        "Reply with JSON {\"narrative\":\"...\",\"confidence\":0.5}.",
        [{"role": "user", "content": "Two related events occurred."}],
        max_tokens=120, timeout=30, json_mode=True, interactive=True)


_TESTS = [
    ("Ollama server (local AI, primary)", _test_ollama_server),
    ("DNS resolve api.groq.com (fallback)", _test_dns),
    ("Provider ping (primary provider)", _test_provider_ping),
    ("Large-payload ping (~4KB)", _test_large_ping),
    ("Analyst answer (full path)", _test_analyst),
    ("Deep summary (LLM call)", _test_deep_summary),
    ("Causal narrative (LLM call)", _test_causal),
]


@route("GET", "/api/diagnostics")
def diagnostics_page(params, q, body):
    """Live feature self-test as an HTML page. GET /api/diagnostics."""
    from ..processing import llm
    providers = {name: llm._usable(name) for name in llm._order()}
    rows = []
    for label, fn in _TESTS:
        ok, ms, preview, error = _timed(fn)
        status = "✅ OK" if ok and preview and preview != "None" else "❌ FAIL"
        detail = _html.escape(preview or error or "(empty)")
        colour = "#1a7f37" if status.startswith("✅") else "#cf222e"
        rows.append(
            f"<tr><td>{_html.escape(label)}</td>"
            f"<td style='color:{colour};font-weight:600'>{status}</td>"
            f"<td>{ms} ms</td>"
            f"<td><code style='white-space:pre-wrap'>{detail}</code></td></tr>")
    prov = ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in providers.items())
    page = f"""<!doctype html><html><head><meta charset=utf-8>
<title>GlobeGrid AI feature self-test</title>
<style>
 body{{font:14px/1.5 system-ui,sans-serif;margin:24px;background:#0d1117;color:#e6edf3}}
 h1{{font-size:20px}} .meta{{color:#8b949e;margin-bottom:16px}}
 table{{border-collapse:collapse;width:100%}}
 td,th{{border:1px solid #30363d;padding:8px 10px;text-align:left;vertical-align:top}}
 th{{background:#161b22}} code{{color:#a5d6ff}}
</style></head><body>
<h1>GlobeGrid — live AI feature self-test</h1>
<div class=meta>ai_available: <b>{llm.available()}</b> · primary: <b>Ollama</b>
 ({_html.escape(llm.ollama_model())} @ {_html.escape(llm.ollama_host())}) ·
 groq_model (fallback): <b>{_html.escape(llm._groq_model())}</b><br>
providers usable: {_html.escape(prov)}</div>
<table><tr><th>Feature</th><th>Result</th><th>Time</th><th>Reply / error</th></tr>
{''.join(rows)}
</table>
<p class=meta>Each row runs the feature's real code path with a hard 50s deadline
(local inference gets extra headroom). A ✅ means that feature works on this
machine right now. A ❌ shows the actual error or "HARD TIMEOUT" if it hung.
Screenshot this and send it back.</p>
</body></html>"""
    return 200, {"_raw_html": page}
