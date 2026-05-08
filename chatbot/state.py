from dataclasses import dataclass


@dataclass
class AgentContext:
    """Runtime context passed to agent.astream() - immutable per invocation.
    
    This is what gets passed to middleware via request.runtime.context
    """
    session_id: str      # Required: Redis session key
    user_id: str         # Required: User identifier  
    channel: str = "web" # Optional: Channel type (web, whatsapp, instagram, facebook)