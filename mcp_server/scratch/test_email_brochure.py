import asyncio
import os
import sys
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib

# Add parent directory to path so we can import client
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from client import dataverse

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SMTP Config (Mocking from env)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME")

async def test_email_flow(to_email: str, user_name: str, course_name: str):
    logger.info(f"Starting test email flow for {to_email} ({course_name})")
    
    try:
        # 1. Find College
        college_name = "Zoxima University"
        endpoint = f"zx_colleges?$filter=zx_collegename eq '{college_name}' or zx_collegename eq 'Cl-1047'&$select=zx_collegeid,zx_collegename,zx_document"
        data = await dataverse.get(endpoint)
        
        colleges = data.get("value", [])
        if not colleges:
            logger.error("No college found")
            return
        
        college = colleges[0]
        college_id = college["zx_collegeid"]
        brochure_filename = college.get("zx_document_name", "Admission_Brochure.png")
        
        # 2. Download Brochure
        token = await dataverse._get_token()
        base_url = os.getenv("DATAVERSE_BASE_URL")
        client_http = await dataverse._get_http_client()
        
        file_endpoint = f"{base_url}/zx_colleges({college_id})/zx_document/$value"
        response = await client_http.get(file_endpoint, headers={"Authorization": f"Bearer {token}"})
        
        if response.status_code != 200:
            logger.error(f"Download failed: {response.status_code}")
            return
        
        brochure_content = response.content
        
        # 3. Build Email
        subject = f"Admission Brochure - {college_name}"
        download_url = f"{base_url}/zx_colleges({college_id})/zx_document/$value"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f7;">
            <div style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                <div style="background-color: #1a1a2e; padding: 40px 30px; color: #ffffff;">
                    <h1 style="margin: 0;">Zoxima University</h1>
                </div>
                <div style="padding: 40px 30px;">
                    <p>Dear <strong>{user_name}</strong>,</p>
                    <p>Thanks for showing interest in <strong>{course_name}</strong> at our college.</p>
                    
                    <div style="text-align: center; margin: 50px 0;">
                        <a href="{download_url}" style="background-color: #d32f2f; color: #ffffff; padding: 18px 40px; border-radius: 35px; text-decoration: none; font-weight: bold; font-size: 20px; display: inline-block;">
                            Download the Brochure
                        </a>
                        <p style="font-size: 12px; color: #888; margin-top: 15px;">(Find the file "{brochure_filename}" attached to this email)</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = to_email
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Attachment ONLY
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(brochure_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{brochure_filename}"')
        msg.attach(part)
        
        # 4. Send Email
        logger.info(f"Sending email to {to_email}")
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("✓ Test email sent successfully!")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        await dataverse.close()

if __name__ == "__main__":
    asyncio.run(test_email_flow(SMTP_USER, "Roshni Sharma", "MBA Programme"))
