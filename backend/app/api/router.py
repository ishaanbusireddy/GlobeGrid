"""Tiny route registry shared by the route modules (stdlib adaptation of
FastAPI routing). Patterns use {name} path params; handlers receive
(params, query, body) and return (status_code, json_serializable)."""

import re

_ROUTES: list[tuple[str, re.Pattern, callable]] = []


def route(method: str, pattern: str):
    regex = re.compile(
        "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$")

    def decorator(fn):
        _ROUTES.append((method.upper(), regex, fn))
        return fn
    return decorator


def dispatch(method: str, path: str, query: dict, body):
    for m, regex, fn in _ROUTES:
        if m != method.upper():
            continue
        match = regex.match(path)
        if match:
            return fn(match.groupdict(), query, body)
    return 404, {"error": f"no route for {method} {path}"}
