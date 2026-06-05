import asyncio
import hashlib
import io
import ipaddress
import socket
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from soulra.config import settings
from soulra.core.logging import logger
from soulra.database import get_db
from soulra.models.ingest_job import IngestJob
from soulra.schemas.ingest import IngestJobResponse
from soulra.schemas.responses import SuccessResponse

router = APIRouter(tags=["ingest"])

_PRIVATE_HOSTNAMES = {"localhost", "0.0.0.0"}


async def _check_url_not_ssrf(url: str) -> None:
    """Raise HTTPException(400) if url is not a safe public http/https URL."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: missing host")
    if hostname in _PRIVATE_HOSTNAMES:
        raise HTTPException(status_code=400, detail="URL host is not allowed")
    # If host is a literal IP, check it directly
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
            raise HTTPException(status_code=400, detail="URL resolves to a disallowed address")
        return
    except ValueError:
        pass  # not a literal IP — resolve it
    loop = asyncio.get_event_loop()
    try:
        infos = await loop.run_in_executor(None, socket.getaddrinfo, hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Invalid URL: cannot resolve host")
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
                raise HTTPException(status_code=400, detail="URL resolves to a disallowed address")
        except ValueError:
            pass


async def _update_job_status(session, job_id: uuid.UUID, **fields) -> None:
    """Update IngestJob fields inside an existing session."""
    stmt = select(IngestJob).where(IngestJob.id == job_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is not None:
        for k, v in fields.items():
            setattr(row, k, v)
        await session.commit()


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
                        actual_content = resp.content
                else:
                    actual_content = file_content
                result = await pipeline.run(
                    file=io.BytesIO(actual_content),
                    filename=filename,
                    metadata=metadata,
                )
                await _update_job_status(
                    session, job_id,
                    status="done",
                    chunks_created=result["chunks_created"],
                    completed_at=datetime.now(timezone.utc),
                )
            except Exception as e:
                logger.exception("ingestion_task_failed", job_id=str(job_id))
                await _update_job_status(
                    session, job_id,
                    status="failed",
                    error="Ingestion failed due to an internal error",
                )
        await eng.dispose()
    except Exception as e:
        logger.error("ingestion_task_setup_failed", job_id=str(job_id), error=str(e))
        try:
            _eng = create_async_engine(settings.database_url)
            _sf = async_sessionmaker(_eng, expire_on_commit=False)
            async with _sf() as _session:
                await _update_job_status(
                    _session, job_id,
                    status="failed",
                    error="Task setup failed due to an internal error",
                )
            await _eng.dispose()
        except Exception as _inner:
            logger.error("ingestion_task_status_update_failed", job_id=str(job_id), error=str(_inner))


@router.post("/ingest/pdf", status_code=202, response_model=SuccessResponse[IngestJobResponse])
async def ingest_pdf(
    request: Request,
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

    max_bytes = settings.max_upload_mb * 1024 * 1024
    # Reject before reading if Content-Length header is already too large
    cl = request.headers.get("content-length")
    if cl and int(cl) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    content = await file.read()
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
    await _check_url_not_ssrf(url)
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
