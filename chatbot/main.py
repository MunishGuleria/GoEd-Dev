from fastapi import FastAPI, HTTPException, Request, Depends, status, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import AsyncGenerator,Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel
import logging
import asyncio
import os  
from datetime import datetime, timezone
 
 
from agent import process_query
from onedrive_excel import append_to_excel
from client.memory_manager import RedisMessageManager, RedisConnectionPool
from client.whatsapp_connection import (
    verify_webhook,
    parse_webhook_payload,
    get_session_id,
    get_lead_id_from_phone,
    mark_as_read,
    send_whatsapp_message,
    send_typing_indicator,
    get_previous_summary_from_redis
)

from client import facebook_connection as fb
from client import instagram_connection as ig
from client.trial_validator import (
    validate_trial_user,
    TrialPostgresPool,
    REJECTION_MESSAGES,
    is_trial_enabled,
    increment_trial_message_count,
    flush_message_count_to_postgres,
)
 
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

# ==================== AUTHENTICATION ====================

from client.config import ADMIN_API_KEY

API_KEY_NAME = "X-Admin-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_admin_api_key(api_key: str = Security(api_key_header)):
    """Verify the admin API key from headers."""
    if not ADMIN_API_KEY:
        # If no key is configured, block all admin requests for safety
        logger.error("❌ ADMIN_API_KEY not configured in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication not configured"
        )
    
    if api_key != ADMIN_API_KEY:
        logger.warning(f"🔐 Unauthorized admin access attempt with key: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Admin API Key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    return api_key
 
 
# ==================== LIFESPAN ====================

async def instagram_token_refresh_loop():
    """Background task to periodically check and refresh Instagram token."""
    while True:
        try:
            await ig.refresh_token_if_needed()
        except Exception as e:
            logger.error(f"Instagram token refresh loop error: {e}")
        
        # Check every 24 hours
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup/shutdown."""
    logger.info("🚀 Starting FastAPI application...")
    
    # Initialize Trial Validator PostgreSQL pool (only if trial is enabled)
    if is_trial_enabled():
        try:
            await TrialPostgresPool.get_pool()
        except Exception as e:
            logger.warning(f"⚠️ Trial Validator PG pool init failed: {e}")
    else:
        logger.info("⏭️ Trial validation disabled — skipping PG pool init")
    
    # Check Instagram token on startup
    try:
        await ig.refresh_token_if_needed()
    except Exception as e:
        logger.warning(f"Could not check Instagram token: {e}")
    
    # Start background refresh task
    refresh_task = asyncio.create_task(instagram_token_refresh_loop())
    logger.info("📅 Instagram token refresh scheduler started (checks every 24h)")
    
    yield
    
    # Cleanup
    refresh_task.cancel()
    if is_trial_enabled():
        await TrialPostgresPool.close()
    RedisConnectionPool.close()
    logger.info("🛑 Application shutdown complete")
 
 
# ==================== APP SETUP ====================
 
app = FastAPI(lifespan=lifespan)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
# ==================== REQUEST MODELS ====================
 
class SessionInitRequest(BaseModel):
    session_id: str
    lead_id: Optional[str] = None
    trial_user_id: Optional[str] = None  # Trial user UUID from frontend
 
class ChatRequest(BaseModel):
    """Chat request model."""
    query: str
    session_id: str
    trial_user_id: Optional[str] = None  # Passed by frontend so /chat can re-validate if Redis is cleared


class FormSubmitRequest(BaseModel):
    """
    Request model for the form submission endpoint.

    Fields:
        sheet     — Which Excel to target: "broadcast", "aiwebinar", or "contact"
        name      — Full name of the person.
        number    — Phone/contact number.

    Additional fields (for "aiwebinar" or "contact" sheet):
        email     — Email address.
        org       — Organization / University name / Institute.
        role      — Role (e.g., director, counsellor).
        questions — Specific questions (optional).
    """
    sheet: str                           # "broadcast", "aiwebinar", or "contact"
    name: str
    number: str

    # ── AI Webinar specific fields (optional for broadcast) ──────
    email: Optional[str] = None
    org: Optional[str] = None
    role: Optional[str] = None
    questions: Optional[str] = None


# ==================== BACKGROUND COURSE FETCHER ====================

COLLEGE_COURSES_TTL = 86400  # 24 hours cache

async def _fetch_college_courses_background(session_id: str, college_guid: str):
    """
    Background task: fetch college info + courses from Dataverse and cache in Redis.
    Uses the shared DataverseClient with 3-tier token caching.
    Runs async — does NOT block the session/init response.
    """
    try:
        from client.dataverse_client import dataverse_client

        r = RedisConnectionPool.get_client()

        # Check cache first — avoid Dataverse call if already fetched for this college
        cache_key = f"college_courses:{college_guid}"
        cached = r.get(cache_key)
        if cached:
            logger.info(f"📦 College courses already cached for {college_guid}, skipping Dataverse fetch")
            # Point this session to the cached data
            r.set(f"session_courses:{session_id}", college_guid, ex=COLLEGE_COURSES_TTL)
            return

        if not dataverse_client.is_configured():
            logger.info(f"⏭️ Dataverse credentials not configured — skipping course fetch")
            return

        # 1. Fetch college info
        college_name = "Unknown College"
        try:
            college_data = await dataverse_client.get(
                f"zx_colleges({college_guid})?$select=zx_name,zx_collegeid"
            )
            college_name = college_data.get("zx_name", "Unknown College")
            logger.info(f"🏫 Fetched college: {college_name} ({college_guid})")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch college {college_guid}: {e}")

        # 2. Fetch courses linked to this college
        courses = []
        try:
            courses_data = await dataverse_client.get(
                f"zx_courses?$filter=_zx_collegeid_value eq {college_guid}&$select=zx_name,zx_courseid"
            )
            for course in courses_data.get("value", []):
                courses.append({
                    "name": course.get("zx_name", ""),
                    "guid": course.get("zx_courseid", "")
                })
            logger.info(f"📚 Fetched {len(courses)} courses for college {college_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch courses for {college_guid}: {e}")

        # 3. Fetch seat availability for this college
        seats = []
        try:
            # zx_College in zx_seatavailabilities is a string field matching the college name
            escaped_college = college_name.replace("'", "''")
            seats_data = await dataverse_client.get(
                f"zx_seatavailabilities?$filter=zx_College eq '{escaped_college}'"
                f"&$select=zx_course,zx_branch,zx_category,zx_totalseats,zx_seatfilled,zx_remainingseats"
            )
            for s in seats_data.get("value", []):
                seats.append({
                    "course": s.get("zx_course", ""),
                    "branch": s.get("zx_branch", ""),
                    "category": s.get("zx_category", ""),
                    "total": s.get("zx_totalseats"),
                    "filled": s.get("zx_seatfilled"),
                    "remaining": s.get("zx_remainingseats")
                })
            logger.info(f"💺 Fetched {len(seats)} seat availability records for {college_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch seat availability for {college_name}: {e}")

        # 4. Store in Redis (cached by college_guid)
        result = json.dumps({
            "college_name": college_name,
            "college_guid": college_guid,
            "courses": courses,
            "seats": seats
        })
        r.set(cache_key, result, ex=COLLEGE_COURSES_TTL)
        # Point this session to the cached data
        r.set(f"session_courses:{session_id}", college_guid, ex=COLLEGE_COURSES_TTL)

        course_names = [c["name"] for c in courses]
        logger.info(f"✅ Cached {len(courses)} courses and {len(seats)} seat records for {college_name}")

    except Exception as e:
        logger.error(f"❌ Background course fetch failed for {college_guid}: {e}")
 
 
# ==================== CORE ENDPOINTS ====================
 
 
@app.post("/session/init")
async def init_session(request: SessionInitRequest):
    """
    Initializes a new session. 
    Simplified: No longer accepts or validates lead_id from the frontend.
    The AI will identify users via check_lead tool during the chat.
    """
    try:
        manager = RedisMessageManager(request.session_id)

        now = datetime.now(timezone.utc).isoformat()
        manager.redis.set(f"last_activity:{request.session_id}", now)
        manager.redis.set(f"session_initialized:{request.session_id}", "true")

        # ── Trial validation (web channel) ──────────────────────────────────
        trial_valid = False
        trial_status_reason = "not_found"
        
        if is_trial_enabled() and request.trial_user_id:
            trial_result = await validate_trial_user("web", request.trial_user_id, manager.redis)
            trial_status_reason = trial_result.status
            if trial_result.status == "valid":
                trial_valid = True
                manager.redis.set(f"trial_user_id:{request.session_id}", request.trial_user_id)
                if trial_result.trial_type:
                    manager.redis.set(f"trial_type:{request.session_id}", trial_result.trial_type)
                if trial_result.metadata:
                    manager.redis.set(f"trial_metadata:{request.session_id}", json.dumps(trial_result.metadata))
                
                # Fire background course fetch
                meta = trial_result.metadata
                if isinstance(meta, str):
                    try: meta = json.loads(meta)
                    except: meta = {}
                
                if isinstance(meta, dict):
                    college_guid = meta.get("dataverse_college_guid")
                    if college_guid:
                        asyncio.create_task(_fetch_college_courses_background(request.session_id, college_guid))
                        logger.info(f"🔄 Background course fetch started for {college_guid}")

                # Store message quota
                if trial_result.message_limit is not None:
                    manager.redis.set(f"trial_msg_limit:{request.session_id}", str(trial_result.message_limit))
                if trial_result.messages_used is not None:
                    manager.redis.set(f"trial_msg_used:{request.session_id}", str(trial_result.messages_used))
                
                logger.info(f"✅ Trial validated: {request.trial_user_id}")

        # Store trial status
        manager.redis.set(f"trial_status:{request.session_id}", "valid" if trial_valid or not is_trial_enabled() else "invalid")
        manager.redis.set(f"trial_status_reason:{request.session_id}", trial_status_reason)

        return {
            "status": "success",
            "message": "Session initialized",
            "trial_valid": trial_valid or not is_trial_enabled()
        }

    except Exception as e:
        logger.error(f"Failed to init session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to init session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Check if a session is still active in Redis.
   
    IMPROVED LOGIC:
    - Check if session was ever initialized (has session_initialized flag OR messages)
    - If never initialized → expired = False (brand new session)
    - If was initialized but data gone → expired = True (archived session)
    - If has data → expired = False (active session)
    """
    try:
        manager = RedisMessageManager(session_id)
       
        # Check if activity tracking exists
        has_activity = manager.redis.exists(f"last_activity:{session_id}")
       
        # Check if there are ANY messages (using correct key format)
        message_count = manager.redis.llen(f"messages:list:{session_id}")
       
        # Check if lead_id exists
        has_lead_id = manager.redis.exists(f"lead_id:{session_id}")
       
        # Check if session was ever initialized
        was_initialized = manager.redis.exists(f"session_initialized:{session_id}")
       
        # Check if session has ANY data in Redis
        session_has_data = has_activity or message_count > 0 or has_lead_id or was_initialized
       
        if not session_has_data:
            # No data in Redis = new or fully expired session
            logger.info(f"✨ Session {session_id} has no Redis data")
            expired = False
            exists = False
        else:
            # Session has data in Redis
            if has_activity and (message_count > 0 or was_initialized):
                # Active session
                logger.info(f"✅ Session {session_id} active (has_activity={has_activity}, messages={message_count})")
                expired = False
                exists = True
            else:
                # Partial data (edge case) - treat as expired if no activity
                logger.warning(f"⚠️ Session {session_id} has partial data (activity={has_activity}, messages={message_count})")
                expired = not has_activity
                exists = True
       
        return {
            "session_id": session_id,
            "expired": expired,
            "exists": exists
        }
    except Exception as e:
        logger.error(f"Error checking session status: {e}")
        # On error, assume session is valid to prevent false expiry
        return {"session_id": session_id, "expired": False, "exists": False}
 
 
@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Stream agent response with Redis session storage.
    Marks session as initialized on first message.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
 
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
 
    # Mark session as initialized when first message is sent
    try:
        manager = RedisMessageManager(request.session_id)
        manager.redis.set(f"session_initialized:{request.session_id}", "true")
    except Exception as e:
        logger.warning(f"Could not mark session as initialized: {e}")
 
    # ── Trial validation gatekeeper (web channel) ──────────────────────
    trial_user_id_for_count = None  # Track for message counting
    if is_trial_enabled():
        try:
            # STRICT CHECK: Ensure frontend is actively sending the trial_id on EVERY chat message
            if not request.trial_user_id:
                logger.warning(f"🚫 Chat blocked — Frontend omitted trial_user_id in ChatRequest for session {request.session_id}")
                trial_status = "invalid"
                rejection_reason = "not_found"
                manager.redis.set(f"trial_status:{request.session_id}", "invalid")
                manager.redis.set(f"trial_status_reason:{request.session_id}", "not_found")
            else:
                trial_status = manager.redis.get(f"trial_status:{request.session_id}")
                
                # Also check message limit (live count from Redis)
                trial_user_id_for_count = manager.redis.get(f"trial_user_id:{request.session_id}")
                if trial_user_id_for_count and isinstance(trial_user_id_for_count, bytes):
                    trial_user_id_for_count = trial_user_id_for_count.decode('utf-8')
                
                # ── FALLBACK: Redis cleared OR Trial ID changed → re-validate against PostgreSQL ──
                # If trial_status is missing, OR if the frontend explicitly sends a
                # trial_user_id that differs from the one cached in Redis (meaning they modified
                # the widget HTML but kept their old browser session), we MUST revalidate.
                if request.trial_user_id and (trial_status is None or request.trial_user_id != trial_user_id_for_count):
                    logger.info(
                        f"🔄 Trial re-validation triggered for session {request.session_id} "
                        f"(Cached ID: {trial_user_id_for_count}, Requested ID: {request.trial_user_id})"
                    )
                    trial_result = await validate_trial_user("web", request.trial_user_id, manager.redis)
                    
                    if trial_result.status == "valid":
                        # Re-populate Redis with the validated trial data
                        trial_status = "valid"
                        trial_user_id_for_count = request.trial_user_id
                        manager.redis.set(f"trial_status:{request.session_id}", "valid")
                        manager.redis.set(f"trial_status_reason:{request.session_id}", "valid")
                        manager.redis.set(f"trial_user_id:{request.session_id}", request.trial_user_id)
                        if trial_result.trial_type:
                            manager.redis.set(f"trial_type:{request.session_id}", trial_result.trial_type)
                        if trial_result.message_limit is not None:
                            manager.redis.set(f"trial_msg_limit:{request.session_id}", str(trial_result.message_limit))
                        if trial_result.messages_used is not None:
                            manager.redis.set(f"trial_msg_used:{request.session_id}", str(trial_result.messages_used))
                        if trial_result.metadata:
                            manager.redis.set(f"trial_metadata:{request.session_id}", json.dumps(trial_result.metadata))
                            
                            # CRITICAL FIX: Also re-trigger course fetch to update session_courses mapping
                            meta = trial_result.metadata
                            if isinstance(meta, dict):
                                college_guid = meta.get("dataverse_college_guid")
                                if college_guid:
                                    asyncio.create_task(_fetch_college_courses_background(request.session_id, college_guid))
                                    logger.info(f"🔄 Background course fetch re-triggered for {college_guid} during session re-validation")
                        # Also re-initialize session markers
                        now = datetime.now(timezone.utc).isoformat()
                        manager.redis.set(f"last_activity:{request.session_id}", now)
                        manager.redis.set(f"session_initialized:{request.session_id}", "true")
                        logger.info(f"✅ Re-validated trial from PostgreSQL — session {request.session_id} is valid")
                    else:
                        trial_status = trial_result.status
                        manager.redis.set(f"trial_status:{request.session_id}", trial_result.status)
                        manager.redis.set(f"trial_status_reason:{request.session_id}", trial_result.status)
                        if trial_result.status == "limit_reached":
                            trial_user_id_for_count = request.trial_user_id
                            manager.redis.set(f"trial_user_id:{request.session_id}", request.trial_user_id)
                            if trial_result.message_limit is not None:
                                manager.redis.set(f"trial_msg_limit:{request.session_id}", str(trial_result.message_limit))
                        logger.info(f"🚫 Re-validated trial from PostgreSQL — status: {trial_result.status}")
            
            if trial_user_id_for_count and trial_status == "valid":
                # Check globally synchronized live message count
                data_key = f"trial_data:{trial_user_id_for_count}"
                msg_limit_raw = manager.redis.hget(data_key, "message_limit")
                msg_used_raw = manager.redis.hget(data_key, "messages_used")
                
                # Fallback to older session snapshots if global hash expired
                if msg_limit_raw is None:
                    msg_limit_raw = manager.redis.get(f"trial_msg_limit:{request.session_id}")
                if msg_used_raw is None:
                    msg_used_raw = manager.redis.get(f"trial_msg_used:{request.session_id}")
                
                live_count_raw = manager.redis.get(f"trial_msg_count:{trial_user_id_for_count}")
                
                msg_limit = int(msg_limit_raw) if msg_limit_raw else 2500
                msg_used = int(msg_used_raw) if msg_used_raw else 0
                live_count = int(live_count_raw) if live_count_raw else 0
                total = msg_used + live_count
                
                if total >= msg_limit:
                    trial_status = "limit_reached"
                    manager.redis.set(f"trial_status:{request.session_id}", "limit_reached")
                    manager.redis.set(f"trial_status_reason:{request.session_id}", "limit_reached")
            
            if trial_status != "valid":
                # Get specific internal reason
                rejection_reason = manager.redis.get(f"trial_status_reason:{request.session_id}")
                if not rejection_reason:
                    rejection_reason = "not_found"
                
                logger.info(f"🚫 Chat blocked — trial not valid ({rejection_reason}) for session {request.session_id}")
                async def rejection_stream():
                    msg = REJECTION_MESSAGES.get(rejection_reason, REJECTION_MESSAGES.get("not_found", "Trial not valid."))
                    # Format the limit_reached message with actual limit
                    if rejection_reason == "limit_reached":
                        msg_limit_raw = manager.redis.get(f"trial_msg_limit:{request.session_id}")
                        limit = int(msg_limit_raw) if msg_limit_raw else 2500
                        msg = msg.format(limit=limit)
                    yield f"{json.dumps({'type': 'token', 'content': msg})}\n"
                    yield f"{json.dumps({'type': 'end'})}\n"
                return StreamingResponse(rejection_stream(), media_type="application/x-ndjson")
        except Exception as e:
            logger.warning(f"Trial check error (allowing through): {e}")
 
    async def event_generator() -> AsyncGenerator:
        try:
            async for chunk in process_query(request.query, request.session_id):
                yield f"{json.dumps(chunk)}\n"
 
        except asyncio.CancelledError:
            logger.warning(
                f"⚠️ Client disconnected during stream | session={request.session_id}"
            )
            return
 
        except Exception as e:
            logger.error(
                f"Streaming error for session {request.session_id}: {e}",
                exc_info=True
            )
            yield f"{json.dumps({'type': 'error', 'error': str(e)})}\n"
 
        finally:
            # ── Increment message count and flush to PostgreSQL ──
            if is_trial_enabled() and trial_user_id_for_count:
                try:
                    increment_trial_message_count(manager.redis, trial_user_id_for_count)
                    # NOTE: Removed flush_message_count_to_postgres on every message per user request
                except Exception as e:
                    logger.warning(f"⚠️ Message count update error: {e}")
 
 
    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson"
    )
 
 
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        manager = RedisMessageManager("health-check")
        manager.redis.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": str(e)}


# ==================== ADMIN ENDPOINTS ====================


class InvalidatePromptRequest(BaseModel):
    """Request model for prompt cache invalidation."""
    prompt_id: str


@app.post("/admin/invalidate-prompt-cache", dependencies=[Depends(verify_admin_api_key)])
async def invalidate_prompt_cache(request: InvalidatePromptRequest):
    """
    Invalidate the in-memory prompt cache for a specific prompt_id.
    
    Call this after updating a prompt in PostgreSQL so the chatbot picks up
    the new version WITHOUT restarting the server.
    
    This endpoint lives in the chatbot server (internal-only, not shared externally).
    
    Usage:
        curl -X POST https://your-chatbot-server/admin/invalidate-prompt-cache \
             -H "Content-Type: application/json" \
             -d '{"prompt_id": "Prompt-6"}'
    """
    prompt_id = request.prompt_id.strip()
    if not prompt_id:
        raise HTTPException(status_code=400, detail="prompt_id is required")
    
    try:
        from agent import _agent_instances, _channel_prompts, _channel_tools
        from client.channel_config import CHANNEL_CONFIGS
        
        # Find and clear all channels that use this prompt_id
        cleared_channels = []
        for ch_name, ch_config in CHANNEL_CONFIGS.items():
            if ch_config.prompt_id == prompt_id:
                _agent_instances.pop(ch_name, None)
                _channel_prompts.pop(ch_name, None)
                _channel_tools.pop(ch_name, None)
                cleared_channels.append(ch_name)
                logger.info(f"🔄 Cleared cached agent for channel='{ch_name}'")
        
        # Also set Redis flag in case multiple chatbot pods are running
        # Other pods will detect this flag on their next request
        redis = RedisConnectionPool.get_client()
        redis.setex(f"prompt_invalidated:{prompt_id}", 300, "true")
        
        logger.info(f"🔄 Prompt cache invalidated for prompt_id='{prompt_id}'. Cleared channels: {cleared_channels}")
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "cleared_channels": cleared_channels,
            "message": f"Cache cleared. Affected channels will re-fetch '{prompt_id}' from PostgreSQL on the next request."
        }
    except Exception as e:
        logger.error(f"❌ Failed to invalidate prompt cache for {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FORM SUBMISSION ENDPOINT ====================
#
#   POST /submit-form
#
#   Accepts { sheet, name, number, ... } from a React frontend form.
#   Routes to the correct Excel file based on the "sheet" field:
#
#   sheet = "broadcast"  →  BROADCAST Excel (Name | Mobile | Date | Status)
#   sheet = "aiwebinar"  →  AIWEBINAR Excel (Full Name | Business Email | Phone Number |
#                                             Org / University | Role | Specific Questions)
#   sheet = "contact"    →  CONTACT Excel (Name | Email | Phone | Institute | Role | Questions)
#
# ==================================================================

# Allowed sheet names → mapped to target prefixes
ALLOWED_SHEETS = {
    "broadcast": "BROADCAST",
    "aiwebinar": "AIWEBINAR",
    "contact": "CONTACT",
}


@app.post("/submit-form")
async def submit_form(request: FormSubmitRequest):
    """
    Receive form data and append it to the correct Excel sheet
    on OneDrive based on the 'sheet' field.

    Supported sheets:
      - "broadcast"  →  Columns: Name | Mobile | Date | Status
      - "aiwebinar"  →  Columns: Full Name | Business Email | Phone Number |
                                  Org / University | Role | Specific Questions
      - "contact"    →  Columns: Name | Email | Phone | Institute | Role | Questions

    Request Body (broadcast):
        {
            "sheet":  "broadcast",
            "name":   "Munish Kumar",
            "number": "9876543210"
        }

    Request Body (aiwebinar):
        {
            "sheet":     "aiwebinar",
            "name":      "Munish Kumar",
            "email":     "munish@zoxima.com",
            "number":    "9876543210",
            "org":       "Zoxima Solutions",
            "role":      "Director",
            "questions": "How does AI help in admissions?"
        }

    Request Body (contact):
        {
            "sheet":     "contact",
            "name":      "Roshni",
            "email":     "roshni@example.com",
            "number":    "1234567890",
            "org":       "Example Institute",
            "role":      "Developer",
            "questions": "Can I connect?"
        }
    """

    # ── Validate sheet name ───────────────────────────────────────────

    sheet_key = request.sheet.strip().lower()

    if sheet_key not in ALLOWED_SHEETS:
        raise HTTPException(
            status_code = 400,
            detail      = f"Invalid sheet: '{request.sheet}'. Allowed: {list(ALLOWED_SHEETS.keys())}",
        )

    target = ALLOWED_SHEETS[sheet_key]


    # ── Validate common inputs ───────────────────────────────────────

    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    if not request.number.strip():
        raise HTTPException(status_code=400, detail="Number cannot be empty")


    # ── Generate the current date (IST) ──────────────────────────────

    from datetime import timedelta

    ist_offset  = timedelta(hours=5, minutes=30)
    now_utc     = datetime.now(timezone.utc)
    now_ist     = now_utc + ist_offset
    date_string = now_ist.strftime("%Y-%m-%d %H:%M:%S")

    logger.info(
        f"📝 [{target}] Form submission received: "
        f"name={request.name}, number={request.number}, date={date_string}"
    )


    # ── Build row values based on target ──────────────────────────────

    if target == "BROADCAST":
        #
        #  BROADCAST Excel columns:
        #    Name | Mobile | Date | Status
        #
        row_values = [
            request.name.strip(),
            request.number.strip(),
            date_string,
            "Pending",                  # ← Default status
        ]

        response_data = {
            "name":   request.name.strip(),
            "number": request.number.strip(),
            "date":   date_string,
            "status": "Pending",
        }


    elif target == "AIWEBINAR":
        #
        #  AIWEBINAR Excel columns:
        #    Full Name | Business Email | Phone Number |
        #    Org / University | Role | Specific Questions (Optional)
        #
        row_values = [
            request.name.strip(),
            (request.email or "").strip(),
            request.number.strip(),
            (request.org or "").strip(),
            (request.role or "").strip(),
            (request.questions or "").strip(),
        ]

        response_data = {
            "name":      request.name.strip(),
            "email":     (request.email or "").strip(),
            "number":    request.number.strip(),
            "org":       (request.org or "").strip(),
            "role":      (request.role or "").strip(),
            "questions": (request.questions or "").strip(),
        }

    elif target == "CONTACT":
        #
        #  CONTACT Excel columns:
        #    Name | Email | Phone | Institute | Role | Questions
        #
        row_values = [
            request.name.strip(),
            (request.email or "").strip(),
            request.number.strip(),
            (request.org or "").strip(),  # Mapped to 'Institute' in Excel
            (request.role or "").strip(),
            (request.questions or "").strip(),
        ]

        response_data = {
            "name":      request.name.strip(),
            "email":     (request.email or "").strip(),
            "number":    request.number.strip(),
            "institute": (request.org or "").strip(),
            "role":      (request.role or "").strip(),
            "questions": (request.questions or "").strip(),
        }


    # ── Append row to the target Excel ───────────────────────────────

    result = await append_to_excel(
        target     = target,
        row_values = row_values,
    )


    # ── Return response ──────────────────────────────────────────────

    if result["success"]:

        logger.info(f"✅ [{target}] Form submitted successfully for {request.name}")

        return {
            "status":  "success",
            "message": f"Form submitted to '{sheet_key}' successfully",
            "sheet":   sheet_key,
            "data":    response_data,
        }

    else:

        logger.error(f"❌ [{target}] Form submission failed: {result.get('error')}")

        raise HTTPException(
            status_code = 500,
            detail      = result.get("message", "Failed to submit form"),
        )


# ==================== ANALYTICS ENDPOINTS ====================
 
@app.get("/session/{session_id}/transcript")
async def get_transcript(session_id: str):
    """Get complete conversation history with all messages and summary."""
    try:
        manager = RedisMessageManager(session_id)
        transcript = manager.get_full_transcript()
        summary = manager.redis.get(f"summary:{session_id}")
 
        return {
            "session_id": session_id,
            "messages": transcript,
            "message_count": len(transcript),
            "summary": summary if summary else None
        }
    except Exception as e:
        logger.error(f"Error fetching transcript for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@app.get("/session/{session_id}/transcript/formatted")
async def get_transcript_formatted(session_id: str):
    """Get formatted transcript for display (role | content | tokens)."""
    try:
        manager = RedisMessageManager(session_id)
        formatted = manager.get_transcript_formatted()
        return {
            "session_id": session_id,
            "formatted_transcript": formatted
        }
    except Exception as e:
        logger.error(f"Error fetching formatted transcript for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@app.get("/session/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get session statistics including message counts and token usage."""
    try:
        manager = RedisMessageManager(session_id)
        stats = manager.get_session_stats()
 
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
 
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stats for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear all session data."""
    try:
        manager = RedisMessageManager(session_id)
        manager.clear_session()
        return {
            "status": "success",
            "message": f"Session {session_id} cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
# ==================== WHATSAPP ENDPOINTS ====================

@app.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """
    WhatsApp webhook verification endpoint.
    Meta calls this once when you register the webhook URL.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    success, response = verify_webhook(mode, token, challenge)
    
    if success:
        logger.info(f"✅ WhatsApp webhook verified, returning challenge")
        return int(response)  # Must return challenge as integer
    
    logger.warning(f"❌ WhatsApp webhook verification failed")
    raise HTTPException(status_code=403, detail=response)

# ==================== WHATSAPP BACKGROUND PROCESSING ====================

_user_locks = {}

def get_user_lock(phone: str) -> asyncio.Lock:
    if phone not in _user_locks:
        _user_locks[phone] = asyncio.Lock()
    return _user_locks[phone]

async def process_whatsapp_message_in_background(phone: str, message_text: str, session_id: str, message_id: str):
    """Background task to run the agent and send the WhatsApp response sequentially per user."""
    lock = get_user_lock(phone)
    
    async with lock:
        import time as _time
        _start = _time.monotonic()
        
        full_response = ""
        try:
            async for chunk in process_query(message_text, session_id, channel="whatsapp"):
                if chunk.get("type") == "token":
                    full_response += chunk.get("content", "")
                elif chunk.get("type") == "error":
                    logger.error(f"🤖 [AGENT] Error: {chunk.get('error')}")
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            full_response = "Sorry, I encountered an error."
        
        _elapsed = _time.monotonic() - _start
        logger.info(f"🤖 [AGENT] Done in {_elapsed:.1f}s | response={len(full_response)} chars")
        
        if full_response.strip():
            await send_whatsapp_message(phone, full_response)
        else:
            logger.warning(f"⚠️ [WHATSAPP] Empty response for {phone} — nothing sent!")


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Handle incoming WhatsApp messages.
    Phone number and name are stored in session, agent checks/creates lead via MCP tools.
    """
    try:
        body = await request.json()
        logger.info(f"🟢 [WHATSAPP RAW BODY] {json.dumps(body, indent=2)}")
        parsed = parse_webhook_payload(body)
        
        if not parsed:
            return {"status": "ok"}
        
        phone = parsed["phone"]
        message_text = parsed["message"]
        message_id = parsed["message_id"]
        profile_name = parsed["profile_name"]
        
        logger.info(f"📩 WhatsApp from {phone} ({profile_name}): {message_text[:50]}...")
        
        # ⚡ INSTANT: blue tick + typing dots — we "read" the message, so mark it NOW
        await send_typing_indicator(phone, message_id, typing_on=True)
        
        session_id = get_session_id(phone)
        
        # FIX: Message deduplication to prevent duplicate processing (Meta can retry)
        manager = RedisMessageManager(session_id)
        dedupe_key = f"wa:mid:{message_id}"
        if manager.redis.exists(dedupe_key):
            logger.info(f"⏭️ Skipping duplicate WhatsApp message {message_id}")
            return {"status": "ok"}
        manager.redis.setex(dedupe_key, 3600, "1")  # 1 hour TTL
        
        # Store WhatsApp info in session INCLUDING NAME
        try:
            TTL = 86400 * 2  # 2 days
            
            # Store user info WITH NAME
            manager.redis.hset(f"user_info:{session_id}", mapping={
                "phone": phone,
                "name": profile_name or "WhatsApp User",
                "source": "whatsapp"
            })
            
            # [LEGACY] Optional: Fast Redis check for previous day's context
            # previous_summary = get_previous_summary_from_redis(phone, manager.redis)
            # if previous_summary:
            #     logger.info(f"📜 Loaded previous day's context for {phone}")
            
            # Update activity timestamp
            now = datetime.now(timezone.utc).isoformat()
            manager.redis.setex(f"last_activity:{session_id}", TTL, now)
            manager.redis.setex(f"session_initialized:{session_id}", TTL, "true")
            
            logger.info(f"✅ Stored user info: phone={phone}, name={profile_name}")
            
        except Exception as e:
            logger.warning(f"Session init error: {e}")
        
        # ⚡ Fire-and-forget: process agent in background
        asyncio.create_task(
            process_whatsapp_message_in_background(phone, message_text, session_id, message_id)
        )
        
        # Return 200 OK to Meta IMMEDIATELY so it doesn't retry
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
   
# ==================== FACEBOOK MESSENGER ENDPOINTS ====================

@app.get("/facebook")
async def facebook_verify(request: Request):
    """
    Facebook Messenger webhook verification endpoint.
    Meta calls this once when you register the webhook URL.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    success, response = fb.verify_webhook(mode, token, challenge)
    
    if success:
        logger.info(f"✅ Facebook webhook verified, returning challenge")
        return int(response)  # Must return challenge as integer
    
    logger.warning(f"❌ Facebook webhook verification failed")
    raise HTTPException(status_code=403, detail=response)



@app.post("/facebook")
async def facebook_webhook(request: Request):
    """
    Handle incoming Facebook Messenger messages.
    Safe version:
    - ignores echoes
    - ignores Page messages
    - only processes real users
    - retry-safe
    
    ✅ FIX: Agent creates real Dataverse lead via MCP tools
    """
    try:
        body = await request.json()
        logger.info(f"🔵 [FACEBOOK RAW BODY] {json.dumps(body, indent=2)}")

        parsed = fb.parse_webhook_payload(body)

        if not parsed:
            return {"status": "ok"}

        sender_id = parsed["sender_id"]
        message_text = parsed["message"]
        message_id = parsed.get("message_id")

        # 🚨 1. Ignore echo messages
        if parsed.get("is_echo"):
            logger.info("🔁 Ignoring Facebook echo message")
            return {"status": "ok"}

        # 🚨 2. Ignore Page → Page or self messages
        if sender_id == fb.FACEBOOK_PAGE_ID:
            logger.info("🛑 Ignoring message sent by Page itself")
            return {"status": "ok"}

        logger.info(f"📩 Facebook from {sender_id}: {message_text[:50]}...")

        #  3. Deduplicate Meta retries
        manager = RedisMessageManager("facebook-dedupe")
        if message_id:
            dedupe_key = f"fb:mid:{message_id}"
            if manager.redis.exists(dedupe_key):
                logger.info("♻️ Duplicate Facebook message ignored")
                return {"status": "ok"}
            manager.redis.setex(dedupe_key, 86400, "1")  # 24h TTL

        # ✅ 4. UX signals ONLY for real users
        await fb.mark_as_seen(sender_id)
        await fb.send_typing_indicator(sender_id, True)

        # 5️⃣ Session handling
        session_id = fb.get_session_id(sender_id)
        trial_user_id_for_count = None

        try:
            manager = RedisMessageManager(session_id)

            lead_id_key = f"lead_id:{session_id}"
            if not manager.redis.exists(lead_id_key):
                # Fetch profile but don't use fallback "Facebook User"
                profile = await fb.get_user_profile(sender_id)
                user_name = profile.get("name") if profile and profile.get("name") else ""

                # Store user info (agent will create lead via MCP)
                manager.redis.hset(
                    f"user_info:{session_id}",
                    mapping={
                        "sender_id": sender_id,
                        "name": user_name,
                        "source": "facebook",
                    },
                )

                logger.info(f"👤 Stored Facebook user info: {user_name or 'no name'} ({sender_id})")

            TTL = 86400 * 2  # 2 days
            now = datetime.now(timezone.utc).isoformat()
            manager.redis.setex(f"last_activity:{session_id}", TTL, now)
            manager.redis.setex(f"session_initialized:{session_id}", TTL, "true")

        except Exception as e:
            logger.warning(f"Could not initialize Facebook session: {e}")

        full_response = ""
        try:
            async for chunk in process_query(
                message_text, session_id, channel="facebook"
            ):
                if chunk.get("type") == "token":
                    full_response += chunk.get("content", "")
        except Exception as e:
            logger.error(f"Agent error for Facebook: {e}", exc_info=True)
            full_response = (
                "Sorry, I encountered an error processing your request."
            )

        await fb.send_typing_indicator(sender_id, False)

        if full_response.strip():
            await fb.send_facebook_message(sender_id, full_response)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Facebook webhook error: {e}", exc_info=True)
        # ALWAYS return 200 to Meta
        return {"status": "ok"}

# ==================== INSTAGRAM ENDPOINTS ====================

@app.get("/instagram")
async def instagram_verify(request: Request):
    """
    Instagram webhook verification endpoint.
    Meta calls this once when you register the webhook URL.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    success, response = ig.verify_webhook(mode, token, challenge)
    
    if success:
        logger.info(f"✅ Instagram webhook verified, returning challenge")
        return int(response)  # Must return challenge as integer
    
    logger.warning(f"❌ Instagram webhook verification failed")
    raise HTTPException(status_code=403, detail=response)


@app.post("/instagram")
async def instagram_webhook(request: Request):
    """
    Handle incoming Instagram DM messages.
    Flow: Parse → Mark Seen → Show Typing → Initialize Session → Process → Reply
    
    ✅ FIX: Agent creates real Dataverse lead via MCP tools (not fake hash-based ID)
    """
    try:
        body = await request.json()
        logger.info(f"🟣 [INSTAGRAM RAW BODY] {json.dumps(body, indent=2)}")

        parsed = ig.parse_webhook_payload(body)
        
        if not parsed:
            return {"status": "ok"}
        
        sender_id = parsed["sender_id"]
        message_text = parsed["message"]
        message_id = parsed.get("message_id")
        
        logger.info(f"📩 Instagram from {sender_id}: {message_text[:50]}...")
        
        # Resolve username from sender_id via Graph API
        profile = await ig.get_user_profile(sender_id)
        user_name = profile.get('name', '') if profile else ''
        ig_username = profile.get('username', '') if profile else ''
        
        # ── Trial validation gatekeeper (COMMENTED OUT FOR INSTAGRAM) ──────────────────────────────────
        trial_user_id_for_count = None
        # if is_trial_enabled():
        #     if ig_username:
        #         redis_client = RedisConnectionPool.get_client()
        #         trial_result = await validate_trial_user("insta", ig_username, redis_client)
        #         
        #         if trial_result.status != "valid":
        #             rejection_msg = REJECTION_MESSAGES.get(trial_result.status, REJECTION_MESSAGES["not_found"])
        #             if trial_result.status == "limit_reached" and trial_result.message_limit:
        #                 rejection_msg = rejection_msg.format(limit=trial_result.message_limit)
        #             logger.info(f"🚫 Instagram trial {trial_result.status} for @{ig_username} — sending rejection")
        #             await ig.send_instagram_message(sender_id, rejection_msg)
        #             return {"status": "ok"}
        #         
        #         # Store trial info for Instagram session
        #         session_id = ig.get_session_id(sender_id)
        #         manager = RedisMessageManager(session_id)
        #         manager.redis.set(f"trial_user_id:{session_id}", trial_result.trial_user_id)
        #         trial_user_id_for_count = trial_result.trial_user_id
        #         if trial_result.trial_type:
        #             manager.redis.set(f"trial_type:{session_id}", trial_result.trial_type)
        #         if trial_result.metadata:
        #             manager.redis.set(f"trial_metadata:{session_id}", json.dumps(trial_result.metadata))
        # 
        #         logger.info(f"✅ Instagram trial valid for @{ig_username} (type={trial_result.trial_type}, msgs={trial_result.messages_used}/{trial_result.message_limit})")
        #     else:
        #         logger.warning(f"⚠️ Could not resolve Instagram username for {sender_id} — skipping trial check")
        
        # Mark message as seen
        await ig.mark_as_seen(sender_id)
        
        # Show typing indicator
        await ig.send_typing_indicator(sender_id, True)
        
        # Get session ID (date-based)
        session_id = ig.get_session_id(sender_id)
        
        # FIX: Message deduplication to prevent duplicate processing (Meta can retry)
        manager = RedisMessageManager(session_id)
        if message_id:
            dedupe_key = f"ig:mid:{message_id}"
            if manager.redis.exists(dedupe_key):
                logger.info(f"⏭️ Skipping duplicate Instagram message {message_id}")
                return {"status": "ok"}
            manager.redis.setex(dedupe_key, 3600, "1")  # 1 hour TTL
        
        # Initialize session
        try:
            lead_id_key = f"lead_id:{session_id}"
            if not manager.redis.exists(lead_id_key):
                # Store user info (agent will create lead via MCP)
                manager.redis.hset(f"user_info:{session_id}", mapping={
                    "sender_id": sender_id,
                    "name": user_name,
                    "username": ig_username,
                    "source": "instagram",
                })
                logger.info(f"👤 Stored Instagram user info: {user_name or 'no name'} (@{ig_username}) ({sender_id})")
                
                # Load previous context if exists
                previous_summary = ig.get_previous_summary_from_redis(sender_id, manager.redis)
                if previous_summary:
                    logger.info(f"📜 Loaded previous day's context for {sender_id}")
            
            TTL = 86400 * 2  # 2 days
            now = datetime.now(timezone.utc).isoformat()
            manager.redis.setex(f"last_activity:{session_id}", TTL, now)
            manager.redis.setex(f"session_initialized:{session_id}", TTL, "true")
            
        except Exception as e:
            logger.warning(f"Could not initialize Instagram session: {e}")
        
        # Get complete response from agent
        full_response = ""
        try:
            async for chunk in process_query(message_text, session_id, channel="instagram"):
                if chunk.get("type") == "token":
                    full_response += chunk.get("content", "")
                    
        except Exception as e:
            logger.error(f"Agent error for Instagram: {e}", exc_info=True)
            full_response = "Sorry, I encountered an error processing your request. Please try again."
        
        # Turn off typing indicator
        await ig.send_typing_indicator(sender_id, False)
        
        # Send response
        if full_response.strip():
            await ig.send_instagram_message(sender_id, full_response)
        else:
            await ig.send_instagram_message(sender_id, "I couldn't generate a response. Please try again.")
        
        # ── Increment message count (COMMENTED OUT FOR INSTAGRAM) ──
        # if is_trial_enabled() and trial_user_id_for_count:
        #     try:
        #         increment_trial_message_count(manager.redis, trial_user_id_for_count)
        #         # NOTE: Removed flush_message_count_to_postgres on every message per user request
        #     except Exception as e:
        #         logger.warning(f"⚠️ Instagram message count update error: {e}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Instagram webhook error: {e}", exc_info=True)
        # FIX: Always return OK to Meta to prevent retries
        return {"status": "ok"}

# ==================== SERVER ====================
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)