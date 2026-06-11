import uuid
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.models.user import TokenUsageLog, User


async def persist_token_usage(
    db: AsyncSession,
    user_id: str,
    conversation_id: uuid.UUID | None,
    usage_metadata: dict[str, Any],
) -> int:
    """Write one TokenUsageLog row per model and increment the user's tokens_used.

    Commits the session itself, so callers should pass a session dedicated to
    this write rather than one shared with a larger in-progress transaction.

    Returns the grand total of tokens recorded.
    """
    grand_total = 0
    for model, usage in usage_metadata.items():
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        grand_total += total_tokens
        db.add(
            TokenUsageLog(
                user_id=user_id,
                conversation_id=conversation_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
        )

    if grand_total:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(tokens_used=User.tokens_used + grand_total)
        )

    await db.commit()
    return grand_total
