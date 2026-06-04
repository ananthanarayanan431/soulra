import pytest
import io
import uuid
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_ingest_pdf_returns_job_id(client):
    with patch("app.api.v1.ingest._get_pipeline") as mock_pipeline_factory:
        mock_pipeline = mock_pipeline_factory.return_value
        mock_pipeline.run = AsyncMock(return_value={"chunks_created": 5, "tokens_used": 0})

        resp = await client.post(
            "/api/v1/ingest/pdf",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 mock"), "application/pdf")},
            data={
                "tradition": "stoic",
                "author": "Marcus Aurelius",
                "source": "Meditations",
                "era": "ancient",
            },
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_ingest_pdf_rejects_non_pdf(client):
    resp = await client.post(
        "/api/v1/ingest/pdf",
        files={"file": ("test.txt", io.BytesIO(b"text"), "text/plain")},
        data={"tradition": "stoic", "author": "Marcus", "source": "Med", "era": "ancient"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_job_status_not_found(client):
    resp = await client.get(f"/api/v1/ingest/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ingest_text_returns_job_id(client):
    with patch("app.api.v1.ingest._get_pipeline") as mock_pipeline_factory:
        mock_pipeline_factory.return_value.run = AsyncMock(return_value={"chunks_created": 3, "tokens_used": 0})
        resp = await client.post(
            "/api/v1/ingest/text",
            data={
                "content": "The Stoic tradition teaches equanimity.",
                "tradition": "stoic",
                "author": "Marcus Aurelius",
                "source": "Meditations",
                "era": "ancient",
            },
        )
    assert resp.status_code == 202
    assert "job_id" in resp.json()


@pytest.mark.asyncio
async def test_ingest_url_returns_job_id(client):
    resp = await client.post(
        "/api/v1/ingest/url",
        data={
            "url": "https://example.com/wisdom.txt",
            "tradition": "stoic",
            "author": "Marcus Aurelius",
            "source": "Online",
            "era": "ancient",
        },
    )
    # URL fetch happens in background — just check 202 returned immediately
    assert resp.status_code == 202
    assert "job_id" in resp.json()


@pytest.mark.asyncio
async def test_ingest_job_status_returns_record(client, test_db):
    from app.models.ingest_job import IngestJob
    job = IngestJob(id=uuid.uuid4(), status="done", chunks_created=5)
    test_db.add(job)
    await test_db.flush()

    resp = await client.get(f"/api/v1/ingest/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
