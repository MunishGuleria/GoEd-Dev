"""
LLM AI Analysis for archive worker.
Replaces simple summarization with structured JSON extraction.
Uses GPT-4o-mini for token-efficient AI analysis of conversations.
"""

# ==================== OLD SUMMARIZER (COMMENTED OUT) ====================
# """
# LLM summarization for archive worker.
# Uses LangChain's abatch() for parallel async processing.
# """
# import logging
# from typing import Dict, List, Optional
# from langchain_core.messages import HumanMessage
# from postgres_ops import get_summary_prompt
#
# log = logging.getLogger("archive_worker")
#
#
# def _build_summary_prompt(session: Dict, template: str) -> Optional[str]:
#     """Build a summary prompt from session's user messages."""
#     user_messages = [
#         m for m in session.get("messages", [])
#         if m.get("role", "").lower() == "user"
#     ]
#
#     if not user_messages:
#         return None
#
#     messages_text = "\n".join([
#         f"{i+1}. {m['content']}"
#         for i, m in enumerate(user_messages)
#     ])
#
#     # Replace placeholder in template
#     return template.replace("{messages_text}", messages_text)
#
#
# async def batch_summarize_sessions(llm, postgres_client, sessions: List[Dict], max_concurrency: int = 5) -> List[Dict]:
#     """
#     Batch summarize sessions using LangChain's abatch().
#     """
#     # Per-cycle cache - resets each scheduler run
#     prompt_cache = {}
#     template = await get_summary_prompt(postgres_client, "Prompt-8", prompt_cache)
#
#     # Build index
#     todo = {}
#     for i, s in enumerate(sessions):
#         prompt = _build_summary_prompt(s, template)
#         if prompt:
#             todo[i] = prompt
#         else:
#             s["summary"] = "No user messages in session."
#
#     if not todo:
#         return sessions
#
#     # Batch LLM call
#     responses = await llm.abatch(
#         [[HumanMessage(content=p)] for p in todo.values()],
#         config={"max_concurrency": max_concurrency}
#     )
#
#     for (idx, _), resp in zip(todo.items(), responses):
#         sessions[idx]["summary"] = resp.content
#
#     log.info(f"🧠 Summarized: {len(todo)} sessions")
#     return sessions
# ==================== END OLD SUMMARIZER ====================


import json
import asyncio
import logging
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

log = logging.getLogger("archive_worker")

# ==================== STRICT SYSTEM PROMPT ====================
SYSTEM_PROMPT = """
You are a precise data extraction engine. You will receive a FULL CONVERSATION transcript
between a user and an AI chatbot about college admissions / education.

Your ONLY task is to produce a strict JSON output with a conversation summary and extracted user details.

### **CRITICAL RULES**
1. **Extract strictly what was explicitly stated.** Do not invent data. Do not guess.
2. **If a field was NEVER mentioned, leave it as "".**
3. **Phone numbers must be exactly 10 digits** (Indian mobile). Ignore if not valid.
4. **Email must look like a valid email address.** Ignore if not valid.
5. **Academic History:** Extract all educational milestones (10th, 12th, Graduation, etc.) into the `academic_history` list.
   - For each milestone, extract: `qualification`, `board`, `passing_year`, `percentage`, `school_college`, and `stream`.
   - Map `qualification` to: "10th / Secondary", "12th / Higher Secondary", "Diploma", "Undergraduate (UG)", "Postgraduate (PG)", "Doctorate (PhD)", or "Other".
   - Map `board` to: "CBSE", "ICSE", "State Board", "IB", "IGCSE", "NIOS", "University Board", or "Other". (Use "University Board" for any Degree/Graduation college board).
    - `stream` should be extracted for 12th and Graduation and mapped to one of: "Science", "Commerce", "Arts / Humanities", "Engineering", "Medical", "Management", "Computer Applications", or "Other".
      * Mapping Knowledge (STRICT): 
        - "Engineering": **ANY** BTech or BE degree (e.g., BTech CSE, BTech Mechanical, BE IT, Computer Science Engineering). 
        - "Computer Applications": BCA, MCA, BSc IT, BSc Computer Science (non-engineering degrees).
        - "Management": BBA, MBA, BMS, PGDM.
        - "Science": PCMB, PCM, Non-Medical (school level).
        - "Medical": PCB, MBBS, BDS, Nursing.
        - "Commerce": BCom, MCom, CA, Accounts.
        - "Arts / Humanities": BA, MA, Fine Arts.
   - `school_college` should be the full name of the institution.
   - `passing_year` should be the year of completion or expected completion.
   - `percentage` should be a numerical value (0-100). 
     **IMPORTANT:** If the user mentions a CGPA (e.g., "8.66 CGPA"), convert it to percentage by multiplying by 10 (e.g., 8.66 * 10 = 86.6).
6. **Summary Style:** Professional, high-level, 2-4 sentences covering the conversation.
   Always end with a one-line summary of the very last interaction.
7. **Entrance Exams:** Extract any competitive or entrance exams mentioned (e.g., CAT, MAT, XAT, SAT, GRE, GMAT, JEE, etc.) into the `entrance_exams` list.
   - For each exam, extract: `exam_name` (exact name as mentioned), `score` (numerical), `percentile` (numerical), `exam_year` (year of exam), and `appeared` (boolean - true if already taken, false if planning to take/appearing).

### **LEAD TYPE DETERMINATION**
Based on conversation and extracted details, determine lead_type:
- "Enquiry": User is NOT eligible for the desired course (low scores or wrong background).
- "Lead": User IS eligible (Meets marks criteria: >50% in 10th/12th AND Graduated/Entrance Score >75%).
- "Suspect/Prospect": User has shared name/number and is interested, but hasn't shared full academic profile yet.
- "Working Professional": User mentions they are currently employed or have significant job experience.
- "Student": Default if they are a student and don't fit the above.

### **LEAD STATUS DETERMINATION**
Determine lead_status:
- "Suspect": Default status for all new interactions.
- "Prospect": If the user shows specific interest in courses, fees, scholarships, or admission process.

### **PRIORITY DETERMINATION**
- "High": Excellent scores (90%+), top entrance ranks, clear goals.
- "Medium": Good scores (70-89%), decent entrance results.
- "Low": Average/below scores (<70%), unclear background.

### **LEAD SCORE CRITERIA (1-5 integer, MINIMUM IS 1)**
Evaluate the lead like a professional admissions officer using these 4 dimensions: Academics, Intent, Profile Completeness, and Course Fit.

- **5 (Hot Lead)**: 
    * **Academics**: Excellent (>85% in 10th & 12th).
    * **Intent**: High. Requested campus visit, asked about scholarships/deadlines, or explicitly mentioned immediate admission.
    * **Profile**: Complete. Shared name, 10-digit phone, and valid email.
- **4 (Warm Lead)**: 
    * **Academics**: Good (>70% in 10th & 12th).
    * **Intent**: Clear interest in specific courses, fees, or placements.
    * **Profile**: Mostly complete (shared at least phone and name).
- **3 (Potential Lead)**: 
    * **Academics**: Average (50-70%) or scores not fully mentioned but background matches course.
    * **Intent**: Basic enquiry about generic topics.
    * **Profile**: Shared contact info but limited academic details.
- **2 (Cold Lead / Pursuing)**: 
    * **Academics**: Low scores (<50%) OR currently in 11th/12th (not yet eligible for immediate degree).
    * **Intent**: Browsing only, very short responses.
    * **Profile**: Missing email or specific course interest.
- **1 (Invalid / Disengaged)**: 
    * **Academics**: Clearly ineligible.
    * **Intent**: Wrong number, greetings only, or refused to share details.
    * **Profile**: No contact info or invalid details provided.

*   **MANDATORY RULE**: If the user has NOT provided BOTH a **name** and at least one contact method (**phone number** or **email**), the `lead_score` **MUST be 1**, regardless of how good their academics or intent are. A lead is only created/updated if we have a name and contact details.

*IMPORTANT: Always return an integer between 1 and 5. Default to 1 for junk/test chats or missing contact info.*

### **OUTPUT FORMAT (STRICT JSON)**

```json
{
  "conversation_summary": "High-level description of topics discussed. Last sentence must summarize the final exchange.",

  "user_details": {
    "name": "Full Name as provided",
    "firstname": "First Name",
    "lastname": "Last Name",
    "phone": "10-digit mobile number",
    "email": "Email address",
    "city": "City if mentioned",
    "highest_qualification": "12th/Diploma/Graduation/Post Graduation/Other",
    "interested_course": "Course name if mentioned",
    "campus_visit_requested": "Boolean (true/false) - Did the user agree to or request a campus visit?",
    "visit_date": "YYYY-MM-DD format if mentioned, else empty string",
    "visit_time": "HH:MM AM/PM format if mentioned, else empty string (e.g. 10:00 AM, 02:30 PM)",
    "visit_details": "Details about the visit: Who is coming (e.g. with parents), purpose, specifically mentioned interests for the visit, etc.",
    "is_rescheduling": "Boolean (true/false) - Is this a request to change/reschedule an existing visit?",
    "lead_score": "Integer 1-5",
    "lead_type": "Enquiry/Lead/Suspect-Prospect/Working Professional/Student",
    "lead_status": "Suspect/Prospect",
    "priority": "High/Medium/Low",
    "academic_history": [
      {
        "qualification": "10th / Secondary",
        "board": "CBSE",
        "passing_year": "2018",
        "percentage": 85.5,
        "school_college": "Modern School",
        "stream": ""
      },
      {
        "qualification": "12th / Higher Secondary",
        "board": "ICSE",
        "passing_year": "2020",
        "percentage": 92.0,
        "school_college": "Loyola College",
        "stream": "Science"
      }
    ],
    "entrance_exams": [
      {
        "exam_name": "CAT",
        "score": 185.5,
        "percentile": 98.2,
        "exam_year": 2023,
        "appeared": true
      }
    ]
  }
}
```

Return ONLY the JSON. No markdown, no explanation, no extra text.
"""


async def batch_analyze_sessions(llm_client, session_data_list: List[Dict], concurrency: int = 5):
    """
    Orchestrates concurrent LLM calls to analyze sessions.
    Analyzes multiple sessions in parallel using an LLM.
    """
    if not session_data_list:
        return

    semaphore = asyncio.Semaphore(concurrency)

    async def analyze_single_session(data: dict):
        async with semaphore:
            sid = data.get("session_id")
            messages = data.get("messages", [])
            prev_context = data.get("previous_context", "")

            # Default values to prevent KeyErrors downstream
            data["ai_analysis"] = "{}"
            data["summary"] = "Summary not available."

            # Format conversation for LLM
            conversation_text = ""
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if isinstance(content, (dict, list)):
                    content = json.dumps(content)
                conversation_text += f"{role.upper()}: {content}\n"

            if not conversation_text.strip():
                return

            try:
                from utils import now_ist
                current_date_str = now_ist().strftime("%Y-%m-%d (%A)")
                
                # Add History Awareness and Date Context to the prompt
                user_prompt = f"TODAY'S DATE: {current_date_str}\n\nAnalyze this conversation:\n\n{conversation_text}"
                if prev_context:
                    user_prompt = (
                        f"TODAY'S DATE: {current_date_str}\n\n"
                        f"PREVIOUS CONTEXT (Existing Summary of this user's history):\n{prev_context}\n\n"
                        f"NEW CONVERSATION:\n{conversation_text}\n\n"
                        "TASK:\n"
                        "1. Analyze the NEW CONVERSATION.\n"
                        "2. Update the 'user_details' JSON. If a field was mentioned in PREVIOUS CONTEXT but NOT in the new conversation, "
                        "you MUST preserve the previous value so it isn't lost.\n"
                        "3. Update the 'conversation_summary'. You MUST combine the PREVIOUS CONTEXT with the new interaction. "
                        "Merge them into a single, professional, high-level summary that captures the full journey. "
                        "Keep it condensed (4-6 sentences total) so it remains within Dataverse length limits."
                    )

                # Call LLM with conversation
                response = await llm_client.ainvoke([
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt)
                ])

                analysis_str = response.content
                
                # Parse & Validate
                try:
                    # Clean up markdown if LLM adds it
                    clean_str = analysis_str.replace("```json", "").replace("```", "").strip()
                    parsed_json = json.loads(clean_str)
                    
                    # Store Results
                    data["ai_analysis"] = clean_str
                    
                    # Extract summary for Postgres compatibility
                    summary_text = parsed_json.get("conversation_summary", "Summary not generated.")
                    
                    # Append extracted details to summary
                    user_details = parsed_json.get("user_details", {})
                    if user_details:
                        lines = []
                        for k, v in user_details.items():
                            if not v:
                                continue
                            if k == "academic_history" and isinstance(v, list):
                                lines.append("\n[Academic History]")
                                for i, entry in enumerate(v):
                                    entry_str = ", ".join([f"{ek}: {ev}" for ek, ev in entry.items() if ev])
                                    lines.append(f" {i+1}. {entry_str}")
                            else:
                                lines.append(f"{k}: {v}")
                        
                        details_str = "\n".join(lines)
                        if details_str:
                            summary_text += f"\n\n[Extracted Details]\n{details_str}"

                    data["summary"] = summary_text
                    
                    log.info(f"✅ AI Analysis complete for {sid}")

                except json.JSONDecodeError:
                    log.error(f"⚠️ JSON Parse failed for {sid}. Raw: {analysis_str[:200]}...")
                    data["ai_analysis"] = json.dumps({"error": "Invalid JSON"})
                    data["summary"] = "Analysis failed (Invalid JSON)."

            except Exception as e:
                log.error(f"❌ LLM Call failed for {sid}: {e}")
                data["ai_analysis"] = json.dumps({"error": str(e)})
                data["summary"] = "Analysis failed (LLM Error)."

    # Run all tasks concurrently
    log.info(f"🧠 Analyzing {len(session_data_list)} sessions (concurrency={concurrency})")
    await asyncio.gather(*[analyze_single_session(d) for d in session_data_list])
