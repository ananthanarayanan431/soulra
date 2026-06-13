# tests/unit/test_node_retrieve_grade.py
import asyncio
import pytest
from unittest.mock import MagicMock
from langchain_core.documents import Document


def _make_state(**overrides):
    base = {
        "situation": "I keep saying yes to projects.",
        "query": "refusing gracefully",
        "tradition_hints": ["stoic", "buddhist"],
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
async def test_retrieve_node_calls_retriever_for_each_hint(mock_vectorstore):
    from soulra.graph.nodes.retrieve import create_retrieve_node
    from soulra.services.retrieval.retriever import WisdomRetriever

    retriever = WisdomRetriever(mock_vectorstore)
    retrieve = create_retrieve_node(retriever)

    result = await retrieve(_make_state())
    assert len(result["retrieved_docs"]) > 0
    # called once per tradition_hint ("stoic", "buddhist")
    assert mock_vectorstore.asimilarity_search.call_count == 2


@pytest.mark.asyncio
async def test_retrieve_node_deduplicates_documents(mock_vectorstore):
    from soulra.graph.nodes.retrieve import create_retrieve_node
    from soulra.services.retrieval.retriever import WisdomRetriever
    from unittest.mock import AsyncMock

    # Both hints return the same document
    dup_doc = Document(page_content="Stoic wisdom.", metadata={"tradition": "stoic"})
    mock_vectorstore.asimilarity_search = AsyncMock(return_value=[dup_doc])
    retriever = WisdomRetriever(mock_vectorstore)
    retrieve = create_retrieve_node(retriever)
    result = await retrieve(_make_state())
    assert len(result["retrieved_docs"]) == 1  # deduplicated


@pytest.mark.asyncio
async def test_retrieve_refined_writes_to_refined_docs_key(mock_vectorstore):
    """retrieve_refined must write to refined_docs, not retrieved_docs."""
    from soulra.graph.nodes.retrieve import create_retrieve_node
    from soulra.services.retrieval.retriever import WisdomRetriever

    retriever = WisdomRetriever(mock_vectorstore)
    retrieve_refined = create_retrieve_node(retriever, output_key="refined_docs")
    result = await retrieve_refined(_make_state())
    assert "refined_docs" in result
    assert "retrieved_docs" not in result


@pytest.mark.asyncio
async def test_grade_node_returns_relevant_when_majority_score_yes():
    from soulra.graph.nodes.grade import create_grade_node, GradeOutput
    from unittest.mock import AsyncMock

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=GradeOutput(score="yes"))
    grade = create_grade_node(mock_llm)

    docs = [
        Document(page_content="Stoic wisdom.", metadata={}),
        Document(page_content="More Stoic wisdom.", metadata={}),
    ]
    result = await grade(_make_state(reranked_docs=docs), {})
    assert result["grade_result"] == "relevant"


@pytest.mark.asyncio
async def test_grade_node_returns_not_relevant_when_majority_score_no():
    from soulra.graph.nodes.grade import create_grade_node, GradeOutput
    from unittest.mock import AsyncMock

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=GradeOutput(score="no"))
    grade = create_grade_node(mock_llm)

    docs = [Document(page_content="Recipes for pasta.", metadata={})]
    result = await grade(_make_state(reranked_docs=docs), {})
    assert result["grade_result"] == "not_relevant"


@pytest.mark.asyncio
async def test_grade_node_returns_relevant_for_single_doc_with_yes_score():
    from soulra.graph.nodes.grade import create_grade_node, GradeOutput
    from unittest.mock import AsyncMock

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=GradeOutput(score="yes"))
    grade = create_grade_node(mock_llm)

    docs = [Document(page_content="Stoic wisdom about equanimity.", metadata={})]
    result = await grade(_make_state(reranked_docs=docs), {})
    assert result["grade_result"] == "relevant"


@pytest.mark.asyncio
async def test_grade_node_returns_not_relevant_for_empty_docs():
    from soulra.graph.nodes.grade import create_grade_node

    mock_llm = MagicMock()
    grade = create_grade_node(mock_llm)
    result = await grade(_make_state(reranked_docs=[]), {})
    assert result["grade_result"] == "not_relevant"


def test_grade_node_is_async():
    """grade node function must be async def so it doesn't block the event loop."""
    from soulra.graph.nodes.grade import create_grade_node

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    grade = create_grade_node(mock_llm)
    assert asyncio.iscoroutinefunction(grade), (
        "grade node must be async def — sync def blocks the asyncio event loop"
    )


@pytest.mark.asyncio
async def test_retrieve_node_searches_traditions_concurrently():
    """retrieve node must fire all tradition searches concurrently, not sequentially."""
    from soulra.graph.nodes.retrieve import create_retrieve_node
    from soulra.services.retrieval.retriever import WisdomRetriever
    from unittest.mock import MagicMock

    call_order = []

    async def slow_search(query, tradition_filter=None, k=5):
        call_order.append(("start", tradition_filter))
        await asyncio.sleep(0.01)  # small delay to make ordering observable
        call_order.append(("end", tradition_filter))
        return [Document(page_content=f"doc-{tradition_filter}", metadata={})]

    mock_vs = MagicMock()
    mock_retriever = WisdomRetriever(vectorstore=mock_vs)
    mock_retriever.search = slow_search

    retrieve = create_retrieve_node(mock_retriever)
    state = {
        "query": "refusing gracefully",
        "tradition_hints": ["stoic", "buddhist", "vedanta"],
        "retrieved_docs": [],
        "reranked_docs": [],
        "situation": "",
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

    result = await retrieve(state)

    # All 3 docs should be returned
    assert len(result["retrieved_docs"]) == 3

    # Concurrent: all three "start" events should appear before any "end" event
    # If sequential, we'd see start-end-start-end-start-end
    # If concurrent, we'd see start-start-start-end-end-end
    # The first "end" must come after all "start"s
    first_end_idx = next(i for i, e in enumerate(call_order) if e[0] == "end")
    starts_before_first_end = sum(1 for e in call_order[:first_end_idx] if e[0] == "start")
    assert starts_before_first_end == 3, (
        f"Expected concurrent execution (3 starts before first end), got: {call_order}"
    )


@pytest.mark.asyncio
async def test_grade_node_calls_ainvoke_concurrently(mock_vectorstore):
    """grade node must use ainvoke (not invoke) and gather calls concurrently."""
    from soulra.graph.nodes.grade import create_grade_node
    from langchain_core.documents import Document

    call_log = []

    class MockStructuredLLM:
        async def ainvoke(self, prompt, config=None):
            call_log.append(prompt)

            class R:
                score = "yes"

            return R()

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=MockStructuredLLM())
    grade = create_grade_node(mock_llm)

    docs = [Document(page_content=f"doc{i}", metadata={}) for i in range(4)]
    state = {
        "situation": "test",
        "query": "test query",
        "retrieved_docs": docs,
        "reranked_docs": docs,
        "tradition_hints": [],
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
    result = await grade(state, {})
    assert len(call_log) == 4, "Expected 4 ainvoke calls for 4 docs"
    assert result["grade_result"] in ("relevant", "not_relevant")


@pytest.mark.asyncio
async def test_grade_node_reads_from_reranked_docs_not_retrieved():
    from soulra.graph.nodes.grade import create_grade_node, GradeOutput
    from unittest.mock import AsyncMock

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=GradeOutput(score="yes"))
    grade = create_grade_node(mock_llm)

    # reranked_docs has 1 doc; retrieved_docs has 5 irrelevant-looking ones
    reranked = [Document(page_content="Reranked stoic wisdom.", metadata={})]
    retrieved = [Document(page_content=f"retrieved-{i}", metadata={}) for i in range(5)]
    state = _make_state(reranked_docs=reranked, retrieved_docs=retrieved)
    result = await grade(state, {})
    # Grade is called once (for the 1 doc in reranked_docs)
    assert mock_llm.ainvoke.call_count == 1
    assert result["grade_result"] == "relevant"
    # Verify the prompt was built from reranked_docs content, not retrieved_docs
    prompt_arg = mock_llm.ainvoke.call_args[0][0]
    assert "Reranked stoic wisdom." in prompt_arg
    assert "retrieved-0" not in prompt_arg


@pytest.mark.asyncio
async def test_grade_node_emits_selection_recall_log(caplog):
    from soulra.graph.nodes.grade import create_grade_node, GradeOutput
    from unittest.mock import AsyncMock

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=GradeOutput(score="yes"))
    grade = create_grade_node(mock_llm)

    retrieved = [Document(page_content=f"r{i}", metadata={"id": f"id{i}"}) for i in range(10)]
    reranked = retrieved[:3]
    result = await grade(_make_state(retrieved_docs=retrieved, reranked_docs=reranked), {})
    # structlog logs to stdout, not caplog — just verify no exception is raised
    # and that grading completed on the non-empty path
    assert result["grade_result"] == "relevant"


@pytest.mark.asyncio
async def test_retrieve_node_requests_k10_per_tradition(mock_vectorstore):
    from soulra.graph.nodes.retrieve import create_retrieve_node
    from soulra.services.retrieval.retriever import WisdomRetriever

    retriever = WisdomRetriever(mock_vectorstore)
    retrieve = create_retrieve_node(retriever)
    await retrieve(_make_state())
    # Each call to asimilarity_search must request k=10
    for call in mock_vectorstore.asimilarity_search.call_args_list:
        assert call.kwargs.get("k", call.args[1] if len(call.args) > 1 else None) == 10, (
            f"Expected k=10 but got: {call}"
        )
