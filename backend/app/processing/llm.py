"""v5 §18 — LLM provider abstraction with free/low-cost fallback.

One call site, many providers. `complete()` tries the configured primary
provider then walks llm_provider.fallback_order until one succeeds, so the
whole app can swap Anthropic for a free tier (Gemini / Groq / Cerebras via
OpenAI-compatible APIs) or fully-local Ollama without touching any of the
causal/debate/briefing/analyst call sites — exactly the CLAUDE_MODEL-style
config-driven swap v1 §7.2 anticipated.

Real, live options as of mid-2026 (checked, not assumed):
  - anthropic_open_source_grant: Anthropic's Claude for Open Source (launched
    Feb 2026) — qualifying AGPL projects like GlobeGrid can get 6 months of
    Claude Max free. Same model, same prompts, zero code change if granted.
    Uses the ordinary CLAUDE_API_KEY once issued.
  - gemini_free: Gemini 2.5 Flash, 1,500 req/day, no card. GEMINI_API_KEY.
  - groq_free: Llama 3.x on Groq, ~14,400 req/day, OpenAI-compatible, fast.
    GROQ_API_KEY.
  - cerebras_free: ~1M tokens/day open-weight, OpenAI-compatible.
    CEREBRAS_API_KEY.
  - openrouter: aggregator across many free tiers. OPENROUTER_API_KEY.
  - ollama_local: zero cost, no rate limit, fully private, runs offline.
    OLLAMA_HOST (default http://localhost:11434). The v1 §3 fallback path.

Every provider is best-effort and independently failing: a provider with no
key configured is skipped, a network/HTTP error falls through to the next,
and if all fail complete() returns None so callers keep their existing
graceful no-LLM behavior (low-confidence fallback, retrieval-only, etc.).
"""

import http.client
import io
import json
import logging
import os
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from ..config import CLAUDE_MODEL, cfg, env

log = logging.getLogger("llm")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              "gemini-2.5-flash:generateContent")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# v5.1.1 — urllib's default User-Agent ("Python-urllib/3.x") reads as a
# scraper to some providers' edge/WAF layer and gets blocked before the
# request ever reaches their auth logic, surfacing as an opaque 403 with no
# JSON body. Identify the app instead.
USER_AGENT = "GlobeGrid/5.1 (+https://github.com/ishaanbusireddy/GlobeGrid)"


# ---------------------------------------------------------------------------
# v6.4.1 — TRANSPORT REBUILD. The owner's /api/diagnostics table proved the
# stall is in Python's HTTPS connection setup itself: pure llm.complete()
# probes with no DB access hung right alongside the DB-touching ones, while a
# tiny ping intermittently succeeded (135ms). The classic Windows causes all
# live below urllib's `timeout=` (which does NOT bound them):
#   - getaddrinfo (DNS) stalls behind AV/VPN DNS interception;
#   - api.groq.com publishes IPv6 addresses, and socket.create_connection
#     tries resolved addresses SEQUENTIALLY with the FULL timeout each — a
#     broken-IPv6 machine burns 24s+ per AAAA before ever reaching IPv4
#     (browsers do parallel Happy Eyeballs; Python does not);
#   - a stale Windows registry proxy (Fiddler/VPN leftovers) that urllib
#     silently honors and that blackholes large POSTs.
# So provider calls no longer go through urllib at all (unless an explicit
# HTTP(S)_PROXY env var is set): we resolve the host ONCE with a bounded,
# cached, IPv4-preferred lookup, open a TLS connection PINNED to that single
# address (real SNI + hostname verification against the true host), and run
# the whole request under a wall-clock deadline in a worker thread — so no
# layer, however broken, can hang a caller past its declared timeout.
# ---------------------------------------------------------------------------

_DNS_CACHE: dict[str, tuple[str, float]] = {}
_DNS_LOCK = threading.Lock()


def _run_bounded(fn, deadline_s: float, stall_message: str):
    """Run fn() on a short-lived DAEMON thread with a wall-clock deadline.
    Deliberately not a ThreadPoolExecutor: its workers are joined at
    interpreter exit, so one abandoned stalled request would block Ctrl+C
    shutdown forever. A daemon thread just dies with the process. If fn()
    finishes in time its result/exception passes through unchanged; if it
    doesn't, TimeoutError(stall_message) is raised and the thread is
    abandoned (it exits on its own whenever the OS gives up)."""
    box: dict = {}
    done = threading.Event()

    def _runner():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 — re-raised in the caller
            box["error"] = exc
        finally:
            done.set()

    threading.Thread(target=_runner, daemon=True, name="llm-net").start()
    if not done.wait(deadline_s):
        raise TimeoutError(stall_message)
    if "error" in box:
        raise box["error"]
    return box["value"]


def _net_cfg(key: str, default):
    try:
        return cfg("network", key)
    except (KeyError, TypeError):
        return default


def _resolve(host: str, deadline_s: float = 6.0) -> str:
    """Bounded, cached, IPv4-preferred DNS. A successful lookup is cached
    (network.dns_cache_ttl_seconds) so feature calls never pay — or hang on —
    DNS again; a stall raises a clear error instead of blocking forever."""
    now = time.time()
    with _DNS_LOCK:
        hit = _DNS_CACHE.get(host)
        if hit and hit[1] > now:
            return hit[0]
    try:
        infos = _run_bounded(
            lambda: socket.getaddrinfo(host, 443, socket.AF_UNSPEC,
                                       socket.SOCK_STREAM),
            deadline_s,
            f"DNS resolution for {host} did not finish in {deadline_s}s "
            "(firewall/antivirus/VPN DNS interception?)")
    except TimeoutError:
        with _DNS_LOCK:
            stale = _DNS_CACHE.get(host)
        if stale:   # a stale answer beats a hang — IPs rarely move
            return stale[0]
        raise
    if bool(_net_cfg("prefer_ipv4", True)):
        # IPv4 first: sequential-connect on a broken-IPv6 machine otherwise
        # burns the full timeout per AAAA record before reaching a v4 address
        infos = sorted(infos, key=lambda i: 0 if i[0] == socket.AF_INET else 1)
    ip = infos[0][4][0]
    ttl = float(_net_cfg("dns_cache_ttl_seconds", 600))
    with _DNS_LOCK:
        _DNS_CACHE[host] = (ip, now + ttl)
    return ip


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """TLS to ONE pre-resolved address, with SNI + certificate verification
    still done against the real hostname — connect can never iterate a list
    of dead addresses."""

    def __init__(self, host: str, ip: str, port: int, timeout: float,
                 context: ssl.SSLContext):
        super().__init__(host, port, timeout=timeout, context=context)
        self._pinned_ip = ip

    def connect(self):
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        ctx = getattr(self, "_context", None) or ssl.create_default_context()
        self.sock = ctx.wrap_socket(sock, server_hostname=self.host)


def _proxy_from_env() -> str | None:
    """Explicit env-var proxies (the sandbox, corporate setups) are honored via
    the legacy urllib path. Windows REGISTRY proxies are deliberately ignored:
    a stale one (Fiddler/VPN leftover) silently blackholing POSTs is a classic
    cause of exactly the hang the owner hit, and urllib would obey it."""
    return (os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"))


def _do_post(url: str, body: dict, headers: dict, timeout: int) -> dict:
    parsed = urllib.parse.urlsplit(url)
    host, port = parsed.hostname, parsed.port
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    payload = json.dumps(body).encode()
    hdrs = {"user-agent": USER_AGENT, "content-type": "application/json",
            "accept": "application/json", "connection": "close", **headers}

    if parsed.scheme == "http":          # Ollama on localhost — no TLS, no DNS risk
        conn = http.client.HTTPConnection(host, port or 80, timeout=timeout)
    elif _proxy_from_env():
        # explicit proxy: fall back to urllib (it speaks CONNECT); the outer
        # wall-clock deadline still bounds it
        req = urllib.request.Request(url, data=payload, method="POST", headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    else:
        ip = _resolve(host)
        conn = _PinnedHTTPSConnection(host, ip, port or 443, timeout,
                                      ssl.create_default_context())
    try:
        conn.request("POST", path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
    except (OSError, ssl.SSLError):
        # a cached IP may have gone stale — evict so the next call re-resolves
        with _DNS_LOCK:
            _DNS_CACHE.pop(host, None)
        raise
    finally:
        conn.close()
    if resp.status >= 400:
        raise urllib.error.HTTPError(url, resp.status, resp.reason,
                                     resp.headers, io.BytesIO(raw))
    return json.loads(raw)


def _post(url: str, body: dict, headers: dict, timeout: int = 60) -> dict:
    """One provider POST under a HARD wall-clock deadline: DNS + connect + TLS
    + send + receive all together can never exceed timeout + the configured
    buffer, no matter which layer misbehaves underneath."""
    buffer_s = float(_net_cfg("request_deadline_buffer_seconds", 6))
    # a socket-level timeout raised INSIDE the worker keeps its own accurate
    # error (it passes through _run_bounded unchanged); the stall message
    # below only fires when the worker genuinely never finished in time.
    return _run_bounded(
        lambda: _do_post(url, body, headers, timeout),
        timeout + buffer_s,
        f"provider request exceeded the hard {timeout + buffer_s:.0f}s deadline "
        "(network stall below the socket timeout — DNS/IPv6/proxy); abandoned")


def _anthropic(system, messages, max_tokens, timeout, json_mode=False):
    key = env("CLAUDE_API_KEY")
    if not key:
        return None
    body = {"model": CLAUDE_MODEL, "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system
    data = _post(ANTHROPIC_URL, body, {
        "content-type": "application/json", "x-api-key": key,
        "anthropic-version": "2023-06-01"}, timeout)
    return "".join(b.get("text", "") for b in data.get("content", [])).strip()


def _openai_compatible(url, key, model, system, messages, max_tokens, timeout,
                       json_mode=False):
    if not key:
        return None
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {"model": model, "max_tokens": max_tokens, "messages": msgs}
    # v6.3.1 — force strict JSON when the caller needs it (the analyst). Groq's
    # OpenAI-compatible API guarantees a valid JSON object with this set, which
    # kills the "Llama wrapped its JSON in prose so we discarded the answer"
    # failure mode. Requires the word 'json' in the prompt (our prompts have it).
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = _post(url, body, {"content-type": "application/json",
                             "authorization": f"Bearer {key}"}, timeout)
    return data["choices"][0]["message"]["content"].strip()


def _gemini(system, messages, max_tokens, timeout, json_mode=False):
    key = env("GEMINI_API_KEY")
    if not key:
        return None
    parts = "\n\n".join(m["content"] for m in messages if isinstance(m.get("content"), str))
    gen_cfg = {"maxOutputTokens": max_tokens}
    if json_mode:
        gen_cfg["responseMimeType"] = "application/json"
    body = {"contents": [{"parts": [{"text": parts}]}], "generationConfig": gen_cfg}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    data = _post(f"{GEMINI_URL}?key={key}", body,
                 {"content-type": "application/json"}, timeout)
    cand = (data.get("candidates") or [{}])[0]
    return "".join(p.get("text", "")
                   for p in cand.get("content", {}).get("parts", [])).strip()


def ollama_host() -> str:
    return env("OLLAMA_HOST", "http://localhost:11434")


def ollama_model() -> str:
    """v6.5 — the Ollama model is a first-class config value
    (llm_provider.ollama_model); OLLAMA_MODEL in .env still wins for local
    experiments. llama3.1 (the 8B tag) is the default: strong enough for the
    analyst/translation prompts, small enough for ordinary hardware."""
    from_env = env("OLLAMA_MODEL")
    if from_env:
        return from_env
    try:
        return str(cfg("llm_provider", "ollama_model"))
    except (KeyError, TypeError):
        return "llama3.1"


def _ollama_floor(timeout: int) -> int:
    """v6.5 — local inference is slower than Groq's datacenter GPUs: the same
    650-token answer that Groq streams in 2s can take 30s+ on a laptop CPU.
    Feature call sites keep their (Groq-tuned) budgets; when the call lands on
    Ollama the timeout is raised to at least llm_provider.
    ollama_timeout_floor_seconds so local generations aren't cut off mid-answer."""
    try:
        floor = int(float(cfg("llm_provider", "ollama_timeout_floor_seconds")))
    except (KeyError, TypeError):
        floor = 40
    return max(timeout, floor)


def _ollama(system, messages, max_tokens, timeout, json_mode=False):
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    payload = {"model": ollama_model(), "messages": msgs, "stream": False,
               "options": {"num_predict": max_tokens}}
    if json_mode:
        payload["format"] = "json"
    try:
        data = _post(f"{ollama_host()}/api/chat", payload,
                     {"content-type": "application/json"}, _ollama_floor(timeout))
    except OSError:
        return None   # Ollama not running locally — skip quietly
    return (data.get("message") or {}).get("content", "").strip()


def _groq_model() -> str:
    """v6 §1 — the Groq model is a first-class config value
    (llm_provider.groq_model); GROQ_MODEL in .env still wins for local
    experiments."""
    from_env = env("GROQ_MODEL")
    if from_env:
        return from_env
    try:
        return str(cfg("llm_provider", "groq_model"))
    except (KeyError, TypeError):
        return "llama-3.3-70b-versatile"


def _groq(s, m, mt, to, json_mode=False):
    return _openai_compatible(GROQ_URL, env("GROQ_API_KEY"), _groq_model(),
                              s, m, mt, to, json_mode)


# provider key -> callable(system, messages, max_tokens, timeout, json_mode)
PROVIDERS = {
    "anthropic": _anthropic,
    "anthropic_open_source_grant": _anthropic,   # same API, grant-issued key
    "gemini_free": _gemini,
    "groq": _groq,          # v6 §1 canonical name
    "groq_free": _groq,     # v5.1 name kept as an alias — old configs still work
    "cerebras_free": lambda s, m, mt, to, jm=False: _openai_compatible(
        CEREBRAS_URL, env("CEREBRAS_API_KEY"), env("CEREBRAS_MODEL", "llama-3.3-70b"),
        s, m, mt, to, jm),
    "openrouter": lambda s, m, mt, to, jm=False: _openai_compatible(
        OPENROUTER_URL, env("OPENROUTER_API_KEY"),
        env("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"), s, m, mt, to, jm),
    "ollama_local": _ollama,
}


def _order() -> list[str]:
    try:
        primary = str(cfg("llm_provider", "primary"))
        fallback = list(cfg("llm_provider", "fallback_order"))
    except (KeyError, TypeError):
        primary, fallback = "anthropic", []
    order, seen = [], set()
    for name in [primary, *fallback]:
        if name in PROVIDERS and name not in seen:
            seen.add(name)
            order.append(name)
    return order


_OLLAMA_PROBE_LOCK = threading.Lock()
_OLLAMA_PROBE: tuple[bool, float] = (False, 0.0)   # (reachable, expiry)


def _ollama_get(path: str, timeout: float = 2.5) -> dict | None:
    """Tiny proxy-free GET against the local Ollama server. Deliberately NOT
    urllib: with HTTP(S)_PROXY env vars set, urllib routes even localhost
    through the proxy unless NO_PROXY says otherwise, which turns 'is my
    local server up?' into a proxy question. http.client talks to the socket
    directly."""
    parsed = urllib.parse.urlsplit(ollama_host())
    try:
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 11434,
                                          timeout=timeout)
        try:
            conn.request("GET", path, headers={"accept": "application/json"})
            resp = conn.getresponse()
            if resp.status != 200:
                return None
            return json.loads(resp.read())
        finally:
            conn.close()
    except (OSError, json.JSONDecodeError):
        return None


def ollama_tags() -> list[str] | None:
    """Installed model names from the local server ([] = running but nothing
    pulled yet; None = server unreachable). Used by Settings + diagnostics."""
    data = _ollama_get("/api/tags")
    if data is None:
        return None
    return [m.get("name", "?") for m in (data.get("models") or [])]


def _ollama_reachable() -> bool:
    """Ollama needs no key, but that doesn't mean a local server is actually
    running — probe it instead of assuming yes, or available() would report AI
    as usable when every real call is about to fail with a connection error
    (the onboarding gate would never fire). v6.5 — with Ollama as the PRIMARY
    provider this runs on every complete()/available() call, so the result is
    cached briefly (8s up, 3s down) instead of re-probing each time."""
    global _OLLAMA_PROBE
    now = time.time()
    with _OLLAMA_PROBE_LOCK:
        ok, expiry = _OLLAMA_PROBE
        if expiry > now:
            return ok
    ok = _ollama_get("/api/tags", timeout=1.5) is not None
    with _OLLAMA_PROBE_LOCK:
        _OLLAMA_PROBE = (ok, now + (8.0 if ok else 3.0))
    return ok


# provider name -> the env key that makes it usable (Ollama is keyless but
# needs a reachable local server)
_REQUIRED_KEY = {
    "anthropic": "CLAUDE_API_KEY", "anthropic_open_source_grant": "CLAUDE_API_KEY",
    "gemini_free": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "groq_free": "GROQ_API_KEY",
    "cerebras_free": "CEREBRAS_API_KEY", "openrouter": "OPENROUTER_API_KEY",
}


def _usable(name: str) -> bool:
    if name == "ollama_local":
        return _ollama_reachable()
    key = _REQUIRED_KEY.get(name)
    return bool(key and env(key))


def available() -> bool:
    """True when at least one provider is actually usable (has a key, or is
    a reachable local Ollama). Lets callers show honest 'AI unavailable'."""
    return any(_usable(name) for name in _order())


# ---------------------------------------------------------------------------
# v6.4.2 — RATE-LIMIT ETIQUETTE. With the transport fixed, the owner's diag
# table showed the last failure: Groq free-tier "429: Rate limit reached …
# TPM: Limit 12000, Used 11556 … try again in 1.31s". The now-working
# background jobs (causal narratives, translation-on-arrival, agenda
# synthesis) legitimately consume the tokens-per-minute quota, and the
# analyst — the single biggest request — is the one that tips over. Two
# rules fix the contention:
#   1. INTERACTIVE calls (a user is waiting: analyst, on-click deep summary,
#      display translation, the diag page) retry once after Groq's own
#      suggested delay when it's short.
#   2. BACKGROUND calls (scheduler jobs) SKIP instantly during the cooldown
#      window a 429 opens, so they stop burning quota the user needs. Every
#      background caller already handles a None return gracefully.
# ---------------------------------------------------------------------------

_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMITED_UNTIL = 0.0


def _note_rate_limit(seconds: float) -> None:
    global _RATE_LIMITED_UNTIL
    with _RATE_LIMIT_LOCK:
        _RATE_LIMITED_UNTIL = max(_RATE_LIMITED_UNTIL, time.time() + seconds)


def rate_limited_for() -> float:
    """Seconds of rate-limit cooldown remaining (0 when clear)."""
    with _RATE_LIMIT_LOCK:
        return max(0.0, _RATE_LIMITED_UNTIL - time.time())


def _parse_retry_delay(detail: str, headers) -> float:
    """Best-effort retry hint: Retry-After header, else Groq's own
    'Please try again in 1.31s' message text, else a conservative 15s."""
    try:
        ra = headers.get("retry-after") if headers else None
        if ra:
            return min(float(ra), 60.0)
    except (TypeError, ValueError):
        pass
    m = re.search(r"try again in ([0-9.]+)\s*s", detail)
    if m:
        try:
            return min(float(m.group(1)), 60.0)
        except ValueError:
            pass
    return 15.0


# v6.3.1 — last provider error, so callers (the analyst) can tell the user WHY
# a call failed (bad key vs decommissioned model vs timeout) instead of hiding
# every failure behind a generic "add a key" fallback.
_LAST_ERROR: str | None = None


def last_error() -> str | None:
    return _LAST_ERROR


def _error_detail(exc) -> str:
    """Extract the provider's real error message from an HTTPError body when
    possible (Groq/OpenAI-style {"error":{"message":...}}), else the exception
    text — so 'model decommissioned' or 'invalid api key' actually surfaces."""
    try:
        if isinstance(exc, urllib.error.HTTPError):
            raw = exc.read().decode("utf-8", "replace")
            try:
                body = json.loads(raw)
                msg = (body.get("error") or {}).get("message") if isinstance(
                    body.get("error"), dict) else body.get("error")
                return f"HTTP {exc.code}: {msg or raw[:200]}"
            except json.JSONDecodeError:
                return f"HTTP {exc.code}: {raw[:200]}"
    except Exception:  # noqa: BLE001
        pass
    return str(exc)[:200]


def complete(system: str | None, messages: list[dict], max_tokens: int = 900,
             timeout: int = 60, prefer: str | None = None,
             json_mode: bool = False, interactive: bool = False) -> str | None:
    """Try providers in configured order; return the first non-empty text, or
    None if every provider is unconfigured/unreachable. Never raises.

    v6 §1 — `prefer` names a provider to try FIRST for this one call site
    (llm_provider.causal_link_override keeps causal narratives independently
    configurable); when the preferred provider isn't usable it silently falls
    through to the normal order, never blocks.

    v6.3.1 — `json_mode` forces strict-JSON output on providers that support it
    (Groq/OpenAI/Gemini/Ollama). On failure the real provider error is captured
    in module state (last_error()).

    v6.4.2 — `interactive=True` means a user is waiting on this call: it may
    briefly sleep out a short rate-limit window and retries once after a 429's
    suggested delay. Background calls (the default) return None IMMEDIATELY
    during a cooldown so scheduler jobs stop competing with the user for the
    free tier's tokens-per-minute quota."""
    global _LAST_ERROR
    _LAST_ERROR = None
    cooldown = rate_limited_for()
    if cooldown > 0:
        if not interactive:
            _LAST_ERROR = (f"rate-limit cooldown ({cooldown:.0f}s left) — "
                           "background call skipped to leave quota for the user")
            return None
        if cooldown <= 8:
            time.sleep(cooldown + 0.25)
    order = _order()
    if prefer and prefer in PROVIDERS and _usable(prefer):
        order = [prefer] + [n for n in order if n != prefer]
    tried_any = False
    for name in order:
        if not _usable(name):
            continue   # skip unconfigured providers fast (no wasted timeout)
        tried_any = True
        fn = PROVIDERS[name]
        for attempt in (0, 1):
            try:
                out = fn(system, messages, max_tokens, timeout, json_mode)
            except (urllib.error.URLError, OSError, KeyError, ValueError,
                    json.JSONDecodeError) as exc:
                detail = _error_detail(exc)
                _LAST_ERROR = f"{name}: {detail}"
                if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                    delay = _parse_retry_delay(detail, getattr(exc, "headers", None))
                    _note_rate_limit(delay)
                    # a user-facing call waits out a SHORT window once —
                    # Groq's TPM hints are typically a second or two
                    if interactive and attempt == 0 and delay <= 8:
                        log.info("llm_rate_limit_retry", extra={"data": {
                            "provider": name, "delay_s": delay}})
                        time.sleep(delay + 0.25)
                        continue
                log.warning("llm_provider_failed", extra={"data": {
                    "provider": name, "error": detail}})
                break   # give up on this provider, fall through to the next
            if out:
                log.info("llm_provider_used", extra={"data": {"provider": name}})
                return out
            _LAST_ERROR = f"{name}: empty response"
            break
    if not tried_any:
        _LAST_ERROR = "no AI provider configured (add a key, e.g. Groq, in Settings)"
    return None
