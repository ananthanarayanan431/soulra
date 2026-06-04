# app/graph/state.py
from typing import Annotated, TypedDict
from langchain_core.documents import Document
from langgraph.graph.message import add_messages


class SoulraState(TypedDict):
    situation: str
    tradition_hints: list[str]    # extracted by intake: ["stoic", "buddhist"]
    query: str                    # current search query (may be rewritten)
    retrieved_docs: list[Document]
    grade_result: str             # "relevant" | "not_relevant"
    clarify_question: str
    clarify_chips: list[str]
    clarify_answer: str | None    # None = graph paused at interrupt
    refined_docs: list[Document]
    tradition_cards: list[dict]
    action_steps: list[dict]
    messages: Annotated[list, add_messages]
    rewrite_count: int            # max 2 rewrites before forcing clarify
