# GoEd AI Chatbot — Multi-Channel Education Assistant

A production-grade, multi-channel AI chatbot for college admissions and education enquiries. Built with **FastAPI**, **LangChain/LangGraph**, and **Anthropic Claude**, it serves students across **Web**, **WhatsApp**, **Facebook**, and **Instagram**.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│   chatbot-widget.min.js (embedded on client websites)        │
└───────────────────────┬──────────────────────────────────────┘
                        │ HTTPS (SSE streaming)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                     CHATBOT (FastAPI)                         │
│   main.py → agent.py → LLM (Claude / GPT)                   │
│   Channels: Web, WhatsApp, Facebook, Instagram               │
│   Session state: Redis                                       │
└──────┬─────────────────────┬─────────────────┬───────────────┘
       │ SSE/MCP             │ Redis            │ Microsoft Graph
       ▼                     ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌────────────────┐
│  MCP SERVER  │   │    REDIS     │   │  OneDrive/Excel│
│  (FastMCP)   │   │  (Sessions)  │   │  (Form Logs)   │
│  Tools +     │   └──────────────┘   └────────────────┘
│  Knowledge   │
│  Base        │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│              EXTERNAL SERVICES                                │
│  ┌──────────┐  ┌────────────┐  ┌─────────────┐              │
│  │PostgreSQL│  │ Dataverse  │  │ Azure OpenAI│              │
│  │(pgvector)│  │ (CRM)      │  │ (Embeddings)│              │
│  └──────────┘  └────────────┘  └─────────────┘              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              BACKGROUND WORKERS                               │
│  ┌─────────────────┐   ┌────────────────────┐                │
│  │ data_sync_worker │   │ vectorDB_workflow  │                │
│  │ (Archive Worker) │   │ (Document API)     │                │
│  └─────────────────┘   └────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
```

---

## Module Map

| Module | Port | Purpose |
|---|---|---|
| [`chatbot/`](./chatbot/README.md) | 8000 | Main API — chat streaming, webhooks, form submissions |
| [`mcp_server/`](./mcp_server/README.md) | 8001 | MCP tools — knowledge base, leads, email, CRM |
| [`frontend/`](./frontend/README.md) | — | Embeddable chat widget (JS bundle) |
| [`data_sync_workflow/`](./data_sync_workflow/README.md) | — | Background worker — session archival, lead creation |
| [`vectordB_workflow/`](./vectordB_workflow/README.md) | 8002 | Document ingestion API (PDF/DOCX → vectors) |
| [`encryption/`](./encryption/README.md) | 8003 | Password-based message encryption utility |
| [`database/`](./database/README.md) | — | PostgreSQL schema definitions |
| [`k8s/`](./k8s/README.md) | — | Kubernetes deployment manifests |

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend build)
- Redis (Azure Cache for Redis or local)
- PostgreSQL with `pgvector` extension
- Azure AD app registration (for Dataverse + OneDrive)

### 1. Clone & Install

```bash
git clone <repo-url>
cd langchain-mcp-chatbot

# Install Python dependencies for each module
pip install -r chatbot/requirements.txt
pip install -r mcp_server/requirements.txt
pip install -r data_sync_workflow/requirements.txt
```

### 2. Environment Setup

Each module has its own `.env` file. Use `k8s/secret.yaml.template` as a reference for all required variables.

**Key variables (shared across modules):**

| Variable | Description |
|---|---|
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` | Redis connection |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL |
| `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` | Azure AD (Dataverse auth) |
| `DATAVERSE_BASE_URL` | Dataverse OData endpoint |
| `ANTHROPIC_API_KEY` | Claude LLM (chatbot) |
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_INSTANCE_NAME` | Azure OpenAI (embeddings + archive analysis) |
| `GRAPH_TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET` | Microsoft Graph (OneDrive/Excel) |
| `TRIAL_ENABLED` | `true` or `false` — enables trial user validation |

### 3. Start Services

```bash
# Terminal 1: MCP Server (must start first)
cd mcp_server && python server.py

# Terminal 2: Chatbot API
cd chatbot && python main.py

# Terminal 3: Archive Worker (background)
cd data_sync_workflow && python archive_worker.py

# Terminal 4: VectorDB API (optional, for document management)
cd vectordB_workflow && python server.py
```

### 4. Build Frontend Widget

```bash
cd frontend
node build.js
# Output: build/chatbot-widget.min.js
```

---

## Data Flow

### Chat Message Flow

```
User types message
  → Frontend sends POST /chat (SSE stream)
  → main.py validates trial user (if enabled)
  → agent.py loads prompt from MCP, injects context via middleware
  → LLM processes with tools (knowledge base, lead check, etc.)
  → Response streamed back via SSE
  → Messages stored in Redis (messages:list:{session_id})
```

### Session Archival Flow

```
User goes inactive (30 min for web, daily 3AM for social)
  → archive_worker.py scans Redis for inactive sessions
  → AI analysis (GPT-4o-mini) extracts user details + summary
  → Lead created/updated in Dataverse (CRM)
  → Session + messages archived to PostgreSQL
  → Redis keys cleaned up
  → Brochure email sent (if email was collected)
```

---

## Key Design Decisions

1. **Middleware-based Context Injection** — `InjectRedisContext` middleware dynamically injects user profiles, lead data, and college info into the system prompt before every LLM call. This enables prompt caching (Anthropic) and reduces latency.

2. **Channel-specific Tool Sets** — Each channel (web, WhatsApp, Instagram, Facebook) has its own set of tools and prompt ID defined in `channel_config.py`. Web users get streaming; social channels get complete responses.

3. **3-Tier Token Caching** — Dataverse auth tokens are cached in: Memory → Redis → Azure AD. Shared across all services via common Redis keys (`dataverse:access_token`).

4. **Background Lead Creation** — Leads are NOT created during chat (removed from real-time tools). Instead, the archive worker's AI analysis extracts user details post-session and creates/updates leads automatically.

5. **Rolling Summary Pattern** — Every 5 user messages, an LLM generates a rolling summary stored in Redis. The agent sees `SUMMARY + recent messages` instead of the full history, keeping context windows small.

---

## Deployment

See [`k8s/README.md`](./k8s/README.md) for Kubernetes deployment instructions.

**Services in production:**
- Chatbot API → `chatbot-deployment.yaml`
- MCP Server → `mcp-server-deployment.yaml`
- Archive Worker → `data-sync-deployment.yaml`
- VectorDB API → `vectordb-workflow-deployment.yaml`
- Frontend Widget → `frontend-widget-deployment.yaml` (static file serving)

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `MCP connection refused` | Ensure MCP server is running on port 8001 before starting chatbot |
| `Redis connection timeout` | Check `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` and SSL settings |
| `Dataverse 401 Unauthorized` | Verify Azure AD credentials and `AZURE_SCOPE` |
| `Trial user not_found` | Check `TRIAL_ENABLED` env var and PostgreSQL `trial_users` table |
| `Widget not loading` | Rebuild with `node build.js` and check `env.js` API URL |
