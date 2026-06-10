import pytest
from sqlalchemy import select
from soulra.models.user import TokenUsageLog, User
from soulra.services.token_usage import persist_token_usage


@pytest.mark.asyncio
async def test_persist_token_usage_writes_log_and_increments_user(test_db, test_user):
    usage_metadata = {
        "anthropic/claude-sonnet-4-6": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        "anthropic/claude-opus-4-8": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    }

    await persist_token_usage(test_db, user_id=test_user.id, conversation_id=None, usage_metadata=usage_metadata)

    logs = (await test_db.execute(select(TokenUsageLog).where(TokenUsageLog.user_id == test_user.id))).scalars().all()
    assert len(logs) == 2
    assert sum(l.total_tokens for l in logs) == 165

    refreshed = await test_db.get(User, test_user.id)
    assert refreshed.tokens_used == 165


@pytest.mark.asyncio
async def test_persist_token_usage_noop_for_empty_metadata(test_db, test_user):
    await persist_token_usage(test_db, user_id=test_user.id, conversation_id=None, usage_metadata={})

    refreshed = await test_db.get(User, test_user.id)
    assert refreshed.tokens_used == 0
