import os
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Global variable to hold the single instance
client_instance = None


async def mcpserver(restart: bool = False):
    """
    Returns the active MCP client.

    Args:
        restart (bool): If True, forces the existing client to close and creates a new one.Use this when catching a 'Connection Closed' error.
    """
    global client_instance

    # 1. Handle Restart Request (Cleanup old connection)
    if restart and client_instance:
        try:
            logger.info("Restarting MCP Client: Closing old connection...")
            await client_instance.aclose()
        except Exception as e:
            # Ignore errors during closure (it might already be closed)
            logger.warning(f"Warning during close: {e}")
        finally:
            # Reset variable to ensure a new one is created
            client_instance = None

    # 2. Initialize if missing (Singleton Pattern)
    if client_instance is None:
        try:
            logger.info("Initializing new MCP Client...")
            client_instance = MultiServerMCPClient(
                {
                    "DB_MCP": {
                        "url": os.getenv("DB_MCP_URL"),
                        "transport": "streamable_http",
                    }
                }
            )
            logger.info("MCP Client initialized successfully.")
        except Exception as e:
            # If initialization fails, ensure we don't leave a broken object
            client_instance = None
            logger.error(f"Failed to initialize MCP Client: {e}")
            raise e

    return client_instance

