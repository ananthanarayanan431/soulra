# tests/unit/test_node_synthesize.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


def _make_state(**overrides):
    docs = [
        Document(page_content="Stoic wisdom.", metadata={"tradition": "stoic", "author": "Marcus Aurelius", "citation": "Meditations 6.13"}),
    ]
    base = {
        "situation": "I say yes too much.",
        "query": "refusing",
        "tradition_hints": ["stoic"],
        "retrieved_docs": docs,
        "grade_result": "relevant",
        "clarify_question": "Is this internal?",
        "clarify_chips": ["Yes", "No"],
        "clarify_answer": "Yes",
        "refined_docs": docs,
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
        "rewrite_count": 0,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_synthesize_produces_tradition_cards_and_action_steps():
    from app.graph.nodes.synthesize import create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep

    mock_output = SynthesizeOutput(
        tradition_cards=[
            TraditionCard(
                tradition="Stoic",
                author="Marcus Aurelius",
                quote="You always own the option of having no opinion.",
                citation="Meditations 6.13",
                analysis="The Stoic move is to notice the request comes from outside.",
            )
        ],
        action_steps=[
            ActionStep(n="01", title="Notice the moment of yes", body="Pause for one breath."),
            ActionStep(n="02", title="Name what you want", body="Write one sentence."),
            ActionStep(n="03", title="Say a small no", body="Decline one small thing."),
        ],
    )

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=mock_output)
    synthesize = create_synthesize_node(mock_llm)

    result = await synthesize(_make_state())
    assert len(result["tradition_cards"]) == 1
    assert result["tradition_cards"][0]["tradition"] == "Stoic"
    assert len(result["action_steps"]) == 3


@pytest.mark.asyncio
async def test_synthesize_falls_back_to_retrieved_docs_when_no_refined():
    from app.graph.nodes.synthesize import create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep

    mock_output = SynthesizeOutput(
        tradition_cards=[TraditionCard(tradition="Buddhist", author="Pema", quote="q", citation="c", analysis="a")],
        action_steps=[ActionStep(n="01", title="t", body="b"), ActionStep(n="02", title="t2", body="b2"), ActionStep(n="03", title="t3", body="b3")],
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=mock_output)
    synthesize = create_synthesize_node(mock_llm)

    # refined_docs is empty — should fall back to retrieved_docs
    result = await synthesize(_make_state(refined_docs=[]))
    assert len(result["tradition_cards"]) == 1
