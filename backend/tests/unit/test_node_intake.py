# tests/unit/test_node_intake.py
import pytest
from unittest.mock import MagicMock
import json


def make_intake_llm_response(tradition_hints, query):
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    from app.graph.nodes.intake import IntakeOutput
    mock_llm.invoke = MagicMock(return_value=IntakeOutput(tradition_hints=tradition_hints, query=query))
    return mock_llm


def _make_empty_state(situation="I keep saying yes to projects I don't want."):
    return {
        "situation": situation,
        "tradition_hints": [],
        "query": "",
        "retrieved_docs": [],
        "grade_result": "",
        "clarify_question": "",
        "clarify_chips": [],
        "clarify_answer": None,
        "refined_docs": [],
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
        "rewrite_count": 0,
    }


def test_intake_extracts_tradition_hints():
    from app.graph.nodes.intake import create_intake_node

    mock_llm = make_intake_llm_response(["stoic", "buddhist"], "refusing gracefully")
    intake = create_intake_node(mock_llm)

    result = intake(_make_empty_state())
    assert result["tradition_hints"] == ["stoic", "buddhist"]
    assert result["query"] == "refusing gracefully"


def test_intake_initialises_rewrite_count():
    from app.graph.nodes.intake import create_intake_node
    mock_llm = make_intake_llm_response([], "query")
    intake = create_intake_node(mock_llm)
    result = intake(_make_empty_state())
    assert result["rewrite_count"] == 0
