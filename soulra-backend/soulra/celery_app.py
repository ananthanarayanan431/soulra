from celery import Celery
from soulra.config import settings

celery_app = Celery(
    "soulra",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["soulra.tasks.ingest"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Acknowledge only after the task completes so a crashed worker re-queues the task.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # One task at a time per worker slot — prevents memory bloat from large PDFs.
    worker_prefetch_multiplier=1,
    task_routes={
        "soulra.tasks.ingest.*": {"queue": "ingest"},
    },
    # Result TTL: 24 h
    result_expires=86400,
)
