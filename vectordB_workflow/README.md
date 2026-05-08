# VectorDB Workflow — Document Ingestion API

A FastAPI service for ingesting documents (PDF, DOCX, PPTX, websites) into PostgreSQL with pgvector embeddings. Used to build and manage the chatbot's knowledge base.

---

## How to Run

```bash
cd vectordB_workflow
pip install -r requirements.txt
python server.py
# Runs on http://localhost:8002
```

---

## File Structure

```
vectordB_workflow/
├── server.py    # FastAPI app — all routes, document processing, Azure Blob ops
├── .env         # Environment variables
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (tests DB connection) |
| `POST` | `/insert` | Insert document from base64 or website URL |
| `POST` | `/insert-from-blob` | Insert document from Azure Blob Storage |
| `POST` | `/retrieve` | Vector similarity search |
| `POST` | `/blob/upload-sas` | Generate SAS token for blob upload |
| `POST` | `/blob/read-sas` | Generate SAS token for blob read |
| `DELETE` | `/document/{id}` | Delete document from DB + Azure Blob |

---

## How Document Ingestion Works

### `/insert` (Base64 or Website)

```
1. Receive base64-encoded file or website URL
2. Extract text (in-memory, no temp files):
   - PDF → pypdf
   - DOCX → docx2txt
   - PPTX → python-pptx
   - Website → LangChain WebBaseLoader
3. Split text into chunks (default: 500 chars, 50 overlap)
4. Embed all chunks using Azure OpenAI (batched)
5. Insert into PostgreSQL education_vector_documents table
6. Return job_id and chunk count
```

### `/insert-from-blob` (Azure Blob)

```
1. Download file from Azure Blob Storage
2. Extract text → Chunk → Embed (same as above)
3. Transactional upsert: DELETE old chunks → INSERT new chunks
4. Supports document_id for deduplication
```

### `/retrieve` (Vector Search)

```
1. Embed search query
2. Vector similarity search using cosine distance (pgvector <=>)
3. Filter by source, trial_id, document_type
4. Return documents with similarity scores
```

---

## Azure Blob Storage

The API manages file storage in Azure Blob:

- **Upload SAS:** Generates 15-minute write tokens for client-side uploads
- **Read SAS:** Generates 15-minute read tokens for file access
- **CORS:** Auto-configures Azure Storage CORS rules on startup

---

## Database Table

Documents are stored in `education_vector_documents`:

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `document_name` | TEXT | File name |
| `document_url` | TEXT | Blob path or website URL |
| `embedding` | VECTOR(1536) | Azure OpenAI embedding |
| `content` | TEXT | Chunk text content |
| `chunk_index` | INTEGER | Position in document |
| `source` | ENUM | `Product-AI` or `Zox-edu-ai` |
| `trial_id` | UUID | College trial reference (nullable) |
| `document_id` | TEXT | Deduplication identifier |
| `document_type` | ENUM | `pdf`, `docx`, `pptx`, `website` |

---

## Environment Variables

```env
# Azure Blob Storage
AZURE_STORAGE_ACCOUNT=...
AZURE_STORAGE_KEY=...
AZURE_CONTAINER=...

# Azure OpenAI (Embeddings)
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_INSTANCE_NAME=https://...openai.azure.com
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=...
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AZURE_OPENAI_API_VERSION=2024-02-01

# PostgreSQL
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_DATABASE=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...

# Optional
CHUNK_SIZE=500
CHUNK_OVERLAP=50
MAX_FILE_SIZE_MB=20
EMBEDDING_BATCH_SIZE=100
```
