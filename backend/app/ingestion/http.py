"""Shared stdlib HTTP helper for ingestion adapters."""

import json
import ssl
import urllib.request

DEFAULT_UA = "TalkDiplomacyLive/1.0 (single-user local build; +https://github.com/ishaanbusireddy/GlobeGrid)"


class SourceNotConfigured(Exception):
    """Raised when a source needs an API key that isn't set — the scheduler
    marks the source degraded instead of down and skips the fetch."""


def fetch_url(url: str, *, headers: dict | None = None, data: bytes | None = None,
              timeout: int = 30) -> bytes:
    req_headers = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, data=data)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read()


def fetch_json(url: str, **kwargs):
    body = fetch_url(url, **kwargs)
    return json.loads(body)
