import os
import asyncio
import logging
from typing import Optional, Dict
from contextlib import asynccontextmanager
import time
import redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
import asyncpg

import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("archive_worker")


# ==================== REDIS CLIENT ====================
class RedisConnectionPool:
    _instance: Optional[redis.Redis] = None
    _lock = asyncio.Lock()

    @classmethod
    def get_client(cls) -> redis.Redis:
        if cls._instance is None:
            cls._instance = redis.Redis(
                host=os.getenv("REDIS_HOST"),
                port=int(os.getenv("REDIS_PORT")),
                password=os.getenv("REDIS_PASSWORD"),
                ssl=True,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            try:
                cls._instance.ping()
            except (RedisConnectionError, RedisTimeoutError) as e:
                log.error(f"❌ Redis connection failed: {e}")
                raise
        return cls._instance

    @classmethod
    async def reconnect(cls):
        """Reconnect to Redis if connection is lost."""
        if cls._instance:
            try:
                cls._instance.ping()
            except (RedisConnectionError, RedisTimeoutError):
                log.warning("⚠️ Redis connection lost, reconnecting...")
                cls._instance.close()
                cls._instance = None
                return cls.get_client()
        return cls.get_client()

    @classmethod
    def close(cls):
        if cls._instance:
            cls._instance.close()
            cls._instance = None


# ==================== POSTGRES CLIENT ====================
class PostgresClient:
    _instance: Optional["PostgresClient"] = None
    _pool: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()

    # Pool configuration constants
    MIN_POOL_SIZE = 1
    MAX_POOL_SIZE = 8
    MAX_QUERIES = 50000
    MAX_INACTIVE_CONNECTION_LIFETIME = 300.0  # 5 minutes
    COMMAND_TIMEOUT = 30.0  # 30 seconds

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool:
            return self._pool
        async with self._lock:
            if self._pool is None:
                try:
                    self._pool = await asyncpg.create_pool(
                        user=os.getenv("POSTGRES_USER"),
                        password=os.getenv("POSTGRES_PASSWORD"),
                        host=os.getenv("POSTGRES_HOST"),
                        port=int(os.getenv("POSTGRES_PORT")),
                        database=os.getenv("POSTGRES_DATABASE"),
                        min_size=self.MIN_POOL_SIZE,
                        max_size=self.MAX_POOL_SIZE,
                        max_queries=self.MAX_QUERIES,
                        max_inactive_connection_lifetime=self.MAX_INACTIVE_CONNECTION_LIFETIME,
                        command_timeout=self.COMMAND_TIMEOUT,
                    )
                    # Test connection
                    async with self._pool.acquire() as conn:
                        await conn.execute("SELECT 1")
                    log.info("✅ PostgreSQL pool created successfully")
                except Exception as e:
                    log.error(f"❌ PostgreSQL connection failed: {e}")
                    raise
            return self._pool

    @asynccontextmanager
    async def acquire(self):
        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                yield conn
        except asyncpg.exceptions.PoolAcquireTimeoutError:
            log.error("❌ PostgreSQL pool exhausted - cannot acquire connection")
            raise

    @classmethod
    def get_client(cls) -> "PostgresClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

# ==================== DATAVERSE CLIENT ====================
class DataverseClient:
    """Handles OData connections to Dataverse with auto-refreshing tokens and reusable HTTP client."""

    _instance: Optional["DataverseClient"] = None

    def __init__(self):
        self.base_url = os.getenv("DATAVERSE_BASE_URL")
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.scope = os.getenv("AZURE_SCOPE")

        # Token Cache
        self._access_token: Optional[str] = None
        self._expiry_time: float = 0
        self._token_lock = asyncio.Lock()  # Lock for token refresh

        # Reusable HTTP client for better performance
        self._http_client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> "DataverseClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create a reusable HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=60,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return self._http_client

    async def close(self):
        """Close the HTTP client when done."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # Redis keys for token caching
    REDIS_TOKEN_KEY = "dataverse:access_token"
    REDIS_EXPIRY_KEY = "dataverse:token_expiry"
    TOKEN_BUFFER_SECONDS = 300  # 5-minute safety buffer

    def _is_token_valid(self, token: str, expiry: float) -> bool:
        """Check if a token is present and not expired (with safety buffer)."""
        return bool(token) and time.time() < (expiry - self.TOKEN_BUFFER_SECONDS)

    def _store_in_redis(self, token: str, expiry: float) -> None:
        """Persist token + expiry in Redis. Non-fatal on failure."""
        try:
            r = RedisConnectionPool.get_client()
            ttl = max(int(expiry - time.time()), 60)  # floor at 60s
            r.setex(self.REDIS_TOKEN_KEY, ttl, token)
            r.setex(self.REDIS_EXPIRY_KEY, ttl, str(expiry))
            log.debug("✅ Dataverse token stored in Redis (TTL=%ds)", ttl)
        except Exception as e:
            log.warning(f"⚠️ Failed to store Dataverse token in Redis: {e}")

    def _load_from_redis(self) -> tuple[Optional[str], float]:
        """Try to load token + expiry from Redis. Returns (None, 0) on miss/failure."""
        try:
            r = RedisConnectionPool.get_client()
            token = r.get(self.REDIS_TOKEN_KEY)
            expiry_str = r.get(self.REDIS_EXPIRY_KEY)
            if token and expiry_str:
                return token, float(expiry_str)
        except Exception as e:
            log.warning(f"⚠️ Failed to load Dataverse token from Redis: {e}")
        return None, 0.0

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
            # Double-check after acquiring lock (another coroutine may have refreshed)
            if self._is_token_valid(self._access_token, self._expiry_time):
                return self._access_token

            # ── Tier 2: Redis cache ──
            redis_token, redis_expiry = self._load_from_redis()
            if self._is_token_valid(redis_token, redis_expiry):
                # Promote to in-memory cache
                self._access_token = redis_token
                self._expiry_time = redis_expiry
                log.info("✅ Dataverse token restored from Redis")
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

                log.info("✅ Dataverse token freshly fetched from Azure AD")
                return self._access_token
            except Exception as e:
                log.error(f"❌ Dataverse token fetch failed: {e}")
                raise

    async def get_headers(self) -> Dict[str, str]:
        """Get authenticated headers for Dataverse API calls."""
        token = await self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }

    async def post_record(self, entity_set: str, payload: dict) -> httpx.Response:
        """Generic method to post to any Dataverse table."""
        client = await self._get_http_client()
        headers = await self.get_headers()
        url = f"{self.base_url}/{entity_set}"
        return await client.post(url, headers=headers, json=payload)


# ==================== LLM CLIENT ====================
from langchain_openai import AzureChatOpenAI

class LLMClient:
    """Singleton Azure OpenAI client for summarization."""
    _instance: Optional[AzureChatOpenAI] = None

    @classmethod
    def get_client(cls) -> AzureChatOpenAI:
        if cls._instance is None:
            cls._instance = AzureChatOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_API_INSTANCE_NAME"),
                model=os.getenv("AZURE_OPENAI_API_DEPLOYMENT_NAME"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                temperature=0.0
            )
        return cls._instance


# ==================== GLOBAL INSTANCES ====================
postgres = PostgresClient.get_client()
dataverse = DataverseClient.get_client()
llm = LLMClient.get_client()