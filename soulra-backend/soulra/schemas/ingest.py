import uuid
from pydantic import BaseModel


class IngestJobResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    filename: str | None = None
    chunks_created: int = 0
    tokens_used: int = 0
    error: str | None = None
