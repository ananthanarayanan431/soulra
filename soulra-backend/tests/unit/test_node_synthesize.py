import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


def _make_state(**overrides):
    docs = [
        Document(
            page_content="Stoic wisdom on equanimity.",
            metadata={
                "tradition": "stoic",
                "author": "Marcus Aurelius",
                "source": "Meditations",
                "era": "170 AD",
                "citation": "Meditations 6.13",
                "ingested_at": "2026-06-06T00:00:00+00:00",
            },
        ),
    ]
    base = {
        "situation": "I say yes too much.",
        "query": "refusing",
        "tradition_hints": ["stoic"],
        "retrieved_docs": docs,
        "reranked_docs": docs,
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


def _mock_llm_with_output(output):
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=output)
    return mock_llm


@pytest.mark.asyncio
async def test_synthesize_produces_tradition_cards_and_action_steps():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node,
        SynthesizeOutput,
        TraditionCard,
        ActionStep,
    )

    mock_output = SynthesizeOutput(
        tradition_cards=[
            TraditionCard(
                tradition="Stoic",
                author="Marcus Aurelius",
                quote="You always own the option of having no opinion.",
                citation="Meditations 6.13",
                analysis="The Stoic move is to pause before committing.",
                source_passage="You always own the option of having no opinion.",
            )
        ],
        action_steps=[
            ActionStep(n="01", title="Notice the moment of yes", body="Pause for one breath."),
            ActionStep(n="02", title="Name what you want", body="Write one sentence."),
            ActionStep(n="03", title="Say a small no", body="Decline one small thing."),
        ],
    )
    synthesize = create_synthesize_node(_mock_llm_with_output(mock_output))
    result = await synthesize(_make_state(), {})
    assert len(result["tradition_cards"]) == 1
    assert result["tradition_cards"][0]["tradition"] == "Stoic"
    assert len(result["action_steps"]) == 3


@pytest.mark.asyncio
async def test_synthesize_tradition_card_has_source_passage():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node,
        SynthesizeOutput,
        TraditionCard,
        ActionStep,
    )

    mock_output = SynthesizeOutput(
        tradition_cards=[
            TraditionCard(
                tradition="Buddhist",
                author="Pema Chödrön",
                quote="Lean into the sharp points.",
                citation="When Things Fall Apart",
                analysis="Resistance makes things worse.",
                source_passage="Lean into the sharp points and fully experience them.",
            )
        ],
        action_steps=[
            ActionStep(n="01", title="t1", body="b1"),
            ActionStep(n="02", title="t2", body="b2"),
            ActionStep(n="03", title="t3", body="b3"),
        ],
    )
    synthesize = create_synthesize_node(_mock_llm_with_output(mock_output))
    result = await synthesize(_make_state(), {})
    card = result["tradition_cards"][0]
    assert "source_passage" in card, (
        "TraditionCard must include source_passage for grounding verification"
    )
    assert card["source_passage"]  # must be non-empty


@pytest.mark.asyncio
async def test_synthesize_reads_from_reranked_docs():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node,
        SynthesizeOutput,
        TraditionCard,
        ActionStep,
    )

    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self

        async def ainvoke(self, prompt, config=None):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[
                    TraditionCard(
                        tradition="S",
                        author="A",
                        quote="q",
                        citation="c",
                        analysis="a",
                        source_passage="sp",
                    )
                ],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    reranked_doc = Document(
        page_content="RERANKED wisdom.",
        metadata={
            "tradition": "stoic",
            "author": "Marcus",
            "source": "Med",
            "era": "170AD",
            "ingested_at": "2026-06-06T00:00:00+00:00",
        },
    )
    await synthesize(_make_state(reranked_docs=[reranked_doc]), {})
    assert "RERANKED wisdom." in captured_prompt[0], "synthesize must read from reranked_docs"


@pytest.mark.asyncio
async def test_synthesize_context_label_includes_metadata_fields():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node,
        SynthesizeOutput,
        TraditionCard,
        ActionStep,
    )

    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self

        async def ainvoke(self, prompt, config=None):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[
                    TraditionCard(
                        tradition="S",
                        author="A",
                        quote="q",
                        citation="c",
                        analysis="a",
                        source_passage="sp",
                    )
                ],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    doc = Document(
        page_content="wisdom here",
        metadata={
            "tradition": "stoic",
            "author": "Marcus Aurelius",
            "source": "Meditations",
            "era": "170 AD",
            "ingested_at": "2026-06-06T00:00:00+00:00",
        },
    )
    await synthesize(_make_state(reranked_docs=[doc]), {})
    prompt = captured_prompt[0]
    assert "Marcus Aurelius" in prompt
    assert "Meditations" in prompt
    assert "170 AD" in prompt
    assert "2026-06-06" in prompt  # ingested_at visible to LLM


@pytest.mark.asyncio
async def test_synthesize_prompt_contains_grounding_instruction():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node,
        SynthesizeOutput,
        TraditionCard,
        ActionStep,
    )

    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self

        async def ainvoke(self, prompt, config=None):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[
                    TraditionCard(
                        tradition="S",
                        author="A",
                        quote="q",
                        citation="c",
                        analysis="a",
                        source_passage="sp",
                    )
                ],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    await synthesize(_make_state(), {})
    prompt = captured_prompt[0]
    assert "ONLY" in prompt, "Prompt must contain strong grounding instruction"
    assert "verbatim" in prompt.lower(), "Prompt must require verbatim quotes"


@pytest.mark.asyncio
async def test_synthesize_caps_content_at_500_chars():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node,
        SynthesizeOutput,
        TraditionCard,
        ActionStep,
    )

    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self

        async def ainvoke(self, prompt, config=None):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[
                    TraditionCard(
                        tradition="S",
                        author="A",
                        quote="q",
                        citation="c",
                        analysis="a",
                        source_passage="sp",
                    )
                ],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    doc = Document(
        page_content="X" * 2000,
        metadata={
            "tradition": "stoic",
            "author": "A",
            "source": "B",
            "era": "?",
            "ingested_at": "2026-06-06T00:00:00+00:00",
        },
    )
    await synthesize(_make_state(reranked_docs=[doc]), {})
    assert "X" * 501 not in captured_prompt[0]
    assert "X" * 499 in captured_prompt[0]


@pytest.mark.asyncio
async def test_synthesize_empty_reranked_docs_sends_fallback_marker():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node,
        SynthesizeOutput,
        TraditionCard,
        ActionStep,
    )

    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self

        async def ainvoke(self, prompt, config=None):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[
                    TraditionCard(
                        tradition="S",
                        author="A",
                        quote="q",
                        citation="c",
                        analysis="a",
                        source_passage="sp",
                    )
                ],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    result = await synthesize(_make_state(reranked_docs=[]), {})
    assert "No source passages available" in captured_prompt[0], (
        "Empty reranked_docs must send fallback marker to LLM"
    )
    assert "tradition_cards" in result
