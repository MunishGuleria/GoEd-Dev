-- ================================================================
--  EDUCATION CUSTOM CHATBOT — COMPLETE DATABASE SCHEMA
--  Last Updated: 2026-03-02
-- ================================================================

-- ==================== PREREQUISITES ====================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ==================== ENUM TYPES ====================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_type_enum') THEN
        CREATE TYPE public.document_type_enum AS ENUM ('website', 'pdf', 'docx', 'ppt');
    END IF;
END
$$;

CREATE TYPE source_enum AS ENUM ('Product-AI', 'Zox-edu-ai');

DO $$ BEGIN
    CREATE TYPE trial_type_enum AS ENUM ('instant', '15days_sample', '15days_full');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ==================== SHARED TRIGGER FUNCTION ====================

CREATE OR REPLACE FUNCTION public.update_timestamp_ist()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_on = now() AT TIME ZONE 'Asia/Kolkata';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ================================================================
--  SECTION 1: PROMPTS
-- ================================================================

CREATE TABLE IF NOT EXISTS public.prompts (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    prompt_id TEXT COLLATE pg_catalog."default" NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    prompt_text TEXT COLLATE pg_catalog."default" NOT NULL,
    temperature NUMERIC(3,2),
    status TEXT COLLATE pg_catalog."default" DEFAULT 'ACTIVE'::text,
    created_by TEXT COLLATE pg_catalog."default" DEFAULT CURRENT_USER,
    last_updated_by TEXT COLLATE pg_catalog."default" DEFAULT CURRENT_USER,
    use_case TEXT COLLATE pg_catalog."default",
    created_on TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    updated_on TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),

    CONSTRAINT prompts_pkey PRIMARY KEY (prompt_id, version),
    CONSTRAINT prompts_temperature_check CHECK (temperature >= 0::numeric AND temperature <= 2::numeric)
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.prompts OWNER to n8npostgres;

CREATE INDEX IF NOT EXISTS idx_prompts_id_version
ON public.prompts USING btree (prompt_id COLLATE pg_catalog."default" ASC NULLS LAST, version DESC NULLS LAST);

DROP TRIGGER IF EXISTS update_prompts_timestamp_ist ON public.prompts;
CREATE TRIGGER update_prompts_timestamp_ist
BEFORE UPDATE ON public.prompts
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_ist();


-- ================================================================
--  SECTION 2: EDUCATION VECTOR DOCUMENTS
-- ================================================================

CREATE TABLE IF NOT EXISTS public.education_vector_documents (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    document_name TEXT COLLATE pg_catalog."default",
    document_url TEXT COLLATE pg_catalog."default",
    embedding VECTOR(1536),
    job_id UUID,
    document_type document_type_enum NOT NULL,
    chunk_index INTEGER,
    source source_enum NOT NULL DEFAULT 'Zox-edu-ai'::source_enum,
    trial_id UUID REFERENCES public.trial_users(id) ON DELETE CASCADE,
    created_on TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    updated_on TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    content TEXT COLLATE pg_catalog."default",

    CONSTRAINT education_vector_documents_pkey PRIMARY KEY (id),
    CONSTRAINT check_doc_name_logic CHECK (
        document_type = 'website'::document_type_enum
        OR (document_name IS NOT NULL AND document_name <> ''::text)
    )
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.education_vector_documents OWNER to n8npostgres;

CREATE INDEX IF NOT EXISTS idx_education_docs_embedding
ON public.education_vector_documents USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_education_docs_source
ON public.education_vector_documents(source);

DROP TRIGGER IF EXISTS update_education_docs_timestamp_ist ON public.education_vector_documents;
CREATE TRIGGER update_education_docs_timestamp_ist
BEFORE UPDATE ON public.education_vector_documents
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_ist();


-- ================================================================
--  SECTION 3: DEMO USERS (TRIAL SYSTEM)
-- ================================================================

CREATE TABLE IF NOT EXISTS public.demo_users (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    email character varying(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    created_on TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'),
    is_active boolean DEFAULT true,
    marketing_optin boolean DEFAULT false,

    CONSTRAINT demo_users_pkey PRIMARY KEY (id)
);


-- ================================================================
--  SECTION 4: TRIAL USERS
-- ================================================================

CREATE TABLE IF NOT EXISTS public.trial_users (
    id               UUID            NOT NULL DEFAULT uuid_generate_v4(),
    user_id          UUID            NOT NULL REFERENCES public.demo_users(id) ON DELETE CASCADE,
    trial_type       trial_type_enum NOT NULL,
    created_on       TIMESTAMPTZ     DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'),
    expires_at       TIMESTAMPTZ     NOT NULL,

    -- Social Channels
    insta_opt_in     BOOLEAN DEFAULT FALSE,
    insta_id         TEXT,
    fb_opt_in        BOOLEAN DEFAULT FALSE,
    fb_id            TEXT,
    whatsapp_opt_in  BOOLEAN DEFAULT FALSE,
    whatsapp_id      TEXT,
    website_opt_in   BOOLEAN DEFAULT FALSE,

    -- Dynamic prompt templating metadata (college name, email, phone, etc.)
    metadata         JSONB   DEFAULT '{}'::jsonb,

    -- Message quota (trial limit enforcement)
    message_limit    INTEGER NOT NULL DEFAULT 2500,
    messages_used    INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT trial_users_pkey         PRIMARY KEY (id),
    CONSTRAINT trial_users_user_id_key  UNIQUE (user_id)
);


-- ================================================================
--  SECTION 5: FEEDBACK
-- ================================================================

CREATE TABLE IF NOT EXISTS public.feedback (
    id         UUID     NOT NULL DEFAULT uuid_generate_v4(),
    user_id    UUID     NOT NULL REFERENCES public.demo_users(id) ON DELETE CASCADE,
    rating     SMALLINT CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    created_on TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'),

    CONSTRAINT feedback_pkey PRIMARY KEY (id)
);


-- ================================================================
--  SECTION 6: SESSIONS  (with trial_user lookup)
-- ================================================================

CREATE TABLE IF NOT EXISTS public.sessions (
    session_id TEXT COLLATE pg_catalog."default" NOT NULL,
    session_started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_on TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    updated_on TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    summary TEXT COLLATE pg_catalog."default",
    user_message_count INTEGER NOT NULL DEFAULT 0,
    total_message_count INTEGER NOT NULL DEFAULT 0,
    assistant_message_count INTEGER GENERATED ALWAYS AS (total_message_count - user_message_count) STORED,
    total_input_tokens BIGINT NOT NULL DEFAULT 0,
    total_output_tokens BIGINT NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    source TEXT COLLATE pg_catalog."default",
    trial_user_id UUID,
    trial_type trial_type_enum,

    CONSTRAINT sessions_pkey PRIMARY KEY (session_id),
    CONSTRAINT sessions_user_count_check CHECK (user_message_count >= 0),
    CONSTRAINT sessions_total_count_check CHECK (total_message_count >= 0),
    CONSTRAINT sessions_tokens_check CHECK (total_input_tokens >= 0 AND total_output_tokens >= 0),
    CONSTRAINT fk_sessions_trial_user FOREIGN KEY (trial_user_id) REFERENCES public.trial_users(id) ON DELETE SET NULL
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.sessions OWNER to n8npostgres;

CREATE INDEX IF NOT EXISTS idx_sessions_session_started_at
ON public.sessions USING btree (session_started_at ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_sessions_last_activity
ON public.sessions USING btree (last_activity_at ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_sessions_created_on
ON public.sessions USING btree (created_on ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_sessions_metadata_gin
ON public.sessions USING gin (metadata);

CREATE INDEX IF NOT EXISTS idx_sessions_trial_user_id
ON public.sessions USING btree (trial_user_id);

DROP TRIGGER IF EXISTS update_session_timestamp_ist ON public.sessions;
CREATE TRIGGER update_session_timestamp_ist
BEFORE UPDATE ON public.sessions
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_ist();


-- ================================================================
--  SECTION 7: SESSION MESSAGES
-- ================================================================

CREATE TABLE IF NOT EXISTS public.session_messages (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    session_id TEXT COLLATE pg_catalog."default" NOT NULL,
    message_order INTEGER NOT NULL,
    role TEXT COLLATE pg_catalog."default" NOT NULL,
    content TEXT COLLATE pg_catalog."default" NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    message_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    created_on TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    updated_on TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
    message_metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT session_messages_pkey PRIMARY KEY (id),
    CONSTRAINT session_messages_unique_order UNIQUE (session_id, message_order),
    CONSTRAINT session_messages_role_check CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    CONSTRAINT session_messages_order_check CHECK (message_order >= 0),
    CONSTRAINT session_messages_tokens_check CHECK (input_tokens >= 0 AND output_tokens >= 0),
    CONSTRAINT fk_session_messages_session FOREIGN KEY (session_id) REFERENCES public.sessions(session_id) ON DELETE CASCADE
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.session_messages OWNER to n8npostgres;

CREATE INDEX IF NOT EXISTS idx_session_messages_session_order
ON public.session_messages USING btree (session_id COLLATE pg_catalog."default" ASC NULLS LAST, message_order ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_session_messages_role
ON public.session_messages USING btree (role COLLATE pg_catalog."default" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_session_messages_timestamp
ON public.session_messages USING btree (message_timestamp ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_session_messages_content_fts
ON public.session_messages USING gin (to_tsvector('english'::regconfig, content));

CREATE INDEX IF NOT EXISTS idx_session_messages_metadata_gin
ON public.session_messages USING gin (message_metadata);

DROP TRIGGER IF EXISTS update_session_messages_timestamp_ist ON public.session_messages;
CREATE TRIGGER update_session_messages_timestamp_ist
BEFORE UPDATE ON public.session_messages
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_ist();


-- ================================================================
--  EXISTING DB MIGRATION: Add trial columns to sessions
--  (Run this ONLY if sessions table already exists without the columns)
-- ================================================================

-- ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS trial_user_id UUID;
-- ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS trial_type trial_type_enum;
-- ALTER TABLE public.sessions ADD CONSTRAINT fk_sessions_trial_user
--     FOREIGN KEY (trial_user_id) REFERENCES public.trial_users(id) ON DELETE SET NULL;
-- CREATE INDEX IF NOT EXISTS idx_sessions_trial_user_id
--     ON public.sessions USING btree (trial_user_id);

-- ================================================================
--  MIGRATION: Add trial_id to education_vector_documents
-- ================================================================

-- ALTER TABLE public.education_vector_documents ADD COLUMN IF NOT EXISTS trial_id UUID;
-- ALTER TABLE public.education_vector_documents ADD CONSTRAINT fk_vector_docs_trial_user
--     FOREIGN KEY (trial_id) REFERENCES public.trial_users(id) ON DELETE CASCADE;
-- CREATE INDEX IF NOT EXISTS idx_education_docs_trial_id
--     ON public.education_vector_documents USING btree (trial_id);


-- ================================================================
--  SECTION 8: COUNSELOR CRM SCHEMA TABLES
--  WhatsApp Counselor Extension - Vector-based schema discovery
-- ================================================================

-- Stores ONE row per Dataverse entity with the COMPLETE table
-- schema (all fields, types, option sets) as one vectorized chunk.
-- Used by resolve_schema tool for CRM schema discovery.
CREATE TABLE IF NOT EXISTS public.crm_schema_embeddings
(
    id                    uuid          NOT NULL DEFAULT uuid_generate_v4(),
    entity_logical_name   varchar(200)  NOT NULL,       -- e.g., 'zx_leads'
    entity_display_name   varchar(300),                  -- e.g., 'Leads'
    description_text      text          NOT NULL,        -- Complete schema as ONE chunk
    embedding             vector(1536)  NOT NULL,        -- Azure OpenAI embedding
    fields_count          integer,                       -- Number of fields in this entity
    is_activity           boolean       DEFAULT false,   -- True for activity entities
    synced_at             timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT crm_schema_embeddings_pkey PRIMARY KEY (id),
    CONSTRAINT crm_schema_embeddings_entity_key UNIQUE (entity_logical_name)
);

CREATE INDEX IF NOT EXISTS idx_crm_schema_vector
    ON public.crm_schema_embeddings
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_crm_schema_entity_name
    ON public.crm_schema_embeddings
    USING btree (entity_logical_name);


-- Pre-built OData query templates for common counselor questions.
-- Used by find_query_template tool for faster query generation.
CREATE TABLE IF NOT EXISTS public.crm_query_templates
(
    id                    uuid          NOT NULL DEFAULT uuid_generate_v4(),
    intent                varchar(200)  NOT NULL,        -- e.g., 'view_my_leads'
    question_template     text          NOT NULL,        -- e.g., 'Show me my assigned leads'
    odata_query           text          NOT NULL,        -- e.g., 'zx_leads?$filter=...'
    parameters            text,                          -- JSON: placeholder params description
    embedding             vector(1536)  NOT NULL,        -- Embedding of question_template
    created_at            timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT crm_query_templates_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_crm_query_templates_vector
    ON public.crm_query_templates
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_crm_query_templates_intent
    ON public.crm_query_templates
    USING btree (intent);


-- ================================================================
--  COMPLETION
-- ================================================================
DO $$
BEGIN
    RAISE NOTICE 'Schema creation completed successfully!';
END $$;
