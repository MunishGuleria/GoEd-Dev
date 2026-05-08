import os
import asyncio
import logging
import json
import time
from typing import List, Optional, AsyncGenerator, Any
import asyncpg
import redis
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================
# EMBEDDINGS CLIENT
# ============================================================
class EmbeddingsClient:
    def __init__(self):

        self._client = AzureOpenAIEmbeddings(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_API_INSTANCE_NAME"),
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            model=os.getenv("AZURE_OPENAI_EMBEDDING_MODEL"),
            max_retries=2,
            request_timeout=30,
        )
        logger.info("✓ Embeddings client initialized")

    async def embed_query(self, query: str) -> List[float]:
        return await self._client.aembed_query(query)


# ============================================================
# POSTGRES CLIENT
# ============================================================
class PostgresClient:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> asyncpg.Pool:
        """Internal safe getter that handles lazy loading."""
        if self._pool:
            return self._pool
        
        async with self._lock:
            if self._pool is None:
                logger.info("Initializing PostgreSQL connection pool...")
                self._pool = await asyncpg.create_pool(
                    user=os.getenv("POSTGRES_USER"),
                    password=os.getenv("POSTGRES_PASSWORD"),
                    host=os.getenv("POSTGRES_HOST"),
                    port=os.getenv("POSTGRES_PORT"),
                    database=os.getenv("POSTGRES_DATABASE"),
                    min_size=1,   # Reduced to prevent connection exhaustion
                    max_size=5,   # Reduced from 30 - sufficient for most workloads
                    command_timeout=60,
                    max_inactive_connection_lifetime=300,  # Close idle connections after 5 min
                    server_settings={
                        "application_name": "MyFastMCPApp",
                        "tcp_keepalives_idle": "60",     # Ping every 60s if idle
                        "tcp_keepalives_interval": "30", # Retry every 30s if failed
                        "tcp_keepalives_count": "3"      # Give up after 3 tries
                    }
                )
            return self._pool

    async def initialize(self):
        """Eagerly initialize the connection pool at startup."""
        pool = await self._get_pool()
        # Verify connection works
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        logger.info("✓ PostgreSQL pool initialized and verified")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Yields a connection from the pool.
        USAGE:
            async with postgres.acquire() as conn:
                await conn.fetch(...)
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            yield conn

    async def close(self):
        """Cleanup method."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("✓ PostgreSQL pool closed")

# ============================================================
# REDIS CLIENT
# ============================================================
class RedisClient:
    """Redis client for cache operations with eager initialization."""
    
    def __init__(self):

        self._client = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            password=os.getenv("REDIS_PASSWORD"),
            ssl=True,
            decode_responses=True,
            socket_timeout=5,
            health_check_interval=30
        )
        logger.info("✓ Redis client initialized")
    
    @property
    def client(self):
        """Returns the Redis client instance."""
        return self._client
    
    def ping(self):
        """Verify Redis connection is working."""
        self._client.ping()
        logger.info("✓ Redis connection verified")

    def close(self):
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("✓ Redis connection closed")


# ============================================================
# DATAVERSE CLIENT
# ============================================================
class DataverseClient:
    """Dataverse client with Redis-based token caching and reusable HTTP client.
    
    Redis keys are shared across all services (chatbot, data_sync_workflow):
      - dataverse:access_token
      - dataverse:token_expiry
    """
    
    # Shared Redis keys (synced across mcp_server, data_sync_workflow, chatbot)
    REDIS_TOKEN_KEY = "dataverse:access_token"
    REDIS_EXPIRY_KEY = "dataverse:token_expiry"
    TOKEN_BUFFER_SECONDS = 300  # 5-minute safety buffer

    def __init__(self):
        self._lock = asyncio.Lock()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._expires_at: float = 0
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=60,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._http_client

    def _is_token_valid(self, token: Optional[str], expiry: float) -> bool:
        """Check if a token is present and not expired (with safety buffer)."""
        return bool(token) and time.time() < (expiry - self.TOKEN_BUFFER_SECONDS)

    def _store_in_redis(self, token: str, expiry: float) -> None:
        """Persist token + expiry in Redis. Non-fatal on failure."""
        try:
            r = redis_client.client
            ttl = max(int(expiry - time.time()), 60)  # floor at 60s
            r.setex(self.REDIS_TOKEN_KEY, ttl, token)
            r.setex(self.REDIS_EXPIRY_KEY, ttl, str(expiry))
            logger.debug("✅ Dataverse token stored in Redis (TTL=%ds)", ttl)
        except Exception as e:
            logger.warning(f"⚠️ Failed to store Dataverse token in Redis: {e}")

    def _load_from_redis(self) -> tuple:
        """Try to load token + expiry from Redis. Returns (None, 0) on miss."""
        try:
            r = redis_client.client
            token = r.get(self.REDIS_TOKEN_KEY)
            expiry_str = r.get(self.REDIS_EXPIRY_KEY)
            if token and expiry_str:
                return token, float(expiry_str)
        except Exception as e:
            logger.warning(f"⚠️ Failed to load Dataverse token from Redis: {e}")
        return None, 0.0

    async def _get_token(self) -> str:
        """
        3-tier token resolution:
          1. In-memory cache  (fastest, same-process)
          2. Redis cache      (cross-pod / cross-restart)
          3. Fresh Azure AD   (last resort)
        On fresh fetch → written to both memory AND Redis.
        """
        # ── Tier 1: In-memory cache ──
        if self._is_token_valid(self._token, self._expires_at):
            return self._token
        
        async with self._lock:
            # Double-check after acquiring lock
            if self._is_token_valid(self._token, self._expires_at):
                return self._token

            # ── Tier 2: Redis cache ──
            redis_token, redis_expiry = self._load_from_redis()
            if self._is_token_valid(redis_token, redis_expiry):
                self._token = redis_token
                self._expires_at = redis_expiry
                logger.info("✅ Dataverse token restored from Redis")
                return self._token

            # ── Tier 3: Fresh fetch from Azure AD ──
            tenant_id = os.getenv("AZURE_TENANT_ID")
            url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            
            client = await self._get_http_client()
            response = await client.post(url, data={
                "client_id": os.getenv("AZURE_CLIENT_ID"),
                "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
                "scope": os.getenv("AZURE_SCOPE"),
                "grant_type": "client_credentials",
            }, headers={"Content-Type": "application/x-www-form-urlencoded"})
            response.raise_for_status()
            token_data = response.json()
            
            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            expiry = time.time() + expires_in

            # Store in memory
            self._token = access_token
            self._expires_at = expiry

            # Store in Redis (non-fatal)
            self._store_in_redis(access_token, expiry)

            logger.info("✅ Dataverse token freshly fetched from Azure AD")
            return access_token
    
    async def get(self, endpoint: str) -> dict:
        """GET request to Dataverse."""
        token = await self._get_token()
        base_url = os.getenv("DATAVERSE_BASE_URL")
        
        client = await self._get_http_client()
        response = await client.get(
            f"{base_url}/{endpoint}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    async def post(self, endpoint: str, payload: dict) -> tuple[int, dict, dict]:
        """POST request to Dataverse. Returns (status_code, headers, body)."""
        token = await self._get_token()
        base_url = os.getenv("DATAVERSE_BASE_URL")
        
        client = await self._get_http_client()
        response = await client.post(
            f"{base_url}/{endpoint}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0"
            },
            json=payload
        )
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        return response.status_code, dict(response.headers), body
    
    async def patch(self, endpoint: str, payload: dict) -> tuple[int, str]:
        """PATCH request to Dataverse. Returns (status_code, response_text)."""
        token = await self._get_token()
        base_url = os.getenv("DATAVERSE_BASE_URL")
        
        client = await self._get_http_client()
        response = await client.patch(
            f"{base_url}/{endpoint}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "If-Match": "*"
            },
            json=payload
        )
        return response.status_code, response.text

    async def download_file(self, endpoint: str) -> bytes:
        """Download binary file content from Dataverse."""
        token = await self._get_token()
        base_url = os.getenv("DATAVERSE_BASE_URL")
        
        client = await self._get_http_client()
        response = await client.get(
            f"{base_url}/{endpoint}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.content
    
    async def delete(self, endpoint: str) -> tuple[int, str]:
        """DELETE request to Dataverse. Returns (status_code, response_text)."""
        token = await self._get_token()
        base_url = os.getenv("DATAVERSE_BASE_URL")
        
        client = await self._get_http_client()
        response = await client.delete(
            f"{base_url}/{endpoint}",
            headers={
                "Authorization": f"Bearer {token}",
            }
        )
        return response.status_code, response.text
    
    async def batch(self, operations: list) -> dict:
        """Execute multiple Dataverse operations in a single $batch request.
        
        Each operation dict should have:
            method: 'POST', 'PATCH', or 'DELETE'
            endpoint: e.g. 'zx_leads' or 'zx_leads(<guid>)'
            payload: dict (for POST/PATCH, omit for DELETE)
        
        Returns:
            { success: bool, results: [...] }
        """
        import uuid as _uuid
        import json as _json_mod
        
        token = await self._get_token()
        base_url = os.getenv("DATAVERSE_BASE_URL")
        
        batch_id = f"batch_{_uuid.uuid4().hex[:12]}"
        changeset_id = f"changeset_{_uuid.uuid4().hex[:12]}"
        
        # Build multipart body
        parts = []
        parts.append(f"--{batch_id}")
        parts.append(f"Content-Type: multipart/mixed; boundary={changeset_id}")
        parts.append("")
        
        for idx, op in enumerate(operations):
            method = op.get("method", "POST").upper()
            endpoint = op.get("endpoint", "")
            payload = op.get("payload", {})
            
            parts.append(f"--{changeset_id}")
            parts.append("Content-Type: application/http")
            parts.append("Content-Transfer-Encoding: binary")
            parts.append(f"Content-ID: {idx + 1}")
            parts.append("")
            parts.append(f"{method} {base_url}/{endpoint} HTTP/1.1")
            parts.append("Content-Type: application/json")
            parts.append("OData-MaxVersion: 4.0")
            parts.append("OData-Version: 4.0")
            
            if method in ("POST", "PATCH") and payload:
                body = _json_mod.dumps(payload)
                parts.append(f"Content-Length: {len(body)}")
                parts.append("")
                parts.append(body)
            else:
                parts.append("")
                parts.append("")
        
        parts.append(f"--{changeset_id}--")
        parts.append(f"--{batch_id}--")
        
        body_str = "\r\n".join(parts)
        
        client = await self._get_http_client()
        response = await client.post(
            f"{base_url}/$batch",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/mixed; boundary={batch_id}",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
            },
            content=body_str.encode("utf-8"),
        )
        
        status = response.status_code
        if status == 200:
            return {
                "success": True,
                "http_status": status,
                "operations_count": len(operations),
                "raw_response": response.text[:2000],
            }
        else:
            return {
                "success": False,
                "http_status": status,
                "error": response.text[:1000],
            }

    async def initialize(self):
        """Eagerly initialize HTTP client and fetch initial token."""
        await self._get_http_client()
        await self._get_token()  # Pre-fetch token
        logger.info("✓ Dataverse client initialized with token")

    async def close(self):
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("✓ Dataverse HTTP client closed")


# Global instances
embeddings = EmbeddingsClient()
postgres = PostgresClient()
redis_client = RedisClient()
dataverse = DataverseClient()