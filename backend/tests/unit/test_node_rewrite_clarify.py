# tests/unit/test_node_rewrite_clarify.py
import pytest
from unittest.mock import MagicMock


def _make_state(**overrides):
    base = {
        "situation": "I say yes too much.",
        "query": "refusing",
        "tradition_hints": ["stoic"],
        "retrieved_docs": [],
        "grade_result": "not_relevant",
        "clarify_question": "",
        "clarify_chips": [],
        "clarify_answer": None,
        "refined_docs": [],
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
        "rewrite_count": 0,
    }
    base.update(overrides)
    return base


def test_rewrite_node_produces_new_query():
    from app.graph.nodes.rewrite import create_rewrite_node, RewriteOutput
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value=RewriteOutput(rewritten_query="how to set boundaries at work"))
    rewrite = create_rewrite_node(mock_llm)
    result = rewrite(_make_state())
    assert result["query"] == "how to set boundaries at work"
    assert result["rewrite_count"] == 1


def test_rewrite_increments_rewrite_count():
    from app.graph.nodes.rewrite import create_rewrite_node, RewriteOutput
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value=RewriteOutput(rewritten_query="new query"))
    rewrite = create_rewrite_node(mock_llm)
    result = rewrite(_make_state(rewrite_count=1))
    assert result["rewrite_count"] == 2


def test_clarify_node_produces_question_and_chips():
    from app.graph.nodes.clarify import create_clarify_node, ClarifyOutput
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value=ClarifyOutput(
        question="Is this about the work, the people, or something inside?",
        chips=["The work", "The people", "Something inside me", "It's all three"],
    ))
    clarify = create_clarify_node(mock_llm)
    result = clarify(_make_state())
    assert len(result["clarify_question"]) > 0
    assert len(result["clarify_chips"]) == 4


def test_clarify_node_truncates_to_4_chips():
    from app.graph.nodes.clarify import create_clarify_node, ClarifyOutput
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value=ClarifyOutput(
        question="Question?",
        chips=["A", "B", "C", "D", "E"],  # 5 chips
    ))
    clarify = create_clarify_node(mock_llm)
    result = clarify(_make_state())
    assert len(result["clarify_chips"]) == 4
