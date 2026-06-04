# tests/unit/test_graph_builder.py
import pytest
from unittest.mock import MagicMock


def test_graph_builds_without_error():
    from langgraph.checkpoint.memory import MemorySaver

    mock_retriever = MagicMock()
    mock_fast = MagicMock()
    mock_smart = MagicMock()

    from app.graph.builder import build_graph
    graph = build_graph(
        retriever=mock_retriever,
        fast_llm=mock_fast,
        smart_llm=mock_smart,
        checkpointer=MemorySaver(),
    )
    assert graph is not None


def test_route_after_grade_returns_rewrite_when_not_relevant():
    from app.graph.edges import route_after_grade
    state = {
        "grade_result": "not_relevant", "rewrite_count": 0,
        "situation": "", "tradition_hints": [], "query": "", "retrieved_docs": [],
        "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
        "refined_docs": [], "tradition_cards": [], "action_steps": [],
        "messages": [],
    }
    assert route_after_grade(state) == "rewrite_query"


def test_route_after_grade_returns_clarify_when_relevant():
    from app.graph.edges import route_after_grade
    state = {
        "grade_result": "relevant", "rewrite_count": 0,
        "situation": "", "tradition_hints": [], "query": "", "retrieved_docs": [],
        "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
        "refined_docs": [], "tradition_cards": [], "action_steps": [],
        "messages": [],
    }
    assert route_after_grade(state) == "clarify"


def test_route_after_grade_forces_clarify_after_max_rewrites():
    from app.graph.edges import route_after_grade
    state = {
        "grade_result": "not_relevant", "rewrite_count": 2,
        "situation": "", "tradition_hints": [], "query": "", "retrieved_docs": [],
        "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
        "refined_docs": [], "tradition_cards": [], "action_steps": [],
        "messages": [],
    }
    assert route_after_grade(state) == "clarify"
