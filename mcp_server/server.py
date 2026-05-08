import os
import time
import logging
import base64
import tempfile
import httpx
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse
import aiosmtplib
import json

from client import embeddings, postgres, redis_client, dataverse

# Configure logger
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================
# SMTP CONFIGURATION
# ============================================================
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME")

# ============================================================
# WHATSAPP CONFIGURATION
# ============================================================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_COLLEGE_NAME = os.getenv("WHATSAPP_COLLEGE_NAME", "Zoxima University")


# ============================================================
# LIFESPAN (CLEANUP)
# ============================================================
@asynccontextmanager
async def lifespan(server: FastMCP):
    # ============================================================
    # STARTUP: Initialize all connections eagerly
    # ============================================================
    logger.info("Starting up... initializing connections.")
    try:
        await postgres.initialize()
        redis_client.ping()
        # await dataverse.initialize()
        # logger.info("✓ All connections initialized successfully")
    except Exception as e:
        logger.error(f"✗ Startup failed: {e}")
        raise  # Fail fast if connections can't be established
    
    yield
    
    # ============================================================
    # SHUTDOWN: Close all connections
    # ============================================================
    logger.info("Shutting down... closing connections.")
    await postgres.close()
    await dataverse.close()
    redis_client.close()


# Initialize FastMCP
mcp = FastMCP("DB_MCP", lifespan=lifespan)


# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================

@mcp.custom_route("/education/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return JSONResponse({"status": "healthy", "service": "education-mcp-server"})


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def resolve_lookup_id(entity_name: str, name_field: str, value: str) -> Optional[str]:
    """
    Resolves a name or GUID string to a valid Dataverse GUID.
    If value is already a GUID, returns it. Otherwise, searches by name.
    """
    if not value or not value.strip():
        return None
    
    import re
    clean_val = value.strip("{}() ")
    guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    
    if re.match(guid_pattern, clean_val):
        return clean_val

    # Search by name
    try:
        # Entity set names are usually plural: zx_courses, zx_branchs
        # Select field is usually entity name + "id": zx_courseid, zx_branchid
        id_field = f"{entity_name.rstrip('s')}id"
        escaped_val = clean_val.replace("'", "''")
        endpoint = f"{entity_name}?$filter=contains({name_field}, '{escaped_val}')&$select={id_field}"
        
        logger.info(f"🔍 [LOOKUP] Resolving '{clean_val}' in {entity_name}")
        data = await dataverse.get(endpoint)
        results = data.get("value", [])
        
        if results:
            resolved_id = results[0].get(id_field)
            logger.info(f"✅ [LOOKUP] Resolved '{clean_val}' -> {resolved_id}")
            return resolved_id
        
        logger.warning(f"⚠️ [LOOKUP] No match found for '{clean_val}' in {entity_name}")
    except Exception as e:
        logger.error(f"💥 [LOOKUP] Error resolving {clean_val} in {entity_name}: {e}")
    
    return None


# ============================================================
# TOOLS
# ============================================================

@mcp.tool()
async def get_knowledge_base(
    query: str, 
    limit: int = 5,
    source: str = "Product-AI",
    trial_id: Optional[str] = None
) -> Dict[str, Any]:
    """
  ALWAYS call this tool before answering any factual question.
NEVER answer from your own knowledge or training data.

Use for:
- Courses, fees, scholarships
- Eligibility and cutoffs
- Admission process and dates
- Placements, campus, entrance exams

Skip only for greetings and small talk.

If found → use it. If partial → share what's available.
If nothing → say: "I don't have this info. Please contact us at {{college_phone}}."

Args:
    query: The search query text
    limit: Maximum number of results (1–5)
    source: 'Product-AI' or 'Zox-edu-ai' (default: 'Product-AI')
    """
    if not query or not query.strip():
        return {"success": False, "error": "Query cannot be empty"}

    limit = max(1, min(limit, 5))
    
    # Validate source
    valid_sources = ["Product-AI", "Zox-edu-ai"]
    if source not in valid_sources:
        return {"success": False, "error": f"Invalid source. Must be one of: {valid_sources}"}

    try:
        # 1. Embed Query
        logger.info(f"Embedding query: '{query[:40]}...' (trial_id: {trial_id}, source: {source})")
        query_embedding = await embeddings.embed_query(query)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # 2. Vector Search with source or trial_id filter
        async with postgres.acquire() as conn:
            if trial_id:
                sql = """
                    SELECT
                        id, document_name, document_url, document_type, content,
                        chunk_index, source,
                        1 - (embedding <=> $1::vector)::float as similarity_score
                    FROM education_vector_documents
                    WHERE trial_id = $3::uuid
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                """
                rows = await conn.fetch(sql, embedding_str, limit, trial_id)
            else:
                sql = """
                    SELECT
                        id, document_name, document_url, document_type, content,
                        chunk_index, source,
                        1 - (embedding <=> $1::vector)::float as similarity_score
                    FROM education_vector_documents
                    WHERE source = $3::source_enum
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                """
                rows = await conn.fetch(sql, embedding_str, limit, source)

        # 3. Format Results
        documents = [
            {
                "id": str(row["id"]),
                "document_name": row["document_name"],
                "document_url": row["document_url"],
                "document_type": row["document_type"],
                "content": row["content"],
                "chunk_index": row["chunk_index"],
                "source": row["source"],
                "similarity_score": round(float(row["similarity_score"]), 4)
            }
            for row in rows
        ]

        logger.info(f"✓ Found {len(documents)} documents (trial_id: {trial_id}, source: {source})")
        return {
            "success": True,
            "query": query,
            "source": source if not trial_id else None,
            "trial_id": trial_id,
            "count": len(documents),
            "documents": documents
        }

    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return {"success": False, "error": str(e)}



@mcp.prompt()
async def get_prompt(prompt_id: str) -> str:
    """Retrieve a single prompt_text from PostgreSQL."""
    if not prompt_id:
        return "Error: No prompt_id provided"

    try:
        logger.info(f"Retrieving prompt_id={prompt_id}")
        async with postgres.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT prompt_text, version
                FROM public.prompts
                WHERE prompt_id = $1
                ORDER BY version DESC
                LIMIT 1
                """,
                prompt_id
            )

        if not row:
            logger.info(f"Prompt not found: {prompt_id}")
            return f"Error: Prompt not found for ID '{prompt_id}'"

        version = row["version"]
        logger.info(f"✅ Prompt loaded: prompt_id={prompt_id}, version={version}")
        # Prefix version metadata for the chatbot to extract and log
        return f"__PROMPT_VERSION:{version}__\n{row['prompt_text']}"

    except Exception as e:
        logger.error(f"Error retrieving prompt: {e}")
        return f"Error: {str(e)}"




@mcp.tool()
async def check_lead(
    phone_number: Optional[str] = None, 
    email_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Checks Dataverse Lead table for a given phone number or email.
Call this tool as soon as a valid phone number OR email is available in the conversation — even if name is not yet collected.
Returns existing lead data including name, email, phone, course interest, scores, and previous conversation context.
Use returned data to avoid asking duplicate questions.
    """
    logger.info(f"Checking lead for phone: {phone_number}, email: {email_id}")

    try:
        # Build the OData Filter dynamically
        filters = []
        if phone_number:
            filters.append(f"zx_mobilenumber eq '{phone_number}'")
        if email_id:
            filters.append(f"zx_emailid eq '{email_id}'")

        if not filters:
            return {"status": "error", "message": "No search criteria provided"}

        filter_query = " or ".join(filters)
        # UPDATED: Added zx_context and other user fields to the select query
        endpoint = f"zx_leads?$filter={filter_query}&$select=zx_emailid,zx_leadid,zx_mobilenumber,zx_context,zx_leadname,zx_firstname,zx_lastname,zx_city,zx_highestqualification,zx_undergraduatecourse,zx_graduationyear,zx_thpercentage,zx_th,zx_leadscore,zx_priority,zx_leadtype,zx_leadstatus"
        
        # Use dataverse client
        data = await dataverse.get(endpoint)
        leads = data.get("value", [])

        if not leads:
            return {"status": "not_found", "message": "No lead found"}

        # Extract Lead ID and context for the Orchestrator
        lead = leads[0]
        context = lead.get("zx_context", "")
        
        result = {
            "status": "success",
            "lead_id": lead.get("zx_leadid"),
            "email": lead.get("zx_emailid"),
            "phone": lead.get("zx_mobilenumber"),
            "lead_name": lead.get("zx_leadname"),
            "first_name": lead.get("zx_firstname"),
            "last_name": lead.get("zx_lastname"),
            "city": lead.get("zx_city"),
            "highest_qualification": lead.get("zx_highestqualification"),
            "interested_course": lead.get("_zx_interestedcourse_value") or lead.get("zx_interestedcourse"),
            "graduation_course": lead.get("zx_undergraduatecourse"),
            "graduation_year": lead.get("zx_graduationyear"),
            "10th_percentage": lead.get("zx_thpercentage"),
            "12th_percentage": lead.get("zx_th"),
            "lead_score": lead.get("zx_leadscore"),
            "priority": lead.get("zx_priority"),
            "lead_type": lead.get("zx_leadtype"),
            "lead_status": lead.get("zx_leadstatus"),
            "previous_context": context if context else None,  # Include previous chat context
        }
        
        # Cache full lead data in Redis for archive worker anti-blank-override
        if session_id and result.get("lead_id"):
            try:
                # Set the primary lead_id key for the Archive Worker
                redis_client.client.setex(f"lead_id:{session_id}", 86400 * 2, result["lead_id"])
                
                redis_client.client.setex(
                    f"existing_lead_data:{session_id}",
                    86400 * 2,  # 2 days TTL
                    json.dumps(result)
                )
                logger.info(f"📋 Cached existing lead data in Redis for session {session_id}")
            except Exception as cache_err:
                logger.warning(f"⚠️ Failed to cache lead data in Redis: {cache_err}")
        
        if context:
            logger.info(f"Lead found with previous context: {result}")
        else:
            logger.info(f"Lead found (no previous context): {result}")
            
        return result

    except Exception as e:
        logger.error(f"Error in check_lead: {str(e)}")
        return {"status": "error", "message": str(e)}
    
@mcp.tool()
async def check_senderid(
    sender_id: str,
    source: str
) -> Dict[str, Any]:
    """
    Checks if a lead exists in Dataverse for the given Instagram/Facebook sender_id.
    
    This tool is called automatically by the system on the first message.
    DO NOT call this tool manually - it is handled programmatically.
    """
    logger.info(f"🔍 [CHECK_SENDERID] Checking for sender_id: {sender_id} ({source})")
    
    # Validate source
    if source not in ["instagram", "facebook", "whatsapp"]:
        return {
            "status": "error",
            "message": f"Invalid source. Must be 'instagram', 'facebook', or 'whatsapp'"
        }
    
    # Clean the sender_id (strip date suffix if present like :2026-05-05)
    clean_sid = sender_id.split(":")[0] if ":" in sender_id else sender_id
    
    # For WhatsApp, also remove country code if present (India: 91, US: 1)
    if source == "whatsapp":
        if clean_sid.startswith("91") and len(clean_sid) > 10:
            clean_sid = clean_sid[2:]
            logger.info(f"📱 [CHECK_SENDERID] Removed India country code: {sender_id} -> {clean_sid}")
        elif clean_sid.startswith("1") and len(clean_sid) == 11:
            clean_sid = clean_sid[1:]
            logger.info(f"📱 [CHECK_SENDERID] Removed US country code: {sender_id} -> {clean_sid}")
    
    try:
        # Query Dataverse by platform-specific sender_id with all requested fields
        if source == "instagram":
            field_name = "zx_senderid"
        elif source == "facebook":
            field_name = "zx_facebooksenderid"
        elif source == "whatsapp":
            field_name = "zx_mobilenumber"
        else:
            field_name = "zx_senderid" # Default
        select_fields = [
            "zx_leadid", "zx_firstname", "zx_lastname", "zx_leadname",
            "zx_emailid", "zx_mobilenumber", "zx_city",
            "zx_highestqualification", "zx_undergraduatecourse", "zx_graduationyear",
            "zx_thpercentage", "zx_th", "zx_leadscore", "zx_priority",
            "zx_leadtype", "zx_context", "zx_senderid", "zx_facebooksenderid"
        ]
        select_param = ",".join(select_fields)
        endpoint = f"zx_leads?$filter={field_name} eq '{clean_sid}'&$select={select_param}"
        data = await dataverse.get(endpoint)
        leads = data.get("value", [])
        
        if leads:
            # Lead found - existing user
            lead = leads[0]
            lead_id = lead.get("zx_leadid")
            
            logger.info(f"✅ [CHECK_SENDERID] Found existing lead: {lead_id}")
            
            return {
                "status": "found",
                "lead_id": lead_id,
                "name": lead.get("zx_leadname"),
                "firstname": lead.get("zx_firstname"),
                "lastname": lead.get("zx_lastname"),
                "phone": lead.get("zx_mobilenumber"),
                "email": lead.get("zx_emailid"),
                "city": lead.get("zx_city"),
                "highestqualification": lead.get("zx_highestqualification"),
                "undergraduatecourse": lead.get("zx_undergraduatecourse"),
                "graduationyear": lead.get("zx_graduationyear"),
                "thpercentage": lead.get("zx_thpercentage"),
                "th": lead.get("zx_th"),
                "leadscore": lead.get("zx_leadscore"),
                "priority": lead.get("zx_priority"),
                "leadtype": lead.get("zx_leadtype"),
                "context": lead.get("zx_context"),
                "insta_sender_id": lead.get("zx_senderid"),
                "fb_sender_id": lead.get("zx_facebooksenderid"),
                "sender_id": clean_sid,
                "source": source
            }
        else:
            # Lead not found - new user
            logger.info(f"🆕 [CHECK_SENDERID] No lead found for sender_id: {sender_id}")
            
            return {
                "status": "not_found",
                "message": "New user - proceed with data collection",
                "sender_id": sender_id,
                "source": source
            }
        
    except Exception as e:
        logger.error(f"💥 [CHECK_SENDERID] Error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }    


async def _resolve_college_brochure_info(college_name: Optional[str] = None, trial_id: Optional[str] = None, college_guid: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolves college brochure information (GUID and Name) based on college_guid, trial_id or college_name.
    
    1. If college_guid is provided, use it directly (highest priority).
    2. If trial_id is provided, look up metadata in Postgres trial_users table.
    3. Fall back to college_name lookup in Dataverse.
    """
    resolved_guid = college_guid
    resolved_name = None
    
    if resolved_guid:
        logger.info(f"✅ [BROCHURE_RESOLVE] Using provided college_guid: {resolved_guid}")
        # Optionally fetch name if not provided
        if not college_name:
            try:
                endpoint = f"zx_colleges({resolved_guid})?$select=zx_collegename"
                data = await dataverse.get(endpoint)
                resolved_name = data.get("zx_collegename")
            except: pass
    
    # Tier 2: Resolve from trial_id via Postgres if still no GUID
    if not resolved_guid and trial_id:
        try:
            logger.info(f"🔍 [BROCHURE_RESOLVE] Resolving college for trial_id: {trial_id}")
            async with postgres.acquire() as conn:
                row = await conn.fetchrow("SELECT metadata FROM trial_users WHERE id = $1", trial_id)
                if row and row['metadata']:
                    metadata = row['metadata']
                    if isinstance(metadata, str): metadata = json.loads(metadata)
                    
                    resolved_guid = metadata.get("dataverse_college_guid")
                    resolved_name = metadata.get("college_name")
                    
                    if resolved_guid:
                        logger.info(f"✅ [BROCHURE_RESOLVE] Found college in trial metadata: {resolved_name} ({resolved_guid})")
        except Exception as e:
            logger.error(f"❌ [BROCHURE_RESOLVE] Postgres lookup failed for trial_id {trial_id}: {e}")

    # Tier 3: Use provided college_name or fallback to env default
    if not resolved_guid:
        search_name = college_name or resolved_name or WHATSAPP_COLLEGE_NAME
        logger.info(f"🔍 [BROCHURE_RESOLVE] Falling back to Dataverse lookup for name: '{search_name}'")
        
        try:
            endpoint = f"zx_colleges?$filter=zx_collegename eq '{search_name}' or zx_collegename eq 'Zoxima University' or zx_collegename eq 'Cl-1047'&$select=zx_collegeid,zx_collegename"
            data = await dataverse.get(endpoint)
            colleges = data.get("value", [])
            
            if colleges:
                match = next((c for c in colleges if c["zx_collegename"] == search_name), colleges[0])
                resolved_guid = match["zx_collegeid"]
                resolved_name = match["zx_collegename"]
                logger.info(f"✅ [BROCHURE_RESOLVE] Resolved from Dataverse: {resolved_name} ({resolved_guid})")
        except Exception as e:
            logger.error(f"❌ [BROCHURE_RESOLVE] Dataverse lookup failed: {e}")

    return {
        "college_id": resolved_guid,
        "college_name": resolved_name or college_name or WHATSAPP_COLLEGE_NAME
    }


@mcp.tool()
async def send_email(to_email: str, user_name: str, course_name: str, subject: str = "Admission Brochure", college_name: Optional[str] = None) -> str:
    """
    Sends an email with the admission brochure to the user.
    
    Args:
        to_email: Recipient's email address
        user_name: User's name to personalize the email
        course_name: Name of the course the user is interested in
        subject: Email subject line
        college_name: Optional name of the college
    """
    logger.info(f"Sending brochure email to: {to_email} for course: {course_name}")

    if not SMTP_USER or not SMTP_PASSWORD:
        return "Error: SMTP credentials missing. Check .env file."

    try:
        # 1. Resolve College Info (Old Logic)
        target_college = college_name or WHATSAPP_COLLEGE_NAME
        endpoint = f"zx_colleges?$filter=zx_collegename eq '{target_college}' or zx_collegename eq 'Zoxima University' or zx_collegename eq 'Cl-1047'&$select=zx_collegeid,zx_collegename,zx_document"
        
        data = await dataverse.get(endpoint)
        colleges = data.get("value", [])
        
        if not colleges:
            return f"Error: No college brochure found for '{target_college}'."
            
        college = colleges[0]
        college_id = college["zx_collegeid"]
        display_college_name = college["zx_collegename"]
        
        # Download the file
        file_endpoint = f"zx_colleges({college_id})/zx_document/$value"
        brochure_content = await dataverse.download_file(file_endpoint)
        
        email_subject = f"Admission Brochure - {display_college_name}" if subject == "Admission Brochure" else subject
        
        brochure_filename = "Admission_Brochure.pdf"
        
        if college_id:
            try:
                # Fetch metadata first to get filename
                meta_endpoint = f"zx_colleges({college_id})?$select=zx_document_name"
                meta_data = await dataverse.get(meta_endpoint)
                brochure_filename = meta_data.get("zx_document_name", f"{display_college_name.replace(' ', '_')}_Brochure.pdf")
                
                # Download the file
                file_endpoint = f"zx_colleges({college_id})/zx_document/$value"
                brochure_content = await dataverse.download_file(file_endpoint)
                logger.info(f"✅ [EMAIL] Brochure downloaded: {brochure_filename} ({len(brochure_content)} bytes)")
            except Exception as download_err:
                logger.error(f"❌ [EMAIL] Failed to download brochure for {college_id}: {download_err}")
                brochure_content = None
        else:
            logger.warning(f"⚠️ [EMAIL] No college found for brochure. Sending email without attachment.")

        # 2. Build Premium HTML Email Template
        initials = "".join([w[0] for w in display_college_name.split()[:2]]).upper() if display_college_name else "ZU"
        download_url = f"{os.getenv('DATAVERSE_BASE_URL')}/zx_colleges({college_id})/zx_document/$value" if college_id else "#"
        
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
                    <p style="font-size: 18px; margin-bottom: 20px;">Dear <strong>{user_name}</strong>,</p>
                    
                    <p style="font-size: 16px; color: #555;">Thanks for showing interest in <strong>{course_name}</strong> at {display_college_name}. We are excited to share our comprehensive brochure with you.</p>
                    
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
        # Use display_college_name as the "From Name"
        msg['From'] = f"{display_college_name} <{FROM_EMAIL}>"
        msg['To'] = to_email
        
        msg.attach(MIMEText(html_body, 'html'))

        # 4. Attach Brochure if available
        if brochure_content:
            # Using application/octet-stream and attachment disposition to minimize previews
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(brochure_content)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=brochure_filename)
            msg.attach(part)
            
            logger.info(f"📎 [EMAIL] Attached brochure as file: {brochure_filename}")

        # 5. Send Email
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )

        logger.info(f"🚀 [EMAIL] Success: Brochure email sent to {to_email}")
        return f"Brochure email sent successfully to {to_email} with name '{user_name}'."

    except Exception as e:
        logger.error(f"❌ [EMAIL] Failed to send email: {e}")
        return f"Error sending email: {str(e)}"

# ============================================================
# COMMENTED OUT: Lead creation now handled by archive worker
# The archive worker's AI analysis extracts user details from
# conversations and creates/updates leads automatically on
# session end. These tools are preserved for reference.
# ============================================================

# @mcp.tool()
# async def create_enquiry_lead(
#     phone: str,
#     leadname: str,
#     firstname: Optional[str] = None,
#     lastname: Optional[str] = None,
#     email: Optional[str] = None,
#     leadtype: int = 128780003, # Defaulting to Enquiry/Student context
#     leadsource: int = 128780000, # Website
#     college_guid: Optional[str] = None,
# ) -> Dict[str, Any]:
#     """
#     Creates an initial ENQUIRY lead ONLY for brand new users.
#
#     **CRITICAL RULE:**
#     - You MUST call `check_lead` first.
#     - ONLY call this tool if `check_lead` returns `{"status": "not_found"}`.
#     - NEVER call this tool if `check_lead` found an existing lead.
#
#     **What happens next:**
#     - The system automatically stores the lead_id internally.
#     - You don't need to remember or pass the lead_id to other tools.
#     
#     **When to call:**
#     - After `check_lead` confirms "not_found" AND you have the user's Name.
#     
#     **Name Handling Instructions:**
#     - If user provides full name (e.g., "John Doe"): set firstname="John", lastname="Doe", leadname="John Doe"
#     - If single name (e.g., "John"): set firstname="John", leadname="John" (leave lastname empty)
#     
#     **Next step:**
#     - Collect profiling information (10th%, 12th%, etc.) and call `create_complete_lead` later.
#     """
#     if not phone or not phone.isdigit() or len(phone) != 10:
#         return {"status": "error", "message": "Valid 10-digit phone required."}
#     
#     payload = {
#         "zx_mobilenumber": phone,
#         "zx_leadname": leadname,
#         "zx_emailid": email,
#         "zx_leadtype": leadtype, # Set as Enquiry value
#         "zx_leadsource": leadsource
#     }
#     if firstname: payload["zx_firstname"] = firstname
#     if lastname: payload["zx_lastname"] = lastname
#     if college_guid: payload["zx_College@odata.bind"] = f"/zx_colleges({college_guid})"
#     
#     try:
#         status_code, headers, body = await dataverse.post("zx_leads", payload)
#
#         # ✅ FIX: Try both header case variations
#         lead_id = headers.get("OData-EntityId") or headers.get("odata-entityid") or ""
#
#         if lead_id and "(" in lead_id:
#             lead_id = lead_id.split("(")[-1].strip(")")
#
#         # ✅ FIX: Only store if we got a valid GUID (should be ~36 characters)
#         if lead_id and len(lead_id) > 30:
#             redis_client.client.setex(f"lead_id:phone:{phone}", 86400, lead_id)
#             logger.info(f"✓ Lead created: {lead_id} for phone: {phone}")
#     
#             return {
#                 "status": "success",
#                 "lead_id": lead_id,
#                 "phone": phone,
#                 "message": "Enquiry lead created successfully"
#             }
#         else:
#             logger.error(f"❌ Failed to extract lead_id | status: {status_code} | headers: {headers}")
#             return {
#                 "status": "error",
#                 "message": "Lead created but could not extract lead_id",
#                 "phone": phone
#             }
#     
#     except Exception as e:
#         logger.error(f"Create lead failed: {str(e)}")
#         return {"status": "error", "message": str(e)}    
#     
# @mcp.tool()
# async def create_complete_lead(
#     phone: str,  # PRIMARY KEY - Required
#     email: Optional[str] = None,
#     city: Optional[str] = None,
#     zx_thpercentage: Optional[float] = None, # 10th %
#     zx_th: Optional[float] = None,           # 12th %
#     highestqualification: Optional[int] = None,
#     leadtype: Optional[int] = None,
#     leadscore: Optional[int] = None,
#     priority: Optional[int] = None,
#     interested_course_id: Optional[str] = None, 
#     interested_branch_id: Optional[str] = None,
#     leadname: Optional[str] = None,
#     firstname: Optional[str] = None,
#     lastname: Optional[str] = None,
#     college_guid: Optional[str] = None
# ) -> Dict[str, Any]:
#     """
#     Updates an ENQUIRY lead with profile information and upgrades lead type. 
#     Call this tool AT THE END of the chat session to create a complete lead with whatever data was collected during the chat.
#     This tool call MUST always be made before the session terminates, sending whatever information the user provided.
#     Do not forget to invoke this tool when it's a new lead.
#     
#     **IMPORTANT:** Just provide the phone number - the system will automatically 
#     find the correct lead_id from the session. You don't need to track or pass lead_id.
#     
#     **Name Handling Instructions:**
#     - If user provides full name (e.g., "John Doe"): set firstname="John", lastname="Doe", leadname="John Doe"
#     - If single name (e.g., "John"): set firstname="John", leadname="John" (leave lastname empty)
#
#     **When to call:**
#     - AT THE END of the chat session, to save all profiling information (10th%, 12th%, stream, exams, etc.) collected.
#     - Uses the phone number to automatically find the correct lead
#     
#     **What it does:**
#     - Updates lead with academic info
#     - Automatically upgrades lead type:
#       * LEAD (128780004) if 10th & 12th > 50% AND graduated
#       * SUSPECT/PROSPECT (128780005) if not graduated or 12th appearing
#     """
#     if not phone or not phone.isdigit() or len(phone) != 10:
#         return {"status": "error", "message": "Valid 10-digit phone required."}
#
#     lead_id = None
#     redis_key = f"lead_id:phone:{phone}"
#     cached_lead_id = redis_client.client.get(redis_key)
#     
#     if cached_lead_id:
#         lead_id = cached_lead_id.decode('utf-8') if isinstance(cached_lead_id, bytes) else cached_lead_id
#         logger.info(f"✓ Found lead_id from cache: {lead_id} for phone: {phone}")
#     else:
#         logger.info(f"Cache miss - querying Dataverse for phone: {phone}")
#         try:
#             endpoint = f"zx_leads?$filter=zx_mobilenumber eq '{phone}'&$select=zx_leadid&$orderby=createdon desc&$top=1"
#             data = await dataverse.get(endpoint)
#             leads = data.get("value", [])
#             
#             if not leads:
#                 return {
#                     "status": "error",
#                     "message": f"No lead found for phone {phone}. Please create an enquiry lead first using create_enquiry_lead."
#                 }
#             
#             lead_id = leads[0].get("zx_leadid")
#             redis_client.client.setex(redis_key, 86400, lead_id)
#             logger.info(f"✓ Found lead_id from Dataverse and cached: {lead_id}")
#             
#         except Exception as e:
#             logger.error(f"Failed to lookup lead: {str(e)}")
#             return {"status": "error", "message": f"Could not find lead: {str(e)}"}
#     
#     if interested_course_id:
#         course_guid = await resolve_lookup_id("zx_courses", "zx_coursename", interested_course_id)
#         if course_guid:
#             interested_course_id = course_guid
#
#     if interested_branch_id:
#         branch_guid = await resolve_lookup_id("zx_branchs", "zx_branchname", interested_branch_id)
#         if branch_guid:
#             interested_branch_id = branch_guid
#
#     payload = {}
#     if leadname: payload["zx_leadname"] = leadname
#     if firstname: payload["zx_firstname"] = firstname
#     if lastname: payload["zx_lastname"] = lastname
#     if email: payload["zx_emailid"] = email
#     if phone: payload["zx_mobilenumber"] = phone
#     if city: payload["zx_city"] = city
#     if zx_thpercentage is not None: payload["zx_thpercentage"] = zx_thpercentage
#     if zx_th is not None: payload["zx_th"] = zx_th
#     if leadtype is not None: payload["zx_leadtype"] = leadtype
#     if leadscore is not None: payload["zx_leadscore"] = leadscore
#     if priority is not None: payload["zx_priority"] = priority
#     if highestqualification is not None: payload["zx_highestqualification"] = highestqualification
#     
#     if interested_course_id:
#         payload["zx_InterestedCourse@odata.bind"] = f"/zx_courses({interested_course_id})"
#     if interested_branch_id:
#         payload["zx_InterestedBranch@odata.bind"] = f"/zx_branchs({interested_branch_id})"
#     if college_guid:
#         payload["zx_College@odata.bind"] = f"/zx_colleges({college_guid})"
#
#     try:
#         clean_id = lead_id.strip("()").strip()
#         status_code, response_text = await dataverse.patch(f"zx_leads({clean_id})", payload)
#         
#         if status_code == 204:
#             logger.info(f"✓ Lead {clean_id} updated successfully with phone {phone}")
#             return {
#                 "status": "success",
#                 "lead_id": clean_id,
#                 "phone": phone,
#                 "updated_fields": list(payload.keys()),
#                 "message": "Lead profile updated successfully"
#             }
#         else:
#             return {"status": "error", "message": f"Dataverse error: {status_code} - {response_text}"}
#             
#     except Exception as e:
#         logger.error(f"Update lead failed: {str(e)}")
#         return {"status": "error", "message": str(e)}


@mcp.tool()
async def check_seat_availability(
    course_name: str = "",
    branch_name: str = "",
    category: str = ""
) -> Dict[str, Any]:
    """
    Check seat availability for courses and branches at Zoxima University.

    <search_behavior>
        - Works with partial inputs (course / branch / category)
        - If nothing is provided, returns all seat records
        - search for courses with these format: Btech, MCA, Mtech, MBA etc.
        - Case-insensitive search (Dataverse default)
        - Handles common branch abbreviations
    </search_behavior>
    """

    logger.info(
        f"Checking seats - Course: {course_name}, "
        f"Branch: {branch_name}, Category: {category}"
    )

    # ----------------------------
    # Helper: escape OData strings
    # ----------------------------
    def esc(value: str) -> str:
        """Escape single quotes for OData"""
        return value.replace("'", "''")

    # ----------------------------
    # Branch abbreviation mapping
    # ----------------------------
    branch_map = {
        "cse": "Computer Science Engineering",
        "cs": "Computer Science Engineering",
        "ece": "Electronics & Communication Engineering",
        "ec": "Electronics & Communication Engineering",
        "me": "Mechanical Engineering",
        "mech": "Mechanical Engineering",
        "civil": "Civil Engineering",
        "ce": "Civil Engineering",
        "eee": "Electrical Engineering",
        "electrical": "Electrical Engineering"
    }

    # Expand branch abbreviation if needed
    if branch_name and branch_name.strip():
        key = branch_name.lower().strip()
        branch_name = branch_map.get(key, branch_name)

    try:
        # ----------------------------
        # Build OData filters safely
        # ----------------------------
        filters = []

        if course_name and course_name.strip():
            filters.append(
                f"contains(zx_course,'{esc(course_name.strip())}')"
            )

        if branch_name and branch_name.strip():
            filters.append(
                f"contains(zx_branch,'{esc(branch_name.strip())}')"
            )

        if category and category.strip():
            filters.append(
                f"contains(zx_category,'{esc(category.strip())}')"
            )

        filter_query = " and ".join(filters)

        # ----------------------------
        # Build endpoint
        # ----------------------------
        endpoint = (
            "zx_seatavailabilities"
            "?$select=zx_course,zx_branch,zx_category,"
            "zx_totalseats,zx_remainingseats"
        )

        if filter_query:
            endpoint += f"&$filter={filter_query}"

        logger.info(f"Dataverse endpoint: {endpoint}")

        # ----------------------------
        # Call Dataverse
        # ----------------------------
        data = await dataverse.get(endpoint)
        records = data.get("value", [])

        if not records:
            return {
                "status": "not_found",
                "message": "No seat data found"
            }

        # ----------------------------
        # Process results
        # ----------------------------
        seat_data = []
        total_sum = 0
        remaining_sum = 0

        for r in records:
            total = int(r.get("zx_totalseats") or 0)
            remaining = int(r.get("zx_remainingseats") or 0)

            seat_data.append({
                "course": r.get("zx_course"),
                "branch": r.get("zx_branch"),
                "category": r.get("zx_category"),
                "total_seats": total,
                "remaining_seats": remaining,
                "filled_seats": total - remaining
            })

            total_sum += total
            remaining_sum += remaining

        logger.info(f"✓ Found {len(seat_data)} seat records")

        return {
            "status": "success",
            "count": len(seat_data),
            "summary": {
                "total_seats": total_sum,
                "remaining_seats": remaining_sum,
                "filled_seats": total_sum - remaining_sum
            },
            "details": seat_data
        }

    except Exception as e:
        logger.error(f"✗ Seat check error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

# @mcp.tool()
# async def check_whatsapp_lead(phone: str) -> Dict[str, Any]:
#     """
#     Checks if a lead exists for the given WhatsApp phone number.
#     Call this tool at the START of WhatsApp conversations to check for existing leads.
#     Immediately call this tool on whatsapp as soon as first message is received.
#     Phone number is auto-captured from WhatsApp, so you don't need to ask the user.
#     
#     Args:
#         phone: WhatsApp phone number (with or without country code)
#     
#     Returns:
#         Dict with lead information or not_found status
#     """
#     logger.info(f"🔍 [CHECK_WHATSAPP_LEAD] Tool invoked for phone: {phone}")
#     
#     # Remove country code (91 for India) if present
#     clean_phone = phone
#     if phone.startswith("91") and len(phone) > 10:
#         clean_phone = phone[2:]  # Remove '91' prefix
#         logger.info(f"📱 [CHECK_WHATSAPP_LEAD] Removed country code: {phone} -> {clean_phone}")
#     
#     try:
#         logger.info(f"📞 [CHECK_WHATSAPP_LEAD] Querying Dataverse for phone: {clean_phone}")
#         
#         endpoint = f"zx_leads?$filter=zx_mobilenumber eq '{clean_phone}'&$select=zx_emailid,zx_leadid,zx_mobilenumber,zx_context"
#         data = await dataverse.get(endpoint)
#         leads = data.get("value", [])
#         
#         if not leads:
#             logger.info(f"🆕 [CHECK_WHATSAPP_LEAD] No existing lead found for phone: {clean_phone}")
#             logger.info(f"💡 [CHECK_WHATSAPP_LEAD] Next step: Agent should call create_enquiry_lead")
#             return {
#                 "status": "not_found", 
#                 "message": "No lead found for this phone number",
#                 "phone": clean_phone
#             }
#         
#         # Lead exists
#         lead = leads[0]
#         lead_id = lead.get("zx_leadid")
#         context = lead.get("zx_context", "")
#         
#         result = {
#             "status": "success",
#             "lead_id": lead_id,
#             "email": lead.get("zx_emailid"),
#             "phone": lead.get("zx_mobilenumber"),
#             "previous_context": context if context else None
#         }
#         
#         if context:
#             logger.info(f"✅ [CHECK_WHATSAPP_LEAD] Found existing lead: {lead_id} with previous context for phone: {clean_phone}")
#         else:
#             logger.info(f"✅ [CHECK_WHATSAPP_LEAD] Found existing lead: {lead_id} (no previous context) for phone: {clean_phone}")
#         
#         logger.info(f"📊 [CHECK_WHATSAPP_LEAD] Lead details: lead_id={lead_id}, email={result.get('email')}, has_context={bool(context)}")
#         
#         return result
#         
#     except Exception as e:
#         logger.error(f"💥 [CHECK_WHATSAPP_LEAD] Error checking lead for phone {clean_phone}: {e}", exc_info=True)
#         return {"status": "error", "message": str(e)}
    
@mcp.tool()
async def create_lead(
    phone: str,
    leadname: Optional[str] = None,
    email: Optional[str] = None,
    city: Optional[str] = None,
    pincode: Optional[str] = None,
    leadsource: Optional[int] = 128780000, # Default: Website
    leadscore: Optional[str] = None,
    leadtype: Optional[int] = None,
    leadstate: Optional[int] = None,
    priority: Optional[int] = None,
    highestqualification: Optional[int] = None,
    zx_thpercentage: Optional[float] = None,  # 10th %
    zx_th: Optional[float] = None,  # 12th %
    lead_status: Optional[int] = None, # 128780000: Suspect, 128780001: Prospect
    graduation_percentage: Optional[float] = None,
    entrance_score: Optional[float] = None,
    has_job_experience: Optional[bool] = None,
    college_guid: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a lead in Dataverse after collecting relevant information from conversation.
    
    <source_mapping>
        - Website (Default): 128780000
        - WhatsApp: 128780010 (ALWAYS use this if chatting via WhatsApp)
    </source_mapping>

    Automatically determines lead type based on eligibility criteria.
    
    <required_fields>
        - phone: Mobile number (will auto-remove country code if present)
        - leadname: Full name of the lead
    </required_fields>
    
    <lead_type_determination>
    The system automatically sets lead type (zx_leadtype) based on eligibility:
    
    1. LEAD (128780004): User is ELIGIBLE if ALL conditions met:
       - 10th percentage > 50%
       - 12th percentage > 50%
       - AND (Graduated with >50% OR Entrance score >75% OR Has job experience)
    
    2. SUSPECT/PROSPECT (128780005): User is PURSUING if:
       - Currently pursuing graduation
       - OR not passed 12th yet
       - OR 12th appearing this year
    
    3. ENQUIRY (128780003): Default for all other cases:
       - Basic inquiry without academic details
       - Does not meet LEAD criteria
       - Not currently pursuing
    
    Note: If leadtype is explicitly provided, it will override auto-determination.
    </lead_type_determination>
    
    <field_mappings>
        <highestqualification description="Educational level of the lead">
            <option value="128780000">12th - High school completed</option>
            <option value="128780001">Diploma - Vocational diploma</option>
            <option value="128780002">Graduation - Bachelor's degree</option>
            <option value="128780003">Post Graduation - Master's or higher</option>
            <option value="128780004">Other - Any other qualification</option>
        </highestqualification>
        
        <leadtype description="Category determined by system based on eligibility">
            <option value="128780000">STUDENT - Currently a student</option>
            <option value="128780001">PARENT - Parent of a student</option>
            <option value="128780002">WORKING PROFESSIONAL - Currently employed</option>
            <option value="128780003">ENQUIRY - Default/basic inquiry or ineligible</option>
            <option value="128780004">LEAD - Eligible candidate (meets marks criteria)</option>
            <option value="128780005">SUSPECT/PROSPECT - Interested but profile incomplete</option>
        </leadtype>
        
        <leadsource description="Source of the lead">
            <option value="128780000">Website - Default for web chat</option>
            <option value="128780010">WhatsApp - Use this if user is on WhatsApp</option>
        </leadsource>

        <leadstatus description="Current status of the lead">
            <option value="128780000">SUSPECT - Default status</option>
            <option value="128780001">PROSPECT - If user shows interest in courses/admission</option>
        </leadstatus>

        <leadscore description="Score based on academic performance">
            - Determined by entrance exam scores, 10th & 12th percentage, graduation score, job experience on the scale 1-5
        </leadscore>

        <leadstate description="Score based on academic performance">
            <option value="128780000">HOT - User shows high interest in courses and has good scores</option>
            <option value="128780001">WARM - User shows normal interest and had decent conversation</option>
            <option value="128780002">COLD - User has low interest</option>
        </leadstate>
        
        <priority description="Lead quality score based on academic performance">
            Choose based on overall lead quality:
            <option value="128780000">High Priority - Excellent scores (90%+), top entrance ranks, clear goals, relevant experience</option>
            <option value="128780001">Medium Priority - Good scores (70-89%), decent entrance results, some clarity</option>
            <option value="128780002">Low Priority - Average/below scores (below 70%), unclear background or goals</option>
        </priority>
    </field_mappings>
    
    <instructions>
        - System auto-determines leadtype based on eligibility (can be overridden)
        - Infer highestqualification from conversation context
        - Evaluate priority based on academic performance, entrance scores, work experience, and career clarity
        - Send numeric values without commas (e.g., 128780000)
        - Call this tool once sufficient information is gathered
    </instructions>
    """  
    # Remove country code if present (India: 91, US: 1)
    clean_phone = phone
    if phone.startswith("91") and len(phone) > 10:
        clean_phone = phone[2:]  # Remove '91' prefix (India)
        logger.info(f"📱 [CREATE_LEAD] Removed India country code: {phone} -> {clean_phone}")
    elif phone.startswith("1") and len(phone) == 11:
        clean_phone = phone[1:]  # Remove '1' prefix (US)
        logger.info(f"📱 [CREATE_LEAD] Removed US country code: {phone} -> {clean_phone}")
    
    # Validate cleaned phone number
    if not clean_phone or not clean_phone.isdigit() or len(clean_phone) != 10:
        logger.error(f"❌ [CREATE_LEAD] Invalid phone format after cleaning: {clean_phone}")
        return {
            "status": "error",
            "message": f"Phone number must be 10 digits. Received: {clean_phone}"
        }
    determined_leadtype = leadtype  # Use provided value if exists
    
    if determined_leadtype is None:
        # Default to Suspect/Prospect
        determined_leadtype = 128780005
        
        # Check if user is PURSUING (SUSPECT/PROSPECT)
        if highestqualification is not None:
            # If highest qualification is 12th or below AND not completed
            if highestqualification == 128780000:  # 12th
                # Check if they're pursuing or appearing
                determined_leadtype = 128780005  # SUSPECT/PROSPECT
                logger.info(f"📊 [CREATE_LEAD] Set lead type to SUSPECT/PROSPECT (pursuing/12th appearing)")
        
        # Check if user is ELIGIBLE (LEAD)
        if zx_thpercentage is not None and zx_th is not None:
            if zx_thpercentage > 50 and zx_th > 50:
                # Check graduation or entrance score or job experience
                is_eligible = False
                
                if graduation_percentage is not None and graduation_percentage > 50:
                    is_eligible = True
                    logger.info(f"📊 [CREATE_LEAD] Eligible: Graduated with {graduation_percentage}%")
                
                if entrance_score is not None and entrance_score > 75:
                    is_eligible = True
                    logger.info(f"📊 [CREATE_LEAD] Eligible: Entrance score {entrance_score}")
                
                if has_job_experience:
                    is_eligible = True
                    logger.info(f"📊 [CREATE_LEAD] Eligible: Has job experience")
                
                if is_eligible:
                    determined_leadtype = 128780004  # LEAD
                    logger.info(f"✅ [CREATE_LEAD] Set lead type to LEAD (eligible candidate)")
        
        logger.info(f"🎯 [CREATE_LEAD] Auto-determined lead type: {determined_leadtype} "
                   f"(ENQUIRY=128780003, LEAD=128780004, PROSPECT=128780005)")
    else:
        logger.info(f"🎯 [CREATE_LEAD] Using explicitly provided lead type: {determined_leadtype}")

    payload = {
        "zx_mobilenumber": clean_phone,
        "zx_leadname": leadname,
        "zx_emailid": email,
        "zx_city": city,
        "zx_pincode": pincode,
        "zx_leadtype": determined_leadtype  # Use determined lead type
    }
    
    # Add academic fields
    if zx_thpercentage is not None: 
        payload["zx_thpercentage"] = zx_thpercentage
    if zx_th is not None: 
        payload["zx_th"] = zx_th
    
    # Add optional fields
    if leadscore is not None: payload["zx_leadscore"] = int(leadscore)
    if leadsource is not None: payload["zx_leadsource"] = int(leadsource)
    if leadstate is not None: payload["zx_leadstate"] = int(leadstate)
    if priority is not None: payload["zx_priority"] = int(priority)
    if highestqualification is not None: payload["zx_highestqualification"] = int(highestqualification)

    # 🎯 Auto-determine Lead Status (zx_leadstatus)
    # Rule: Default Suspect (128780000). Only Prospect (128780001) if interested.
    # Since this tool is usually called when a user shows interest, we can default to Suspect 
    # unless lead_status is explicitly passed by the agent.
    if lead_status is not None:
        determined_leadstatus = lead_status
    else:
        # If the agent is creating a lead, they usually have interest, but we'll follow 
        # the "Suspect by default" rule unless it's a qualified Lead.
        determined_leadstatus = 128780000 
        if determined_leadtype == 128780004: # Lead
            determined_leadstatus = 128780001 # Prospect
            
    payload["zx_leadstatus"] = determined_leadstatus
    
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}
    
    if college_guid:
        payload["zx_College@odata.bind"] = f"/zx_colleges({college_guid})"
    
    logger.info(f"📝 [CREATE_LEAD] Creating lead with cleaned phone: {clean_phone}, leadtype: {determined_leadtype}")
    
    try:
        status_code, headers, body = await dataverse.post("zx_leads", payload)
        if status_code not in (201, 204):
            logger.error(f"❌ [CREATE_LEAD] Dataverse error {status_code}: {body}")
            return {
                "status": "error",
                "message": f"Dataverse error {status_code}",
                "details": body
            }
        
        lead_id = headers.get("OData-EntityId") or headers.get("odata-entityid")
        if lead_id:
            lead_id = lead_id.split("(")[-1].strip(")")
        
        # ✅ Store lead_id mapped to cleaned phone number in Redis (24 hour expiry)
        redis_client.client.setex(f"lead_id:phone:{clean_phone}", 86400, lead_id)
        
        # ✅ Also link it to the current session so the Archive Worker knows it's already linked
        if session_id:
            redis_client.client.setex(f"lead_id:{session_id}", 86400 * 2, lead_id)
            logger.info(f"🔗 Linked new lead {lead_id} to session {session_id} in Redis")
        
        # Map lead type to readable name
        leadtype_name = {
            128780003: "ENQUIRY",
            128780004: "LEAD",
            128780005: "SUSPECT/PROSPECT"
        }.get(determined_leadtype, "UNKNOWN")
        
        logger.info(f"✅ [CREATE_LEAD] Lead created successfully: {lead_id} for phone: {clean_phone} as {leadtype_name}")
        
        return {
            "status": "success",
            "message": "Lead created successfully",
            "lead_id": lead_id,
            "phone": clean_phone,
            "lead_type": leadtype_name,
            "lead_type_value": determined_leadtype,
            "created_at": time.time()
        }
    except Exception as e:
        logger.error(f"💥 [CREATE_LEAD] Error creating lead: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def create_social_media_lead(
    sender_id: str,                                
    source: str,                                   
    leadname: Optional[str] = None,                
    phone: Optional[str] = None,                   
    email: Optional[str] = None,
    city: Optional[str] = None,
    pincode: Optional[str] = None,
    leadsource: Optional[int] = 128780002,       
    leadscore: Optional[str] = None,
    leadtype: Optional[int] = None,
    leadstate: Optional[int] = None,
    priority: Optional[int] = None,
    highestqualification: Optional[int] = None,
    zx_thpercentage: Optional[float] = None,       
    zx_th: Optional[float] = None,                
    graduation_percentage: Optional[float] = None,
    entrance_score: Optional[float] = None,
    has_job_experience: Optional[bool] = None,
    college_guid: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a lead in Dataverse for Instagram / Facebook users. After getting name and contact details call this tool.
    
    The agent already has sender_id available from the webhook parsing — just pass it directly.
    Name and phone are asked during the conversation like any other field.
    
    <required_fields>
        - sender_id: Instagram-Scoped ID or Facebook Sender ID (auto-available from webhook)
        - source: Channel name — "instagram" or "facebook"
    </required_fields>

    """
    # ============================================================
    # VALIDATE REQUIRED FIELDS
    # ============================================================
    if not sender_id or not sender_id.strip():
        return {"status": "error", "message": "sender_id is required (auto-captured from webhook)"}
    
    # Clean the sender_id (strip date suffix if present)
    clean_sid = sender_id.split(":")[0] if ":" in sender_id else sender_id

    valid_sources = ["instagram", "facebook"]
    if source not in valid_sources:
        return {"status": "error", "message": f"source must be one of: {valid_sources}"}

    # Simple phone validation - just like create_enquiry_lead
    if phone:
        if not phone.isdigit() or len(phone) != 10:
            logger.error(f"❌ [CREATE_SOCIAL_MEDIA_LEAD] Invalid phone format: {phone}")
            return {"status": "error", "message": f"Phone must be 10 digits. Received: {phone}"}

    determined_leadtype = leadtype  # Use explicitly provided value if exists

    if determined_leadtype is None:
        determined_leadtype = 128780003  

        # Check SUSPECT/PROSPECT: pursuing / 12th appearing
        if highestqualification == 128780000:  
            determined_leadtype = 128780005
            logger.info(f"📊 [CREATE_SOCIAL_MEDIA_LEAD] Set to SUSPECT/PROSPECT (pursuing/12th appearing)")

        # Check LEAD: eligible candidate
        if zx_thpercentage is not None and zx_th is not None:
            if zx_thpercentage > 50 and zx_th > 50:
                is_eligible = False

                if graduation_percentage is not None and graduation_percentage > 50:
                    is_eligible = True
                    logger.info(f"📊 [CREATE_SOCIAL_MEDIA_LEAD] Eligible: Graduated with {graduation_percentage}%")

                if entrance_score is not None and entrance_score > 75:
                    is_eligible = True
                    logger.info(f"📊 [CREATE_SOCIAL_MEDIA_LEAD] Eligible: Entrance score {entrance_score}")

                if has_job_experience:
                    is_eligible = True
                    logger.info(f"📊 [CREATE_SOCIAL_MEDIA_LEAD] Eligible: Has job experience")

                if is_eligible:
                    determined_leadtype = 128780004  # LEAD
                    logger.info(f"✅ [CREATE_SOCIAL_MEDIA_LEAD] Set to LEAD (eligible candidate)")

        logger.info(f"🎯 [CREATE_SOCIAL_MEDIA_LEAD] Auto-determined leadtype: {determined_leadtype}")
    else:
        logger.info(f"🎯 [CREATE_SOCIAL_MEDIA_LEAD] Using explicitly provided leadtype: {determined_leadtype}")

    sid_field = "zx_senderid" if source == "instagram" else "zx_facebooksenderid"
    payload = {
        sid_field: clean_sid,                  
        "zx_leadsource": leadsource,               
        "zx_leadtype": determined_leadtype,
    }

    # Optional fields — only add if provided
    if leadname:    payload["zx_leadname"] = leadname
    if phone:       payload["zx_mobilenumber"] = phone  # Direct usage, no cleaning
    if email:       payload["zx_emailid"] = email
    if city:        payload["zx_city"] = city
    if pincode:     payload["zx_pincode"] = pincode
    if zx_thpercentage is not None: payload["zx_thpercentage"] = zx_thpercentage
    if zx_th is not None:           payload["zx_th"] = zx_th
    if leadscore is not None:       payload["zx_leadscore"] = int(leadscore)
    if leadstate is not None:       payload["zx_leadstate"] = int(leadstate)
    if priority is not None:        payload["zx_priority"] = int(priority)
    if highestqualification is not None: payload["zx_highestqualification"] = int(highestqualification)
    if college_guid: payload["zx_College@odata.bind"] = f"/zx_colleges({college_guid})"

    logger.info(f"📝 [CREATE_SOCIAL_MEDIA_LEAD] Payload: clean_sid={clean_sid}, field={sid_field}, source={source}, "
                f"name={leadname}, leadtype={determined_leadtype}")

    try:
        status_code, headers, body = await dataverse.post("zx_leads", payload)

        if status_code not in (201, 204):
            logger.error(f"❌ [CREATE_SOCIAL_MEDIA_LEAD] Dataverse error {status_code}: {body}")
            return {"status": "error", "message": f"Dataverse error {status_code}", "details": body}

        # Extract lead_id from OData-EntityId header
        lead_id = headers.get("OData-EntityId") or headers.get("odata-entityid")
        if lead_id:
            lead_id = lead_id.split("(")[-1].strip(")")

        # Cache sender_id → lead_id mapping
        redis_client.client.setex(f"lead_id:sender:{source}:{clean_sid}", 86400, lead_id)
        logger.info(f"✓ [CREATE_SOCIAL_MEDIA_LEAD] Cached sender_id -> lead_id in Redis")

        # Cache phone → lead_id mapping if phone was provided
        if phone:
            redis_client.client.setex(f"lead_id:phone:{phone}", 86400, lead_id)
            logger.info(f"✓ [CREATE_SOCIAL_MEDIA_LEAD] Cached phone -> lead_id in Redis")

        leadtype_name = {
            128780003: "ENQUIRY",
            128780004: "LEAD",
            128780005: "SUSPECT/PROSPECT"
        }.get(determined_leadtype, "UNKNOWN")

        logger.info(f"✅ [CREATE_SOCIAL_MEDIA_LEAD] Lead created: {lead_id} | "
                    f"source={source} | sender_id={sender_id} | type={leadtype_name}")

        return {
            "status": "success",
            "message": "Social media lead created successfully",
            "lead_id": lead_id,
            "sender_id": sender_id,
            "source": source,
            "phone": phone,
            "lead_type": leadtype_name,
            "lead_type_value": determined_leadtype,
            "created_at": time.time()
        }

    except Exception as e:
        logger.error(f"💥 [CREATE_SOCIAL_MEDIA_LEAD] Error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


# @mcp.tool()
# async def get_courses_with_branches(search_query: str = "") -> Dict[str, Any]:
#     """Retrieves Courses and their associated Branches."""
#     COURSE_NAME_COL = "zx_coursename"
#     BRANCH_NAME_COL = "zx_branchname"
#     BRANCH_TO_COURSE_FILTER_COL = "_zx_courseid_value"

#     try:
#         # Build course endpoint
#         filter_part = f"$filter=contains({COURSE_NAME_COL}, '{search_query}')&" if search_query else ""
#         course_endpoint = f"zx_courses?{filter_part}$select=zx_courseid,{COURSE_NAME_COL}"
        
#         course_data = await dataverse.get(course_endpoint)
#         courses = course_data.get("value", [])

#         if not courses:
#             return {"status": "success", "data": []}

#         final_results = []
#         for course in courses:
#             course_id = course.get("zx_courseid")
#             branch_endpoint = f"zx_branchs?$filter={BRANCH_TO_COURSE_FILTER_COL} eq '{course_id}'&$select=zx_branchid,{BRANCH_NAME_COL}"
            
#             try:
#                 branch_data = await dataverse.get(branch_endpoint)
#                 raw_branches = branch_data.get("value", [])
#             except Exception:
#                 raw_branches = []
            
#             branches_list = [
#                 {"branch_name": b.get(BRANCH_NAME_COL), "branch_id": b.get("zx_branchid")}
#                 for b in raw_branches
#             ]

#             final_results.append({
#                 "course_name": course.get(COURSE_NAME_COL),
#                 "course_id": course_id,
#                 "available_branches": branches_list
#             })

#         return {"status": "success", "count": len(final_results), "data": final_results}

#     except Exception as e:
#         return {"status": "error", "message": str(e)}


@mcp.tool()
async def update_lead(lead_id: str, email: Optional[str] = None, phone: Optional[str] = None, city: Optional[str] = None, dob: Optional[str] = None, interested_course_id: Optional[str] = None, interested_branch_id: Optional[str] = None, college_guid: Optional[str] = None) -> Dict[str, Any]:
    """Updates specific fields of an existing lead. Whenever existing user comes, if any new information is provided then always update that particular lead with new information using this tool"""
    if not lead_id:
        return {"status": "error", "message": "lead_id is mandatory."}

    # Resolve Course/Branch IDs if names were provided instead of GUIDs
    if interested_course_id:
        course_guid = await resolve_lookup_id("zx_courses", "zx_coursename", interested_course_id)
        if course_guid:
            interested_course_id = course_guid

    if interested_branch_id:
        branch_guid = await resolve_lookup_id("zx_branchs", "zx_branchname", interested_branch_id)
        if branch_guid:
            interested_branch_id = branch_guid

    payload = {}
    if email:
        payload["zx_emailid"] = email
    if phone:
        if phone.isdigit() and len(phone) == 10:
            payload["zx_mobilenumber"] = phone
        else:
            return {"status": "error", "message": "Phone must be 10 digits."}
    if city:
        payload["zx_city"] = city
    if dob:
        payload["zx_dateofbirth"] = dob
    if interested_course_id:
        payload["zx_InterestedCourse@odata.bind"] = f"/zx_courses({interested_course_id})"
    if interested_branch_id:
        payload["zx_InterestedBranch@odata.bind"] = f"/zx_branchs({interested_branch_id})"
    if college_guid:
        payload["zx_College@odata.bind"] = f"/zx_colleges({college_guid})"

    if not payload:
        return {"status": "success", "message": "No fields to update."}

    try:
        clean_id = lead_id.strip("()").strip()
        status_code, response_text = await dataverse.patch(f"zx_leads({clean_id})", payload)
        
        if status_code == 204:
            return {"status": "success", "message": "Lead updated successfully", "lead_id": clean_id, "updated_fields": list(payload.keys())}
        else:
            return {"status": "error", "message": f"HTTP {status_code}: {response_text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# @mcp.tool()
# async def get_previous_chat_context(lead_id: str, limit: int = 5) -> Dict[str, Any]:
#     """
#     Retrieves previous chat context (engagement history) for a given lead from Dataverse.
#     Returns the chat summary and subject from engagement history records associated with the lead.
#     
#     Args:
#         lead_id: The Dataverse Lead ID (GUID) to retrieve chat context for.
#         limit: Maximum number of records to return (default 5, max 10).
#     
#     Returns:
#         Dict containing chat history records with subject and summary.
#     """
#     if not lead_id or not lead_id.strip():
#         return {"status": "error", "message": "lead_id is required"}
#     
#     # Clamp limit between 1 and 10
#     limit = max(1, min(limit, 10))
#     
#     logger.info(f"Retrieving previous chat context for lead: {lead_id} (limit: {limit})")
#     
#     try:
#         clean_id = lead_id.strip()
#         endpoint = f"zx_engagementhistories?$select=zx_chatsummary,zx_subject&$filter=_zx_lead_value eq {clean_id}&$top={limit}"
#         
#         data = await dataverse.get(endpoint)
#         records = data.get("value", [])
#         
#         if not records:
#             logger.info(f"No engagement history found for lead: {lead_id}")
#             return {
#                 "status": "success",
#                 "message": "No previous chat context found",
#                 "lead_id": lead_id,
#                 "count": 0,
#                 "history": []
#             }
#         
#         # Extract relevant fields
#         history = [
#             {
#                 "id": record.get("zx_engagementhistoryid"),
#                 "subject": record.get("zx_subject"),
#                 "chat_summary": record.get("zx_chatsummary")
#             }
#             for record in records
#         ]
#         
#         logger.info(f"✓ Found {len(history)} engagement history records for lead: {lead_id}")
#         return {
#             "status": "success",
#             "lead_id": lead_id,
#             "count": len(history),
#             "history": history
#         }
#     
#     except Exception as e:
#         logger.error(f"✗ Error retrieving chat context: {e}")
#         return {"status": "error", "message": str(e)}


async def _perform_whatsapp_document_send(
    pdf_bytes: bytes,
    phone_number: str,
    filename: str
) -> Dict[str, Any]:
    """
    Internal helper to upload and send a PDF document via WhatsApp.
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return {"status": "error", "message": "WhatsApp credentials not configured"}
    
    # Ensure filename ends with .pdf
    if not filename.lower().endswith('.pdf'):
        filename = f"{filename}.pdf"
    
    logger.info(f"Uploading and sending WhatsApp document to: {phone_number}, filename: {filename}")
    
    tmp_path = None
    try:
        # Create a temporary file to use in multipart upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name
        
        # Upload media to WhatsApp using httpx
        upload_url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/media"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Upload the PDF
            with open(tmp_path, 'rb') as f:
                # Some Meta API versions/Business Accounts prefer all fields in the multipart form
                files = {
                    'file': (filename, f, 'application/pdf'),
                    'messaging_product': (None, 'whatsapp'),
                    'type': (None, 'application/pdf')
                }
                
                upload_response = await client.post(upload_url, headers=headers, files=files)
                
                if upload_response.status_code != 200:
                    logger.error(f"Media upload failed: {upload_response.text}")
                    return {"status": "error", "message": f"Media upload failed: {upload_response.text}"}
                
                upload_result = upload_response.json()
                media_id = upload_result.get("id")
            
            if not media_id:
                return {"status": "error", "message": "Failed to get media_id from upload response"}
            
            logger.info(f"✓ Media uploaded, media_id: {media_id}")
            
            # Send document message
            message_url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
            message_payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "document",
                "document": {
                    "id": media_id,
                    "filename": filename
                }
            }
            
            message_response = await client.post(
                message_url,
                headers={**headers, "Content-Type": "application/json"},
                json=message_payload
            )
            
            if message_response.status_code != 200:
                logger.error(f"Message send failed: {message_response.text}")
                return {"status": "error", "message": f"Message send failed: {message_response.text}"}
            
            message_result = message_response.json()
            message_id = message_result.get("messages", [{}])[0].get("id")
            
            logger.info(f"✓ Document sent to {phone_number}, message_id: {message_id}")
            
            return {
                "status": "success",
                "message": f"Document '{filename}' sent successfully",
                "phone_number": phone_number,
                "media_id": media_id,
                "message_id": message_id
            }
            
    except Exception as e:
        logger.error(f"✗ WhatsApp document send helper failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

@mcp.tool()
async def send_brochure(
    phone_number: str,
    college_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches the admission brochure from Dataverse for a specific college and sends it to a WhatsApp user.
    
    Args:
        phone_number: Recipient's phone number with country code (e.g., "917985847848")
        college_name: Optional name of the college to fetch the brochure for.
    """
    target_college = college_name or WHATSAPP_COLLEGE_NAME
    logger.info(f"Attempting to send WhatsApp brochure for '{target_college}' to {phone_number}")

    try:
        # 1. Fetch College Brochure from Dataverse
        endpoint = f"zx_colleges?$filter=zx_collegename eq '{target_college}' or zx_collegename eq 'Zoxima University' or zx_collegename eq 'Cl-1047'&$select=zx_collegeid,zx_collegename,zx_document"
        
        logger.info(f"🔍 [BROCHURE] Looking up college brochure in Dataverse for '{target_college}'")
        data = await dataverse.get(endpoint)
        colleges = data.get("value", [])
        
        if not colleges:
            return {"status": "error", "message": f"No college brochure found for '{target_college}' in Dataverse."}
        
        college = colleges[0]
        college_id = college["zx_collegeid"]
        filename = college.get("zx_document_name", f"{target_college.replace(' ', '_')}_Brochure.pdf")
        
        # Download the file
        file_endpoint = f"zx_colleges({college_id})/zx_document/$value"
        brochure_content = await dataverse.download_file(file_endpoint)
        
        if not brochure_content:
            return {"status": "error", "message": "Brochure file exists in Dataverse but content is empty or failed to download."}
            
        logger.info(f"✅ [BROCHURE] Brochure downloaded: {filename} ({len(brochure_content)} bytes)")
        
        # 2. Send via WhatsApp using helper
        result = await _perform_whatsapp_document_send(brochure_content, phone_number, filename)
        
        if result["status"] == "success":
            result["college_name"] = target_college
            result["message"] = f"Brochure for '{target_college}' sent successfully to {phone_number}."
            
        return result

    except Exception as e:
        logger.error(f"✗ send_brochure failed: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def send_whatsapp_document(
    base64_content: str,
    phone_number: str,
    filename: str
) -> Dict[str, Any]:
    """
    Sends a PDF document to a WhatsApp user using base64 encoded content.
    
    Args:
        base64_content: The PDF file content encoded as base64 string
        phone_number: Recipient's phone number with country code (e.g., "917985847848")
        filename: Display filename for the document (e.g., "Admission_Brochure.pdf")
    
    Returns:
        Dict with status, message_id, and media_id on success
    """
    try:
        pdf_bytes = base64.b64decode(base64_content)
        return await _perform_whatsapp_document_send(pdf_bytes, phone_number, filename)
    except base64.binascii.Error:
        return {"status": "error", "message": "Invalid base64 content"}
    except Exception as e:
        logger.error(f"✗ send_whatsapp_document failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def clear_redis(clear_all: bool, session_id: str = None) -> Dict[str, Any]:
    """
    Clear Redis cache data.
    
    Args:
        clear_all: If True, clears the entire Redis database. If False, clears only the specified session(s).
        session_id: Required when clear_all is False - the session ID(s) to clear. Can be comma-separated for multiple sessions.
    
    Returns:
        Status of the clear operation
    """
    logger.info(f"Redis clear requested: clear_all={clear_all}, session_id={session_id}")
    
    try:
        if clear_all:
            redis_client.client.flushdb()
            logger.info("✓ Redis: All data cleared")
            return {"status": "success", "message": "All Redis data cleared successfully"}
        
        else:
            if not session_id:
                return {
                    "status": "error",
                    "message": "session_id is required when clear_all is False"
                }
            
            # Split comma-separated session IDs and strip whitespace
            session_ids = [sid.strip() for sid in session_id.split(",") if sid.strip()]
            
            total_deleted = 0
            cleared_sessions = []
            
            for sid in session_ids:
                # Define all possible session-related key patterns
                session_keys = [
                    f"messages:list:{sid}",
                    f"summary:{sid}",
                    f"user_count:{sid}",
                    f"last_summarized_index:{sid}",
                    f"count:{sid}",
                    f"summary_in_progress:{sid}",
                    f"last_activity:{sid}",
                    f"created_at:{sid}"
                ]
                
                # Delete all session keys
                deleted_count = 0
                for key in session_keys:
                    deleted_count += redis_client.client.delete(key)
                
                total_deleted += deleted_count
                cleared_sessions.append(sid)
                logger.info(f"✓ Redis: Session {sid} cleared ({deleted_count} keys deleted)")
            
            return {
                "status": "success",
                "message": f"{len(cleared_sessions)} session(s) cleared successfully",
                "sessions_cleared": cleared_sessions,
                "keys_deleted": total_deleted
            }
    
    except Exception as e:
        logger.error(f"✗ Redis clear error: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================
# COUNSELOR CRM TOOLS
# ============================================================

import json as _json
from openai import AzureOpenAI as _AzureOpenAI

_llm_client = _AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_API_INSTANCE_NAME"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)
_LLM_MODEL = os.getenv("AZURE_OPENAI_API_DEPLOYMENT_NAME", "gpt-4.1-mini")


@mcp.tool()
async def check_user_type(phone: str) -> Dict[str, Any]:
    """Checks if a WhatsApp phone belongs to a counselor (systemuser) or student.
    Detects managers by checking subordinates via parentsystemuserid hierarchy.
    """
    logger.info(f"🔍 [CHECK_USER_TYPE] Checking: {phone}")
    clean_phone = phone[2:] if phone.startswith("91") and len(phone) > 10 else phone

    try:
        endpoint = (
            f"systemusers?$filter=mobilephone eq '{clean_phone}' "
            f"or mobilephone eq '{phone}' or mobilephone eq '+{phone}'"
            f"&$select=systemuserid,fullname,internalemailaddress,mobilephone,title"
            f"&$top=1"
        )
        data = await dataverse.get(endpoint)
        users = data.get("value", [])

        if users:
            user = users[0]
            user_id = user.get("systemuserid")
            fullname = user.get("fullname")
            logger.info(f"✅ [CHECK_USER_TYPE] System user found: {fullname}")

            is_manager = False
            subordinate_ids = []
            try:
                sub_endpoint = (
                    f"systemusers?$filter=_parentsystemuserid_value eq '{user_id}'"
                    f"&$select=systemuserid,fullname"
                )
                sub_data = await dataverse.get(sub_endpoint)
                subordinates = sub_data.get("value", [])
                if subordinates:
                    is_manager = True
                    subordinate_ids = [
                        {"systemuserid": s.get("systemuserid"), "fullname": s.get("fullname")}
                        for s in subordinates
                    ]
                    logger.info(f"👔 [CHECK_USER_TYPE] Manager with {len(subordinates)} subordinate(s)")
            except Exception as sub_e:
                logger.warning(f"⚠️ [CHECK_USER_TYPE] Subordinate check failed: {sub_e}")

            result = {
                "user_type": "counselor_manager" if is_manager else "counselor",
                "systemuserid": user_id,
                "fullname": fullname,
                "email": user.get("internalemailaddress"),
                "phone": user.get("mobilephone"),
                "title": user.get("title"),
            }
            if is_manager:
                result["subordinates"] = subordinate_ids
            return result

        logger.info(f"🆕 [CHECK_USER_TYPE] Not a counselor: {clean_phone}")
        return {"user_type": "student", "phone": clean_phone}

    except Exception as e:
        logger.error(f"💥 [CHECK_USER_TYPE] Error: {e}", exc_info=True)
        return {"user_type": "student", "phone": clean_phone, "error": str(e)}


@mcp.tool()
async def get_subordinate_counselors(manager_id: str) -> Dict[str, Any]:
    """Retrieves counselors reporting to a manager via parentsystemuserid hierarchy."""
    if not manager_id or not manager_id.strip():
        return {"success": False, "error": "manager_id is required"}

    clean_id = manager_id.strip("(){}").strip()
    try:
        endpoint = (
            f"systemusers?$filter=_parentsystemuserid_value eq '{clean_id}'"
            f"&$select=systemuserid,fullname,internalemailaddress,mobilephone,title"
        )
        data = await dataverse.get(endpoint)
        users = data.get("value", [])
        subordinates = [
            {"systemuserid": u.get("systemuserid"), "fullname": u.get("fullname"),
             "email": u.get("internalemailaddress"), "title": u.get("title")}
            for u in users
        ]
        logger.info(f"✅ [GET_SUBORDINATES] Found {len(subordinates)} subordinates")
        return {"success": True, "manager_id": clean_id, "count": len(subordinates), "subordinates": subordinates}
    except Exception as e:
        logger.error(f"💥 [GET_SUBORDINATES] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def resolve_schema(question: str, limit: int = 5) -> Dict[str, Any]:
    """Vector searches CRM schema store to find relevant Dataverse entities and fields."""
    if not question or not question.strip():
        return {"success": False, "error": "Question cannot be empty"}
    limit = max(1, min(limit, 5))
    try:
        query_embedding = await embeddings.embed_query(question)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        sql = """
            SELECT entity_logical_name, entity_display_name, description_text,
                   fields_count, is_activity,
                   1 - (embedding <=> $1::vector)::float as similarity_score
            FROM crm_schema_embeddings
            ORDER BY embedding <=> $1::vector LIMIT $2
        """
        async with postgres.acquire() as conn:
            rows = await conn.fetch(sql, embedding_str, limit)
        if not rows:
            return {"success": False, "message": "No CRM schemas found. Sync schemas first."}
        schemas = [{"entity": r["entity_logical_name"], "display_name": r["entity_display_name"],
                     "schema": r["description_text"], "fields_count": r["fields_count"],
                     "is_activity": r["is_activity"], "relevance": round(float(r["similarity_score"]), 4)}
                    for r in rows]
        return {"success": True, "count": len(schemas), "schemas": schemas}
    except Exception as e:
        logger.error(f"💥 [RESOLVE_SCHEMA] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def build_crm_query(schema_context: str, user_question: str, counselor_id: str = "", subordinate_ids: str = "") -> Dict[str, Any]:
    """Uses LLM to generate a valid OData query from CRM schema context and user question."""
    if not schema_context or not user_question:
        return {"success": False, "error": "Both schema_context and user_question are required"}

    system_prompt = """You are an OData query builder for Microsoft Dynamics 365 / Dataverse.
Given a CRM schema and user question, generate a VALID OData query path.

RULES:
1. Use EntitySetName in URL path. Use $filter, $select, $top, $orderby as needed.
2. For option set fields, use numeric values.
3. For lookup fields use: _<fieldname>_value eq '<guid>'.
4. Return ONLY the OData query path (no base URL, no markdown).
5. $select MUST only contain fields from the Schema.
6. FOR LEADS: Whenever querying 'zx_leads', ALWAYS include 'zx_firstname', 'zx_lastname', and 'zx_leadname' in the $select statement to ensure you have the full name.
7. Default $top to 20. For "my" queries filter by _ownerid_value eq '<counselor_id>'.
8. For "my team" queries, OR filter all subordinate IDs plus counselor_id.
9. NEVER use $expand. NEVER invent field names. NEVER use 'owneridname'.
10. DATE FILTERING: Use ge/le bounds, not eq. STRING FILTERING: Use contains()."""

    user_msg = f"Schema:\n{schema_context}\n\nQuestion: {user_question}"
    if counselor_id:
        user_msg += f"\nCounselor ID: {counselor_id}"
    if subordinate_ids:
        user_msg += f"\nSubordinate IDs: {subordinate_ids}"

    try:
        import asyncio
        response = await asyncio.to_thread(
            _llm_client.chat.completions.create,
            model=_LLM_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
            temperature=0, max_tokens=500
        )
        odata_query = response.choices[0].message.content.strip().replace("```", "").strip()
        logger.info(f"✅ [BUILD_CRM_QUERY] Generated: {odata_query[:100]}...")
        return {"success": True, "odata_query": odata_query}
    except Exception as e:
        logger.error(f"💥 [BUILD_CRM_QUERY] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def execute_crm_query(odata_query: str, max_records: int = 20) -> Dict[str, Any]:
    """Executes an OData query against Dataverse and returns results."""
    if not odata_query or not odata_query.strip():
        return {"success": False, "error": "odata_query cannot be empty"}
    max_records = max(1, min(max_records, 50))
    clean_query = odata_query.strip()
    if "$top=" not in clean_query.lower():
        sep = "&" if "?" in clean_query else "?"
        clean_query += f"{sep}$top={max_records}"
    try:
        data = await dataverse.get(clean_query)
        records = data.get("value", [])
        cleaned = [{k: v for k, v in rec.items()
                     if not k.startswith("@odata") and (not k.startswith("_") or k.endswith("_value"))}
                    for rec in records[:max_records]]
        logger.info(f"✅ [EXECUTE_CRM_QUERY] Returned {len(cleaned)} records")
        return {"success": True, "count": len(cleaned), "records": cleaned, "query": clean_query}
    except httpx.HTTPStatusError as e:
        error_body = e.response.text if hasattr(e, 'response') else str(e)
        return {"success": False, "error": f"HTTP {e.response.status_code}", "details": error_body[:500], "query": clean_query}
    except Exception as e:
        logger.error(f"💥 [EXECUTE_CRM_QUERY] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e), "query": clean_query}


@mcp.tool()
async def find_query_template(question: str) -> Dict[str, Any]:
    """Vector searches pre-built OData query templates for common CRM questions."""
    if not question or not question.strip():
        return {"success": False, "error": "Question cannot be empty"}
    try:
        query_embedding = await embeddings.embed_query(question)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        sql = """
            SELECT intent, question_template, odata_query, parameters,
                   1 - (embedding <=> $1::vector)::float as similarity_score
            FROM crm_query_templates ORDER BY embedding <=> $1::vector LIMIT 1
        """
        async with postgres.acquire() as conn:
            row = await conn.fetchrow(sql, embedding_str)
        if row and row['similarity_score'] >= 0.76:
            return {"success": True, "matched": True, "intent": row['intent'],
                    "question_template": row['question_template'], "odata_query": row['odata_query'],
                    "parameters": row['parameters'], "similarity_score": round(row['similarity_score'], 3)}
        score = round(row['similarity_score'], 3) if row else 0
        return {"success": True, "matched": False, "message": "No template matched.", "best_score": score}
    except Exception as e:
        logger.error(f"💥 [QUERY_TEMPLATE] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
async def search_crm(question: str, counselor_id: str = "", subordinate_ids: str = "") -> Dict[str, Any]:
    """Unified CRM search: template match → schema lookup → query build → execute in one call."""
    logger.info(f"🔎 [SEARCH_CRM] Searching: '{question[:60]}...'")

    template = await find_query_template.fn(question)
    odata_query = None

    if template.get("matched"):
        import datetime
        odata_query = template.get("odata_query", "")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if counselor_id:
            odata_query = odata_query.replace("{{counselor_id}}", counselor_id)
        if subordinate_ids:
            odata_query = odata_query.replace("{{subordinate_ids}}", subordinate_ids)
        odata_query = odata_query.replace("{{today}}", today)
        odata_query = odata_query.replace("{{today_start}}", f"{today}T00:00:00Z")
        odata_query = odata_query.replace("{{today_end}}", f"{today}T23:59:59Z")

    if not odata_query:
        schema_data = await resolve_schema.fn(question)
        if not schema_data.get("success"):
            return schema_data
        schema_text = "\n".join([str(s) for s in schema_data.get("schemas", [])])
        build_data = await build_crm_query.fn(schema_text, question, counselor_id, subordinate_ids)
        if not build_data.get("success"):
            return build_data
        odata_query = build_data.get("odata_query")

    if odata_query:
        return await execute_crm_query.fn(odata_query)
    return {"success": False, "error": "Could not generate query"}


@mcp.tool()
async def batch_crm_operations(operations_json: str) -> Dict[str, Any]:
    """Execute multiple CRM operations (create, update, delete) in a single batch.
    
    Args:
        operations_json: JSON array. Each op: {action, entity, record_id, payload}
            action: 'create', 'update', or 'delete'
            entity: Entity set name (e.g. 'zx_leads', 'tasks', 'zx_engagementhistories')
            record_id: GUID (required for update/delete)
            payload: Field values dict (for create/update)
    
    CRITICAL LOOKUP RULES:
    1. NEVER send lookup fields as direct properties (e.g., "zx_collegeid": "GUID" is WRONG).
    2. ALWAYS use @odata.bind syntax for any field that links to another table.
    3. Syntax: "navigation_property_name@odata.bind": "/entity_set_name(GUID)"
    
    Examples:
    - Link Task to Lead: {"regardingobjectid_zx_lead@odata.bind": "/zx_leads(guid)"}
    - Set Lead Course: {"zx_InterestedCourse@odata.bind": "/zx_courses(guid)"}
    - Set Owner: {"ownerid@odata.bind": "/systemusers(guid)"}
    """
    if not operations_json or not operations_json.strip():
        return {"status": "error", "message": "operations_json is required"}
    try:
        ops = _json.loads(operations_json)
    except _json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON: {e}"}
    if not isinstance(ops, list) or len(ops) == 0:
        return {"status": "error", "message": "operations_json must be a non-empty JSON array"}
    if len(ops) > 20:
        return {"status": "error", "message": "Maximum 20 operations per batch"}

    batch_ops = []
    for i, op in enumerate(ops):
        action = op.get("action", "").lower()
        entity = op.get("entity", "")
        record_id = op.get("record_id", "").strip("(){}").strip() if op.get("record_id") else ""
        payload = op.get("payload", {})

        # --- AUTO-FIX PAYLOAD LOOKUPS ---
        # CRM fails if user sends "field_id": "guid". Must be "field_id@odata.bind": "/set(guid)"
        fixed_payload = {}
        for k, v in payload.items():
            if isinstance(v, str) and len(v) == 36 and "-" in v: # Potential GUID
                # If it ends in 'id' but doesn't have @odata.bind
                if (k.endswith("id") or k.endswith("_value")) and "@odata.bind" not in k:
                    # Attempt to infer entity set name (naive pluralization)
                    entity_set = ""
                    if "college" in k: entity_set = "zx_colleges"
                    elif "course" in k: entity_set = "zx_courses"
                    elif "branch" in k: entity_set = "zx_branchs"
                    elif "lead" in k: entity_set = "zx_leads"
                    elif "owner" in k: entity_set = "systemusers"
                    
                    if entity_set:
                        new_key = k if "@odata.bind" in k else f"{k}@odata.bind"
                        fixed_payload[new_key] = f"/{entity_set}({v})"
                        logger.info(f"🔧 [BATCH_CRM] Auto-fixed lookup: {k} -> {new_key}")
                        continue
            fixed_payload[k] = v
        payload = fixed_payload
        # --------------------------------
        if not entity:
            return {"status": "error", "message": f"Operation {i+1}: 'entity' is required"}
        if action == "create":
            batch_ops.append({"method": "POST", "endpoint": entity, "payload": payload})
        elif action == "update":
            if not record_id:
                return {"status": "error", "message": f"Operation {i+1}: 'record_id' required for update"}
            batch_ops.append({"method": "PATCH", "endpoint": f"{entity}({record_id})", "payload": payload})
        elif action == "delete":
            if not record_id:
                return {"status": "error", "message": f"Operation {i+1}: 'record_id' required for delete"}
            batch_ops.append({"method": "DELETE", "endpoint": f"{entity}({record_id})", "payload": {}})
        else:
            return {"status": "error", "message": f"Operation {i+1}: invalid action '{action}'"}

    logger.info(f"⚡ [BATCH_CRM] Executing {len(batch_ops)} operations")
    try:
        result = await dataverse.batch(batch_ops)
        if result.get("success"):
            logger.info(f"✅ [BATCH_CRM] Batch completed: {len(batch_ops)} operations")
        else:
            logger.error(f"❌ [BATCH_CRM] Batch failed: {result.get('error', 'Unknown')}")
        return result
    except Exception as e:
        logger.error(f"💥 [BATCH_CRM] Error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============================================================
# API: Seed / List Query Templates
# ============================================================

@mcp.custom_route("/api/query-templates", methods=["POST"])
async def seed_query_templates(request):
    """POST /api/query-templates - Seed pre-built OData query templates."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    templates = body.get("templates", [])
    if not templates:
        return JSONResponse({"error": "No templates provided"}, status_code=400)

    inserted, errors = [], []
    for i, t in enumerate(templates):
        intent = t.get("intent", "").strip()
        question = t.get("question_template", "").strip()
        odata = t.get("odata_query", "").strip()
        params = t.get("parameters", "")
        if not intent or not question or not odata:
            errors.append({"index": i, "error": "Missing required fields"})
            continue
        try:
            emb = await embeddings.embed_query(question)
            emb_str = "[" + ",".join(map(str, emb)) + "]"
            async with postgres.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("DELETE FROM crm_query_templates WHERE intent = $1", intent)
                    await conn.execute(
                        "INSERT INTO crm_query_templates (intent, question_template, odata_query, parameters, embedding) VALUES ($1, $2, $3, $4, $5::vector)",
                        intent, question, odata, params, emb_str)
            inserted.append({"intent": intent})
        except Exception as e:
            errors.append({"index": i, "intent": intent, "error": str(e)})

    return JSONResponse({"success": True, "inserted_count": len(inserted), "error_count": len(errors),
                         "inserted": inserted, "errors": errors if errors else None})


@mcp.custom_route("/api/query-templates", methods=["GET"])
async def list_query_templates(request):
    """GET /api/query-templates - List all stored query templates."""
    try:
        async with postgres.acquire() as conn:
            rows = await conn.fetch(
                "SELECT intent, question_template, odata_query, parameters, created_at FROM crm_query_templates ORDER BY created_at DESC")
        templates = [{"intent": r['intent'], "question_template": r['question_template'],
                      "odata_query": r['odata_query'], "parameters": r['parameters'],
                      "created_at": r['created_at'].isoformat() if r['created_at'] else None} for r in rows]
        return JSONResponse({"success": True, "count": len(templates), "templates": templates})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8001,
            host="0.0.0.0", path="/education")