# Data Sync Workflow — Archive Worker

A background worker that continuously monitors Redis for inactive chat sessions and archives them to PostgreSQL and Dataverse (CRM). Also handles AI-driven lead creation, academic history tracking, campus visit scheduling, and automated brochure emails.

---

## How to Run

```bash
cd data_sync_workflow
pip install -r requirements.txt
python archive_worker.py
# Runs continuously, scanning every 120 seconds
```

---

## File Structure

```
data_sync_workflow/
├── archive_worker.py    # Main orchestrator — session discovery, archival pipeline
├── connection.py        # Singleton clients (Redis, PostgreSQL, Dataverse, LLM)
├── postgres_ops.py      # PostgreSQL insertion (sessions + messages)
├── dataverse_ops.py     # Dataverse lead CRUD, engagement history, campus visits
├── llm_ops.py           # AI analysis — extracts user details from conversations
├── email_ops.py         # Automated brochure email dispatch
├── utils.py             # IST timezone helpers, datetime parsing
├── .env                 # Environment variables
```

---

## What It Does (Step by Step)

### 1. Find Inactive Sessions

```
Every 120 seconds:
  → Scan Redis for all last_activity:* keys
  → Web sessions: Inactive > 30 minutes → archive
  → Social sessions (WA/FB/IG): Archive on daily cron (3 AM IST)
```

### 2. Fetch Session Data from Redis

For each inactive session, fetch via pipeline:
- `messages:list:{sid}` — Full message history
- `summary:{sid}` — Rolling summary
- `lead_id:{sid}` — Associated lead (if any)
- `existing_lead_data:{sid}` — Cached lead profile
- `trial_user_id:{sid}` — Trial user UUID

### 3. AI Analysis (llm_ops.py)

Each session's conversation is sent to **GPT-4o-mini** with a strict extraction prompt:

```json
{
  "conversation_summary": "2-4 sentence summary",
  "user_details": {
    "name": "...",
    "phone": "...",
    "email": "...",
    "interested_course": "...",
    "lead_score": 1-5,
    "lead_type": "Enquiry/Lead/Suspect-Prospect",
    "academic_history": [...]
  }
}
```

**Concurrency:** Up to 5 sessions analyzed in parallel.

### 4. Lead Creation / Update (dataverse_ops.py)

```
Has phone or email?
  ├─ lead_id already in Redis → UPDATE existing lead
  ├─ No lead_id → Search Dataverse by name+phone/email
  │   ├─ Found → UPDATE
  │   └─ Not Found → CREATE new lead
  └─ No contact info but lead_id exists → UPDATE context only
```

**Anti-Blank Override:** When updating leads, the worker fetches current Dataverse values first. Fields are only updated if the new value is non-empty and better (e.g., scores only increase, emails don't get overwritten with blanks).

### 5. Archive to PostgreSQL (postgres_ops.py)

- Sessions inserted with UPSERT (`ON CONFLICT DO UPDATE`)
- Messages bulk-inserted using `COPY` (10-100x faster than individual inserts)
- Processed in chunks of 50 sessions per transaction

### 6. Archive to Dataverse

- Creates `zx_engagementhistory` record for each session
- Links to lead via `_zx_lead_value` lookup field
- Individual messages stored as `zx_sessionmessage` records

### 7. Cleanup Redis

After successful archival:
- Sets `archived:{sid}` key (2-hour TTL) for idempotency
- Deletes all session keys (messages, summary, counters, etc.)

### 8. Post-Archival Actions

- **Academic History:** If AI extracted academic records → creates `zx_leadacademichistory` entries in Dataverse
- **Campus Visit:** If user requested a visit → creates/updates a Dataverse `tasks` record
- **Brochure Email:** If email was collected → sends admission brochure via SMTP
- **Trial Message Flush:** Flushes `trial_msg_count` from Redis to PostgreSQL

---

## Scheduling

| Session Type | When Archived | Inactivity Threshold |
|---|---|---|
| **Web** (`sess_*`) | Continuously | 30 minutes |
| **WhatsApp** (`whatsapp:*`) | Daily at 3 AM IST | 10 minutes safety buffer |
| **Instagram** (`instagram:*`) | Daily at 3 AM IST | 10 minutes safety buffer |
| **Facebook** (`facebook:*`) | Daily at 3 AM IST | 10 minutes safety buffer |

Social sessions use a **cron-based schedule** (`SOCIAL_SYNC_CRON`) with idempotency checks to ensure single execution per cycle.

---

## Lead Score Rules

| Score | Criteria |
|---|---|
| **5 (Hot)** | Academics > 85%, requested visit, shared name + phone + email |
| **4 (Warm)** | Academics > 70%, specific interest, shared phone + name |
| **3 (Potential)** | Academics 50-70%, basic enquiry, shared contact |
| **2 (Cold)** | Low scores or pursuing 11th/12th, browsing only |
| **1 (Invalid)** | No name or contact info, greetings only, test messages |

**Mandatory Rule:** If user didn't provide BOTH a name AND a contact method (phone or email), score is forced to 1.

---

## Connection Clients (connection.py)

| Client | Type | Purpose |
|---|---|---|
| `RedisConnectionPool` | Singleton | Session data, caching, deduplication |
| `PostgresClient` | asyncpg pool (1-8 connections) | Session archival |
| `DataverseClient` | httpx + 3-tier token cache | CRM operations |
| `LLMClient` | Azure ChatOpenAI (GPT-4o-mini) | AI analysis |

---

## Graceful Shutdown

Handles `SIGINT` and `SIGTERM` signals. Completes current archival cycle before stopping.

---

## Environment Variables

```env
# Redis
REDIS_HOST=...
REDIS_PORT=6380
REDIS_PASSWORD=...

# PostgreSQL
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_DATABASE=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...

# Dataverse
DATAVERSE_BASE_URL=https://...dynamics.com/api/data/v9.2
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_SCOPE=https://...dynamics.com/.default

# Azure OpenAI (for AI analysis)
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_INSTANCE_NAME=https://...openai.azure.com
AZURE_OPENAI_API_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-01

# SMTP (for brochure emails)
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
FROM_EMAIL=...

# Worker Settings
SESSION_INACTIVITY_MINUTES=30
ARCHIVE_BATCH_SIZE=50
ARCHIVE_WORKER_INTERVAL_SECONDS=120
SOCIAL_SYNC_CRON=0 3 * * *
```
