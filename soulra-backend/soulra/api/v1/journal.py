import uuid
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text, any_
from sqlalchemy.ext.asyncio import AsyncSession
from soulra.database import get_db
from soulra.models.journal import JournalEntry
from soulra.schemas.journal import (
    JournalData, JournalEntryOut, JournalStats, TagCount,
    CreateJournalEntry, PatchJournalEntry,
)
from soulra.schemas.responses import SuccessResponse

router = APIRouter(tags=["journal"])


async def _tag_counts(db: AsyncSession) -> list[TagCount]:
    rows = await db.execute(
        text(
            "SELECT tag, COUNT(*) AS cnt "
            "FROM journal_entries, unnest(tags) AS t(tag) "
            "GROUP BY tag ORDER BY cnt DESC"
        )
    )
    return [TagCount(name=r.tag, count=r.cnt) for r in rows]


async def _tradition_counts(db: AsyncSession) -> list[TagCount]:
    rows = await db.execute(
        select(JournalEntry.tradition, func.count().label("cnt"))
        .where(JournalEntry.tradition.isnot(None))
        .group_by(JournalEntry.tradition)
        .order_by(func.count().desc())
    )
    return [TagCount(name=r.tradition, count=r.cnt) for r in rows]


async def _stats(db: AsyncSession) -> JournalStats:
    total = (await db.execute(select(func.count()).select_from(JournalEntry))).scalar_one()

    month_start = datetime(date.today().year, date.today().month, 1, tzinfo=timezone.utc)
    applied_this_month = (
        await db.execute(
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.applied.is_(True))
            .where(JournalEntry.applied_at >= month_start)
        )
    ).scalar_one()

    last_applied = (
        await db.execute(
            select(func.max(JournalEntry.applied_at))
            .where(JournalEntry.applied.is_(True))
        )
    ).scalar_one()

    last_applied_days_ago: int | None = None
    if last_applied:
        delta = datetime.now(timezone.utc) - last_applied
        last_applied_days_ago = delta.days

    return JournalStats(
        total=total,
        applied_this_month=applied_this_month,
        last_applied_days_ago=last_applied_days_ago,
    )


async def _revisit_entry(db: AsyncSession) -> JournalEntry | None:
    # Surface the oldest unapplied entry, or the oldest overall if all applied
    row = (
        await db.execute(
            select(JournalEntry)
            .where(JournalEntry.applied.is_(False))
            .order_by(JournalEntry.saved_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        row = (
            await db.execute(
                select(JournalEntry).order_by(JournalEntry.saved_at.asc()).limit(1)
            )
        ).scalar_one_or_none()
    return row


@router.get(
    "/journal",
    response_model=SuccessResponse[JournalData],
    summary="List journal entries",
)
async def list_journal(
    tag: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(JournalEntry).order_by(JournalEntry.saved_at.desc())
    if tag and tag != "all":
        stmt = stmt.where(tag == any_(JournalEntry.tags))
    entries = (await db.execute(stmt)).scalars().all()

    tag_rows = await _tag_counts(db)
    total = (await db.execute(select(func.count()).select_from(JournalEntry))).scalar_one()
    all_tag = [TagCount(name="all", count=total)] + tag_rows

    tradition_rows = await _tradition_counts(db)
    stats = await _stats(db)
    revisit = await _revisit_entry(db)

    return SuccessResponse(data=JournalData(
        entries=[JournalEntryOut.model_validate(e) for e in entries],
        stats=stats,
        tag_counts=all_tag,
        tradition_counts=tradition_rows,
        revisit=JournalEntryOut.model_validate(revisit) if revisit else None,
    ))


@router.post(
    "/journal",
    response_model=SuccessResponse[JournalEntryOut],
    status_code=201,
    summary="Save a journal entry",
)
async def create_journal_entry(
    body: CreateJournalEntry,
    db: AsyncSession = Depends(get_db),
):
    entry = JournalEntry(
        text=body.text,
        quote=body.quote,
        tradition=body.tradition,
        author=body.author,
        citation=body.citation,
        analysis=body.analysis,
        tags=body.tags,
        saved_at=datetime.now(timezone.utc),
        conversation_id=body.conversation_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return SuccessResponse(data=JournalEntryOut.model_validate(entry))


@router.patch(
    "/journal/{entry_id}",
    response_model=SuccessResponse[JournalEntryOut],
    summary="Update a journal entry",
)
async def patch_journal_entry(
    entry_id: uuid.UUID,
    body: PatchJournalEntry,
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(JournalEntry).where(JournalEntry.id == entry_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if body.applied is not None:
        row.applied = body.applied
        row.applied_at = datetime.now(timezone.utc) if body.applied else None
    if body.tags is not None:
        row.tags = body.tags
    if body.personal_note is not None:
        row.personal_note = body.personal_note

    await db.commit()
    await db.refresh(row)
    return SuccessResponse(data=JournalEntryOut.model_validate(row))


@router.delete(
    "/journal/{entry_id}",
    status_code=204,
    summary="Delete a journal entry",
)
async def delete_journal_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(JournalEntry).where(JournalEntry.id == entry_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    await db.delete(row)
    await db.commit()
