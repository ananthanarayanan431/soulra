import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from soulra.database import get_db
from soulra.models.conversation import Conversation
from soulra.models.practice import PracticeArc, PracticeDay
from soulra.models.tradition_card import TraditionCard
from soulra.schemas.practice import PracticeArcOut, PracticeDayOut, ReflectBody
from soulra.schemas.responses import SuccessResponse
from soulra.services.practice_builder import _build_days

router = APIRouter(tags=["practice"])


def _day_state(day: PracticeDay, current_day: int) -> str:
    if day.completed:
        return "done"
    if day.day_number == current_day:
        return "today"
    return "future"


def _arc_to_out(arc: PracticeArc) -> PracticeArcOut:
    days = [
        PracticeDayOut(
            id=d.id,
            day_number=d.day_number,
            day_label=d.day_label,
            task_title=d.task_title,
            task_body=d.task_body,
            morning_quote=d.morning_quote,
            morning_author=d.morning_author,
            morning_citation=d.morning_citation,
            morning_analysis=d.morning_analysis,
            evening_prompt=d.evening_prompt,
            reflection_text=d.reflection_text,
            completed=d.completed,
            state=_day_state(d, arc.current_day),
        )
        for d in arc.days
    ]
    return PracticeArcOut(
        id=arc.id,
        theme=arc.theme,
        status=arc.status,
        current_day=arc.current_day,
        days_into_arc=f"{arc.current_day} days into a 7-day arc",
        created_at=arc.created_at,
        days=days,
    )


async def _load_arc(arc_id: uuid.UUID, db: AsyncSession) -> PracticeArc:
    stmt = (
        select(PracticeArc)
        .options(selectinload(PracticeArc.days))
        .where(PracticeArc.id == arc_id)
    )
    arc = (await db.execute(stmt)).scalar_one_or_none()
    if not arc:
        raise HTTPException(status_code=404, detail="Practice arc not found")
    return arc


@router.get(
    "/practice/active",
    response_model=SuccessResponse[PracticeArcOut | None],
    summary="Get active practice arc",
    description="Returns the most recent active 7-day practice arc with all days. Returns null if none exists.",
)
async def get_active_practice(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(PracticeArc)
        .options(selectinload(PracticeArc.days))
        .where(PracticeArc.status == "active")
        .order_by(PracticeArc.created_at.desc())
        .limit(1)
    )
    arc = (await db.execute(stmt)).scalar_one_or_none()
    return SuccessResponse(data=_arc_to_out(arc) if arc else None)


@router.post(
    "/practice/{conversation_id}",
    response_model=SuccessResponse[PracticeArcOut],
    status_code=201,
    summary="Create practice arc from conversation",
    description="Idempotent. Creates a 7-day practice arc from the conversation's action steps and tradition cards. Returns the existing arc if already created.",
)
async def create_practice_arc(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # Check if arc already exists for this conversation
    existing = (
        await db.execute(
            select(PracticeArc)
            .options(selectinload(PracticeArc.days))
            .where(PracticeArc.conversation_id == conversation_id)
        )
    ).scalar_one_or_none()
    if existing:
        return SuccessResponse(data=_arc_to_out(existing))

    conv = (
        await db.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.action_steps),
                selectinload(Conversation.tradition_cards),
            )
            .where(Conversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not conv.action_steps or not conv.tradition_cards:
        raise HTTPException(status_code=422, detail="Conversation has no action steps or tradition cards")

    now = datetime.now(timezone.utc)
    arc = PracticeArc(
        conversation_id=conv.id,
        theme=conv.situation[:120],
        status="active",
        current_day=1,
        created_at=now,
    )
    db.add(arc)
    await db.flush()

    for day in _build_days(arc, conv.action_steps, conv.tradition_cards):
        db.add(day)
    await db.flush()

    await db.refresh(arc, ["days"])
    return SuccessResponse(data=_arc_to_out(arc))


@router.patch(
    "/practice/{arc_id}/days/{day_number}/complete",
    response_model=SuccessResponse[PracticeArcOut],
    summary="Complete a practice day",
    description="Marks the specified day as completed and advances current_day. Marks arc as completed when day 7 is done.",
)
async def complete_day(
    arc_id: uuid.UUID,
    day_number: int,
    db: AsyncSession = Depends(get_db),
):
    arc = await _load_arc(arc_id, db)
    day = next((d for d in arc.days if d.day_number == day_number), None)
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")

    day.completed = True
    arc.current_day = min(day_number + 1, 7)
    if all(d.completed for d in arc.days):
        arc.status = "completed"

    await db.flush()
    await db.refresh(arc, ["days"])
    return SuccessResponse(data=_arc_to_out(arc))


@router.patch(
    "/practice/{arc_id}/days/{day_number}/reflect",
    status_code=204,
    summary="Save evening reflection",
    description="Saves the user's evening reflection text for the specified day.",
)
async def save_reflection(
    arc_id: uuid.UUID,
    day_number: int,
    body: ReflectBody,
    db: AsyncSession = Depends(get_db),
):
    arc = await _load_arc(arc_id, db)
    day = next((d for d in arc.days if d.day_number == day_number), None)
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")

    day.reflection_text = body.text
    day.reflection_at = datetime.now(timezone.utc)
    await db.flush()
