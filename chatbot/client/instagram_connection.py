"""
Instagram Messaging API Connection Manager

Handles all Instagram DM functionality including:
- Webhook verification
- Message parsing
- Sending messages
- Session ID generation
- Cross-day context fetching
- Story mentions and replies
"""

import os
import httpx
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict

# Import shared utilities
from client.base_connection import (
    get_session_id as _get_session_id,
    get_yesterday_session_id as _get_yesterday_session_id,
    get_lead_id as _get_lead_id,
    get_previous_summary_from_redis as _get_previous_summary,
    verify_webhook as _verify_webhook
)

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

INSTAGRAM_PAGE_ACCESS_TOKEN = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN")
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")  # Instagram Business Account ID

GRAPH_API_VERSION = "v19.0"
GRAPH_API_URL = f"https://graph.instagram.com/v24.0"

# Validate configuration
if not INSTAGRAM_ACCOUNT_ID:
    logger.warning("⚠️ INSTAGRAM_ACCOUNT_ID not set - Instagram messaging will not work!")
if not INSTAGRAM_PAGE_ACCESS_TOKEN:
    logger.warning("⚠️ INSTAGRAM_PAGE_ACCESS_TOKEN not set - Instagram messaging will not work!")

# ==================== TOKEN REFRESH ====================

from pathlib import Path

TOKEN_CREATED_FILE = Path(__file__).parent / ".ig_token_created"
REFRESH_AFTER_DAYS = 50  # Refresh before 60-day expiry


async def refresh_token_if_needed() -> bool:
    """
    Check and refresh Instagram token if it's older than REFRESH_AFTER_DAYS.
    Call this on app startup and periodically via background task.
    
    Returns:
        True if token is valid (refreshed or still fresh), False on error
    """
    global INSTAGRAM_PAGE_ACCESS_TOKEN
    
    if not INSTAGRAM_PAGE_ACCESS_TOKEN:
        logger.warning("⚠️ No Instagram token to refresh")
        return False
    
    # Check token age
    days_old = _get_token_age_days()
    
    if days_old < REFRESH_AFTER_DAYS:
        logger.info(f"✅ Instagram token OK ({days_old} days old, refresh at {REFRESH_AFTER_DAYS})")
        return True
    
    logger.info(f"🔄 Instagram token is {days_old} days old, refreshing...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.instagram.com/refresh_access_token",
                params={
                    "grant_type": "ig_refresh_token",
                    "access_token": INSTAGRAM_PAGE_ACCESS_TOKEN
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data["access_token"]
                expires_in = data.get("expires_in", 5183944)
                
                # Update token in memory
                INSTAGRAM_PAGE_ACCESS_TOKEN = new_token
                os.environ["INSTAGRAM_PAGE_ACCESS_TOKEN"] = new_token
                
                # Save refresh timestamp
                _save_token_timestamp()
                
                logger.info(f"✅ Instagram token refreshed! Valid for {expires_in // 86400} days")
                logger.warning(f"⚠️ UPDATE .env with new token: {new_token[:20]}...{new_token[-10:]}")
                
                return True
            else:
                logger.error(f"❌ Token refresh failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Token refresh error: {e}")
        return False


def _get_token_age_days() -> int:
    """Get how many days old the token is based on last refresh timestamp."""
    if not TOKEN_CREATED_FILE.exists():
        # First run - assume token is fresh, save current time
        _save_token_timestamp()
        return 0
    
    try:
        created_str = TOKEN_CREATED_FILE.read_text().strip()
        created = datetime.fromisoformat(created_str)
        age = (datetime.now(timezone.utc) - created).days
        return age
    except Exception as e:
        logger.warning(f"Could not read token timestamp: {e}")
        return 0


def _save_token_timestamp():
    """Save current time as token refresh timestamp."""
    try:
        TOKEN_CREATED_FILE.write_text(datetime.now(timezone.utc).isoformat())
        logger.debug(f"📝 Saved token timestamp to {TOKEN_CREATED_FILE}")
    except Exception as e:
        logger.warning(f"Could not save token timestamp: {e}")


# ==================== WEBHOOK VERIFICATION ====================

def verify_webhook(mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Tuple[bool, str]:
    """Verify Meta webhook subscription for Instagram."""
    return _verify_webhook(mode, token, INSTAGRAM_VERIFY_TOKEN, challenge, "Instagram")


# ==================== MESSAGE PARSING ====================

def parse_webhook_payload(body: dict) -> Optional[Dict]:
    """
    Extract message details from Instagram webhook payload.
    
    Instagram webhook structure is similar to Messenger but with some differences:
    - Uses 'messaging' array like Messenger
    - Can include story_mention, story_reply
    - Media messages have different structure
    
    Args:
        body: Raw webhook JSON body
        
    Returns:
        Dict with sender_id, message, message_id, timestamp, message_type
        or None if not a valid message
    """
    try:
        entry = body.get("entry", [{}])[0]
        messaging = entry.get("messaging", [])
        
        if not messaging:
            return None
            
        event = messaging[0]
        sender = event.get("sender", {})
        recipient = event.get("recipient", {})
        timestamp = event.get("timestamp")
        
        # Handle regular text messages
        if "message" in event:
            message_data = event["message"]
            
            # Skip echo messages (messages sent by our own account)
            if message_data.get("is_echo"):
                logger.debug(f"↩️ Skipping echo message")
                return None
            
            message_id = message_data.get("mid")
            message_text = message_data.get("text")
            
            # Handle story replies (when user replies to your story)
            if "reply_to" in message_data:
                story_id = message_data["reply_to"].get("story", {}).get("id")
                logger.info(f"📖 Story reply from {sender.get('id')}: {story_id}")
                # You can fetch story details if needed
            
            # Handle media messages (images, videos)
            if "attachments" in message_data and not message_text:
                attachments = message_data.get("attachments", [])
                if attachments:
                    attachment_type = attachments[0].get("type")
                    logger.info(f"📎 Received {attachment_type} from {sender.get('id')}")
                    # For now, we'll skip media messages
                    return None
            
            # Skip if no text
            if not message_text:
                return None
            
            return {
                "sender_id": sender.get("id"),
                "recipient_id": recipient.get("id"),
                "message": message_text,
                "message_id": message_id,
                "timestamp": timestamp,
                "message_type": "text"
            }
        
        # Handle story mentions (when user mentions you in their story)
        elif "story_mention" in event:
            mention_data = event["story_mention"]
            logger.info(f"🏷️ Story mention from {sender.get('id')}")
            
            # You might want to respond to story mentions
            return {
                "sender_id": sender.get("id"),
                "recipient_id": recipient.get("id"),
                "message": "[User mentioned you in their story]",
                "message_id": None,
                "timestamp": timestamp,
                "message_type": "story_mention"
            }
        
        # Handle message reads
        elif "read" in event:
            logger.debug(f"👁️ Message read by {sender.get('id')}")
            return None
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing Instagram webhook payload: {e}")
        return None


# ==================== SESSION MANAGEMENT ====================
# These functions use the shared base_connection module

def get_session_id(sender_id: str) -> str:
    """Generate date-based session ID for Instagram conversations."""
    return _get_session_id("instagram", sender_id)


def get_yesterday_session_id(sender_id: str) -> str:
    """Get yesterday's session ID for fetching previous context."""
    return _get_yesterday_session_id("instagram", sender_id)


def get_lead_id_from_sender(sender_id: str) -> str:
    """Generate a consistent lead_id for Instagram users."""
    return _get_lead_id("ig", sender_id)


# ==================== INSTAGRAM API CALLS ====================

async def mark_as_seen(sender_id: str) -> bool:
    """
    Mark message as seen (shows 'Seen' indicator).
    
    Args:
        sender_id: Instagram-Scoped ID of the sender
        
    Returns:
        Success status
    """
    if not INSTAGRAM_PAGE_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.error("Instagram configuration not complete (missing token or account ID)")
        return False
    
    url = f"{GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/messages"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": INSTAGRAM_PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": sender_id},
                    "sender_action": "mark_seen"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.debug(f"👁️ Marked Instagram message from {sender_id} as seen")
                return True
            else:
                logger.warning(f"Failed to mark as seen: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error marking Instagram message as seen: {e}")
        return False


async def send_typing_indicator(sender_id: str, typing_on: bool = True) -> bool:
    """
    Show/hide typing indicator.
    
    Args:
        sender_id: Instagram-Scoped ID of the recipient
        typing_on: True to show typing, False to hide
        
    Returns:
        Success status
    """
    if not INSTAGRAM_PAGE_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.error("Instagram configuration not complete (missing token or account ID)")
        return False
    
    url = f"{GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/messages"
    action = "typing_on" if typing_on else "typing_off"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": INSTAGRAM_PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": sender_id},
                    "sender_action": action
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.debug(f"⌨️ Instagram typing indicator {'on' if typing_on else 'off'} for {sender_id}")
                return True
            else:
                logger.warning(f"Failed to set typing indicator: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error setting Instagram typing indicator: {e}")
        return False


async def send_instagram_message(sender_id: str, text: str) -> bool:
    """
    Send text message via Instagram Messaging API.
    
    Args:
        sender_id: Instagram-Scoped ID of the recipient
        text: Message text to send
        
    Returns:
        Success status
    """
    if not INSTAGRAM_PAGE_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.error("Instagram configuration not complete (missing token or account ID)")
        return False
    
    # url = f"{GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/messages"
    url= f"{GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/messages"
    
    # Instagram has a 1000 character limit per message
    MAX_LENGTH = 1000
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH - 50] + "\n\n... (message truncated)"
        logger.warning(f"Message truncated to {MAX_LENGTH} characters")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": INSTAGRAM_PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": sender_id},
                    "messaging_type":"RESPONSE",
                    "message": {"text": text}
                },
                timeout=30.0
            )
            
            if response.status_code == 200:


                logger.info(f"✅ Instagram message sent to {sender_id}")
                return True
            else:
                logger.error(f"Failed to send Instagram message: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending Instagram message: {e}")
        return False


async def send_instagram_quick_replies(sender_id: str, text: str, quick_replies: list) -> bool:
    """
    Send message with quick reply buttons.
    
    Args:
        sender_id: Instagram-Scoped ID of the recipient
        text: Message text
        quick_replies: List of button dicts with 'title' and 'payload'
                       Example: [{"title": "Yes", "payload": "YES"}, {"title": "No", "payload": "NO"}]
        
    Returns:
        Success status
    """
    if not INSTAGRAM_PAGE_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.error("Instagram configuration not complete (missing token or account ID)")
        return False
    
    url = f"{GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/messages"
    
    # Format quick replies (max 13)
    formatted_replies = [
        {
            "content_type": "text",
            "title": reply["title"],
            "payload": reply["payload"]
        }
        for reply in quick_replies[:13]
    ]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": INSTAGRAM_PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": sender_id},
                    "message": {
                        "text": text,
                        "quick_replies": formatted_replies
                    }
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Instagram quick replies sent to {sender_id}")
                return True
            else:
                logger.error(f"Failed to send quick replies: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending Instagram quick replies: {e}")
        return False


async def send_instagram_ice_breakers(ice_breakers: list) -> bool:
    """
    Set up ice breakers (conversation starters) for Instagram DMs.
    These appear when users start a new conversation.
    
    Args:
        ice_breakers: List of dicts with 'question' and 'payload'
                      Example: [
                          {"question": "What services do you offer?", "payload": "SERVICES"},
                          {"question": "Pricing info", "payload": "PRICING"}
                      ]
        
    Returns:
        Success status
    """
    if not INSTAGRAM_PAGE_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.error("Instagram configuration not complete (missing token or account ID)")
        return False
    
    url = f"{GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/messenger_profile"
    
    # Format ice breakers (max 4)
    formatted_breakers = [
        {
            "question": breaker["question"],
            "payload": breaker["payload"]
        }
        for breaker in ice_breakers[:4]
    ]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": INSTAGRAM_PAGE_ACCESS_TOKEN},
                json={
                    "ice_breakers": formatted_breakers
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Instagram ice breakers set up")
                return True
            else:
                logger.error(f"Failed to set ice breakers: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error setting Instagram ice breakers: {e}")
        return False


async def get_user_profile(sender_id: str) -> Optional[Dict]:
    """
    Get user's profile information from Instagram.
    
    Note: Instagram API provides limited profile info compared to Facebook.
    You can get: name, profile_pic (if they allow it)
    
    Args:
        sender_id: Instagram-Scoped ID
        
    Returns:
        Dict with name, profile_pic, etc. or None
    """
    if not INSTAGRAM_PAGE_ACCESS_TOKEN:
        logger.error("Instagram Page Access Token not configured")
        return None
    
    url = f"{GRAPH_API_URL}/{sender_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params={
                    "access_token": INSTAGRAM_PAGE_ACCESS_TOKEN,
                    "fields": "name,username" 
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                profile = response.json()
                logger.info(f"📇 Retrieved Instagram profile for {sender_id}: {profile.get('name')} (@{profile.get('username', 'N/A')})")
                return profile
            else:
                logger.warning(f"Failed to get Instagram user profile: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error getting Instagram user profile: {e}")
        return None


# ==================== CROSS-DAY CONTEXT ====================

def get_previous_summary_from_redis(sender_id: str, redis_client) -> Optional[str]:
    """
    Try to get yesterday's summary from Redis (if not yet archived).
    
    Args:
        sender_id: Instagram-Scoped ID
        redis_client: Redis client instance
        
    Returns:
        Summary string or None
    """
    try:
        yesterday_session_id = get_yesterday_session_id(sender_id)
        summary_key = f"summary:{yesterday_session_id}"
        summary = redis_client.get(summary_key)
        if summary:
            logger.info(f"📜 Found yesterday's summary in Redis for Instagram user {sender_id}")
            return summary
    except Exception as e:
        logger.warning(f"Could not fetch yesterday's summary from Redis: {e}")
    return None