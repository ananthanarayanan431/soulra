import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from soulra.database import get_db
from soulra.models.conversation import Conversation
from soulra.schemas.conversation import ConversationOut
from soulra.schemas.responses import SuccessResponse

router = APIRouter(tags=["conversations"])


@router.get("/conversations", response_model=SuccessResponse[list[ConversationOut]])
async def list_conversations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.action_steps))
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return SuccessResponse(data=[ConversationOut.model_validate(r) for r in rows])


@router.get("/conversations/{conversation_id}", response_model=SuccessResponse[ConversationOut])
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.action_steps))
        .where(Conversation.id == conversation_id)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return SuccessResponse(data=ConversationOut.model_validate(row))


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(row)
    await db.commit()
