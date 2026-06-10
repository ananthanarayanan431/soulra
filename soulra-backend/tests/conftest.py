import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from soulra.core.auth import get_current_user
from soulra.database import Base, get_db
from soulra.models.conversation import Conversation, ActionStep  # noqa: F401
from soulra.models.ingest_job import IngestJob  # noqa: F401
from soulra.models.tradition import Tradition  # noqa: F401
from soulra.models.tradition_card import TraditionCard  # noqa: F401
from soulra.models.user import User, LoginEvent, TokenUsageLog  # noqa: F401
from soulra.models.journal import JournalEntry  # noqa: F401

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
async def test_user(test_db):
    user = User(id="user_test_primary", email="primary@example.com", role="user")
    test_db.add(user)
    await test_db.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(test_db):
    user = User(id="user_test_admin", email="admin@example.com", role="admin")
    test_db.add(user)
    await test_db.flush()
    return user


@pytest_asyncio.fixture
async def other_user(test_db):
    user = User(id="user_test_other", email="other@example.com", role="user")
    test_db.add(user)
    await test_db.flush()
    return user


async def _make_client(test_db, user):
    """Build an AsyncClient that authenticates as `user` via an X-Test-User-Id header.

    Using a header (read per-request) rather than baking the user into the
    dependency override allows multiple clients (e.g. `client` and
    `other_client`) authenticated as different users to be used within the
    same test, since `app.dependency_overrides` is a single shared dict.
    """
    from soulra.main import app
    from fastapi import Request

    async def override_get_db():
        yield test_db

    async def override_get_current_user(request: Request):
        user_id = request.headers.get("x-test-user-id")
        if user_id == user.id:
            return user
        result = await test_db.get(type(user), user_id)
        return result if result is not None else user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Test-User-Id": user.id},
    ) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def client(test_db, test_user):
    async for c in _make_client(test_db, test_user):
        yield c


@pytest_asyncio.fixture
async def admin_client(test_db, admin_user):
    async for c in _make_client(test_db, admin_user):
        yield c


@pytest_asyncio.fixture
async def other_client(test_db, other_user):
    async for c in _make_client(test_db, other_user):
        yield c


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
