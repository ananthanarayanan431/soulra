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
