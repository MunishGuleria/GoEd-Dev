"""
Trial User Validator

Validates whether an incoming user is a registered trial user
BEFORE any message reaches the LLM. Saves LLM costs and enforces
trial boundaries.

Channels supported:
  - Website:   trial_user_id (UUID) passed from frontend
  - Instagram: username resolved from sender_id via Graph API
  - WhatsApp:  phone number from webhook payload

Caching strategy:
  - Cache ONLY when user IS found (valid or expired)
  - Do NOT cache "not_found" → every message from unknown users
    hits PostgreSQL (so newly added trial users work immediately)
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional
import json
import asyncpg

logger = logging.getLogger(__name__)


# ============================================================
# FEATURE FLAG
# ============================================================

def is_trial_enabled() -> bool:
    """Check if trial validation is enabled via TRIAL_ENABLED env var.
    Defaults to True (trial validation ON) if not set."""
    return os.getenv("TRIAL_ENABLED", "true").lower() in ("true", "1", "yes")


# ============================================================
# RESULT DATA CLASS
# ============================================================

@dataclass
class TrialValidationResult:
    """Result of trial user validation."""
    status: str  # "valid" | "expired" | "not_found" | "limit_reached"
    trial_user_id: Optional[str] = None
    trial_type: Optional[str] = None
    expires_at: Optional[str] = None
    email: Optional[str] = None
    metadata: Optional[dict] = None
    message_limit: Optional[int] = None
    messages_used: Optional[int] = None


# ============================================================
# POSTGRES CONNECTION POOL (Singleton)
# ============================================================

class TrialPostgresPool:
    """Singleton async PostgreSQL connection pool for trial validation."""
    _pool: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool:
            return cls._pool

        async with cls._lock:
            if cls._pool is None:
                logger.info("🔌 Initializing Trial Validator PostgreSQL pool...")
                cls._pool = await asyncpg.create_pool(
                    user=os.getenv("POSTGRES_USER"),
                    password=os.getenv("POSTGRES_PASSWORD"),
                    host=os.getenv("POSTGRES_HOST"),
                    port=os.getenv("POSTGRES_PORT", "5432"),
                    database=os.getenv("POSTGRES_DATABASE"),
                    min_size=1,
                    max_size=3,  # Small pool — only used for trial checks
                    command_timeout=15,
                    max_inactive_connection_lifetime=300,
                    server_settings={
                        "application_name": "chatbot-trial-validator",
                    }
                )
                logger.info("✅ Trial Validator PostgreSQL pool initialized")
            return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("🛑 Trial Validator PostgreSQL pool closed")


# ============================================================
# REDIS CACHE HELPERS
# ============================================================

TRIAL_CACHE_TTL = 86400 * 2  # 2 days


def _cache_trial_data(redis_client, trial_data: dict):
    """
    Cache trial user data in Redis with multiple lookup keys.

    Keys created:
      trial_data:{trial_user_id}       → hash with all trial info
      trial_lookup:web:{trial_user_id} → trial_user_id
      trial_lookup:insta:{insta_id}    → trial_user_id  (if exists)
      trial_lookup:whatsapp:{phone}    → trial_user_id  (if exists)
    """
    trial_user_id = trial_data["trial_user_id"]

    # Store full trial data hash
    data_key = f"trial_data:{trial_user_id}"
    redis_client.hset(data_key, mapping={
        "trial_user_id": trial_user_id,
        "trial_type": trial_data.get("trial_type", ""),
        "expires_at": trial_data.get("expires_at", ""),
        "email": trial_data.get("email", ""),
        "insta_id": trial_data.get("insta_id", ""),
        "whatsapp_id": trial_data.get("whatsapp_id", ""),
        "message_limit": str(trial_data.get("message_limit", 2500)),
        "messages_used": str(trial_data.get("messages_used", 0)),
    })
    redis_client.expire(data_key, TRIAL_CACHE_TTL)

    # Store lookup keys for cross-platform resolution
    # Website lookup
    web_key = f"trial_lookup:web:{trial_user_id}"
    redis_client.setex(web_key, TRIAL_CACHE_TTL, trial_user_id)

    # Instagram lookup (if insta_id exists)
    insta_id = trial_data.get("insta_id")
    if insta_id:
        insta_key = f"trial_lookup:insta:{insta_id.lower()}"
        redis_client.setex(insta_key, TRIAL_CACHE_TTL, trial_user_id)

    # WhatsApp lookup (if whatsapp_id exists)
    whatsapp_id = trial_data.get("whatsapp_id")
    if whatsapp_id:
        wa_key = f"trial_lookup:whatsapp:{whatsapp_id}"
        redis_client.setex(wa_key, TRIAL_CACHE_TTL, trial_user_id)

    # Store metadata (JSON serialized) if exists
    metadata = trial_data.get("metadata")
    if metadata:
        meta_key = f"trial_metadata_cache:{trial_user_id}"
        redis_client.setex(meta_key, TRIAL_CACHE_TTL, json.dumps(metadata))

    logger.info(f"📦 Cached trial data for {trial_user_id} (TTL={TRIAL_CACHE_TTL}s)")


def _check_redis_cache(redis_client, channel: str, identifier: str) -> Optional[TrialValidationResult]:
    """
    Check Redis cache for trial user data.

    Returns:
        TrialValidationResult if found in cache, None if cache miss
    """
    # Build lookup key
    lookup_key = f"trial_lookup:{channel}:{identifier}"
    trial_user_id = redis_client.get(lookup_key)

    if not trial_user_id:
        return None

    # Found lookup → get full data
    data_key = f"trial_data:{trial_user_id}"
    data = redis_client.hgetall(data_key)

    if not data:
        # Lookup key exists but data expired — clean up
        redis_client.delete(lookup_key)
        return None

    # Check expiry
    expires_at_str = data.get("expires_at", "")
    status = _check_expiry(expires_at_str)

    logger.info(f"🔍 Redis cache HIT for {channel}:{identifier} → {status}")

    # Fetch metadata if it exists in cache
    metadata = None
    meta_key = f"trial_metadata_cache:{trial_user_id}"
    meta_raw = redis_client.get(meta_key)
    if meta_raw:
        try:
            metadata = json.loads(meta_raw)
        except (ValueError, json.JSONDecodeError):
            pass

    # Get message quota info
    message_limit = int(data.get("message_limit", 2500))
    messages_used = int(data.get("messages_used", 0))

    # Also check the live Redis counter (incremented during active sessions)
    live_count_raw = redis_client.get(f"trial_msg_count:{trial_user_id}")
    live_count = int(live_count_raw) if live_count_raw else 0
    total_used = messages_used + live_count

    # Override status if limit reached
    if status == "valid" and total_used >= message_limit:
        status = "limit_reached"

    return TrialValidationResult(
        status=status,
        trial_user_id=trial_user_id,
        trial_type=data.get("trial_type"),
        expires_at=expires_at_str,
        email=data.get("email"),
        metadata=metadata,
        message_limit=message_limit,
        messages_used=total_used
    )


def _check_expiry(expires_at_str: str) -> str:
    """Check if trial has expired. Returns 'valid' or 'expired'."""
    if not expires_at_str:
        return "valid"  # No expiry set = valid

    try:
        expires_at = datetime.fromisoformat(expires_at_str)
        # Make timezone-aware if not already
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now > expires_at:
            return "expired"
        return "valid"
    except (ValueError, TypeError):
        logger.warning(f"⚠️ Could not parse expires_at: {expires_at_str}")
        return "valid"  # If we can't parse, assume valid


# ============================================================
# POSTGRESQL LOOKUP
# ============================================================

async def _lookup_in_postgres(channel: str, identifier: str) -> Optional[dict]:
    """
    Query PostgreSQL trial_users table for a matching user.

    Returns:
        dict with trial info or None if not found
    """
    pool = await TrialPostgresPool.get_pool()

    # Build query based on channel
    if channel == "web":
        sql = """
            SELECT tu.id, tu.trial_type, tu.expires_at,
                   tu.insta_id, tu.whatsapp_id, tu.metadata,
                   tu.message_limit, tu.messages_used,
                   du.email
            FROM trial_users tu
            JOIN demo_users du ON tu.user_id = du.id
            WHERE tu.id = $1::uuid
        """
        params = [identifier]

    elif channel == "insta":
        sql = """
            SELECT tu.id, tu.trial_type, tu.expires_at,
                   tu.insta_id, tu.whatsapp_id, tu.metadata,
                   tu.message_limit, tu.messages_used,
                   du.email
            FROM trial_users tu
            JOIN demo_users du ON tu.user_id = du.id
            WHERE LOWER(tu.insta_id) = LOWER($1)
            AND tu.insta_opt_in = true
        """
        params = [identifier]

    elif channel == "whatsapp":
        sql = """
            SELECT tu.id, tu.trial_type, tu.expires_at,
                   tu.insta_id, tu.whatsapp_id, tu.metadata,
                   tu.message_limit, tu.messages_used,
                   du.email
            FROM trial_users tu
            JOIN demo_users du ON tu.user_id = du.id
            WHERE tu.whatsapp_id = $1
            AND tu.whatsapp_opt_in = true
        """
        params = [identifier]

    else:
        logger.warning(f"⚠️ Unknown channel for trial lookup: {channel}")
        return None

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)

        if not row:
            return None

        return {
            "trial_user_id": str(row["id"]),
            "trial_type": row["trial_type"],
            "expires_at": row["expires_at"].isoformat() if row["expires_at"] else "",
            "email": row["email"] or "",
            "insta_id": row["insta_id"] or "",
            "whatsapp_id": row["whatsapp_id"] or "",
            "metadata": row["metadata"] if row["metadata"] else {},
            "message_limit": row["message_limit"] if row["message_limit"] is not None else 2500,
            "messages_used": row["messages_used"] if row["messages_used"] is not None else 0,
        }

    except Exception as e:
        logger.error(f"❌ PostgreSQL trial lookup error ({channel}:{identifier}): {e}")
        return None


# ============================================================
# MAIN VALIDATION FUNCTION
# ============================================================

REJECTION_MESSAGES = {
    "not_found": (
        "Welcome! 👋 It looks like you don't have an active trial yet.\n\n"
        "To start your free trial, sign up here:\n"
        f"🔗 {os.getenv('TRIAL_SIGNUP_URL', 'https://goedulabs.com/trial')}"
    ),
    "expired": (
        "Your trial period has ended. ⏰\n\n"
        "To continue using our services, upgrade your plan here:\n"
        f"🔗 {os.getenv('TRIAL_UPGRADE_URL', 'https://goedulabs.com/upgrade')}"
    ),
    "limit_reached": (
        "Your free trial message limit has been reached. 📋\n\n"
        "You have used all {limit} messages included in your trial period.\n\n"
        "Please upgrade.\n"
        "Thank you for trying our service! 🙏"
    ),
}


async def validate_trial_user(
    channel: str,
    identifier: str,
    redis_client,
) -> TrialValidationResult:
    """
    Validate whether a user is an active trial user.

    Args:
        channel: "web", "insta", or "whatsapp"
        identifier: The channel-specific identifier
                    - web: trial_user_id (UUID)
                    - insta: username 
                    - whatsapp: phone number (e.g., "862804")
        redis_client: Redis client instance

    Returns:
        TrialValidationResult with status, trial_type, etc.
    """
    # If trial validation is disabled, let everyone through
    if not is_trial_enabled():
        logger.debug(f"⏭️ Trial validation disabled — allowing {channel}:{identifier}")
        return TrialValidationResult(status="valid")

    if not identifier:
        logger.warning(f"⚠️ Empty identifier for trial validation ({channel})")
        return TrialValidationResult(status="not_found")

    # Normalize identifier
    identifier = identifier.strip()

    # Step 1: Check Redis cache
    cached = _check_redis_cache(redis_client, channel, identifier.lower() if channel == "insta" else identifier)
    if cached:
        return cached

    # Step 2: Cache miss → query PostgreSQL
    logger.info(f"🔍 Redis cache MISS for {channel}:{identifier} → querying PostgreSQL")
    trial_data = await _lookup_in_postgres(channel, identifier)

    if not trial_data:
        # NOT FOUND — do NOT cache (user might be added soon)
        logger.info(f"🚫 Trial user NOT FOUND: {channel}:{identifier}")
        return TrialValidationResult(status="not_found")

    # Step 3: Found → cache it (valid or expired)
    _cache_trial_data(redis_client, trial_data)

    # Step 4: Check expiry
    status = _check_expiry(trial_data["expires_at"])

    # Step 5: Check message limit
    message_limit = trial_data.get("message_limit", 2500)
    messages_used = trial_data.get("messages_used", 0)

    # Also check the live Redis counter
    live_count_raw = redis_client.get(f"trial_msg_count:{trial_data['trial_user_id']}")
    live_count = int(live_count_raw) if live_count_raw else 0
    total_used = messages_used + live_count

    if status == "valid" and total_used >= message_limit:
        status = "limit_reached"

    logger.info(f"{'✅' if status == 'valid' else '⏰'} Trial user {status}: {channel}:{identifier} "
                f"(type={trial_data['trial_type']}, expires={trial_data['expires_at']}, "
                f"msgs={total_used}/{message_limit})")

    return TrialValidationResult(
        status=status,
        trial_user_id=trial_data["trial_user_id"],
        trial_type=trial_data["trial_type"],
        expires_at=trial_data["expires_at"],
        email=trial_data["email"],
        metadata=trial_data.get("metadata"),
        message_limit=message_limit,
        messages_used=total_used
    )


# ============================================================
# MESSAGE COUNTING HELPERS
# ============================================================

def increment_trial_message_count(redis_client, trial_user_id: str) -> int:
    """Atomically increment the session message counter in Redis.
    
    Returns:
        New count value after increment
    """
    key = f"trial_msg_count:{trial_user_id}"
    new_count = redis_client.incr(key)
    # Set TTL of 7 days if this is the first increment (key was just created)
    if new_count == 1:
        redis_client.expire(key, 86400 * 7)
    return new_count


async def flush_message_count_to_postgres(redis_client, trial_user_id: str):
    """Flush the accumulated Redis counter to PostgreSQL.
    
    Uses GETSET to atomically read and reset the counter,
    then adds it to messages_used in the database.
    """
    key = f"trial_msg_count:{trial_user_id}"
    
    # Atomically get current value and reset to 0
    count_raw = redis_client.getset(key, 0)
    if not count_raw:
        return  # Nothing to flush
    
    count = int(count_raw)
    if count <= 0:
        return
    
    try:
        pool = await TrialPostgresPool.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE trial_users SET messages_used = messages_used + $1 WHERE id = $2::uuid",
                count, trial_user_id
            )
        
        # Also update the cached value in Redis hash
        data_key = f"trial_data:{trial_user_id}"
        if redis_client.exists(data_key):
            current = int(redis_client.hget(data_key, "messages_used") or 0)
            redis_client.hset(data_key, "messages_used", str(current + count))
        
        logger.info(f"📊 Flushed {count} messages to PostgreSQL for trial {trial_user_id}")
    except Exception as e:
        # If flush fails, put the count back so we don't lose it
        redis_client.incrby(key, count)
        logger.error(f"❌ Failed to flush message count for {trial_user_id}: {e}")
