# Database — PostgreSQL Schema

Contains the complete database schema for the chatbot ecosystem. Uses PostgreSQL with the `pgvector` extension for vector similarity search.

---

## How to Apply

```bash
psql -h <host> -U <user> -d <database> -f schema.sql
```

Or run sections individually in your PostgreSQL client.

---

## Prerequisites

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID generation
CREATE EXTENSION IF NOT EXISTS "vector";      -- pgvector for embeddings
```

---

## Tables Overview

### 1. `prompts`
Stores versioned system prompts for the chatbot.

| Column | Type | Description |
|---|---|---|
| `prompt_id` | TEXT | Identifier (e.g., "Prompt-6") |
| `version` | INTEGER | Version number (latest is used) |
| `prompt_text` | TEXT | Full prompt content |
| `temperature` | NUMERIC | LLM temperature setting |
| `status` | TEXT | ACTIVE or INACTIVE |

**Primary Key:** `(prompt_id, version)` — allows multiple versions per prompt.

---

### 2. `education_vector_documents`
Knowledge base documents with vector embeddings (1536 dimensions).

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `document_name` | TEXT | File name |
| `embedding` | VECTOR(1536) | Azure OpenAI embedding |
| `content` | TEXT | Chunk text |
| `source` | source_enum | `Product-AI` or `Zox-edu-ai` |
| `trial_id` | UUID | FK to `trial_users` (nullable) |
| `chunk_index` | INTEGER | Position within document |

**Index:** HNSW index on `embedding` for fast cosine similarity search.

---

### 3. `demo_users`
User accounts for the trial/demo system.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `email` | VARCHAR(255) | Unique email |
| `password_hash` | TEXT | Hashed password |
| `is_active` | BOOLEAN | Account status |

---

### 4. `trial_users`
Trial subscriptions linked to demo users.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key (= `trial_user_id`) |
| `user_id` | UUID | FK to `demo_users` |
| `trial_type` | trial_type_enum | `instant`, `15days_sample`, `15days_full` |
| `expires_at` | TIMESTAMPTZ | Trial expiration |
| `message_limit` | INTEGER | Max messages allowed |
| `messages_used` | INTEGER | Messages consumed |
| `metadata` | JSONB | College name, phone, branding, etc. |
| `insta_opt_in` | BOOLEAN | Instagram enabled |
| `insta_id` | TEXT | Instagram username |
| `whatsapp_opt_in` | BOOLEAN | WhatsApp enabled |
| `whatsapp_id` | TEXT | WhatsApp phone |
| `website_opt_in` | BOOLEAN | Website widget enabled |

---

### 5. `sessions`
Archived chat sessions.

| Column | Type | Description |
|---|---|---|
| `session_id` | TEXT | Primary key (e.g., `sess_abc123`) |
| `summary` | TEXT | AI-generated conversation summary |
| `user_message_count` | INTEGER | Number of user messages |
| `total_message_count` | INTEGER | Total messages (user + assistant) |
| `total_input_tokens` | BIGINT | Input tokens consumed |
| `total_output_tokens` | BIGINT | Output tokens consumed |
| `source` | TEXT | Channel (Website, WhatsApp, etc.) |
| `trial_user_id` | UUID | FK to `trial_users` |

---

### 6. `session_messages`
Individual messages within archived sessions.

| Column | Type | Description |
|---|---|---|
| `session_id` | TEXT | FK to `sessions` (CASCADE delete) |
| `message_order` | INTEGER | Position in conversation |
| `role` | TEXT | `user`, `assistant`, `system`, `tool` |
| `content` | TEXT | Message content |
| `input_tokens` | INTEGER | Tokens for this message |
| `output_tokens` | INTEGER | Tokens for this message |

---

### 7. `feedback`
User feedback on trial experience.

---

### 8. CRM Schema Tables (Counselor Extension)

| Table | Purpose |
|---|---|
| `crm_schema_embeddings` | Vectorized Dataverse entity schemas for AI schema discovery |
| `crm_query_templates` | Pre-built OData query templates with embeddings |

---

## Custom Types

```sql
-- Document types for knowledge base
CREATE TYPE document_type_enum AS ENUM ('website', 'pdf', 'docx', 'ppt');

-- Knowledge base sources
CREATE TYPE source_enum AS ENUM ('Product-AI', 'Zox-edu-ai');

-- Trial types
CREATE TYPE trial_type_enum AS ENUM ('instant', '15days_sample', '15days_full');
```

---

## Auto-Update Trigger

All tables use a shared trigger that auto-updates `updated_on` to IST on every UPDATE:

```sql
CREATE OR REPLACE FUNCTION public.update_timestamp_ist()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_on = now() AT TIME ZONE 'Asia/Kolkata';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```
