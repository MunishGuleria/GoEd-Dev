"""
Dataverse Client for the Chatbot Service.
3-tier token caching: In-Memory → Redis → Fresh Azure AD fetch.

Uses the same Redis keys as all other services (mcp_server, data_sync_workflow):
  - dataverse:access_token
  - dataverse:token_expiry

This ensures cross-pod token sharing when services share the same Redis instance.
"""

import os
import asyncio
import logging
import time
from typing import Optional, Dict

import httpx

logger = logging.getLogger(__name__)


class DataverseClient:
    """Dataverse client with 3-tier token caching and reusable HTTP client."""

    _instance: Optional["DataverseClient"] = None

    # Shared Redis keys (synced across mcp_server, data_sync_workflow, chatbot)
    REDIS_TOKEN_KEY = "dataverse:access_token"
    REDIS_EXPIRY_KEY = "dataverse:token_expiry"
    TOKEN_BUFFER_SECONDS = 300  # 5-minute safety buffer

    def __init__(self):
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.scope = os.getenv("AZURE_SCOPE")
        self.base_url = os.getenv("DATAVERSE_BASE_URL")

        # In-memory token cache
        self._access_token: Optional[str] = None
        self._expiry_time: float = 0
        self._token_lock = asyncio.Lock()

        # Reusable HTTP client
        self._http_client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> "DataverseClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        """Check if Dataverse credentials are available in this environment."""
        return bool(
            self.tenant_id
            and self.client_id
            and self.client_secret
            and self.base_url
        )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create a reusable HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=60,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._http_client

    async def close(self):
        """Close the HTTP client when done."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # ── Token helpers ────────────────────────────────────────────────────

    def _is_token_valid(self, token: Optional[str], expiry: float) -> bool:
        """Check if a token is present and not expired (with safety buffer)."""
        return bool(token) and time.time() < (expiry - self.TOKEN_BUFFER_SECONDS)

    def _get_redis(self):
        """Get Redis client. Returns None if unavailable."""
        try:
            from client.memory_manager import RedisConnectionPool
            return RedisConnectionPool.get_client()
        except Exception:
            return None

    def _store_in_redis(self, token: str, expiry: float) -> None:
        """Persist token + expiry in Redis. Non-fatal on failure."""
        try:
            r = self._get_redis()
            if not r:
                return
            ttl = max(int(expiry - time.time()), 60)  # floor at 60s
            r.setex(self.REDIS_TOKEN_KEY, ttl, token)
            r.setex(self.REDIS_EXPIRY_KEY, ttl, str(expiry))
            logger.debug("✅ Dataverse token stored in Redis (TTL=%ds)", ttl)
        except Exception as e:
            logger.warning(f"⚠️ Failed to store Dataverse token in Redis: {e}")

    def _load_from_redis(self) -> tuple:
        """Try to load token + expiry from Redis. Returns (None, 0) on miss."""
        try:
            r = self._get_redis()
            if not r:
                return None, 0.0
            token = r.get(self.REDIS_TOKEN_KEY)
            expiry_str = r.get(self.REDIS_EXPIRY_KEY)
            if token and expiry_str:
                return token, float(expiry_str)
        except Exception as e:
            logger.warning(f"⚠️ Failed to load Dataverse token from Redis: {e}")
        return None, 0.0

    # ── Main token method ────────────────────────────────────────────────

    async def get_token(self) -> str:
        """
        3-tier token resolution:
          1. In-memory cache  (fastest, same-process)
          2. Redis cache      (cross-pod / cross-restart)
          3. Fresh Azure AD   (last resort)
        On fresh fetch → written to both memory AND Redis.
        """
        # ── Tier 1: In-memory cache ──
        if self._is_token_valid(self._access_token, self._expiry_time):
            return self._access_token

        # ── Slow path: acquire lock to avoid thundering-herd refreshes ──
        async with self._token_lock:
            # Double-check after acquiring lock
            if self._is_token_valid(self._access_token, self._expiry_time):
                return self._access_token

            # ── Tier 2: Redis cache ──
            redis_token, redis_expiry = self._load_from_redis()
            if self._is_token_valid(redis_token, redis_expiry):
                self._access_token = redis_token
                self._expiry_time = redis_expiry
                logger.info("✅ Dataverse token restored from Redis")
                return self._access_token

            # ── Tier 3: Fresh fetch from Azure AD ──
            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
                "grant_type": "client_credentials",
            }

            try:
                client = await self._get_http_client()
                resp = await client.post(url, data=data)
                resp.raise_for_status()
                res_json = resp.json()

                token = res_json["access_token"]
                expiry = time.time() + res_json["expires_in"]

                # Store in memory
                self._access_token = token
                self._expiry_time = expiry

                # Store in Redis (non-fatal)
                self._store_in_redis(token, expiry)

                logger.info("✅ Dataverse token freshly fetched from Azure AD")
                return self._access_token
            except Exception as e:
                logger.error(f"❌ Dataverse token fetch failed: {e}")
                raise

    # ── Convenience HTTP methods ─────────────────────────────────────────

    async def _get_headers(self) -> Dict[str, str]:
        """Get authenticated headers for Dataverse API calls."""
        token = await self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }

    async def get(self, endpoint: str) -> dict:
        """GET request to Dataverse."""
        client = await self._get_http_client()
        headers = await self._get_headers()
        url = f"{self.base_url}/{endpoint}"
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    async def post(self, endpoint: str, payload: dict) -> httpx.Response:
        """POST request to Dataverse."""
        client = await self._get_http_client()
        headers = await self._get_headers()
        url = f"{self.base_url}/{endpoint}"
        return await client.post(url, headers=headers, json=payload)


# Global singleton
dataverse_client = DataverseClient.get_client()
