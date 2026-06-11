import uuid
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text, any_
from sqlalchemy.ext.asyncio import AsyncSession
from soulra.core.auth import get_current_user
from soulra.database import get_db
from soulra.models.journal import JournalEntry
from soulra.models.user import User
from soulra.schemas.journal import (
    JournalData,
    JournalEntryOut,
    JournalStats,
    TagCount,
    CreateJournalEntry,
    PatchJournalEntry,
)
from soulra.schemas.responses import SuccessResponse

router = APIRouter(tags=["journal"])


async def _tag_counts(db: AsyncSession, user_id: str) -> list[TagCount]:
    if db.bind.dialect.name == "sqlite":
        # SQLite has no unnest(); aggregate the JSON-encoded tag arrays in Python.
        rows = await db.execute(select(JournalEntry.tags).where(JournalEntry.user_id == user_id))
        counts: dict[str, int] = {}
        for (tags,) in rows:
            for tag in tags or []:
                counts[tag] = counts.get(tag, 0) + 1
        return [
            TagCount(name=name, count=count)
            for name, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        ]

    rows = await db.execute(
        text(
            "SELECT tag, COUNT(*) AS cnt "
            "FROM journal_entries, unnest(tags) AS t(tag) "
            "WHERE user_id = :user_id "
            "GROUP BY tag ORDER BY cnt DESC"
        ),
        {"user_id": user_id},
    )
    return [TagCount(name=r.tag, count=r.cnt) for r in rows]


async def _tradition_counts(db: AsyncSession, user_id: str) -> list[TagCount]:
    rows = await db.execute(
        select(JournalEntry.tradition, func.count().label("cnt"))
        .where(JournalEntry.tradition.isnot(None), JournalEntry.user_id == user_id)
        .group_by(JournalEntry.tradition)
        .order_by(func.count().desc())
    )
    return [TagCount(name=r.tradition, count=r.cnt) for r in rows]


async def _stats(db: AsyncSession, user_id: str) -> JournalStats:
    total = (
        await db.execute(
            select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == user_id)
        )
    ).scalar_one()

    month_start = datetime(date.today().year, date.today().month, 1, tzinfo=timezone.utc)
    applied_this_month = (
        await db.execute(
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.applied.is_(True))
            .where(JournalEntry.applied_at >= month_start)
            .where(JournalEntry.user_id == user_id)
        )
    ).scalar_one()

    last_applied = (
        await db.execute(
            select(func.max(JournalEntry.applied_at))
            .where(JournalEntry.applied.is_(True))
            .where(JournalEntry.user_id == user_id)
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


async def _revisit_entry(db: AsyncSession, user_id: str) -> JournalEntry | None:
    # Surface the oldest unapplied entry, or the oldest overall if all applied
    row = (
        await db.execute(
            select(JournalEntry)
            .where(JournalEntry.applied.is_(False), JournalEntry.user_id == user_id)
            .order_by(JournalEntry.saved_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        row = (
            await db.execute(
                select(JournalEntry)
                .where(JournalEntry.user_id == user_id)
                .order_by(JournalEntry.saved_at.asc())
                .limit(1)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(JournalEntry)
        .where(JournalEntry.user_id == current_user.id)
        .order_by(JournalEntry.saved_at.desc())
    )
    if tag and tag != "all":
        stmt = stmt.where(any_(JournalEntry.tags) == tag)
    entries = (await db.execute(stmt)).scalars().all()

    tag_rows = await _tag_counts(db, current_user.id)
    total = (
        await db.execute(
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.user_id == current_user.id)
        )
    ).scalar_one()
    all_tag = [TagCount(name="all", count=total)] + tag_rows

    tradition_rows = await _tradition_counts(db, current_user.id)
    stats = await _stats(db, current_user.id)
    revisit = await _revisit_entry(db, current_user.id)

    return SuccessResponse(
        data=JournalData(
            entries=[JournalEntryOut.model_validate(e) for e in entries],
            stats=stats,
            tag_counts=all_tag,
            tradition_counts=tradition_rows,
            revisit=JournalEntryOut.model_validate(revisit) if revisit else None,
        )
    )


@router.post(
    "/journal",
    response_model=SuccessResponse[JournalEntryOut],
    status_code=201,
    summary="Save a journal entry",
)
async def create_journal_entry(
    body: CreateJournalEntry,
    current_user: User = Depends(get_current_user),
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
        user_id=current_user.id,
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(JournalEntry).where(
                JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id
            )
        )
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(JournalEntry).where(
                JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    await db.delete(row)
    await db.commit()
