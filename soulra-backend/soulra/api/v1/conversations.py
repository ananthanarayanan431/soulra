import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from soulra.core.auth import get_current_user
from soulra.database import get_db
from soulra.models.conversation import Conversation, ActionStep
from soulra.models.user import User
from soulra.schemas.conversation import ConversationOut, ActionStepOut
from soulra.schemas.responses import SuccessResponse
from soulra.dependencies import get_smart_llm

router = APIRouter(tags=["conversations"])

REGEN_STEPS_PROMPT = """You are Soulra, an AI wisdom companion.

User situation: {situation}
Clarification: {clarify_answer}

Source passages from traditions already cited:
{passages}

Previous steps shown to the user (generate DIFFERENT steps — do not repeat the same titles or actions):
{previous_steps}

Generate exactly 3 concrete action steps the user can take today. Each step must:
- Be grounded in the passages above
- Differ meaningfully from the previous steps
- Have n ("01"/"02"/"03"), a short title (3-6 words), and a body (1-2 specific sentences)"""


class RegenStepsOutput(BaseModel):
    action_steps: list[ActionStepOut]


@router.get(
    "/conversations",
    response_model=SuccessResponse[list[ConversationOut]],
    summary="List conversations",
    description="Returns a paginated list of all conversations ordered by most recent first. Includes associated action steps for each conversation.",
)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.action_steps),
            selectinload(Conversation.tradition_cards),
        )
        .where(Conversation.user_id == current_user.id)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.action_steps),
            selectinload(Conversation.tradition_cards),
        )
        .where(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return SuccessResponse(data=ConversationOut.model_validate(row))


@router.post(
    "/conversations/{conversation_id}/regenerate-steps",
    response_model=SuccessResponse[list[ActionStepOut]],
    summary="Regenerate action steps",
)
async def regenerate_steps(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.action_steps),
            selectinload(Conversation.tradition_cards),
        )
        .where(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
    )
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    passages = "\n\n".join(
        f"[{c.tradition} | {c.author} | {c.citation}]\n{c.source_passage}"
        for c in conv.tradition_cards
    )
    previous = "\n".join(
        f"{s.step_number}. {s.title}: {s.body}"
        for s in sorted(conv.action_steps, key=lambda s: s.step_number)
    )

    llm = get_smart_llm()

    class _Step(BaseModel):
        n: str
        title: str
        body: str

    class _Out(BaseModel):
        action_steps: list[_Step]

    result: _Out = await llm.with_structured_output(_Out).ainvoke(
        REGEN_STEPS_PROMPT.format(
            situation=conv.situation,
            clarify_answer=conv.clarify_ans or "not provided",
            passages=passages or "[No passages available]",
            previous_steps=previous or "[None]",
        )
    )

    await db.execute(delete(ActionStep).where(ActionStep.conversation_id == conversation_id))
    new_steps = [
        ActionStep(
            conversation_id=conversation_id,
            step_number=int(s.n),
            title=s.title,
            body=s.body,
        )
        for s in result.action_steps
    ]
    db.add_all(new_steps)
    await db.commit()
    for s in new_steps:
        await db.refresh(s)

    return SuccessResponse(data=[ActionStepOut.model_validate(s) for s in new_steps])


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
    summary="Delete a conversation",
    description="Permanently deletes a conversation and its associated action steps by UUID. Returns 404 if not found. This action is irreversible.",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(row)
    await db.commit()
