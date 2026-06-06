# app/schemas/websocket.py
from typing import Literal
from pydantic import BaseModel


# Client → Server
class StartMessage(BaseModel):
    type: Literal["start"]
    situation: str


class ClarificationMessage(BaseModel):
    type: Literal["clarification"]
    choice: str


class FollowupMessage(BaseModel):
    type: Literal["followup"]
    text: str


# Server → Client
class StatusEvent(BaseModel):
    type: Literal["status"] = "status"
    node: str


class ClarifyEvent(BaseModel):
    type: Literal["clarify"] = "clarify"
    question: str


class ChipsEvent(BaseModel):
    type: Literal["chips"] = "chips"
    options: list[str]


class TraditionDoneEvent(BaseModel):
    type: Literal["tradition_done"] = "tradition_done"
    tradition: str
    author: str
    quote: str
    citation: str
    analysis: str
    source_passage: str


class ActionStepEvent(BaseModel):
    type: Literal["action_step"] = "action_step"
    n: str
    title: str
    body: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str = "INTERNAL_ERROR"
