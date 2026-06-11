import asyncio
import hashlib
import ipaddress
import re
import socket
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.config import settings
from soulra.core.auth import get_current_user
from soulra.core.logging import logger
from soulra.database import get_db
from soulra.models.ingest_job import IngestJob
from soulra.models.user import User
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
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(status_code=400, detail="URL resolves to a disallowed address")
        return
    except ValueError:
        pass
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Invalid URL: cannot resolve host")
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise HTTPException(status_code=400, detail="URL resolves to a disallowed address")
        except ValueError:
            pass


async def _create_job(db: AsyncSession, filename: str, tradition: str, user_id: str) -> IngestJob:
    job = IngestJob(filename=filename, tradition=tradition, user_id=user_id)
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


@router.post(
    "/ingest/pdf",
    status_code=202,
    response_model=SuccessResponse[IngestJobResponse],
    summary="Ingest a PDF file",
    description="Accepts a PDF upload along with tradition metadata (tradition, author, source, era) and enqueues a background ingest job. Returns the job ID immediately — poll `/ingest/jobs/{job_id}` to track progress.",
)
async def ingest_pdf(
    request: Request,
    file: UploadFile = File(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    cl = request.headers.get("content-length")
    if cl and int(cl) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit"
        )

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit"
        )

    filename = file.filename or "upload.pdf"
    metadata = {"tradition": tradition, "author": author, "source": source, "era": era}

    job = await _create_job(db, filename, tradition, current_user.id)
    job_id_str = str(job.id)
    ukey = cache.upload_key(job_id_str)

    await cache.store_upload(job_id_str, content)
    await cache.set_job(job_id_str, {"status": "processing"}, ttl=cache._PROCESSING_TTL)
    _dispatch(job, filename, metadata, upload_key=ukey)

    return SuccessResponse(
        data=IngestJobResponse(job_id=job.id, status="processing", filename=filename)
    )


@router.post(
    "/ingest/text",
    status_code=202,
    response_model=SuccessResponse[IngestJobResponse],
    summary="Ingest plain text",
    description="Accepts a raw text string along with tradition metadata and enqueues a background ingest job. Useful for ingesting passages that are already extracted. Returns a job ID for polling.",
)
async def ingest_text(
    content: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = f"text-{hashlib.md5(content[:50].encode()).hexdigest()[:8]}.txt"
    metadata = {"tradition": tradition, "author": author, "source": source, "era": era}

    job = await _create_job(db, filename, tradition, current_user.id)
    job_id_str = str(job.id)
    ukey = cache.upload_key(job_id_str)

    await cache.store_upload(job_id_str, content.encode())
    await cache.set_job(job_id_str, {"status": "processing"}, ttl=cache._PROCESSING_TTL)
    _dispatch(job, filename, metadata, upload_key=ukey)

    return SuccessResponse(
        data=IngestJobResponse(job_id=job.id, status="processing", filename=filename)
    )


@router.post(
    "/ingest/url",
    status_code=202,
    response_model=SuccessResponse[IngestJobResponse],
    summary="Ingest from a URL",
    description="Fetches and ingests content from a public HTTP/HTTPS URL. Private IPs and loopback addresses are blocked (SSRF protection). Enqueues a background ingest job and returns the job ID for polling.",
)
async def ingest_url(
    url: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_url_not_ssrf(url)
    metadata = {"tradition": tradition, "author": author, "source": source, "era": era}

    job = await _create_job(db, url, tradition, current_user.id)
    job_id_str = str(job.id)

    await cache.set_job(job_id_str, {"status": "processing"}, ttl=cache._PROCESSING_TTL)
    _dispatch(job, url, metadata, source_url=url)

    return SuccessResponse(data=IngestJobResponse(job_id=job.id, status="processing", filename=url))


_YT_PATTERN = re.compile(r"(?:v=|youtu\.be/|embed/|shorts/|/v/)([a-zA-Z0-9_-]{11})")


def _extract_youtube_id(url: str) -> str | None:
    m = _YT_PATTERN.search(url)
    return m.group(1) if m else None


@router.post(
    "/ingest/youtube",
    status_code=202,
    response_model=SuccessResponse[IngestJobResponse],
    summary="Ingest from a YouTube video transcript",
    description="Extracts the auto-generated or manually-uploaded transcript from a YouTube video and ingests it as text. Captions must be available on the video. Returns a job ID for polling.",
)
async def ingest_youtube(
    url: str = Form(...),
    tradition: str = Form(...),
    author: str = Form(...),
    source: str = Form(...),
    era: str = Form(default="unknown"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video_id = _extract_youtube_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400, detail="Invalid YouTube URL — could not extract video ID"
        )

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        def _fetch() -> str:
            transcript = YouTubeTranscriptApi().fetch(video_id)
            return " ".join(snippet.text for snippet in transcript)

        text = await asyncio.to_thread(_fetch)
    except ImportError:
        raise HTTPException(
            status_code=501, detail="YouTube transcript support not available on this server"
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not fetch transcript: {exc}")

    filename = f"youtube-{video_id}.txt"
    metadata = {"tradition": tradition, "author": author, "source": source, "era": era}

    job = await _create_job(db, filename, tradition, current_user.id)
    job_id_str = str(job.id)
    ukey = cache.upload_key(job_id_str)

    await cache.store_upload(job_id_str, text.encode())
    await cache.set_job(job_id_str, {"status": "processing"}, ttl=cache._PROCESSING_TTL)
    _dispatch(job, filename, metadata, upload_key=ukey)

    return SuccessResponse(
        data=IngestJobResponse(job_id=job.id, status="processing", filename=filename)
    )


@router.get(
    "/ingest/jobs/{job_id}",
    response_model=SuccessResponse[IngestJobResponse],
    summary="Get ingest job status",
    description="Polls the status of a background ingest job by its UUID. Checks Redis first (fast path), then falls back to Postgres. Returns status, chunk count, token usage, and any error message.",
)
async def get_ingest_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job_id_str = str(job_id)

    # Ownership check against Postgres first, then overlay live fields from Redis.
    row = (
        await db.execute(
            select(IngestJob).where(IngestJob.id == job_id, IngestJob.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    status = row.status
    chunks_created = row.chunks_created
    error = row.error

    try:
        cached = await cache.get_job(job_id_str)
        if cached:
            status = cached.get("status", status)
            chunks_created = cached.get("chunks_created", chunks_created)
            error = cached.get("error", error)
    except Exception:
        logger.warning("redis_cache_miss_fallback", job_id=job_id_str)

    return SuccessResponse(
        data=IngestJobResponse(
            job_id=row.id,
            status=status,
            filename=row.filename,
            chunks_created=chunks_created,
            tokens_used=row.tokens_used,
            error=error,
        )
    )
