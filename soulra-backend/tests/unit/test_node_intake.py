# tests/unit/test_node_intake.py
import asyncio
import pytest
from unittest.mock import MagicMock
import json


def make_intake_llm_response(tradition_hints, query):
    from unittest.mock import AsyncMock
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    from soulra.graph.nodes.intake import IntakeOutput
    mock_llm.ainvoke = AsyncMock(return_value=IntakeOutput(tradition_hints=tradition_hints, query=query))
    return mock_llm


def _make_empty_state(situation="I keep saying yes to projects I don't want."):
    return {
        "situation": situation,
        "tradition_hints": [],
        "query": "",
        "retrieved_docs": [],
        "reranked_docs": [],
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


@pytest.mark.asyncio
async def test_intake_extracts_tradition_hints():
    from soulra.graph.nodes.intake import create_intake_node

    mock_llm = make_intake_llm_response(["stoic", "buddhist"], "refusing gracefully")
    intake = create_intake_node(mock_llm)

    result = await intake(_make_empty_state())
    assert result["tradition_hints"] == ["stoic", "buddhist"]
    assert result["query"] == "refusing gracefully"


@pytest.mark.asyncio
async def test_intake_initialises_rewrite_count():
    from soulra.graph.nodes.intake import create_intake_node
    mock_llm = make_intake_llm_response([], "query")
    intake = create_intake_node(mock_llm)
    result = await intake(_make_empty_state())
    assert result["rewrite_count"] == 0


def test_intake_node_is_async():
    """intake node function must be async def so it doesn't block the event loop."""
    from soulra.graph.nodes.intake import create_intake_node
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = MagicMock()
    intake = create_intake_node(mock_llm)
    assert asyncio.iscoroutinefunction(intake), \
        "intake node must be async def — sync def blocks the asyncio event loop"
