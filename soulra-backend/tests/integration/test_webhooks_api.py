import json
import time
from datetime import datetime, timezone
import pytest
from svix.webhooks import Webhook
from soulra.config import settings
from soulra.models.user import User


def _signed_headers(payload: dict) -> tuple[str, dict]:
    body = json.dumps(payload)
    wh = Webhook(settings.clerk_webhook_secret)
    msg_id = "msg_test123"
    now = int(time.time())
    timestamp = str(now)
    signature = wh.sign(
        msg_id=msg_id, timestamp=datetime.fromtimestamp(now, tz=timezone.utc), data=body
    )
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

    user = await test_db.get(User, "user_x")
    assert user is None


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
