import pytest
from soulra.models.conversation import Conversation
from soulra.models.journal import JournalEntry
from soulra.models.ingest_job import IngestJob


@pytest.mark.asyncio
async def test_user_cannot_see_another_users_conversation(
    client, other_client, test_db, test_user, other_user
):
    conv = Conversation(
        thread_id="thread-scoped", situation="my private situation", user_id=other_user.id
    )
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
