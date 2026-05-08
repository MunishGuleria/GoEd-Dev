"""
WhatsApp Business API Connection Manager

Handles all WhatsApp-related functionality including:
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

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

GRAPH_API_VERSION = "v23.0"
GRAPH_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# ⚡ Shared persistent HTTP client (reuses TCP+TLS connections)
_http_client: httpx.AsyncClient | None = None

def _get_http_client() -> httpx.AsyncClient:
    """Get or create a shared httpx.AsyncClient with connection pooling."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=5.0,
        )
    return _http_client


# ==================== WEBHOOK VERIFICATION ====================

def verify_webhook(mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Tuple[bool, str]:
    """Verify Meta webhook subscription for WhatsApp."""
    return _verify_webhook(mode, token, WHATSAPP_VERIFY_TOKEN, challenge, "WhatsApp")


# ==================== MESSAGE PARSING ====================

def parse_webhook_payload(body: dict) -> Optional[Dict]:
    """
    Extract message details from Meta webhook payload.
    
    Args:
        body: Raw webhook JSON body
        
    Returns:
        Dict with phone, message, message_id, profile_name, timestamp
        or None if not a valid text message
    """
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        contacts = value.get("contacts", [])
        
        if not messages:
            return None
            
        msg = messages[0]
        message_type = msg.get("type")
        
        # Only handle text messages for now
        if message_type != "text":
            logger.info(f"📎 Received non-text message type: {message_type}")
            return None
        
        # Get user's WhatsApp profile name
        profile_name = None
        if contacts:
            profile_name = contacts[0].get("profile", {}).get("name")
            
        return {
            "phone": msg.get("from"),
            "message": msg.get("text", {}).get("body", ""),
            "message_id": msg.get("id"),
            "message_type": message_type,
            "profile_name": profile_name,
            "timestamp": msg.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"Error parsing webhook payload: {e}")
        return None


# ==================== SESSION MANAGEMENT ====================
# These functions use the shared base_connection module

def get_session_id(phone: str) -> str:
    """Generate date-based session ID for WhatsApp conversations."""
    return _get_session_id("whatsapp", phone)


def get_yesterday_session_id(phone: str) -> str:
    """Get yesterday's session ID for fetching previous context."""
    return _get_yesterday_session_id("whatsapp", phone)


def get_lead_id_from_phone(phone: str) -> str:
    """Generate a consistent lead_id for WhatsApp users."""
    return _get_lead_id("wa", phone)


# ==================== WHATSAPP API CALLS ====================

async def mark_as_read(message_id: str) -> bool:
    """
    Mark incoming message as read (shows blue ticks ✓✓).
    
    Args:
        message_id: WhatsApp message ID from webhook
        
    Returns:
        Success status
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return False
    
    url = f"{GRAPH_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    try:
        client = _get_http_client()
        response = await client.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            },
        )
        
        if response.status_code == 200:
            logger.debug(f"✓✓ Marked message {message_id} as read")
            return True
        else:
            logger.warning(f"Failed to mark as read: {response.text}")
            return False
                
    except Exception as e:
        logger.error(f"Error marking message as read: {e}")
        return False


async def send_whatsapp_message(phone: str, text: str) -> bool:
    """
    Send text message via WhatsApp Business API.
    
    Args:
        phone: Recipient phone number (e.g., "919876543210")
        text: Message text to send
        
    Returns:
        Success status
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return False
    
    url = f"{GRAPH_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    # WhatsApp has a 4096 character limit per message
    MAX_LENGTH = 4096
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH - 50] + "\n\n... (message truncated)"
        logger.warning(f"Message truncated to {MAX_LENGTH} characters")
    
    try:
        client = _get_http_client()
        response = await client.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": text}
            },
        )
        
        if response.status_code == 200:
            logger.info(f"✅ WhatsApp message sent to {phone}")
            return True
        else:
            logger.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
            return False
                
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        return False


# ==================== TYPING INDICATOR ====================

async def send_typing_indicator(phone: str, message_id: str, typing_on: bool = True) -> bool:
    """
    Show typing indicator ("...") in WhatsApp chat.
    Uses the official WhatsApp Cloud API typing_indicator feature.
    
    The indicator auto-expires after 25 seconds or when a message is sent.
    
    Args:
        phone: Recipient phone number (used for logging only)
        message_id: The message_id of the received message to respond to
        typing_on: True to show typing, False is a no-op (auto-clears on send)
        
    Returns:
        Success status
    """
    if not typing_on:
        return True
    
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return False
    
    url = f"{GRAPH_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    try:
        client = _get_http_client()
        response = await client.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
                "typing_indicator": {
                    "type": "text"
                }
            },
        )
        
        if response.status_code == 200:
            logger.info(f"⌨️ Typing ON for {phone} (msg: {message_id[:20]}...)")
            return True
        else:
            logger.warning(f"Typing indicator failed: {response.status_code} - {response.text}")
            return False
                
    except Exception as e:
        logger.error(f"Error setting WhatsApp typing indicator: {e}")
        return False


# ==================== CROSS-DAY CONTEXT ====================

def get_previous_summary_from_redis(phone: str, redis_client) -> Optional[str]:
    """Try to get yesterday's summary from Redis."""
    return _get_previous_summary("whatsapp", phone, redis_client)

