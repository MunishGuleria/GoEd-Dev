import os
import logging
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# Environment mode (development/production)
APP_ENV = os.getenv("APP_ENV", "production").lower()

def is_dev_mode() -> bool:
    """Check if running in development mode."""
    return APP_ENV == "development"

# Admin API Key for protected endpoints
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

# ==================== LLM PROVIDER SELECTION ====================

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure_openai").lower()

def _create_llm():
    """Create LLM instance based on LLM_PROVIDER env var.
    
    Supported providers:
        - azure_openai (default): Uses AzureChatOpenAI with AZURE_OPENAI_* env vars
        - anthropic: Uses ChatAnthropic with ANTHROPIC_* env vars
    """
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        logger.info(f"🤖 Using Anthropic provider | model={os.getenv('ANTHROPIC_MODEL', 'claude-haiku-4-5-20251001')}")
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.0,
            max_tokens=4096,
            streaming=True,
        )
    
    elif LLM_PROVIDER == "azure_openai":
        logger.info(f"🤖 Using Azure OpenAI provider | model={os.getenv('AZURE_OPENAI_API_DEPLOYMENT_NAME')}")
        return AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_API_INSTANCE_NAME"),
            model=os.getenv("AZURE_OPENAI_API_DEPLOYMENT_NAME"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            temperature=0.0,
            top_p=0.1,
            streaming=True,
        )
    
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{LLM_PROVIDER}'. "
            f"Use 'azure_openai' or 'anthropic'."
        )

llm = _create_llm()