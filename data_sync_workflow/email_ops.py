"""
Email operations for the archive worker.
Handles sending admission brochures to users at session end.
"""
import os
import logging
import httpx
import json
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib

log = logging.getLogger("archive_worker")

# ==================== CONFIG ====================
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT") or 587)
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME", "Admissions Office")

from connection import postgres

async def send_brochure_email(
    dataverse_client, 
    to_email: str, 
    user_name: str, 
    course_name: str, 
    subject: str = "Admission Brochure", 
    college_guid: str = None,
    college_name: str = None,
    trial_id: str = None
) -> bool:
    """
    Sends an email with the admission brochure to the user.
    Uses dynamic college_guid to fetch the brochure and college_name for the template.
    If college_guid is missing, resolves it via trial_id from Postgres.
    """
    if not to_email:
        return False

    # Resolve college info from trial_id if GUID is missing
    actual_college_id = college_guid
    display_college_name = college_name
    
    # Resolution logic: Prioritize GUID -> trial_id -> college_name fallback
    actual_college_id = college_guid
    display_college_name = college_name
    
    # 1. Resolve from trial_id via Postgres if GUID is missing
    if not actual_college_id and trial_id:
        try:
            log.info(f"🔍 [EMAIL] Resolving college for trial_id: {trial_id}")
            async with postgres.acquire() as conn:
                # Use ::text for trial_id to avoid UUID cast errors if it's alphanumeric
                row = await conn.fetchrow("SELECT metadata FROM trial_users WHERE id::text = $1", str(trial_id))
                if row and row['metadata']:
                    meta = row['metadata']
                    # Handle double-encoded JSON
                    if isinstance(meta, str):
                        meta = json.loads(meta)
                        if isinstance(meta, str):
                            meta = json.loads(meta)
                            
                    actual_college_id = meta.get("dataverse_college_guid")
                    display_college_name = meta.get("college_name") or display_college_name
                    if actual_college_id:
                        log.info(f"✅ [EMAIL] Resolved from Postgres: {display_college_name} ({actual_college_id})")
        except Exception as e:
            log.error(f"❌ [EMAIL] Postgres lookup failed for trial_id {trial_id}: {e}")

    # 2. Fallback to name-based search if still no GUID
    if not actual_college_id:
        fallback_name = display_college_name or os.getenv("WHATSAPP_COLLEGE_NAME")
        if fallback_name:
            log.warning(f"⚠️ [EMAIL] No college_guid. Falling back to name search for '{fallback_name}'")
            try:
                # Remove hardcoded "Zoxima University" and "Cl-1047" from filter
                endpoint = f"zx_colleges?$filter=zx_collegename eq '{fallback_name}'&$select=zx_collegeid,zx_collegename,zx_document"
                from dataverse_ops import _custom_get
                data = await _custom_get(dataverse_client, endpoint)
                colleges = data.get("value", [])
                if colleges:
                    actual_college_id = colleges[0]["zx_collegeid"]
                    display_college_name = colleges[0]["zx_collegename"]
                    log.info(f"✅ [EMAIL] Resolved from Dataverse name search: {display_college_name} ({actual_college_id})")
            except Exception as e:
                log.error(f"❌ [EMAIL] Dataverse fallback search failed: {e}")

    # Final visual fallback for template
    display_college_name = display_college_name or "Zoxima University"
    email_subject = f"Admission Brochure - {display_college_name}" if subject == "Admission Brochure" else subject

    log.info(f"📧 [EMAIL] Preparing brochure email for {to_email} (College: {display_college_name}, Course: {course_name})")

    if not SMTP_USER or not SMTP_PASSWORD:
        log.error("❌ [EMAIL] SMTP credentials missing. Cannot send email.")
        return False

    try:
        brochure_content = None
        brochure_filename = "Admission_Brochure.pdf" # Default fallback

        if actual_college_id:
            try:
                # Download logic
                base_url = dataverse_client.base_url.rstrip("/")
                token = await dataverse_client.get_token()
                file_url = f"{base_url}/zx_colleges({actual_college_id})/zx_document/$value"
                
                headers = {"Authorization": f"Bearer {token}"}
                async with httpx.AsyncClient(timeout=60) as http:
                    response = await http.get(file_url, headers=headers)
                    if response.status_code == 200:
                        brochure_content = response.content
                        log.info(f"✅ [EMAIL] Brochure downloaded for {actual_college_id} ({len(brochure_content)} bytes)")
                        
                        # Try to extract the exact filename from Dataverse headers
                        content_disp = response.headers.get("Content-Disposition")
                        if content_disp and "filename=" in content_disp:
                            import re
                            # Matches both filename="name.ext" and filename=name.ext
                            fn_match = re.search(r'filename=["\']?([^"\';]+)["\']?', content_disp)
                            if fn_match:
                                brochure_filename = fn_match.group(1)
                                log.info(f"📎 [EMAIL] Using exact filename from Dataverse: {brochure_filename}")
                    else:
                        log.error(f"❌ [EMAIL] Failed to download brochure for {actual_college_id} ({response.status_code})")
            except Exception as download_err:
                log.error(f"❌ [EMAIL] Download error: {download_err}")

        # 2. Build HTML Body
        # Extract initials for the logo
        initials = "".join([w[0] for w in display_college_name.split()[:2]]).upper() if display_college_name else "ZU"
        download_url = f"{os.getenv('DATAVERSE_BASE_URL')}/zx_colleges({actual_college_id})/zx_document/$value" if actual_college_id else "#"
        
        html_body = f"""
        <html>
        <head>
            <style>
                .button-shadow {{
                    box-shadow: 0 4px 10px rgba(211, 47, 47, 0.3);
                }}
            </style>
        </head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f7;">
            <div style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                <!-- Header Section -->
                <div style="background-color: #1a1a2e; padding: 40px 30px; text-align: left; color: #ffffff;">
                    <div style="display: flex; align-items: center; margin-bottom: 25px;">
                        <div style="background-color: #d32f2f; color: #ffffff; width: 50px; height: 50px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 24px; margin-right: 15px; float: left; text-align: center; line-height: 50px;">{initials}</div>
                        <div style="float: left;">
                            <span style="font-size: 28px; font-weight: bold; letter-spacing: 1px;">{display_college_name}</span><br>
                            <span style="font-size: 10px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.7;">Where Excellence Meets Opportunity</span>
                        </div>
                        <div style="clear: both;"></div>
                    </div>
                    
                    <div style="background-color: #d32f2f; color: #ffffff; display: inline-block; padding: 6px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase; margin-bottom: 20px;">
                        ADMISSIONS OPEN 2026
                    </div>
                    
                    <h1 style="margin: 0; font-size: 32px; font-weight: 800; line-height: 1.2; margin-bottom: 15px;">Your Journey to Success Starts Here.</h1>
                </div>

                <!-- Body Section -->
                <div style="padding: 40px 30px;">
                    <p style="font-size: 18px; margin-bottom: 20px;">Dear <strong>{user_name or 'Applicant'}</strong>,</p>
                    
                    <p style="font-size: 16px; color: #555;">Thanks for showing interest in <strong>{course_name or 'our courses'}</strong> at {display_college_name}. We are excited to share our comprehensive brochure with you.</p>
                    
                    <p style="font-size: 16px; color: #555;">{display_college_name} is committed to providing world-class education and shaping the leaders of tomorrow. Click the button below to download the brochure.</p>
                    
                    <!-- Download Button Section -->
                    <div style="text-align: center; margin: 50px 0;">
                        <a href="{download_url}" style="background-color: #d32f2f; color: #ffffff; padding: 18px 40px; border-radius: 35px; text-decoration: none; font-weight: bold; font-size: 20px; display: inline-block;">
                            Download the Brochure
                        </a>
                    </div>

                    <p style="font-size: 16px; color: #555;">If you have any questions or would like to schedule a 1-on-1 counseling session, our team is ready to assist you.</p>
                    
                    <div style="margin-top: 40px; border-top: 1px solid #eeeeee; padding-top: 30px;">
                        <p style="margin: 0; color: #777;">Warm Regards,</p>
                        <p style="margin: 5px 0 0 0; font-weight: bold; color: #1a1a2e; font-size: 18px;">Admissions Office</p>
                        <p style="margin: 0; font-size: 14px; color: #d32f2f; font-weight: bold;">{display_college_name}</p>
                    </div>
                </div>

                <!-- Footer Section -->
                <div style="background-color: #f8f9fa; padding: 25px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eeeeee;">
                    <p style="margin: 0;">&copy; 2026 {display_college_name}. All rights reserved.</p>
                    <p style="margin: 5px 0 0 0;">This is an automated communication from Zox Ed AI.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 3. Construct Multi-part Message
        msg = MIMEMultipart()
        msg['Subject'] = email_subject
        # Use display_college_name as the "From Name" instead of FROM_NAME from env
        msg['From'] = f"{display_college_name} <{FROM_EMAIL}>"
        msg['To'] = to_email
        
        msg.attach(MIMEText(html_body, 'html'))

        # 4. Attach Brochure if available
        if brochure_content:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(brochure_content)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=brochure_filename)
            msg.attach(part)
            log.info(f"📎 [EMAIL] Attached brochure: {brochure_filename}")

        # 5. Send Email
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )

        log.info(f"🚀 [EMAIL] Success: Brochure email sent to {to_email}")
        return True

    except Exception as e:
        log.error(f"❌ [EMAIL] Failed to send email: {e}")
        return False
