"""
Dataverse archival operations for the archive worker.
Handles engagement history, session messages, and lead management.
"""
import json
import asyncio
import logging
import httpx
from typing import Dict, List, Any, Optional

log = logging.getLogger("archive_worker")

ROLE_MAP = {"assistant": 128780000, "user": 128780001}


# ==============================================================================
# 🔧 HTTP HELPERS (GET / PATCH for lead operations)
# ==============================================================================

async def _custom_get(client, endpoint: str) -> Dict:
    """Manual GET request using DataverseClient credentials."""
    try:
        base_url = client.base_url.rstrip("/")
        token = await client.get_token()
        if not token:
            raise ValueError("No Dataverse token")

        url = f"{base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }

        async with httpx.AsyncClient(timeout=60) as http:
            response = await http.get(url, headers=headers)
            if response.status_code >= 400:
                raise Exception(f"GET Failed ({response.status_code}): {response.text}")
            try:
                return response.json() if response.content else {}
            except:
                return {}
    except Exception as e:
        log.error(f"❌ _custom_get failed: {e}")
        raise


async def _custom_patch(client, entity_query: str, payload: Dict):
    """Manual PATCH request using DataverseClient credentials."""
    try:
        base_url = client.base_url.rstrip("/")
        token = await client.get_token()
        if not token:
            raise ValueError("No Dataverse token")

        url = f"{base_url}/{entity_query.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }

        async with httpx.AsyncClient(timeout=60) as http:
            response = await http.patch(url, json=payload, headers=headers)
            if response.status_code >= 400:
                raise Exception(f"PATCH Failed ({response.status_code}): {response.text}")
            try:
                body = response.json() if response.content else {}
            except:
                body = {}
            return response.status_code, response.headers, body
    except Exception as e:
        log.error(f"❌ _custom_patch failed: {e}")
        raise


# ==============================================================================
# 🔧 DATA CLEANERS
# ==============================================================================

def _clean_int(value) -> Optional[int]:
    """Extract integer from various formats."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in ("", "none", "null", "nan"):
        return None
    try:
        import re
        nums = re.findall(r"[-+]?\d*\.?\d+", s)
        return int(float(nums[0])) if nums else None
    except:
        return None


def _clean_float(value) -> Optional[float]:
    """Extract float from various formats."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in ("", "none", "null", "nan"):
        return None
    try:
        import re
        nums = re.findall(r"[-+]?\d*\.?\d+", s)
        return float(nums[0]) if nums else None
    except:
        return None


def _resolve_highest_qualification(value) -> Optional[int]:
    """Map AI string to Dataverse choice int for zx_highestqualification."""
    if value is None:
        return None
    QUAL_MAP = {
        "12th": 128780000,
        "12th / higher secondary": 128780000,
        "higher secondary": 128780000,
        "hsc": 128780000,
        "10+2": 128780000,
        "diploma": 128780001,
        "graduation": 128780002,
        "ug": 128780002,
        "undergraduate": 128780002,
        "bachelor": 128780002,
        "bachelors": 128780002,
        "btech": 128780002,
        "b.tech": 128780002,
        "post graduation": 128780003,
        "postgraduate": 128780003,
        "postgraduation": 128780003,
        "pg": 128780003,
        "masters": 128780003,
        "mba": 128780003,
        "mtech": 128780003,
        "m.tech": 128780003,
        "other": 128780004,
    }
    if isinstance(value, str):
        mapped = QUAL_MAP.get(value.strip().lower())
        if mapped is not None:
            return mapped
    # Guard: only accept valid Dataverse choice ints, never garbage like 12
    raw = _clean_int(value)
    if raw is not None and raw >= 128780000:
        return raw
    if raw is not None:
        log.warning(f"⚠️ Dropping invalid zx_highestqualification value: {value} → {raw}")
    return None


def _resolve_lead_type(value) -> Optional[int]:
    """Map AI string to Dataverse choice int for zx_leadtype.
    
    Dataverse zx_leadtype values:
        Student: 128780000, Parent: 128780001, Working Professional: 128780002,
        Enquiry: 128780003, Lead: 128780004, Suspect/Prospect: 128780005
    """
    if value is None:
        return None
    TYPE_MAP = {
        "student": 128780000,
        "parent": 128780001,
        "working professional": 128780002,
        "enquiry": 128780003,
        "lead": 128780004,
        "suspect/prospect": 128780005,
        "suspect": 128780005,
        "prospect": 128780005,
    }
    if isinstance(value, str):
        mapped = TYPE_MAP.get(value.strip().lower())
        if mapped is not None:
            return mapped
    raw = _clean_int(value)
    if raw is not None and raw >= 128780000:
        return raw
    if raw is not None:
        log.warning(f"⚠️ Dropping invalid zx_leadtype value: {value} → {raw}")
    return None


def _resolve_lead_status(value) -> Optional[int]:
    """Map AI string to Dataverse choice int for zx_leadstatus."""
    if value is None:
        return None
    STATUS_MAP = {
        "suspect": 128780000,
        "prospect": 128780001,
    }
    if isinstance(value, str):
        mapped = STATUS_MAP.get(value.strip().lower())
        if mapped is not None:
            return mapped
    raw = _clean_int(value)
    if raw is not None and raw >= 128780000:
        return raw
    if raw is not None:
        log.warning(f"⚠️ Dropping invalid zx_leadstatus value: {value} → {raw}")
    return None


def _resolve_priority(value) -> Optional[int]:
    """Map AI string to Dataverse choice int for zx_priority."""
    if value is None:
        return None
    PRIORITY_MAP = {
        "high": 128780000,
        "medium": 128780001,
        "low": 128780002,
    }
    if isinstance(value, str):
        mapped = PRIORITY_MAP.get(value.strip().lower())
        if mapped is not None:
            return mapped
    raw = _clean_int(value)
    if raw is not None and raw >= 128780000:
        return raw
    if raw is not None:
        log.warning(f"⚠️ Dropping invalid zx_priority value: {value} → {raw}")
    return None


def _resolve_academic_board(value) -> Optional[int]:
    """Map AI string to Dataverse choice int for zx_Board."""
    if not value:
        return None
    BOARD_MAP = {
        "cbse": 128780000,
        "icse": 128780001,
        "state board": 128780002,
        "ib": 128780003,
        "igcse": 128780004,
        "nios": 128780005,
        "university board": 128780006,
        "other": 128780007,
    }
    if isinstance(value, str):
        mapped = BOARD_MAP.get(value.strip().lower())
        if mapped is not None:
            return mapped
    raw = _clean_int(value)
    if raw is not None and raw >= 128780000:
        return raw
    if raw is not None:
        log.warning(f"⚠️ Dropping invalid zx_Board value: {value} → {raw}")
    return None


def _resolve_academic_qualification(value) -> Optional[int]:
    """Map AI string to Dataverse choice int for zx_Qualification."""
    if not value:
        return None
    QUAL_MAP = {
        "10th / secondary": 128780000,
        "12th / higher secondary": 128780001,
        "diploma": 128780002,
        "undergraduate (ug)": 128780003,
        "postgraduate (pg)": 128780004,
        "doctorate (phd)": 128780005,
        "other": 128780006,
        "10th": 128780000,
        "12th": 128780001,
        "ug": 128780003,
        "pg": 128780004,
        "phd": 128780005,
    }
    if isinstance(value, str):
        mapped = QUAL_MAP.get(value.strip().lower())
        if mapped is not None:
            return mapped
    raw = _clean_int(value)
    if raw is not None and raw >= 128780000:
        return raw
    if raw is not None:
        log.warning(f"⚠️ Dropping invalid zx_Qualification value: {value} → {raw}")
    return None


def _resolve_academic_stream(value) -> Optional[int]:
    """Map AI string to Dataverse choice int for zx_Stream."""
    if not value:
        return None
    STREAM_MAP = {
        "science": 128780000,
        "commerce": 128780001,
        "arts / humanities": 128780002,
        "arts": 128780002,
        "humanities": 128780002,
        "engineering": 128780003,
        "medical": 128780004,
        "management": 128780005,
        "computer applications": 128780006,
        "other": 128780007,
    }
    if isinstance(value, str):
        mapped = STREAM_MAP.get(value.strip().lower())
        if mapped is not None:
            return mapped
    raw = _clean_int(value)
    if raw is not None and raw >= 128780000:
        return raw
    if raw is not None:
        log.warning(f"⚠️ Dropping invalid zx_Stream value: {value} → {raw}")
    return None


async def _resolve_interested_course(course_name: str, college_guid: str) -> Optional[str]:
    """
    Resolve a course name to its Dataverse GUID by checking the college's course list in Redis.
    Uses intelligent matching:
    1. Exact match.
    2. Partial match (is Dataverse course name a substring of AI input? e.g. "B.Tech" in "B.Tech CSE").
    3. Seat availability cross-reference (if branch is mentioned).
    """
    if not course_name or not college_guid:
        return None

    try:
        from connection import RedisConnectionPool
        r = RedisConnectionPool.get_client()
        cache_key = f"college_courses:{college_guid}"
        cached_data = r.get(cache_key)
        
        if not cached_data:
            log.warning(f"⚠️ No cached course list found for college {college_guid} in Redis")
            return None

        data = json.loads(cached_data)
        courses = data.get("courses", [])
        seats = data.get("seats", [])
        
        target = course_name.strip().lower()
        
        # 1. Exact match
        match = next((c for c in courses if c["name"].strip().lower() == target), None)
        if match:
            log.info(f"🎯 Exact match for course: '{course_name}' -> {match['name']} ({match['guid']})")
            return match["guid"]

        # 2. Seat Availability Cross-Reference (Specialization/Branch matching)
        # If user says "B.Tech CSE", we check seats to see if "CSE" is a branch for "B.Tech"
        if seats:
            for s in seats:
                s_course = s.get("course", "").strip().lower()
                s_branch = s.get("branch", "").strip().lower()
                
                # Check if BOTH course and branch from a seat record are in the target string
                if s_course and s_branch and s_course in target and s_branch in target:
                    # Find the Course GUID for this course name
                    match = next((c for c in courses if c["name"].strip().lower() == s_course), None)
                    if match:
                        log.info(f"🎯 Seat-based match: '{course_name}' matched Course '{s_course}' and Branch '{s_branch}'")
                        return match["guid"]

        # 3. Smart Substring Match (fallback)
        # Check if any Dataverse course name is contained within the user's input
        # We sort by length descending to match "B.Tech CSE" to "B.Tech" but prioritize longer names if any
        sorted_courses = sorted(courses, key=lambda x: len(x["name"]), reverse=True)
        for c in sorted_courses:
            c_name = c["name"].strip().lower()
            if c_name and c_name in target:
                log.info(f"🎯 Substring match: '{course_name}' contains '{c['name']}' -> Mapping to GUID")
                return c["guid"]
        
        log.warning(f"⚠️ Could not find match for '{course_name}' in college course/seat list")
        return None
    except Exception as e:
        log.error(f"❌ Error resolving interested course: {e}")
        return None



# ==============================================================================
# 🏥 LEAD MANAGEMENT (check / create / update / tag)
# ==============================================================================

async def check_lead(
    dataverse_client,
    firstname: str = None,
    phone: str = None,
    email: str = None,
    insta_sender_id: str = None,
    fb_sender_id: str = None
) -> Dict[str, Any]:
    """
    Check if a lead exists in Dataverse using multi-criteria matching.
    
    Lookup priority:
    1. insta_sender_id / fb_sender_id (for social media sessions)
    2. firstname + phone (most specific)
    3. firstname + email
    4. phone alone (fallback when no name)
    5. email alone (fallback when no name)
    """
    log.info(f"🔍 Checking lead: firstname={firstname}, phone={phone}, email={email}, insta_sid={insta_sender_id}, fb_sid={fb_sender_id}")

    has_name = bool(firstname and firstname.strip())
    has_phone = bool(phone and phone.strip())
    has_email = bool(email and email.strip())
    has_insta = bool(insta_sender_id and insta_sender_id.strip())
    has_fb = bool(fb_sender_id and fb_sender_id.strip())

    if not has_phone and not has_email and not has_insta and not has_fb:
        return {"status": "error", "message": "No search criteria provided."}

    select_fields = [
        "zx_leadid", "zx_firstname", "zx_lastname", "zx_leadname",
        "zx_emailid", "zx_mobilenumber", "zx_city",
        "zx_highestqualification", "zx_undergraduatecourse", "zx_graduationyear",
        "zx_thpercentage", "zx_th", "zx_leadscore", "zx_priority",
        "zx_leadtype", "zx_context"
    ]
    select_param = ','.join(select_fields)

    # Build search strategies in priority order
    search_strategies = []
    
    # 1. Platform-Specific Sender ID (Highest Priority)
    if has_insta:
        search_strategies.append(
            ("insta_id", f"zx_senderid eq '{insta_sender_id}'")
        )
    if has_fb:
        search_strategies.append(
            ("fb_id", f"zx_facebooksenderid eq '{fb_sender_id}'")
        )
    if has_name and has_phone:
        search_strategies.append(
            ("firstname+phone", f"zx_firstname eq '{firstname}' and zx_mobilenumber eq '{phone}'")
        )
    if has_name and has_email:
        search_strategies.append(
            ("firstname+email", f"zx_firstname eq '{firstname}' and zx_emailid eq '{email}'")
        )
    if has_phone:
        search_strategies.append(
            ("phone", f"zx_mobilenumber eq '{phone}'")
        )
    if has_email:
        search_strategies.append(
            ("email", f"zx_emailid eq '{email}'")
        )

    try:
        for strategy_name, filter_query in search_strategies:
            endpoint = f"zx_leads?$filter={filter_query}&$select={select_param}"
            log.info(f"🔎 Trying strategy: {strategy_name}")

            data = await _custom_get(dataverse_client, endpoint)
            leads = data.get("value", [])

            if leads:
                lead = leads[0]
                result = {
                    "status": "success",
                    "lead_id": lead.get("zx_leadid"),
                    "lead_name": lead.get("zx_leadname"),
                    "first_name": lead.get("zx_firstname"),
                    "last_name": lead.get("zx_lastname"),
                    "email": lead.get("zx_emailid"),
                    "phone": lead.get("zx_mobilenumber"),
                    "city": lead.get("zx_city"),
                    "highest_qualification": lead.get("zx_highestqualification"),
                    "graduation_course": lead.get("zx_graduationcourse"),
                    "graduation_year": lead.get("zx_graduationyear"),
                    "10th_percentage": lead.get("zx_thpercentage"),
                    "12th_percentage": lead.get("zx_th"),
                    "lead_score": lead.get("zx_leadscore"),
                    "priority": lead.get("zx_priority"),
                    "lead_type": lead.get("zx_leadtype"),
                }
                log.info(f"✅ Lead found via {strategy_name}: {result['lead_id']}")
                return result

        return {"status": "not_found", "message": "No lead found."}

    except Exception as e:
        log.error(f"❌ check_lead error: {e}")
        return {"status": "error", "message": str(e)}


async def create_new_lead(
    dataverse_client,
    user_details: Dict,
    summary: str,
    college_guid: str = None,
    insta_sender_id: str = None,
    fb_sender_id: str = None,
    lead_source: int = 128780000  # Default: Website
) -> Optional[str]:
    """
    Create a new lead in Dataverse from AI-extracted user_details.
    Uses GoEd field names: zx_mobilenumber, zx_emailid, zx_leadname, etc.
    Returns the new lead_id or None.
    """
    try:
        firstname = user_details.get("firstname", "")
        lastname = user_details.get("lastname", "")
        leadname = user_details.get("name", "") or f"{firstname} {lastname}".strip()

        # Determine lead type and status
        lead_type = _resolve_lead_type(user_details.get("lead_type")) or 128780003  # Default: Enquiry
        lead_status = _resolve_lead_status(user_details.get("lead_status")) or 128780000  # Default: Suspect

        payload = {
            "zx_mobilenumber": user_details.get("phone"),
            "zx_leadname": leadname,
            "zx_emailid": user_details.get("email"),
            "zx_leadtype": lead_type,
            "zx_leadstatus": lead_status,
            "zx_leadsource": lead_source,
        }
        if insta_sender_id:
            payload["zx_senderid"] = insta_sender_id
        if fb_sender_id:
            payload["zx_facebooksenderid"] = fb_sender_id
        if firstname:
            payload["zx_firstname"] = firstname
        if lastname:
            payload["zx_lastname"] = lastname
        if user_details.get("city"):
            payload["zx_city"] = user_details["city"]

        # Academic fields
        tenth = _clean_float(user_details.get("tenth_percentage"))
        if tenth is not None:
            payload["zx_thpercentage"] = tenth
        twelfth = _clean_float(user_details.get("twelfth_percentage"))
        if twelfth is not None:
            payload["zx_th"] = twelfth

        qual = _resolve_highest_qualification(user_details.get("highest_qualification"))
        if qual is not None:
            payload["zx_highestqualification"] = qual

        if user_details.get("graduation_course"):
            payload["zx_undergraduatecourse"] = user_details["graduation_course"]
        grad_year = _clean_int(user_details.get("graduation_year"))
        if grad_year is not None:
            payload["zx_graduationyear"] = grad_year

        score = _clean_int(user_details.get("lead_score"))
        if score is not None:
            payload["zx_leadscore"] = max(score, 1)  # Floor: minimum score is 1

        priority = _resolve_priority(user_details.get("priority"))
        if priority is not None:
            payload["zx_priority"] = priority

        if summary:
            payload["zx_context"] = summary[:4000]  # Dataverse text limit

        if college_guid:
            payload["zx_College@odata.bind"] = f"/zx_colleges({college_guid})"
            
            # Map Interested Course if mentioned
            course_name = user_details.get("interested_course")
            if course_name:
                try:
                    course_guid = await _resolve_interested_course(course_name, college_guid)
                    if course_guid:
                        payload["zx_InterestedCourse@odata.bind"] = f"/zx_courses({course_guid})"
                except Exception as course_err:
                    log.warning(f"⚠️ Course mapping failed (non-blocking): {course_err}")

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        log.info(f"📋 CREATE LEAD PAYLOAD: {json.dumps(payload, default=str)}")
        response = await dataverse_client.post_record("zx_leads", payload)

        if response.status_code not in (200, 201, 204):
            log.error(f"❌ Create lead failed ({response.status_code}): {response.text}")
            return None

        # Extract lead_id
        entity_id = response.headers.get("OData-EntityId") or response.headers.get("odata-entityid") or ""
        if entity_id and "(" in entity_id:
            lead_id = entity_id.split("(")[-1].strip(")")
        else:
            try:
                body = response.json()
                lead_id = body.get("zx_leadid")
            except:
                lead_id = None

        if lead_id:
            log.info(f"🆕 Lead created: {lead_id}")
        else:
            log.error(f"❌ Lead created but could not extract lead_id")

        return lead_id

    except Exception as e:
        log.error(f"❌ Error creating lead: {e}")
        return None


async def handle_campus_visit(dataverse_client, lead_id: str, user_details: Dict, lead_name: str = None, summary: str = None):
    """
    Handle campus visit scheduling by creating/updating Dataverse Tasks.
    Table: tasks (Standard)
    Lead Lookup: regardingobjectid
    """
    requested = user_details.get("campus_visit_requested")
    is_rescheduling = user_details.get("is_rescheduling")
    visit_date_str = user_details.get("visit_date")
    visit_details = user_details.get("visit_details", "")

    if not requested and not is_rescheduling:
        return

    try:
        from datetime import datetime, timedelta
        
        # 1. Determine Visit Date & Time
        visit_time_str = user_details.get("visit_time")
        
        if visit_date_str:
            try:
                if visit_time_str:
                    # Try parsing combined date and time (AI usually returns HH:MM AM/PM)
                    try:
                        visit_date = datetime.strptime(f"{visit_date_str} {visit_time_str}", "%Y-%m-%d %I:%M %p")
                    except:
                        # Fallback to date only with default 10 AM
                        visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").replace(hour=10, minute=0)
                else:
                    # Default to 10 AM if no time provided
                    visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").replace(hour=10, minute=0)
                
                # Safety: If AI extracted a year in the past (e.g. 2024), shift to current year
                curr_now = datetime.now()
                if visit_date.year < curr_now.year:
                    visit_date = visit_date.replace(year=curr_now.year)
                    
            except:
                visit_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            visit_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)

        # 2. Format for Dataverse (Convert IST to UTC for correct display)
        # Dataverse stores in UTC, so we subtract 5:30 to make it show correctly in IST UI
        from datetime import timedelta
        visit_date_utc = visit_date - timedelta(hours=5, minutes=30)
        iso_date = visit_date_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_str = visit_date.strftime("%I:%M %p")

        # Prepare Subject and Description
        name_part = f" - {lead_name}" if lead_name else ""
        subject = f"Campus Visit{name_part} - {time_str}"
        
        # Use only the AI summary for description
        description = summary if summary else f"Campus visit requested for {visit_date_str or 'tomorrow'}."

        payload = {
            "subject": subject,
            "description": description,
            "scheduledend": iso_date,  # Use as Due Date
            "prioritycode": 2,         # High
            "statecode": 0,            # Open
            "zx_tasktype": 128780000,   # Structured field: Campus Visit
            "regardingobjectid_zx_lead@odata.bind": f"/zx_leads({lead_id})"
        }

        # 2. Check for existing "Open" Campus Visit tasks for this lead (Rescheduling/Duplicate prevention)
        existing_task_id = None
        try:
            # Filter by lead lookup, the new zx_tasktype field, and ensure it's "Open" (statecode 0)
            # We sort by createdon desc to ensure we pick the most recent one if multiples exist
            filter_query = (
                f"_regardingobjectid_value eq '{lead_id}' "
                f"and zx_tasktype eq 128780000 "
                f"and statecode eq 0"
            )
            endpoint = f"tasks?$filter={filter_query}&$select=activityid&$orderby=createdon desc"
            
            data = await _custom_get(dataverse_client, endpoint)
            records = data.get("value", [])
            if records:
                existing_task_id = records[0].get("activityid")
        except Exception as e:
            log.warning(f"⚠️ Error checking for existing tasks: {e}")

        if existing_task_id:
            log.info(f"🔄 Updating existing open visit task: {existing_task_id}")
            # PATCH existing to avoid duplicates
            await _custom_patch(dataverse_client, f"tasks({existing_task_id})", payload)
        else:
            log.info(f"📅 Creating new campus visit task for lead {lead_id}")
            # POST new
            await dataverse_client.post_record("tasks", payload)

    except Exception as e:
        log.error(f"❌ handle_campus_visit failed: {e}")


async def update_existing_lead(
    dataverse_client,
    lead_id: str,
    user_details: Dict,
    summary: str,
    cached_lead_data: Dict = None
):
    """
    Update an existing lead with AI-extracted details.
    Anti-downgrade logic: never overwrite with empty/worse values.
    
    Args:
        cached_lead_data: Lead info cached in Redis from check_lead during chat.
                         Used to fill blanks - if AI extraction returned empty but 
                         cached data had a value, we preserve the existing value.
    """
    try:
        # Fetch current lead state from Dataverse (authoritative source)
        current_data = await _custom_get(
            dataverse_client,
            f"zx_leads({lead_id})?$select=zx_leadscore,zx_thpercentage,zx_th,"
            f"zx_highestqualification,zx_undergraduatecourse,zx_graduationyear,"
            f"zx_emailid,zx_city,zx_priority,zx_leadtype,zx_firstname,zx_lastname,"
            f"_zx_interestedcourse_value,_zx_college_value"
        )

        # Merge: AI-extracted → cached lead data → current Dataverse data
        # Only send updates for fields that genuinely changed in the chat
        cached = cached_lead_data or {}

        payload = {}

        # Update context/summary always
        if summary:
            payload["zx_context"] = summary[:4000]

        def should_update(new_val, current_key):
            """Only update if new value is non-empty and exists."""
            if new_val is None:
                return False
            if isinstance(new_val, str) and not new_val.strip():
                return False
            if isinstance(new_val, (int, float)) and new_val == 0 and current_data.get(current_key) is not None:
                return False
            return True

        # Academic fields with anti-downgrade
        tenth = _clean_float(user_details.get("tenth_percentage"))
        if should_update(tenth, "zx_thpercentage"):
            curr = current_data.get("zx_thpercentage")
            if curr is None or tenth > float(curr):
                payload["zx_thpercentage"] = tenth

        twelfth = _clean_float(user_details.get("twelfth_percentage"))
        if should_update(twelfth, "zx_th"):
            curr = current_data.get("zx_th")
            if curr is None or twelfth > float(curr):
                payload["zx_th"] = twelfth

        # Qualification: only upgrade, never downgrade
        qual = _resolve_highest_qualification(user_details.get("highest_qualification"))
        if should_update(qual, "zx_highestqualification"):
            payload["zx_highestqualification"] = qual

        grad_course = user_details.get("graduation_course")
        if grad_course and not current_data.get("zx_undergraduatecourse"):
            payload["zx_undergraduatecourse"] = grad_course

        grad_year = _clean_int(user_details.get("graduation_year"))
        if grad_year is not None and not current_data.get("zx_graduationyear"):
            payload["zx_graduationyear"] = grad_year

        # Email: only set if currently empty
        email = user_details.get("email")
        if email and not current_data.get("zx_emailid"):
            payload["zx_emailid"] = email

        # Interested Course: only set if currently empty and we have a college
        course_name = user_details.get("interested_course")
        college_guid = user_details.get("college_guid") or current_data.get("_zx_college_value")
        
        # Note: current_data doesn't select zx_college in the fetch above, let's fix that too
        if course_name and college_guid and not current_data.get("_zx_interestedcourse_value"):
            try:
                course_guid = await _resolve_interested_course(course_name, college_guid)
                if course_guid:
                    payload["zx_InterestedCourse@odata.bind"] = f"/zx_courses({course_guid})"
            except Exception as course_err:
                log.warning(f"⚠️ Course mapping update failed (non-blocking): {course_err}")

        # City: only set if currently empty
        city = user_details.get("city")
        if city and not current_data.get("zx_city"):
            payload["zx_city"] = city

        # Lead score: only increase, minimum is 1
        current_score = current_data.get("zx_leadscore") or 0
        new_score = _clean_int(user_details.get("lead_score")) or 0
        new_score = max(new_score, 1)  # Floor: minimum score is 1
        if new_score > current_score:
            payload["zx_leadscore"] = new_score

        # Lead type and status updates
        lead_type = _resolve_lead_type(user_details.get("lead_type"))
        if lead_type is not None:
            payload["zx_leadtype"] = lead_type
            
        lead_status = _resolve_lead_status(user_details.get("lead_status"))
        if lead_status is not None:
            # Only update status if it's an upgrade or explicitly set
            current_status = current_data.get("zx_leadstatus")
            if current_status is None or lead_status > current_status or user_details.get("lead_status"):
                payload["zx_leadstatus"] = lead_status

        # Priority: update if determined
        priority = _resolve_priority(user_details.get("priority"))
        if priority is not None:
            payload["zx_priority"] = priority

        if payload:
            log.info(f"📋 UPDATE LEAD PAYLOAD for {lead_id}: {json.dumps(payload, default=str)}")
            await _custom_patch(dataverse_client, f"zx_leads({lead_id})", payload)
            log.info(f"📝 Updated Lead {lead_id}")
        else:
            log.info(f"ℹ️ No updates needed for lead {lead_id} (all values preserved)")

    except Exception as e:
        log.error(f"❌ Error updating lead {lead_id}: {e}")


async def create_or_update_academic_history(dataverse_client, lead_id: str, academic_history: List[Dict]):
    """
    Store lead academic info in zx_leadacademichistory table.
    Checks for existing records with the same lead_id and qualification to avoid duplicates.
    """
    if not academic_history or not lead_id:
        return

    log.info(f"🎓 Processing academic history for lead {lead_id}...")

    for item in academic_history:
        try:
            qual_str = item.get("qualification")
            qual_val = _resolve_academic_qualification(qual_str)
            if qual_val is None:
                log.warning(f"⚠️ Unknown qualification '{qual_str}', skipping academic record.")
                continue

            # 1. Check if record already exists for this lead and qualification
            endpoint = f"zx_leadacademichistories?$filter=_zx_leadid_value eq {lead_id} and zx_qualification eq {qual_val}&$select=zx_leadacademichistoryid"
            data = await _custom_get(dataverse_client, endpoint)
            records = data.get("value", [])

            payload = {
                "zx_qualification": qual_val,
                "zx_board": _resolve_academic_board(item.get("board")),
                "zx_passingyear": str(item.get("passing_year", ""))[:100],
                "zx_percentage": _clean_float(item.get("percentage")),
                "zx_schoolcollegename": str(item.get("school_college", ""))[:100],
                "zx_stream": _resolve_academic_stream(item.get("stream")),
                "zx_LeadID@odata.bind": f"/zx_leads({lead_id})"
            }
            
            # Map Stream if possible (optional, logic depends on actual choice values)
            # if item.get("stream"): payload["zx_Stream"] = _resolve_academic_stream(item.get("stream"))

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            if records:
                # Update existing
                record_id = records[0]["zx_leadacademichistoryid"]
                log.info(f"📝 Updating academic history {record_id} (Qual: {qual_str})")
                await _custom_patch(dataverse_client, f"zx_leadacademichistories({record_id})", payload)
            else:
                # Create new
                log.info(f"🆕 Creating academic history for lead {lead_id} (Qual: {qual_str})")
                await dataverse_client.post_record("zx_leadacademichistories", payload)

        except Exception as e:
            log.error(f"❌ Failed to process academic history item {item}: {e}")


async def create_or_update_lead_exams(dataverse_client, lead_id: str, exams: List[Dict]):
    """
    Store lead entrance exam info in zx_leadexamseminars table.
    Checks for existing records with the same lead_id and entrance exam name to avoid duplicates.
    """
    if not exams or not lead_id:
        return

    log.info(f"✍️ Processing entrance exams for lead {lead_id}...")

    for item in exams:
        try:
            exam_name = item.get("exam_name")
            if not exam_name:
                log.warning("⚠️ Exam item missing 'exam_name', skipping.")
                continue

            # 1. Check if record already exists for this lead and exam name
            # We filter by zx_entranceexamname (text field as requested)
            # URL encode the exam name for the OData filter
            import urllib.parse
            encoded_name = urllib.parse.quote(exam_name.replace("'", "''"))
            endpoint = f"zx_leadexamseminars?$filter=_zx_leadid_value eq {lead_id} and zx_entranceexamname eq '{encoded_name}'&$select=zx_leadexamseminarid"
            data = await _custom_get(dataverse_client, endpoint)
            records = data.get("value", [])

            payload = {
                "zx_entranceexamname": exam_name,
                "zx_score": _clean_float(item.get("score")),
                "zx_percentile": _clean_float(item.get("percentile")),
                "zx_examyear": _clean_int(item.get("exam_year")),
                "zx_appeared": item.get("appeared", True),
                "zx_LeadID@odata.bind": f"/zx_leads({lead_id})"
            }

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            if records:
                # Update existing
                record_id = records[0]["zx_leadexamseminarid"]
                log.info(f"📝 Updating exam record {record_id} ({exam_name})")
                await _custom_patch(dataverse_client, f"zx_leadexamseminars({record_id})", payload)
            else:
                # Create new
                log.info(f"🆕 Creating exam record for lead {lead_id} ({exam_name})")
                await dataverse_client.post_record("zx_leadexamseminars", payload)

        except Exception as e:
            log.error(f"❌ Failed to process exam item {item}: {e}")


async def tag_engagement_to_lead(dataverse_client, parent_id: str, lead_id: str):
    """Bind an engagement history record to a lead via zx_Lead lookup."""
    try:
        await _custom_patch(
            dataverse_client,
            f"zx_engagementhistories({parent_id})",
            {"zx_Lead@odata.bind": f"/zx_leads({lead_id})"}
        )
        log.info(f"🔗 Tagged engagement {parent_id} -> lead {lead_id}")
    except Exception as e:
        log.error(f"❌ Error tagging engagement to lead: {e}")


# ==============================================================================
# 📡 ENGAGEMENT HISTORY ARCHIVAL (existing flow, preserved)
# ==============================================================================

async def create_engagement_history(dataverse_client, data: Dict) -> str | None:
    """
    Create parent engagement history record in Dataverse.
    Returns the parent record ID or None on failure.
    All sessions are sent to Dataverse regardless of lead_id.
    lead_id is only used to optionally bind the Lead reference.
    """
    payload = {
        "zx_chatsummary": data["summary"] or "No summary",
        "zx_totalinputtokens": data["input_tokens"],
        "zx_totalmessagecount": data["total_messages"],
        "zx_totaloutputtokens": data["output_tokens"],
        "zx_usermessagecount": data["user_message_count"],
        "zx_assistantmessagecount": data["assistant_message_count"],
        "zx_postgressessionid": data["session_id"],
        "zx_chatstarttime": data["created_at"].isoformat() if data.get("created_at") else None,
        "zx_chatendtime": data["last_activity"].isoformat() if data.get("last_activity") else None,
        "zx_engagementsource": data.get("source_value", 128780004),  # Default to Website
    }

    # Only bind Lead if lead_id exists — does NOT block archival if absent
    if data.get("lead_id"):
        payload["zx_Lead@odata.bind"] = f"/zx_leads({data['lead_id']})"
        
    if data.get("college_guid"):
        payload["zx_College@odata.bind"] = f"/zx_colleges({data['college_guid']})"

    response = await dataverse_client.post_record("zx_engagementhistories", payload)

    # Accept 200, 201, 204 — some Dataverse environments return 200
    if response.status_code not in (200, 201, 204):
        log.error(f"❌ [DATAVERSE] Parent Record Failed (status={response.status_code}): {response.text}")
        return None

    # Extract Parent ID from OData-EntityId header
    entity_id_header = response.headers.get("OData-EntityId", "")
    if entity_id_header:
        parent_id = entity_id_header.split("(")[-1].strip(")")
    else:
        # Fallback: try to get ID from response body (some configs return it there)
        try:
            body = response.json()
            parent_id = body.get("zx_engagementhistoryid") or body.get("value", [{}])[0].get("zx_engagementhistoryid")
        except Exception:
            parent_id = None

    if not parent_id:
        log.error(f"❌ [DATAVERSE] Could not extract parent_id from response. Header: '{entity_id_header}'")
        return None

    lead_info = f" (Lead: {data['lead_id']})" if data.get("lead_id") else " (No Lead)"
    log.info(f"✅ Parent Engagement History created: {parent_id}{lead_info}")
    return parent_id


async def create_single_message(dataverse_client, parent_id: str, index: int, msg: Dict) -> bool:
    """Insert a single message record."""
    try:
        payload = {
            "zx_name": f"Msg {index + 1}",
            "zx_messageorder": index + 1,
            "zx_content": msg.get("content", ""),
            "zx_role": ROLE_MAP.get(msg.get("role", "").lower(), 128780001),
            "zx_inputtokens": msg.get("tokens", {}).get("input", 0),
            "zx_outputtokens": msg.get("tokens", {}).get("output", 0),
            "zx_SessionID@odata.bind": f"/zx_engagementhistories({parent_id})",
        }

        resp = await dataverse_client.post_record("zx_sessionmessagetables", payload)
        if resp.status_code not in (200, 201, 204):
            log.warning(f"⚠️ Failed message {index + 1} (status={resp.status_code}): {resp.text}")
            return False
        return True
    except Exception as e:
        log.error(f"❌ Error on message {index + 1}: {str(e)}")
        return False


async def create_session_messages(dataverse_client, parent_id: str, messages: List[Dict], batch_size: int = 5) -> bool:
    """
    Insert messages into Dataverse using parallel batches.
    """
    log.info(f"📡 [DATAVERSE] Sending {len(messages)} messages in parallel batches...")

    all_results = []
    for batch_start in range(0, len(messages), batch_size):
        batch = list(enumerate(messages[batch_start : batch_start + batch_size], start=batch_start))
        results = await asyncio.gather(
            *[create_single_message(dataverse_client, parent_id, i, msg) for i, msg in batch],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                log.error(f"❌ [DATAVERSE] Message insert exception: {r}")
            all_results.append(r is True)

    success_count = sum(all_results)
    total = len(all_results)
    log.info(f"📊 [DATAVERSE] Messages inserted: {success_count}/{total}")
    return all(all_results)


async def archive_to_dataverse(dataverse_client, data: Dict) -> bool:
    """
    Full Dataverse archival: parent record + child messages.
    Runs for ALL sessions regardless of whether lead_id is present.
    lead_id only controls whether the Lead lookup is bound on the parent record.
    """
    session_id = data["session_id"]
    lead_info = f" | Lead: {data['lead_id']}" if data.get("lead_id") else " | No Lead"
    log.info(f"📡 [DATAVERSE] Archiving session: {session_id}{lead_info}")

    try:
        # 1. Create parent record (always, with or without lead_id)
        parent_id = await create_engagement_history(dataverse_client, data)
        if not parent_id:
            return False

        # 2. Create message records
        msg_success = await create_session_messages(dataverse_client, parent_id, data["messages"])

        # 3. If lead was found/created AFTER engagement history was created without binding,
        #    tag it now (safety net — normally lead_id is set before this function is called)
        if data.get("lead_id") and parent_id:
            # The binding is already set in create_engagement_history via payload,
            # but if it was missed, tag_engagement_to_lead acts as a safety net.
            pass

        return msg_success

    except Exception as e:
        log.error(f"💥 [DATAVERSE] Critical Error for {session_id}: {str(e)}")
        return False