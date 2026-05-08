import asyncio
import os
import sys
import logging

# Add parent directory to path so we can import server and client
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from server import send_email
from client import dataverse

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_test():
    to_email = os.getenv("SMTP_USER")
    user_name = "Roshni Sharma"
    course_name = "Data Science & AI"
    
    logger.info(f"Testing send_email tool directly for {to_email}")
    
    result = await send_email(to_email, user_name, course_name)
    print(f"\nRESULT: {result}")
    
    await dataverse.close()

if __name__ == "__main__":
    asyncio.run(run_test())
