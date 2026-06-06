# app/graph/state.py
from typing import Annotated, TypedDict
from langchain_core.documents import Document
from langgraph.graph.message import add_messages


class SoulraState(TypedDict):
    situation: str
    tradition_hints: list[str]    # extracted by intake: ["stoic", "buddhist"]
    query: str                    # current search query (may be rewritten)
    retrieved_docs: list[Document]
    reranked_docs: list[Document]      # top-5 after Cohere rerank + U-shape
    grade_result: str             # "relevant" | "not_relevant"
    clarify_question: str
    clarify_chips: list[str]
    clarify_answer: str | None    # None = graph paused at interrupt
    refined_docs: list[Document]
    tradition_cards: list[dict]
    action_steps: list[dict]
    messages: Annotated[list, add_messages]
    rewrite_count: int            # max 2 rewrites before forcing clarify


def make_initial_state(situation: str) -> SoulraState:
    """Build a fully-initialised SoulraState for a new conversation."""
    return SoulraState(
        situation=situation,
        tradition_hints=[],
        query="",
        retrieved_docs=[],
        reranked_docs=[],              # new
        grade_result="",
        clarify_question="",
        clarify_chips=[],
        clarify_answer=None,
        refined_docs=[],
        tradition_cards=[],
        action_steps=[],
        messages=[],
        rewrite_count=0,
    )
