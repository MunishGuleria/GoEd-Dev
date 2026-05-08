"""
Test Archive Runner — One-Shot Full Pipeline Test

Discovers ALL sessions in Redis (web + social media), bypasses cron
scheduling and inactivity thresholds, and runs the complete archival
pipeline with detailed per-step logging.

ALL sessions go to both PostgreSQL and Dataverse regardless of lead_id.
lead_id only controls whether the Lead lookup is bound on the Dataverse
parent record — it never blocks archival.

Usage:
    python test_archive.py             # Full run — archives everything
    python test_archive.py --dry-run   # Inspect only — no writes
"""
import os
import sys
import json
import time
import asyncio
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict

from dotenv import load_dotenv

# ==================== SETUP ====================
load_dotenv()

# ——— Logging (DEBUG level for maximum visibility) ———
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(name)-18s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
handler.flush = sys.stdout.flush
logging.basicConfig(level=logging.DEBUG, handlers=[handler])
log = logging.getLogger("test_archive")

# Suppress noisy third-party loggers
for noisy in ("httpx", "httpcore", "urllib3", "azure", "openai", "asyncio"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ——— Imports (after dotenv so env vars are available) ———
from connection import RedisConnectionPool, postgres, dataverse, llm
from postgres_ops import batch_archive_to_postgres
from dataverse_ops import archive_to_dataverse
from llm_ops import batch_summarize_sessions
from utils import now_ist, parse_dt
from archive_worker import ArchiveWorker, validate_environment, ARCHIVE_BATCH_SIZE, LLM_CONCURRENCY


# ==================== HELPERS ====================
def classify_session(sid: str) -> str:
    """Return 'SOCIAL' or 'WEB' based on the session ID prefix."""
    social_prefixes = ("whatsapp:", "facebook:", "instagram:")
    return "SOCIAL" if any(sid.startswith(p) for p in social_prefixes) else "WEB"


def lead_label(data: Dict) -> str:
    """Return a short lead status label for logging."""
    lead = data.get("lead_id")
    return f"Lead={lead}" if lead else "No Lead"


def session_detail_line(data: Dict) -> str:
    """Build a one-line detail string for a session."""
    sid = data["session_id"]
    channel = classify_session(sid)
    msgs = data["total_messages"]
    user_msgs = data["user_message_count"]
    asst_msgs = data["assistant_message_count"]
    in_tok = data["input_tokens"]
    out_tok = data["output_tokens"]
    created = data["created_at"].strftime("%Y-%m-%d %H:%M:%S") if data.get("created_at") else "?"
    last_act = data["last_activity"].strftime("%Y-%m-%d %H:%M:%S") if data.get("last_activity") else "?"
    lead = data.get("lead_id") or "— (no lead, will still archive)"
    return (
        f"  [{channel:6s}] {sid}\n"
        f"           Messages: {msgs} (User: {user_msgs}, Assistant: {asst_msgs}) | "
        f"Tokens: in={in_tok} out={out_tok}\n"
        f"           Created: {created} | Last Activity: {last_act} | Lead: {lead}"
    )


def print_summary_table(results: Dict):
    """Print a formatted summary table."""
    border = "=" * 80
    log.info(border)
    log.info("                        📊  FINAL SUMMARY TABLE")
    log.info(border)
    log.info(
        f"  {'Channel':<10} | {'Found':<6} | {'Fetched':<8} | "
        f"{'PG OK':<6} | {'PG Fail':<8} | {'DV OK':<6} | {'DV Fail':<8} | "
        f"{'w/Lead':<7} | {'No Lead':<7}"
    )
    log.info("-" * 80)
    for channel in ("WEB", "SOCIAL"):
        r = results.get(channel, {})
        log.info(
            f"  {channel:<10} | {r.get('found', 0):<6} | {r.get('fetched', 0):<8} | "
            f"{r.get('pg_ok', 0):<6} | {r.get('pg_fail', 0):<8} | "
            f"{r.get('dv_ok', 0):<6} | {r.get('dv_fail', 0):<8} | "
            f"{r.get('with_lead', 0):<7} | {r.get('without_lead', 0):<7}"
        )
    log.info("-" * 80)
    # Totals row
    total = {
        k: sum(results.get(ch, {}).get(k, 0) for ch in ("WEB", "SOCIAL"))
        for k in ("found", "fetched", "pg_ok", "pg_fail", "dv_ok", "dv_fail", "with_lead", "without_lead")
    }
    log.info(
        f"  {'TOTAL':<10} | {total['found']:<6} | {total['fetched']:<8} | "
        f"{total['pg_ok']:<6} | {total['pg_fail']:<8} | "
        f"{total['dv_ok']:<6} | {total['dv_fail']:<8} | "
        f"{total['with_lead']:<7} | {total['without_lead']:<7}"
    )
    log.info(border)
    log.info("  ℹ️  'No Lead' sessions are archived to BOTH PG + Dataverse — lead only controls Lead binding.")
    log.info(border)


# ==================== MAIN TEST ====================
async def run_test(dry_run: bool = False):
    overall_start = time.time()
    worker = ArchiveWorker()

    mode_label = "🔍 DRY-RUN" if dry_run else "🚀 FULL RUN"
    log.info(f"{'=' * 80}")
    log.info(f"  {mode_label} — Test Archive Runner")
    log.info(f"  Time: {now_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    log.info(f"  NOTE: ALL sessions archived regardless of lead_id presence")
    log.info(f"{'=' * 80}")

    # ——————————————————————————————————————————————
    # PHASE 1: Discover sessions (bypass all thresholds)
    # ——————————————————————————————————————————————
    log.info("")
    log.info("━" * 60)
    log.info("  PHASE 1 — Session Discovery (Redis SCAN, no threshold filters)")
    log.info("━" * 60)
    phase_start = time.time()

    cursor = 0
    all_keys: List[str] = []
    while True:
        cursor, keys = await worker._redis_scan(cursor, "last_activity:*", 200)
        for key in keys:
            all_keys.append(key if isinstance(key, str) else key.decode())
        if cursor == 0:
            break

    session_ids = [k.split("last_activity:")[-1] for k in all_keys]
    web_ids = [s for s in session_ids if classify_session(s) == "WEB"]
    social_ids = [s for s in session_ids if classify_session(s) == "SOCIAL"]

    log.info(f"  Found {len(session_ids)} sessions (Web: {len(web_ids)}, Social: {len(social_ids)})")
    for sid in session_ids:
        log.debug(f"    → [{classify_session(sid):6s}] {sid}")
    log.info(f"  ⏱ Discovery took {time.time() - phase_start:.2f}s")

    if not session_ids:
        log.info("  ⚠️ No sessions found in Redis. Nothing to do.")
        return

    # Track results per channel — now includes with_lead / without_lead counters
    results: Dict[str, Dict] = {
        "WEB": {
            "found": len(web_ids), "fetched": 0,
            "pg_ok": 0, "pg_fail": 0,
            "dv_ok": 0, "dv_fail": 0,
            "with_lead": 0, "without_lead": 0,
        },
        "SOCIAL": {
            "found": len(social_ids), "fetched": 0,
            "pg_ok": 0, "pg_fail": 0,
            "dv_ok": 0, "dv_fail": 0,
            "with_lead": 0, "without_lead": 0,
        },
    }

    # ——————————————————————————————————————————————
    # PHASE 2: Fetch session data
    # ——————————————————————————————————————————————
    log.info("")
    log.info("━" * 60)
    log.info("  PHASE 2 — Fetch Session Data")
    log.info("━" * 60)
    phase_start = time.time()

    fetch_tasks = [worker.get_session_data(sid) for sid in session_ids]
    fetched_raw = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    session_data_list: List[Dict] = []
    for sid, data in zip(session_ids, fetched_raw):
        channel = classify_session(sid)
        if isinstance(data, Exception):
            log.error(f"  ❌ Fetch FAILED for [{channel}] {sid}: {data}")
            continue
        if not data or not data.get("messages"):
            log.warning(f"  ⚠️  No messages for [{channel}] {sid} — skipping")
            continue
        session_data_list.append(data)
        results[channel]["fetched"] += 1

        # Track lead presence
        if data.get("lead_id"):
            results[channel]["with_lead"] += 1
            log.info(f"  ✅ Fetched [{channel}] {sid} — {data['total_messages']} msgs | Lead: {data['lead_id']}")
        else:
            results[channel]["without_lead"] += 1
            log.info(f"  ✅ Fetched [{channel}] {sid} — {data['total_messages']} msgs | No Lead (will still archive)")

    log.info(f"  ⏱ Fetch took {time.time() - phase_start:.2f}s")
    log.info(f"  📦 Successfully fetched: {len(session_data_list)} / {len(session_ids)}")

    if not session_data_list:
        log.info("  ⚠️ No valid session data fetched. Nothing to archive.")
        print_summary_table(results)
        return

    # Print detailed session info
    log.info("")
    log.info("─" * 60)
    log.info("  SESSION DETAILS:")
    log.info("─" * 60)
    for data in session_data_list:
        log.info(session_detail_line(data))

    # ——————————————————————————————————————————————
    # PHASE 3: LLM Summarization
    # ——————————————————————————————————————————————
    log.info("")
    log.info("━" * 60)
    log.info("  PHASE 3 — LLM Summarization")
    log.info("━" * 60)
    phase_start = time.time()

    needs_summary = [d for d in session_data_list if not d.get("summary")]
    already_has = len(session_data_list) - len(needs_summary)
    log.info(f"  Sessions needing summary: {len(needs_summary)} (already have: {already_has})")

    if dry_run:
        log.info("  ⏭️  DRY-RUN: Skipping LLM summarization")
        for d in needs_summary:
            d["summary"] = "[DRY-RUN] Summary skipped"
    else:
        try:
            await batch_summarize_sessions(llm, postgres, session_data_list, LLM_CONCURRENCY)
            log.info(f"  ✅ Summarization complete")
        except Exception as e:
            log.error(f"  ❌ Summarization error: {e}")
            for d in session_data_list:
                if not d.get("summary"):
                    d["summary"] = "Summary generation failed."

    # Log summaries
    for data in session_data_list:
        sid = data["session_id"]
        channel = classify_session(sid)
        summary_preview = (data.get("summary") or "—")[:120]
        log.info(f"  📝 [{channel}] {sid} → {summary_preview}")

    log.info(f"  ⏱ Summarization took {time.time() - phase_start:.2f}s")

    # ——————————————————————————————————————————————
    # PHASE 3.5: Enrich with Source Info
    # ——————————————————————————————————————————————
    log.info("")
    log.info("━" * 60)
    log.info("  PHASE 3.5 — Source Enrichment")
    log.info("━" * 60)
    for data in session_data_list:
        source_name, source_value = worker.determine_source(data["session_id"])
        data["source"] = source_name
        data["source_value"] = source_value
        channel = classify_session(data["session_id"])
        log.info(
            f"  🏷️  [{channel}] {data['session_id']} → "
            f"source={source_name} (DV: {source_value}) | {lead_label(data)}"
        )

    # ——————————————————————————————————————————————
    # PHASE 4: Archive to PostgreSQL
    # ——————————————————————————————————————————————
    log.info("")
    log.info("━" * 60)
    log.info("  PHASE 4 — Archive to PostgreSQL")
    log.info("━" * 60)
    phase_start = time.time()

    if dry_run:
        log.info("  ⏭️  DRY-RUN: Skipping PostgreSQL writes")
        pg_results = [{"sid": d["session_id"], "success": True, "error": None} for d in session_data_list]
    else:
        pg_results = await batch_archive_to_postgres(postgres, session_data_list, ARCHIVE_BATCH_SIZE)

    pg_failed_sids = set()
    for r in pg_results:
        sid = r["sid"]
        channel = classify_session(sid)
        if r.get("success"):
            results[channel]["pg_ok"] += 1
            log.info(f"  ✅ [PG] [{channel}] {sid} — archived successfully")
        else:
            results[channel]["pg_fail"] += 1
            pg_failed_sids.add(sid)
            log.error(f"  ❌ [PG] [{channel}] {sid} — FAILED: {r.get('error', 'unknown')}")

    log.info(f"  ⏱ PostgreSQL took {time.time() - phase_start:.2f}s")

    # ——————————————————————————————————————————————
    # PHASE 5: Archive to Dataverse
    # ALL sessions go here — lead_id only controls Lead binding on the record
    # ——————————————————————————————————————————————
    log.info("")
    log.info("━" * 60)
    log.info("  PHASE 5 — Archive to Dataverse (ALL sessions, with or without Lead)")
    log.info("━" * 60)
    phase_start = time.time()

    successful_sessions = [d for d in session_data_list if d["session_id"] not in pg_failed_sids]
    dv_with_lead = [d for d in successful_sessions if d.get("lead_id")]
    dv_without_lead = [d for d in successful_sessions if not d.get("lead_id")]

    log.info(
        f"  Sessions eligible for Dataverse: {len(successful_sessions)} "
        f"(PG-failed excluded: {len(pg_failed_sids)})"
    )
    log.info(f"  → With Lead (will bind Lead record): {len(dv_with_lead)}")
    log.info(f"  → Without Lead (parent record only): {len(dv_without_lead)}")

    if dry_run:
        log.info("  ⏭️  DRY-RUN: Skipping Dataverse writes")
        for d in successful_sessions:
            channel = classify_session(d["session_id"])
            results[channel]["dv_ok"] += 1
            log.info(
                f"  ⏭️  [DV] [{channel}] {d['session_id']} — would archive | {lead_label(d)}"
            )
    else:
        # Log intent before firing
        for d in successful_sessions:
            channel = classify_session(d["session_id"])
            if d.get("lead_id"):
                log.info(
                    f"  📤 [DV] [{channel}] {d['session_id']} — "
                    f"sending with Lead binding ({d['lead_id']})"
                )
            else:
                log.info(
                    f"  📤 [DV] [{channel}] {d['session_id']} — "
                    f"sending WITHOUT Lead binding (no lead_id)"
                )

        dv_tasks = [archive_to_dataverse(dataverse, d) for d in successful_sessions]
        dv_results = await asyncio.gather(*dv_tasks, return_exceptions=True)

        for data, dv_result in zip(successful_sessions, dv_results):
            sid = data["session_id"]
            channel = classify_session(sid)
            if isinstance(dv_result, Exception):
                results[channel]["dv_fail"] += 1
                log.error(
                    f"  ❌ [DV] [{channel}] {sid} — EXCEPTION: {dv_result} | {lead_label(data)}"
                )
            elif dv_result is True:
                results[channel]["dv_ok"] += 1
                log.info(
                    f"  ✅ [DV] [{channel}] {sid} — archived successfully | {lead_label(data)}"
                )
            else:
                results[channel]["dv_fail"] += 1
                log.error(
                    f"  ❌ [DV] [{channel}] {sid} — FAILED (returned {dv_result}) | {lead_label(data)}"
                )

    log.info(f"  ⏱ Dataverse took {time.time() - phase_start:.2f}s")

    # ——————————————————————————————————————————————
    # PHASE 6: Redis Cleanup
    # ——————————————————————————————————————————————
    log.info("")
    log.info("━" * 60)
    log.info("  PHASE 6 — Redis Cleanup")
    log.info("━" * 60)
    phase_start = time.time()

    if dry_run:
        log.info("  ⏭️  DRY-RUN: Skipping Redis cleanup")
    else:
        for data in successful_sessions:
            sid = data["session_id"]
            channel = classify_session(sid)
            try:
                await worker._cleanup_redis(sid)
                log.info(f"  🧹 [{channel}] {sid} — cleaned up")
            except Exception as e:
                log.error(f"  ❌ [{channel}] {sid} — cleanup failed: {e}")

    log.info(f"  ⏱ Cleanup took {time.time() - phase_start:.2f}s")

    # ——————————————————————————————————————————————
    # FINAL SUMMARY
    # ——————————————————————————————————————————————
    log.info("")
    total_duration = time.time() - overall_start
    print_summary_table(results)
    log.info(f"  ⏱ Total execution time: {total_duration:.2f}s")
    log.info(f"  {'🔍 DRY-RUN complete — no data was modified' if dry_run else '✅ FULL RUN complete'}")


# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test Archive Runner — full pipeline for web + social sessions"
    )
    parser.add_argument("--dry-run", action="store_true", help="Inspect sessions without archiving")
    args = parser.parse_args()

    try:
        validate_environment()
        asyncio.run(run_test(dry_run=args.dry_run))
    except ValueError as e:
        log.error(f"❌ Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Shutdown requested by user")
    except Exception as e:
        log.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)