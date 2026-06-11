import uuid
from datetime import datetime
from pydantic import BaseModel


class JournalEntryOut(BaseModel):
    id: uuid.UUID
    text: str
    quote: str | None
    tradition: str | None
    author: str | None
    citation: str | None
    analysis: str | None
    personal_note: str | None
    tags: list[str]
    applied: bool
    applied_at: datetime | None
    saved_at: datetime
    conversation_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class TagCount(BaseModel):
    name: str
    count: int


class JournalStats(BaseModel):
    total: int
    applied_this_month: int
    last_applied_days_ago: int | None


class JournalData(BaseModel):
    entries: list[JournalEntryOut]
    stats: JournalStats
    tag_counts: list[TagCount]
    tradition_counts: list[TagCount]
    revisit: JournalEntryOut | None


class CreateJournalEntry(BaseModel):
    text: str
    quote: str | None = None
    tradition: str | None = None
    author: str | None = None
    citation: str | None = None
    analysis: str | None = None
    tags: list[str] = []
    conversation_id: uuid.UUID | None = None


class PatchJournalEntry(BaseModel):
    applied: bool | None = None
    tags: list[str] | None = None
    personal_note: str | None = None
