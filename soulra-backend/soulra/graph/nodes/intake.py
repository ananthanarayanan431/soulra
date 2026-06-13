# app/graph/nodes/intake.py
from typing import cast

from pydantic import BaseModel
from sqlalchemy import select
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from soulra.database import AsyncSessionLocal
from soulra.graph.state import SoulraState
from soulra.models.tradition import Tradition

DEFAULT_TRADITION_OPTIONS = [
    "stoic",
    "vedanta",
    "buddhist",
    "sufi",
    "taoist",
    "jewish",
    "christian_mystic",
    "zen",
]


async def get_tradition_options(user_id: str | None) -> list[str]:
    """Tradition slugs the intake LLM can route to for this user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Tradition.slug).where(Tradition.user_id == user_id)
        )
        slugs = [row[0] for row in result.all()]
    return slugs or DEFAULT_TRADITION_OPTIONS


INTAKE_PROMPT = """You are helping route a user's situation to the right wisdom traditions.
Given this situation: {situation}

Extract:
1. tradition_hints: list of 2-3 most relevant traditions from {options}
2. query: a clear, concise search query (max 15 words) capturing the core problem

Respond with a JSON object with keys "tradition_hints" and "query"."""

MAX_TRADITION_HINTS = 5
MAX_HINT_LENGTH = 50


class IntakeOutput(BaseModel):
    tradition_hints: list[str]
    query: str


def _sanitize_hints(hints: list) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for h in hints:
        if not isinstance(h, str):
            continue
        h = h.strip()[:MAX_HINT_LENGTH]
        if not h or h in seen:
            continue
        seen.add(h)
        result.append(h)
        if len(result) >= MAX_TRADITION_HINTS:
            break
    return result


def create_intake_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(IntakeOutput)

    async def intake(state: SoulraState, config: RunnableConfig) -> dict:
        user_id = config.get("configurable", {}).get("user_id")
        options = await get_tradition_options(user_id)
        prompt = INTAKE_PROMPT.format(
            situation=state["situation"],
            options=options,
        )
        result = cast(IntakeOutput, await structured_llm.ainvoke(prompt, config=config))
        return {
            "tradition_hints": _sanitize_hints(result.tradition_hints),
            "query": result.query,
            "rewrite_count": 0,
        }

    return intake
