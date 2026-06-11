import uuid
import pytest
from sqlalchemy import select
from soulra.models.user import User, LoginEvent, TokenUsageLog


@pytest.mark.asyncio
async def test_user_table_round_trip(test_db):
    user = User(id="user_abc123", email="a@example.com", name="Ann")
    test_db.add(user)
    await test_db.flush()

    row = (await test_db.execute(select(User).where(User.id == "user_abc123"))).scalar_one()
    assert row.email == "a@example.com"
    assert row.role == "user"
    assert row.token_limit == 1_000_000
    assert row.tokens_used == 0


@pytest.mark.asyncio
async def test_login_event_and_usage_log_round_trip(test_db):
    user = User(id="user_abc123", email="a@example.com")
    test_db.add(user)
    await test_db.flush()

    test_db.add(LoginEvent(user_id=user.id, event_type="login"))
    test_db.add(
        TokenUsageLog(
            id=uuid.uuid4(),
            user_id=user.id,
            model="anthropic/claude-sonnet-4-6",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
    )
    await test_db.flush()

    events = (await test_db.execute(select(LoginEvent))).scalars().all()
    logs = (await test_db.execute(select(TokenUsageLog))).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "login"
    assert len(logs) == 1
    assert logs[0].total_tokens == 30
