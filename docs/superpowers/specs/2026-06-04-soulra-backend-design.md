# Soulra Backend — Design Spec

**Date:** 2026-06-04
**Status:** Approved
**Stack:** Python 3.12 · FastAPI · LangGraph 1.x · LangChain · pgvector · OpenRouter · WebSocket

---

## 1. What we are building

A production-ready Python backend that powers the Soulra chat experience. The backend:

1. Accepts spiritual text documents (PDF, text, URL) and builds a searchable vector knowledge base using pgvector inside Postgres.
2. On each user conversation, runs a LangGraph **Corrective RAG (CRAG)** graph: retrieve passages from the knowledge base → grade relevance → rewrite query if needed → pause for a clarifying question (Soulra's signature UX moment) → retrieve again with full context → synthesize a structured response (3 tradition cards + action plan) streamed over WebSocket.
3. Persists all graph state, conversation metadata, and vector embeddings in a single Postgres instance running the `pgvector/pgvector:pg16` Docker image.
4. Uses OpenRouter as the sole external API — both LLM completions and embeddings flow through one key and one base URL, with zero vendor lock-in (model is a config string).

---

## 2. Architecture overview

```
Next.js frontend (TypeScript)
        │
        │  WebSocket  /ws/chat
        │  REST       /api/v1/*
        ▼
FastAPI backend (Python 3.12, async)
        │
        ├─ LangGraph CRAG graph ──► OpenRouter (chat completions)
        │       │                   anthropic/claude-opus-4-8  (synthesize node)
        │       │                   anthropic/claude-sonnet-4-6 (intake/grade/clarify)
        │
        ├─ PGVector retriever ───► OpenRouter (embeddings)
        │                          openai/text-embedding-3-small  (1536-dim)
        │
        └─ Postgres (pgvector/pgvector:pg16)
                ├── langchain_pg_embedding    (vectors + JSONB metadata)
                ├── langchain_pg_collection   (collection registry)
                ├── langgraph_checkpoints*    (graph state per conversation)
                ├── conversations             (session metadata)
                └── action_steps             (saved action plans)
```

> `*` Created automatically by `AsyncPostgresSaver` from `langgraph-checkpoint-postgres`.

---

## 3. API surface

### 3.1 REST — `/api/v1/`

#### Ingestion

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest/pdf` | Upload PDF file. Accepts `UploadFile` + form fields `tradition`, `author`, `source`, `era`. Returns `{job_id, status: "processing"}` immediately; ingestion runs as a background task. |
| `POST` | `/ingest/text` | Ingest raw text body with the same metadata fields. |
| `POST` | `/ingest/url` | Fetch URL content, parse to text, ingest. |
| `GET` | `/ingest/jobs/{job_id}` | Poll ingestion status. Returns `{status, chunks_created, tokens_used, error?}`. |

#### Knowledge base

| Method | Path | Description |
|---|---|---|
| `GET` | `/passages` | List passages. Query params: `tradition`, `author`, `era`, `limit`, `offset`. |
| `GET` | `/passages/{id}` | Single passage with full metadata. |
| `DELETE` | `/passages/{id}` | Remove from vector store. |
| `GET` | `/collections` | List named pgvector collections and document counts. |

#### Conversations

| Method | Path | Description |
|---|---|---|
| `GET` | `/conversations` | List conversations. Query params: `limit`, `offset`. |
| `GET` | `/conversations/{id}` | Conversation detail including tradition cards and action steps. |
| `DELETE` | `/conversations/{id}` | Delete conversation and its graph checkpoint. |

#### System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe. Returns `{status: "ok"}`. |
| `GET` | `/status` | Readiness: DB connectivity, passage count, embedding model reachability. |

### 3.2 WebSocket — `/ws/chat`

One socket per conversation. Bidirectional JSON messages.

**Client → Server**

```jsonc
// Start a new conversation
{"type": "start", "situation": "I keep saying yes to projects I don't want to do…"}

// Send chip selection after graph pauses at clarify node
{"type": "clarification", "choice": "Something inside me"}

// Follow-up message after synthesis completes
{"type": "followup", "text": "Can you say more about the Stoic view?"}
```

**Server → Client**

```jsonc
{"type": "status",           "node": "retrieve"}
{"type": "status",           "node": "grade_docs"}
{"type": "status",           "node": "clarify"}
{"type": "clarify",          "question": "Before I draw on the traditions…"}
{"type": "chips",            "options": ["The work", "The people", "Something inside me", "It's all three"]}
{"type": "status",           "node": "synthesize"}
{"type": "tradition_token",  "tradition": "Stoic", "token": "You always own "}
{"type": "tradition_done",   "tradition": "Stoic", "author": "Marcus Aurelius", "quote": "You always own the option…", "citation": "Meditations 6.13", "analysis": "…"}
{"type": "action_step",      "n": "01", "title": "Notice the moment of yes", "body": "…"}
{"type": "done"}
{"type": "error",            "message": "…", "code": "RETRIEVAL_FAILED"}
```

---

## 4. LangGraph CRAG graph

### State

```python
class SoulraState(TypedDict):
    situation: str
    tradition_hints: list[str]      # extracted by intake node
    query: str                      # current search query (may be rewritten)
    retrieved_docs: list[Document]
    grade_result: str               # "relevant" | "not_relevant"
    clarify_question: str
    clarify_chips: list[str]
    clarify_answer: str | None      # None = graph paused at interrupt
    refined_docs: list[Document]
    tradition_cards: list[dict]
    action_steps: list[dict]
    messages: Annotated[list, add_messages]
    rewrite_count: int              # guard against infinite rewrite loops (max 2)
```

### Nodes

| Node | Model | Responsibility |
|---|---|---|
| `intake` | `claude-sonnet-4-6` | Parse situation, extract tradition hints, form initial query |
| `retrieve` | — | pgvector similarity search, top-5 per tradition hint |
| `grade_docs` | `claude-sonnet-4-6` | Structured output: `relevant` or `not_relevant` per doc |
| `rewrite_query` | `claude-sonnet-4-6` | Rewrite query for better retrieval; increment `rewrite_count` |
| `clarify` | `claude-sonnet-4-6` | Generate pause question + 4 chip options; stream to client |
| `retrieve_refined` | — | pgvector search with situation + clarification answer |
| `synthesize` | `claude-opus-4-8` | Stream 3 tradition cards + 3-step action plan |

### Graph topology

```
START
  → intake
  → retrieve
  → grade_docs
      ├─ "not_relevant" AND rewrite_count < 2 → rewrite_query → retrieve
      └─ "relevant" OR rewrite_count >= 2 → clarify
  → [INTERRUPT before retrieve_refined]   ← user sends chip choice
  → retrieve_refined
  → synthesize
  → END
```

### Compilation

```python
graph = builder.compile(
    checkpointer=AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL),
    interrupt_before=["retrieve_refined"],
)
```

---

## 5. Ingestion pipeline

```
POST /ingest/pdf
    FastAPI UploadFile
        ↓ (background task, non-blocking)
    pdf_parser.py       → pypdf text extraction, page metadata preserved
        ↓
    chunker.py          → RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        ↓
    pipeline.py         → OpenRouter embeddings (openai/text-embedding-3-small)
                        → PGVector.aadd_documents(docs, collection_name="wisdom_passages")
                        → update ingestion job status in DB
```

Each chunk stored with JSONB metadata:

```json
{
  "tradition": "stoic",
  "author": "Marcus Aurelius",
  "source": "Meditations",
  "era": "ancient",
  "page": 42,
  "chunk_index": 3
}
```

---

## 6. LLM / embedding factory

```python
# services/llm/factory.py

def make_chat_llm(model: str, streaming: bool = True) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        streaming=streaming,
    )

def make_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,  # "openai/text-embedding-3-small"
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )
```

Config values drive every model choice. Swapping provider = changing `.env`.

---

## 7. Folder structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, router registration, middleware
│   ├── config.py                # pydantic-settings: DATABASE_URL, OPENROUTER_API_KEY,
│   │                            #   SMART_MODEL, FAST_MODEL, EMBEDDING_MODEL, MAX_UPLOAD_MB
│   ├── database.py              # async engine, AsyncSession factory, Base
│   ├── dependencies.py          # get_db, get_vectorstore, get_smart_llm, get_fast_llm
│   │
│   ├── api/
│   │   ├── v1/
│   │   │   ├── ingest.py
│   │   │   ├── passages.py
│   │   │   ├── conversations.py
│   │   │   └── health.py
│   │   └── websocket.py
│   │
│   ├── models/
│   │   ├── conversation.py      # conversations, action_steps ORM models
│   │   └── ingest_job.py        # ingestion job tracking
│   │
│   ├── schemas/
│   │   ├── ingest.py            # IngestPDFRequest, IngestJobResponse
│   │   ├── passage.py           # PassageOut, PassageListOut
│   │   ├── conversation.py      # ConversationOut, ConversationDetailOut
│   │   └── websocket.py         # WSMessage union type (discriminated by "type")
│   │
│   ├── services/
│   │   ├── ingestion/
│   │   │   ├── pdf_parser.py    # extract_text_from_pdf(file) → list[Document]
│   │   │   ├── chunker.py       # chunk_documents(docs, config) → list[Document]
│   │   │   └── pipeline.py      # IngestionPipeline.run(file, metadata, job_id)
│   │   ├── retrieval/
│   │   │   └── retriever.py     # WisdomRetriever.search(query, tradition_filter, k)
│   │   └── llm/
│   │       └── factory.py       # make_chat_llm, make_embeddings
│   │
│   ├── graph/
│   │   ├── state.py             # SoulraState TypedDict
│   │   ├── nodes/
│   │   │   ├── intake.py
│   │   │   ├── retrieve.py
│   │   │   ├── grade.py
│   │   │   ├── rewrite.py
│   │   │   ├── clarify.py
│   │   │   └── synthesize.py
│   │   ├── edges.py             # route_after_grade, route_after_retrieve
│   │   └── builder.py           # build_graph() → CompiledGraph
│   │
│   └── core/
│       ├── exceptions.py        # SoulraException, IngestionError, RetrievalError
│       ├── logging.py           # structlog JSON config
│       └── middleware.py        # RequestIDMiddleware, TimingMiddleware
│
├── migrations/
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py      # conversations, action_steps, ingest_jobs tables
│
├── tests/
│   ├── unit/
│   │   ├── test_chunker.py
│   │   ├── test_graph_nodes.py
│   │   └── test_pdf_parser.py
│   ├── integration/
│   │   ├── test_ingest_api.py
│   │   └── test_ws_chat.py
│   └── conftest.py              # async DB session, mock LLM fixtures
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── pyproject.toml
├── alembic.ini
└── .env.example
```

---

## 8. Docker Compose

```yaml
# docker-compose.yml  (development)
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: soulra
      POSTGRES_USER: soulra
      POSTGRES_PASSWORD: soulra
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U soulra"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./app:/app/app

volumes:
  pgdata:
```

---

## 9. Key dependencies

```toml
# pyproject.toml — runtime
fastapi[standard] = ">=0.115"
uvicorn[standard] = ">=0.30"
sqlalchemy[asyncio] = ">=2.0"
asyncpg = ">=0.30"
alembic = ">=1.13"
pydantic-settings = ">=2.3"
langchain = ">=0.3"
langchain-openai = ">=0.2"
langchain-postgres = ">=0.0.9"
langgraph = ">=1.0"
langgraph-checkpoint-postgres = ">=2.0"
pypdf = ">=4.0"
structlog = ">=24.0"
python-multipart = ">=0.0.9"   # UploadFile support
```

---

## 10. Production-readiness requirements

| Concern | Implementation |
|---|---|
| Async end-to-end | `asyncpg`, `AsyncSession`, `async for` on graph events, `aiofiles` |
| Non-blocking ingestion | `BackgroundTasks`; job status in `ingest_jobs` table |
| Config management | `pydantic-settings`; single `.env`; no hardcoded values |
| DB migrations | Alembic; run on container startup via `prestart.sh` |
| Graph state persistence | `AsyncPostgresSaver` → same Postgres instance |
| Error handling | Custom exceptions; global handler returns RFC 7807 problem detail JSON |
| Structured logging | `structlog` JSON; `request_id` on every log line |
| File size limit | `MAX_UPLOAD_MB` setting enforced in middleware before handler |
| CORS | Configurable origins in `config.py` |
| Type safety | Pydantic v2 schemas; strict `TypedDict` in graph state |
| WebSocket reconnect | Client reconnects with existing `thread_id`; graph resumes from checkpoint |
| Rewrite loop guard | `rewrite_count` field in state; max 2 rewrites before forcing clarify |

---

## 11. Environment variables

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://soulra:soulra@localhost:5432/soulra
OPENROUTER_API_KEY=sk-or-v1-...

SMART_MODEL=anthropic/claude-opus-4-8
FAST_MODEL=anthropic/claude-sonnet-4-6
EMBEDDING_MODEL=openai/text-embedding-3-small

MAX_UPLOAD_MB=50
ALLOWED_ORIGINS=http://localhost:3000
```

---

## 12. Out of scope for V1

- Authentication / user accounts
- Rate limiting per user
- Celery worker (BackgroundTasks is sufficient for V1)
- Streaming ingestion progress over WebSocket
- Multi-language support
- Admin dashboard
