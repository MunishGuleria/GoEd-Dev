"""
==============================================================================
  OneDrive Excel Helper — Microsoft Graph API (Multi-Excel Support)
==============================================================================

  This module handles appending rows to MULTIPLE Excel files hosted on
  OneDrive using the Microsoft Graph API.

  Each Excel file is identified by a "target" name (e.g., "BROADCAST").
  The target name maps to environment variables:
    - {TARGET}_EXCEL_SHARE_LINK   →  Sharing link to the Excel file
    - {TARGET}_EXCEL_SHEET_NAME   →  Worksheet name (default: "Sheet1")
    - {TARGET}_EXCEL_TABLE_NAME   →  Table name (default: "Table1")

  Authentication (shared across all targets):
    - GRAPH_TENANT_ID        →  Azure AD tenant ID
    - GRAPH_CLIENT_ID        →  App registration client ID
    - GRAPH_CLIENT_SECRET    →  App registration client secret

  Example .env for two Excel files:

    # Broadcast Excel
    BROADCAST_EXCEL_SHARE_LINK=https://zoxima0-my.sharepoint.com/...
    BROADCAST_EXCEL_SHEET_NAME=Sheet1
    BROADCAST_EXCEL_TABLE_NAME=Table1

    # Leads Excel (future)
    LEADS_EXCEL_SHARE_LINK=https://zoxima0-my.sharepoint.com/...
    LEADS_EXCEL_SHEET_NAME=Sheet1
    LEADS_EXCEL_TABLE_NAME=Table1

  Usage:
    # Append to the Broadcast Excel
    result = await append_to_excel("BROADCAST", ["Munish", "9876543210", "2026-04-08", "Pending"])

    # Append to the Leads Excel (different file)
    result = await append_to_excel("LEADS", ["John", "1234567890", "2026-04-08", "New"])
==============================================================================
"""

import os
import base64
import time
import logging
from typing import Optional, Dict, Tuple, List, Any

import httpx


# ─────────────────────────────────────────────────────────────────────
#   Logger
# ─────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
#   Constants
# ─────────────────────────────────────────────────────────────────────

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# Scope for Microsoft Graph API (application-level)
GRAPH_SCOPE = "https://graph.microsoft.com/.default"


# ─────────────────────────────────────────────────────────────────────
#   Token Cache  —  Shared across all Excel targets (same app)
# ─────────────────────────────────────────────────────────────────────

_token_cache: Dict[str, Any] = {
    "access_token": None,
    "expires_at":   0,
}


# ─────────────────────────────────────────────────────────────────────
#   Per-Target Caches  —  Each Excel file has its own driveId, itemId,
#                         and table name. Keyed by target name.
# ─────────────────────────────────────────────────────────────────────

# { "BROADCAST": {"drive_id": "...", "item_id": "..."}, "LEADS": {...} }
_drive_item_cache: Dict[str, Dict[str, Optional[str]]] = {}

# { "BROADCAST": "Table1", "LEADS": "Table2" }
_table_name_cache: Dict[str, str] = {}


# ============================================================
#   1. AUTHENTICATION  —  Client Credentials (shared)
# ============================================================

async def get_graph_token() -> str:
    """
    Get a valid Microsoft Graph API access token using
    client_credentials grant (application-level).

    Uses the separate OneDrive app registration:
      - GRAPH_TENANT_ID       (may differ from AZURE_TENANT_ID)
      - GRAPH_CLIENT_ID       (separate from Dataverse)
      - GRAPH_CLIENT_SECRET   (separate from Dataverse)

    This token is shared across ALL Excel targets — we only
    need one token for all files.

    Returns:
        str: A valid access token for Microsoft Graph API.

    Raises:
        Exception: If authentication fails.
    """

    global _token_cache

    # ── Check if we have a valid cached token ────────────────────────

    current_time   = time.time()
    BUFFER_SECONDS = 300  # 5-minute safety buffer before expiry

    if (
        _token_cache["access_token"]
        and current_time < (_token_cache["expires_at"] - BUFFER_SECONDS)
    ):
        logger.debug("📦 Using cached Graph API token")
        return _token_cache["access_token"]


    # ── Read credentials from environment ────────────────────────────
    #
    #  GRAPH_TENANT_ID  — may be different from AZURE_TENANT_ID
    #  GRAPH_CLIENT_ID  — separate app registration for OneDrive
    #

    tenant_id     = os.getenv("GRAPH_TENANT_ID", os.getenv("AZURE_TENANT_ID"))
    client_id     = os.getenv("GRAPH_CLIENT_ID")
    client_secret = os.getenv("GRAPH_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "❌ GRAPH_CLIENT_ID and GRAPH_CLIENT_SECRET must be set in .env!"
        )


    # ── Build the client_credentials token request ───────────────────

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    token_data = {
        "client_id":     client_id,
        "client_secret": client_secret,
        "scope":         GRAPH_SCOPE,
        "grant_type":    "client_credentials",
    }

    logger.info(f"🔑 Requesting Graph API token for client: {client_id[:8]}...")


    # ── Send the token request ───────────────────────────────────────

    async with httpx.AsyncClient(timeout=15) as client:

        response = await client.post(token_url, data=token_data)

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(
                f"❌ Graph token request failed: "
                f"status={response.status_code}, body={error_detail}"
            )
            raise Exception(
                f"Graph API auth failed ({response.status_code}). "
                f"Detail: {error_detail}"
            )

        result = response.json()


    # ── Cache the token ──────────────────────────────────────────────

    _token_cache["access_token"] = result["access_token"]
    _token_cache["expires_at"]   = current_time + result.get("expires_in", 3600)

    logger.info("✅ Microsoft Graph API token acquired")
    return _token_cache["access_token"]


# ============================================================
#   2. SHARING LINK RESOLUTION  —  Per-target driveId + itemId
# ============================================================

def _encode_sharing_url(sharing_url: str) -> str:
    """
    Encode a OneDrive/SharePoint sharing URL for the Graph API
    /shares endpoint.

    Microsoft requires a special encoding:
      1. Base64-encode the URL (UTF-8)
      2. Strip trailing '=' padding
      3. Replace '/' with '_' and '+' with '-'
      4. Prepend 'u!'

    Args:
        sharing_url: The full OneDrive sharing URL.

    Returns:
        str: The encoded sharing token (e.g., "u!aHR0cH...")
    """

    # Step 1: Base64 encode
    encoded = base64.b64encode(sharing_url.encode("utf-8")).decode("utf-8")

    # Step 2: Strip trailing '=' characters
    encoded = encoded.rstrip("=")

    # Step 3: URL-safe Base64 replacements
    encoded = encoded.replace("/", "_").replace("+", "-")

    # Step 4: Prepend the 'u!' prefix
    return f"u!{encoded}"


async def _resolve_sharing_link(target: str) -> Tuple[str, str]:
    """
    Resolve the OneDrive sharing link for a specific Excel target
    to get the driveId and itemId.

    The result is cached per target — only the first call for
    each target hits the Graph API.

    Args:
        target: The target name (e.g., "BROADCAST", "LEADS").
                Maps to env var: {TARGET}_EXCEL_SHARE_LINK

    Returns:
        Tuple[str, str]: (drive_id, item_id)

    Raises:
        Exception: If the sharing link cannot be resolved.
    """

    global _drive_item_cache

    # ── Return cached values if available ────────────────────────────

    if target in _drive_item_cache:
        cached = _drive_item_cache[target]
        if cached.get("drive_id") and cached.get("item_id"):
            logger.debug(f"📦 [{target}] Using cached drive item IDs")
            return cached["drive_id"], cached["item_id"]


    # ── Get the sharing link from environment ────────────────────────

    env_key    = f"{target}_EXCEL_SHARE_LINK"
    share_link = os.getenv(env_key)

    if not share_link:
        raise ValueError(
            f"❌ {env_key} environment variable is not set! "
            f"Set it to the OneDrive sharing link for the '{target}' Excel file."
        )


    # ── Encode the sharing URL ───────────────────────────────────────

    encoded_url = _encode_sharing_url(share_link)

    logger.info(f"🔗 [{target}] Resolving sharing link...")


    # ── Call the Graph API /shares endpoint ───────────────────────────

    token = await get_graph_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }

    url = f"{GRAPH_BASE_URL}/shares/{encoded_url}/driveItem"

    async with httpx.AsyncClient(timeout=15) as client:

        response = await client.get(url, headers=headers)

        if response.status_code != 200:
            logger.error(
                f"❌ [{target}] Failed to resolve sharing link: "
                f"status={response.status_code}, body={response.text[:500]}"
            )
            raise Exception(
                f"[{target}] Could not resolve sharing link: "
                f"{response.status_code} — {response.text[:300]}"
            )

        data = response.json()


    # ── Extract driveId and itemId ───────────────────────────────────

    drive_id = data.get("parentReference", {}).get("driveId")
    item_id  = data.get("id")

    if not drive_id or not item_id:
        raise Exception(
            f"❌ [{target}] Could not extract driveId/itemId from response"
        )


    # ── Cache for future requests ────────────────────────────────────

    _drive_item_cache[target] = {
        "drive_id": drive_id,
        "item_id":  item_id,
    }

    logger.info(
        f"✅ [{target}] Resolved → driveId={drive_id}, itemId={item_id}"
    )
    return drive_id, item_id


# ============================================================
#   3. TABLE DISCOVERY  —  Per-target table name
# ============================================================

async def _get_table_name(target: str, drive_id: str, item_id: str) -> str:
    """
    Find the table name in the Excel worksheet for a specific target.

    Reads from env var: {TARGET}_EXCEL_TABLE_NAME
    If not set, discovers the first table in the sheet.

    The result is cached per target.

    Args:
        target:   The target name (e.g., "BROADCAST").
        drive_id: The OneDrive drive ID.
        item_id:  The Excel file item ID.

    Returns:
        str: The table name (used for appending rows).

    Raises:
        Exception: If no table is found in the worksheet.
    """

    global _table_name_cache

    # ── Return cached table name if available ────────────────────────

    if target in _table_name_cache:
        logger.debug(f"📦 [{target}] Using cached table: {_table_name_cache[target]}")
        return _table_name_cache[target]


    # ── Read config ──────────────────────────────────────────────────

    token          = await get_graph_token()
    sheet_name     = os.getenv(f"{target}_EXCEL_SHEET_NAME", "Sheet1")
    expected_table = os.getenv(f"{target}_EXCEL_TABLE_NAME", "")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }


    # ── List all tables in the worksheet ─────────────────────────────

    workbook_url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}/workbook"
    tables_url   = f"{workbook_url}/worksheets/{sheet_name}/tables"

    async with httpx.AsyncClient(timeout=30) as client:

        resp = await client.get(tables_url, headers=headers)

        if resp.status_code != 200:
            logger.error(
                f"❌ [{target}] Failed to list tables: "
                f"status={resp.status_code}, body={resp.text[:500]}"
            )
            raise Exception(
                f"[{target}] Could not list tables: "
                f"{resp.status_code} — {resp.text[:300]}"
            )

        tables = resp.json().get("value", [])

    logger.info(
        f"📋 [{target}] Found {len(tables)} table(s): "
        f"{[t.get('name') for t in tables]}"
    )


    # ── No tables found ──────────────────────────────────────────────

    if not tables:
        raise Exception(
            f"❌ [{target}] No tables found in worksheet '{sheet_name}'! "
            f"Please create a table in the Excel file first."
        )


    # ── Look for the expected table name ─────────────────────────────

    if expected_table:
        for table in tables:
            if table.get("name") == expected_table:
                _table_name_cache[target] = expected_table
                logger.info(f"✅ [{target}] Found table: '{expected_table}'")
                return expected_table


    # ── Fall back to the first table found ───────────────────────────

    first_table = tables[0].get("name")
    _table_name_cache[target] = first_table

    logger.info(f"✅ [{target}] Using first table: '{first_table}'")
    return first_table


# ============================================================
#   4. APPEND ROW  —  The main function to call
# ============================================================

async def append_to_excel(
    target: str,
    row_values: List[str],
) -> dict:
    """
    Append a single row to a specific Excel file on OneDrive.

    This is the main entry point. It:
      1. Resolves the sharing link for the target (cached)
      2. Finds the table name for the target (cached)
      3. Appends a row with the given values

    Args:
        target:     The target name (e.g., "BROADCAST", "LEADS").
                    Maps to env vars: {TARGET}_EXCEL_SHARE_LINK, etc.

        row_values: List of cell values to append as a single row.
                    Must match the column order in your Excel table.
                    Example: ["Munish", "9876543210", "2026-04-08", "Pending"]

    Returns:
        dict: Success/failure info with details.

    Example:
        # Append to Broadcast Excel
        result = await append_to_excel(
            target     = "BROADCAST",
            row_values = ["Munish", "9876543210", "2026-04-08 15:30:00", "Pending"]
        )

        # Append to a different Excel (future)
        result = await append_to_excel(
            target     = "LEADS",
            row_values = ["John", "1234567890", "2026-04-08 15:30:00", "New"]
        )
    """

    try:

        # ── Step 1: Resolve the sharing link ─────────────────────────

        logger.info(f"📤 [{target}] Appending row: {row_values}")

        drive_id, item_id = await _resolve_sharing_link(target)


        # ── Step 2: Get the table name ───────────────────────────────

        table_name = await _get_table_name(target, drive_id, item_id)


        # ── Step 3: Append the row to the table ─────────────────────

        token = await get_graph_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

        # Build the append URL
        workbook_url = (
            f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}/workbook"
        )
        append_url = f"{workbook_url}/tables/{table_name}/rows/add"

        # Build the row data
        payload = {
            "values": [row_values]
        }

        logger.info(f"📡 [{target}] POST to table '{table_name}'")

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                append_url,
                headers=headers,
                json=payload,
            )


        # ── Step 4: Handle the response ──────────────────────────────

        if response.status_code in (200, 201):

            logger.info(f"✅ [{target}] Row appended successfully")

            return {
                "success": True,
                "message": f"Row appended to '{target}' Excel successfully",
                "data":    row_values,
            }

        else:

            error_body = response.text[:500]

            logger.error(
                f"❌ [{target}] Failed to append row: "
                f"status={response.status_code}, body={error_body}"
            )

            return {
                "success": False,
                "message": f"[{target}] Graph API error: {response.status_code}",
                "error":   error_body,
            }


    except Exception as e:

        logger.error(f"❌ [{target}] append_to_excel failed: {e}", exc_info=True)

        return {
            "success": False,
            "message": f"[{target}] Failed to append row to Excel",
            "error":   str(e),
        }
