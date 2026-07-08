"""Scheduling + failure isolation (v1 Sections 2.3, 5.10, 10.2; v2 §2, §7).

Zero-install adaptation: APScheduler is replaced by daemon threads from
the standard library — one loop per source plus pipeline, instability,
and the v2 jobs (prediction resolution, daily briefing, second-order
scan, nightly DB backup). Behavior matches the manuals' policy exactly:

  - each ingestion job wrapped in its own try/except; a failure updates
    that source's health_status/last_error and never propagates;
  - exponential backoff on repeated failure up to
    resilience.max_backoff_seconds, reset on the next success;
  - every health update also appends a source_uptime_history row (§7.1);
  - a dead source is surfaced via /api/sources/status, never silently
    dropped, and never blocks other sources or the serving layer;
  - v2 §2: event_created is broadcast the instant extraction lands,
    BEFORE correlation — pins appear on the map immediately and are
    upgraded when story_created/story_updated follows.
"""

import json
import logging
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from ..config import cfg, sqlite_path, REPO_ROOT
from ..db.models import new_id, now_iso
from ..db.session import query, write_tx
from ..logging_setup import job_log
from ..processing import briefing, causal_link, extract, instability, predictions, second_order
from ..processing.correlate import correlate_new_events
from ..websocket.feed_socket import hub
from .budget import BudgetExhausted
from .http import SourceNotConfigured
from .sources import (acled, ais, bluesky, firms, market,
                      mastodon, nightlights, opensky, reddit, rss, usgs, wiki)

log = logging.getLogger("scheduler")

# v6 §2 — GDELT (Events + Cloud) removed entirely: fetchers deleted, source
# rows retired via is_active=0 (historical fact-chain rows keep attribution)
# v7.4 — HARD BLOCK on GDELT ingestion (owner: "add an internal blocker/note
# against ingesting GDELT news sources, they are horribly mass produced and low
# quality"). Any source whose type or url/name smells of GDELT is refused a
# polling thread AND skipped in the fetch path, so it can never be reintroduced
# accidentally by a seed edit or a manually-added source row.
GDELT_BLOCKED = ("gdelt", "gdelt_events")


def _is_gdelt(name: str, stype: str, url: str = "") -> bool:
    s = f"{name} {stype} {url}".lower()
    return stype in GDELT_BLOCKED or "gdelt" in s
FETCHERS = {
    "rss": rss.fetch,
    "usgs": usgs.fetch, "market": market.fetch, "reddit": reddit.fetch,
    "firms": firms.fetch, "volcano": rss.fetch, "wikipedia": wiki.fetch,
    "wiki_views": wiki.fetch, "mastodon": mastodon.fetch, "bluesky": bluesky.fetch,
    "opensky": opensky.fetch, "acled": acled.fetch,
    "ais": ais.fetch, "nightlights": nightlights.fetch,
}

PIPELINE_TICK_SECONDS = 20

stop_event = threading.Event()


def _translate_recent() -> int:
    """v6.6.8 — display translation is now on-demand (the site-wide DOM
    translator), NOT a background arrival job. This is a no-op kept only so the
    job registry entry stays valid; ingestion-time English normalization for
    correlation still lives in extract.py."""
    return 0


def _assign_threads() -> int:
    """v6 §27 — deferred import, same pattern."""
    from ..processing.threads import assign_threads
    return assign_threads()


def _accuracy_refresh() -> int:
    """v6 §30 — deferred import, same pattern."""
    from ..processing.accuracy import refresh_stale_leadership
    return refresh_stale_leadership()


def _store_items(source_id: str, items: list[dict]) -> int:
    stored = 0
    with write_tx() as conn:
        for item in items:
            cur = conn.execute(
                "INSERT OR IGNORE INTO raw_items (id, source_id, raw_content, fetched_at,"
                " external_id) VALUES (?,?,?,?,?)",
                (new_id(), source_id, json.dumps(item), now_iso(),
                 str(item.get("external_id") or item.get("link") or item.get("title"))))
            stored += cur.rowcount
    return stored


def _set_health(source_id: str, status: str, error: str | None, fetched: bool) -> None:
    with write_tx() as conn:
        if fetched:
            conn.execute(
                "UPDATE sources SET health_status = ?, last_error = ?, last_fetched_at = ?"
                " WHERE id = ?", (status, error, now_iso(), source_id))
        else:
            conn.execute("UPDATE sources SET health_status = ?, last_error = ? WHERE id = ?",
                         (status, error, source_id))
        # v2 §7.1 — every health tick appends to the uptime history
        conn.execute("INSERT INTO source_uptime_history (id, source_id, checked_at, status)"
                     " VALUES (?,?,?,?)", (new_id(), source_id, now_iso(), status))


def _source_loop(source_id: str) -> None:
    """One independent ingestion loop per source (Section 2.3)."""
    consecutive_failures = 0
    while not stop_event.is_set():
        row = query("SELECT * FROM sources WHERE id = ?", (source_id,))
        if not row:
            return
        source = dict(row[0])
        base_interval = max(30, source["poll_interval_seconds"] or 300)
        # v4 §13.1 — dynamic polling: high recent conflict activity tightens
        # the cadence for broad-scope sources (config-gated)
        try:
            from ..geopolitics.sync import dynamic_poll_factor
            base_interval = max(30, base_interval * dynamic_poll_factor(source["type"]))
        except Exception:  # noqa: BLE001 — never let tuning break ingestion
            pass
        interval = base_interval
        start = time.monotonic()
        try:
            items = FETCHERS[source["type"]](source)
            stored = _store_items(source_id, items)
            _set_health(source_id, "ok", None, fetched=True)
            consecutive_failures = 0
            job_log(log, source_id=source["name"], status="ok", item_count=stored,
                    duration_ms=int((time.monotonic() - start) * 1000))
        except SourceNotConfigured as exc:
            _set_health(source_id, "degraded", str(exc), fetched=False)
            job_log(log, source_id=source["name"], status="degraded", item_count=0,
                    duration_ms=int((time.monotonic() - start) * 1000), error=str(exc))
            interval = float(cfg("resilience", "max_backoff_seconds"))
        except BudgetExhausted as exc:
            # §7.2 — budget spent is deliberate, not a failure: stay healthy,
            # wait out the UTC day quietly.
            _set_health(source_id, "ok", str(exc), fetched=False)
            job_log(log, source_id=source["name"], status="budget_exhausted",
                    item_count=0, duration_ms=int((time.monotonic() - start) * 1000),
                    error=str(exc))
            interval = float(cfg("resilience", "max_backoff_seconds"))
        except Exception as exc:  # noqa: BLE001 — isolation boundary
            consecutive_failures += 1
            multiplier = float(cfg("resilience", "backoff_multiplier"))
            max_backoff = float(cfg("resilience", "max_backoff_seconds"))
            interval = min(base_interval * (multiplier ** consecutive_failures), max_backoff)
            status = "degraded" if consecutive_failures < 3 else "down"
            _set_health(source_id, status, str(exc)[:500], fetched=False)
            job_log(log, source_id=source["name"], status=status, item_count=0,
                    duration_ms=int((time.monotonic() - start) * 1000), error=str(exc))
        stop_event.wait(interval)


def _pipeline_loop() -> None:
    """Stages 2-5 driver. Each stage isolated; one bad batch never kills it."""
    while not stop_event.is_set():
        try:
            new_events = extract.process_pending()
            # v2 §2 — push pins the moment extraction lands, before correlation
            for ev in new_events:
                hub.broadcast("event_created", ev["ws_payload"])
            if new_events:
                results = correlate_new_events([e["event_id"] for e in new_events])
                for res in results:
                    story = query("SELECT * FROM stories WHERE id = ?", (res["story_id"],))
                    if story:
                        payload = {k: story[0][k] for k in
                                   ("id", "headline", "summary", "confidence",
                                    "first_seen_at", "last_updated_at")}
                        hub.broadcast("story_created" if res["created"] else "story_updated",
                                      payload)
            causal_link.refresh_pending()
            # v6.6.6 — LLM geoplacement correction: nudge a few low-confidence /
            # mis-placed events (the "everything lands in India" bug) to their
            # real coordinates and move the live pins. Self-limiting (flags each
            # event once) and a no-op with no provider, so it never spins.
            from ..processing import geoplace
            for mv in geoplace.correct_recent():
                hub.broadcast("event_relocated", mv)
            # v7 §5 — text + physical signal agreeing: re-score recent
            # conflict-zone stories against sensor-sourced events
            from ..processing import corroborate
            for ch in corroborate.score_recent():
                hub.broadcast("story_corroborated", ch)
        except Exception:  # noqa: BLE001
            log.exception("pipeline_tick_failed")
        stop_event.wait(PIPELINE_TICK_SECONDS)


def _instability_loop() -> None:
    while not stop_event.is_set():
        try:
            result = instability.compute_score()
            hub.broadcast("instability_updated", result)
            # v3 §6 — flag anomalies on the fresh reading (marker, never action)
            from ..processing import anomaly
            for flag in anomaly.check_latest():
                hub.broadcast("anomaly_flagged", flag)
        except Exception:  # noqa: BLE001
            log.exception("instability_tick_failed")
        stop_event.wait(float(cfg("instability", "recompute_interval_seconds")))


def _predictions_loop() -> None:
    """v2 §3.4 — periodic batched grading of pending predictions."""
    while not stop_event.is_set():
        try:
            predictions.resolve_pending()
        except Exception:  # noqa: BLE001
            log.exception("predictions_tick_failed")
        stop_event.wait(float(cfg("predictions", "resolve_interval_seconds")))


def _daily_loop() -> None:
    """v2 §6.1 briefing + §7.4 DB backup, each at its configured UTC hour."""
    done: dict[str, str] = {}
    while not stop_event.is_set():
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        try:
            if now.hour >= int(cfg("briefing", "daily_briefing_hour_utc")) and \
                    done.get("briefing") != today:
                briefing.generate_briefing(today)
                done["briefing"] = today
            if now.hour >= int(cfg("ops", "db_backup")["backup_hour_utc"]) and \
                    done.get("backup") != today:
                _backup_database()
                done["backup"] = today
            # v7 §4 — nightly Brier backtest keeps the accuracy scorecards
            # (and the per-category forecast gate) current as history grows
            if done.get("backtest") != today:
                from ..processing import backtest
                backtest.run_backtest()
                done["backtest"] = today
        except Exception:  # noqa: BLE001
            log.exception("daily_tick_failed")
        stop_event.wait(600)


def _backup_database() -> None:
    """v2 §7.4 — nightly copy of the SQLite file, keep last N."""
    backup_cfg = cfg("ops", "db_backup")
    backup_dir = Path(backup_cfg["backup_dir"])
    if not backup_dir.is_absolute():
        backup_dir = REPO_ROOT / backup_cfg["backup_dir"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    src = sqlite_path()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"talkdiplomacy_live-{stamp}.db"
    import sqlite3
    with sqlite3.connect(str(src)) as live, sqlite3.connect(str(dest)) as copy:
        live.backup(copy)   # consistent even mid-write, unlike file copy
    backups = sorted(backup_dir.glob("talkdiplomacy_live-*.db"))
    for old in backups[:-int(backup_cfg["keep_last_n"])]:
        old.unlink(missing_ok=True)
    log.info("db_backup", extra={"data": {"dest": str(dest), "kept": min(
        len(backups), int(backup_cfg["keep_last_n"]))}})


def _v3_jobs_loop() -> None:
    """v3 periodic jobs on persisted due-times (one thread, not seven):
    self-tuning (§5), Wikidata leadership (§13.2/weekly), World Bank trade
    (monthly), agenda + bilateral synthesis, conflict tag suggestions
    (§15.1), election-triggered refreshes (§23.1), TLE fetch (§10.2), and
    the forecast pass (§7 — no-op while forecasting.enabled is false)."""
    import json as _json
    from ..db.models import meta_get, meta_set
    from ..geopolitics import sync as geo_sync, synthesis as geo_synth
    from ..processing import forecast, self_tuning

    def due(name: str, interval_hours: float) -> bool:
        state = _json.loads(meta_get("v3_jobs") or "{}")
        last = state.get(name, 0)
        return time.time() - last >= interval_hours * 3600

    def mark(name: str) -> None:
        state = _json.loads(meta_get("v3_jobs") or "{}")
        state[name] = time.time()
        meta_set("v3_jobs", _json.dumps(state))

    jobs = [
        ("self_tuning", lambda: float(cfg("self_tuning", "aggregation_interval_hours")),
         self_tuning.aggregate_and_adjust),
        ("wikidata", lambda: float(cfg("geopolitical_entities",
                                       "wikidata_refresh_interval_hours")),
         geo_sync.refresh_leadership),
        ("trade", lambda: float(cfg("geopolitical_entities",
                                    "trade_stats_refresh_interval_hours")),
         geo_sync.refresh_trade_stats),
        ("agendas", lambda: float(cfg("geopolitical_entities",
                                      "agenda_synthesis_interval_hours")),
         geo_synth.synthesize_country_agendas),
        ("bilateral", lambda: float(cfg("geopolitical_entities",
                                        "bilateral_relations_refresh_interval_hours")),
         geo_synth.synthesize_bilateral_relations),
        ("conflict_tags", lambda: 2.0, geo_sync.suggest_conflict_tags),
        ("elections", lambda: 6.0, geo_sync.election_triggered_refreshes),
        ("tles", lambda: float(cfg("satellite_overlay", "tle_refresh_interval_hours")),
         geo_sync.refresh_tles),
        ("forecast", lambda: 6.0, forecast.generate_for_recent_stories),
        # --- v4 jobs ---
        ("country_completeness", lambda: float(cfg(
            "geopolitical_entities", "wikidata_refresh_interval_hours")),
         geo_sync.sync_countries_from_wikidata),          # §5.1
        ("alliance_rosters", lambda: float(cfg(
            "geopolitical_entities", "wikidata_refresh_interval_hours")),
         geo_sync.sync_alliance_memberships),             # §5.1
        ("background_content", lambda: 6.0,               # §7 (batched; each
         geo_sync.refresh_background_content),            # cycle does a few)
        # v6 §2 — GDELT historical_backfill job removed with GDELT itself
        # v6 §11 — translate new stories into every active UI language on
        # arrival (cache-first; a no-op when no language beyond en is active)
        ("translate_arrivals", lambda: 0.1, _translate_recent),
        # v6 §27 — macro-trend thread grouping over new stories
        ("story_threads", lambda: 0.25, _assign_threads),
        # v6 §30 — live-search verification of the most-stale leadership rows,
        # ahead of (and independent of) the weekly Wikidata sync
        ("accuracy_refresh", lambda: 1.0, _accuracy_refresh),
        ("prognosis", lambda: float(cfg("prognosis", "refresh_interval_hours")),
         forecast.generate_prognoses),                    # §10
        # --- v5 jobs ---
        ("flags", lambda: float(cfg(                      # §7 — cache flag SVGs
            "geopolitical_entities", "wikidata_refresh_interval_hours")),
         geo_sync.refresh_flags),
    ]
    stop_event.wait(90)  # let ingestion warm up first
    while not stop_event.is_set():
        for name, interval_fn, fn in jobs:
            if stop_event.is_set():
                return
            try:
                if due(name, interval_fn()):
                    fn()
                    mark(name)
            except Exception as exc:  # noqa: BLE001 — per-job isolation; a
                # blocked network (or missing key) just retries next cycle
                log.warning("v3_job_failed", extra={"data": {"job": name,
                                                             "error": str(exc)[:200]}})
                mark(name)
        stop_event.wait(600)


def _second_order_loop() -> None:
    """v2 §3.7 — periodic shared-root-cause scan across cluster pairs."""
    while not stop_event.is_set():
        stop_event.wait(float(cfg("second_order", "scan_interval_seconds")))
        if stop_event.is_set():
            return
        try:
            second_order.scan_once()
        except Exception:  # noqa: BLE001
            log.exception("second_order_tick_failed")


def _backfill_loop() -> None:
    """v7 Part 6 / v7.4 — historical backfill: seed the curated + deep event
    packs once. The GDELT archive walk is GONE (owner: "Scrap all GDELT news
    sources … they are horribly mass produced and low quality"); only the
    hand-curated, correctly-dated history packs seed the chain now."""
    from . import backfill
    try:
        backfill.seed_curated_history()
    except Exception:  # noqa: BLE001
        log.exception("curated_history_seed_failed")
    try:
        backfill.seed_deep_history()   # v7.2 — 1945→present deep pack
    except Exception:  # noqa: BLE001
        log.exception("deep_history_seed_failed")
    # v7.4 — GDELT archive backfill deliberately not run (see GDELT_BLOCKED).
    # v7.4 — one-time pass: auto-classify already-ingested untagged stories into
    # their conflicts so War Mode / conflict tabs fill immediately.
    try:
        from ..processing.correlate import reclassify_untagged_conflicts
        n = reclassify_untagged_conflicts()
        log.info("conflict_reclassify_backfill", extra={"data": {"stories": n}})
    except Exception:  # noqa: BLE001
        log.exception("conflict_reclassify_failed")


def start_all() -> list[threading.Thread]:
    threads = []
    # v6.6.6 — ensure the llm_geoplaced flag column exists (additive migration)
    try:
        from ..processing import geoplace
        geoplace.ensure_column()
    except Exception:  # noqa: BLE001
        log.exception("geoplace_column_init_failed")
    try:   # v7 §5 — corroboration columns (additive migration)
        from ..processing import corroborate
        corroborate.ensure_columns()
    except Exception:  # noqa: BLE001
        log.exception("corroborate_column_init_failed")
    # v6 §2 — retired sources (is_active=0) and types with no registered
    # fetcher never get a polling thread
    for row in query("SELECT id, name, type, url FROM sources WHERE type != 'synthetic'"
                     " AND is_active = 1"):
        if row["type"] not in FETCHERS:
            continue
        if _is_gdelt(row["name"], row["type"], row["url"]):   # v7.4 hard block
            log.info("gdelt_source_blocked", extra={"data": {"name": row["name"]}})
            continue
        t = threading.Thread(target=_source_loop, args=(row["id"],),
                             name=f"ingest-{row['name']}", daemon=True)
        t.start()
        threads.append(t)
    for target, name in ((_pipeline_loop, "pipeline"), (_instability_loop, "instability"),
                         (_predictions_loop, "predictions"), (_daily_loop, "daily"),
                         (_second_order_loop, "second_order"), (_v3_jobs_loop, "v3_jobs"),
                         (_backfill_loop, "backfill")):
        t = threading.Thread(target=target, name=name, daemon=True)
        t.start()
        threads.append(t)
    log.info("scheduler_started", extra={"data": {"threads": len(threads)}})
    return threads
