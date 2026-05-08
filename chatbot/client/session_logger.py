"""
Session-based debug logging for development mode.

Creates per-session log files with consolidated debugging information.
Only active when APP_ENV=development.

Log Format:
1. SYSTEM MESSAGE - The LLM prompt
2. INPUT - User message  
3. TOOL CALLS - Any tool invocations
4. OUTPUT - Assistant response
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, List

# Indian Standard Time (IST) - UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))


class SessionLogger:
    """Per-session debug logger - only active in development mode.
    
    Creates a single log file per session with format:
    1. SYSTEM MESSAGE: LLM prompt
    2. INPUT: User message with token count
    3. TOOL CALLS: Tool invocations and results
    4. OUTPUT: Assistant response
    
    Usage:
        logger = SessionLogger(session_id)
        logger.start_interaction(user_query, system_prompt, context)
        logger.log_tool_call(name, args, result)
        logger.end_interaction(response, input_tokens, output_tokens)
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.enabled = os.getenv("APP_ENV", "production").lower() == "development"
        
        # ✅ FIX: Sanitize session_id for Windows-compatible filenames
        # Replace colons and other invalid characters with hyphens
        safe_session_id = session_id.replace(":", "-").replace("/", "-").replace("\\", "-")
        
        # Base logs directory (relative to chatbot folder)
        base_dir = Path(__file__).parent.parent / "logs"
        self.log_dir = base_dir
        self.log_file = base_dir / f"sess_{safe_session_id}.log"
        
        # Pending data for current interaction
        self._pending_system_msg = None
        self._pending_context = None
        self._pending_query = None
        self._pending_tools = []
        
        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in IST."""
        return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    
    def _write(self, content: str):
        """Write content to log file."""
        if not self.enabled:
            return
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(content)
    
    def start_interaction(
        self,
        user_query: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ):
        """Start logging a new interaction.
        
        Args:
            user_query: Current user message
            system_prompt: Base LLM system prompt
            context: Injected context (user info, conversation history)
        """
        if not self.enabled:
            return
        
        self._pending_query = user_query
        self._pending_system_msg = system_prompt
        self._pending_context = context
        self._pending_tools = []
        
        timestamp = self._get_timestamp()
        
        # Write header
        entry = f"""
{'='*60}
[{timestamp}] SESSION: {self.session_id}
{'='*60}

"""
        
        # 1. SYSTEM MESSAGE (prompt)
        entry += "--- SYSTEM MESSAGE ---\n"
        if system_prompt:
            entry += f"{system_prompt}\n"
        else:
            entry += "[No system prompt available]\n"
        
        # Add injected context if any
        if context:
            entry += f"\n[Injected Context]\n{context}\n"
        
        # 2. INPUT (user message)
        entry += f"\n--- INPUT ---\nUSER: {user_query}\n"
        
        self._write(entry)
    
    def log_tool_call(self, tool_name: str, arguments: Any, result: Any):
        """Log a tool invocation.
        
        Args:
            tool_name: Name of the tool called
            arguments: Arguments passed to the tool
            result: Result returned by the tool
        """
        if not self.enabled:
            return
        
        timestamp = self._get_timestamp()
        
        # Format arguments
        args_str = "None"
        if arguments:
            args_str = json.dumps(arguments, indent=2, ensure_ascii=False, default=str)
        
        # Format result (truncate if too long)
        result_str = "None"
        if result:
            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) > 500:
                result_str = result_str[:500] + "... [truncated]"
        
        entry = f"""
--- TOOL CALL [{timestamp}] ---
TOOL: {tool_name}
ARGS: {args_str}
RESULT: {result_str}
"""
        self._write(entry)
        self._pending_tools.append({"name": tool_name, "args": arguments, "result": result})
    
    def end_interaction(
        self, 
        response: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ):
        """End the interaction and log the response.
        
        Args:
            response: Assistant's response
            input_tokens: Input token count
            output_tokens: Output token count
        """
        if not self.enabled:
            return
        
        token_info = ""
        if input_tokens:
            token_info += f" | Input tokens: {input_tokens}"
        if output_tokens:
            token_info += f" | Output tokens: {output_tokens}"
        
        entry = f"""
--- OUTPUT{token_info} ---
ASSISTANT: {response}

"""
        self._write(entry)
        
        # Clear pending data
        self._pending_query = None
        self._pending_system_msg = None
        self._pending_context = None
        self._pending_tools = []
    
    def log_user_info(self, user_info: Optional[Dict[str, str]]):
        """Log user profile data."""
        if not self.enabled or not user_info:
            return
        
        timestamp = self._get_timestamp()
        entry = f"\n--- USER INFO [{timestamp}] ---\n{json.dumps(user_info, indent=2, ensure_ascii=False)}\n"
        self._write(entry)
    
    # ==================== LEGACY METHODS (for backward compatibility) ====================
    
    def log_system_message(self, content: str):
        """Legacy: Store system message for later use."""
        self._pending_system_msg = content
    
    def log_context(self, context: str):
        """Legacy: Store context for later use."""
        self._pending_context = context
    
    def log_request(self, query: str):
        """Legacy: Start interaction with just the query."""
        self._pending_query = query
        # Note: Will be written when end_interaction is called
    
    def log_response(self, response: str):
        """Legacy: End interaction with the response."""
        if not self.enabled:
            return
        
        # If we have pending data, write the full interaction
        if self._pending_query:
            self.start_interaction(
                user_query=self._pending_query,
                system_prompt=self._pending_system_msg,
                context=self._pending_context
            )
        
        self.end_interaction(response)


def is_dev_mode() -> bool:
    """Check if running in development mode."""
    return os.getenv("APP_ENV", "production").lower() == "development"