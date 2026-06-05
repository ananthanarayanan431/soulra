import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from soulra.database import Base, get_db
from soulra.models.conversation import Conversation, ActionStep  # noqa: F401
from soulra.models.ingest_job import IngestJob  # noqa: F401

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
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_db):
    from soulra.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


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

    async def _astream(*args, **kwargs):
        for chunk in [MagicMock(content="token1"), MagicMock(content=" token2")]:
            yield chunk

    llm.astream = _astream
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
