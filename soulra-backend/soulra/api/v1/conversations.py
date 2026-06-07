import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from soulra.database import get_db
from soulra.models.conversation import Conversation
from soulra.schemas.conversation import ConversationOut
from soulra.schemas.responses import SuccessResponse

router = APIRouter(tags=["conversations"])


@router.get(
    "/conversations",
    response_model=SuccessResponse[list[ConversationOut]],
    summary="List conversations",
    description="Returns a paginated list of all conversations ordered by most recent first. Includes associated action steps for each conversation.",
)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.action_steps),
            selectinload(Conversation.tradition_cards),
        )
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return SuccessResponse(data=[ConversationOut.model_validate(r) for r in rows])


@router.get(
    "/conversations/{conversation_id}",
    response_model=SuccessResponse[ConversationOut],
    summary="Get a conversation",
    description="Fetches a single conversation by its UUID, including all associated action steps. Returns 404 if not found.",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.action_steps),
            selectinload(Conversation.tradition_cards),
        )
        .where(Conversation.id == conversation_id)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return SuccessResponse(data=ConversationOut.model_validate(row))


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
    summary="Delete a conversation",
    description="Permanently deletes a conversation and its associated action steps by UUID. Returns 404 if not found. This action is irreversible.",
)
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
