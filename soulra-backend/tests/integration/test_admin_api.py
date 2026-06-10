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
