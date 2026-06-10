# Authentication, Admin Dashboard & Token Limits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Clerk-based authentication, per-user data scoping, an admin dashboard (user list + login activity + token usage), and per-user LLM token usage limits to Soulra.

**Architecture:** FastAPI backend verifies Clerk JWTs (JWKS) and mirrors users into a local `users` table (role, token_limit, tokens_used). Next.js frontend uses `@clerk/nextjs` for sign-in/up and attaches the session token to API/WS calls. Token usage is captured via LangChain's `get_usage_metadata_callback` and persisted per conversation; an admin-only `/admin` UI surfaces all users, login activity, and usage.

**Tech Stack:** FastAPI, SQLAlchemy (async) + Alembic, PyJWT (JWKS verification), svix (webhook verification), Next.js 16 + `@clerk/nextjs`, Postgres (sqlite for tests).

Spec: `docs/superpowers/specs/2026-06-10-auth-admin-token-limits-design.md`

---

## Task 1: Backend auth dependencies

**Files:**
- Modify: `soulra-backend/pyproject.toml`

- [ ] **Step 1: Add dependencies**

In `pyproject.toml`, in the `dependencies` list (after `"youtube-transcript-api>=0.6"`), add:

```toml
    "pyjwt[crypto]>=2.8",
    "svix>=1.15",
```

- [ ] **Step 2: Sync the environment**

Run: `cd soulra-backend && uv sync`
Expected: completes successfully, `pyjwt` and `svix` (and `cryptography`) appear in `.venv/lib/python3.12/site-packages`.

- [ ] **Step 3: Verify imports**

Run: `.venv/bin/python -c "import jwt, svix, cryptography; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add soulra-backend/pyproject.toml soulra-backend/uv.lock
git commit -m "chore: add pyjwt and svix for Clerk auth"
```

---

## Task 2: Config settings for Clerk + token limits

**Files:**
- Modify: `soulra-backend/soulra/config.py`
- Modify: `soulra-backend/.env.example`
- Modify: `soulra-backend/.env`
- Test: `soulra-backend/tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_config.py`:

```python
def test_clerk_and_token_limit_defaults(monkeypatch):
    from soulra.config import Settings
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://soulra:soulra@localhost:5432/soulra")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("COHERE_API_KEY", "test")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    monkeypatch.delenv("CLERK_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("DEFAULT_TOKEN_LIMIT", raising=False)

    settings = Settings()

    assert settings.clerk_publishable_key == "pk_test_placeholder"
    assert settings.clerk_secret_key == "sk_test_placeholder"
    assert settings.clerk_jwks_url.endswith("/.well-known/jwks.json")
    assert settings.clerk_webhook_secret == "whsec_placeholder"
    assert settings.default_token_limit == 1_000_000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit/test_config.py::test_clerk_and_token_limit_defaults -v`
Expected: FAIL with `AttributeError` (no `clerk_publishable_key` etc.)

- [ ] **Step 3: Add the settings**

In `soulra/config.py`, inside `class Settings`, after `cohere_api_key: str` add:

```python
    clerk_publishable_key: str = "pk_test_placeholder"
    clerk_secret_key: str = "sk_test_placeholder"
    clerk_jwks_url: str = "https://placeholder.clerk.accounts.dev/.well-known/jwks.json"
    clerk_webhook_secret: str = "whsec_placeholder"
    default_token_limit: int = 1_000_000
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit/test_config.py -v`
Expected: PASS (all tests in file)

- [ ] **Step 5: Update env files**

In `soulra-backend/.env.example`, append:

```
CLERK_PUBLISHABLE_KEY=pk_test_placeholder
CLERK_SECRET_KEY=sk_test_placeholder
CLERK_JWKS_URL=https://placeholder.clerk.accounts.dev/.well-known/jwks.json
CLERK_WEBHOOK_SECRET=whsec_placeholder
DEFAULT_TOKEN_LIMIT=1000000
```

In `soulra-backend/.env`, append the same four lines (so local dev runs without crashing before real keys are added).

- [ ] **Step 6: Commit**

```bash
git add soulra-backend/soulra/config.py soulra-backend/.env.example soulra-backend/.env soulra-backend/tests/unit/test_config.py
git commit -m "feat: add Clerk and token-limit config settings"
```

---

## Task 3: User, LoginEvent, TokenUsageLog models + migration

**Files:**
- Create: `soulra-backend/soulra/models/user.py`
- Create: `soulra-backend/migrations/versions/0006_users_auth.py`
- Modify: `soulra-backend/migrations/env.py`
- Modify: `soulra-backend/tests/conftest.py`
- Test: `soulra-backend/tests/unit/test_user_model.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_user_model.py`:

```python
import uuid
import pytest
from sqlalchemy import select
from soulra.models.user import User, LoginEvent, TokenUsageLog


@pytest.mark.asyncio
async def test_user_table_round_trip(test_db):
    user = User(id="user_abc123", email="a@example.com", name="Ann")
    test_db.add(user)
    await test_db.flush()

    row = (await test_db.execute(select(User).where(User.id == "user_abc123"))).scalar_one()
    assert row.email == "a@example.com"
    assert row.role == "user"
    assert row.token_limit == 1_000_000
    assert row.tokens_used == 0


@pytest.mark.asyncio
async def test_login_event_and_usage_log_round_trip(test_db):
    user = User(id="user_abc123", email="a@example.com")
    test_db.add(user)
    await test_db.flush()

    test_db.add(LoginEvent(user_id=user.id, event_type="login"))
    test_db.add(TokenUsageLog(
        id=uuid.uuid4(), user_id=user.id, model="anthropic/claude-sonnet-4-6",
        prompt_tokens=10, completion_tokens=20, total_tokens=30,
    ))
    await test_db.flush()

    events = (await test_db.execute(select(LoginEvent))).scalars().all()
    logs = (await test_db.execute(select(TokenUsageLog))).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "login"
    assert len(logs) == 1
    assert logs[0].total_tokens == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit/test_user_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'soulra.models.user'`

- [ ] **Step 3: Create the User, LoginEvent, TokenUsageLog models**

Create `soulra/models/user.py`:

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import BigInteger, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from soulra.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # Clerk user id
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user", server_default="user")
    token_limit: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1_000_000, server_default="1000000"
    )
    tokens_used: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class LoginEvent(Base):
    __tablename__ = "login_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "signup" | "login"
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class TokenUsageLog(Base):
    __tablename__ = "token_usage_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
```

- [ ] **Step 4: Register the new models in `tests/conftest.py`**

In `tests/conftest.py`, after the existing model imports (`from soulra.models.tradition import Tradition  # noqa: F401`), add:

```python
from soulra.models.user import User, LoginEvent, TokenUsageLog  # noqa: F401
from soulra.models.journal import JournalEntry  # noqa: F401
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit/test_user_model.py -v`
Expected: PASS

- [ ] **Step 6: Register models in `migrations/env.py`**

In `migrations/env.py`, after `import soulra.models.practice       # noqa: F401`, add:

```python
import soulra.models.user           # noqa: F401
import soulra.models.journal        # noqa: F401
```

- [ ] **Step 7: Write the migration**

Create `migrations/versions/0006_users_auth.py`:

```python
"""users, login_events, token_usage_log + user_id on existing tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('token_limit', sa.BigInteger(), nullable=False, server_default='1000000'),
        sa.Column('tokens_used', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'login_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_events_user_id', 'login_events', ['user_id'])
    op.create_index('ix_login_events_created_at', 'login_events', ['created_at'])

    op.create_table(
        'token_usage_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_token_usage_log_user_id', 'token_usage_log', ['user_id'])
    op.create_index('ix_token_usage_log_created_at', 'token_usage_log', ['created_at'])

    # Scope existing tables to a user. No production data exists yet, so these
    # are added as NOT NULL directly (no backfill migration needed).
    for table in ('conversations', 'journal_entries', 'ingest_jobs'):
        op.add_column(table, sa.Column('user_id', sa.String(length=255), nullable=False))
        op.create_foreign_key(
            f'fk_{table}_user_id', table, 'users', ['user_id'], ['id'], ondelete='CASCADE'
        )
        op.create_index(f'ix_{table}_user_id', table, ['user_id'])


def downgrade() -> None:
    for table in ('conversations', 'journal_entries', 'ingest_jobs'):
        op.drop_index(f'ix_{table}_user_id', table_name=table)
        op.drop_constraint(f'fk_{table}_user_id', table, type_='foreignkey')
        op.drop_column(table, 'user_id')

    op.drop_index('ix_token_usage_log_created_at', table_name='token_usage_log')
    op.drop_index('ix_token_usage_log_user_id', table_name='token_usage_log')
    op.drop_table('token_usage_log')

    op.drop_index('ix_login_events_created_at', table_name='login_events')
    op.drop_index('ix_login_events_user_id', table_name='login_events')
    op.drop_table('login_events')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
```

- [ ] **Step 8: Run the full unit test suite to confirm nothing else broke**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit -v`
Expected: PASS (existing tests still green; new model tests pass)

- [ ] **Step 9: Commit**

```bash
git add soulra-backend/soulra/models/user.py soulra-backend/migrations/versions/0006_users_auth.py soulra-backend/migrations/env.py soulra-backend/tests/conftest.py soulra-backend/tests/unit/test_user_model.py
git commit -m "feat: add users, login_events, token_usage_log tables and user_id scoping columns"
```

---

## Task 4: Auth core — JWT verification, current-user dependency, admin guard

**Files:**
- Create: `soulra-backend/soulra/core/auth.py`
- Modify: `soulra-backend/tests/conftest.py`
- Test: `soulra-backend/tests/unit/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_auth.py`:

```python
import time
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
import pytest
from fastapi import HTTPException
from soulra.core import auth as auth_module
from soulra.models.user import User, LoginEvent


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def fake_jwk_client(rsa_keypair, monkeypatch):
    _, public_key = rsa_keypair

    class _FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class _FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return _FakeSigningKey(public_key)

    monkeypatch.setattr(auth_module, "_get_jwk_client", lambda: _FakeJWKClient())


def _make_token(private_key, **claims):
    payload = {"sub": "user_abc123", "email": "a@example.com", "exp": int(time.time()) + 3600}
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_verify_clerk_token_returns_claims(rsa_keypair, fake_jwk_client):
    private_key, _ = rsa_keypair
    token = _make_token(private_key)
    claims = auth_module.verify_clerk_token(token)
    assert claims["sub"] == "user_abc123"
    assert claims["email"] == "a@example.com"


def test_verify_clerk_token_rejects_expired(rsa_keypair, fake_jwk_client):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, exp=int(time.time()) - 10)
    with pytest.raises(HTTPException) as exc_info:
        auth_module.verify_clerk_token(token)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_creates_user_on_first_sight(test_db, rsa_keypair, fake_jwk_client):
    from starlette.requests import Request

    private_key, _ = rsa_keypair
    token = _make_token(private_key)

    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    user = await auth_module.get_current_user(request, test_db)

    assert user.id == "user_abc123"
    assert user.email == "a@example.com"
    assert user.role == "user"
    assert user.token_limit == 1_000_000

    from sqlalchemy import select
    events = (await test_db.execute(select(LoginEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "signup"


@pytest.mark.asyncio
async def test_get_current_user_missing_token_raises_401(test_db):
    from starlette.requests import Request
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})
    with pytest.raises(HTTPException) as exc_info:
        await auth_module.get_current_user(request, test_db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_admin_rejects_non_admin(test_db):
    user = User(id="user_x", email="x@example.com", role="user")
    with pytest.raises(HTTPException) as exc_info:
        await auth_module.require_admin(user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_allows_admin(test_db):
    user = User(id="user_y", email="y@example.com", role="admin")
    result = await auth_module.require_admin(user)
    assert result is user
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit/test_auth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'soulra.core.auth'`

- [ ] **Step 3: Implement `soulra/core/auth.py`**

Create `soulra/core/auth.py`:

```python
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.config import settings
from soulra.database import get_db
from soulra.models.user import LoginEvent, User

LOGIN_EVENT_DEDUPE_WINDOW = timedelta(minutes=30)


@lru_cache
def _get_jwk_client() -> PyJWKClient:
    return PyJWKClient(settings.clerk_jwks_url)


def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk session JWT and return its claims. Raises 401 on failure."""
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return claims


async def _get_or_create_user(
    db: AsyncSession, claims: dict, ip_address: str | None, user_agent: str | None
) -> User:
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    email = claims.get("email") or ""
    name = claims.get("name")
    now = datetime.now(timezone.utc)

    user = await db.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=email,
            name=name,
            role="user",
            token_limit=settings.default_token_limit,
            tokens_used=0,
            created_at=now,
            last_login_at=now,
        )
        db.add(user)
        await db.flush()
        db.add(LoginEvent(
            user_id=user.id, event_type="signup",
            ip_address=ip_address, user_agent=user_agent,
        ))
        return user

    if email and user.email != email:
        user.email = email

    if user.last_login_at is None or now - user.last_login_at > LOGIN_EVENT_DEDUPE_WINDOW:
        db.add(LoginEvent(
            user_id=user.id, event_type="login",
            ip_address=ip_address, user_agent=user_agent,
        ))
    user.last_login_at = now
    return user


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header[len("bearer "):]
    claims = verify_clerk_token(token)
    return await _get_or_create_user(
        db, claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


async def get_current_user_ws(websocket: WebSocket, db: AsyncSession) -> User | None:
    """Like get_current_user but for WS connections (token via ?token= query param)."""
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        claims = verify_clerk_token(token)
        return await _get_or_create_user(
            db, claims,
            ip_address=websocket.client.host if websocket.client else None,
            user_agent=websocket.headers.get("user-agent"),
        )
    except HTTPException:
        return None


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Add shared auth fixtures to `tests/conftest.py`**

These fixtures make every existing endpoint test "authenticated by default" as `test_user`, and provide a second user/client pair for cross-user scoping tests added in Task 8. Add to `tests/conftest.py`, after the existing imports:

```python
from soulra.core.auth import get_current_user
from soulra.models.user import User
```

Then add these fixtures (after the `test_db` fixture):

```python
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
```

Now update the `client` fixture to authenticate as `test_user` by default:

```python
@pytest_asyncio.fixture
async def client(test_db, test_user):
    from soulra.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
```

Finally add an admin client and a second-user client fixture:

```python
@pytest_asyncio.fixture
async def admin_client(test_db, admin_user):
    from soulra.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def other_client(test_db, other_user):
    from soulra.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return other_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
```

- [ ] **Step 6: Run the full test suite**

Run: `cd soulra-backend && .venv/bin/pytest -v`
Expected: PASS — existing tests still pass since `get_current_user` isn't wired into any router yet, and the new fixtures don't break anything unused.

- [ ] **Step 7: Commit**

```bash
git add soulra-backend/soulra/core/auth.py soulra-backend/tests/conftest.py soulra-backend/tests/unit/test_auth.py
git commit -m "feat: add Clerk JWT verification and current-user/admin auth dependencies"
```

---

## Task 5: `/api/v1/me` endpoint + shared pagination schema

**Files:**
- Create: `soulra-backend/soulra/schemas/user.py`
- Create: `soulra-backend/soulra/api/v1/me.py`
- Modify: `soulra-backend/soulra/schemas/responses.py`
- Modify: `soulra-backend/soulra/main.py`
- Test: `soulra-backend/tests/integration/test_me_api.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_me_api.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_get_me_returns_current_user(client, test_user):
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["role"] == "user"
    assert data["token_limit"] == 1_000_000
    assert data["tokens_used"] == 0


@pytest.mark.asyncio
async def test_get_me_requires_auth(test_db):
    """Without the get_current_user override, a real (invalid) token is required."""
    from httpx import AsyncClient, ASGITransport
    from soulra.main import app
    from soulra.database import get_db

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/me")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soulra-backend && .venv/bin/pytest tests/integration/test_me_api.py -v`
Expected: FAIL with 404 (route doesn't exist)

- [ ] **Step 3: Add `PaginatedResponse` to `soulra/schemas/responses.py`**

Add after `SuccessResponse`:

```python
class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 4: Create `soulra/schemas/user.py`**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


class MeOut(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    token_limit: int
    tokens_used: int

    model_config = {"from_attributes": True}


class UserOut(MeOut):
    created_at: datetime
    last_login_at: datetime | None


class LoginEventOut(BaseModel):
    id: uuid.UUID
    user_id: str
    user_email: str
    event_type: str
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenUsageOut(BaseModel):
    id: uuid.UUID
    user_id: str
    user_email: str
    conversation_id: uuid.UUID | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserDetailOut(UserOut):
    recent_logins: list[LoginEventOut]
    recent_usage: list[TokenUsageOut]


class UserUpdate(BaseModel):
    role: str | None = None
    token_limit: int | None = None
```

- [ ] **Step 5: Create `soulra/api/v1/me.py`**

```python
from fastapi import APIRouter, Depends
from soulra.core.auth import get_current_user
from soulra.models.user import User
from soulra.schemas.responses import SuccessResponse
from soulra.schemas.user import MeOut

router = APIRouter(tags=["me"])


@router.get(
    "/me",
    response_model=SuccessResponse[MeOut],
    summary="Get the current authenticated user's profile",
)
async def get_me(user: User = Depends(get_current_user)):
    return SuccessResponse(data=MeOut.model_validate(user))
```

- [ ] **Step 6: Register the router in `soulra/main.py`**

Add the import alongside the other v1 routers:

```python
from soulra.api.v1.me import router as me_router
```

Add the registration alongside the other `app.include_router(...)` calls:

```python
app.include_router(me_router, prefix="/api/v1")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd soulra-backend && .venv/bin/pytest tests/integration/test_me_api.py -v`
Expected: PASS

- [ ] **Step 8: Run full suite**

Run: `cd soulra-backend && .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add soulra-backend/soulra/schemas/user.py soulra-backend/soulra/schemas/responses.py soulra-backend/soulra/api/v1/me.py soulra-backend/soulra/main.py soulra-backend/tests/integration/test_me_api.py
git commit -m "feat: add /api/v1/me endpoint and PaginatedData schema"
```

---

## Task 6: Admin API — users, login activity, token usage

**Files:**
- Create: `soulra-backend/soulra/api/v1/admin.py`
- Modify: `soulra-backend/soulra/main.py`
- Test: `soulra-backend/tests/integration/test_admin_api.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_admin_api.py`:

```python
import pytest
from soulra.models.user import User, LoginEvent, TokenUsageLog


@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(client):
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_users(admin_client, admin_user, test_db, test_user):
    resp = await admin_client.get("/api/v1/admin/users")
    assert resp.status_code == 200
    data = resp.json()["data"]
    emails = {u["email"] for u in data["items"]}
    assert admin_user.email in emails
    assert test_user.email in emails
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_admin_can_update_user_role_and_limit(admin_client, test_db, test_user):
    resp = await admin_client.patch(
        f"/api/v1/admin/users/{test_user.id}",
        json={"role": "admin", "token_limit": 5_000_000},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["role"] == "admin"
    assert data["token_limit"] == 5_000_000


@pytest.mark.asyncio
async def test_admin_get_user_detail_includes_logins_and_usage(admin_client, test_db, test_user):
    test_db.add(LoginEvent(user_id=test_user.id, event_type="login", ip_address="1.2.3.4"))
    test_db.add(TokenUsageLog(
        user_id=test_user.id, model="anthropic/claude-sonnet-4-6",
        prompt_tokens=10, completion_tokens=5, total_tokens=15,
    ))
    await test_db.flush()

    resp = await admin_client.get(f"/api/v1/admin/users/{test_user.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["recent_logins"]) == 1
    assert data["recent_logins"][0]["ip_address"] == "1.2.3.4"
    assert len(data["recent_usage"]) == 1
    assert data["recent_usage"][0]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_admin_get_unknown_user_404(admin_client):
    resp = await admin_client.get("/api/v1/admin/users/user_does_not_exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_can_list_login_events(admin_client, test_db, test_user):
    test_db.add(LoginEvent(user_id=test_user.id, event_type="login"))
    test_db.add(LoginEvent(user_id=test_user.id, event_type="signup"))
    await test_db.flush()

    resp = await admin_client.get("/api/v1/admin/login-events")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2

    resp = await admin_client.get(f"/api/v1/admin/login-events?user_id={test_user.id}")
    assert resp.json()["data"]["total"] == 2


@pytest.mark.asyncio
async def test_admin_can_list_token_usage(admin_client, test_db, test_user):
    test_db.add(TokenUsageLog(
        user_id=test_user.id, model="anthropic/claude-sonnet-4-6",
        prompt_tokens=100, completion_tokens=50, total_tokens=150,
    ))
    await test_db.flush()

    resp = await admin_client.get("/api/v1/admin/usage")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["total_tokens"] == 150
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soulra-backend && .venv/bin/pytest tests/integration/test_admin_api.py -v`
Expected: FAIL with 404s (route doesn't exist)

- [ ] **Step 3: Implement `soulra/api/v1/admin.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.core.auth import require_admin
from soulra.core.logging import logger
from soulra.database import get_db
from soulra.models.user import LoginEvent, TokenUsageLog, User
from soulra.schemas.responses import PaginatedData, SuccessResponse
from soulra.schemas.user import LoginEventOut, TokenUsageOut, UserDetailOut, UserOut, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

RECENT_LIMIT = 20


@router.get("/users", response_model=SuccessResponse[PaginatedData[UserOut]])
async def list_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    rows = (
        await db.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return SuccessResponse(data=PaginatedData(
        items=[UserOut.model_validate(r) for r in rows], total=total, limit=limit, offset=offset,
    ))


@router.get("/users/{user_id}", response_model=SuccessResponse[UserDetailOut])
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logins = (
        await db.execute(
            select(LoginEvent)
            .where(LoginEvent.user_id == user_id)
            .order_by(LoginEvent.created_at.desc())
            .limit(RECENT_LIMIT)
        )
    ).scalars().all()
    usage = (
        await db.execute(
            select(TokenUsageLog)
            .where(TokenUsageLog.user_id == user_id)
            .order_by(TokenUsageLog.created_at.desc())
            .limit(RECENT_LIMIT)
        )
    ).scalars().all()

    detail = UserDetailOut(
        **UserOut.model_validate(user).model_dump(),
        recent_logins=[
            LoginEventOut(**LoginEventOut.model_validate(e).model_dump(exclude={"user_email"}), user_email=user.email)
            for e in logins
        ],
        recent_usage=[
            TokenUsageOut(**TokenUsageOut.model_validate(u).model_dump(exclude={"user_email"}), user_email=user.email)
            for u in usage
        ],
    )
    return SuccessResponse(data=detail)


@router.patch("/users/{user_id}", response_model=SuccessResponse[UserOut])
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = body.model_dump(exclude_unset=True)
    if "role" in changes and changes["role"] not in ("user", "admin"):
        raise HTTPException(status_code=422, detail="role must be 'user' or 'admin'")
    if "token_limit" in changes and changes["token_limit"] < 0:
        raise HTTPException(status_code=422, detail="token_limit must be >= 0")

    for field, value in changes.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    logger.info("admin_user_updated", actor_id=actor.id, target_id=user.id, changes=changes)
    return SuccessResponse(data=UserOut.model_validate(user))


@router.get("/login-events", response_model=SuccessResponse[PaginatedData[LoginEventOut]])
async def list_login_events(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(LoginEvent, User.email).join(User, User.id == LoginEvent.user_id)
    count_stmt = select(func.count()).select_from(LoginEvent)
    if user_id:
        stmt = stmt.where(LoginEvent.user_id == user_id)
        count_stmt = count_stmt.where(LoginEvent.user_id == user_id)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(LoginEvent.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()
    items = [
        LoginEventOut(**LoginEventOut.model_validate(event).model_dump(exclude={"user_email"}), user_email=email)
        for event, email in rows
    ]
    return SuccessResponse(data=PaginatedData(items=items, total=total, limit=limit, offset=offset))


@router.get("/usage", response_model=SuccessResponse[PaginatedData[TokenUsageOut]])
async def list_token_usage(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TokenUsageLog, User.email).join(User, User.id == TokenUsageLog.user_id)
    count_stmt = select(func.count()).select_from(TokenUsageLog)
    if user_id:
        stmt = stmt.where(TokenUsageLog.user_id == user_id)
        count_stmt = count_stmt.where(TokenUsageLog.user_id == user_id)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(TokenUsageLog.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()
    items = [
        TokenUsageOut(**TokenUsageOut.model_validate(log).model_dump(exclude={"user_email"}), user_email=email)
        for log, email in rows
    ]
    return SuccessResponse(data=PaginatedData(items=items, total=total, limit=limit, offset=offset))
```

Note: `LoginEventOut`/`TokenUsageOut` declare `user_email` as a required field but the ORM rows don't have that attribute — `model_validate(event)` would fail on a raw `LoginEvent`/`TokenUsageLog` row directly because `from_attributes` validation requires all fields. The pattern above works around this by validating only the overlapping fields via `.model_dump(exclude={"user_email"})` then re-constructing with `user_email` — but `model_validate` on the raw row will still raise on the missing field before `.model_dump()` can run. Fix this in Step 3a below before running tests.

- [ ] **Step 3a: Fix schema validation for joined rows**

The cleanest fix: make `user_email` optional with a default in both schemas, so `model_validate(row)` succeeds, then override the value. In `soulra/schemas/user.py`, change:

```python
class LoginEventOut(BaseModel):
    id: uuid.UUID
    user_id: str
    user_email: str
    ...
```

to:

```python
class LoginEventOut(BaseModel):
    id: uuid.UUID
    user_id: str
    user_email: str = ""
    ...
```

and similarly for `TokenUsageOut.user_email: str = ""`. Then in `admin.py`, simplify the construction in `list_login_events`, `list_token_usage`, and `get_user` to:

```python
items = [LoginEventOut.model_validate(event, update={"user_email": email}) for event, email in rows]
```

If `model_validate(obj, update=...)` is not supported by the installed Pydantic version, use this equivalent instead everywhere:

```python
out = LoginEventOut.model_validate(event)
out.user_email = email
items.append(out)
```

Use the same `.model_validate(obj); obj_out.user_email = email` pattern in `get_user` for `recent_logins`/`recent_usage` (email is `user.email` there for every row).

- [ ] **Step 4: Register the router in `soulra/main.py`**

```python
from soulra.api.v1.admin import router as admin_router
```
```python
app.include_router(admin_router, prefix="/api/v1")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd soulra-backend && .venv/bin/pytest tests/integration/test_admin_api.py -v`
Expected: PASS

- [ ] **Step 6: Run full suite**

Run: `cd soulra-backend && .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add soulra-backend/soulra/api/v1/admin.py soulra-backend/soulra/schemas/user.py soulra-backend/soulra/main.py soulra-backend/tests/integration/test_admin_api.py
git commit -m "feat: add admin API for user management, login activity, and token usage"
```

---

## Task 7: Clerk webhook — sync user profile/role changes

**Files:**
- Create: `soulra-backend/soulra/api/v1/webhooks.py`
- Modify: `soulra-backend/soulra/main.py`
- Test: `soulra-backend/tests/integration/test_webhooks_api.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_webhooks_api.py`:

```python
import json
import time
import pytest
from svix.webhooks import Webhook
from sqlalchemy import select
from soulra.config import settings
from soulra.models.user import User


def _signed_headers(payload: dict) -> tuple[str, dict]:
    body = json.dumps(payload)
    wh = Webhook(settings.clerk_webhook_secret)
    msg_id = "msg_test123"
    timestamp = str(int(time.time()))
    signature = wh.sign(msg_id=msg_id, timestamp=int(timestamp), data=body)
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": timestamp,
        "svix-signature": signature,
        "content-type": "application/json",
    }
    return body, headers


@pytest.mark.asyncio
async def test_webhook_user_created_syncs_user(test_db):
    from httpx import AsyncClient, ASGITransport
    from soulra.main import app
    from soulra.database import get_db

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        payload = {
            "type": "user.created",
            "data": {
                "id": "user_webhook_1",
                "email_addresses": [{"id": "idn_1", "email_address": "wh@example.com"}],
                "primary_email_address_id": "idn_1",
                "first_name": "Wendy",
                "last_name": "Hook",
                "public_metadata": {},
            },
        }
        body, headers = _signed_headers(payload)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/webhooks/clerk", content=body, headers=headers)
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)

    user = await test_db.get(User, "user_webhook_1")
    assert user is not None
    assert user.email == "wh@example.com"
    assert user.name == "Wendy Hook"


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature(test_db):
    from httpx import AsyncClient, ASGITransport
    from soulra.main import app
    from soulra.database import get_db

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        body = json.dumps({"type": "user.created", "data": {"id": "user_x"}})
        headers = {
            "svix-id": "msg_bad",
            "svix-timestamp": str(int(time.time())),
            "svix-signature": "v1,invalidsignature==",
            "content-type": "application/json",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/webhooks/clerk", content=body, headers=headers)
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_webhook_user_updated_changes_role(test_db, test_user):
    from httpx import AsyncClient, ASGITransport
    from soulra.main import app
    from soulra.database import get_db

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        payload = {
            "type": "user.updated",
            "data": {
                "id": test_user.id,
                "email_addresses": [{"id": "idn_1", "email_address": test_user.email}],
                "primary_email_address_id": "idn_1",
                "first_name": "Updated",
                "last_name": "Name",
                "public_metadata": {"role": "admin"},
            },
        }
        body, headers = _signed_headers(payload)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/webhooks/clerk", content=body, headers=headers)
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)

    await test_db.refresh(test_user)
    assert test_user.name == "Updated Name"
    assert test_user.role == "admin"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soulra-backend && .venv/bin/pytest tests/integration/test_webhooks_api.py -v`
Expected: FAIL with 404 (route doesn't exist)

- [ ] **Step 3: Implement `soulra/api/v1/webhooks.py`**

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from soulra.config import settings
from soulra.core.logging import logger
from soulra.database import get_db
from soulra.models.user import User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _primary_email(data: dict) -> str:
    primary_id = data.get("primary_email_address_id")
    for entry in data.get("email_addresses", []):
        if entry.get("id") == primary_id:
            return entry.get("email_address", "")
    addresses = data.get("email_addresses") or []
    return addresses[0].get("email_address", "") if addresses else ""


def _full_name(data: dict) -> str | None:
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    name = f"{first} {last}".strip()
    return name or None


@router.post("/clerk", include_in_schema=False)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    wh = Webhook(settings.clerk_webhook_secret)
    try:
        payload = wh.verify(body, headers)
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc

    event_type = payload.get("type")
    data = payload.get("data", {})

    if event_type in ("user.created", "user.updated"):
        user_id = data.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user id")

        role = (data.get("public_metadata") or {}).get("role", "user")
        if role not in ("user", "admin"):
            role = "user"

        user = await db.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                email=_primary_email(data),
                name=_full_name(data),
                role=role,
                token_limit=settings.default_token_limit,
                tokens_used=0,
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)
        else:
            user.email = _primary_email(data) or user.email
            user.name = _full_name(data)
            user.role = role
        await db.commit()
        logger.info("clerk_webhook_user_synced", user_id=user_id, event_type=event_type)

    elif event_type == "user.deleted":
        user_id = data.get("id")
        if user_id:
            user = await db.get(User, user_id)
            if user is not None:
                await db.delete(user)
                await db.commit()
                logger.info("clerk_webhook_user_deleted", user_id=user_id)

    else:
        logger.info("clerk_webhook_ignored", event_type=event_type)

    return {"received": True}
```

- [ ] **Step 4: Register the router in `soulra/main.py`**

```python
from soulra.api.v1.webhooks import router as webhooks_router
```
```python
app.include_router(webhooks_router, prefix="/api/v1")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd soulra-backend && .venv/bin/pytest tests/integration/test_webhooks_api.py -v`
Expected: PASS

- [ ] **Step 6: Run full suite**

Run: `cd soulra-backend && .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add soulra-backend/soulra/api/v1/webhooks.py soulra-backend/soulra/main.py soulra-backend/tests/integration/test_webhooks_api.py
git commit -m "feat: add Clerk webhook endpoint for user profile/role sync"
```

---

## Task 8: Scope conversations, journal, and ingest jobs to the current user

**Files:**
- Modify: `soulra-backend/soulra/models/conversation.py`
- Modify: `soulra-backend/soulra/models/journal.py`
- Modify: `soulra-backend/soulra/models/ingest_job.py`
- Modify: `soulra-backend/soulra/api/v1/conversations.py`
- Modify: `soulra-backend/soulra/api/v1/journal.py`
- Modify: `soulra-backend/soulra/api/v1/ingest.py`
- Modify: `soulra-backend/soulra/api/v1/practice.py`
- Modify: `soulra-backend/soulra/services/practice_builder.py`
- Modify: `soulra-backend/soulra/api/websocket.py`
- Modify: `soulra-backend/tests/integration/test_conversations_api.py`
- Modify: `soulra-backend/tests/integration/test_ingest_api.py`
- Test: `soulra-backend/tests/integration/test_scoping.py`

- [ ] **Step 1: Add `user_id` to the `Conversation`, `JournalEntry`, `IngestJob` models**

In `soulra/models/conversation.py`, add the import and column. Change:

```python
from sqlalchemy import ForeignKey, Text, String, TIMESTAMP
```
to:
```python
from sqlalchemy import ForeignKey, Text, String, TIMESTAMP
```
(no change to imports needed — `String` and `ForeignKey` are already imported). Add the column to `Conversation`, right after `id`:

```python
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
```

In `soulra/models/journal.py`, add the same column to `JournalEntry` (right after `id`):

```python
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
```

In `soulra/models/ingest_job.py`, add the same column to `IngestJob` (right after `id`), and add `from sqlalchemy import ForeignKey` to its existing `from sqlalchemy import Text, String, Integer, TIMESTAMP` import:

```python
from sqlalchemy import ForeignKey, Text, String, Integer, TIMESTAMP
```
```python
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
```

- [ ] **Step 2: Write the failing scoping test**

Create `tests/integration/test_scoping.py`:

```python
import pytest
from soulra.models.conversation import Conversation
from soulra.models.journal import JournalEntry
from soulra.models.ingest_job import IngestJob


@pytest.mark.asyncio
async def test_user_cannot_see_another_users_conversation(client, other_client, test_db, test_user, other_user):
    conv = Conversation(thread_id="thread-scoped", situation="my private situation", user_id=other_user.id)
    test_db.add(conv)
    await test_db.flush()

    # owner (other_client) can fetch it
    resp = await other_client.get(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 200

    # a different user gets 404, not the data
    resp = await client.get(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 404

    # list only returns your own
    resp = await client.get("/api/v1/conversations")
    assert resp.json()["data"] == []
    resp = await other_client.get("/api/v1/conversations")
    assert len(resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_journal_entries_are_scoped_per_user(client, other_client, test_db, other_user):
    entry = JournalEntry(text="private reflection", tags=[], user_id=other_user.id)
    test_db.add(entry)
    await test_db.flush()

    resp = await client.get("/api/v1/journal")
    assert resp.json()["data"]["entries"] == []

    resp = await other_client.get("/api/v1/journal")
    assert len(resp.json()["data"]["entries"]) == 1


@pytest.mark.asyncio
async def test_ingest_job_status_is_scoped_per_user(client, other_client, test_db, other_user):
    import uuid
    job = IngestJob(id=uuid.uuid4(), status="done", chunks_created=1, user_id=other_user.id)
    test_db.add(job)
    await test_db.flush()

    resp = await client.get(f"/api/v1/ingest/jobs/{job.id}")
    assert resp.status_code == 404

    resp = await other_client.get(f"/api/v1/ingest/jobs/{job.id}")
    assert resp.status_code == 200
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd soulra-backend && .venv/bin/pytest tests/integration/test_scoping.py -v`
Expected: FAIL — model fields don't exist yet / endpoints don't filter

- [ ] **Step 4: Update `soulra/api/v1/conversations.py`**

Add the imports:

```python
from soulra.core.auth import get_current_user
from soulra.models.user import User
```

Update `list_conversations` to filter and inject `current_user`:

```python
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.action_steps),
            selectinload(Conversation.tradition_cards),
        )
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
```
(rest of the function body unchanged)

Update `get_conversation`:

```python
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.action_steps),
            selectinload(Conversation.tradition_cards),
        )
        .where(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
    )
```
(rest unchanged — the existing `if not row: raise 404` already covers the cross-user case)

Update `regenerate_steps` — add `current_user: User = Depends(get_current_user)` to its signature and add `Conversation.user_id == current_user.id` to its `select(...).where(...)` clause (same pattern as `get_conversation`).

Update `delete_conversation` — add `current_user: User = Depends(get_current_user)` to its signature; view the rest of the function (lines after 155) and add `Conversation.user_id == current_user.id` to whichever `select`/`where` it uses to locate the row before deleting.

- [ ] **Step 5: Update `soulra/api/v1/journal.py`**

Add the imports:

```python
from soulra.core.auth import get_current_user
from soulra.models.user import User
```

Every helper that queries `JournalEntry` (`_tag_counts`, `_tradition_counts`, `_stats`, `_revisit_entry`) needs a `user_id: str` parameter and a `.where(JournalEntry.user_id == user_id)` clause added to each of their queries (for `_tag_counts`, which uses raw SQL, add `WHERE user_id = :user_id` and pass `{"user_id": user_id}` to `db.execute(text(...), {...})`).

Concretely:

```python
async def _tag_counts(db: AsyncSession, user_id: str) -> list[TagCount]:
    rows = await db.execute(
        text(
            "SELECT tag, COUNT(*) AS cnt "
            "FROM journal_entries, unnest(tags) AS t(tag) "
            "WHERE user_id = :user_id "
            "GROUP BY tag ORDER BY cnt DESC"
        ),
        {"user_id": user_id},
    )
    return [TagCount(name=r.tag, count=r.cnt) for r in rows]


async def _tradition_counts(db: AsyncSession, user_id: str) -> list[TagCount]:
    rows = await db.execute(
        select(JournalEntry.tradition, func.count().label("cnt"))
        .where(JournalEntry.tradition.isnot(None), JournalEntry.user_id == user_id)
        .group_by(JournalEntry.tradition)
        .order_by(func.count().desc())
    )
    return [TagCount(name=r.tradition, count=r.cnt) for r in rows]


async def _stats(db: AsyncSession, user_id: str) -> JournalStats:
    total = (
        await db.execute(
            select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == user_id)
        )
    ).scalar_one()

    month_start = datetime(date.today().year, date.today().month, 1, tzinfo=timezone.utc)
    applied_this_month = (
        await db.execute(
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.applied.is_(True))
            .where(JournalEntry.applied_at >= month_start)
            .where(JournalEntry.user_id == user_id)
        )
    ).scalar_one()

    last_applied = (
        await db.execute(
            select(func.max(JournalEntry.applied_at))
            .where(JournalEntry.applied.is_(True))
            .where(JournalEntry.user_id == user_id)
        )
    ).scalar_one()

    last_applied_days_ago: int | None = None
    if last_applied:
        delta = datetime.now(timezone.utc) - last_applied
        last_applied_days_ago = delta.days

    return JournalStats(
        total=total,
        applied_this_month=applied_this_month,
        last_applied_days_ago=last_applied_days_ago,
    )


async def _revisit_entry(db: AsyncSession, user_id: str) -> JournalEntry | None:
    row = (
        await db.execute(
            select(JournalEntry)
            .where(JournalEntry.applied.is_(False), JournalEntry.user_id == user_id)
            .order_by(JournalEntry.saved_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        row = (
            await db.execute(
                select(JournalEntry)
                .where(JournalEntry.user_id == user_id)
                .order_by(JournalEntry.saved_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
    return row
```

Update `list_journal`:

```python
@router.get(
    "/journal",
    response_model=SuccessResponse[JournalData],
    summary="List journal entries",
)
async def list_journal(
    tag: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(JournalEntry).where(JournalEntry.user_id == current_user.id).order_by(JournalEntry.saved_at.desc())
    if tag and tag != "all":
        stmt = stmt.where(tag == any_(JournalEntry.tags))
    entries = (await db.execute(stmt)).scalars().all()

    tag_rows = await _tag_counts(db, current_user.id)
    total = (
        await db.execute(
            select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == current_user.id)
        )
    ).scalar_one()
    all_tag = [TagCount(name="all", count=total)] + tag_rows

    tradition_rows = await _tradition_counts(db, current_user.id)
    stats = await _stats(db, current_user.id)
    revisit = await _revisit_entry(db, current_user.id)

    return SuccessResponse(data=JournalData(
        entries=[JournalEntryOut.model_validate(e) for e in entries],
        stats=stats,
        tag_counts=all_tag,
        tradition_counts=tradition_rows,
        revisit=JournalEntryOut.model_validate(revisit) if revisit else None,
    ))
```

Update `create_journal_entry` to set `user_id` and require auth:

```python
async def create_journal_entry(
    body: CreateJournalEntry,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = JournalEntry(
        text=body.text,
        quote=body.quote,
        tradition=body.tradition,
        author=body.author,
        citation=body.citation,
        analysis=body.analysis,
        tags=body.tags,
        saved_at=datetime.now(timezone.utc),
        conversation_id=body.conversation_id,
        user_id=current_user.id,
    )
```
(rest unchanged)

Update `patch_journal_entry` and `delete_journal_entry` — add `current_user: User = Depends(get_current_user)` to each signature, and add `JournalEntry.user_id == current_user.id` to each `select(JournalEntry).where(...)`.

- [ ] **Step 6: Update `soulra/api/v1/ingest.py`**

Add the imports:

```python
from soulra.core.auth import get_current_user
from soulra.models.user import User
```

Update `_create_job` to accept and set `user_id`:

```python
async def _create_job(db: AsyncSession, filename: str, tradition: str, user_id: str) -> IngestJob:
    job = IngestJob(filename=filename, tradition=tradition, user_id=user_id)
    db.add(job)
    await db.flush()
    await db.commit()
    return job
```

In each of `ingest_pdf`, `ingest_text`, `ingest_url`, `ingest_youtube`: add `current_user: User = Depends(get_current_user)` to the function signature, and change the `await _create_job(db, filename, tradition)` call to `await _create_job(db, filename, tradition, current_user.id)`.

Update `get_ingest_job`:

```python
@router.get("/ingest/jobs/{job_id}", response_model=SuccessResponse[IngestJobResponse])
async def get_ingest_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```
and add `IngestJob.user_id == current_user.id` to its lookup query's `where` clause (read the existing function body around line 239 to match its exact query shape).

- [ ] **Step 7: Thread `user_id` through `websocket.py` and `practice_builder.py`**

In `soulra/services/practice_builder.py`, add a `user_id: str` parameter to `save_conversation_and_create_arc` and set it on the `Conversation(...)` construction:

```python
async def save_conversation_and_create_arc(
    conversation_id: str,
    thread_id: str,
    situation: str,
    clarify_q: str,
    clarify_ans: str,
    tradition_cards_data: list[dict],
    action_steps_data: list[dict],
    user_id: str,
) -> None:
```
and in the `Conversation(...)` construction inside, add `user_id=user_id,`.

In `soulra/api/websocket.py`:

1. Add imports:
```python
from soulra.database import AsyncSessionLocal
from soulra.core.auth import get_current_user_ws
```

2. Right after `await websocket.accept()`, authenticate the connection and close with `1008` (policy violation) if it fails:

```python
    async with AsyncSessionLocal() as auth_db:
        current_user = await get_current_user_ws(websocket, auth_db)
    if current_user is None:
        await websocket.close(code=1008)
        return
```

3. Pass `user_id=current_user.id` into the `save_conversation_and_create_arc(...)` call.

- [ ] **Step 8: Update `soulra/api/v1/practice.py` to scope arcs through their conversation's owner**

Add the imports:

```python
from soulra.core.auth import get_current_user
from soulra.models.user import User
```

Read the rest of `practice.py` (it was only partially viewed) and add `current_user: User = Depends(get_current_user)` to every route, joining `PracticeArc` to `Conversation` and adding `Conversation.user_id == current_user.id` to each lookup `where` clause — `PracticeArc` is created from a `Conversation` (see `practice_builder.py`), so it has a `conversation_id` FK to join through. If any route currently fetches a `PracticeArc` without joining `Conversation`, add `.join(Conversation, Conversation.id == PracticeArc.conversation_id)` to the `select(...)`.

- [ ] **Step 9: Update existing tests that construct `Conversation`/`IngestJob` directly**

In `tests/integration/test_conversations_api.py`, every direct `Conversation(...)` construction needs `user_id=test_user.id` and the test needs the `test_user` fixture. Update:

```python
@pytest.mark.asyncio
async def test_get_conversation_returns_detail(client, test_db, test_user):
    conv = Conversation(
        thread_id="thread-abc",
        situation="I say yes too much.",
        clarify_q="Is this internal?",
        clarify_ans="Yes, internal.",
        user_id=test_user.id,
    )
```

```python
@pytest.mark.asyncio
async def test_delete_conversation_removes_record(client, test_db, test_user):
    conv = Conversation(thread_id="thread-del", situation="test", user_id=test_user.id)
```

```python
@pytest.mark.asyncio
async def test_list_conversations_supports_offset(client, test_db, test_user):
    """GET /conversations must support offset-based pagination."""
    for i in range(3):
        c = Conversation(thread_id=f"thread-offset-{i}", situation=f"situation {i}", user_id=test_user.id)
        test_db.add(c)
```

In `tests/integration/test_ingest_api.py`, update the direct `IngestJob(...)` construction:

```python
@pytest.mark.asyncio
async def test_ingest_job_status_returns_record(client, test_db, test_user):
    from soulra.models.ingest_job import IngestJob
    job = IngestJob(id=uuid.uuid4(), status="done", chunks_created=5, user_id=test_user.id)
```

- [ ] **Step 10: Run the full suite**

Run: `cd soulra-backend && .venv/bin/pytest -v`
Expected: PASS — all existing tests (now authenticated as `test_user` via the `client` fixture default) plus the new `test_scoping.py` tests pass.

- [ ] **Step 11: Commit**

```bash
git add soulra-backend/soulra/models/conversation.py soulra-backend/soulra/models/journal.py soulra-backend/soulra/models/ingest_job.py soulra-backend/soulra/api/v1/conversations.py soulra-backend/soulra/api/v1/journal.py soulra-backend/soulra/api/v1/ingest.py soulra-backend/soulra/api/v1/practice.py soulra-backend/soulra/services/practice_builder.py soulra-backend/soulra/api/websocket.py soulra-backend/tests/integration/test_conversations_api.py soulra-backend/tests/integration/test_ingest_api.py soulra-backend/tests/integration/test_scoping.py
git commit -m "feat: scope conversations, journal entries, and ingest jobs to the authenticated user"
```

---

## Task 9: Token usage accounting and per-user limit enforcement

**Files:**
- Create: `soulra-backend/soulra/services/token_usage.py`
- Modify: `soulra-backend/soulra/api/websocket.py`
- Modify: `soulra-backend/soulra/schemas/websocket.py`
- Test: `soulra-backend/tests/unit/test_token_usage.py`
- Test: `soulra-backend/tests/integration/test_ws_chat.py`

- [ ] **Step 1: Write the failing unit test for the persistence helper**

Create `tests/unit/test_token_usage.py`:

```python
import pytest
from sqlalchemy import select
from soulra.models.user import TokenUsageLog, User
from soulra.services.token_usage import persist_token_usage


@pytest.mark.asyncio
async def test_persist_token_usage_writes_log_and_increments_user(test_db, test_user):
    usage_metadata = {
        "anthropic/claude-sonnet-4-6": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        "anthropic/claude-opus-4-8": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    }

    await persist_token_usage(test_db, user_id=test_user.id, conversation_id=None, usage_metadata=usage_metadata)

    logs = (await test_db.execute(select(TokenUsageLog).where(TokenUsageLog.user_id == test_user.id))).scalars().all()
    assert len(logs) == 2
    assert sum(l.total_tokens for l in logs) == 165

    refreshed = await test_db.get(User, test_user.id)
    assert refreshed.tokens_used == 165


@pytest.mark.asyncio
async def test_persist_token_usage_noop_for_empty_metadata(test_db, test_user):
    await persist_token_usage(test_db, user_id=test_user.id, conversation_id=None, usage_metadata={})

    refreshed = await test_db.get(User, test_user.id)
    assert refreshed.tokens_used == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit/test_token_usage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'soulra.services.token_usage'`

- [ ] **Step 3: Implement `soulra/services/token_usage.py`**

```python
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.models.user import TokenUsageLog, User


async def persist_token_usage(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID | None,
    usage_metadata: dict[str, dict],
) -> int:
    """Write one TokenUsageLog row per model and increment the user's tokens_used.

    Returns the grand total of tokens recorded.
    """
    grand_total = 0
    for model, usage in usage_metadata.items():
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        grand_total += total_tokens
        db.add(TokenUsageLog(
            user_id=user_id,
            conversation_id=conversation_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ))

    if grand_total:
        await db.execute(
            update(User).where(User.id == user_id).values(tokens_used=User.tokens_used + grand_total)
        )

    await db.commit()
    return grand_total
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd soulra-backend && .venv/bin/pytest tests/unit/test_token_usage.py -v`
Expected: PASS

- [ ] **Step 5: Add a `token_limit_exceeded` error code to `schemas/websocket.py`**

Open `soulra/schemas/websocket.py` and confirm `ErrorEvent` has a `code: str` field (it should already, per `ErrorEvent(message=..., code=...)` usages elsewhere). No change needed if so — this step is just verification. If `code` has no default and some `ErrorEvent(...)` calls in `websocket.py` omit it (e.g. `ErrorEvent(message="Internal server error, ref: ...")` in the final `except` block), add `code: str = "INTERNAL_ERROR"` as the field default in `schemas/websocket.py` so existing calls keep working.

- [ ] **Step 6: Wire enforcement + capture into `soulra/api/websocket.py`**

Add imports:

```python
from langchain_core.callbacks.usage import get_usage_metadata_callback
from soulra.services.token_usage import persist_token_usage
```

Right after the `current_user is None` check added in Task 8 Step 7, enforce the limit:

```python
    if current_user.tokens_used >= current_user.token_limit:
        await send(ErrorEvent(
            message="Token usage limit reached. Contact an administrator to increase your limit.",
            code="TOKEN_LIMIT_EXCEEDED",
        ).model_dump())
        await websocket.close()
        return
```

Now wrap the entire existing `try:` block (both phases — clarify and synthesize — everything from `initial_input = make_initial_state(...)` / `config = {"configurable": {"thread_id": thread_id}}` through the final `await send(DoneEvent(...))`) in a single `with get_usage_metadata_callback() as usage_cb:` block, indenting the whole body one level further. `astream_events` takes `config` as its second positional argument, so the callback handler must be merged into that same dict — change the existing `config = {"configurable": {"thread_id": thread_id}}` line to:

```python
        config = {"configurable": {"thread_id": thread_id}, "callbacks": [usage_cb]}
```

Resulting shape:

```python
    with get_usage_metadata_callback() as usage_cb:
        try:
            initial_input = make_initial_state(msg.situation)
            config = {"configurable": {"thread_id": thread_id}, "callbacks": [usage_cb]}
            async for event in graph.astream_events(initial_input, config, version="v2"):
                ...
            # ... rest of existing body unchanged, just re-indented ...
        except Exception:
            ...
```

Then, immediately before `await send(DoneEvent(conversation_id=conv_id).model_dump())`, persist the captured usage:

```python
        async with AsyncSessionLocal() as usage_db:
            await persist_token_usage(
                usage_db,
                user_id=current_user.id,
                conversation_id=uuid.UUID(conv_id) if tradition_cards and action_steps else None,
                usage_metadata=usage_cb.usage_metadata,
            )
```

`tradition_cards` and `action_steps` are the local variables already populated inside the `synthesize` branch (from `output.get("tradition_cards", [])` / `output.get("action_steps", [])`) — `conv_id` is only a real, persisted conversation row when both are non-empty (see `save_conversation_and_create_arc`'s early-return guard), so the FK is only set in that case.

- [ ] **Step 7: Add an integration test for limit enforcement**

In `tests/integration/test_ws_chat.py`, add:

```python
def test_ws_chat_rejects_when_token_limit_exceeded():
    """A user who has already hit their token_limit gets TOKEN_LIMIT_EXCEEDED and the socket closes."""
    import jwt
    import time
    from cryptography.hazmat.primitives.asymmetric import rsa
    from soulra.main import app
    from soulra.api.websocket import set_graph
    from soulra.core import auth as auth_module

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    class _FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class _FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return _FakeSigningKey(public_key)

    auth_module._get_jwk_client.cache_clear()
    original_get_jwk_client = auth_module._get_jwk_client
    auth_module._get_jwk_client = lambda: _FakeJWKClient()

    token = jwt.encode(
        {"sub": "user_over_limit", "email": "over@example.com", "exp": int(time.time()) + 3600},
        private_key, algorithm="RS256",
    )

    # The limit check must run before the graph is touched, but chat_ws checks
    # graph-availability first — provide a mock graph so that check passes
    # and the token-limit check is what actually fires.
    from unittest.mock import MagicMock
    set_graph(MagicMock())

    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # First connection: creates the user with default token_limit via signup flow,
        # then we manually push them over the limit via the admin API isn't available here —
        # instead, directly seed via a DB session through the app's engine.
        import asyncio
        from soulra.database import AsyncSessionLocal
        from soulra.models.user import User

        async def _seed_over_limit_user():
            async with AsyncSessionLocal() as db:
                existing = await db.get(User, "user_over_limit")
                if existing is None:
                    db.add(User(id="user_over_limit", email="over@example.com", token_limit=100, tokens_used=100))
                else:
                    existing.token_limit = 100
                    existing.tokens_used = 100
                await db.commit()

        asyncio.get_event_loop().run_until_complete(_seed_over_limit_user())

        with client.websocket_connect(f"/ws/chat?token={token}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "TOKEN_LIMIT_EXCEEDED"
    finally:
        auth_module._get_jwk_client = original_get_jwk_client
        set_graph(None)
```

Note: this test talks to the real app database (via `AsyncSessionLocal`), not the in-memory `test_db` fixture, because the WS route doesn't go through `get_db` dependency overrides. If `DATABASE_URL` in the test environment doesn't point at a usable Postgres instance, mark this test `@pytest.mark.skipif` based on a quick connectivity check, or (preferred if available) point `AsyncSessionLocal`'s engine at the same SQLite test DB for the duration of the test via `monkeypatch.setattr("soulra.database.AsyncSessionLocal", test_session_factory)` where `test_session_factory` is built from the `test_engine` fixture. Use whichever approach the existing test environment supports — check `tests/integration/test_ws_chat.py`'s existing fixtures for a DB-backed pattern before choosing.

- [ ] **Step 8: Run the WS test file**

Run: `cd soulra-backend && .venv/bin/pytest tests/integration/test_ws_chat.py -v`
Expected: PASS (existing tests still pass; new limit-enforcement test passes)

- [ ] **Step 9: Run full suite**

Run: `cd soulra-backend && .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add soulra-backend/soulra/services/token_usage.py soulra-backend/soulra/api/websocket.py soulra-backend/soulra/schemas/websocket.py soulra-backend/tests/unit/test_token_usage.py soulra-backend/tests/integration/test_ws_chat.py
git commit -m "feat: capture and enforce per-user LLM token usage limits"
```

---

## Task 10: Frontend — install Clerk and add env placeholders

**Files:**
- Modify: `package.json`, `package-lock.json`
- Modify: `.env.local`

- [ ] **Step 1: Install `@clerk/nextjs`**

Run: `cd /Volumes/External/soulra && npm install @clerk/nextjs`
Expected: `package.json` gains `"@clerk/nextjs": "^<version>"` under `dependencies`, `package-lock.json` updates.

- [ ] **Step 2: Add placeholder Clerk env vars**

Append to `.env.local`:

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_placeholder
CLERK_SECRET_KEY=sk_test_placeholder
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/home
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/home
```

- [ ] **Step 3: Verify install**

Run: `cd /Volumes/External/soulra && npm run typecheck`
Expected: passes (no usages yet, but the package resolves)

- [ ] **Step 4: Commit**

```bash
git add package.json package-lock.json .env.local
git commit -m "chore: add @clerk/nextjs dependency and env placeholders"
```

---

## Task 11: Frontend — ClerkProvider, route protection middleware, sign-in/sign-up pages

**Files:**
- Modify: `app/layout.tsx`
- Create: `middleware.ts`
- Create: `app/sign-in/[[...sign-in]]/page.tsx`
- Create: `app/sign-up/[[...sign-up]]/page.tsx`

- [ ] **Step 1: Wrap the app in `<ClerkProvider>`**

In `app/layout.tsx`, add the import:

```tsx
import { ClerkProvider } from "@clerk/nextjs";
```

Wrap the returned `<html>` element in `<ClerkProvider>`:

```tsx
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${cormorant.variable} ${inter.variable} ${jetbrains.variable} ${caveat.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col">{children}</body>
      </html>
    </ClerkProvider>
  );
}
```

- [ ] **Step 2: Create route-protection middleware**

Create `middleware.ts` at the project root (same level as `package.json`):

```ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
```

- [ ] **Step 3: Create sign-in and sign-up pages**

Create `app/sign-in/[[...sign-in]]/page.tsx`:

```tsx
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <SignIn />
    </div>
  );
}
```

Create `app/sign-up/[[...sign-up]]/page.tsx`:

```tsx
import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <SignUp />
    </div>
  );
}
```

- [ ] **Step 4: Verify build**

Run: `cd /Volumes/External/soulra && npm run typecheck && npm run lint`
Expected: both pass

Run: `cd /Volumes/External/soulra && npm run dev` (in background), then visit `http://localhost:3000/home` in a browser.
Expected: redirected to `/sign-in` (Clerk's hosted sign-in form renders — using placeholder keys it may show a Clerk configuration error page instead of a working form; that's expected until real keys are supplied, and confirms middleware + provider wiring is active). Stop the dev server afterward.

- [ ] **Step 5: Commit**

```bash
git add app/layout.tsx middleware.ts "app/sign-in/[[...sign-in]]/page.tsx" "app/sign-up/[[...sign-up]]/page.tsx"
git commit -m "feat: add Clerk provider, route protection middleware, and sign-in/sign-up pages"
```

---

## Task 12: Frontend — attach auth tokens to API and WebSocket calls

**Files:**
- Create: `lib/api-fetch.ts`
- Modify: `lib/api.ts`
- Modify: `hooks/useSoulraChat.ts`

- [ ] **Step 1: Create the authed fetch helper**

Create `lib/api-fetch.ts`:

```ts
// lib/api-fetch.ts
// Wraps `fetch` to attach the current Clerk session token as a Bearer header,
// working in both Server Components/route handlers and Client Components.

declare global {
  interface Window {
    Clerk?: {
      session?: { getToken: () => Promise<string | null> } | null;
    };
  }
}

async function getAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    const { auth } = await import("@clerk/nextjs/server");
    const session = await auth();
    return session.getToken();
  }
  const clerk = window.Clerk;
  if (!clerk?.session) return null;
  return clerk.session.getToken();
}

export async function authedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAuthToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}
```

- [ ] **Step 2: Route every API call in `lib/api.ts` through `authedFetch`**

Add the import at the top of `lib/api.ts`:

```ts
import { authedFetch } from "@/lib/api-fetch";
```

Every call in the file is of the form `fetch(\`${BASE}...\`, ...)`. Replace all occurrences of `` fetch(`${BASE} `` with `` authedFetch(`${BASE} `` (i.e. every call site that hits the backend — there are ~20, all using the `${BASE}` template literal prefix). This is a literal find-and-replace across the file; do not change anything else (URLs, options, error handling stay identical).

- [ ] **Step 3: Verify**

Run: `cd /Volumes/External/soulra && npm run typecheck`
Expected: PASS

Run: `cd /Volumes/External/soulra && grep -c "authedFetch(\`\${BASE}" lib/api.ts` and `grep -c "fetch(\`\${BASE}" lib/api.ts`
Expected: the second count is `0` (no bare `fetch` calls to `${BASE}` remain) and the first count matches the original ~20.

- [ ] **Step 4: Attach the token to the chat WebSocket**

In `hooks/useSoulraChat.ts`, add the import:

```ts
import { useAuth } from "@clerk/nextjs";
```

Inside `useSoulraChat`, add `const { getToken } = useAuth();` after the existing `useRef` line. Replace the `useEffect` body (the block currently spanning lines 116-144) with:

```tsx
  useEffect(() => {
    if (!situation) return;

    let cancelled = false;
    let ws: WebSocket | null = null;

    (async () => {
      const token = await getToken();
      if (cancelled) return;

      const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
      const url = token
        ? `${WS_BASE}/ws/chat?token=${encodeURIComponent(token)}`
        : `${WS_BASE}/ws/chat`;

      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        const msg: WsClientMessage = { type: "start", situation };
        ws!.send(JSON.stringify(msg));
        dispatch({ type: "OPEN" });
      };

      ws.onmessage = (ev: MessageEvent<string>) => {
        try {
          const event = JSON.parse(ev.data) as WsServerEvent;
          dispatch({ type: "EVENT", event });
        } catch {
          // malformed message — ignore
        }
      };

      ws.onerror = () => dispatch({ type: "WS_ERROR" });
    })();

    return () => {
      cancelled = true;
      ws?.close();
      wsRef.current = null;
    };
  }, [situation, getToken]);
```

- [ ] **Step 5: Verify**

Run: `cd /Volumes/External/soulra && npm run typecheck && npm run lint`
Expected: both pass

- [ ] **Step 6: Commit**

```bash
git add lib/api-fetch.ts lib/api.ts hooks/useSoulraChat.ts
git commit -m "feat: attach Clerk session tokens to API and WebSocket requests"
```

---

## Task 13: Frontend — admin dashboard (users, activity, usage)

**Files:**
- Modify: `lib/api.ts`
- Create: `app/admin/layout.tsx`
- Create: `app/admin/users/page.tsx`
- Create: `app/admin/activity/page.tsx`
- Create: `app/admin/usage/page.tsx`
- Modify: `components/layout/Sidebar.tsx`

- [ ] **Step 1: Add admin API client functions to `lib/api.ts`**

Append to `lib/api.ts`:

```ts
export interface MeData {
  id: string;
  email: string;
  name: string | null;
  role: "user" | "admin";
  token_limit: number;
  tokens_used: number;
}

export async function getMe(): Promise<MeData | null> {
  try {
    const res = await authedFetch(`${BASE}/api/v1/me`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()).data as MeData;
  } catch {
    return null;
  }
}

export interface AdminUser extends MeData {
  created_at: string;
  last_login_at: string | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export async function listAdminUsers(limit = 50, offset = 0): Promise<Paginated<AdminUser>> {
  const res = await authedFetch(`${BASE}/api/v1/admin/users?limit=${limit}&offset=${offset}`, { cache: "no-store" });
  if (!res.ok) return { items: [], total: 0, limit, offset };
  return (await res.json()).data as Paginated<AdminUser>;
}

export async function updateAdminUser(
  userId: string,
  body: { role?: "user" | "admin"; token_limit?: number }
): Promise<AdminUser | null> {
  const res = await authedFetch(`${BASE}/api/v1/admin/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) return null;
  return (await res.json()).data as AdminUser;
}

export interface AdminLoginEvent {
  id: string;
  user_id: string;
  user_email: string;
  event_type: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export async function listLoginEvents(limit = 50, offset = 0, userId?: string): Promise<Paginated<AdminLoginEvent>> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (userId) params.set("user_id", userId);
  const res = await authedFetch(`${BASE}/api/v1/admin/login-events?${params}`, { cache: "no-store" });
  if (!res.ok) return { items: [], total: 0, limit, offset };
  return (await res.json()).data as Paginated<AdminLoginEvent>;
}

export interface AdminTokenUsage {
  id: string;
  user_id: string;
  user_email: string;
  conversation_id: string | null;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  created_at: string;
}

export async function listTokenUsage(limit = 50, offset = 0, userId?: string): Promise<Paginated<AdminTokenUsage>> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (userId) params.set("user_id", userId);
  const res = await authedFetch(`${BASE}/api/v1/admin/usage?${params}`, { cache: "no-store" });
  if (!res.ok) return { items: [], total: 0, limit, offset };
  return (await res.json()).data as Paginated<AdminTokenUsage>;
}
```

- [ ] **Step 2: Create the admin layout (role gate)**

Create `app/admin/layout.tsx`:

```tsx
import { redirect } from "next/navigation";
import Link from "next/link";
import { getMe } from "@/lib/api";

const ADMIN_NAV = [
  { href: "/admin/users", label: "Users" },
  { href: "/admin/activity", label: "Login activity" },
  { href: "/admin/usage", label: "Token usage" },
];

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const me = await getMe();
  if (!me || me.role !== "admin") {
    redirect("/home");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-[200px] border-r border-line bg-paper-alt flex-shrink-0 px-4 py-5">
        <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">Admin</div>
        <nav className="flex flex-col gap-1">
          {ADMIN_NAV.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className="px-2.5 py-2 rounded-md text-sm text-ink border border-transparent hover:bg-paper/50"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-6">
          <Link href="/home" className="font-mono text-[10px] text-muted uppercase tracking-widest">
            ← Back to app
          </Link>
        </div>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: Create the users page**

Create `app/admin/users/page.tsx`:

```tsx
import { listAdminUsers } from "@/lib/api";
import { UsersTable } from "./UsersTable";

export default async function AdminUsersPage() {
  const { items, total } = await listAdminUsers(100, 0);

  return (
    <div>
      <h1 className="font-serif text-2xl text-ink mb-1">Users</h1>
      <p className="font-mono text-[11px] text-muted mb-6">{total} total</p>
      <UsersTable users={items} />
    </div>
  );
}
```

Create `app/admin/users/UsersTable.tsx` (client component for the inline edit controls):

```tsx
"use client";
import { useState } from "react";
import { updateAdminUser, type AdminUser } from "@/lib/api";

export function UsersTable({ users: initialUsers }: { users: AdminUser[] }) {
  const [users, setUsers] = useState(initialUsers);
  const [savingId, setSavingId] = useState<string | null>(null);

  async function handleLimitChange(userId: string, value: string) {
    const tokenLimit = Number(value);
    if (!Number.isFinite(tokenLimit) || tokenLimit < 0) return;
    setSavingId(userId);
    const updated = await updateAdminUser(userId, { token_limit: tokenLimit });
    if (updated) {
      setUsers(prev => prev.map(u => (u.id === userId ? updated : u)));
    }
    setSavingId(null);
  }

  async function handleRoleToggle(userId: string, currentRole: "user" | "admin") {
    const role = currentRole === "admin" ? "user" : "admin";
    setSavingId(userId);
    const updated = await updateAdminUser(userId, { role });
    if (updated) {
      setUsers(prev => prev.map(u => (u.id === userId ? updated : u)));
    }
    setSavingId(null);
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left font-mono text-[10px] uppercase tracking-widest text-muted border-b border-line">
          <th className="py-2 pr-4">Email</th>
          <th className="py-2 pr-4">Name</th>
          <th className="py-2 pr-4">Role</th>
          <th className="py-2 pr-4">Joined</th>
          <th className="py-2 pr-4">Last login</th>
          <th className="py-2 pr-4">Tokens used / limit</th>
        </tr>
      </thead>
      <tbody>
        {users.map(u => {
          const pct = u.token_limit > 0 ? Math.min(100, Math.round((u.tokens_used / u.token_limit) * 100)) : 0;
          return (
            <tr key={u.id} className="border-b border-line-soft">
              <td className="py-2 pr-4">{u.email}</td>
              <td className="py-2 pr-4">{u.name ?? "—"}</td>
              <td className="py-2 pr-4">
                <button
                  onClick={() => handleRoleToggle(u.id, u.role)}
                  disabled={savingId === u.id}
                  className="font-mono text-[11px] uppercase tracking-wide border border-line rounded px-2 py-0.5 hover:bg-paper-alt disabled:opacity-50"
                >
                  {u.role}
                </button>
              </td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">
                {new Date(u.created_at).toLocaleDateString()}
              </td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">
                {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "never"}
              </td>
              <td className="py-2 pr-4">
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-line-soft rounded overflow-hidden">
                    <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="font-mono text-[11px] text-muted">{u.tokens_used.toLocaleString()}</span>
                  <span className="font-mono text-[11px] text-muted">/</span>
                  <input
                    type="number"
                    defaultValue={u.token_limit}
                    onBlur={e => handleLimitChange(u.id, e.target.value)}
                    disabled={savingId === u.id}
                    className="w-24 font-mono text-[11px] border border-line rounded px-1 py-0.5 bg-paper"
                  />
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Create the activity page**

Create `app/admin/activity/page.tsx`:

```tsx
import { listLoginEvents } from "@/lib/api";

export default async function AdminActivityPage() {
  const { items, total } = await listLoginEvents(100, 0);

  return (
    <div>
      <h1 className="font-serif text-2xl text-ink mb-1">Login activity</h1>
      <p className="font-mono text-[11px] text-muted mb-6">{total} events</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left font-mono text-[10px] uppercase tracking-widest text-muted border-b border-line">
            <th className="py-2 pr-4">User</th>
            <th className="py-2 pr-4">Event</th>
            <th className="py-2 pr-4">IP address</th>
            <th className="py-2 pr-4">User agent</th>
            <th className="py-2 pr-4">When</th>
          </tr>
        </thead>
        <tbody>
          {items.map(e => (
            <tr key={e.id} className="border-b border-line-soft">
              <td className="py-2 pr-4">{e.user_email}</td>
              <td className="py-2 pr-4 font-mono text-[11px] uppercase">{e.event_type}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{e.ip_address ?? "—"}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted truncate max-w-[240px]">{e.user_agent ?? "—"}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{new Date(e.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 5: Create the usage page**

Create `app/admin/usage/page.tsx`:

```tsx
import { listTokenUsage } from "@/lib/api";

export default async function AdminUsagePage() {
  const { items, total } = await listTokenUsage(100, 0);

  return (
    <div>
      <h1 className="font-serif text-2xl text-ink mb-1">Token usage</h1>
      <p className="font-mono text-[11px] text-muted mb-6">{total} entries</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left font-mono text-[10px] uppercase tracking-widest text-muted border-b border-line">
            <th className="py-2 pr-4">User</th>
            <th className="py-2 pr-4">Model</th>
            <th className="py-2 pr-4">Prompt</th>
            <th className="py-2 pr-4">Completion</th>
            <th className="py-2 pr-4">Total</th>
            <th className="py-2 pr-4">When</th>
          </tr>
        </thead>
        <tbody>
          {items.map(u => (
            <tr key={u.id} className="border-b border-line-soft">
              <td className="py-2 pr-4">{u.user_email}</td>
              <td className="py-2 pr-4 font-mono text-[11px]">{u.model}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{u.prompt_tokens.toLocaleString()}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{u.completion_tokens.toLocaleString()}</td>
              <td className="py-2 pr-4 font-mono text-[11px]">{u.total_tokens.toLocaleString()}</td>
              <td className="py-2 pr-4 font-mono text-[11px] text-muted">{new Date(u.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 6: Add a conditional "Admin" link to the sidebar**

In `components/layout/Sidebar.tsx`, add the import:

```tsx
import { useEffect, useState } from "react";
import { listConversations, formatRelativeDate, getMe } from "@/lib/api";
import type { Conversation, MeData } from "@/lib/api";
```

(merge with the existing `useEffect, useState` import — don't duplicate the import line). Add state and a fetch alongside the existing `conversations` state:

```tsx
  const [me, setMe] = useState<MeData | null>(null);

  useEffect(() => {
    getMe().then(setMe).catch(() => {});
  }, []);
```

Then, after the closing `</nav>` of the main nav list, conditionally render an admin link:

```tsx
      {me?.role === "admin" && (
        <div className="px-4 mt-1">
          <Link
            href="/admin/users"
            className="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-ink border border-transparent hover:bg-paper/50"
          >
            <span className="font-mono text-muted w-3 text-[11px]">▲</span>
            <span>Admin</span>
          </Link>
        </div>
      )}
```

- [ ] **Step 7: Verify**

Run: `cd /Volumes/External/soulra && npm run typecheck && npm run lint`
Expected: both pass

- [ ] **Step 8: Commit**

```bash
git add lib/api.ts app/admin components/layout/Sidebar.tsx
git commit -m "feat: add admin dashboard for users, login activity, and token usage"
```

---

## Task 14: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend test suite**

Run: `cd soulra-backend && .venv/bin/pytest -v`
Expected: all tests PASS

- [ ] **Step 2: Run backend lint/type checks**

Run: `cd soulra-backend && .venv/bin/ruff check . && .venv/bin/mypy soulra`
Expected: no new errors introduced by this change (pre-existing issues unrelated to auth/admin/token work are out of scope)

- [ ] **Step 3: Run frontend checks**

Run: `cd /Volumes/External/soulra && npm run typecheck && npm run lint && npm run build`
Expected: all PASS

- [ ] **Step 4: Manual smoke test (requires Docker/Postgres running)**

Run: `cd soulra-backend && docker-compose up -d` then `make` target or `uvicorn soulra.main:app --reload` to start the backend, and `cd /Volumes/External/soulra && npm run dev` for the frontend. With placeholder Clerk keys, sign-in/sign-up will show a Clerk configuration warning instead of a working form — this confirms the integration points (middleware redirect, ClerkProvider, `/api/v1/me` 401 without a token) are wired correctly. Document for the user that real Clerk keys (set in `.env.local` and `soulra-backend/.env`) are required for an end-to-end login flow.

- [ ] **Step 5: Update `.env.example` (frontend) if one exists, or note required env vars in README**

If `/Volumes/External/soulra/.env.example` doesn't exist, create it mirroring `.env.local` (without secrets — use placeholders), so the next developer knows which env vars are required:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/home
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/home
```

- [ ] **Step 6: Commit**

```bash
git add .env.example
git commit -m "docs: document required frontend env vars for Clerk"
```

- [ ] **Step 7: Note deferred follow-up — webhook rate limiting**

Spec Section 8 lists rate limiting on `/api/v1/webhooks/clerk` and other auth-sensitive endpoints as a nice-to-have. Adding `slowapi` is a separate dependency + middleware change with its own testing surface, so it is deferred to a follow-up task rather than bundled here. No action needed now — just don't forget to raise it as a follow-up when handing off this plan.
