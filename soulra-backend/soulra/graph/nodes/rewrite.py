# app/graph/nodes/rewrite.py
from typing import cast

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from soulra.graph.state import SoulraState

REWRITE_PROMPT = """The original search query returned poor results.

User situation: {situation}
Original query: {query}

Write a better search query (max 15 words) that is more specific and likely to find
relevant wisdom passages. Focus on the emotional or philosophical core."""


class RewriteOutput(BaseModel):
    rewritten_query: str


def create_rewrite_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(RewriteOutput)

    async def rewrite(state: SoulraState) -> dict:
        prompt = REWRITE_PROMPT.format(
            situation=state["situation"],
            query=state["query"],
        )
        result = cast(RewriteOutput, await structured_llm.ainvoke(prompt))
        return {
            "query": result.rewritten_query,
            "rewrite_count": state["rewrite_count"] + 1,
        }

    return rewrite
