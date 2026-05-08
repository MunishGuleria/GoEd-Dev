"""
Facebook Messenger API Connection Manager

Handles all Facebook Messenger functionality including:
- Webhook verification
- Message parsing
- Sending messages
- Session ID generation
- Cross-day context fetching
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

FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")


GRAPH_API_VERSION = "v21.0"
GRAPH_API_URL = f"https://graph.facebook.com/v21.0"


# ==================== WEBHOOK VERIFICATION ====================

def verify_webhook(mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Tuple[bool, str]:
    """Verify Meta webhook subscription for Facebook Messenger."""
    return _verify_webhook(mode, token, FACEBOOK_VERIFY_TOKEN, challenge, "Facebook")


# ==================== MESSAGE PARSING ====================

def parse_webhook_payload(body: dict) -> Optional[Dict]:
    """
    Extract message details from Facebook Messenger webhook payload.
    
    Args:
        body: Raw webhook JSON body
        
    Returns:
        Dict with sender_id, message, message_id, timestamp
        or None if not a valid text message
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
        
        sender_id = sender.get("id")
        recipient_id = recipient.get("id")
        
        # DEBUG: Log the IDs to understand the flow
        logger.info(f"📋 Webhook IDs - Sender: {sender_id}, Recipient: {recipient_id}")
        
        # Handle regular messages
        if "message" in event:
            message_data = event["message"]
            is_echo = message_data.get("is_echo", False)

            message_id = message_data.get("mid")
            message_text = message_data.get("text")

            logger.info(f"📎 Received non-text message from {message_id}")
            
            # Skip if no text (could be attachment, sticker, etc.)
            if not message_text:
                logger.info(f"📎 Received non-text message from {sender_id}")
                return None
            
            return {
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "message": message_text,
                "message_id": message_id,
                "timestamp": timestamp,
                "message_type": "text",
                "is_echo": is_echo

            }
        
        # Handle postbacks (button clicks)
        elif "postback" in event:
            postback = event["postback"]
            payload = postback.get("payload")
            title = postback.get("title")
            
            logger.info(f"🔘 Received postback: {title} ({payload})")
            
            return {
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "message": payload or title,  # Use payload as message
                "message_id": None,
                "timestamp": timestamp,
                "message_type": "postback"
            }
        
        # Handle message reads (optional)
        elif "read" in event:
            logger.debug(f"👁️ Message read by {sender_id}")
            return None
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing Facebook webhook payload: {e}")
        return None


# ==================== SESSION MANAGEMENT ====================
# These functions use the shared base_connection module

def get_session_id(sender_id: str) -> str:
    """Generate date-based session ID for Facebook Messenger conversations."""
    return _get_session_id("facebook", sender_id)


def get_yesterday_session_id(sender_id: str) -> str:
    """Get yesterday's session ID for fetching previous context."""
    return _get_yesterday_session_id("facebook", sender_id)


def get_lead_id_from_sender(sender_id: str) -> str:
    """Generate a consistent lead_id for Facebook Messenger users."""
    return _get_lead_id("fb", sender_id)


# ==================== FACEBOOK MESSENGER API CALLS ====================

async def mark_as_seen(sender_id: str) -> bool:
    """
    Mark message as seen (shows 'Seen' indicator).
    
    Args:
        sender_id: Facebook PSID of the sender
        
    Returns:
        Success status
    """
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error("Facebook Page Access Token not configured")
        return False
    
    url = f"{GRAPH_API_URL}/me/messages"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": sender_id},
                    "sender_action": "mark_seen"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.debug(f"👁️ Marked message from {sender_id} as seen")
                return True
            else:
                logger.warning(f"Failed to mark as seen: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error marking message as seen: {e}")
        return False


async def send_typing_indicator(sender_id: str, typing_on: bool = True) -> bool:
    """
    Show/hide typing indicator.
    
    Args:
        sender_id: Facebook PSID of the recipient
        typing_on: True to show typing, False to hide
        
    Returns:
        Success status
    """
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error("Facebook Page Access Token not configured")
        return False
    
    url = f"{GRAPH_API_URL}/me/messages"
    action = "typing_on" if typing_on else "typing_off"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": sender_id},
                    "sender_action": action
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.debug(f"⌨️ Typing indicator {'on' if typing_on else 'off'} for {sender_id}")
                return True
            else:
                logger.warning(f"Failed to set typing indicator: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error setting typing indicator: {e}")
        return False


async def send_facebook_message(sender_id: str, text: str) -> bool:
    """
    Send text message via Facebook Messenger API.
    
    Args:
        sender_id: Facebook PSID of the recipient
        text: Message text to send
        
    Returns:
        Success status
    """
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error("Facebook Page Access Token not configured")
        return False
    
    url = f"{GRAPH_API_URL}/me/messages"
    
    # Facebook Messenger has a 2000 character limit per message
    MAX_LENGTH = 2000
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH - 50] + "\n\n... (message truncated)"
        logger.warning(f"Message truncated to {MAX_LENGTH} characters")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": sender_id},
                    "message": {"text": text}
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Facebook message sent to {sender_id}")
                return True
            else:
                logger.error(f"Failed to send Facebook message: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending Facebook message: {e}")
        return False


async def send_facebook_message_with_buttons(sender_id: str, text: str, buttons: list) -> bool:
    """
    Send message with quick reply buttons.
    
    Args:
        sender_id: Facebook PSID of the recipient
        text: Message text
        buttons: List of button dicts with 'title' and 'payload'
                 Example: [{"title": "Yes", "payload": "YES"}, {"title": "No", "payload": "NO"}]
        
    Returns:
        Success status
    """
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error("Facebook Page Access Token not configured")
        return False
    
    url = f"{GRAPH_API_URL}/me/messages"
    
    # Format buttons as quick replies
    quick_replies = [
        {
            "content_type": "text",
            "title": btn["title"],
            "payload": btn["payload"]
        }
        for btn in buttons[:13]  # Facebook allows max 13 quick replies
    ]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
                json={
                    "recipient": {"id": sender_id},
                    "message": {
                        "text": text,
                        "quick_replies": quick_replies
                    }
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Facebook message with buttons sent to {sender_id}")
                return True
            else:
                logger.error(f"Failed to send message with buttons: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending message with buttons: {e}")
        return False


# ==================== USER PROFILE ====================

async def get_user_profile(sender_id: str) -> Optional[Dict]:
    """
    Get user's or page's name from Facebook.
    Works for both regular users and Pages.
    
    Args:
        sender_id: Facebook PSID or Page ID
        
    Returns:
        Dict with name or None
    """
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error("Facebook Page Access Token not configured")
        return None
    
    url = f"{GRAPH_API_URL}/{sender_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            # Try to get name - works for both Users and Pages
            response = await client.get(
                url,
                params={
                    "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
                    "fields": "name"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                profile = response.json()
                name = profile.get("name", "Facebook User")
                logger.info(f"📇 Retrieved profile for {sender_id}: {name}")
                return {"first_name": name, "last_name": "", "name": name}
            else:
                logger.warning(f"Failed to get profile: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return None


# ==================== CROSS-DAY CONTEXT ====================

def get_previous_summary_from_redis(sender_id: str, redis_client) -> Optional[str]:
    """Try to get yesterday's summary from Redis."""
    return _get_previous_summary("facebook", sender_id, redis_client)