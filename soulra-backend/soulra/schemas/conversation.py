import uuid
from datetime import datetime
from pydantic import BaseModel


class ActionStepOut(BaseModel):
    step_number: int
    title: str
    body: str


class ConversationOut(BaseModel):
    id: uuid.UUID
    thread_id: str
    situation: str
    clarify_q: str | None
    clarify_ans: str | None
    created_at: datetime
    action_steps: list[ActionStepOut] = []

    model_config = {"from_attributes": True}
