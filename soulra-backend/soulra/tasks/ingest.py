"""
Celery task for PDF / text / URL ingestion.

Design notes:
- Tasks are *synchronous* Celery tasks that call asyncio.run() to drive
  the async ingestion pipeline.  Each invocation creates and disposes its
  own asyncpg pool — acceptable for heavy, long-running ingestion work.
- File bytes are staged in Redis (not in the task message) to avoid
  serialising multi-megabyte blobs through the broker.
- Retry on transient failure (up to 3 attempts, exponential back-off).
  DB + Redis are updated to "failed" only after all retries are exhausted.
"""

import asyncio
import io
import json
import uuid
from datetime import datetime, timezone
from typing import cast

import redis as sync_redis

from soulra.celery_app import celery_app
from soulra.config import settings
from soulra.core.logging import logger


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sync_redis() -> sync_redis.Redis:
    return sync_redis.from_url(settings.redis_url, decode_responses=False)


def _cache_job(r: sync_redis.Redis, job_id: str, data: dict, ttl: int = 3600) -> None:
    r.setex(f"job:{job_id}", ttl, json.dumps(data))


# ── Async helpers (run inside asyncio.run()) ─────────────────────────────────


async def _run_pipeline(
    filename: str,
    metadata: dict,
    source_url: str | None,
    file_bytes: bytes | None,
) -> dict:
    """Executes the ingestion pipeline. Returns result. Raises on failure."""
    import httpx
    from langchain_postgres import PGVector
    from soulra.services.ingestion.pipeline import IngestionPipeline
    from soulra.services.llm.factory import make_embeddings

    vs = PGVector(
        embeddings=make_embeddings(),
        collection_name="wisdom_passages",
        connection=settings.database_url,
        async_mode=True,
        create_extension=False,
    )
    pipeline = IngestionPipeline(vectorstore=vs)

    content: bytes
    if source_url:
        async with httpx.AsyncClient() as client:
            resp = await client.get(source_url, timeout=30)
            resp.raise_for_status()
            content = resp.content
    elif file_bytes is not None:
        content = file_bytes
    else:
        raise ValueError("No source_url or file_bytes provided")

    return await pipeline.run(
        file=io.BytesIO(content),
        filename=filename,
        metadata=metadata,
    )


async def _update_db(job_id: str, **fields) -> None:
    """Updates an IngestJob row. Creates and disposes its own engine."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from soulra.models.ingest_job import IngestJob

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            row = (
                await session.execute(select(IngestJob).where(IngestJob.id == uuid.UUID(job_id)))
            ).scalar_one_or_none()
            if row is not None:
                for k, v in fields.items():
                    setattr(row, k, v)
                await session.commit()
    finally:
        await engine.dispose()


# ── Celery task ──────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="soulra.tasks.ingest.run_ingest",
    max_retries=3,
    acks_late=True,
)
def run_ingest(
    self,
    job_id: str,
    filename: str,
    metadata: dict,
    source_url: str | None = None,
    upload_key: str | None = None,
) -> dict:
    """
    Run the ingestion pipeline for a single document.

    Args:
        job_id:     IngestJob UUID string.
        filename:   Original filename (used for routing to PDF vs text parser).
        metadata:   Tradition/author/source/era dict stored with each chunk.
        source_url: If set, worker fetches the file from this URL.
        upload_key: Redis key holding raw file bytes (for PDF / text uploads).
    """
    attempt = self.request.retries + 1
    logger.info("ingest_task_started", job_id=job_id, attempt=attempt)
    r = _sync_redis()

    # Fetch staged file bytes from Redis.
    file_bytes: bytes | None = None
    if upload_key:
        file_bytes = cast(bytes | None, r.get(upload_key))
        if file_bytes is None:
            logger.error("ingest_upload_expired", job_id=job_id)
            asyncio.run(
                _update_db(job_id, status="failed", error="Upload expired before processing")
            )
            _cache_job(r, job_id, {"status": "failed", "error": "Upload expired"}, ttl=600)
            return {"status": "failed"}

    try:
        result = asyncio.run(_run_pipeline(filename, metadata, source_url, file_bytes))
        asyncio.run(
            _update_db(
                job_id,
                status="done",
                chunks_created=result["chunks_created"],
                tokens_used=result["tokens_used"],
                completed_at=datetime.now(timezone.utc),
            )
        )
        _cache_job(
            r,
            job_id,
            {
                "status": "done",
                "chunks_created": result["chunks_created"],
                "tokens_used": result["tokens_used"],
            },
        )
        if upload_key:
            r.delete(upload_key)
        logger.info("ingest_task_done", job_id=job_id, **result)
        return result

    except Exception as exc:
        logger.warning(
            "ingest_task_failed",
            job_id=job_id,
            attempt=attempt,
            error=str(exc),
        )
        is_last = self.request.retries >= self.max_retries
        if not is_last:
            raise self.retry(exc=exc, countdown=30 * (2**self.request.retries))

        # All retries exhausted — persist failure.
        asyncio.run(_update_db(job_id, status="failed", error="Ingestion failed after retries"))
        _cache_job(
            r, job_id, {"status": "failed", "error": "Ingestion failed after retries"}, ttl=600
        )
        if upload_key:
            r.delete(upload_key)
        logger.error("ingest_task_exhausted", job_id=job_id)
        return {"status": "failed"}
