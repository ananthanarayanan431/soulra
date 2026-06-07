import uuid
from datetime import datetime
from pydantic import BaseModel


class ActionStepOut(BaseModel):
    step_number: int
    title: str
    body: str

    model_config = {"from_attributes": True}


class TraditionCardOut(BaseModel):
    card_order: int
    tradition: str
    author: str
    quote: str
    citation: str
    analysis: str
    source_passage: str

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: uuid.UUID
    thread_id: str
    situation: str
    clarify_q: str | None
    clarify_ans: str | None
    created_at: datetime
    action_steps: list[ActionStepOut] = []
    tradition_cards: list[TraditionCardOut] = []

    model_config = {"from_attributes": True}
