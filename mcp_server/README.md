# MCP Server — Tools & Knowledge Base

The Model Context Protocol (MCP) server provides the chatbot agent with tools for CRM operations, knowledge base search, email, and prompt retrieval. Built with **FastMCP**.

---

## How to Run

```bash
cd mcp_server
pip install -r requirements.txt
python server.py
# Runs on http://localhost:8001 (via FastMCP/SSE)
```

---

## File Structure

```
mcp_server/
├── server.py      # FastMCP app — all tools, prompts, and routes
├── client.py      # Connection clients (Postgres, Redis, Dataverse, Embeddings)
├── .env           # Environment variables
```

---

## Tools Provided

The chatbot agent calls these tools via MCP:

| Tool | Description | Used By |
|---|---|---|
| `get_knowledge_base` | Vector search in PostgreSQL (pgvector) — courses, fees, eligibility, etc. | All channels |
| `check_lead` | Search Dataverse for existing lead by phone/email | Web, Instagram, Facebook |
| `check_senderid` | Search Dataverse for lead by Instagram/Facebook sender_id | Instagram, Facebook |
| `check_whatsapp_lead` | Search Dataverse for lead by WhatsApp phone number | WhatsApp |
| `create_lead` | Create a new lead in Dataverse (WhatsApp users) | WhatsApp |
| `create_social_media_lead` | Create a new lead for Instagram/Facebook users | Instagram, Facebook |
| `update_lead` | Update existing lead fields in Dataverse | WhatsApp, Instagram, Facebook |
| `send_email` | Send admission brochure via SMTP with PDF attachment | Web (trial), Instagram, Facebook |
| `check_seat_availability` | Query Dataverse seat availability table | All channels |
| `get_courses_with_branches` | List all courses and their branches from Dataverse | All channels |
| `get_previous_chat_context` | Get engagement history for a lead from Dataverse | All channels |

### Prompts

| Prompt Function | Description |
|---|---|
| `get_prompt` | Retrieve versioned prompt text from PostgreSQL `prompts` table |

---

## How Tools Work

### Knowledge Base Search (`get_knowledge_base`)

```
1. Embed query using Azure OpenAI (text-embedding model)
2. Vector search in PostgreSQL (education_vector_documents table)
3. Filter by source ("Product-AI" or "Zox-edu-ai") or trial_id
4. Return top-N documents with similarity scores
```

### Lead Management

**Lead Lifecycle:**
```
User starts chat → check_lead / check_whatsapp_lead / check_senderid
  ├─ Found → lead_id stored in Redis, agent has context
  └─ Not Found → agent collects info, calls create_lead
       └─ Lead created in Dataverse, lead_id cached in Redis
```

**Lead Type Auto-Determination:**
```
LEAD (128780004):     10th > 50% AND 12th > 50% AND (Graduated > 50% OR Entrance > 75%)
SUSPECT (128780005):  Currently pursuing OR 12th appearing
ENQUIRY (128780003):  Default for all other cases
```

### Email Tool (`send_email`)

1. Looks up college brochure from Dataverse (file attachment on `zx_colleges`)
2. Downloads brochure PDF
3. Builds premium HTML email template with college branding
4. Sends via SMTP with brochure attached
5. College name is dynamically injected (not hardcoded)

---

## Connection Clients (client.py)

All clients are **singleton instances** initialized once:

| Client | Purpose |
|---|---|
| `embeddings` | Azure OpenAI embeddings (1536-dim vectors) |
| `postgres` | asyncpg connection pool (lazy init, max 5 connections) |
| `redis_client` | Redis for caching (lead_id, tokens, etc.) |
| `dataverse` | Dataverse OData client with 3-tier token caching |

### Dataverse Token Caching

```
Tier 1: In-memory (same process, fastest)
Tier 2: Redis (cross-pod, survives restarts)
Tier 3: Azure AD (fresh fetch, last resort)
```

Token is shared across all services via Redis keys: `dataverse:access_token`, `dataverse:token_expiry`.

---

## Health Check

```
GET /education/health
→ { "status": "healthy", "service": "education-mcp-server" }
```

Used by Kubernetes readiness/liveness probes.

---

## Environment Variables

```env
# PostgreSQL
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_DATABASE=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...

# Redis
REDIS_HOST=...
REDIS_PORT=6380
REDIS_PASSWORD=...

# Azure OpenAI (Embeddings)
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_INSTANCE_NAME=https://...openai.azure.com
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=...
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AZURE_OPENAI_API_VERSION=2024-02-01

# Dataverse
DATAVERSE_BASE_URL=https://...dynamics.com/api/data/v9.2
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_SCOPE=https://...dynamics.com/.default

# SMTP (Email)
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
FROM_EMAIL=...

# WhatsApp (for send_whatsapp_document tool)
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
```
