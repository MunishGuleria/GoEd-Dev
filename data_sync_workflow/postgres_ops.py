"""
PostgreSQL operations for the archive worker.
Handles session/message insertions and prompt retrieval.
"""
import logging
from typing import Dict, List, Optional
from utils import now_ist, parse_dt

log = logging.getLogger("archive_worker")

async def flush_trial_message_count(postgres_client, redis_client, trial_user_id: str):
    """Atomically flush accumulated trial messages from Redis to PostgreSQL."""
    if not trial_user_id: return
    count_key = f"trial_msg_count:{trial_user_id}"
    import asyncio
    try:
        # Atomic GETSET - take current count and immediately reset to 0
        old_val = await asyncio.to_thread(redis_client.getset, count_key, 0)
        if not old_val:
            return
            
        count_to_add = int(old_val)
        if count_to_add <= 0:
            return
            
        async with postgres_client.acquire() as conn:
            # Update PostgreSQL
            await conn.execute(
                "UPDATE trial_users SET messages_used = messages_used + $1 WHERE id = $2::uuid",
                count_to_add, trial_user_id
            )
            # Fetch the actual total from PostgreSQL (authoritative source)
            row = await conn.fetchrow(
                "SELECT messages_used FROM trial_users WHERE id = $1::uuid",
                trial_user_id
            )
        
        # Update the Redis hash so next cache HIT shows correct count
        data_key = f"trial_data:{trial_user_id}"
        if await asyncio.to_thread(redis_client.exists, data_key):
            if row:
                actual_total = row["messages_used"]
                await asyncio.to_thread(redis_client.hset, data_key, "messages_used", str(actual_total))
                log.info(f"📊 Flushed {count_to_add} messages to PostgreSQL for trial {trial_user_id} (total now: {actual_total})")
            else:
                current = int(await asyncio.to_thread(redis_client.hget, data_key, "messages_used") or 0)
                await asyncio.to_thread(redis_client.hset, data_key, "messages_used", str(current + count_to_add))
                log.info(f"📊 Flushed {count_to_add} messages to PostgreSQL for trial {trial_user_id}")
        else:
            log.info(f"📊 Flushed {count_to_add} messages to PostgreSQL for trial {trial_user_id}")
    except Exception as e:
        log.error(f"Error flushing trial message count: {e}")
        # Add back to Redis if Postgres fails to avoid losing count
        if 'count_to_add' in locals():
            await asyncio.to_thread(redis_client.incrby, count_key, count_to_add)

# Default fallback prompt
DEFAULT_SUMMARY_PROMPT = """Summarize this chat session in 2-3 sentences:

USER MESSAGES:
{messages_text}

INSTRUCTIONS:
- Be concise and specific
- Include: what user asked, key info provided, outcome
- Return ONLY the summary, no extra text

Summary:"""


async def get_summary_prompt(postgres_client, prompt_id: str, cache: dict) -> str:
    """
    Retrieve prompt from PostgreSQL by prompt_id.
    Uses the provided cache dict to store the result for reuse during the run.
    Cache is passed externally so it resets each scheduler cycle.
    """
    if "prompt" in cache:
        return cache["prompt"]
    
    try:
        log.info(f"📄 Retrieving prompt: {prompt_id}")
        async with postgres_client.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT prompt_text
                FROM public.prompts
                WHERE prompt_id = $1
                ORDER BY version DESC
                LIMIT 1
                """,
                prompt_id
            )
        
        if row:
            cache["prompt"] = row["prompt_text"]
            log.info("✅ Summary prompt loaded from database")
        else:
            log.warning(f"⚠️ {prompt_id} not found. Using default.")
            cache["prompt"] = DEFAULT_SUMMARY_PROMPT
            
    except Exception as e:
        log.error(f"❌ Error retrieving prompt: {e}. Using default.")
        cache["prompt"] = DEFAULT_SUMMARY_PROMPT
    
    return cache["prompt"]


async def insert_session(conn, data: Dict) -> bool:
    """
    Insert session record into Postgres.
    Uses UPSERT to handle duplicates.
    """
    ts = now_ist()
    await conn.execute(
        """
        INSERT INTO sessions (session_id, session_started_at, created_on, last_activity_at, 
            updated_on, summary, user_message_count, total_message_count, 
            total_input_tokens, total_output_tokens, source, trial_user_id, trial_type)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        ON CONFLICT (session_id) DO UPDATE SET
            last_activity_at = EXCLUDED.last_activity_at, updated_on = EXCLUDED.updated_on,
            summary = EXCLUDED.summary, user_message_count = EXCLUDED.user_message_count,
            total_message_count = EXCLUDED.total_message_count,
            total_input_tokens = EXCLUDED.total_input_tokens,
            total_output_tokens = EXCLUDED.total_output_tokens,
            source = EXCLUDED.source,
            trial_user_id = COALESCE(EXCLUDED.trial_user_id, sessions.trial_user_id),
            trial_type = COALESCE(EXCLUDED.trial_type, sessions.trial_type)
        """,
        data["session_id"],
        data["created_at"],
        ts,
        data["last_activity"],
        ts,
        data["summary"],
        data["user_message_count"],
        data["total_messages"],
        data["input_tokens"],
        data["output_tokens"],
        data.get("source", "Website"),  # Default to Website if missing
        data.get("trial_user_id"),      # UUID or None
        data.get("trial_type"),         # trial_type_enum or None
    )
    return True


async def insert_messages(conn, session_id: str, messages: List[Dict], batch_size: int = 50) -> bool:
    """
    Bulk insert messages using COPY (10-100x faster than executemany).
    Uses delete-then-insert for idempotency since COPY doesn't support ON CONFLICT.
    """
    ts = now_ist()
    
    # Delete existing messages for this session (idempotency)
    await conn.execute(
        "DELETE FROM session_messages WHERE session_id = $1",
        session_id
    )
    
    # Prepare all records
    records = [
        (
            session_id,
            i,
            m.get("role"),
            m.get("content"),
            m.get("tokens", {}).get("input", 0),
            m.get("tokens", {}).get("output", 0),
            parse_dt(m.get("timestamp")) or ts,
            ts,
            ts,
        )
        for i, m in enumerate(messages)
    ]
    
    # Bulk insert using COPY (single round-trip for all messages)
    await conn.copy_records_to_table(
        'session_messages',
        records=records,
        columns=[
            'session_id', 'message_order', 'role', 'content',
            'input_tokens', 'output_tokens', 'message_timestamp',
            'created_on', 'updated_on'
        ]
    )
    return True


async def archive_to_postgres(postgres_client, data: Dict, batch_size: int = 50) -> bool:
    """
    Full PostgreSQL archival: session + messages in single transaction.
    """
    async with postgres_client.acquire() as conn:
        async with conn.transaction():
            await insert_session(conn, data)
            await insert_messages(conn, data["session_id"], data["messages"], batch_size)
    return True


async def batch_archive_to_postgres(postgres_client, sessions: List[Dict], chunk_size: int = 50) -> List[Dict]:
    """
    Chunked batch archival: processes sessions in chunks for optimal performance.
    
    - Chunks of 50 sessions (configurable)
    - Single DELETE + COPY per chunk
    - O(N/chunk) queries instead of O(N)
    
    Returns list of results: [{sid, success, error}, ...]
    """
    from utils import now_ist, parse_dt
    
    results = []
    
    for i in range(0, len(sessions), chunk_size):
        chunk = sessions[i:i+chunk_size]
        chunk_results = []
        
        try:
            async with postgres_client.acquire() as conn:
                async with conn.transaction():
                    ts = now_ist()
                    
                    # 1. Insert all sessions in chunk
                    for data in chunk:
                        await insert_session(conn, data)
                    
                    # 2. Collect all session IDs and messages
                    chunk_sids = [d["session_id"] for d in chunk]
                    all_records = []
                    
                    for data in chunk:
                        sid = data["session_id"]
                        for j, m in enumerate(data["messages"]):
                            all_records.append((
                                sid,
                                j,
                                m.get("role"),
                                m.get("content"),
                                m.get("tokens", {}).get("input", 0),
                                m.get("tokens", {}).get("output", 0),
                                parse_dt(m.get("timestamp")) or ts,
                                ts,
                                ts,
                            ))
                    
                    # 3. Single DELETE for all sessions in chunk
                    await conn.execute(
                        "DELETE FROM session_messages WHERE session_id = ANY($1)",
                        chunk_sids
                    )
                    
                    # 4. Single COPY for all messages in chunk
                    if all_records:
                        await conn.copy_records_to_table(
                            'session_messages',
                            records=all_records,
                            columns=[
                                'session_id', 'message_order', 'role', 'content',
                                'input_tokens', 'output_tokens', 'message_timestamp',
                                'created_on', 'updated_on'
                            ]
                        )
                    
                    # Mark all as successful
                    for data in chunk:
                        chunk_results.append({"sid": data["session_id"], "success": True, "error": None})
        
        except Exception as e:
            # Chunk failed - mark all sessions in chunk as failed
            for data in chunk:
                chunk_results.append({"sid": data["session_id"], "success": False, "error": str(e)})
        
        results.extend(chunk_results)
    
    return results