"""v2 addendum §7.2 — per-source daily request budgeting.

Counters live in app_meta keyed by UTC date, so they reset naturally at
UTC midnight and survive restarts. Sources with a configured budget call
spend() before each outbound request; when the budget is exhausted the
fetch is skipped for the rest of the UTC day (BudgetExhausted), which the
scheduler treats as a quiet no-op rather than a failure.
"""

import json
from datetime import datetime, timezone

from ..config import CONFIG
from ..db.models import meta_get, meta_set


class BudgetExhausted(Exception):
    pass


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def budget_for(name: str) -> int | None:
    budgets = CONFIG.get("ops", {}).get("daily_request_budgets", {})
    value = budgets.get(name)
    return int(value) if value is not None else None


def spent_today(name: str) -> int:
    raw = meta_get(f"budget:{name}") or "{}"
    state = json.loads(raw)
    return state.get(_today(), 0)


def spend(name: str, n: int = 1) -> None:
    """Consume n requests from today's budget; raises BudgetExhausted when
    the configured daily budget would be exceeded. Unbudgeted sources pass
    through freely."""
    limit = budget_for(name)
    if limit is None:
        return
    today = _today()
    used = spent_today(name)
    if used + n > limit:
        raise BudgetExhausted(f"{name}: daily budget {limit} exhausted")
    meta_set(f"budget:{name}", json.dumps({today: used + n}))
