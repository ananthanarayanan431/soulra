"""
Redis-backed caching layer.

Two concerns are handled here:
  1. Job status cache — fast reads for GET /ingest/jobs/{id} without hitting Postgres.
  2. Temporary upload store — binary file bytes held in Redis until the Celery worker
     picks them up, avoiding serialising large blobs through the task message.
"""

import json
from typing import Any

import redis.asyncio as aioredis

_redis: aioredis.Redis | None = None

_JOB_KEY = "job:{}"
_UPLOAD_KEY = "upload:{}"

# TTLs
_PROCESSING_TTL = 7200  # 2 h — enough for a slow ingestion
_DONE_TTL = 3600  # 1 h cache for completed / failed results
_UPLOAD_TTL = 3600  # 1 h window for the worker to pick up the file


def init_redis(url: str) -> aioredis.Redis:
    global _redis
    _redis = aioredis.from_url(url, decode_responses=False)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised — call init_redis() during app lifespan")
    return _redis


# ── Job status ──────────────────────────────────────────────────────────────


async def set_job(job_id: str, data: dict[str, Any], ttl: int = _DONE_TTL) -> None:
    await get_redis().setex(_JOB_KEY.format(job_id), ttl, json.dumps(data))


async def get_job(job_id: str) -> dict[str, Any] | None:
    raw = await get_redis().get(_JOB_KEY.format(job_id))
    return json.loads(raw) if raw else None


# ── Temporary upload store ───────────────────────────────────────────────────


async def store_upload(job_id: str, content: bytes) -> None:
    await get_redis().setex(_UPLOAD_KEY.format(job_id), _UPLOAD_TTL, content)


def upload_key(job_id: str) -> str:
    return _UPLOAD_KEY.format(job_id)
