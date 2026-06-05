# app/graph/edges.py
from typing import Literal
from soulra.graph.state import SoulraState

MAX_REWRITES = 2


def route_after_grade(
    state: SoulraState,
) -> Literal["rewrite_query", "clarify"]:
    if state["grade_result"] == "relevant" or state["rewrite_count"] >= MAX_REWRITES:
        return "clarify"
    return "rewrite_query"
