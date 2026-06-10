import uuid
from datetime import datetime
from pydantic import BaseModel


class MeOut(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    token_limit: int
    tokens_used: int

    model_config = {"from_attributes": True}


class UserOut(MeOut):
    created_at: datetime
    last_login_at: datetime | None


class LoginEventOut(BaseModel):
    id: uuid.UUID
    user_id: str
    user_email: str = ""
    event_type: str
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenUsageOut(BaseModel):
    id: uuid.UUID
    user_id: str
    user_email: str = ""
    conversation_id: uuid.UUID | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserDetailOut(UserOut):
    recent_logins: list[LoginEventOut]
    recent_usage: list[TokenUsageOut]


class UserUpdate(BaseModel):
    role: str | None = None
    token_limit: int | None = None
