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
