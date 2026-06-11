import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


def _doc(content: str, **meta) -> Document:
    return Document(page_content=content, metadata=meta)


# ── _jaccard ────────────────────────────────────────────────────────────────


def test_jaccard_identical_texts():
    from soulra.graph.nodes.rerank import _jaccard

    assert _jaccard("the quick brown fox", "the quick brown fox") == 1.0


def test_jaccard_no_overlap():
    from soulra.graph.nodes.rerank import _jaccard

    assert _jaccard("alpha beta", "gamma delta") == 0.0


def test_jaccard_partial_overlap():
    from soulra.graph.nodes.rerank import _jaccard

    # shared: {"the"} — union: {"the", "cat", "dog"} → 1/3
    score = _jaccard("the cat", "the dog")
    assert abs(score - 1 / 3) < 1e-6


def test_jaccard_empty_strings():
    from soulra.graph.nodes.rerank import _jaccard

    assert _jaccard("", "") == 1.0


# ── _near_dedup ──────────────────────────────────────────────────────────────


def test_near_dedup_keeps_distinct_docs():
    from soulra.graph.nodes.rerank import _near_dedup

    docs = [_doc("Stoic wisdom about courage"), _doc("Buddhist teaching on impermanence")]
    result = _near_dedup(docs)
    assert len(result) == 2


def test_near_dedup_drops_near_duplicate():
    from soulra.graph.nodes.rerank import _near_dedup

    # 100 chars of identical leading content (slice size)
    base = "word " * 20  # 100 chars of shared content
    docs = [_doc(base + " extra_a"), _doc(base + " extra_b")]
    result = _near_dedup(docs)
    # Second doc is a near-duplicate of the first — should be dropped
    assert len(result) == 1
    assert result[0].page_content == docs[0].page_content


def test_near_dedup_keeps_first_and_drops_later():
    from soulra.graph.nodes.rerank import _near_dedup

    base = "identical content " * 7
    d1 = _doc(base + "end1")
    d2 = _doc(base + "end2")
    d3 = _doc("completely different wisdom passage about impermanence")
    result = _near_dedup([d1, d2, d3])
    assert len(result) == 2
    assert result[0] is d1
    assert result[1] is d3


# ── _u_shape ────────────────────────────────────────────────────────────────


def test_u_shape_empty():
    from soulra.graph.nodes.rerank import _u_shape

    assert _u_shape([]) == []


def test_u_shape_single_doc():
    from soulra.graph.nodes.rerank import _u_shape

    d = _doc("only doc")
    assert _u_shape([d]) == [d]


def test_u_shape_two_docs():
    from soulra.graph.nodes.rerank import _u_shape

    d1, d2 = _doc("rank1"), _doc("rank2")
    result = _u_shape([d1, d2])
    # rank1 → slot 0, rank2 → slot 1 (last)
    assert result == [d1, d2]


def test_u_shape_three_docs():
    from soulra.graph.nodes.rerank import _u_shape

    d1, d2, d3 = _doc("r1"), _doc("r2"), _doc("r3")
    result = _u_shape([d1, d2, d3])
    # r1 → 0, r2 → 2 (last), r3 → 1 (middle)
    assert result == [d1, d3, d2]


def test_u_shape_five_docs():
    from soulra.graph.nodes.rerank import _u_shape

    docs = [_doc(f"r{i}") for i in range(1, 6)]
    result = _u_shape(docs)
    # slot 0=r1, slot 1=r3, slot 2=r5, slot 3=r4, slot 4=r2
    assert result[0].page_content == "r1"  # most relevant → first
    assert result[4].page_content == "r2"  # 2nd most relevant → last
    assert result[2].page_content == "r5"  # least relevant → middle


# ── rerank node ──────────────────────────────────────────────────────────────


def _make_state(**overrides):
    base = {
        "situation": "I feel overwhelmed",
        "query": "equanimity under pressure",
        "tradition_hints": ["stoic"],
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
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_rerank_node_empty_docs_returns_empty():
    from soulra.graph.nodes.rerank import create_rerank_node

    mock_cohere = MagicMock()
    node = create_rerank_node(mock_cohere)
    result = await node(_make_state(retrieved_docs=[]))
    assert result == {"reranked_docs": []}
    mock_cohere.rerank.assert_not_called()


@pytest.mark.asyncio
async def test_rerank_node_calls_cohere_and_reorders():
    from soulra.graph.nodes.rerank import create_rerank_node

    d0 = _doc("least relevant passage")
    d1 = _doc("most relevant stoic passage about equanimity")
    d2 = _doc("moderately relevant passage")

    # Cohere ranks: index 1 first, index 2 second, index 0 third
    mock_result = [
        MagicMock(index=1, relevance_score=0.95),
        MagicMock(index=2, relevance_score=0.70),
        MagicMock(index=0, relevance_score=0.30),
    ]
    mock_cohere = MagicMock()
    mock_cohere.rerank = AsyncMock(return_value=MagicMock(results=mock_result))

    node = create_rerank_node(mock_cohere)
    state = _make_state(retrieved_docs=[d0, d1, d2])
    result = await node(state)

    reranked = result["reranked_docs"]
    # After U-shape with 3 docs: rank1→slot0, rank2→slot2(last), rank3→slot1
    assert reranked[0] is d1  # most relevant at front
    assert reranked[-1] is d2  # 2nd most relevant at back
    mock_cohere.rerank.assert_called_once_with(
        model="rerank-v3.5",
        query="equanimity under pressure",
        documents=[
            "least relevant passage",
            "most relevant stoic passage about equanimity",
            "moderately relevant passage",
        ],
        top_n=3,
    )


@pytest.mark.asyncio
async def test_rerank_node_falls_back_on_cohere_failure():
    from soulra.graph.nodes.rerank import create_rerank_node

    docs = [_doc(f"doc{i}") for i in range(7)]
    mock_cohere = MagicMock()
    mock_cohere.rerank = AsyncMock(side_effect=Exception("API unavailable"))

    node = create_rerank_node(mock_cohere)
    result = await node(_make_state(retrieved_docs=docs))

    # graceful degradation: first 5 docs passed through _near_dedup and _u_shape
    assert len(result["reranked_docs"]) == 5
    assert result["reranked_docs"][0] is docs[0]


@pytest.mark.asyncio
async def test_rerank_node_uses_custom_input_output_keys():
    from soulra.graph.nodes.rerank import create_rerank_node

    d = _doc("refined passage")
    mock_cohere = MagicMock()
    mock_cohere.rerank = AsyncMock(
        return_value=MagicMock(results=[MagicMock(index=0, relevance_score=0.9)])
    )
    node = create_rerank_node(mock_cohere, input_key="refined_docs", output_key="reranked_docs")
    state = _make_state(refined_docs=[d])
    result = await node(state)
    assert "reranked_docs" in result
    assert len(result["reranked_docs"]) == 1


def test_rerank_node_is_async():
    from soulra.graph.nodes.rerank import create_rerank_node

    node = create_rerank_node(MagicMock())
    assert asyncio.iscoroutinefunction(node)
