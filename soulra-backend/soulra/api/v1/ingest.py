import hashlib
import ipaddress
import socket
import uuid
from asyncio import get_event_loop
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.config import settings
from soulra.core.logging import logger
from soulra.database import get_db
from soulra.models.ingest_job import IngestJob
from soulra.schemas.ingest import IngestJobResponse
from soulra.schemas.responses import SuccessResponse
from soulra.services import cache
from soulra.tasks.ingest import run_ingest

router = APIRouter(tags=["ingest"])

_PRIVATE_HOSTNAMES = {"localhost", "0.0.0.0"}


async def _check_url_not_ssrf(url: str) -> None:
    """Raise 400 if url is not a safe public http/https URL."""
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
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
            raise HTTPException(status_code=400, detail="URL resolves to a disallowed address")
        return
    except ValueError:
        pass
    loop = get_event_loop()
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


async def _create_job(db: AsyncSession, filename: str, tradition: str) -> IngestJob:
    job = IngestJob(filename=filename, tradition=tradition)
    db.add(job)
    await db.flush()
    await db.commit()
    return job


def _dispatch(job: IngestJob, filename: str, metadata: dict, **kwargs) -> None:
    """Enqueue the Celery ingest task and log the task ID."""
    task = run_ingest.delay(
        job_id=str(job.id),
        filename=filename,
        metadata=metadata,
        **kwargs,
    )
    logger.info("ingest_task_queued", job_id=str(job.id), task_id=task.id)


@router.post("/ingest/pdf", status_code=202, response_model=SuccessResponse[IngestJobResponse])
async def ingest_pdf(
    request: Request,
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
    cl = request.headers.get("content-length")
    if cl and int(cl) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    filename = file.filename or "upload.pdf"
    metadata = {"tradition": tradition, "author": author, "source": source, "era": era}

    job = await _create_job(db, filename, tradition)
    job_id_str = str(job.id)
    ukey = cache.upload_key(job_id_str)

    await cache.store_upload(job_id_str, content)
    await cache.set_job(job_id_str, {"status": "processing"}, ttl=cache._PROCESSING_TTL)
    _dispatch(job, filename, metadata, upload_key=ukey)

    return SuccessResponse(data=IngestJobResponse(job_id=job.id, status="processing", filename=filename))


@router.post("/ingest/text", status_code=202, response_model=SuccessResponse[IngestJobResponse])
async def ingest_text(
    content: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    db: AsyncSession = Depends(get_db),
):
    filename = f"text-{hashlib.md5(content[:50].encode()).hexdigest()[:8]}.txt"
    metadata = {"tradition": tradition, "author": author, "source": source, "era": era}

    job = await _create_job(db, filename, tradition)
    job_id_str = str(job.id)
    ukey = cache.upload_key(job_id_str)

    await cache.store_upload(job_id_str, content.encode())
    await cache.set_job(job_id_str, {"status": "processing"}, ttl=cache._PROCESSING_TTL)
    _dispatch(job, filename, metadata, upload_key=ukey)

    return SuccessResponse(data=IngestJobResponse(job_id=job.id, status="processing", filename=filename))


@router.post("/ingest/url", status_code=202, response_model=SuccessResponse[IngestJobResponse])
async def ingest_url(
    url: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    db: AsyncSession = Depends(get_db),
):
    await _check_url_not_ssrf(url)
    metadata = {"tradition": tradition, "author": author, "source": source, "era": era}

    job = await _create_job(db, url, tradition)
    job_id_str = str(job.id)

    await cache.set_job(job_id_str, {"status": "processing"}, ttl=cache._PROCESSING_TTL)
    _dispatch(job, url, metadata, source_url=url)

    return SuccessResponse(data=IngestJobResponse(job_id=job.id, status="processing", filename=url))


@router.get("/ingest/jobs/{job_id}", response_model=SuccessResponse[IngestJobResponse])
async def get_ingest_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job_id_str = str(job_id)

    # Fast path: Redis cache
    try:
        cached = await cache.get_job(job_id_str)
        if cached:
            return SuccessResponse(data=IngestJobResponse(
                job_id=job_id,
                status=cached["status"],
                chunks_created=cached.get("chunks_created", 0),
                error=cached.get("error"),
            ))
    except Exception:
        logger.warning("redis_cache_miss_fallback", job_id=job_id_str)

    # Slow path: Postgres
    row = (await db.execute(select(IngestJob).where(IngestJob.id == job_id))).scalar_one_or_none()
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
