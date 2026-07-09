"""v7 Part 6 — historical news backfill (curated only, v7.4.1).

A CURATED pack of major world events (1945 → early 2026, dates and facts from
the historical record) is seeded once at startup — works fully offline,
attributed to the "Historical Archive (curated)" source (type 'archive') and
dated in the past so it sorts below fresh news in the feed.

The old LIVE GDELT 2.0 archive walk that used to also live here is DELETED and
GDELT is permanently banned (see purge_gdelt below). The curated packs emit the
standard raw_items envelope, so the normal extraction → facts → correlation
pipeline (provenance included) does the rest.
"""

import json

from ..db.models import meta_get, meta_set, new_id, now_iso
from ..db.session import query, query_one, write_tx
import logging

log = logging.getLogger("backfill")

ARCHIVE_SOURCE_NAME = "Historical Archive (curated)"

# (date, title, summary, category, lat, lon, location_name, severity)
HISTORICAL_EVENTS = [
    ("2024-07-13", "Assassination attempt on Donald Trump at Butler rally",
     "A gunman wounded the former president at a Pennsylvania campaign rally; the attack reshaped the 2024 US race.", "geopolitics", 40.86, -79.90, "Butler", 4),
    ("2024-08-06", "Ukraine launches surprise incursion into Russia's Kursk region",
     "Ukrainian brigades seized hundreds of square kilometers inside Russia — the first foreign occupation of Russian soil since WWII.", "conflict", 51.42, 34.99, "Sudzha", 4),
    ("2024-08-05", "Sheikh Hasina flees Bangladesh after student uprising",
     "Mass protests toppled the 15-year PM; Nobel laureate Muhammad Yunus took over an interim government.", "geopolitics", 23.81, 90.41, "Dhaka", 4),
    ("2024-09-17", "Pager attack maims Hezbollah operatives across Lebanon",
     "Thousands of booby-trapped pagers and radios detonated in a covert Israeli operation decapitating Hezbollah communications.", "conflict", 33.89, 35.50, "Beirut", 4),
    ("2024-09-27", "Israel kills Hezbollah leader Hassan Nasrallah in Beirut strike",
     "Massive bunker-buster strikes on Dahiyeh killed the group's secretary-general of 32 years, gutting its command.", "conflict", 33.85, 35.50, "Beirut", 5),
    ("2024-10-01", "Iran fires ~180 ballistic missiles at Israel",
     "Tehran's second-ever direct attack on Israel, answered weeks later by Israeli strikes on Iranian air defenses.", "conflict", 32.08, 34.78, "Tel Aviv", 5),
    ("2024-10-17", "Israel kills Hamas leader Yahya Sinwar in Rafah",
     "The October 7 architect died in a chance firefight, removing Hamas's top decision-maker in Gaza.", "conflict", 31.29, 34.25, "Rafah", 4),
    ("2024-11-05", "Donald Trump wins 2024 US presidential election",
     "Trump defeated Kamala Harris, sweeping swing states; Republicans took the Senate and held the House.", "geopolitics", 38.90, -77.04, "Washington", 5),
    ("2024-11-27", "Israel-Hezbollah ceasefire takes effect in Lebanon",
     "A US/French-brokered 60-day truce ended 14 months of war; Israeli forces later kept five border positions.", "diplomacy", 33.27, 35.20, "South Lebanon", 4),
    ("2024-12-03", "South Korean President Yoon declares martial law, reversed in hours",
     "Parliament defied troops to vote the decree down; Yoon was impeached and later removed, triggering 2025 elections.", "geopolitics", 37.53, 126.98, "Seoul", 4),
    ("2024-12-08", "Assad regime falls as HTS-led rebels take Damascus",
     "Bashar al-Assad fled to Moscow after a 11-day offensive; Ahmed al-Sharaa's coalition ended 53 years of Assad rule.", "conflict", 33.51, 36.29, "Damascus", 5),
    ("2025-01-19", "Gaza ceasefire and hostage-release deal takes effect",
     "A phased Israel-Hamas deal brokered by Qatar/Egypt/US began exchanging hostages for prisoners after 15 months of war.", "diplomacy", 31.50, 34.47, "Gaza", 5),
    ("2025-01-20", "Trump inaugurated; signs blitz of executive orders",
     "The 47th president withdrew from the Paris accord and WHO, declared a border emergency, and launched a tariff agenda.", "geopolitics", 38.90, -77.04, "Washington", 4),
    ("2025-01-27", "DeepSeek R1 shock wipes $1T off tech stocks",
     "A Chinese lab's cheap frontier model triggered the biggest single-stock loss in history (Nvidia -$589B) and an AI rethink.", "technology", 22.54, 114.06, "Hangzhou", 4),
    ("2025-01-27", "M23 rebels capture Goma in eastern DR Congo",
     "The Rwanda-backed group seized the region's largest city; Bukavu followed in February.", "conflict", -1.68, 29.22, "Goma", 4),
    ("2025-02-28", "Trump-Zelensky Oval Office meeting collapses on camera",
     "A public clash over 'gratitude' and security guarantees briefly froze US aid and intelligence sharing to Ukraine.", "geopolitics", 38.90, -77.04, "Washington", 4),
    ("2025-03-08", "Sectarian massacres hit Syria's Alawite coast",
     "Over a thousand mostly-Alawite civilians were killed in reprisal violence — the transition's darkest episode.", "conflict", 35.52, 35.79, "Latakia", 4),
    ("2025-03-19", "Istanbul mayor İmamoğlu arrested; mass protests erupt",
     "The jailing of Erdoğan's chief rival ignited Turkey's largest demonstrations in a decade.", "geopolitics", 41.01, 28.98, "Istanbul", 3),
    ("2025-03-28", "M7.7 earthquake devastates central Myanmar",
     "The Sagaing-fault quake killed thousands in Mandalay and Naypyidaw amid the civil war, collapsing a Bangkok tower.", "disaster", 21.98, 96.08, "Mandalay", 5),
    ("2025-04-02", "Trump's 'Liberation Day': sweeping global tariffs announced",
     "Baseline 10% tariffs plus steep 'reciprocal' rates triggered a market plunge and a cascade of retaliations and deals.", "finance", 38.90, -77.04, "Washington", 5),
    ("2025-04-22", "Pahalgam attack: gunmen massacre 26 tourists in Kashmir",
     "The killings, blamed by India on Pakistan-linked militants, lit the fuse for May's four-day war.", "conflict", 34.02, 75.32, "Pahalgam", 4),
    ("2025-05-07", "India strikes Pakistan: Operation Sindoor begins four-day war",
     "Missile, drone and air battles deep into both countries — the worst India-Pakistan fighting in decades — ended in a May 10 ceasefire.", "conflict", 31.55, 74.34, "Lahore", 5),
    ("2025-05-08", "Cardinal Robert Prevost elected Pope Leo XIV",
     "The first American pope succeeded Francis, who died April 21.", "geopolitics", 41.90, 12.45, "Vatican City", 3),
    ("2025-06-13", "Israel launches Operation Rising Lion against Iran",
     "Strikes killed IRGC commanders and nuclear scientists and opened a 12-day war; Iran answered with missile barrages.", "conflict", 35.69, 51.39, "Tehran", 5),
    ("2025-06-22", "US B-2s strike Fordow, Natanz and Isfahan nuclear sites",
     "Operation Midnight Hammer brought Washington directly into the Israel-Iran war; a ceasefire followed on June 24.", "conflict", 34.95, 51.75, "Fordow", 5),
    ("2025-06-25", "NATO summit pledges 5% GDP defense/security spending",
     "The Hague summit adopted the historic target under US pressure — the alliance's biggest burden-sharing shift ever.", "diplomacy", 52.08, 4.31, "The Hague", 4),
    ("2025-07-04", "Texas Hill Country flash floods kill over 130",
     "The Guadalupe River disaster, including a girls' summer camp, became the deadliest US freshwater flood in decades.", "disaster", 30.05, -99.14, "Kerrville", 4),
    ("2025-05-16", "Moody's strips the US of its last triple-A rating",
     "The downgrade cited debt trajectory and interest costs — a milestone for global bond markets.", "finance", 40.71, -74.01, "New York", 3),
    ("2025-07-01", "OPEC+ accelerates output hikes to defend market share",
     "Saudi-led producers unwound voluntary cuts faster than expected, pressuring prices amid tariff-clouded demand.", "finance", 24.71, 46.68, "Riyadh", 3),
    ("2025-02-24", "Third anniversary: Ukraine war grinds into attrition",
     "Drone-dominated positional warfare along a ~1,000 km front; Russian gains slow and costly around Pokrovsk and Kupiansk.", "conflict", 48.28, 37.18, "Pokrovsk", 4),
    ("2025-08-08", "Armenia and Azerbaijan sign Washington peace framework",
     "White House-brokered declaration advanced normalization and a transit corridor through Syunik ('Trump Route').", "diplomacy", 38.90, -77.04, "Washington", 4),
    ("2025-05-12", "PKK announces dissolution and end of armed struggle",
     "Following Öcalan's February call, the group began disarmament — a potential end to a 40-year insurgency.", "diplomacy", 37.07, 43.99, "Qandil Mountains", 4),
    ("2025-06-01", "Ukraine's Operation Spiderweb strikes Russian strategic bombers",
     "Smuggled FPV drones hit airbases across Russia, damaging or destroying long-range aircraft thousands of km from Ukraine.", "conflict", 55.04, 82.93, "Novosibirsk", 4),
    ("2025-09-10", "Israel strikes Hamas negotiators in Doha",
     "An unprecedented attack on Qatari soil during ceasefire talks strained US-Israel-Gulf relations.", "conflict", 25.29, 51.53, "Doha", 4),
    ("2025-10-09", "Gaza phase-one deal: hostages for prisoners, partial pullback",
     "A Trump-plan-based agreement in Sharm el-Sheikh returned the last living hostages and set a fragile truce.", "diplomacy", 31.50, 34.47, "Gaza", 5),
    ("2025-10-26", "El Fasher falls to the RSF amid mass killings",
     "The last army stronghold in Darfur collapsed after an 18-month siege; satellite imagery documented massacres.", "conflict", 13.63, 25.35, "El Fasher", 5),
    ("2025-10-10", "María Corina Machado awarded Nobel Peace Prize",
     "The Venezuelan opposition leader was honored as US military pressure on the Maduro government escalated.", "geopolitics", 10.49, -66.88, "Caracas", 3),
    ("2025-11-29", "US strikes on alleged drug boats stir legal storm",
     "A months-long campaign of lethal strikes on suspected trafficking vessels off Venezuela drew congressional and allied scrutiny.", "military", 12.0, -68.0, "Caribbean Sea", 4),
    ("2025-06-12", "Air India Boeing 787 crashes after takeoff from Ahmedabad",
     "The crash killed 241 aboard and dozens on the ground — the deadliest aviation disaster in a decade.", "disaster", 23.03, 72.58, "Ahmedabad", 5),
    ("2025-09-03", "Beijing stages massive WWII-anniversary military parade",
     "Xi hosted Putin and Kim Jong Un, debuting hypersonic and AI-enabled systems in a show of alignment.", "military", 39.90, 116.40, "Beijing", 3),
    ("2025-08-15", "Trump and Putin meet in Alaska; no ceasefire breakthrough",
     "The Anchorage summit reset US-Russia contact over Ukraine but produced no agreement.", "diplomacy", 61.22, -149.90, "Anchorage", 4),
    ("2025-12-01", "JNIM fuel blockade strangles Bamako",
     "Al-Qaeda's Sahel franchise besieged Mali's capital economy, marking jihadist momentum across the region.", "conflict", 12.64, -8.00, "Bamako", 4),
    ("2025-10-29", "Hurricane Melissa devastates Jamaica at Category 5",
     "One of the Atlantic's strongest recorded landfalls caused catastrophic damage across the Caribbean.", "disaster", 18.11, -77.30, "Jamaica", 5),
    ("2025-11-21", "COP30 in Belém ends with modest adaptation deal",
     "The Amazon-hosted summit tripled adaptation finance but dodged a fossil-fuel roadmap; the US skipped it.", "diplomacy", -1.46, -48.50, "Belém", 3),
    ("2025-12-10", "Venezuela standoff deepens as US carrier group patrols Caribbean",
     "Washington's pressure campaign against Maduro — strikes, sanctions, bounty — kept regional war risk elevated.", "geopolitics", 10.49, -66.88, "Caracas", 4),
    ("2026-01-05", "Ukraine peace-plan diplomacy intensifies into the new year",
     "US-mediated shuttle talks over a revised peace framework continued amid fighting; core disputes (territory, guarantees) unresolved.", "diplomacy", 50.45, 30.52, "Kyiv", 4),
    ("2025-11-10", "Syria's al-Sharaa makes historic White House visit",
     "The first Syrian presidential visit to Washington sealed sanctions relief and a new regional alignment.", "diplomacy", 38.90, -77.04, "Washington", 4),
    ("2025-09-28", "Moldova's pro-EU party wins pivotal election despite interference",
     "PAS held its majority against a massive Russian influence operation, keeping EU accession on track.", "geopolitics", 47.01, 28.86, "Chișinău", 3),
]


def _ensure_source(name, kind, attribution):
    """The curated historical packs get their OWN source row of type 'archive'
    (v7.4.1). It is NEVER polled (is_active=0) — it only attributes the
    hand-curated raw_items. It used to be mislabeled type 'gdelt', which
    conflated our clean curated history with the banned GDELT junk feed and
    made it look like GDELT was still a source."""
    row = query_one("SELECT id, type FROM sources WHERE name = ?", (name,))
    if row:
        # an existing DB may still carry the old mislabeled type 'gdelt' on this
        # curated row — re-type it to 'archive' so it stops showing up as a
        # GDELT source AND survives purge_gdelt()'s type='gdelt' sweep.
        if row["type"] != kind:
            with write_tx() as conn:
                conn.execute("UPDATE sources SET type = ? WHERE id = ?",
                             (kind, row["id"]))
        return row["id"]
    sid = new_id()
    with write_tx() as conn:
        conn.execute(
            "INSERT INTO sources (id, name, type, url, poll_interval_seconds,"
            " health_status, kind, attribution, reliability_tier, is_active)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, name, "archive", "", 86400, "ok", "reported",
             attribution, "high", 0))   # is_active=0: never polled live
    return sid


def seed_curated_history():
    """Insert the curated pack once (idempotent via external_id)."""
    if meta_get("backfill:curated_seeded") == "1":
        return 0
    sid = _ensure_source(ARCHIVE_SOURCE_NAME, "archive",
                         "Curated from the public record (historical)")
    n = 0
    for date, title, summary, cat, lat, lon, place, sev in HISTORICAL_EVENTS:
        ext = f"hist:{date}:{title[:40]}"
        if query_one("SELECT id FROM raw_items WHERE external_id = ?", (ext,)):
            continue
        payload = {"title": title, "summary": summary + " (historical)",
                   "link": "", "published": f"{date}T12:00:00+00:00",
                   "lat": lat, "lon": lon, "location_name": place,
                   "category": _CAT_TO_BASE.get(cat, cat), "severity": sev}
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO raw_items (id, source_id, raw_content, fetched_at,"
                " processed, external_id) VALUES (?,?,?,?,0,?)",
                (new_id(), sid, json.dumps(payload), now_iso(), ext))
        n += 1
    meta_set("backfill:curated_seeded", "1")
    log.info("curated_history_seeded", extra={"data": {"events": n}})
    return n


# the pack uses a rich editorial taxonomy; events.category admits the v8.13
# stored set — map the remaining extras onto their closest base category (the
# finer label survives in the title/summary text for retrieval). v8.13:
# 'technology' is now a real stored category, so it no longer collapses to
# 'other'; only 'military'/'diplomacy' still fold down.
_CAT_TO_BASE = {"military": "conflict", "diplomacy": "geopolitics"}


def seed_deep_history():
    """v7.2 — insert the deep 1945→present pack once (idempotent). Same archive
    source; dated in the past so it sorts below fresh news but fills the chain
    with seven decades of ground truth for correlation + analyst grounding."""
    if meta_get("backfill:deep_seeded") == "1":
        return 0
    from .history_pack import DEEP_HISTORY
    sid = _ensure_source(ARCHIVE_SOURCE_NAME, "archive",
                         "Curated from the public record (historical)")
    n = 0
    for date, title, summary, cat, lat, lon, place, sev in DEEP_HISTORY:
        ext = f"deep:{date}:{title[:40]}"
        if query_one("SELECT id FROM raw_items WHERE external_id = ?", (ext,)):
            continue
        payload = {"title": title, "summary": summary + " (historical)",
                   "link": "", "published": f"{date}T12:00:00+00:00",
                   "lat": lat, "lon": lon, "location_name": place,
                   "category": _CAT_TO_BASE.get(cat, cat), "severity": sev}
        with write_tx() as conn:
            conn.execute(
                "INSERT INTO raw_items (id, source_id, raw_content, fetched_at,"
                " processed, external_id) VALUES (?,?,?,?,0,?)",
                (new_id(), sid, json.dumps(payload), now_iso(), ext))
        n += 1
    meta_set("backfill:deep_seeded", "1")
    log.info("deep_history_seeded", extra={"data": {"events": n}})
    return n


# ── GDELT PERMANENT BAN + PURGE (v7.4.1) ────────────────────────────────────
# The GDELT 2.0 archive walk that used to live here is DELETED. GDELT is
# banned everywhere (owner: "block them EVERYWHERE AND IN EVERY WAY … literally
# DELETE them instantly … it keeps sending me shitty articles and trashing the
# system"). purge_gdelt() runs at every startup and hard-deletes any GDELT
# source row and ALL derived rows (raw_items → events → extracted_facts →
# story_members, and now-orphaned stories) — belt-and-suspenders with the
# scheduler _is_gdelt() thread block and the extract-time source-type guard.

# any source whose type, name or url smells of GDELT — but NEVER our clean
# curated archive (it once carried the old mislabeled type 'gdelt'; we re-type
# it first, then exclude it by name so its 177 curated events can never be swept)
_GDELT_MATCH = (
    "(type = 'gdelt' OR type = 'gdelt_events'"
    " OR lower(name) LIKE '%gdelt%' OR lower(url) LIKE '%gdelt%')"
    " AND name != ?"
)


def purge_gdelt() -> dict:
    """Delete every GDELT-sourced entry and the GDELT source rows themselves.
    Idempotent and cheap when there's nothing to purge. Cascades by hand
    because SQLite FKs aren't ON DELETE CASCADE here."""
    # first heal the curated archive row if a legacy DB still types it 'gdelt',
    # so it survives the sweep below (it holds real 1945→present ground truth).
    with write_tx() as conn:
        conn.execute(
            "UPDATE sources SET type = 'archive' WHERE name = ?"
            " AND type IN ('gdelt', 'gdelt_events')", (ARCHIVE_SOURCE_NAME,))
    sids = [r["id"] for r in query(
        f"SELECT id FROM sources WHERE {_GDELT_MATCH}", (ARCHIVE_SOURCE_NAME,))]
    if not sids:
        return {"sources": 0, "raw_items": 0, "events": 0, "facts": 0}
    marks = ",".join("?" * len(sids))
    # raw_items from these sources, and the events/facts derived from them
    raw_ids = [r["id"] for r in query(
        f"SELECT id FROM raw_items WHERE source_id IN ({marks})", sids)]
    ev_ids = [r["id"] for r in query(
        f"SELECT id FROM events WHERE raw_item_id IN ({marks})", raw_ids)] if raw_ids else []
    # facts can be attributed straight to the source too (extracted_facts.source_id)
    fact_ids = set(r["id"] for r in query(
        f"SELECT id FROM extracted_facts WHERE source_id IN ({marks})", sids))
    if ev_ids:
        em = ",".join("?" * len(ev_ids))
        fact_ids.update(r["id"] for r in query(
            f"SELECT id FROM extracted_facts WHERE event_id IN ({em})", ev_ids))
    counts = {"sources": len(sids), "raw_items": len(raw_ids),
              "events": len(ev_ids), "facts": len(fact_ids)}
    with write_tx() as conn:
        def _del(table, col, ids):
            for i in range(0, len(ids), 400):
                chunk = ids[i:i + 400]
                conn.execute(
                    f"DELETE FROM {table} WHERE {col} IN ({','.join('?' * len(chunk))})",
                    chunk)
        fids = list(fact_ids)
        _del("story_members", "event_id", ev_ids)
        _del("story_members", "fact_id", fids)
        _del("extracted_facts", "id", fids)
        _del("events", "id", ev_ids)
        _del("raw_items", "id", raw_ids)
        _del("sources", "id", sids)
        # drop any stories left with no members (they were purely GDELT-built)
        conn.execute(
            "DELETE FROM stories WHERE id NOT IN"
            " (SELECT DISTINCT story_id FROM story_members)")
        # clear the retired backfill cursor so nothing tries to resume
        conn.execute("DELETE FROM app_meta WHERE key LIKE 'backfill:gdelt%'")
    log.info("gdelt_purged", extra={"data": counts})
    return counts
