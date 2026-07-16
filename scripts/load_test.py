#!/usr/bin/env python3
"""v8.17 — a synthetic load harness for the read API (owner-run).

Every latency fix in this project's history — the analyst timeout, the
translation flood, the SQLite lock contention, the source-health-page timeout —
was found REACTIVELY from an owner bug report, never caught ahead of time. This
harness fires concurrent requests at the hot read endpoints and reports latency
percentiles + error rate, so the NEXT such regression shows up as a p95 spike
here before it ships.

Pure stdlib (urllib + threads), no install. Run it against a live server:

    python run.py                       # in one terminal
    python scripts/load_test.py         # in another

    python scripts/load_test.py --base http://127.0.0.1:8000 \
        --concurrency 16 --requests 400

It only issues GETs to read endpoints, so it never mutates state.
"""
import argparse
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict

# The read endpoints the frontend actually hammers on boot + live updates.
ENDPOINTS = [
    "/api/config",
    "/api/stories?limit=60",
    "/api/map/events",
    "/api/instability?range=72h",
    "/api/conflicts",
    "/api/mapmodes",
    "/api/sources/status",
    "/api/military",
    "/api/trade",
    "/api/predmarkets",
]


def _percentile(values, pct):
    if not values:
        return None
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((pct / 100.0) * (len(values) - 1)))))
    return values[k]


def worker(base, paths, n, lat, errs, lock, stop_at):
    i = 0
    while True:
        if n is not None and i >= n:
            return
        if stop_at is not None and time.monotonic() >= stop_at:
            return
        path = paths[i % len(paths)]
        i += 1
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(base + path, timeout=30) as r:
                r.read()
                ms = (time.monotonic() - t0) * 1000.0
                with lock:
                    lat[path].append(ms)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            with lock:
                errs[path].append(str(exc)[:80])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--requests", type=int, default=200,
                    help="total requests across all workers (ignored if --duration set)")
    ap.add_argument("--duration", type=float, default=None,
                    help="run for N seconds instead of a fixed request count")
    args = ap.parse_args()

    lat = defaultdict(list)
    errs = defaultdict(list)
    lock = threading.Lock()
    per_worker = None if args.duration else max(1, args.requests // args.concurrency)
    stop_at = (time.monotonic() + args.duration) if args.duration else None

    print(f"load test → {args.base}  concurrency={args.concurrency}  "
          + (f"duration={args.duration}s" if args.duration
             else f"requests≈{per_worker * args.concurrency}"))
    t0 = time.monotonic()
    threads = [threading.Thread(
        target=worker, args=(args.base, ENDPOINTS, per_worker, lat, errs, lock, stop_at))
        for _ in range(args.concurrency)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.monotonic() - t0

    total_ok = sum(len(v) for v in lat.values())
    total_err = sum(len(v) for v in errs.values())
    print(f"\ndone in {wall:.1f}s — {total_ok} ok, {total_err} errors, "
          f"{total_ok / wall:.0f} req/s\n")
    print(f"{'endpoint':<32} {'n':>5} {'p50':>8} {'p95':>8} {'p99':>8} {'max':>8} {'err':>5}")
    print("-" * 80)
    worst_p95 = 0.0
    for path in ENDPOINTS:
        v = lat.get(path, [])
        e = len(errs.get(path, []))
        if not v and not e:
            continue
        p50 = _percentile(v, 50) or 0
        p95 = _percentile(v, 95) or 0
        p99 = _percentile(v, 99) or 0
        mx = max(v) if v else 0
        worst_p95 = max(worst_p95, p95)
        print(f"{path:<32} {len(v):>5} {p50:>7.0f}m {p95:>7.0f}m {p99:>7.0f}m {mx:>7.0f}m {e:>5}")

    # a crude regression gate: p95 over 2s on any read endpoint, or any errors
    # against a reachable server, is worth investigating.
    bad = worst_p95 > 2000 or total_err > 0
    if total_err:
        print(f"\n⚠ {total_err} request errors — is the server up at {args.base}?")
    if worst_p95 > 2000:
        print(f"\n⚠ worst p95 = {worst_p95:.0f}ms (> 2000ms) — investigate that endpoint.")
    if not bad:
        print(f"\nOK — worst p95 {worst_p95:.0f}ms, 0 errors.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
