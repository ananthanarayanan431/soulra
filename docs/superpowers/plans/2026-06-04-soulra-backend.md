# Soulra Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready Python RAG backend that accepts spiritual text PDFs, embeds them into pgvector, and runs a LangGraph CRAG graph over WebSocket to deliver streaming wisdom responses.

**Architecture:** FastAPI async backend with a LangGraph CRAG graph (intake → retrieve → grade → rewrite → clarify → synthesize). All state, vectors, and conversation metadata live in a single Postgres instance running the `pgvector/pgvector:pg16` Docker image. LLM completions and embeddings both route through OpenRouter via LangChain's OpenAI-compatible wrapper.

**Tech Stack:** Python 3.12 · FastAPI · LangGraph 1.x · LangChain · langchain-openai · langchain-postgres · pgvector · AsyncPostgresSaver · pypdf · pydantic-settings · SQLAlchemy async · Alembic · pytest-asyncio · httpx

---

## File map

```
backend/
├── app/
│   ├── main.py                        # Task 20
│   ├── config.py                      # Task 2
│   ├── database.py                    # Task 3
│   ├── dependencies.py                # Task 20
│   ├── api/
│   │   ├── v1/
│   │   │   ├── health.py              # Task 15
│   │   │   ├── ingest.py              # Task 16
│   │   │   ├── passages.py            # Task 17
│   │   │   └── conversations.py       # Task 18
│   │   └── websocket.py               # Task 19
│   ├── models/
│   │   ├── conversation.py            # Task 4
│   │   └── ingest_job.py              # Task 4
│   ├── schemas/
│   │   ├── ingest.py                  # Task 16
│   │   ├── passage.py                 # Task 17
│   │   ├── conversation.py            # Task 18
│   │   └── websocket.py               # Task 19
│   ├── services/
│   │   ├── ingestion/
│   │   │   ├── pdf_parser.py          # Task 7
│   │   │   ├── chunker.py             # Task 7
│   │   │   └── pipeline.py            # Task 8
│   │   ├── retrieval/
│   │   │   └── retriever.py           # Task 9
│   │   └── llm/
│   │       └── factory.py             # Task 6
│   ├── graph/
│   │   ├── state.py                   # Task 10
│   │   ├── nodes/
│   │   │   ├── intake.py              # Task 10
│   │   │   ├── retrieve.py            # Task 11
│   │   │   ├── grade.py               # Task 11
│   │   │   ├── rewrite.py             # Task 12
│   │   │   ├── clarify.py             # Task 12
│   │   │   └── synthesize.py          # Task 13
│   │   ├── edges.py                   # Task 14
│   │   └── builder.py                 # Task 14
│   └── core/
│       ├── exceptions.py              # Task 2
│       ├── logging.py                 # Task 2
│       └── middleware.py              # Task 2
├── migrations/
│   ├── env.py                         # Task 4
│   └── versions/
│       └── 0001_initial.py            # Task 4
├── tests/
│   ├── conftest.py                    # Task 5
│   ├── unit/
│   │   ├── test_config.py             # Task 2
│   │   ├── test_llm_factory.py        # Task 6
│   │   ├── test_pdf_parser.py         # Task 7
│   │   ├── test_chunker.py            # Task 7
│   │   ├── test_retriever.py          # Task 9
│   │   ├── test_node_intake.py        # Task 10
│   │   ├── test_node_retrieve_grade.py # Task 11
│   │   ├── test_node_rewrite_clarify.py # Task 12
│   │   ├── test_node_synthesize.py    # Task 13
│   │   └── test_graph_builder.py      # Task 14
│   └── integration/
│       ├── test_health_api.py          # Task 15
│       ├── test_ingest_api.py          # Task 16
│       ├── test_passages_api.py        # Task 17
│       ├── test_conversations_api.py   # Task 18
│       └── test_ws_chat.py            # Task 19
├── docker-compose.yml                 # Task 1
├── Dockerfile                         # Task 1
├── pyproject.toml                     # Task 1
├── alembic.ini                        # Task 4
└── .env.example                       # Task 1
```

---

## Task 1: Project scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`
- Create: `backend/docker-compose.yml`
- Create: `backend/.env.example`

- [ ] **Step 1: Create `backend/` directory and `pyproject.toml`**

```toml
[project]
name = "soulra-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.13",
    "pydantic-settings>=2.3",
    "langchain>=0.3",
    "langchain-openai>=0.2",
    "langchain-postgres>=0.0.9",
    "langgraph>=1.0",
    "langgraph-checkpoint-postgres>=2.0",
    "pypdf>=4.0",
    "structlog>=24.0",
    "python-multipart>=0.0.9",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "httpx>=0.27",
    "anyio>=4.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
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

- [ ] **Step 4: Create `.env.example`**

```bash
DATABASE_URL=postgresql+asyncpg://soulra:soulra@localhost:5432/soulra
OPENROUTER_API_KEY=sk-or-v1-...

SMART_MODEL=anthropic/claude-opus-4-8
FAST_MODEL=anthropic/claude-sonnet-4-6
EMBEDDING_MODEL=openai/text-embedding-3-small

MAX_UPLOAD_MB=50
ALLOWED_ORIGINS=["http://localhost:3000"]
```

- [ ] **Step 5: Create stub `app/__init__.py` and package skeleton**

```bash
mkdir -p app/api/v1 app/models app/schemas app/services/ingestion \
         app/services/retrieval app/services/llm app/graph/nodes app/core \
         migrations/versions tests/unit tests/integration
touch app/__init__.py app/api/__init__.py app/api/v1/__init__.py \
      app/models/__init__.py app/schemas/__init__.py \
      app/services/__init__.py app/services/ingestion/__init__.py \
      app/services/retrieval/__init__.py app/services/llm/__init__.py \
      app/graph/__init__.py app/graph/nodes/__init__.py app/core/__init__.py \
      tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "chore: scaffold backend project structure"
```

---

## Task 2: Config and core utilities

**Files:**
- Create: `app/config.py`
- Create: `app/core/exceptions.py`
- Create: `app/core/logging.py`
- Create: `app/core/middleware.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing config test**

```python
# tests/unit/test_config.py
import pytest
from pydantic import ValidationError


def test_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from importlib import reload
    import app.config as cfg_module
    with pytest.raises((ValidationError, Exception)):
        reload(cfg_module)


def test_settings_defaults():
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    os.environ.setdefault("OPENROUTER_API_KEY", "sk-test")
    from app.config import Settings
    s = Settings()
    assert s.smart_model == "anthropic/claude-opus-4-8"
    assert s.fast_model == "anthropic/claude-sonnet-4-6"
    assert s.embedding_model == "openai/text-embedding-3-small"
    assert s.max_upload_mb == 50
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/unit/test_config.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` (app.config doesn't exist yet)

- [ ] **Step 3: Implement `app/config.py`**

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str
    openrouter_api_key: str

    smart_model: str = "anthropic/claude-opus-4-8"
    fast_model: str = "anthropic/claude-sonnet-4-6"
    embedding_model: str = "openai/text-embedding-3-small"

    max_upload_mb: int = 50
    allowed_origins: list[str] = ["http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v


settings = Settings()
```

- [ ] **Step 4: Implement `app/core/exceptions.py`**

```python
# app/core/exceptions.py
from fastapi import HTTPException


class SoulraException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class IngestionError(SoulraException):
    def __init__(self, message: str):
        super().__init__(message, code="INGESTION_FAILED")


class RetrievalError(SoulraException):
    def __init__(self, message: str):
        super().__init__(message, code="RETRIEVAL_FAILED")


class NotFoundError(SoulraException):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} '{id}' not found", code="NOT_FOUND")
```

- [ ] **Step 5: Implement `app/core/logging.py`**

```python
# app/core/logging.py
import structlog
import logging


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


logger = structlog.get_logger()
```

- [ ] **Step 6: Implement `app/core/middleware.py`**

```python
# app/core/middleware.py
import uuid
import time
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("request_handled",
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    duration_ms=round(duration_ms, 2))
        return response
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/unit/test_config.py -v
```

Expected: `PASSED`

- [ ] **Step 8: Commit**

```bash
git add app/config.py app/core/
git commit -m "feat: add config and core utilities"
```

---

## Task 3: Database engine and session

**Files:**
- Create: `app/database.py`

- [ ] **Step 1: Implement `app/database.py`**

No test at this layer — the async engine is integration-only; tested implicitly in Task 5 conftest.

```python
# app/database.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 2: Commit**

```bash
git add app/database.py
git commit -m "feat: add async database engine"
```

---

## Task 4: ORM models and Alembic migration

**Files:**
- Create: `app/models/conversation.py`
- Create: `app/models/ingest_job.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_initial.py`

- [ ] **Step 1: Implement `app/models/conversation.py`**

```python
# app/models/conversation.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Text, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    clarify_q: Mapped[str | None] = mapped_column(Text, nullable=True)
    clarify_ans: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    action_steps: Mapped[list["ActionStep"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ActionStep(Base):
    __tablename__ = "action_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="action_steps")
```

- [ ] **Step 2: Implement `app/models/ingest_job.py`**

```python
# app/models/ingest_job.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Text, String, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="processing"
    )  # processing | done | failed
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    tradition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunks_created: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
```

- [ ] **Step 3: Set up Alembic**

```bash
cd backend && alembic init migrations
```

- [ ] **Step 4: Replace `migrations/env.py` content**

```python
# migrations/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.config import settings
from app.database import Base
import app.models.conversation  # noqa: F401 — registers models
import app.models.ingest_job    # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Generate and inspect the initial migration**

```bash
alembic revision --autogenerate -m "initial"
```

Open the generated file in `migrations/versions/`. Verify it creates `conversations`, `action_steps`, and `ingest_jobs` tables.

- [ ] **Step 6: Commit**

```bash
git add app/models/ migrations/ alembic.ini
git commit -m "feat: add ORM models and initial Alembic migration"
```

---

## Task 5: Test infrastructure (conftest)

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Implement `tests/conftest.py`**

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.conversation import Conversation, ActionStep  # noqa: F401
from app.models.ingest_job import IngestJob  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_db):
    from app.main import app
    app.dependency_overrides[get_db] = lambda: test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_fast_llm():
    from langchain_core.messages import AIMessage
    llm = MagicMock()
    llm.invoke = MagicMock(return_value=AIMessage(content="mock response"))
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="mock response"))
    return llm


@pytest.fixture
def mock_smart_llm():
    from langchain_core.messages import AIMessage
    llm = MagicMock()
    llm.astream = AsyncMock(return_value=iter([
        MagicMock(content="token1"),
        MagicMock(content=" token2"),
    ]))
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="mock synthesis"))
    return llm


@pytest.fixture
def mock_vectorstore():
    from langchain_core.documents import Document
    vs = MagicMock()
    vs.asimilarity_search = AsyncMock(return_value=[
        Document(page_content="Stoic wisdom about refusing.", metadata={"tradition": "stoic", "author": "Marcus Aurelius", "citation": "Meditations 6.13"}),
        Document(page_content="Buddhist wisdom about attachment.", metadata={"tradition": "buddhist", "author": "Pema Chödrön", "citation": "When Things Fall Apart"}),
    ])
    return vs
```

- [ ] **Step 2: Verify conftest imports without error**

```bash
pytest tests/ --collect-only 2>&1 | head -20
```

Expected: no `ImportError`s (warnings about missing `app.main` are OK at this stage)

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add test infrastructure and fixtures"
```

---

## Task 6: LLM factory

**Files:**
- Create: `app/services/llm/factory.py`
- Create: `tests/unit/test_llm_factory.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_llm_factory.py
import pytest
from unittest.mock import patch


def test_make_chat_llm_uses_openrouter_base():
    with patch("app.services.llm.factory.settings") as mock_settings:
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.smart_model = "anthropic/claude-opus-4-8"
        from app.services.llm.factory import make_chat_llm
        llm = make_chat_llm("anthropic/claude-opus-4-8")
        assert llm.openai_api_base == "https://openrouter.ai/api/v1"
        assert llm.model_name == "anthropic/claude-opus-4-8"


def test_make_smart_llm_uses_smart_model():
    with patch("app.services.llm.factory.settings") as mock_settings:
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.smart_model = "anthropic/claude-opus-4-8"
        mock_settings.fast_model = "anthropic/claude-sonnet-4-6"
        mock_settings.embedding_model = "openai/text-embedding-3-small"
        from app.services.llm.factory import make_smart_llm, make_fast_llm
        smart = make_smart_llm()
        fast = make_fast_llm()
        assert smart.model_name == "anthropic/claude-opus-4-8"
        assert fast.model_name == "anthropic/claude-sonnet-4-6"


def test_make_embeddings_uses_openrouter():
    with patch("app.services.llm.factory.settings") as mock_settings:
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.embedding_model = "openai/text-embedding-3-small"
        from app.services.llm.factory import make_embeddings
        emb = make_embeddings()
        assert "openrouter" in emb.openai_api_base
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_llm_factory.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `app/services/llm/factory.py`**

```python
# app/services/llm/factory.py
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def make_chat_llm(model: str, streaming: bool = True) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        openai_api_base=OPENROUTER_BASE,
        openai_api_key=settings.openrouter_api_key,
        streaming=streaming,
    )


def make_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_base=OPENROUTER_BASE,
        openai_api_key=settings.openrouter_api_key,
    )


def make_smart_llm(streaming: bool = True) -> ChatOpenAI:
    return make_chat_llm(settings.smart_model, streaming=streaming)


def make_fast_llm(streaming: bool = True) -> ChatOpenAI:
    return make_chat_llm(settings.fast_model, streaming=streaming)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_llm_factory.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/llm/ tests/unit/test_llm_factory.py
git commit -m "feat: add LLM factory for OpenRouter"
```

---

## Task 7: PDF parser and chunker

**Files:**
- Create: `app/services/ingestion/pdf_parser.py`
- Create: `app/services/ingestion/chunker.py`
- Create: `tests/unit/test_pdf_parser.py`
- Create: `tests/unit/test_chunker.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_pdf_parser.py
import pytest
import io
from unittest.mock import patch, MagicMock


def test_extract_text_returns_documents():
    mock_pdf_content = b"%PDF-1.4 mock"
    file_like = io.BytesIO(mock_pdf_content)

    with patch("app.services.ingestion.pdf_parser.PdfReader") as mock_reader:
        page = MagicMock()
        page.extract_text.return_value = "Stoic wisdom on page one."
        mock_reader.return_value.pages = [page]

        from app.services.ingestion.pdf_parser import extract_text_from_pdf
        docs = extract_text_from_pdf(file_like, metadata={"tradition": "stoic", "author": "Marcus"})

    assert len(docs) == 1
    assert docs[0].page_content == "Stoic wisdom on page one."
    assert docs[0].metadata["tradition"] == "stoic"
    assert docs[0].metadata["page"] == 1


def test_extract_text_skips_empty_pages():
    file_like = io.BytesIO(b"%PDF mock")
    with patch("app.services.ingestion.pdf_parser.PdfReader") as mock_reader:
        p1, p2 = MagicMock(), MagicMock()
        p1.extract_text.return_value = "Text here."
        p2.extract_text.return_value = "   "  # whitespace only
        mock_reader.return_value.pages = [p1, p2]
        from app.services.ingestion.pdf_parser import extract_text_from_pdf
        docs = extract_text_from_pdf(file_like, metadata={})
    assert len(docs) == 1
```

```python
# tests/unit/test_chunker.py
from langchain_core.documents import Document
from app.services.ingestion.chunker import chunk_documents


def test_chunk_documents_splits_long_text():
    long_text = "word " * 300  # ~1500 chars
    docs = [Document(page_content=long_text, metadata={"tradition": "stoic"})]
    chunks = chunk_documents(docs)
    assert len(chunks) > 1


def test_chunk_documents_preserves_metadata():
    docs = [Document(page_content="Short text.", metadata={"tradition": "stoic", "author": "Marcus"})]
    chunks = chunk_documents(docs)
    assert all(c.metadata["tradition"] == "stoic" for c in chunks)
    assert all(c.metadata["author"] == "Marcus" for c in chunks)


def test_chunk_documents_no_empty_chunks():
    docs = [Document(page_content="A" * 1000, metadata={})]
    chunks = chunk_documents(docs)
    assert all(len(c.page_content.strip()) > 0 for c in chunks)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_pdf_parser.py tests/unit/test_chunker.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `app/services/ingestion/pdf_parser.py`**

```python
# app/services/ingestion/pdf_parser.py
from typing import IO
from pypdf import PdfReader
from langchain_core.documents import Document


def extract_text_from_pdf(
    file: IO[bytes],
    metadata: dict,
) -> list[Document]:
    reader = PdfReader(file)
    documents = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            documents.append(
                Document(
                    page_content=text,
                    metadata={**metadata, "page": i},
                )
            )
    return documents
```

- [ ] **Step 4: Implement `app/services/ingestion/chunker.py`**

```python
# app/services/ingestion/chunker.py
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    length_function=len,
)


def chunk_documents(documents: list[Document]) -> list[Document]:
    chunks = _splitter.split_documents(documents)
    return [c for c in chunks if c.page_content.strip()]
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_pdf_parser.py tests/unit/test_chunker.py -v
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/services/ingestion/pdf_parser.py app/services/ingestion/chunker.py \
        tests/unit/test_pdf_parser.py tests/unit/test_chunker.py
git commit -m "feat: add PDF parser and text chunker"
```

---

## Task 8: Ingestion pipeline

**Files:**
- Create: `app/services/ingestion/pipeline.py`
- Create: `tests/unit/test_pipeline.py` (unit, mocked embeddings)

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_pipeline.py
import pytest
import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_pipeline_run_returns_chunk_count(mock_vectorstore):
    from app.services.ingestion.pipeline import IngestionPipeline

    mock_embeddings = MagicMock()
    pipeline = IngestionPipeline(vectorstore=mock_vectorstore, embeddings=mock_embeddings)
    mock_vectorstore.aadd_documents = AsyncMock(return_value=["id1", "id2"])

    with patch("app.services.ingestion.pipeline.extract_text_from_pdf") as mock_parse, \
         patch("app.services.ingestion.pipeline.chunk_documents") as mock_chunk:
        from langchain_core.documents import Document
        mock_parse.return_value = [Document(page_content="text", metadata={})]
        mock_chunk.return_value = [
            Document(page_content="chunk1", metadata={"tradition": "stoic"}),
            Document(page_content="chunk2", metadata={"tradition": "stoic"}),
        ]

        result = await pipeline.run(
            file=io.BytesIO(b"pdf"),
            filename="test.pdf",
            metadata={"tradition": "stoic", "author": "Marcus", "source": "Meditations", "era": "ancient"},
        )

    assert result["chunks_created"] == 2
    mock_vectorstore.aadd_documents.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_run_raises_ingestion_error_on_failure(mock_vectorstore):
    from app.services.ingestion.pipeline import IngestionPipeline
    from app.core.exceptions import IngestionError

    mock_vectorstore.aadd_documents = AsyncMock(side_effect=Exception("DB error"))
    pipeline = IngestionPipeline(vectorstore=mock_vectorstore, embeddings=MagicMock())

    with patch("app.services.ingestion.pipeline.extract_text_from_pdf") as mock_parse, \
         patch("app.services.ingestion.pipeline.chunk_documents") as mock_chunk:
        from langchain_core.documents import Document
        mock_parse.return_value = [Document(page_content="t", metadata={})]
        mock_chunk.return_value = [Document(page_content="c", metadata={})]

        with pytest.raises(IngestionError):
            await pipeline.run(file=io.BytesIO(b"pdf"), filename="f.pdf", metadata={})
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/test_pipeline.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `app/services/ingestion/pipeline.py`**

```python
# app/services/ingestion/pipeline.py
from typing import IO
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from app.services.ingestion.pdf_parser import extract_text_from_pdf
from app.services.ingestion.chunker import chunk_documents
from app.core.exceptions import IngestionError
from app.core.logging import logger


class IngestionPipeline:
    def __init__(self, vectorstore: PGVector, embeddings: OpenAIEmbeddings):
        self.vectorstore = vectorstore
        self.embeddings = embeddings

    async def run(
        self,
        file: IO[bytes],
        filename: str,
        metadata: dict,
    ) -> dict:
        try:
            logger.info("ingestion_started", filename=filename)
            documents = extract_text_from_pdf(file, metadata=metadata)
            if not documents:
                raise IngestionError(f"No extractable text found in {filename}")

            chunks = chunk_documents(documents)
            if not chunks:
                raise IngestionError(f"No chunks produced from {filename}")

            await self.vectorstore.aadd_documents(chunks)
            logger.info("ingestion_complete", filename=filename, chunks=len(chunks))
            return {"chunks_created": len(chunks), "tokens_used": 0}
        except IngestionError:
            raise
        except Exception as e:
            logger.error("ingestion_failed", filename=filename, error=str(e))
            raise IngestionError(f"Ingestion failed for {filename}: {e}") from e
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_pipeline.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/ingestion/pipeline.py tests/unit/test_pipeline.py
git commit -m "feat: add ingestion pipeline"
```

---

## Task 9: PGVector retriever

**Files:**
- Create: `app/services/retrieval/retriever.py`
- Create: `tests/unit/test_retriever.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_retriever.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


@pytest.mark.asyncio
async def test_search_returns_documents(mock_vectorstore):
    from app.services.retrieval.retriever import WisdomRetriever
    retriever = WisdomRetriever(vectorstore=mock_vectorstore)
    results = await retriever.search("How to refuse gracefully?", k=5)
    assert len(results) == 2
    assert all(isinstance(d, Document) for d in results)


@pytest.mark.asyncio
async def test_search_with_tradition_filter(mock_vectorstore):
    from app.services.retrieval.retriever import WisdomRetriever
    retriever = WisdomRetriever(vectorstore=mock_vectorstore)
    await retriever.search("wisdom", tradition_filter="stoic", k=3)
    call_kwargs = mock_vectorstore.asimilarity_search.call_args.kwargs
    assert call_kwargs.get("filter") == {"tradition": "stoic"}


@pytest.mark.asyncio
async def test_search_raises_retrieval_error_on_failure():
    from app.services.retrieval.retriever import WisdomRetriever
    from app.core.exceptions import RetrievalError
    bad_vs = MagicMock()
    bad_vs.asimilarity_search = AsyncMock(side_effect=Exception("connection refused"))
    retriever = WisdomRetriever(vectorstore=bad_vs)
    with pytest.raises(RetrievalError):
        await retriever.search("query")
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/test_retriever.py -v
```

- [ ] **Step 3: Implement `app/services/retrieval/retriever.py`**

```python
# app/services/retrieval/retriever.py
from langchain_core.documents import Document
from langchain_postgres import PGVector
from app.core.exceptions import RetrievalError
from app.core.logging import logger


class WisdomRetriever:
    def __init__(self, vectorstore: PGVector):
        self.vectorstore = vectorstore

    async def search(
        self,
        query: str,
        tradition_filter: str | None = None,
        k: int = 5,
    ) -> list[Document]:
        try:
            kwargs: dict = {"k": k}
            if tradition_filter:
                kwargs["filter"] = {"tradition": tradition_filter}
            return await self.vectorstore.asimilarity_search(query, **kwargs)
        except Exception as e:
            logger.error("retrieval_failed", query=query, error=str(e))
            raise RetrievalError(f"Vector search failed: {e}") from e
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_retriever.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/retrieval/retriever.py tests/unit/test_retriever.py
git commit -m "feat: add PGVector retriever service"
```

---

## Task 10: LangGraph state and intake node

**Files:**
- Create: `app/graph/state.py`
- Create: `app/graph/nodes/intake.py`
- Create: `tests/unit/test_node_intake.py`

- [ ] **Step 1: Implement `app/graph/state.py`**

```python
# app/graph/state.py
from typing import Annotated, TypedDict
from langchain_core.documents import Document
from langgraph.graph.message import add_messages


class SoulraState(TypedDict):
    situation: str
    tradition_hints: list[str]    # extracted by intake: ["stoic", "buddhist"]
    query: str                    # current search query (may be rewritten)
    retrieved_docs: list[Document]
    grade_result: str             # "relevant" | "not_relevant"
    clarify_question: str
    clarify_chips: list[str]
    clarify_answer: str | None    # None = graph paused at interrupt
    refined_docs: list[Document]
    tradition_cards: list[dict]
    action_steps: list[dict]
    messages: Annotated[list, add_messages]
    rewrite_count: int            # max 2 rewrites before forcing clarify
```

No test for TypedDict — it is a type declaration.

- [ ] **Step 2: Write failing test for intake node**

```python
# tests/unit/test_node_intake.py
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
import json


def make_intake_llm_response(tradition_hints, query):
    content = json.dumps({"tradition_hints": tradition_hints, "query": query})
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value={"tradition_hints": tradition_hints, "query": query})
    return mock_llm


def test_intake_extracts_tradition_hints():
    from app.graph.nodes.intake import create_intake_node
    from app.graph.state import SoulraState

    mock_llm = make_intake_llm_response(["stoic", "buddhist"], "refusing gracefully")
    intake = create_intake_node(mock_llm)

    state: SoulraState = {
        "situation": "I keep saying yes to projects I don't want.",
        "tradition_hints": [],
        "query": "",
        "retrieved_docs": [],
        "grade_result": "",
        "clarify_question": "",
        "clarify_chips": [],
        "clarify_answer": None,
        "refined_docs": [],
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
        "rewrite_count": 0,
    }
    result = intake(state)
    assert result["tradition_hints"] == ["stoic", "buddhist"]
    assert result["query"] == "refusing gracefully"


def test_intake_initialises_rewrite_count():
    from app.graph.nodes.intake import create_intake_node
    mock_llm = make_intake_llm_response([], "query")
    intake = create_intake_node(mock_llm)
    state = {"situation": "test", "tradition_hints": [], "query": "", "retrieved_docs": [],
             "grade_result": "", "clarify_question": "", "clarify_chips": [],
             "clarify_answer": None, "refined_docs": [], "tradition_cards": [],
             "action_steps": [], "messages": [], "rewrite_count": 0}
    result = intake(state)
    assert result["rewrite_count"] == 0
```

- [ ] **Step 3: Run to verify failure**

```bash
pytest tests/unit/test_node_intake.py -v
```

- [ ] **Step 4: Implement `app/graph/nodes/intake.py`**

```python
# app/graph/nodes/intake.py
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from app.graph.state import SoulraState

TRADITION_OPTIONS = ["stoic", "vedanta", "buddhist", "sufi", "taoist",
                     "jewish", "christian_mystic", "zen"]

INTAKE_PROMPT = """You are helping route a user's situation to the right wisdom traditions.
Given this situation: {situation}

Extract:
1. tradition_hints: list of 2-3 most relevant traditions from {options}
2. query: a clear, concise search query (max 15 words) capturing the core problem

Respond with a JSON object with keys "tradition_hints" and "query"."""


class IntakeOutput(BaseModel):
    tradition_hints: list[str]
    query: str


def create_intake_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(IntakeOutput)

    def intake(state: SoulraState) -> dict:
        prompt = INTAKE_PROMPT.format(
            situation=state["situation"],
            options=TRADITION_OPTIONS,
        )
        result: IntakeOutput = structured_llm.invoke(prompt)
        return {
            "tradition_hints": result.tradition_hints,
            "query": result.query,
            "rewrite_count": 0,
        }

    return intake
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_node_intake.py -v
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/graph/state.py app/graph/nodes/intake.py tests/unit/test_node_intake.py
git commit -m "feat: add LangGraph state and intake node"
```

---

## Task 11: Retrieve and grade nodes

**Files:**
- Create: `app/graph/nodes/retrieve.py`
- Create: `app/graph/nodes/grade.py`
- Create: `tests/unit/test_node_retrieve_grade.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_node_retrieve_grade.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


@pytest.mark.asyncio
async def test_retrieve_node_calls_retriever_for_each_hint(mock_vectorstore):
    from app.graph.nodes.retrieve import create_retrieve_node
    from app.services.retrieval.retriever import WisdomRetriever
    retriever = WisdomRetriever(mock_vectorstore)
    retrieve = create_retrieve_node(retriever)

    state = {"query": "refusing gracefully", "tradition_hints": ["stoic", "buddhist"],
             "retrieved_docs": [], "situation": "", "grade_result": "",
             "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
             "refined_docs": [], "tradition_cards": [], "action_steps": [],
             "messages": [], "rewrite_count": 0}

    result = await retrieve(state)
    assert len(result["retrieved_docs"]) > 0
    assert mock_vectorstore.asimilarity_search.call_count == 2  # once per hint


def test_grade_node_returns_relevant_for_good_docs():
    from app.graph.nodes.grade import create_grade_node
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value={"score": "yes"})
    grade = create_grade_node(mock_llm)

    docs = [Document(page_content="Stoic wisdom on refusing.", metadata={})]
    state = {"query": "refusing gracefully", "retrieved_docs": docs,
             "situation": "I keep saying yes.", "tradition_hints": [],
             "grade_result": "", "clarify_question": "", "clarify_chips": [],
             "clarify_answer": None, "refined_docs": [], "tradition_cards": [],
             "action_steps": [], "messages": [], "rewrite_count": 0}
    result = grade(state)
    assert result["grade_result"] == "relevant"


def test_grade_node_returns_not_relevant_for_poor_docs():
    from app.graph.nodes.grade import create_grade_node
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value={"score": "no"})
    grade = create_grade_node(mock_llm)

    docs = [Document(page_content="Recipes for pasta.", metadata={})]
    state = {"query": "refusing gracefully", "retrieved_docs": docs,
             "situation": "I keep saying yes.", "tradition_hints": [],
             "grade_result": "", "clarify_question": "", "clarify_chips": [],
             "clarify_answer": None, "refined_docs": [], "tradition_cards": [],
             "action_steps": [], "messages": [], "rewrite_count": 0}
    result = grade(state)
    assert result["grade_result"] == "not_relevant"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/test_node_retrieve_grade.py -v
```

- [ ] **Step 3: Implement `app/graph/nodes/retrieve.py`**

```python
# app/graph/nodes/retrieve.py
from langchain_core.documents import Document
from app.graph.state import SoulraState
from app.services.retrieval.retriever import WisdomRetriever


def create_retrieve_node(retriever: WisdomRetriever):
    async def retrieve(state: SoulraState) -> dict:
        query = state["query"]
        hints = state["tradition_hints"] or [None]
        all_docs: list[Document] = []
        seen_contents: set[str] = set()

        for hint in hints:
            docs = await retriever.search(query, tradition_filter=hint, k=4)
            for doc in docs:
                if doc.page_content not in seen_contents:
                    all_docs.append(doc)
                    seen_contents.add(doc.page_content)

        return {"retrieved_docs": all_docs}

    return retrieve
```

- [ ] **Step 4: Implement `app/graph/nodes/grade.py`**

```python
# app/graph/nodes/grade.py
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from app.graph.state import SoulraState

GRADE_PROMPT = """Does this retrieved document contain wisdom relevant to the user's situation?

User situation: {situation}
Search query: {query}
Document: {content}

Answer with JSON: {{"score": "yes"}} if relevant, {{"score": "no"}} if not."""


class GradeOutput(BaseModel):
    score: str  # "yes" | "no"


def create_grade_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(GradeOutput)

    def grade(state: SoulraState) -> dict:
        docs = state["retrieved_docs"]
        if not docs:
            return {"grade_result": "not_relevant"}

        # Grade the majority of docs — if more than half are relevant, proceed
        relevant_count = 0
        for doc in docs[:4]:  # sample up to 4
            prompt = GRADE_PROMPT.format(
                situation=state["situation"],
                query=state["query"],
                content=doc.page_content[:500],
            )
            result: GradeOutput = structured_llm.invoke(prompt)
            if result.score == "yes":
                relevant_count += 1

        grade_result = "relevant" if relevant_count >= 2 else "not_relevant"
        return {"grade_result": grade_result}

    return grade
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_node_retrieve_grade.py -v
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/graph/nodes/retrieve.py app/graph/nodes/grade.py \
        tests/unit/test_node_retrieve_grade.py
git commit -m "feat: add retrieve and grade LangGraph nodes"
```

---

## Task 12: Rewrite and clarify nodes

**Files:**
- Create: `app/graph/nodes/rewrite.py`
- Create: `app/graph/nodes/clarify.py`
- Create: `tests/unit/test_node_rewrite_clarify.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_node_rewrite_clarify.py
import pytest
from unittest.mock import MagicMock


def make_structured_llm(return_value: dict):
    mock = MagicMock()
    mock.with_structured_output = MagicMock(return_value=mock)
    mock.invoke = MagicMock(return_value=return_value)
    return mock


def test_rewrite_node_produces_new_query():
    from app.graph.nodes.rewrite import create_rewrite_node
    mock_llm = make_structured_llm({"rewritten_query": "how to set boundaries at work"})
    rewrite = create_rewrite_node(mock_llm)

    state = {"situation": "I say yes too much.", "query": "refusing",
             "tradition_hints": ["stoic"], "retrieved_docs": [],
             "grade_result": "not_relevant", "clarify_question": "",
             "clarify_chips": [], "clarify_answer": None, "refined_docs": [],
             "tradition_cards": [], "action_steps": [], "messages": [],
             "rewrite_count": 0}
    result = rewrite(state)
    assert result["query"] == "how to set boundaries at work"
    assert result["rewrite_count"] == 1


def test_rewrite_increments_rewrite_count():
    from app.graph.nodes.rewrite import create_rewrite_node
    mock_llm = make_structured_llm({"rewritten_query": "new query"})
    rewrite = create_rewrite_node(mock_llm)

    state = {"situation": "s", "query": "q", "tradition_hints": [],
             "retrieved_docs": [], "grade_result": "not_relevant",
             "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
             "refined_docs": [], "tradition_cards": [], "action_steps": [],
             "messages": [], "rewrite_count": 1}
    result = rewrite(state)
    assert result["rewrite_count"] == 2


def test_clarify_node_produces_question_and_chips():
    from app.graph.nodes.clarify import create_clarify_node
    mock_llm = make_structured_llm({
        "question": "Is this about the work, the people, or something inside?",
        "chips": ["The work", "The people", "Something inside me", "It's all three"],
    })
    clarify = create_clarify_node(mock_llm)

    state = {"situation": "I say yes too much.", "query": "refusing",
             "tradition_hints": ["stoic"], "retrieved_docs": [],
             "grade_result": "relevant", "clarify_question": "",
             "clarify_chips": [], "clarify_answer": None, "refined_docs": [],
             "tradition_cards": [], "action_steps": [], "messages": [],
             "rewrite_count": 0}
    result = clarify(state)
    assert len(result["clarify_question"]) > 0
    assert len(result["clarify_chips"]) == 4
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/test_node_rewrite_clarify.py -v
```

- [ ] **Step 3: Implement `app/graph/nodes/rewrite.py`**

```python
# app/graph/nodes/rewrite.py
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from app.graph.state import SoulraState

REWRITE_PROMPT = """The original search query returned poor results.

User situation: {situation}
Original query: {query}

Write a better search query (max 15 words) that is more specific and likely to find
relevant wisdom passages. Focus on the emotional or philosophical core."""


class RewriteOutput(BaseModel):
    rewritten_query: str


def create_rewrite_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(RewriteOutput)

    def rewrite(state: SoulraState) -> dict:
        prompt = REWRITE_PROMPT.format(
            situation=state["situation"],
            query=state["query"],
        )
        result: RewriteOutput = structured_llm.invoke(prompt)
        return {
            "query": result.rewritten_query,
            "rewrite_count": state["rewrite_count"] + 1,
        }

    return rewrite
```

- [ ] **Step 4: Implement `app/graph/nodes/clarify.py`**

```python
# app/graph/nodes/clarify.py
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from app.graph.state import SoulraState

CLARIFY_PROMPT = """You are Soulra, a wisdom companion. Before drawing on ancient traditions,
you pause to understand the user's situation more deeply.

User situation: {situation}

Generate:
1. A single, thoughtful clarifying question (max 25 words, italic-style, contemplative tone)
2. Exactly 4 chip options the user can tap to answer

The question should help you understand whether this is about:
- External circumstances (work, people, situations)
- Internal patterns (fear, approval-seeking, identity)
- Relationships
- All of the above"""


class ClarifyOutput(BaseModel):
    question: str
    chips: list[str]


def create_clarify_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(ClarifyOutput)

    def clarify(state: SoulraState) -> dict:
        prompt = CLARIFY_PROMPT.format(situation=state["situation"])
        result: ClarifyOutput = structured_llm.invoke(prompt)
        return {
            "clarify_question": result.question,
            "clarify_chips": result.chips[:4],
        }

    return clarify
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_node_rewrite_clarify.py -v
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/graph/nodes/rewrite.py app/graph/nodes/clarify.py \
        tests/unit/test_node_rewrite_clarify.py
git commit -m "feat: add rewrite and clarify LangGraph nodes"
```

---

## Task 13: Synthesize node

**Files:**
- Create: `app/graph/nodes/synthesize.py`
- Create: `tests/unit/test_node_synthesize.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_node_synthesize.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


@pytest.mark.asyncio
async def test_synthesize_produces_tradition_cards_and_action_steps():
    from app.graph.nodes.synthesize import create_synthesize_node

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value={
        "tradition_cards": [
            {
                "tradition": "Stoic",
                "author": "Marcus Aurelius",
                "quote": "You always own the option of having no opinion.",
                "citation": "Meditations 6.13",
                "analysis": "The Stoic move is to notice the request comes from outside.",
            }
        ],
        "action_steps": [
            {"n": "01", "title": "Notice the moment of yes", "body": "Pause for one breath."},
        ],
    })
    synthesize = create_synthesize_node(mock_llm)

    docs = [
        Document(page_content="Stoic wisdom.", metadata={"tradition": "stoic", "author": "Marcus Aurelius", "citation": "Meditations 6.13"}),
    ]
    state = {"situation": "I say yes too much.", "query": "refusing",
             "tradition_hints": ["stoic"], "retrieved_docs": docs,
             "grade_result": "relevant", "clarify_question": "Is this internal?",
             "clarify_chips": ["Yes", "No"], "clarify_answer": "Yes",
             "refined_docs": docs, "tradition_cards": [], "action_steps": [],
             "messages": [], "rewrite_count": 0}
    result = await synthesize(state)
    assert len(result["tradition_cards"]) == 1
    assert result["tradition_cards"][0]["tradition"] == "Stoic"
    assert len(result["action_steps"]) >= 1
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/test_node_synthesize.py -v
```

- [ ] **Step 3: Implement `app/graph/nodes/synthesize.py`**

```python
# app/graph/nodes/synthesize.py
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from app.graph.state import SoulraState

SYNTHESIZE_PROMPT = """You are Soulra, an AI wisdom companion.

User situation: {situation}
Clarification: {clarify_answer}

Retrieved passages:
{passages}

Generate a response with:
1. tradition_cards: 2-3 cards, each with tradition, author, quote (exact passage), citation, analysis (2-3 sentences applying the wisdom to this situation)
2. action_steps: exactly 3 concrete steps the user can take today, each with n ("01"/"02"/"03"), title (short), body (1-2 sentences)

Ground every card in the retrieved passages. Do not invent quotes."""


class TraditionCard(BaseModel):
    tradition: str
    author: str
    quote: str
    citation: str
    analysis: str


class ActionStep(BaseModel):
    n: str
    title: str
    body: str


class SynthesizeOutput(BaseModel):
    tradition_cards: list[TraditionCard]
    action_steps: list[ActionStep]


def create_synthesize_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(SynthesizeOutput)

    async def synthesize(state: SoulraState) -> dict:
        docs = state["refined_docs"] or state["retrieved_docs"]
        passages = "\n\n".join(
            f"[{d.metadata.get('tradition', 'unknown')} — {d.metadata.get('citation', '')}]\n{d.page_content}"
            for d in docs[:8]
        )
        prompt = SYNTHESIZE_PROMPT.format(
            situation=state["situation"],
            clarify_answer=state.get("clarify_answer") or "not provided",
            passages=passages,
        )
        result: SynthesizeOutput = await structured_llm.ainvoke(prompt)
        return {
            "tradition_cards": [c.model_dump() for c in result.tradition_cards],
            "action_steps": [s.model_dump() for s in result.action_steps],
        }

    return synthesize
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_node_synthesize.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/graph/nodes/synthesize.py tests/unit/test_node_synthesize.py
git commit -m "feat: add synthesize LangGraph node"
```

---

## Task 14: Graph edges and builder

**Files:**
- Create: `app/graph/edges.py`
- Create: `app/graph/builder.py`
- Create: `tests/unit/test_graph_builder.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_graph_builder.py
import pytest
from unittest.mock import MagicMock, AsyncMock


def test_graph_builds_without_error():
    mock_retriever = MagicMock()
    mock_fast = MagicMock()
    mock_smart = MagicMock()
    mock_checkpointer = MagicMock()

    from app.graph.builder import build_graph
    graph = build_graph(
        retriever=mock_retriever,
        fast_llm=mock_fast,
        smart_llm=mock_smart,
        checkpointer=mock_checkpointer,
    )
    assert graph is not None


def test_route_after_grade_returns_rewrite_when_not_relevant():
    from app.graph.edges import route_after_grade
    state = {"grade_result": "not_relevant", "rewrite_count": 0,
             "situation": "", "tradition_hints": [], "query": "", "retrieved_docs": [],
             "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
             "refined_docs": [], "tradition_cards": [], "action_steps": [],
             "messages": []}
    assert route_after_grade(state) == "rewrite_query"


def test_route_after_grade_returns_clarify_when_relevant():
    from app.graph.edges import route_after_grade
    state = {"grade_result": "relevant", "rewrite_count": 0,
             "situation": "", "tradition_hints": [], "query": "", "retrieved_docs": [],
             "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
             "refined_docs": [], "tradition_cards": [], "action_steps": [],
             "messages": []}
    assert route_after_grade(state) == "clarify"


def test_route_after_grade_forces_clarify_after_max_rewrites():
    from app.graph.edges import route_after_grade
    state = {"grade_result": "not_relevant", "rewrite_count": 2,
             "situation": "", "tradition_hints": [], "query": "", "retrieved_docs": [],
             "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
             "refined_docs": [], "tradition_cards": [], "action_steps": [],
             "messages": []}
    assert route_after_grade(state) == "clarify"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/unit/test_graph_builder.py -v
```

- [ ] **Step 3: Implement `app/graph/edges.py`**

```python
# app/graph/edges.py
from typing import Literal
from app.graph.state import SoulraState

MAX_REWRITES = 2


def route_after_grade(
    state: SoulraState,
) -> Literal["rewrite_query", "clarify"]:
    if state["grade_result"] == "relevant" or state["rewrite_count"] >= MAX_REWRITES:
        return "clarify"
    return "rewrite_query"
```

- [ ] **Step 4: Implement `app/graph/builder.py`**

```python
# app/graph/builder.py
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_openai import ChatOpenAI
from app.graph.state import SoulraState
from app.graph.edges import route_after_grade
from app.graph.nodes.intake import create_intake_node
from app.graph.nodes.retrieve import create_retrieve_node
from app.graph.nodes.grade import create_grade_node
from app.graph.nodes.rewrite import create_rewrite_node
from app.graph.nodes.clarify import create_clarify_node
from app.graph.nodes.synthesize import create_synthesize_node
from app.services.retrieval.retriever import WisdomRetriever


def build_graph(
    retriever: WisdomRetriever,
    fast_llm: ChatOpenAI,
    smart_llm: ChatOpenAI,
    checkpointer: BaseCheckpointSaver,
):
    workflow = StateGraph(SoulraState)

    workflow.add_node("intake", create_intake_node(fast_llm))
    workflow.add_node("retrieve", create_retrieve_node(retriever))
    workflow.add_node("grade_docs", create_grade_node(fast_llm))
    workflow.add_node("rewrite_query", create_rewrite_node(fast_llm))
    workflow.add_node("clarify", create_clarify_node(fast_llm))
    workflow.add_node("retrieve_refined", create_retrieve_node(retriever))
    workflow.add_node("synthesize", create_synthesize_node(smart_llm))

    workflow.add_edge(START, "intake")
    workflow.add_edge("intake", "retrieve")
    workflow.add_edge("retrieve", "grade_docs")
    workflow.add_conditional_edges("grade_docs", route_after_grade)
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("clarify", "retrieve_refined")  # graph pauses BEFORE this node
    workflow.add_edge("retrieve_refined", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["retrieve_refined"],
    )
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_graph_builder.py -v
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/graph/edges.py app/graph/builder.py tests/unit/test_graph_builder.py
git commit -m "feat: add LangGraph edges and graph builder"
```

---

## Task 15: Health and status endpoints

**Files:**
- Create: `app/api/v1/health.py`
- Create: `tests/integration/test_health_api.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_health_api.py
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_status_returns_components(client):
    resp = await client.get("/api/v1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "database" in data
    assert "vector_store" in data
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/integration/test_health_api.py -v
```

- [ ] **Step 3: Implement `app/api/v1/health.py`**

```python
# app/api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    db_ok = False
    passage_count = 0
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        result = await db.execute(
            text("SELECT COUNT(*) FROM langchain_pg_embedding")
        )
        passage_count = result.scalar() or 0
    except Exception:
        pass

    return {
        "database": "ok" if db_ok else "error",
        "vector_store": {"passage_count": passage_count},
    }
```

- [ ] **Step 4: Create a minimal `app/main.py` to run the test**

```python
# app/main.py (minimal for Task 15 — expanded in Task 20)
from fastapi import FastAPI
from app.api.v1.health import router as health_router

app = FastAPI(title="Soulra Backend")
app.include_router(health_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/integration/test_health_api.py -v
```

Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/api/v1/health.py app/main.py tests/integration/test_health_api.py
git commit -m "feat: add health and status endpoints"
```

---

## Task 16: Ingest endpoints

**Files:**
- Create: `app/schemas/ingest.py`
- Create: `app/api/v1/ingest.py`
- Create: `tests/integration/test_ingest_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_ingest_api.py
import pytest
import io
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_ingest_pdf_returns_job_id(client):
    with patch("app.api.v1.ingest.IngestionPipeline") as MockPipeline:
        instance = MockPipeline.return_value
        instance.run = AsyncMock(return_value={"chunks_created": 5, "tokens_used": 1000})

        resp = await client.post(
            "/api/v1/ingest/pdf",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 mock"), "application/pdf")},
            data={"tradition": "stoic", "author": "Marcus Aurelius",
                  "source": "Meditations", "era": "ancient"},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_ingest_pdf_rejects_non_pdf(client):
    resp = await client.post(
        "/api/v1/ingest/pdf",
        files={"file": ("test.txt", io.BytesIO(b"text"), "text/plain")},
        data={"tradition": "stoic", "author": "Marcus", "source": "Med", "era": "ancient"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_job_status_returns_processing(client, test_db):
    from app.models.ingest_job import IngestJob
    import uuid
    job = IngestJob(id=uuid.uuid4(), status="processing")
    test_db.add(job)
    await test_db.flush()

    resp = await client.get(f"/api/v1/ingest/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/integration/test_ingest_api.py -v
```

- [ ] **Step 3: Implement `app/schemas/ingest.py`**

```python
# app/schemas/ingest.py
import uuid
from pydantic import BaseModel, field_validator


class IngestPDFRequest(BaseModel):
    tradition: str
    author: str
    source: str
    era: str = "unknown"


class IngestJobResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    filename: str | None = None
    chunks_created: int = 0
    tokens_used: int = 0
    error: str | None = None
```

- [ ] **Step 4: Implement `app/api/v1/ingest.py`**

```python
# app/api/v1/ingest.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.ingest_job import IngestJob
from app.schemas.ingest import IngestJobResponse
from app.services.ingestion.pipeline import IngestionPipeline
from app.core.logging import logger

router = APIRouter(tags=["ingest"])


def _get_pipeline() -> IngestionPipeline:
    from app.dependencies import get_vectorstore, get_embeddings
    return IngestionPipeline(
        vectorstore=get_vectorstore(),
        embeddings=get_embeddings(),
    )


async def _run_ingestion(
    pipeline: IngestionPipeline,
    file_content: bytes,
    filename: str,
    metadata: dict,
    job_id: uuid.UUID,
    db_url: str,
):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.config import settings
    eng = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(eng, expire_on_commit=False)
    async with session_factory() as session:
        try:
            import io
            result = await pipeline.run(
                file=io.BytesIO(file_content),
                filename=filename,
                metadata=metadata,
            )
            stmt = select(IngestJob).where(IngestJob.id == job_id)
            row = (await session.execute(stmt)).scalar_one()
            row.status = "done"
            row.chunks_created = result["chunks_created"]
            row.completed_at = datetime.now(timezone.utc)
            await session.commit()
        except Exception as e:
            stmt = select(IngestJob).where(IngestJob.id == job_id)
            row = (await session.execute(stmt)).scalar_one()
            row.status = "failed"
            row.error = str(e)
            await session.commit()
    await eng.dispose()


@router.post("/ingest/pdf", status_code=202, response_model=IngestJobResponse)
async def ingest_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")

    content = await file.read()
    job = IngestJob(filename=file.filename, tradition=tradition)
    db.add(job)
    await db.flush()
    await db.commit()

    from app.config import settings
    background_tasks.add_task(
        _run_ingestion,
        _get_pipeline(),
        content,
        file.filename or "upload.pdf",
        {"tradition": tradition, "author": author, "source": source, "era": era},
        job.id,
        settings.database_url,
    )
    return IngestJobResponse(job_id=job.id, status="processing", filename=file.filename)


@router.get("/ingest/jobs/{job_id}", response_model=IngestJobResponse)
async def get_ingest_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(IngestJob).where(IngestJob.id == job_id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return IngestJobResponse(
        job_id=row.id,
        status=row.status,
        filename=row.filename,
        chunks_created=row.chunks_created,
        tokens_used=row.tokens_used,
        error=row.error,
    )
```

- [ ] **Step 5: Add ingest router to `app/main.py`**

```python
# app/main.py (add after health_router line)
from app.api.v1.ingest import router as ingest_router
app.include_router(ingest_router, prefix="/api/v1")
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/integration/test_ingest_api.py -v
```

Expected: all `PASSED`

- [ ] **Step 7: Commit**

```bash
git add app/schemas/ingest.py app/api/v1/ingest.py tests/integration/test_ingest_api.py
git commit -m "feat: add PDF ingest endpoints with background task"
```

---

## Task 17: Passages and collections endpoints

**Files:**
- Create: `app/schemas/passage.py`
- Create: `app/api/v1/passages.py`
- Create: `tests/integration/test_passages_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_passages_api.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_list_passages_returns_array(client):
    with patch("app.api.v1.passages.get_vectorstore_dep") as mock_vs_dep:
        mock_vs = MagicMock()
        mock_vs.asimilarity_search = AsyncMock(return_value=[])
        mock_vs_dep.return_value = mock_vs
        resp = await client.get("/api/v1/passages")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_delete_passage_calls_vectorstore(client):
    with patch("app.api.v1.passages.get_vectorstore_dep") as mock_vs_dep:
        mock_vs = MagicMock()
        mock_vs.adelete = AsyncMock(return_value=True)
        mock_vs_dep.return_value = mock_vs
        resp = await client.delete("/api/v1/passages/some-passage-id")
    assert resp.status_code == 204
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/integration/test_passages_api.py -v
```

- [ ] **Step 3: Implement `app/schemas/passage.py`**

```python
# app/schemas/passage.py
from pydantic import BaseModel


class PassageOut(BaseModel):
    id: str
    content: str
    tradition: str | None = None
    author: str | None = None
    source: str | None = None
    era: str | None = None
    citation: str | None = None
```

- [ ] **Step 4: Implement `app/api/v1/passages.py`**

```python
# app/api/v1/passages.py
from fastapi import APIRouter, Depends, Query
from app.schemas.passage import PassageOut
from app.dependencies import get_vectorstore as get_vectorstore_dep

router = APIRouter(tags=["passages"])


@router.get("/passages", response_model=list[PassageOut])
async def list_passages(
    tradition: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    vectorstore=Depends(get_vectorstore_dep),
):
    filter_kwargs = {}
    if tradition:
        filter_kwargs["filter"] = {"tradition": tradition}
    # PGVector similarity_search with empty query returns recent docs
    docs = await vectorstore.asimilarity_search("*", k=limit, **filter_kwargs)
    return [
        PassageOut(
            id=str(i),
            content=d.page_content,
            **{k: d.metadata.get(k) for k in ("tradition", "author", "source", "era", "citation")},
        )
        for i, d in enumerate(docs)
    ]


@router.delete("/passages/{passage_id}", status_code=204)
async def delete_passage(
    passage_id: str,
    vectorstore=Depends(get_vectorstore_dep),
):
    await vectorstore.adelete(ids=[passage_id])


@router.get("/collections")
async def list_collections(vectorstore=Depends(get_vectorstore_dep)):
    # PGVector stores collection name on the instance
    return [{"name": vectorstore.collection_name}]
```

- [ ] **Step 5: Add to `app/main.py`**

```python
from app.api.v1.passages import router as passages_router
app.include_router(passages_router, prefix="/api/v1")
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/integration/test_passages_api.py -v
```

Expected: all `PASSED`

- [ ] **Step 7: Commit**

```bash
git add app/schemas/passage.py app/api/v1/passages.py tests/integration/test_passages_api.py
git commit -m "feat: add passages and collections endpoints"
```

---

## Task 18: Conversations endpoint

**Files:**
- Create: `app/schemas/conversation.py`
- Create: `app/api/v1/conversations.py`
- Create: `tests/integration/test_conversations_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_conversations_api.py
import pytest
import uuid
from app.models.conversation import Conversation, ActionStep


@pytest.mark.asyncio
async def test_list_conversations_returns_empty(client):
    resp = await client.get("/api/v1/conversations")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_conversation_returns_detail(client, test_db):
    conv = Conversation(
        thread_id="thread-abc",
        situation="I say yes too much.",
        clarify_q="Is this internal?",
        clarify_ans="Yes, internal.",
    )
    test_db.add(conv)
    await test_db.flush()

    resp = await client.get(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["situation"] == "I say yes too much."
    assert data["clarify_q"] == "Is this internal?"


@pytest.mark.asyncio
async def test_delete_conversation_removes_record(client, test_db):
    conv = Conversation(thread_id="thread-del", situation="test")
    test_db.add(conv)
    await test_db.flush()

    resp = await client.delete(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/integration/test_conversations_api.py -v
```

- [ ] **Step 3: Implement `app/schemas/conversation.py`**

```python
# app/schemas/conversation.py
import uuid
from datetime import datetime
from pydantic import BaseModel


class ActionStepOut(BaseModel):
    step_number: int
    title: str
    body: str


class ConversationOut(BaseModel):
    id: uuid.UUID
    thread_id: str
    situation: str
    clarify_q: str | None
    clarify_ans: str | None
    created_at: datetime
    action_steps: list[ActionStepOut] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Implement `app/api/v1/conversations.py`**

```python
# app/api/v1/conversations.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationOut

router = APIRouter(tags=["conversations"])


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conversation).order_by(Conversation.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [ConversationOut.model_validate(r) for r in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationOut.model_validate(row)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(row)
    await db.commit()
```

- [ ] **Step 5: Add to `app/main.py`**

```python
from app.api.v1.conversations import router as conversations_router
app.include_router(conversations_router, prefix="/api/v1")
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/integration/test_conversations_api.py -v
```

Expected: all `PASSED`

- [ ] **Step 7: Commit**

```bash
git add app/schemas/conversation.py app/api/v1/conversations.py \
        tests/integration/test_conversations_api.py
git commit -m "feat: add conversations CRUD endpoints"
```

---

## Task 19: WebSocket chat handler

**Files:**
- Create: `app/schemas/websocket.py`
- Create: `app/api/websocket.py`
- Create: `tests/integration/test_ws_chat.py`

- [ ] **Step 1: Implement `app/schemas/websocket.py`**

```python
# app/schemas/websocket.py
from typing import Literal, Union
from pydantic import BaseModel


# Client → Server
class StartMessage(BaseModel):
    type: Literal["start"]
    situation: str


class ClarificationMessage(BaseModel):
    type: Literal["clarification"]
    choice: str


class FollowupMessage(BaseModel):
    type: Literal["followup"]
    text: str


ClientMessage = Union[StartMessage, ClarificationMessage, FollowupMessage]

# Server → Client
class StatusEvent(BaseModel):
    type: Literal["status"] = "status"
    node: str


class ClarifyEvent(BaseModel):
    type: Literal["clarify"] = "clarify"
    question: str


class ChipsEvent(BaseModel):
    type: Literal["chips"] = "chips"
    options: list[str]


class TraditionTokenEvent(BaseModel):
    type: Literal["tradition_token"] = "tradition_token"
    tradition: str
    token: str


class TraditionDoneEvent(BaseModel):
    type: Literal["tradition_done"] = "tradition_done"
    tradition: str
    author: str
    quote: str
    citation: str
    analysis: str


class ActionStepEvent(BaseModel):
    type: Literal["action_step"] = "action_step"
    n: str
    title: str
    body: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str = "INTERNAL_ERROR"
```

- [ ] **Step 2: Write failing test**

```python
# tests/integration/test_ws_chat.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def test_ws_chat_accepts_connection():
    """Verify WebSocket endpoint is registered and accepts connections."""
    from app.main import app
    client = TestClient(app)
    with client.websocket_connect("/ws/chat") as ws:
        # Connection established without error
        assert ws is not None


def test_ws_chat_responds_to_start_message():
    from app.main import app

    mock_graph = MagicMock()
    mock_graph.astream_events = AsyncMock(return_value=_make_event_stream([
        {"event": "on_chain_start", "name": "intake", "data": {}},
        {"event": "on_chain_start", "name": "clarify", "data": {}},
        {"event": "on_chain_end",   "name": "clarify", "data": {
            "output": {
                "clarify_question": "Is this about work or something inside?",
                "clarify_chips": ["The work", "Something inside", "Both", "Other"],
            }
        }},
    ]))

    with patch("app.api.websocket.get_graph", return_value=mock_graph):
        client = TestClient(app)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"type": "start", "situation": "I say yes too much."})
            messages = []
            try:
                for _ in range(10):
                    msg = ws.receive_json(timeout=1)
                    messages.append(msg)
                    if msg.get("type") in ("chips", "error", "done"):
                        break
            except Exception:
                pass

    types = [m["type"] for m in messages]
    assert "clarify" in types or "chips" in types or "status" in types


async def _make_event_stream(events):
    for e in events:
        yield e
```

- [ ] **Step 3: Run to verify failure**

```bash
pytest tests/integration/test_ws_chat.py -v
```

- [ ] **Step 4: Implement `app/api/websocket.py`**

```python
# app/api/websocket.py
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.schemas.websocket import (
    StartMessage, ClarificationMessage, StatusEvent, ClarifyEvent,
    ChipsEvent, TraditionDoneEvent, ActionStepEvent, DoneEvent, ErrorEvent,
)
from app.core.logging import logger

router = APIRouter(tags=["websocket"])

_graph = None


def get_graph():
    global _graph
    return _graph


def set_graph(g):
    global _graph
    _graph = g


@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()

    async def send(payload: dict):
        await websocket.send_text(json.dumps(payload))

    try:
        # Phase 1: receive situation, run graph until interrupt
        raw = await websocket.receive_json()
        msg = StartMessage(**raw)

        await send(StatusEvent(node="intake").model_dump())

        initial_input = {
            "situation": msg.situation,
            "tradition_hints": [],
            "query": "",
            "retrieved_docs": [],
            "grade_result": "",
            "clarify_question": "",
            "clarify_chips": [],
            "clarify_answer": None,
            "refined_docs": [],
            "tradition_cards": [],
            "action_steps": [],
            "messages": [],
            "rewrite_count": 0,
        }

        async for event in graph.astream_events(initial_input, config, version="v2"):
            event_name = event.get("name", "")
            event_type = event.get("event", "")

            if event_type == "on_chain_start":
                await send(StatusEvent(node=event_name).model_dump())

            if event_type == "on_chain_end" and event_name == "clarify":
                output = event.get("data", {}).get("output", {})
                question = output.get("clarify_question", "")
                chips = output.get("clarify_chips", [])
                if question:
                    await send(ClarifyEvent(question=question).model_dump())
                    await send(ChipsEvent(options=chips).model_dump())
                break  # graph is now paused at interrupt

        # Phase 2: wait for chip selection, resume graph
        raw = await websocket.receive_json()
        clarification = ClarificationMessage(**raw)

        await send(StatusEvent(node="retrieve_refined").model_dump())

        await graph.aupdate_state(
            config,
            {"clarify_answer": clarification.choice},
        )

        async for event in graph.astream_events(None, config, version="v2"):
            event_name = event.get("name", "")
            event_type = event.get("event", "")

            if event_type == "on_chain_start":
                await send(StatusEvent(node=event_name).model_dump())

            if event_type == "on_chain_end" and event_name == "synthesize":
                output = event.get("data", {}).get("output", {})
                for card in output.get("tradition_cards", []):
                    await send(TraditionDoneEvent(**card).model_dump())
                for step in output.get("action_steps", []):
                    await send(ActionStepEvent(**step).model_dump())
                break

        await send(DoneEvent().model_dump())

    except WebSocketDisconnect:
        logger.info("ws_disconnected", thread_id=thread_id)
    except Exception as e:
        logger.error("ws_error", error=str(e), thread_id=thread_id)
        try:
            await send(ErrorEvent(message=str(e)).model_dump())
        except Exception:
            pass
```

- [ ] **Step 5: Add websocket router to `app/main.py`**

```python
from app.api.websocket import router as ws_router
app.include_router(ws_router)
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/integration/test_ws_chat.py -v
```

Expected: all `PASSED`

- [ ] **Step 7: Commit**

```bash
git add app/schemas/websocket.py app/api/websocket.py tests/integration/test_ws_chat.py
git commit -m "feat: add WebSocket chat handler with LangGraph interrupt"
```

---

## Task 20: Dependencies and final app wiring

**Files:**
- Create: `app/dependencies.py`
- Modify: `app/main.py` (complete version)

- [ ] **Step 1: Implement `app/dependencies.py`**

```python
# app/dependencies.py
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, engine, AsyncSessionLocal  # noqa: F401
from app.services.llm.factory import make_smart_llm, make_fast_llm, make_embeddings
from app.services.retrieval.retriever import WisdomRetriever
from langchain_postgres import PGVector
from app.config import settings


@lru_cache
def get_embeddings():
    return make_embeddings()


@lru_cache
def get_vectorstore() -> PGVector:
    return PGVector(
        embeddings=get_embeddings(),
        collection_name="wisdom_passages",
        connection=settings.database_url,
    )


@lru_cache
def get_retriever() -> WisdomRetriever:
    return WisdomRetriever(vectorstore=get_vectorstore())


@lru_cache
def get_smart_llm():
    return make_smart_llm()


@lru_cache
def get_fast_llm():
    return make_fast_llm()
```

- [ ] **Step 2: Write the complete `app/main.py`**

```python
# app/main.py
import contextlib
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.core.exceptions import SoulraException
from app.core.logging import configure_logging, logger
from app.core.middleware import RequestIDMiddleware, TimingMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.passages import router as passages_router
from app.api.v1.conversations import router as conversations_router
from app.api.websocket import router as ws_router, set_graph


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup", env="development")

    # Run Alembic migrations on startup
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"], check=True)

    # Build and wire the LangGraph graph
    async with AsyncPostgresSaver.from_conn_string(
        settings.database_url.replace("+asyncpg", "")  # sync URL for checkpointer
    ) as checkpointer:
        from app.dependencies import get_retriever, get_fast_llm, get_smart_llm
        from app.graph.builder import build_graph
        graph = build_graph(
            retriever=get_retriever(),
            fast_llm=get_fast_llm(),
            smart_llm=get_smart_llm(),
            checkpointer=checkpointer,
        )
        set_graph(graph)
        logger.info("graph_ready")
        yield

    logger.info("shutdown")


app = FastAPI(
    title="Soulra Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(health_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(passages_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(ws_router)


@app.exception_handler(SoulraException)
async def soulra_exception_handler(request: Request, exc: SoulraException):
    return JSONResponse(
        status_code=500,
        content={"type": exc.code, "message": exc.message},
    )
```

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all previously-passing tests still `PASSED`

- [ ] **Step 4: Commit**

```bash
git add app/dependencies.py app/main.py
git commit -m "feat: wire complete app with lifespan, middleware, and LangGraph graph"
```

---

## Task 21: Docker smoke test

- [ ] **Step 1: Copy `.env.example` to `.env` and fill in your OpenRouter key**

```bash
cp .env.example .env
# Set OPENROUTER_API_KEY=sk-or-v1-...
```

- [ ] **Step 2: Start services**

```bash
docker compose up --build -d
```

- [ ] **Step 3: Wait for health**

```bash
curl -s http://localhost:8000/api/v1/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Check status**

```bash
curl -s http://localhost:8000/api/v1/status | python3 -m json.tool
```

Expected: `{"database": "ok", "vector_store": {"passage_count": 0}}`

- [ ] **Step 5: Upload a test PDF**

```bash
curl -s -X POST http://localhost:8000/api/v1/ingest/pdf \
  -F "file=@/path/to/meditations.pdf" \
  -F "tradition=stoic" \
  -F "author=Marcus Aurelius" \
  -F "source=Meditations" \
  -F "era=ancient" | python3 -m json.tool
```

Expected: `{"job_id": "...", "status": "processing"}`

- [ ] **Step 6: Poll until done**

```bash
JOB_ID="<job_id from above>"
curl -s http://localhost:8000/api/v1/ingest/jobs/$JOB_ID | python3 -m json.tool
```

Expected after a few seconds: `{"status": "done", "chunks_created": N, ...}`

- [ ] **Step 7: Commit**

```bash
git add .env.example docker-compose.yml
git commit -m "chore: verify Docker smoke test passes"
```

---

## Self-review

**Spec coverage:**
- ✅ All REST endpoints: health, ingest (pdf+text+url+status), passages, collections, conversations, status
- ✅ WebSocket `/ws/chat` with full two-phase interrupt protocol
- ✅ LangGraph CRAG graph: all 7 nodes, edges, interrupt
- ✅ PDF ingestion as non-blocking background task
- ✅ pgvector via `langchain-postgres` PGVector
- ✅ OpenRouter for both LLM and embeddings via single factory
- ✅ AsyncPostgresSaver for graph checkpoints
- ✅ ORM models for conversations, action_steps, ingest_jobs
- ✅ Alembic migrations run on startup
- ✅ Docker Compose with `pgvector/pgvector:pg16`
- ✅ Modular folder structure matching spec

**Gap noted:** `/ingest/text` and `/ingest/url` endpoints are specified but not tasked. Adding them to Task 16 is low-risk — they share the same pipeline, just different parsers. Add after Task 16 passes:

```python
# app/api/v1/ingest.py — add these two handlers after ingest_pdf

@router.post("/ingest/text", status_code=202, response_model=IngestJobResponse)
async def ingest_text(
    background_tasks: BackgroundTasks,
    content: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    db: AsyncSession = Depends(get_db),
):
    import hashlib
    filename = f"text-{hashlib.md5(content[:50].encode()).hexdigest()[:8]}.txt"
    job = IngestJob(filename=filename, tradition=tradition)
    db.add(job)
    await db.flush()
    await db.commit()
    from app.config import settings
    background_tasks.add_task(
        _run_ingestion,
        _get_pipeline(),
        content.encode(),
        filename,
        {"tradition": tradition, "author": author, "source": source, "era": era},
        job.id,
        settings.database_url,
    )
    return IngestJobResponse(job_id=job.id, status="processing")


@router.post("/ingest/url", status_code=202, response_model=IngestJobResponse)
async def ingest_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    db: AsyncSession = Depends(get_db),
):
    import httpx
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.get(url, timeout=15)
        resp.raise_for_status()
        text_content = resp.text

    job = IngestJob(filename=url, tradition=tradition)
    db.add(job)
    await db.flush()
    await db.commit()
    from app.config import settings
    background_tasks.add_task(
        _run_ingestion,
        _get_pipeline(),
        text_content.encode(),
        url,
        {"tradition": tradition, "author": author, "source": source, "era": era},
        job.id,
        settings.database_url,
    )
    return IngestJobResponse(job_id=job.id, status="processing", filename=url)
```

**Type consistency check:** `SoulraState` field names are consistent across all nodes and the graph builder. `clarify_answer` (not `clarification_answer`) used throughout. `tradition_cards` / `action_steps` return `list[dict]` from synthesize and are consumed directly in the WebSocket handler. ✅

**Placeholder scan:** No TBDs, no "implement later", no "add appropriate X" patterns. All code blocks are complete. ✅
