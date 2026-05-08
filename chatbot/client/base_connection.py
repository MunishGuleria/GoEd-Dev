"""
Base Connection Utilities

Shared functions used by WhatsApp, Facebook, and Instagram connection modules.
This reduces code duplication across the codebase.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# ==================== SESSION MANAGEMENT ====================

def get_session_id(prefix: str, identifier: str) -> str:
    """
    Generate date-based session ID for any channel.
    
    Args:
        prefix: Channel prefix (e.g., "whatsapp", "facebook", "instagram")
        identifier: User identifier (phone, sender_id, etc.)
        
    Returns:
        Session ID string in format: {prefix}:{identifier}:{YYYY-MM-DD}
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{prefix}:{identifier}:{today}"


def get_yesterday_session_id(prefix: str, identifier: str) -> str:
    """
    Get yesterday's session ID for fetching previous context.
    
    Args:
        prefix: Channel prefix
        identifier: User identifier
        
    Returns:
        Yesterday's session ID string
    """
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    return f"{prefix}:{identifier}:{yesterday}"


def get_lead_id(prefix: str, identifier: str) -> str:
    """
    Generate a consistent lead_id for any channel.
    
    Args:
        prefix: Channel prefix (wa, fb, ig)
        identifier: User identifier
        
    Returns:
        Lead ID string
    """
    return f"{prefix}-{identifier}"


# ==================== CROSS-DAY CONTEXT ====================

def get_previous_summary_from_redis(
    prefix: str, 
    identifier: str, 
    redis_client
) -> Optional[str]:
    """
    Try to get yesterday's summary from Redis.
    
    Args:
        prefix: Channel prefix
        identifier: User identifier
        redis_client: Redis client instance
        
    Returns:
        Summary string or None
    """
    try:
        yesterday_session_id = get_yesterday_session_id(prefix, identifier)
        summary_key = f"summary:{yesterday_session_id}"
        summary = redis_client.get(summary_key)
        if summary:
            logger.info(f"📜 Found yesterday's summary in Redis for {prefix}:{identifier}")
            return summary
    except Exception as e:
        logger.warning(f"Could not fetch yesterday's summary from Redis: {e}")
    return None


# ==================== WEBHOOK VERIFICATION ====================

def verify_webhook(
    mode: Optional[str], 
    token: Optional[str], 
    expected_token: Optional[str],
    challenge: Optional[str],
    channel_name: str = "Unknown"
) -> Tuple[bool, str]:
    """
    Verify Meta webhook subscription.
    
    Args:
        mode: hub.mode from query params
        token: hub.verify_token from query params
        expected_token: Expected verification token from environment
        challenge: hub.challenge from query params
        channel_name: Name for logging (e.g., "WhatsApp", "Instagram")
        
    Returns:
        Tuple of (success: bool, response: str)
    """
    if mode == "subscribe" and token == expected_token:
        logger.info(f"✅ {channel_name} webhook verified successfully")
        return True, challenge or ""
    
    logger.warning(
        f"❌ {channel_name} webhook verification failed. "
        f"Mode: {mode}, Token match: {token == expected_token}"
    )
    return False, "Verification failed"
