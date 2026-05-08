import json
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import redis
import asyncio
from langchain_core.messages import HumanMessage
from client.config import llm

# Setup logging
logger = logging.getLogger(__name__)

# Indian Standard Time (IST) - UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

# ==================== REDIS CONNECTION ====================

class RedisConnectionPool:
    """Singleton Redis connection pool."""
    _instance: Optional[redis.Redis] = None

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
                health_check_interval=30
            )
        return cls._instance

    @classmethod
    def close(cls):
        if cls._instance:
            cls._instance.close()
            cls._instance = None


# ==================== MESSAGE MANAGER ====================

class RedisMessageManager:
    """
    Store messages with per-message token tracking.

    Rolling summary pattern:
    - Messages 1-5 (USER): Agent sees raw messages only
    - Summary created after message 5
    - Messages 6-10 (USER): Agent sees SUMMARY + raw messages 6-10
    - Summary updated after message 10
    - Messages 11-15 (USER): Agent sees NEW SUMMARY + raw messages 11-15
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.redis = RedisConnectionPool.get_client()

        # Keys
        self.messages_list_key = f"messages:list:{session_id}"
        self.summary_key = f"summary:{session_id}"
        self.user_message_count_key = f"user_count:{session_id}"
        self.last_summarized_index_key = f"last_summarized_index:{session_id}"
        self.message_count_key = f"count:{session_id}"
        self.summary_in_progress_key = f"summary_in_progress:{session_id}"
        self.last_activity_key = f"last_activity:{session_id}"
        self.created_at_key = f"created_at:{session_id}"
        self.lead_id_key = f"lead_id:{session_id}"
        self.existing_lead_data_key = f"existing_lead_data:{session_id}"

        # Settings
        self.summary_batch_size = 5  # Summarize every 5 USER messages
        self.ttl = 86400 * 2  # 2 days
        self.summary_timeout = 30  # Max 30 seconds to wait for summary

    def set_lead_id(self, lead_id: str):
        """Store lead_id in Redis for this session."""
        self.redis.setex(self.lead_id_key, self.ttl, lead_id)

    def get_lead_id(self) -> Optional[str]:
        """Retrieve lead_id for this session."""
        return self.redis.get(self.lead_id_key)

    def set_existing_lead_data(self, lead_data: dict):
        """Cache full lead info from check_lead in Redis for archive worker."""
        self.redis.setex(self.existing_lead_data_key, self.ttl, json.dumps(lead_data))

    def get_existing_lead_data(self) -> Optional[dict]:
        """Retrieve cached lead data."""
        data = self.redis.get(self.existing_lead_data_key)
        if data:
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def get_user_info(self) -> Optional[Dict[str, str]]:
        """Retrieve user info (name, phone, source) for this session.
        
        User info should be stored by webhook when user first connects.
        Format in Redis:
            key: user_info:{session_id}
            value: hash with {name, phone, source}
        
        Used by middleware to inject user context into LLM system message.
        
        Returns:
            Dict with user profile data or None if not found
        """
        try:
            user_info_key = f"user_info:{self.session_id}"
            user_info_data = self.redis.hgetall(user_info_key)
            
            if user_info_data:
                logger.info(f"✅ User info found: {list(user_info_data.keys())}")
            else:
                logger.debug(f"⚠️ No user info for session {self.session_id}")
                
            return user_info_data if user_info_data else None
        except Exception as e:
            logger.warning(f"Could not fetch user info for {self.session_id}: {e}")
            return None

    async def add_message(
        self,
        role: str,
        content: str,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> Dict:
        """
        Add message with exact token counts.
        Trigger rolling summary every 5 USER messages.
        """
        # If previous summary is still processing, wait for it
        if role.lower() == 'user':
            await self._wait_for_summary_if_needed()

        message = {
            "timestamp": datetime.now(IST).isoformat(),
            "role": role,
            "content": str(content),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }

        # OPTIMIZED PIPELINE: All operations in one batch
        current_time = datetime.now(IST).isoformat()
        pipe = self.redis.pipeline()
        
        # 1. Store message
        pipe.rpush(self.messages_list_key, json.dumps(message))
        pipe.expire(self.messages_list_key, self.ttl)
        
        # 2. Increment total message counter
        pipe.incr(self.message_count_key)
        pipe.expire(self.message_count_key, self.ttl)
        
        # 3. Increment user message counter (if user message)
        if role.lower() == 'user':
            pipe.incr(self.user_message_count_key)
            pipe.expire(self.user_message_count_key, self.ttl)
        
        # 4. Update last_activity (for all messages - user or assistant)
        pipe.setex(self.last_activity_key, self.ttl, current_time)
        
        # 5. Set created_at if this is the first message (only set if doesn't exist)
        pipe.set(self.created_at_key, current_time, ex=self.ttl, nx=True)
        
        # Execute all operations at once
        results = pipe.execute()
        
        # OPTIMIZATION: Extract user_count from pipeline results
        # No need for separate redis.get() call
        if role.lower() == 'user':
            user_count = results[4]  # Get user count from pipeline
            
            # Trigger summary if needed
            if user_count > 0 and user_count % self.summary_batch_size == 0:
                await self._async_rolling_summarize()
        
        return message

    async def _wait_for_summary_if_needed(self):
        """
        Check if summary is in progress.
        If yes, wait for it to complete (with timeout).
        This ensures message 6+ waits for summary from message 5.
        """
        wait_time = 0
        check_interval = 0.1  # Check every 100ms

        while wait_time < self.summary_timeout:
            # Check if summary is being processed
            summary_in_progress = self.redis.get(self.summary_in_progress_key)

            if not summary_in_progress:
                # Summary completed or never started
                return

            # Wait before checking again
            try:
              await asyncio.shield(asyncio.sleep(check_interval))
            except asyncio.CancelledError:
              return
            wait_time += check_interval

        # Timeout reached, proceed anyway
        # FIX #3: Clean up stale flag to prevent future requests from waiting on orphaned lock
        self.redis.delete(self.summary_in_progress_key)
        logger.warning(
            f"Summary took too long (>{self.summary_timeout}s), cleaned up stale flag and proceeding")

    async def _async_rolling_summarize(self):
        """
        Rolling Summary: Last 5 USER messages -> New summary.
        Sets a flag while processing so message 6+ can wait for it.
        """
        try:
            # Mark summary as in progress
            self.redis.setex(self.summary_in_progress_key,self.summary_timeout, "1")

            # Fetch all messages
            all_messages_json = self.redis.lrange(self.messages_list_key, 0, -1)

            if not all_messages_json:
                return

            all_messages = [json.loads(m) for m in all_messages_json]

            # Filter for USER messages only
            user_messages = [
                m for m in all_messages if m['role'].lower() == 'user']

            if not user_messages:
                return

            # Get last 5 user messages
            last_5_user_messages = user_messages[-5:]

            existing_summary = self.redis.get(self.summary_key) or "No previous context."

            # Format ONLY user messages for summarization
            text_to_summarize = "\n".join([
                f"{i+1}. {m['content']}" for i, m in enumerate(last_5_user_messages)
            ])

            summary_prompt = f"""You are a summary assistant. Extract key information from user messages.

            PREVIOUS SUMMARY:
            {existing_summary}

            USER MESSAGES (Last 5):
            {text_to_summarize}

            TASK:
            Create a concise summary (2-3 sentences). Include:
            - User name (if provided)
            - Contact details (if provided)
            - Always include name and phone in summary.
            - What they're asking for
            - Any preferences mentioned

            Be factual and specific. Do not repeat information from previous summary unless updated except phone and name. Contact details should always be included in each summary created if given by user."""

            # Call LLM - await for completion
            response = await asyncio.shield(
                llm.ainvoke([HumanMessage(content=summary_prompt)])
           )

            new_summary = response.content

            # OPTIMIZED: Use pipeline for multiple writes
            pipe = self.redis.pipeline()
            
            # Save new summary
            pipe.setex(self.summary_key, self.ttl, new_summary)
            
            # Track the INDEX of the last message that was summarized
            last_summarized_message = last_5_user_messages[-1]
            last_summarized_index = all_messages.index(last_summarized_message)
            pipe.setex(
                self.last_summarized_index_key,
                self.ttl,
                str(last_summarized_index)
            )
            
            # Execute both writes at once
            pipe.execute()

            logger.info(f"Summary completed for session {self.session_id}")
            logger.debug(f"Summary: {new_summary}")

        except asyncio.CancelledError:
              self.redis.delete(self.summary_in_progress_key)
              return

        except Exception as e:
              logger.error(f"Summary error: {e}")

        finally:
              self.redis.delete(self.summary_in_progress_key)


    def get_context_for_chat(self, exclude_last: bool = False) -> str:
        """
        Get context for agent with intelligent message splitting.

        Pattern:
        - If no summary: Show raw recent user messages (last 5)
        - If summary exists: Show SUMMARY + ALL messages AFTER the summarized point

        IMPORTANT: Include ALL conversation after summary point, not just user messages
        
        Args:
            exclude_last: If True, the very last message in Redis is skipped 
                         (use this if you're already passing the query as the current message).
        """
        try:
            all_messages_json = self.redis.lrange(
                self.messages_list_key, 0, -1)

            if not all_messages_json:
                return ""

            all_messages = [json.loads(m) for m in all_messages_json]
            
            # Optionally exclude the last message if it's already being provided as the current query
            if exclude_last and len(all_messages) > 0:
                all_messages = all_messages[:-1]

            # Get all user messages for fallback (if no summary)
            user_messages = [
                m for m in all_messages if m['role'].lower() == 'user']

            if not user_messages:
                return ""

            summary = self.redis.get(self.summary_key)
            last_summarized_index_str = self.redis.get(
                self.last_summarized_index_key)

            # Build context based on whether summary exists
            context_parts = []

            if summary and last_summarized_index_str:
                # Summary exists: Show SUMMARY + all recent messages (both user and assistant)
                context_parts.append(f"### Context Summary\n{summary}")

                last_summarized_index = int(last_summarized_index_str)

                # Get ALL messages after the summarized point (not just user messages)
                recent_messages = all_messages[last_summarized_index + 1:]

                if recent_messages:
                    recent_text = "\n".join([
                        f"{m['role'].upper()}: {m['content']}" for m in recent_messages
                    ])
                    context_parts.append(
                        f"### Recent Conversation\n{recent_text}")
            else:
                # No summary yet: Show recent messages (User + Assistant) to preserve flow
                # FIX: Previously only showed user messages, causing AI to forget its own questions
                recent_messages = all_messages[-10:] if all_messages else []

                if recent_messages:
                    recent_text = "\n".join([
                        f"{m['role'].upper()}: {m['content']}" for m in recent_messages
                    ])
                    context_parts.append(f"### Recent Conversation\n{recent_text}")

            return "\n\n".join(context_parts) if context_parts else ""
        except Exception as e:
            logger.error(f"Error in get_context_for_chat: {e}")
            return ""

    def get_full_transcript(self) -> List[Dict]:
        """
        Get complete transcript from start to end with all message data and exact tokens.
        """
        try:
            all_messages_json = self.redis.lrange(
                self.messages_list_key, 0, -1)
            messages = [json.loads(m) for m in all_messages_json]
            return messages
        except Exception as e:
            return []

    def get_transcript_formatted(self) -> str:
        """
        Get formatted transcript for display.
        """
        messages = self.get_full_transcript()
        if not messages:
            return "No messages yet."

        lines = []
        for idx, msg in enumerate(messages, 1):
            role = msg['role'].upper()
            content = (msg['content'][:60] + "...") if len(msg['content']) > 60 else msg['content']
            input_tokens = msg.get('tokens', {}).get('input', 0)
            output_tokens = msg.get('tokens', {}).get('output', 0)
            total_tokens = msg.get('tokens', {}).get('total', 0)

            lines.append(
                f"{idx:2d}. {role:10} | {content:65} | "
                f"In: {input_tokens:5d} | Out: {output_tokens:5d} | Total: {total_tokens:5d}"
            )

        return "\n".join(lines)

    def get_session_stats(self) -> Dict:
        """
        Get session statistics including message counts and token usage.
        
        OPTIMIZED: Use pipeline to fetch multiple keys at once
        """
        try:
            # OPTIMIZATION: Fetch multiple keys in one pipeline
            pipe = self.redis.pipeline()
            pipe.lrange(self.messages_list_key, 0, -1)  # All messages
            pipe.get(self.user_message_count_key)        # User count
            pipe.get(self.message_count_key)             # Total count
            pipe.get(self.summary_key)                   # Summary
            
            # Execute all at once
            results = pipe.execute()
            
            # Extract results
            all_messages_json = results[0]
            user_count = int(results[1] or 0)
            total_count = int(results[2] or 0)
            summary = results[3]
            
            # Parse messages
            transcript = [json.loads(m) for m in all_messages_json] if all_messages_json else []

            # Calculate token totals
            total_input_tokens = sum(m.get('tokens', {}).get('input', 0) for m in transcript)
            total_output_tokens = sum(m.get('tokens', {}).get('output', 0) for m in transcript)
            total_tokens = sum(m.get('tokens', {}).get('total', 0) for m in transcript)

            return {
                "session_id": self.session_id,
                "user_messages": user_count,
                "total_messages": total_count,
                "assistant_messages": total_count - user_count,
                "summary": summary,
                "tokens": {
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                    "total": total_tokens
                },
                "message_count": len(transcript)
            }
        except Exception as e:
            return {
                "error": str(e)
            }

    def clear_session(self):
        """
        Delete all session data from Redis.
        
        OPTIMIZED: Use pipeline for batch deletion
        """
        # OPTIMIZATION: Delete multiple keys in one pipeline
        pipe = self.redis.pipeline()
        pipe.delete(
            self.messages_list_key,
            self.summary_key,
            self.message_count_key,
            self.user_message_count_key,
            self.last_summarized_index_key,
            self.summary_in_progress_key,
            self.last_activity_key,
            self.created_at_key,
            self.lead_id_key,
            f"session_initialized:{self.session_id}"
        )
        pipe.execute()