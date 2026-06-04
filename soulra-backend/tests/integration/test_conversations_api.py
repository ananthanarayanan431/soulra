import pytest
import uuid
from soulra.models.conversation import Conversation, ActionStep


@pytest.mark.asyncio
async def test_list_conversations_returns_empty(client):
    resp = await client.get("/api/v1/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"] == []


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
    assert data["success"] is True
    assert data["data"]["situation"] == "I say yes too much."
    assert data["data"]["clarify_q"] == "Is this internal?"


@pytest.mark.asyncio
async def test_get_conversation_returns_404_for_unknown(client):
    resp = await client.get(f"/api/v1/conversations/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_removes_record(client, test_db):
    conv = Conversation(thread_id="thread-del", situation="test")
    test_db.add(conv)
    await test_db.flush()

    resp = await client.delete(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/conversations/{conv.id}")
    assert resp.status_code == 404
