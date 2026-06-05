import uuid
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from soulra.database import get_db
from soulra.models.ingest_job import IngestJob
from soulra.schemas.ingest import IngestJobResponse
from soulra.schemas.responses import SuccessResponse
from soulra.config import settings
from soulra.core.logging import logger

router = APIRouter(tags=["ingest"])


def _get_pipeline():
    from soulra.dependencies import get_vectorstore
    from soulra.services.ingestion.pipeline import IngestionPipeline
    return IngestionPipeline(vectorstore=get_vectorstore())


async def _run_ingestion_task(
    file_content: bytes | None,
    filename: str,
    metadata: dict,
    job_id: uuid.UUID,
    source_url: str | None = None,
):
    try:
        eng = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(eng, expire_on_commit=False)
        pipeline = _get_pipeline()
        async with session_factory() as session:
            try:
                if source_url:
                    import httpx
                    async with httpx.AsyncClient() as http_client:
                        resp = await http_client.get(source_url, timeout=30)
                        resp.raise_for_status()
                        actual_content = resp.text.encode()
                else:
                    actual_content = file_content
                result = await pipeline.run(
                    file=io.BytesIO(actual_content),
                    filename=filename,
                    metadata=metadata,
                )
                stmt = select(IngestJob).where(IngestJob.id == job_id)
                row = (await session.execute(stmt)).scalar_one_or_none()
                if row is not None:
                    row.status = "done"
                    row.chunks_created = result["chunks_created"]
                    row.completed_at = datetime.now(timezone.utc)
                    await session.commit()
            except Exception as e:
                stmt = select(IngestJob).where(IngestJob.id == job_id)
                row = (await session.execute(stmt)).scalar_one_or_none()
                if row is not None:
                    row.status = "failed"
                    row.error = str(e)
                    await session.commit()
                logger.error("ingestion_task_failed", job_id=str(job_id), error=str(e))
        await eng.dispose()
    except Exception as e:
        logger.error("ingestion_task_setup_failed", job_id=str(job_id), error=str(e))
        # Best-effort: mark job as failed so callers aren't stuck polling 'processing'
        try:
            _eng = create_async_engine(settings.database_url)
            _sf = async_sessionmaker(_eng, expire_on_commit=False)
            async with _sf() as _session:
                _stmt = select(IngestJob).where(IngestJob.id == job_id)
                _row = (await _session.execute(_stmt)).scalar_one_or_none()
                if _row is not None:
                    _row.status = "failed"
                    _row.error = f"Task setup failed: {e}"
                    await _session.commit()
            await _eng.dispose()
        except Exception as _inner:
            logger.error("ingestion_task_status_update_failed", job_id=str(job_id), error=str(_inner))


@router.post("/ingest/pdf", status_code=202, response_model=SuccessResponse[IngestJobResponse])
async def ingest_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit"
        )
    job = IngestJob(filename=file.filename, tradition=tradition)
    db.add(job)
    await db.flush()
    await db.commit()

    background_tasks.add_task(
        _run_ingestion_task,
        content,
        file.filename or "upload.pdf",
        {"tradition": tradition, "author": author, "source": source, "era": era},
        job.id,
    )
    return SuccessResponse(data=IngestJobResponse(job_id=job.id, status="processing", filename=file.filename))


@router.post("/ingest/text", status_code=202, response_model=SuccessResponse[IngestJobResponse])
async def ingest_text(
    background_tasks: BackgroundTasks,
    content: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    db: AsyncSession = Depends(get_db),
):
    import hashlib
    filename = f"text-{hashlib.md5(content[:50].encode()).hexdigest()[:8]}.txt"
    job = IngestJob(filename=filename, tradition=tradition)
    db.add(job)
    await db.flush()
    await db.commit()
    background_tasks.add_task(
        _run_ingestion_task,
        content.encode(),
        filename,
        {"tradition": tradition, "author": author, "source": source, "era": era},
        job.id,
    )
    return SuccessResponse(data=IngestJobResponse(job_id=job.id, status="processing", filename=filename))


@router.post("/ingest/url", status_code=202, response_model=SuccessResponse[IngestJobResponse])
async def ingest_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    db: AsyncSession = Depends(get_db),
):
    job = IngestJob(filename=url, tradition=tradition)
    db.add(job)
    await db.flush()
    await db.commit()
    background_tasks.add_task(
        _run_ingestion_task,
        None,
        url,
        {"tradition": tradition, "author": author, "source": source, "era": era},
        job.id,
        url,
    )
    return SuccessResponse(data=IngestJobResponse(job_id=job.id, status="processing", filename=url))


@router.get("/ingest/jobs/{job_id}", response_model=SuccessResponse[IngestJobResponse])
async def get_ingest_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(IngestJob).where(IngestJob.id == job_id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return SuccessResponse(data=IngestJobResponse(
        job_id=row.id,
        status=row.status,
        filename=row.filename,
        chunks_created=row.chunks_created,
        tokens_used=row.tokens_used,
        error=row.error,
    ))
