"""
Archive Worker - Session Archival Orchestrator

Orchestrates the archival of inactive chat sessions from Redis to:
- PostgreSQL (primary storage)
- Dataverse (CRM integration)

Features:
- LLM-based final summary generation
- Batch processing for efficiency
- Graceful shutdown handling
- Dual Scheduling:
  - Web: Continuous archival (30 min inactivity)
  - Social: Cron-scheduled archival (Daily 3 AM)
"""
import os
import sys
import json
import asyncio
import signal
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from croniter import croniter

from connection import RedisConnectionPool, postgres, dataverse, llm
from postgres_ops import archive_to_postgres, batch_archive_to_postgres, flush_trial_message_count
from dataverse_ops import (
    archive_to_dataverse, check_lead, create_new_lead, 
    update_existing_lead, create_or_update_academic_history,
    create_or_update_lead_exams, handle_campus_visit
)
from llm_ops import batch_analyze_sessions
from email_ops import send_brochure_email
from utils import now_ist, parse_dt

# ==================== CONFIG ====================
load_dotenv()

# Time Constants (in seconds)
SOCIAL_SYNC_WINDOW_SECONDS = 3900  # 65 minutes - window for social sync detection
SOCIAL_IDEMPOTENCY_THRESHOLD_SECONDS = 72000  # 20 hours - threshold for social sync idempotency
ARCHIVED_KEY_TTL_SECONDS = 2 * 3600  # 2 hours - Redis auto-expires archived:{sid} keys
LOCK_TTL_SECONDS = 300  # 5 minutes - distributed lock TTL
RETRY_BACKOFF_SECONDS = 2  # Backoff delay between retries

# Session Settings
SESSION_INACTIVITY_MINUTES = int(os.getenv("SESSION_INACTIVITY_MINUTES", 30))
ARCHIVE_BATCH_SIZE = int(os.getenv("ARCHIVE_BATCH_SIZE", 50))
WORKER_INTERVAL_SECONDS = int(os.getenv("ARCHIVE_WORKER_INTERVAL_SECONDS", 120))
MAX_PARALLEL_ARCHIVES = 10
MAX_RETRIES = 3
LLM_CONCURRENCY = 5
POSTGRES_CHUNK_SIZE = ARCHIVE_BATCH_SIZE  # Sessions per Postgres batch (from env)

# Social Sync Config
SOCIAL_SYNC_CRON = os.getenv("SOCIAL_SYNC_CRON", "0 3 * * *")
SOCIAL_SAFETY_BUFFER_MINUTES = int(os.getenv("SOCIAL_SAFETY_BUFFER_MINUTES", 10))

# Required Environment Variables
REQUIRED_ENV_VARS = [
    "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DATABASE", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "DATAVERSE_BASE_URL", "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_SCOPE",
    "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_INSTANCE_NAME", "AZURE_OPENAI_API_DEPLOYMENT_NAME", "AZURE_OPENAI_API_VERSION"
]

def validate_environment():
    """Validate that all required environment variables are set."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# ==================== LOGGING ====================
# Use StreamHandler with explicit flush to avoid buffering issues
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
handler.flush = sys.stdout.flush  # Force immediate flush
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger("archive_worker")


# ==================== WORKER ====================
class ArchiveWorker:
    KEYS = {
        "messages": "messages:list:{}",
        "summary": "summary:{}",
        "buffer": "messages:buffer:{}",
        "ai_analysis": "ai_analysis:{}",
        "count": "count:{}",
        "user_count": "user_count:{}",
        "last_activity": "last_activity:{}",
        "created_at": "created_at:{}",
        "last_summarized_index": "last_summarized_index:{}",
        "archived": "archived:{}",
        "lock": "archive_lock:{}",
        "lead_id": "lead_id:{}",
        "existing_lead_data": "existing_lead_data:{}",
        "analysis_in_progress": "analysis_in_progress:{}",
        "social_sync_last_run": "social_sync:last_run",
    }

    def __init__(self):
        self.redis = RedisConnectionPool.get_client()
        self.web_inactivity_threshold = timedelta(minutes=SESSION_INACTIVITY_MINUTES)
        self.social_safety_buffer = timedelta(minutes=SOCIAL_SAFETY_BUFFER_MINUTES)
        self.batch_size = ARCHIVE_BATCH_SIZE
        self.semaphore = asyncio.Semaphore(MAX_PARALLEL_ARCHIVES)
        self.shutdown_event = asyncio.Event()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        def signal_handler(signum, frame):
            self.shutdown_event.set()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, signal_handler)

    def key(self, name: str, sid: str) -> str:
        return self.KEYS[name].format(sid)

    # ---------- ASYNC REDIS HELPERS ----------
    async def _redis_scan(self, cursor: int, match: str, count: int):
        """Async wrapper for Redis SCAN with error handling."""
        try:
            return await asyncio.to_thread(self.redis.scan, cursor, match=match, count=count)
        except Exception as e:
            log.error(f"❌ Redis SCAN error: {e}")
            await RedisConnectionPool.reconnect()
            raise

    async def _redis_get(self, key: str):
        """Async wrapper for Redis GET with error handling."""
        try:
            return await asyncio.to_thread(self.redis.get, key)
        except Exception as e:
            log.error(f"❌ Redis GET error for key {key}: {e}")
            await RedisConnectionPool.reconnect()
            raise

    async def _redis_set(self, key: str, value: str, **kwargs):
        """Async wrapper for Redis SET with error handling."""
        try:
            return await asyncio.to_thread(self.redis.set, key, value, **kwargs)
        except Exception as e:
            log.error(f"❌ Redis SET error for key {key}: {e}")
            await RedisConnectionPool.reconnect()
            raise

    async def _redis_setex(self, key: str, ttl: int, value: str):
        """Async wrapper for Redis SETEX with error handling."""
        try:
            return await asyncio.to_thread(self.redis.setex, key, ttl, value)
        except Exception as e:
            log.error(f"❌ Redis SETEX error for key {key}: {e}")
            await RedisConnectionPool.reconnect()
            raise

    async def _redis_delete(self, *keys: str):
        """Async wrapper for Redis DELETE with error handling."""
        try:
            return await asyncio.to_thread(self.redis.delete, *keys)
        except Exception as e:
            log.error(f"❌ Redis DELETE error for keys {keys}: {e}")
            await RedisConnectionPool.reconnect()
            raise

    async def _redis_pipeline_execute(self, pipe):
        """Async wrapper for pipeline execution with error handling."""
        try:
            return await asyncio.to_thread(pipe.execute)
        except Exception as e:
            log.error(f"❌ Redis pipeline execution error: {e}")
            await RedisConnectionPool.reconnect()
            raise

    # Maps session ID prefix → (Postgres source name, zx_engagementsource, zx_leadsource)
    SOURCE_MAP = {
        "whatsapp:":  ("WhatsApp",  128780003, 128780010),
        "facebook:":  ("Facebook",  128780000, 128780002),
        "instagram:": ("Instagram", 128780001, 128780002),
        "sess_":      ("Website",   128780004, 128780000),
    }
    DEFAULT_SOURCE = (None, None, None)

    def determine_source(self, sid: str) -> tuple:
        """Determine engagement source from session ID prefix."""
        for prefix, source in self.SOURCE_MAP.items():
            if sid.startswith(prefix):
                return source
        return self.DEFAULT_SOURCE

    # ---------- SESSION DISCOVERY & SCHEDULING ----------
    def _is_social_session(self, sid: str) -> bool:
        """Heuristic to check if session is from social media (WhatsApp, FB, IG)."""
        return any(sid.startswith(prefix) for prefix in ["whatsapp:", "facebook:", "instagram:"])

    def _should_run_social_sync(self, now: datetime) -> bool:
        """
        Check if we are in the 'Cron Window' for social sync.
        Rule: Current time matches cron AND we haven't run in this window yet.
        """
        try:
            cron = croniter(SOCIAL_SYNC_CRON, now)
            prev_run_time = cron.get_prev(datetime)
            time_since_schedule = (now - prev_run_time).total_seconds()
            return time_since_schedule < SOCIAL_SYNC_WINDOW_SECONDS
        except Exception as e:
            log.error(f"❌ Cron Check Error: {e}")
            return False

    async def _check_social_idempotency(self, now: datetime) -> bool:
        """
        Ensure we run only once per cycle.
        Returns True if we SHOULD run (haven't run yet).
        """
        last_run_str = await self._redis_get(self.KEYS["social_sync_last_run"])
        if not last_run_str:
            return True

        last_run = parse_dt(last_run_str)
        if not last_run:
            return True

        if (now - last_run).total_seconds() > SOCIAL_IDEMPOTENCY_THRESHOLD_SECONDS:
            return True

        return False

    async def find_inactive_sessions(self) -> List[str]:
        now = now_ist()

        # 1. Determine if Social Sync should run
        run_social = False
        if self._should_run_social_sync(now):
            if await self._check_social_idempotency(now):
                log.info(f"⏰ Cron Match ({SOCIAL_SYNC_CRON}) - Triggering Social Sync")
                run_social = True
                await self._redis_set(self.KEYS["social_sync_last_run"], str(now))

        inactive = []
        cursor = 0

        # 2. Scan All Sessions - collect all keys first
        all_keys = []
        while True:
            cursor, keys = await self._redis_scan(cursor, "last_activity:*", 200)
            for key in keys:
                all_keys.append(key if isinstance(key, str) else key.decode())
            if cursor == 0:
                break

        if not all_keys:
            return inactive

        # 3. Batch fetch all last_activity values using pipeline
        pipe = self.redis.pipeline()
        for key in all_keys:
            pipe.get(key)
        results = await self._redis_pipeline_execute(pipe)

        # 4. Process results
        for key, last_activity_str in zip(all_keys, results):
            if not last_activity_str:
                continue

            session_id = key.split("last_activity:")[-1]
            
            # Skip sessions from other modules (ZOX_, IMT_, GoEd_, etc.)
            ALLOWED_PREFIXES = ("sess_", "whatsapp:", "facebook:", "instagram:")
            if not session_id.startswith(ALLOWED_PREFIXES):
                continue
            
            last_activity = parse_dt(last_activity_str)
            if not last_activity:
                continue

            is_social = self._is_social_session(session_id)

            # --- WEB LOGIC (Continuous) ---
            if not is_social:
                if last_activity < (now - self.web_inactivity_threshold):
                    inactive.append(session_id)

            # --- SOCIAL LOGIC (Scheduled) ---
            elif run_social and is_social:
                if last_activity < (now - self.social_safety_buffer):
                    inactive.append(session_id)

        return inactive

    # ---------- LOCKING ----------
    async def acquire_lock(self, sid: str) -> bool:
        result = await self._redis_set(self.key("lock", sid), "1", nx=True, ex=LOCK_TTL_SECONDS)
        return result is True

    async def release_lock(self, sid: str):
        await self._redis_delete(self.key("lock", sid))

    # ---------- IDEMPOTENCY CHECK ----------
    async def is_already_archived(self, sid: str) -> bool:
        """
        Check if session is already archived in Postgres.
        NOTE: Even if already in Postgres, Dataverse may have failed — 
        that is handled separately via the archived Redis key check.
        """
        async with postgres.acquire() as conn:
            return (
                await conn.fetchval("SELECT 1 FROM sessions WHERE session_id = $1", sid)
                is not None
            )

    # ---------- REDIS FETCH ----------
    async def get_session_data(self, sid: str) -> Optional[Dict]:
        pipe = self.redis.pipeline()
        pipe.lrange(self.key("messages", sid), 0, -1)
        pipe.get(self.key("summary", sid))
        pipe.lrange(self.key("buffer", sid), 0, -1)
        pipe.get(self.key("ai_analysis", sid))
        pipe.get(self.key("user_count", sid))
        pipe.get(self.key("last_activity", sid))
        pipe.get(self.key("created_at", sid))
        pipe.get(self.key("lead_id", sid))
        pipe.get(self.key("existing_lead_data", sid))
        pipe.get(self.key("last_summarized_index", sid))
        pipe.get(f"trial_user_id:{sid}")
        pipe.get(f"trial_type:{sid}")
        pipe.get(f"trial_metadata:{sid}")

        results = await self._redis_pipeline_execute(pipe)
        (messages_raw, existing_summary, buffer_raw, ai_analysis_raw,
         user_count, last_act, created, lead_id, existing_lead_data_raw,
         last_summarized_idx, trial_user_id, trial_type, trial_metadata) = results

        # Parse messages with error handling
        messages = []
        for m in (messages_raw or []):
            if not m:
                continue
            try:
                messages.append(json.loads(m))
            except (json.JSONDecodeError, TypeError) as e:
                log.warning(f"⚠️ Failed to parse message for session {sid}: {e}")
                continue

        # Parse buffer messages
        buffer_messages = []
        for m in (buffer_raw or []):
            if not m:
                continue
            try:
                buffer_messages.append(json.loads(m))
            except:
                continue

        # Parse existing lead data
        existing_lead_data = None
        if existing_lead_data_raw:
            try:
                existing_lead_data = json.loads(existing_lead_data_raw)
            except:
                pass

        actual_user_count = sum(1 for m in messages if m.get("role") == "user")
        u_count = int(user_count) if user_count else actual_user_count
        total_msg = len(messages)

        metadata = {}
        if trial_metadata:
            try:
                loaded = json.loads(trial_metadata)
                if isinstance(loaded, str):
                    loaded = json.loads(loaded)
                metadata = loaded if isinstance(loaded, dict) else {}
            except Exception:
                pass
                
        # --- COLLEGE RESOLUTION FALLBACK ---
        college_guid = metadata.get("dataverse_college_guid")
        college_name = metadata.get("college_name")
        
        # If Redis is missing college info but we have a trial_user_id, fetch from Postgres
        if trial_user_id and not college_guid:
            try:
                async with postgres.acquire() as conn:
                    row = await conn.fetchrow("SELECT metadata FROM trial_users WHERE id = $1", trial_user_id)
                    if row and row['metadata']:
                        pg_meta = row['metadata']
                        if isinstance(pg_meta, str): pg_meta = json.loads(pg_meta)
                        
                        college_guid = pg_meta.get("dataverse_college_guid") or college_guid
                        college_name = pg_meta.get("college_name") or college_name
                        
                        if college_guid:
                            log.info(f"✅ [RESOLVE] Found college in Postgres for trial {trial_user_id}: {college_name}")
            except Exception as e:
                log.error(f"❌ [RESOLVE] Postgres trial metadata lookup failed for {trial_user_id}: {e}")

        # lead_id is optional — None means no lead, session still gets archived everywhere
        return {
            "session_id": sid,
            "messages": messages,
            "existing_summary": existing_summary,
            "buffer_messages": buffer_messages,
            "ai_analysis": ai_analysis_raw,
            "summary": existing_summary,  # Will be overwritten by AI analysis
            "last_summarized_index": int(last_summarized_idx) if last_summarized_idx else None,
            "lead_id": lead_id,
            "existing_lead_data": existing_lead_data,
            "previous_context": existing_lead_data.get("previous_context", "") if existing_lead_data else "",
            "total_messages": total_msg,
            "user_message_count": u_count,
            "assistant_message_count": total_msg - u_count,
            "input_tokens": sum(m.get("tokens", {}).get("input", 0) for m in messages),
            "output_tokens": sum(m.get("tokens", {}).get("output", 0) for m in messages),
            "created_at": parse_dt(created) or now_ist(),
            "last_activity": parse_dt(last_act) or now_ist(),
            "trial_user_id": trial_user_id,
            "trial_type": trial_type,
            "college_guid": college_guid,
            "college_name": college_name
        }

    # ---------- ARCHIVE WITH RETRY (single-session legacy path) ----------
    async def archive_session_with_data(self, data: Dict) -> Dict:
        """
        Archive a session using pre-fetched and pre-summarized data.
        Returns dict with status: {"sid": str, "pg": bool, "dv": bool, "error": str|None}
        """
        sid = data["session_id"]
        result = {"sid": sid, "pg": False, "dv": False, "error": None}

        # 1. Enrich data with Source info
        source_name, engagement_source, lead_source_val = self.determine_source(sid)
        data["source"] = source_name
        data["engagement_source"] = engagement_source
        data["lead_source"] = lead_source_val

        async with self.semaphore:
            if not await self.acquire_lock(sid):
                result["error"] = "Could not acquire lock"
                return result
            try:
                if await self.is_already_archived(sid):
                    await self._cleanup_redis(sid)
                    return {"sid": sid, "pg": True, "dv": True, "error": None}

                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        pg_success = await archive_to_postgres(postgres, data, self.batch_size)

                        dv_success = False
                        try:
                            # All sessions go to Dataverse — lead_id only affects Lead binding
                            dv_success = await archive_to_dataverse(dataverse, data)
                        except Exception as e:
                            log.error(f"⚠️ Dataverse archive failed for {sid}: {e}")

                        if pg_success:
                            await self._cleanup_redis(sid)
                            return {"sid": sid, "pg": True, "dv": dv_success, "error": None}
                        else:
                            raise Exception("PostgreSQL insertion returned False")

                    except Exception as e:
                        if attempt < MAX_RETRIES:
                            log.warning(f"⚠️ Archive attempt {attempt} failed for {sid}: {e}. Retrying...")
                            await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                        else:
                            log.error(f"❌ Archive failed for {sid} after {MAX_RETRIES} attempts: {e}")
                            result["error"] = str(e)

                return result
            finally:
                await self.release_lock(sid)

    async def _archive_to_dataverse_and_cleanup(self, data: Dict) -> bool:
        """
        Archive to Dataverse and cleanup Redis.
        Only called for sessions that HAVE successfully archived to Postgres.
        All sessions are sent to Dataverse — lead_id only controls Lead binding.
        """
        sid = data["session_id"]
        dv_success = False

        try:
            # All sessions go to Dataverse regardless of lead_id
            _, engagement_source, _ = self.determine_source(sid)
            data["engagement_source"] = engagement_source
            dv_success = await archive_to_dataverse(dataverse, data)
            if not dv_success:
                log.warning(f"⚠️ Dataverse archive failed for {sid}")
        except Exception as e:
            log.error(f"❌ Dataverse error for {sid}: {e}")

        # Always cleanup Redis — Postgres is already secured
        await self._cleanup_redis(sid)

        return dv_success

    # ---------- REDIS CLEANUP ----------
    async def _cleanup_redis(self, sid: str):
        """Clean up all session keys from Redis after archival."""
        await self._redis_setex(self.key("archived", sid), ARCHIVED_KEY_TTL_SECONDS, "1")
        await self._redis_delete(
            self.key("messages", sid),
            self.key("summary", sid),
            self.key("buffer", sid),
            self.key("ai_analysis", sid),
            self.key("count", sid),
            self.key("user_count", sid),
            self.key("last_summarized_index", sid),
            self.key("last_activity", sid),
            self.key("created_at", sid),
            self.key("lead_id", sid),
            self.key("existing_lead_data", sid),
            self.key("analysis_in_progress", sid),
            f"trial_user_id:{sid}",
            f"trial_type:{sid}",
            f"trial_status:{sid}",
            f"trial_metadata:{sid}",
        )

    # ---------- MAIN LOOP ----------
    async def run_archive_cycle(self):
        try:
            await self._archive_inactive_sessions()
        except Exception as e:
            log.error(f"❌ Cycle error: {e}")

    async def _archive_inactive_sessions(self):
        """Find and archive inactive sessions with AI analysis, lead creation, and email dispatch."""
        import time
        cycle_start = time.time()

        sessions = await self.find_inactive_sessions()
        if not sessions:
            log.info("🔄 Scan complete — no inactive sessions found")
            return

        # Fetch all session data in parallel
        fetch_tasks = [self.get_session_data(sid) for sid in sessions]
        fetched_data = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        session_data_list = []
        for sid, data in zip(sessions, fetched_data):
            if isinstance(data, Exception):
                log.error(f"❌ Failed to fetch session {sid}: {data}")
                continue
            if data and data.get("messages"):
                session_data_list.append(data)

        if not session_data_list:
            return

        fetched_count = len(session_data_list)
        web_count = sum(1 for d in session_data_list if not self._is_social_session(d["session_id"]))
        social_count = fetched_count - web_count
        with_lead = sum(1 for d in session_data_list if d.get("lead_id"))
        without_lead = fetched_count - with_lead
        total_msgs = sum(d["total_messages"] for d in session_data_list)

        log.info(
            f"📥 Fetched: {fetched_count} sessions "
            f"(Web: {web_count}, Social: {social_count}) | "
            f"With Lead: {with_lead}, Without Lead: {without_lead} | "
            f"Messages: {total_msgs}"
        )

        # ── STEP 1: Batch AI ANALYZE all sessions ──────────────────────────
        try:
            await batch_analyze_sessions(llm, session_data_list, LLM_CONCURRENCY)
        except Exception as e:
            log.error(f"⚠️ Batch analysis failed: {e}. Applying fallbacks...")

        # ── STEP 2: Post-analysis safety + lead creation ───────────────────
        for data in session_data_list:
            sid = data["session_id"]

            # 2a. Ensure summary exists
            if not data.get("summary"):
                if data.get("ai_analysis"):
                    try:
                        parsed = json.loads(data["ai_analysis"])
                        data["summary"] = parsed.get("conversation_summary", "Summary not generated.")
                    except:
                        data["summary"] = "Summary extraction failed."
                else:
                    data["summary"] = "Summary generation failed."

            # 2b. Ensure ai_analysis exists
            if "ai_analysis" not in data or not data["ai_analysis"]:
                data["ai_analysis"] = json.dumps({"error": "Skipped due to batch failure"})

            # Log AI analysis result
            log.info(f"🧠 AI ANALYSIS for {sid}: {data['ai_analysis']}")

            # ── 2c. DETERMINISTIC LEAD CREATION / UPDATE LOGIC ─────────────
            try:
                ai_json = json.loads(data.get("ai_analysis", "{}"))
                user_details = ai_json.get("user_details", {})
                
                # Ensure college_guid is available for course mapping
                if data.get("college_guid"):
                    user_details["college_guid"] = data["college_guid"]

                # Enforce: Score 1 if mandatory lead info is missing (MANDATORY RULE)
                # Creation requirement: Name AND (Phone OR Email)
                has_name = bool(user_details.get("firstname")) or bool(user_details.get("name"))
                has_phone = bool(user_details.get("phone"))
                has_email = bool(user_details.get("email"))

                if not has_name or not (has_phone or has_email):
                    user_details["lead_score"] = "1"
                else:
                    raw_score = user_details.get("lead_score")
                    try:
                        score_val = int(raw_score) if raw_score else 1
                        user_details["lead_score"] = str(max(score_val, 1))
                    except (ValueError, TypeError):
                        user_details["lead_score"] = "1"

                # ── Channel and Sender Identification ──
                channel_name, engagement_source, lead_source_val = self.determine_source(sid)
                insta_sender_id = None
                fb_sender_id = None
                if ":" in sid:
                    parts = sid.split(":")
                    if len(parts) >= 2:
                        # Extract the actual ID (middle part if date exists, else second part)
                        # Format is usually 'instagram:ID:DATE' or 'instagram:ID'
                        extracted_id = parts[1] 
                        
                        if channel_name == "Instagram":
                            insta_sender_id = extracted_id
                        elif channel_name == "Facebook":
                            fb_sender_id = extracted_id
                
                if insta_sender_id or fb_sender_id:
                    log.info(f"📱 Social Media Session: Channel={channel_name}, InstaID={insta_sender_id}, FBID={fb_sender_id}")

                # Lookup criteria: need phone, email, or sender_id
                can_lookup = has_phone or has_email or bool(insta_sender_id) or bool(fb_sender_id)

                # ── PRIORITY 1: Has contact info or Sender ID → search by sender_id/name+phone/email ──
                if can_lookup:
                    if data.get("lead_id"):
                        # lead_id already known → update with AI-extracted details
                        cached_lead_data = data.get("existing_lead_data")
                        log.info(f"📌 LEAD UPDATE: Updating existing lead {data['lead_id']} for {sid}")
                        await update_existing_lead(
                            dataverse, data["lead_id"], user_details,
                            data.get("summary", ""),
                            cached_lead_data=cached_lead_data
                        )
                    else:
                        # No lead_id → search Dataverse by sender_id/name+phone/email
                        log.info(f"🕵️ LEAD CHECK: Checking Dataverse for {sid}...")

                        check_result = await check_lead(
                            dataverse,
                            firstname=user_details.get("firstname") if has_name else None,
                            phone=user_details.get("phone") if has_phone else None,
                            email=user_details.get("email") if has_email else None,
                            insta_sender_id=insta_sender_id,
                            fb_sender_id=fb_sender_id
                        )

                        if check_result.get("status") == "success":
                            lead_id = check_result["lead_id"]
                            log.info(f"♻️ FOUND: Existing lead {lead_id} for {sid}")
                            await update_existing_lead(
                                dataverse, lead_id, user_details,
                                data.get("summary", ""),
                                cached_lead_data=check_result
                            )
                            data["lead_id"] = lead_id
                            data["lead_name"] = check_result.get("lead_name")
                        else:
                            log.info(f"✅ CREATING new lead for {sid}")
                            new_lead_id = await create_new_lead(
                                dataverse, user_details, data.get("summary", ""),
                                college_guid=data.get("college_guid"),
                                insta_sender_id=insta_sender_id,
                                fb_sender_id=fb_sender_id,
                                lead_source=lead_source_val
                            )
                            if new_lead_id:
                                data["lead_id"] = new_lead_id
                                data["lead_name"] = user_details.get("name")
                                log.info(f"🆕 Lead created: {new_lead_id} for {sid}")
                            else:
                                log.error(f"❌ Lead creation failed for {sid}")

                # ── PRIORITY 2: No contact info BUT lead_id exists (returning user) ──
                elif data.get("lead_id"):
                    lead_id = data["lead_id"]
                    log.info(f"📌 LEAD UPDATE (no contact info): Fetching existing lead {lead_id} for {sid}")

                    # Fetch existing lead from Dataverse so we have current values
                    try:
                        from dataverse_ops import _custom_get
                        existing = await _custom_get(
                            dataverse,
                            f"zx_leads({lead_id})?$select=zx_leadid,zx_firstname,zx_lastname,"
                            f"zx_emailid,zx_mobilenumber,zx_city,zx_highestqualification,"
                            f"zx_undergraduatecourse,zx_graduationyear,zx_thpercentage,zx_th,"
                            f"zx_leadscore,zx_priority,zx_leadtype,"
                            f"_zx_interestedcourse_value,_zx_college_value"
                        )
                        cached_from_dv = {
                            "lead_id": existing.get("zx_leadid"),
                            "first_name": existing.get("zx_firstname"),
                            "last_name": existing.get("zx_lastname"),
                            "email": existing.get("zx_emailid"),
                            "phone": existing.get("zx_mobilenumber"),
                            "city": existing.get("zx_city"),
                            "lead_score": existing.get("zx_leadscore"),
                        }
                        log.info(f"📋 Fetched existing lead data for anti-blank-override: {lead_id}")
                    except Exception as fetch_err:
                        log.warning(f"⚠️ Could not fetch existing lead {lead_id}: {fetch_err}")
                        cached_from_dv = None

                    # Update with anti-blank-override — only summary/context will change
                    # since user_details has no phone/email, should_update() blocks nulls
                    await update_existing_lead(
                        dataverse, lead_id, user_details,
                        data.get("summary", ""),
                        cached_lead_data=cached_from_dv
                    )
                    log.info(f"✅ Lead {lead_id} updated with chat summary for {sid}")

                # ── PRIORITY 3: No lead_id AND no contact info → skip ──
                else:
                    log.info(f"⏭️ No lead_id and no phone/email for {sid}. Skipping lead creation.")

                if data.get("lead_id") and user_details.get("academic_history"):
                    await create_or_update_academic_history(
                        dataverse, data["lead_id"], user_details["academic_history"]
                    )

                # ── STEP 2d-2: PROCESS ENTRANCE EXAMS (if lead exists) ─────
                if data.get("lead_id") and user_details.get("entrance_exams"):
                    await create_or_update_lead_exams(
                        dataverse, data["lead_id"], user_details["entrance_exams"]
                    )

                # ── STEP 2e: HANDLE CAMPUS VISIT SCHEDULING ───────────────────
                if data.get("lead_id"):
                    await handle_campus_visit(
                        dataverse_client=dataverse, 
                        lead_id=data["lead_id"], 
                        user_details=user_details,
                        lead_name=data.get("lead_name") or user_details.get("name"),
                        summary=ai_json.get("conversation_summary")
                    )

                # ── STEP 2f: AUTOMATED BROCHURE EMAIL ───────────────────────
                if has_email:
                    log.info(f"✉️ [AUTO-EMAIL] Triggering automated brochure for {user_details.get('email')} ({sid})")
                    # No await here to avoid blocking archival loop? 
                    # Actually, we are in a loop, better to await or gather?
                    # Since we want it fixed code wise, we can await it.
                    await send_brochure_email(
                        dataverse_client=dataverse,
                        to_email=user_details.get("email"),
                        user_name=user_details.get("name") or user_details.get("firstname"),
                        course_name=user_details.get("interested_course"),
                        college_guid=data.get("college_guid"),
                        college_name=data.get("college_name"),
                        trial_id=data.get("trial_user_id")
                    )

            except Exception as e:
                log.warning(f"⚠️ Lead post-processing failed for {sid}: {e}")

        # ── STEP 3: Enrich with source info ────────────────────────────────
        for data in session_data_list:
            source_name, engagement_source, lead_source_val = self.determine_source(data["session_id"])
            data["source"] = source_name
            data["engagement_source"] = engagement_source
            data["lead_source"] = lead_source_val

        # ── STEP 4: Batch Archive to Postgres (chunked) ───────────────────
        pg_results = await batch_archive_to_postgres(postgres, session_data_list, POSTGRES_CHUNK_SIZE)
        pg_ok = sum(1 for r in pg_results if r.get("success"))
        pg_failed_sids = {r["sid"] for r in pg_results if not r.get("success")}

        # ── STEP 4.5: Flush trial message counts ──────────────────────────
        flushed_trials = set()
        for data in session_data_list:
            if data["session_id"] not in pg_failed_sids and data.get("trial_user_id"):
                tid = data["trial_user_id"]
                if tid not in flushed_trials:
                    await flush_trial_message_count(postgres, self.redis, tid)
                    flushed_trials.add(tid)

        # ── STEP 5: Archive to Dataverse (parallel, PG success only) ──────
        dv_tasks = []
        successful_sessions = [d for d in session_data_list if d["session_id"] not in pg_failed_sids]

        for data in successful_sessions:
            dv_tasks.append(self._archive_to_dataverse_and_cleanup(data))

        dv_results = await asyncio.gather(*dv_tasks, return_exceptions=True)
        dv_ok = sum(1 for r in dv_results if r is True)

        # Aggregate results
        leads_created = sum(1 for d in session_data_list if d.get("lead_id") and d["session_id"] not in pg_failed_sids)
        failed = fetched_count - pg_ok
        duration = round(time.time() - cycle_start, 1)
        log.info(
            f"✅ Archived: {pg_ok}/{fetched_count} | "
            f"Postgres: {pg_ok} | Dataverse: {dv_ok} | "
            f"Leads: {leads_created} | "
            f"Failed: {failed} | Duration: {duration}s"
        )

        # Log failure details
        for r in pg_results:
            if r.get("error"):
                log.error(f"❌ FAILED: {r['sid']} | Reason: {r['error']}")

    async def run_continuously(self):
        log.info(f"🚀 Archive worker started (Interval: {WORKER_INTERVAL_SECONDS}s)")
        log.info(f"📅 Social Sync Schedule: {SOCIAL_SYNC_CRON} (Buffer: {SOCIAL_SAFETY_BUFFER_MINUTES}m)")
        while not self.shutdown_event.is_set():
            await self.run_archive_cycle()
            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(), timeout=WORKER_INTERVAL_SECONDS
                )
            except asyncio.TimeoutError:
                pass
        log.info("Graceful shutdown complete")


if __name__ == "__main__":
    try:
        validate_environment()
        asyncio.run(ArchiveWorker().run_continuously())
    except ValueError as e:
        log.error(f"❌ Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Shutdown requested by user")
    except Exception as e:
        log.error(f"❌ Fatal error: {e}")
        sys.exit(1)