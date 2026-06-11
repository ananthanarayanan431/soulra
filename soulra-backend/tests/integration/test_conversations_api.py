import pytest
import uuid
from soulra.models.conversation import Conversation


@pytest.mark.asyncio
async def test_list_conversations_returns_empty(client):
    resp = await client.get("/api/v1/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"] == []


@pytest.mark.asyncio
async def test_get_conversation_returns_detail(client, test_db, test_user):
    conv = Conversation(
        thread_id="thread-abc",
        situation="I say yes too much.",
        clarify_q="Is this internal?",
        clarify_ans="Yes, internal.",
        user_id=test_user.id,
    )
    test_db.add(conv)
    await test_db.flush()

    resp = await client.get(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["situation"] == "I say yes too much."
    assert data["data"]["clarify_q"] == "Is this internal?"


@pytest.mark.asyncio
async def test_get_conversation_returns_404_for_unknown(client):
    resp = await client.get(f"/api/v1/conversations/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_removes_record(client, test_db, test_user):
    conv = Conversation(thread_id="thread-del", situation="test", user_id=test_user.id)
    test_db.add(conv)
    await test_db.flush()

    resp = await client.delete(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_conversations_supports_offset(client, test_db, test_user):
    """GET /conversations must support offset-based pagination."""
    # Create 3 conversations
    for i in range(3):
        c = Conversation(
            thread_id=f"thread-offset-{i}", situation=f"situation {i}", user_id=test_user.id
        )
        test_db.add(c)
    await test_db.flush()

    resp_page1 = await client.get("/api/v1/conversations?limit=2&offset=0")
    resp_page2 = await client.get("/api/v1/conversations?limit=2&offset=2")

    assert resp_page1.status_code == 200
    assert resp_page2.status_code == 200
    page1_ids = [c["thread_id"] for c in resp_page1.json()["data"]]
    page2_ids = [c["thread_id"] for c in resp_page2.json()["data"]]
    # Pages should not overlap
    assert not set(page1_ids) & set(page2_ids), "Pagination overlap detected"


@pytest.mark.asyncio
async def test_list_conversations_limit_requires_ge1(client):
    """limit=0 must be rejected with 422."""
    resp = await client.get("/api/v1/conversations?limit=0")
    assert resp.status_code == 422
