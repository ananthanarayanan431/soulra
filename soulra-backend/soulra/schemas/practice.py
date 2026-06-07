import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Literal


class PracticeDayOut(BaseModel):
    id: uuid.UUID
    day_number: int
    day_label: str
    task_title: str
    task_body: str
    morning_quote: str
    morning_author: str
    morning_citation: str
    morning_analysis: str
    evening_prompt: str
    reflection_text: str | None
    completed: bool
    state: Literal["done", "today", "future"]

    model_config = {"from_attributes": True}


class PracticeArcOut(BaseModel):
    id: uuid.UUID
    theme: str
    status: str
    current_day: int
    days_into_arc: str
    created_at: datetime
    days: list[PracticeDayOut]

    model_config = {"from_attributes": True}


class ReflectBody(BaseModel):
    text: str
