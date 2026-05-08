# Chatbot Module — FastAPI Backend

The core application. Handles all chat interactions, webhook processing, session management, and form submissions.

---

## How to Run

```bash
cd chatbot
pip install -r requirements.txt
python main.py
# Runs on http://localhost:8000
```

**Requires:** MCP server running on port 8001 (see `../mcp_server/`).

---

## File Structure

```
chatbot/
├── main.py                  # FastAPI app — all routes and endpoints
├── agent.py                 # LLM agent logic — middleware, tool execution, streaming
├── state.py                 # AgentContext dataclass
├── onedrive_excel.py        # Microsoft Graph — append rows to OneDrive Excel files
├── client/
│   ├── config.py            # LLM client config (Anthropic Claude)
│   ├── base_connection.py   # MCP connection manager
│   ├── channel_config.py    # Per-channel tool sets and prompt IDs
│   ├── memory_manager.py    # Redis message storage + rolling summaries
│   ├── trial_validator.py   # Trial user validation (Redis → PostgreSQL)
│   ├── session_logger.py    # Logging utilities
│   ├── mcp_tools.py         # MCP tool wrapper
│   ├── dataverse_client.py  # Dataverse HTTP client
│   ├── whatsapp_connection.py   # WhatsApp webhook + message sending
│   ├── facebook_connection.py   # Facebook Messenger webhook
│   └── instagram_connection.py  # Instagram DM webhook
```

---

## Key Endpoints (main.py)

| Method | Path | Description |
|---|---|---|
| `POST` | `/init-session` | Initialize a new chat session. Validates trial user, fetches college metadata, loads base prompt from MCP. |
| `POST` | `/chat` | Main chat endpoint. Streams LLM response via SSE (Server-Sent Events). |
| `POST` | `/submit-form` | Submit form data (Broadcast, Webinar, Contact) → appends to OneDrive Excel. |
| `POST` | `/webhook/whatsapp` | WhatsApp incoming message webhook. |
| `GET`  | `/webhook/whatsapp` | WhatsApp webhook verification. |
| `POST` | `/webhook/instagram` | Instagram DM webhook. |
| `POST` | `/webhook/facebook` | Facebook Messenger webhook. |
| `GET`  | `/webhook/instagram` | Meta webhook verification (shared). |
| `GET`  | `/health` | Health check for Kubernetes probes. |

---

## How the Chat Flow Works

### Step 1: Session Init (`/init-session`)

```
Client sends: { session_id, trial_user_id? }
  1. If TRIAL_ENABLED → validate trial_user_id against PostgreSQL
  2. Fetch college metadata (courses, seats) from MCP + Dataverse
  3. Store trial info in Redis: trial_user_id:{sid}, trial_metadata:{sid}
  4. Return: { session_id, status, college_name, ... }
```

### Step 2: Chat Message (`/chat`)

```
Client sends: { session_id, message, channel }
  1. Load channel config → get prompt_id + tool list
  2. Store user message in Redis via RedisMessageManager
  3. Call agent.process_query():
     a. Fetch base prompt from MCP (via get_prompt)
     b. InjectRedisContext middleware injects:
        - User profile (name, phone from user_info:{sid})
        - Lead data (if lead_id:{sid} exists)
        - College course list + seat availability
     c. LLM processes with tools (knowledge base, check_lead, etc.)
     d. HandleToolErrors middleware catches and retries tool failures
  4. Stream response tokens via SSE
  5. Store assistant message in Redis
  6. If lead_id found by a tool → store in Redis for archive worker
```

### Step 3: Social Channel Webhooks

WhatsApp, Instagram, and Facebook messages follow the same pattern but with key differences:

- **Deduplication**: Every webhook checks `mid:{message_id}` in Redis to prevent processing Meta retries
- **Background Processing**: Replies use `asyncio.create_task()` to prevent webhook timeouts (Meta requires < 20s response)
- **User Info Storage**: Phone/name/sender_id stored in `user_info:{session_id}` Redis hash
- **Non-streaming**: Social channels use `response_format="complete"` (no SSE)

---

## Agent Architecture (agent.py)

The agent uses a **middleware pipeline** pattern:

```
                    ┌─────────────────────────┐
                    │     process_query()      │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  InjectRedisContext      │  ← Injects user profile,
                    │  (before_invoke)         │     lead data, courses
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  HandleToolErrors        │  ← Catches tool failures,
                    │  (after_invoke)          │     retries with error context
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  LLM (Claude 3.5)       │  ← Generates response
                    │  + MCP Tools            │     using injected context
                    └─────────────────────────┘
```

### InjectRedisContext Middleware

This is the most important middleware. It dynamically modifies the system prompt before each LLM call:

1. **Fetches user profile** from `user_info:{session_id}` Redis hash
2. **Fetches lead data** from `lead_id:{session_id}` → queries Dataverse if lead exists
3. **Injects college context** (courses, seats) from `trial_metadata:{session_id}`
4. **Appends all context** to the base prompt as structured XML blocks

This approach enables **Anthropic prompt caching** — the static base prompt is cached, and dynamic context is appended, reducing costs by ~90%.

### Channel Configuration

Each channel has different tools and prompts (defined in `client/channel_config.py`):

| Channel | Prompt | Tools | Response |
|---|---|---|---|
| `web` | Prompt-11 (trial) / Prompt-6 | knowledge_base, check_lead, seats | Streaming (SSE) |
| `whatsapp` | Prompt-3 | knowledge_base, check_whatsapp_lead, create_lead, update_lead, send_doc, seats | Complete |
| `instagram` | Prompt-7 | knowledge_base, check_senderid, check_lead, create_social_lead, update_lead, seats | Complete |
| `facebook` | Prompt-7 | Same as Instagram | Complete |

---

## Memory Management (memory_manager.py)

Uses a **rolling summary** pattern to keep LLM context windows small:

```
Messages 1-5 (USER):   Agent sees → raw messages only
                        After message 5: LLM generates summary
Messages 6-10 (USER):  Agent sees → SUMMARY + messages 6-10
                        After message 10: LLM updates summary
Messages 11+:          Agent sees → UPDATED SUMMARY + messages 11+
```

**Redis Keys per Session:**

| Key | Purpose |
|---|---|
| `messages:list:{sid}` | Full message history (JSON list) |
| `summary:{sid}` | Current rolling summary |
| `user_count:{sid}` | Number of user messages |
| `last_activity:{sid}` | Timestamp of last message |
| `lead_id:{sid}` | Dataverse lead ID (set by tools) |
| `existing_lead_data:{sid}` | Cached lead profile from check_lead |
| `trial_user_id:{sid}` | Trial user UUID |
| `trial_metadata:{sid}` | College metadata JSON |

---

## Trial Validation (trial_validator.py)

When `TRIAL_ENABLED=true`, every session is validated:

```
1. Check Redis cache: trial_lookup:{channel}:{identifier}
2. If miss → Query PostgreSQL: trial_users + demo_users
3. If found → Cache in Redis (2-day TTL)
4. Check: expired? limit_reached? valid?
5. If invalid → Return rejection message, block LLM call
```

**Message Counting:** Each user message increments `trial_msg_count:{trial_user_id}` in Redis. The archive worker flushes this to PostgreSQL periodically.

---

## Form Submission (onedrive_excel.py)

The `/submit-form` endpoint appends rows to OneDrive Excel files:

| Target | Excel File | Env Variable |
|---|---|---|
| `BROADCAST` | Broadcast signups | `BROADCAST_EXCEL_SHARE_LINK` |
| `AIWEBINAR` | Webinar registrations | `AIWEBINAR_EXCEL_SHARE_LINK` |
| `CONTACT` | Contact form | `CONTACT_EXCEL_SHARE_LINK` |

Uses Microsoft Graph API with OAuth2 client credentials. Auth tokens and drive info are cached to minimize API calls.

---

## Environment Variables

```env
# LLM
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-20250514

# MCP Server
MCP_SERVER_URL=http://localhost:8001

# Redis
REDIS_HOST=...
REDIS_PORT=6380
REDIS_PASSWORD=...

# PostgreSQL (for trial validation)
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_DATABASE=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...

# Microsoft Graph (OneDrive Excel)
GRAPH_TENANT_ID=...
CLIENT_ID=...
CLIENT_SECRET=...

# Meta Webhooks
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...
INSTAGRAM_VERIFY_TOKEN=...
INSTAGRAM_PAGE_ACCESS_TOKEN=...

# Trial System
TRIAL_ENABLED=true
```
