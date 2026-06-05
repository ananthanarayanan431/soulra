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
    from soulra.graph.nodes.synthesize import create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep

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
    from soulra.graph.nodes.synthesize import create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep

    mock_output = SynthesizeOutput(
        tradition_cards=[TraditionCard(tradition="Buddhist", author="Pema", quote="q", citation="c", analysis="a")],
        action_steps=[ActionStep(n="01", title="t", body="b"), ActionStep(n="02", title="t2", body="b2"), ActionStep(n="03", title="t3", body="b3")],
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=mock_output)
    synthesize = create_synthesize_node(mock_llm)

    # refined_docs is None — should fall back to retrieved_docs
    result = await synthesize(_make_state(refined_docs=None))
    assert len(result["tradition_cards"]) == 1


@pytest.mark.asyncio
async def test_synthesize_uses_refined_docs_not_retrieved_when_refined_is_empty():
    """When refined_docs is [] (retrieve_refined ran but found nothing), we should NOT
    fall back to retrieved_docs — that would silently ignore the user's chip selection.
    Fall back to retrieved_docs only when refined_docs is None (never ran)."""
    from soulra.graph.nodes.synthesize import create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep

    calls = []

    class MockLLM:
        def with_structured_output(self, schema):
            return self

        async def ainvoke(self, prompt):
            calls.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[TraditionCard(tradition="Stoic", author="Marcus", quote="q", citation="c", analysis="a")],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(MockLLM())

    retrieved_doc = Document(page_content="PRE-CLARIFICATION doc", metadata={"tradition": "stoic"})
    state = {
        "situation": "test",
        "refined_docs": [],   # explicitly empty — retrieve_refined ran but found nothing
        "retrieved_docs": [retrieved_doc],
        "clarify_answer": "Something inside me",
        "tradition_hints": [], "query": "", "grade_result": "",
        "clarify_question": "", "clarify_chips": [], "tradition_cards": [],
        "action_steps": [], "messages": [], "rewrite_count": 0,
    }
    await synthesize(state)

    # After fix: when refined_docs=[], we should NOT use "PRE-CLARIFICATION doc"
    assert "PRE-CLARIFICATION" not in calls[0], \
        "Bug: empty refined_docs fell back to retrieved_docs, ignoring clarification"


@pytest.mark.asyncio
async def test_synthesize_caps_document_content_at_500_chars():
    """Each document in the prompt should be capped at 500 chars to prevent context overflow."""
    from soulra.graph.nodes.synthesize import create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep

    captured_prompt = []

    class MockLLM:
        def with_structured_output(self, schema):
            return self

        async def ainvoke(self, prompt):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[TraditionCard(tradition="S", author="A", quote="q", citation="c", analysis="a")],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(MockLLM())
    long_content = "X" * 2000  # 2000 chars, should be capped at 500
    state = {
        "situation": "test",
        "refined_docs": None,
        "retrieved_docs": [Document(page_content=long_content, metadata={"tradition": "stoic", "citation": "ref"})],
        "clarify_answer": "yes",
        "tradition_hints": [], "query": "", "grade_result": "",
        "clarify_question": "", "clarify_chips": [], "tradition_cards": [],
        "action_steps": [], "messages": [], "rewrite_count": 0,
    }
    await synthesize(state)

    assert captured_prompt, "LLM was not called"
    prompt = captured_prompt[0]
    # The 2000-char content should be truncated; verify "X"*501 is not in prompt
    assert "X" * 501 not in prompt, "Document content was not capped at 500 chars"
    assert "X" * 499 in prompt, "Document content was truncated too aggressively"
