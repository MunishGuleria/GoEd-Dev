import asyncio
import json
import os
import logging
import datetime as _dt
from typing import Optional, Dict, Any
from langsmith import traceable
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, ToolMessage, AIMessageChunk
from langchain.messages import SystemMessage
from client.config import llm
from client.mcp_tools import mcpserver
from client.memory_manager import RedisMessageManager, RedisConnectionPool
from client.channel_config import get_channel_config
from client.session_logger import SessionLogger
from state import AgentContext
from client.trial_validator import is_trial_enabled

# Setup logging
logger = logging.getLogger(__name__)

# ==================== AGENT SINGLETONS ====================

# Channel-specific agent instances: {(channel, trial_id): agent}
_agent_instances: dict = {}
_agent_lock = asyncio.Lock()

# Cached prompts per (channel, trial_id)
_channel_prompts: dict = {}

# Cached tools per channel (needed for programmatic tool calls)
_channel_tools: dict = {}


# ==================== MIDDLEWARE (Class-based Pattern) ====================

class InjectRedisContext(AgentMiddleware):
    """Inject Redis conversation context + user info into system message.

    Uses LangChain's awrap_model_call hook (async, wrap-style).
    Appends context to the system message content blocks.
    """

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler,
    ) -> ModelResponse:
        """Async wrap-style hook that runs around each model call.

        Args:
            request: ModelRequest with state, runtime, system_message, messages
            handler: The next handler to call (the actual model call)

        Returns:
            ModelResponse from the handler
        """
        # Access AgentContext as object attributes (not dict)
        ctx = request.runtime.context
        session_id = getattr(ctx, 'session_id', None) if ctx else None
        if not session_id:
            return await handler(request)

        # Initialize session logger (only logs in dev mode)
        session_logger = SessionLogger(session_id)

        manager = RedisMessageManager(session_id)

        # Check for WhatsApp/Instagram/Facebook user info (stored by webhook)
        user_info = manager.get_user_info()

        # Log user info (dev mode only)
        session_logger.log_user_info(user_info)

        # Build context text to inject into system message
        context_parts = []

        # Remove explicit LLM instructions for trial_id, as it will be auto-injected by middleware
        # The auto-injection happens in HandleToolErrors below.

        # Initialize variables for cross-channel logic
        user_phone = "Unknown"
        source = "web"
        
        # IST date/time for task scheduling and prompt variables
        ist = _dt.timezone(_dt.timedelta(hours=5, minutes=30))
        now_ist = _dt.datetime.now(ist)
        current_date_str = now_ist.strftime('%A, %B %d, %Y')
        current_time_str = now_ist.strftime('%I:%M %p IST')
        current_date_iso = now_ist.strftime('%Y-%m-%d')

        context_parts.append(f"""
================================
CURRENT DATE/TIME (IST)
================================
Date: {current_date_str}
Time: {current_time_str}
Use this for scheduling tasks, filtering by date, and answering time-sensitive questions.

================================
PROMPT VARIABLE MAPPING
================================
{{{{current_date}}}}: {current_date_str}
{{{{current_time}}}}: {current_time_str}
{{{{date_iso}}}}: {current_date_iso}
""")

        # Add user info if available (WhatsApp/Instagram/Facebook)
        if user_info:
            user_name = user_info.get("name", "Unknown")
            user_phone = user_info.get("phone", "Unknown")
            source = user_info.get("source", "unknown")
            # Clean the sender_id for display to AI
            sender_id = user_info.get("sender_id", "")
            if ":" in sender_id:
                sender_id = sender_id.split(":")[0]

            context_parts.append(f"""
================================
USER PROFILE (Auto-captured from {source.upper()})
================================
Name: {user_name}
Phone: {user_phone}
Email: {user_info.get("email", "Unknown")}
City: {user_info.get("city", "Unknown")}
Sender ID: {sender_id}

QUALIFICATIONS:
- Highest Qualification: {user_info.get("highestqualification", "Unknown")}
- Undergraduate Course: {user_info.get("undergraduatecourse", "Unknown")}
- Graduation Year: {user_info.get("graduationyear", "Unknown")}
- Percentage: {user_info.get("thpercentage", "Unknown")}%

IMPORTANT: Do NOT ask for information already captured above.
Address them as "{user_name}".
DO NOT call check_senderid tool - it has already been handled automatically.""")

            # Counselor-specific context injection
            is_counselor = manager.redis.get(f"is_counselor:{session_id}")
            if is_counselor == "true":
                systemuserid = user_info.get("systemuserid", "")
                title = user_info.get("title", "")
                email = user_info.get("email", "")
                user_role = manager.redis.get(f"user_role:{session_id}") or "counselor"

                context_parts.append(f"""
================================
COUNSELOR IDENTITY
================================
Role: {user_role.upper()}
SystemUserID: {systemuserid}
Title: {title}
Email: {email}
IMPORTANT: Use SystemUserID as counselor_id when calling search_crm or batch_crm_operations.""")

                # Manager subordinates
                if user_role == "counselor_manager":
                    sub_ids = manager.redis.get(f"subordinate_ids:{session_id}") or ""
                    sub_names = manager.redis.get(f"subordinate_names:{session_id}") or ""
                    if sub_ids:
                        context_parts.append(f"""
================================
MANAGER CONTEXT
================================
Subordinate Counselor IDs: {sub_ids}
Subordinate Names: {sub_names}
Use these IDs as subordinate_ids parameter for team-wide CRM queries.""")


        # Add lead lookup results and previous context for ALL channels
        lead_id = manager.get_lead_id()
        lead_data = manager.get_existing_lead_data()
        
        if lead_id:
            context_parts.append(f"""
================================
LEAD IDENTIFIED (ID: {lead_id})
================================
System: The user has been identified. Do NOT ask for information already available below.""")
            
            # Use 'context' (from social leads) or 'previous_context' (from web leads)
            history_context = (lead_data.get("context") or lead_data.get("previous_context")) if lead_data else None
            
            if history_context:
                context_parts.append(f"""
================================
PREVIOUS CONVERSATION CONTEXT
================================
Summary of previous interactions:
{history_context}
================================""")

        # Add phone collection instruction for Instagram/Facebook when phone is unavailable
        if user_phone == "Unknown" and source in ["instagram", "facebook"]:
            # Check if we already looked up the lead
            senderid_status = manager.redis.get(f"senderid_status:{session_id}")
            
            if senderid_status == "found" and lead_id:
                # Already handled by general block above
                pass
            elif senderid_status == "not_found":
                 context_parts.append("""
================================
LEAD LOOKUP RESULT
================================
System: Lead lookup completed. Lead NOT found.
ACTION REQUIRED: You MUST collect user details (Name, Phone) to create a new lead.
Ask politely for their name and phone number.""")
            else:
                context_parts.append("""
================================
LEAD COLLECTION INSTRUCTION
================================
Create lead with provided information. Only ask for information that is not given in chat till now.""")

        # === FLOW HINT: Detect if last assistant message was a question ===
        try:
            all_messages_json = manager.redis.lrange(
                f"messages:list:{session_id}", 0, -1)
            if all_messages_json:
                messages = [json.loads(m) for m in all_messages_json]
                last_assistant = next(
                    (m for m in reversed(messages)
                     if m['role'].lower() == 'assistant'),
                    None
                )
                if last_assistant and last_assistant['content'].strip().endswith("?"):
                    context_parts.append("""
================================
FLOW HINT
================================
You just asked the user a question. If their response is short (1-3 words) or a numeric value (like 85%),
they are responding directly to YOUR pending question.

→ ACKNOWLEDGE the answer briefly (e.g., "Great!", "Got it").
→ Do NOT repeat your previous answer or question.
→ Do NOT call get_knowledge_base if you already have the answer.
→ Continue the flow: Ask for the next missing lead detail or move to course selection.
""")
        except Exception as e:
            logger.warning(f"Could not check for flow hint: {e}")

        # Add general instructions and conciseness rules
        context_parts.append("""
<Instructions>
- Carefully use the conversation history before responding.
- Reuse already provided information (name, contact details, preferences) without asking for it again.
- Respond ONLY to the user’s latest message while staying context-aware.
- Provide clear, direct, and accurate answers without repeating previous queries.
- NEVER repeat your own sentences or duplicate your output.

**CONCISENESS RULE:**
- If the user provides a short answer or a data point (like a percentage or "OK"), acknowledge it briefly and move to the NEXT logical question.
- Do NOT repeat the entire list of benefits or scholarships unless specifically asked again.
- Keep responses focused on the current turn.
</Instructions>
""")

        # Inject available courses for this college (fetched in background)
        try:
            college_guid = manager.redis.get(f"session_courses:{session_id}")
            if college_guid:
                courses_json = manager.redis.get(f"college_courses:{college_guid}")
                if courses_json:
                    courses_data = json.loads(courses_json)
                    courses_list = courses_data.get("courses", [])
                    if courses_list:
                        course_lines = "\n".join(
                            f"  - {c['name']} (ID: {c['guid']})" for c in courses_list
                        )
                        context_parts.append(f"""
================================
AVAILABLE COURSES FOR THIS COLLEGE
================================
College: {courses_data.get('college_name', 'Unknown')}
Courses offered:
{course_lines}

INSTRUCTIONS:
- When the user expresses interest in a specific course, check if it matches one of the courses above.
- If the course matches, note the course name for lead details (use the exact name as shown above).
- If the course is NOT in the list, inform the user that this specific course is not currently offered and suggest the closest alternatives from the list above.
- Do NOT make up courses that are not in this list.
""")
        except Exception as e:
            logger.warning(f"Could not inject college courses: {e}")

        # Fetch trial metadata for dynamic prompt interpolation
        metadata = {}
        if is_trial_enabled():
            metadata_raw = manager.redis.get(f"trial_metadata:{session_id}")
            if metadata_raw:
                try:
                    loaded = json.loads(metadata_raw)
                    if isinstance(loaded, str):
                        loaded = json.loads(loaded)
                    metadata = loaded if isinstance(loaded, dict) else {}
                except Exception:
                    pass

        # Normalize content blocks for the system message
        if hasattr(request.system_message, 'content_blocks'):
            blocks = list(request.system_message.content_blocks)
        elif isinstance(request.system_message.content, list):
            blocks = list(request.system_message.content)
        else:
            blocks = [{"type": "text", "text": str(request.system_message.content)}]

        # Interpolate variables dynamically on the fly
        new_content = []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block["text"]
                
                # Trial-specific prompt variables (static per trial - OK for caching)
                if is_trial_enabled():
                    col_name = metadata.get("college_name", "Zoxima University")
                    col_email = metadata.get("college_email", "info@zoxima.com")
                    col_phone = metadata.get("college_phone", "+91-9999988888")
                    col_website = metadata.get("college_website", "https://zoxima.com")
                    
                    text = text.replace("{{college_name}}", col_name)
                    text = text.replace("{{college_email}}", col_email)
                    text = text.replace("{{college_phone}}", col_phone)
                    text = text.replace("{{college_website}}", col_website)
                new_content.append({"type": "text", "text": text})
            else:
                new_content.append(block)

        # Anthropic prompt caching: mark the last static block for caching
        # This caches the base prompt (largest part) — ~90% cost reduction on input tokens
        from client.config import LLM_PROVIDER
        if LLM_PROVIDER == "anthropic" and new_content:
            last_static = new_content[-1]
            if isinstance(last_static, dict):
                last_static["cache_control"] = {"type": "ephemeral"}

        # Append execution context (dynamic per call — NOT cached)
        if context_parts:
            context_text = "\n".join(context_parts)
            session_logger.log_system_message(context_text)
            new_content.append({"type": "text", "text": context_text})

        new_system_message = SystemMessage(content=new_content)
        return await handler(request.override(system_message=new_system_message))


class HandleToolErrors(AgentMiddleware):
    """Handle tool execution errors gracefully and inject context variables"""

    async def awrap_tool_call(self, request, handler):
        from client.memory_manager import RedisMessageManager
        
        try:
            # INTERCEPT TOOL CALL TO AUTO-INJECT trial_id
            tool_name = request.tool_call.get('name')
            ctx = getattr(request.runtime, 'context', None)
            session_id = getattr(ctx, 'session_id', None) if ctx else None
            
            if session_id:
                manager = RedisMessageManager(session_id)
                
                if is_trial_enabled() and tool_name == "get_knowledge_base":
                    trial_user_id_raw = manager.redis.get(f"trial_user_id:{session_id}")
                    if trial_user_id_raw:
                        trial_user_id = trial_user_id_raw.decode('utf-8') if isinstance(trial_user_id_raw, bytes) else trial_user_id_raw
                        # Explicitly set trial_id directly in the args dict
                        if "args" not in request.tool_call:
                            request.tool_call["args"] = {}
                        request.tool_call["args"]["trial_id"] = trial_user_id
                        logger.info(f"💉 Auto-injected trial_id={trial_user_id} into get_knowledge_base tool call for session {session_id}")
                
                # Auto-inject session_id into check_lead so MCP can cache lead data in Redis
                elif tool_name == "check_lead":
                    if "args" not in request.tool_call:
                        request.tool_call["args"] = {}
                    request.tool_call["args"]["session_id"] = session_id
                    logger.info(f"💉 Auto-injected session_id into check_lead for session {session_id}")
                
                elif tool_name in ["create_lead", "create_social_media_lead", "update_lead"]:
                    # 1. Inject trial_id if available
                    trial_user_id_raw = manager.redis.get(f"trial_user_id:{session_id}")
                    if trial_user_id_raw:
                        trial_user_id = trial_user_id_raw.decode('utf-8') if isinstance(trial_user_id_raw, bytes) else trial_user_id_raw
                        if "args" not in request.tool_call:
                            request.tool_call["args"] = {}
                        request.tool_call["args"]["trial_id"] = trial_user_id

                    # 2. Inject college_guid from metadata
                    metadata_raw = manager.redis.get(f"trial_metadata:{session_id}")
                    if metadata_raw:
                        try:
                            import json
                            loaded = json.loads(metadata_raw)
                            if isinstance(loaded, str):
                                loaded = json.loads(loaded)
                            metadata = loaded if isinstance(loaded, dict) else {}
                            col_guid = metadata.get("dataverse_college_guid")
                            
                            if col_guid:
                                if "args" not in request.tool_call:
                                    request.tool_call["args"] = {}
                                request.tool_call["args"]["college_guid"] = col_guid
                                logger.info(f"💉 Auto-injected college_guid={col_guid} into {tool_name} tool call for session {session_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to parse metadata for college_guid injection: {e}")

            return await handler(request)
        except Exception as e:
            logger.warning(
                f"Tool error in {request.tool_call.get('name', 'unknown')}: {e}")
            return ToolMessage(
                content=f"Tool execution failed: {str(e)}",
                tool_call_id=request.tool_call.get("id")
            )


# ==================== AGENT FACTORY ====================

def _check_prompt_invalidation(cache_key: str) -> bool:
    """Check if a Redis invalidation flag exists for this channel's prompt.
    
    If found, clears ALL channels sharing the same prompt_id (e.g., instagram
    and facebook both use Prompt-7), deletes the flag, and returns True.
    """
    try:
        config = get_channel_config(cache_key)
        prompt_id = config.prompt_id
        
        redis = RedisConnectionPool.get_client()
        redis_key = f"prompt_invalidated:{prompt_id}"
        
        if redis.get(redis_key):
            # Find ALL channels that use this prompt_id and clear them all
            from client.channel_config import CHANNEL_CONFIGS
            for ch_name, ch_config in CHANNEL_CONFIGS.items():
                if ch_config.prompt_id == prompt_id:
                    _agent_instances.pop(ch_name, None)
                    _channel_prompts.pop(ch_name, None)
                    _channel_tools.pop(ch_name, None)
                    logger.info(f"🔄 Cleared cached agent for channel='{ch_name}'")
            
            # Delete the flag so it doesn't trigger again
            redis.delete(redis_key)
            
            logger.info(f"🔄 Prompt cache invalidated for prompt_id='{prompt_id}'. Affected channels will re-fetch from DB.")
            return True
    except Exception as e:
        logger.warning(f"⚠️ Error checking prompt invalidation: {e}")
    
    return False


async def get_or_create_agent(channel: str = "web", trial_id: Optional[str] = None, metadata: Optional[dict] = None):
    """
    Create a SINGLE channel-specific agent singleton per channel.
    Prompt interpolation takes place dynamically on each invocation 
    inside the InjectRedisContext middleware.
    
    Checks Redis for prompt invalidation flags before returning cached agents.
    """
    global _agent_instances, _channel_prompts, _channel_tools

    channel = channel.lower()
    cache_key = channel

    # Check for prompt invalidation BEFORE returning cached agent
    _check_prompt_invalidation(cache_key)

    # Return cached agent if exists (and wasn't just invalidated)
    if cache_key in _agent_instances:
        return _agent_instances[cache_key]

    async with _agent_lock:
        # Double-check after acquiring lock
        if cache_key in _agent_instances:
            return _agent_instances[cache_key]

        config = get_channel_config(channel)
        logger.info(f"Creating {channel.upper()} agent | prompt={config.prompt_id}")

        try:
            # Fetch tools from MCP with timeout protection
            client = await asyncio.wait_for(mcpserver(), timeout=30.0)
            all_tools = await asyncio.wait_for(client.get_tools(), timeout=30.0)

            # Filter tools for this channel
            selected_tools = [
                tool for tool in all_tools
                if tool.name in config.tools
            ]

            # Cache tools for programmatic access
            _channel_tools[channel] = selected_tools

            logger.info(
                f"Selected {len(selected_tools)} tools for {channel}: {[t.name for t in selected_tools]}")

            # Fetch channel-specific base prompt
            prompt_response = await asyncio.wait_for(
                client.get_prompt(
                    server_name="DB_MCP",
                    prompt_name="get_prompt",
                    arguments={"prompt_id": config.prompt_id}
                ),
                timeout=30.0
            )
            base_prompt = prompt_response[0].content

            # Extract version metadata if present (prefixed by MCP server)
            prompt_version = "unknown"
            if base_prompt and base_prompt.startswith("__PROMPT_VERSION:"):
                version_line, base_prompt = base_prompt.split("\n", 1)
                prompt_version = version_line.replace("__PROMPT_VERSION:", "").replace("__", "")

            # Log error if prompt not found or empty
            if not base_prompt or not base_prompt.strip():
                logger.error(f"❌ Prompt '{config.prompt_id}' returned empty")
            elif base_prompt.startswith("Error:"):
                logger.error(f"❌ Prompt '{config.prompt_id}' error: {base_prompt}")

            logger.info(f"📄 Prompt loaded: prompt_id={config.prompt_id}, version={prompt_version}")

            # Do NOT interpolate here. Interpolation happens live via middleware.
            _channel_prompts[cache_key] = base_prompt

            # Create agent with channel-specific configuration
            agent = create_agent(
                model=llm,
                tools=selected_tools,
                system_prompt=base_prompt,
                middleware=[
                    InjectRedisContext(),  # Class-based (documented pattern)
                    HandleToolErrors()     # Class-based (documented pattern)
                ],
                context_schema=AgentContext
            )

            _agent_instances[cache_key] = agent
            logger.info(f"✅ {channel.upper()} agent created successfully (Trial enabled: {is_trial_enabled()})")
            return agent

        except asyncio.TimeoutError:
            logger.error(
                f"⏰ {channel.upper()} agent initialization timed out (30s)")
            raise RuntimeError(
                f"MCP server took too long to respond for {channel} agent. Please try again.")


# ==================== QUERY PROCESSING ====================

@traceable(
    run_type="chain",
    name="process_query",
    project_name=os.getenv("LANGSMITH_PROJECT")
)
async def process_query(query: str, session_id: str, channel: str = "web", user_id: str = None):
    """
    Process query with channel-specific agent and middleware-based context injection.

    Args:
        query: User's message
        session_id: Session identifier
        channel: Channel identifier ("web", "whatsapp", etc.)
        user_id: User identifier (optional, extracted from session_id if not provided)
    """

    # Extract user_id from session_id if not provided
    # Assumes session_id format like "user123_timestamp" or just use session_id
    if not user_id:
        user_id = session_id.split("_")[0] if "_" in session_id else session_id

    # Initialize session logger (only logs in dev mode)
    session_logger = SessionLogger(session_id)

    # Get Redis manager for this session
    message_manager = RedisMessageManager(session_id)

    # Fetch trial info from Redis (ONLY if trial is enabled)
    trial_id = None
    metadata = {}
    if is_trial_enabled():
        trial_id_raw = message_manager.redis.get(f"trial_user_id:{session_id}")
        if trial_id_raw:
            trial_id = trial_id_raw.decode('utf-8') if isinstance(trial_id_raw, bytes) else trial_id_raw
            
        metadata_raw = message_manager.redis.get(f"trial_metadata:{session_id}")
        if metadata_raw:
            try:
                loaded = json.loads(metadata_raw)
                # Handle double-encoded JSON from Postgres JSONB -> dict -> string
                if isinstance(loaded, str):
                    loaded = json.loads(loaded)
                metadata = loaded if isinstance(loaded, dict) else {}
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse metadata from Redis: {e}")
                metadata = {}

    # ====== COUNSELOR ROUTING (WhatsApp only) ======
    if channel == "whatsapp":
        user_info = message_manager.get_user_info()
        phone = user_info.get("phone", "") if user_info else ""
        
        if phone:
            is_counselor_key = f"is_counselor:{session_id}"
            is_counselor = message_manager.redis.get(is_counselor_key)
            
            if is_counselor == "true":
                user_role = message_manager.redis.get(f"user_role:{session_id}")
                if user_role == "counselor_manager":
                    channel = "whatsapp_counselor_manager"
                else:
                    channel = "whatsapp_counselor"
                logger.info(f"➡️ [ROUTING] Cached: {channel} | Phone: {phone}")
            elif is_counselor == "false":
                logger.info(f"➡️ [ROUTING] Cached: STUDENT | Phone: {phone}")
            elif is_counselor is None:
                # First message — check via MCP tool
                logger.info(f"🔍 [ROUTING] Checking user type for {phone}")
                try:
                    client = await asyncio.wait_for(mcpserver(), timeout=10.0)
                    all_tools = await asyncio.wait_for(client.get_tools(), timeout=15.0)
                    check_tool = next((t for t in all_tools if t.name == "check_user_type"), None)
                    
                    tool_data = {}
                    if check_tool:
                        try:
                            result = await asyncio.wait_for(
                                check_tool.ainvoke({"phone": phone}), timeout=15.0
                            )
                            if isinstance(result, dict):
                                tool_data = result
                            elif isinstance(result, str):
                                tool_data = json.loads(result.replace("'", '"'))
                            elif isinstance(result, list) and len(result) > 0:
                                if hasattr(result[0], 'text'):
                                    tool_data = json.loads(getattr(result[0], 'text').replace("'", '"'))
                                elif isinstance(result[0], dict) and 'text' in result[0]:
                                    tool_data = json.loads(result[0]['text'].replace("'", '"'))
                        except Exception as inner_e:
                            logger.error(f"Failed to query/parse check_user_type: {inner_e}")
                    else:
                        logger.error("❌ check_user_type tool not found in MCP server")
                    
                    if tool_data and tool_data.get("user_type") in ("counselor", "counselor_manager"):
                        user_type = tool_data.get("user_type")
                        is_manager = user_type == "counselor_manager"
                        
                        if is_manager:
                            channel = "whatsapp_counselor_manager"
                        else:
                            channel = "whatsapp_counselor"
                        logger.info(f"🎓 [ROUTING] Detected: {user_type} | {tool_data.get('fullname')}")
                        
                        # Cache counselor status for 7 days
                        message_manager.redis.set(is_counselor_key, "true")
                        message_manager.redis.expire(is_counselor_key, 86400 * 7)
                        message_manager.redis.set(f"user_role:{session_id}", user_type)
                        message_manager.redis.expire(f"user_role:{session_id}", 86400 * 7)
                        
                        # Update user info with counselor details
                        message_manager.redis.hset(f"user_info:{session_id}", mapping={
                            "name": tool_data.get("fullname") or "",
                            "email": tool_data.get("email") or "",
                            "title": tool_data.get("title") or "",
                            "systemuserid": tool_data.get("systemuserid") or ""
                        })
                        
                        # Cache subordinate IDs for managers
                        if is_manager and tool_data.get("subordinates"):
                            sub_ids = ",".join(
                                s["systemuserid"] for s in tool_data["subordinates"]
                                if s.get("systemuserid")
                            )
                            sub_names = ",".join(
                                s["fullname"] for s in tool_data["subordinates"]
                                if s.get("fullname")
                            )
                            message_manager.redis.set(f"subordinate_ids:{session_id}", sub_ids)
                            message_manager.redis.set(f"subordinate_names:{session_id}", sub_names)
                            message_manager.redis.expire(f"subordinate_ids:{session_id}", 86400 * 7)
                            message_manager.redis.expire(f"subordinate_names:{session_id}", 86400 * 7)
                            logger.info(f"👔 [ROUTING] Cached {len(tool_data['subordinates'])} subordinate IDs")
                    else:
                        logger.info(f"👤 [ROUTING] Detected: STUDENT | Phone: {phone}")
                        message_manager.redis.set(is_counselor_key, "false")
                        message_manager.redis.expire(is_counselor_key, 86400)
                        
                except Exception as e:
                    logger.error(f"💥 [ROUTING] Error checking user type: {e}")

    # Get channel-specific agent (trial aware)
    agent = await get_or_create_agent(channel=channel, trial_id=trial_id, metadata=metadata)

    # Since prompt uses only channel, lookup via channel cache key
    cache_key = channel.lower()
        
    system_prompt = _channel_prompts.get(cache_key, "[Prompt not cached]")

    # Get context that will be injected
    context_text = message_manager.get_context_for_chat()

    # Start logging the interaction (dev mode only)
    session_logger.start_interaction(
        user_query=query,
        system_prompt=system_prompt,
        context=context_text
    )

    # Store user message in Redis (triggers summary if needed)
    await message_manager.add_message(
        "user",
        query,
        input_tokens=0,
        output_tokens=0
    )

    # ====== PROGRAMMATIC check_senderid (runs ONCE per session) ======
    # For Instagram/Facebook/WhatsApp: automatically call check_senderid on first message
    if channel in ["instagram", "facebook", "whatsapp"]:
        user_info = message_manager.get_user_info()
        
        # For WhatsApp, sender_id is usually 'phone'
        sender_id = user_info.get("sender_id") or user_info.get("phone") or ""
        senderid_flag_key = f"senderid_checked:{session_id}"

        if sender_id and not message_manager.redis.exists(senderid_flag_key):
            # Clean the sender_id for the tool call
            clean_sid = sender_id.split(":")[0] if ":" in sender_id else sender_id
            
            try:
                logger.info(
                    f"🔍 [AUTO] Calling check_senderid for {clean_sid} ({channel})")

                # Get the check_senderid tool from the cached channel tools
                channel_tools = _channel_tools.get(channel, [])
                check_senderid_tool = None
                for tool in channel_tools:
                    if tool.name == "check_senderid":
                        check_senderid_tool = tool
                        break

                if check_senderid_tool:
                    # Invoke the tool directly
                    result = await check_senderid_tool.ainvoke({
                        "sender_id": clean_sid,
                        "source": channel
                    })
                    logger.info(
                        f"✅ [AUTO] check_senderid completed for {sender_id}: {result}")

                    # ✅ FIX: Parse result and save lead_id if found
                    try:
                        # Handle MCP response format
                        result_data = result
                        if isinstance(result, list) and len(result) > 0:
                            item = result[0]
                            if hasattr(item, 'text'):
                                result_data = json.loads(item.text)
                            elif isinstance(item, dict) and 'text' in item:
                                result_data = json.loads(item['text'])

                        if isinstance(result_data, dict):
                            status = result_data.get("status")
                            if status == "found":
                                lead_id = result_data.get("lead_id")
                                if lead_id:
                                    message_manager.set_lead_id(lead_id)
                                    
                                    # Store full lead data for archive worker
                                    message_manager.set_existing_lead_data(result_data)
                                    
                                    # Update user_info in Redis so AI knows the details immediately
                                    updates = {
                                        "name": result_data.get("name") or "",
                                        "firstname": result_data.get("firstname") or "",
                                        "lastname": result_data.get("lastname") or "",
                                        "phone": result_data.get("phone") or "",
                                        "email": result_data.get("email") or "",
                                        "city": result_data.get("city") or "",
                                        "highestqualification": result_data.get("highestqualification") or "",
                                        "undergraduatecourse": result_data.get("undergraduatecourse") or "",
                                        "graduationyear": result_data.get("graduationyear") or "",
                                        "thpercentage": result_data.get("thpercentage") or "",
                                        "th": result_data.get("th") or "",
                                        "leadscore": result_data.get("leadscore") or "",
                                        "priority": result_data.get("priority") or "",
                                        "leadtype": result_data.get("leadtype") or "",
                                        "context": result_data.get("context") or "",
                                        "insta_sender_id": result_data.get("insta_sender_id") or "",
                                        "fb_sender_id": result_data.get("fb_sender_id") or ""
                                    }
                                    # Filter out empty/None values
                                    updates = {k: str(v) for k, v in updates.items() if v is not None and v != ""}
                                    if updates:
                                        message_manager.redis.hset(f"user_info:{session_id}", mapping=updates)
                                    
                                    logger.info(f"✅ [AUTO] Stored full lead details and user_info from check_senderid: {lead_id}")
                                    # Store explicit status for context injection
                                    message_manager.redis.set(f"senderid_status:{session_id}", "found")
                                    message_manager.redis.expire(f"senderid_status:{session_id}", 86400)
                                else:
                                    # Found but no lead_id? Treat as error or not_found
                                    message_manager.redis.set(f"senderid_status:{session_id}", "not_found")
                                    message_manager.redis.expire(f"senderid_status:{session_id}", 86400)
                            elif status == "not_found":
                                message_manager.redis.set(f"senderid_status:{session_id}", "not_found")
                                message_manager.redis.expire(f"senderid_status:{session_id}", 86400)
                            else:
                                message_manager.redis.set(f"senderid_status:{session_id}", "error")
                                message_manager.redis.expire(f"senderid_status:{session_id}", 86400)
                    except Exception as parse_err:
                        logger.warning(f"⚠️ [AUTO] Could not parse check_senderid result: {parse_err}")
                        message_manager.redis.set(f"senderid_status:{session_id}", "error") # Fallback
                else:
                    logger.warning(
                        f"⚠️ [AUTO] check_senderid tool not found in {channel} tools")

                # Set flag so it never runs again for this session
                message_manager.redis.set(senderid_flag_key, "true")
                message_manager.redis.expire(
                    senderid_flag_key, 86400)  # 24h expiry

            except Exception as e:
                logger.error(
                    f"❌ [AUTO] check_senderid failed for {sender_id}: {e}")
                # Set flag anyway to avoid retrying on every message
                message_manager.redis.set(senderid_flag_key, "true")
                message_manager.redis.expire(senderid_flag_key, 86400)

    full_response = ""
    # FIX #1: Accumulate tokens across ALL LLM calls (not just last)
    total_input_tokens = 0
    total_output_tokens = 0
    # FIX #4: Track pending tool args from AIMessage for logging
    pending_tool_args = {}  # {tool_call_id: {name, args}}

    # Get history for the agent state (last 10 messages)
    history = message_manager.get_full_transcript()
    formatted_history = []
    
    # Handle the fact that we already added the current query to Redis
    # We want messages BEFORE the current one
    if len(history) > 0:
        # history[-1] is the query we just added
        for msg in history[:-1]:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            if role == "user":
                formatted_history.append({"role": "user", "content": content})
            else:
                formatted_history.append({"role": "assistant", "content": content})

    # Track what we have already yielded to the client
    # (prevents chunks vs full messages from doubling the UI content)
    yielded_text = ""

    try:
        async for token, metadata in agent.astream(
            {"messages": formatted_history + [{"role": "user", "content": query}]},
            context={
                "session_id": session_id,
                "user_id": user_id,
                "channel": channel
            },
            stream_mode="messages"
        ):
            # ── FIX #1: Skip history messages being re-yielded from start node ──
            node = metadata.get('langgraph_node') if metadata else None
            if node == '__start__':
                continue

            # Only accumulate content from AIMessage
            if isinstance(token, AIMessage):
                # ── FIX #2: Deduplicate Chunks vs Full Messages ──────────────────
                # stream_mode="messages" yields chunks DURING generation AND 
                # the final full AIMessage at the end of the node.
                # Chunks are yielded additive during generation in some providers.
                
                is_chunk = isinstance(token, AIMessageChunk)
                
                # Emit tool_start event when AI is calling a tool
                if hasattr(token, 'tool_calls') and token.tool_calls:
                    for tool_call in token.tool_calls:
                        yield {
                            "type": "tool_start",
                            "tool_name": tool_call.get("name", "unknown"),
                            "tool_id": tool_call.get("id", "")
                        }

                if token.content:
                    # Extract text - GPT returns str, Claude returns list of content blocks
                    text = ""
                    if isinstance(token.content, str):
                        text = token.content
                    elif isinstance(token.content, list):
                        for block in token.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text += block.get("text", "")
                            elif isinstance(block, str):
                                text += block

                    if text:
                        # Find the new content to yield
                        # If a chunk, we just yield it (it's the delta)
                        # If a full message, we only yield what isn't in full_response yet
                        if is_chunk:
                            new_text = text
                        else:
                            # This is a full AIMessage re-yielded by LangGraph at node exit
                            # We only want the delta that wasn't already yielded by chunks
                            # Protect against negative slicing if for some reason yielded_text is longer
                            start_index = len(yielded_text)
                            new_text = text[start_index:] if len(text) > start_index else ""
                        
                        if new_text:
                            yielded_text += new_text
                            full_response += new_text
                            yield {
                                "type": "token",
                                "content": new_text,
                                "node": node or 'model'
                            }

                # FIX #1: Accumulate usage stats across ALL LLM calls
                if token.usage_metadata:
                    if isinstance(token.usage_metadata, dict):
                        total_input_tokens += token.usage_metadata.get(
                            "input_tokens", 0)
                        total_output_tokens += token.usage_metadata.get(
                            "output_tokens", 0)
                    else:
                        total_input_tokens += getattr(
                            token.usage_metadata, 'input_tokens', 0)
                        total_output_tokens += getattr(
                            token.usage_metadata, 'output_tokens', 0)

                # FIX #4: Capture tool args from AIMessage for later logging
                if hasattr(token, 'tool_calls') and token.tool_calls:
                    for tool_call in token.tool_calls:
                        tool_id = tool_call.get("id", "")
                        if tool_id:
                            pending_tool_args[tool_id] = {
                                "name": tool_call.get("name", "unknown"),
                                "args": tool_call.get("args", {})
                            }

            elif isinstance(token, ToolMessage):
                # ✅ FIX: Improved lead tracking - handles both "success" and "found" status
                if token.name in ["check_lead", "check_senderid", "create_lead", "create_social_media_lead"]:
                    try:
                        # Parse tool content for lead tracking
                        logger.debug(f"[LEAD TRACKING] Tool: {token.name}")
                        logger.debug(
                            f"[LEAD TRACKING] Raw content type: {type(token.content)}")
                        logger.debug(
                            f"[LEAD TRACKING] Raw content value: {token.content}")

                        data = token.content

                        # 2. Handle if it's a JSON string
                        if isinstance(data, str):
                            try:
                                data = json.loads(data)
                            except json.JSONDecodeError:
                                pass  # Keep as string if not JSON

                        # 3. Handle if it's a list (Standard MCP format)
                        # MCP results often come as: [TextContent(type='text', text='{"status": "success", ...}')]
                        if isinstance(data, list) and len(data) > 0:
                            item = data[0]
                            # Check if it has a 'text' attribute (Pydantic model) or 'text' key (dict)
                            if hasattr(item, 'text'):
                                try:
                                    data = json.loads(item.text)
                                except json.JSONDecodeError:
                                    data = item.text
                            elif isinstance(item, dict) and 'text' in item:
                                try:
                                    data = json.loads(item['text'])
                                except json.JSONDecodeError:
                                    data = item['text']
                            else:
                                data = item

                        # 4. Check for success/found status and capture lead_id
                        if isinstance(data, dict):
                            # ✅ FIX: check_senderid returns status="found" (not "success")
                            status = data.get("status")

                            if status in ["success", "found"]:
                                l_id = data.get("lead_id")
                                if l_id:
                                    # Save lead_id to Redis
                                    message_manager.set_lead_id(l_id)
                                    logger.info(
                                        f"✅ [LEAD TRACKING] {token.name} - Captured Lead ID: {l_id}")
                                    # Cache full lead info for archive worker anti-blank-override
                                    if token.name in ["check_lead", "check_senderid"]:
                                        message_manager.set_existing_lead_data(data)
                                        logger.info(
                                            f"📋 [LEAD TRACKING] Cached existing lead data for archive worker")
                                else:
                                    logger.warning(
                                        f"⚠️ [LEAD TRACKING] {token.name} - Status '{status}' but lead_id missing in response")
                            elif status == "not_found":
                                logger.info(
                                    f"ℹ️ [LEAD TRACKING] {token.name} - No existing lead found (expected for new users)")
                            else:
                                logger.info(
                                    f"ℹ️ [LEAD TRACKING] {token.name} - Status: {status}, Data: {data}")
                        else:
                            logger.warning(
                                f"⚠️ [LEAD TRACKING] {token.name} - Unexpected data format: {type(data)}")

                    except Exception as e:
                        logger.error(
                            f"❌ [LEAD TRACKING] {token.name} - Error parsing output: {e}", exc_info=True)

                # Emit tool results for UI visibility
                # Serialize properly as JSON to avoid Python single-quote issues
                tool_content = token.content
                if isinstance(tool_content, list):
                    # Convert list of dicts to proper JSON array
                    serialized_items = []
                    for item in tool_content:
                        if hasattr(item, 'model_dump'):
                            # Pydantic model - convert to dict
                            serialized_items.append(item.model_dump())
                        elif hasattr(item, '__dict__'):
                            # Object with __dict__
                            serialized_items.append(vars(item))
                        elif isinstance(item, dict):
                            serialized_items.append(item)
                        else:
                            serialized_items.append(str(item))
                    tool_content = json.dumps(serialized_items)
                elif isinstance(tool_content, dict):
                    tool_content = json.dumps(tool_content)
                elif not isinstance(tool_content, str):
                    tool_content = str(tool_content)

                # Log tool call with args (dev mode only)
                # FIX #4: Get args from pending_tool_args captured from AIMessage
                tool_call_id = getattr(token, 'tool_call_id', None)
                tool_args = None
                if tool_call_id and tool_call_id in pending_tool_args:
                    tool_args = pending_tool_args[tool_call_id].get("args")

                session_logger.log_tool_call(
                    tool_name=token.name or "unknown",
                    arguments=tool_args,
                    result=tool_content
                )

                yield {
                    "type": "tool_result",
                    "tool_name": token.name or "unknown",
                    "content": tool_content,
                    "node": metadata.get('langgraph_node', 'tools') if metadata else 'tools'
                }

    except asyncio.CancelledError:
        logger.warning(
            f"⚠️ Stream cancelled for session {session_id} - client likely disconnected")
        # Save partial response if any
        if full_response:
            await message_manager.add_message(
                "assistant",
                full_response + " [Response interrupted]",
                input_tokens=0,
                output_tokens=0
            )
        return  # Exit gracefully without re-raising

    except Exception as e:
        logger.error(f"❌ Streaming error for session {session_id}: {e}")
        yield {"type": "error", "error": str(e)}
        return

    # FIX #1: Use accumulated token counts (sums all LLM calls)
    input_tokens = total_input_tokens
    output_tokens = total_output_tokens

    await message_manager.add_message(
        "assistant",
        full_response,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )

    # End logging the interaction (dev mode only)
    session_logger.end_interaction(
        response=full_response,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )
