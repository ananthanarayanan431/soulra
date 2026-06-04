# tests/unit/test_node_retrieve_grade.py
import pytest
from unittest.mock import MagicMock
from langchain_core.documents import Document


def _make_state(**overrides):
    base = {
        "situation": "I keep saying yes to projects.",
        "query": "refusing gracefully",
        "tradition_hints": ["stoic", "buddhist"],
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
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_retrieve_node_calls_retriever_for_each_hint(mock_vectorstore):
    from app.graph.nodes.retrieve import create_retrieve_node
    from app.services.retrieval.retriever import WisdomRetriever
    retriever = WisdomRetriever(mock_vectorstore)
    retrieve = create_retrieve_node(retriever)

    result = await retrieve(_make_state())
    assert len(result["retrieved_docs"]) > 0
    # called once per tradition_hint ("stoic", "buddhist")
    assert mock_vectorstore.asimilarity_search.call_count == 2


@pytest.mark.asyncio
async def test_retrieve_node_deduplicates_documents(mock_vectorstore):
    from app.graph.nodes.retrieve import create_retrieve_node
    from app.services.retrieval.retriever import WisdomRetriever
    from unittest.mock import AsyncMock
    # Both hints return the same document
    dup_doc = Document(page_content="Stoic wisdom.", metadata={"tradition": "stoic"})
    mock_vectorstore.asimilarity_search = AsyncMock(return_value=[dup_doc])
    retriever = WisdomRetriever(mock_vectorstore)
    retrieve = create_retrieve_node(retriever)
    result = await retrieve(_make_state())
    assert len(result["retrieved_docs"]) == 1  # deduplicated


def test_grade_node_returns_relevant_when_majority_score_yes():
    from app.graph.nodes.grade import create_grade_node, GradeOutput
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value=GradeOutput(score="yes"))
    grade = create_grade_node(mock_llm)

    docs = [
        Document(page_content="Stoic wisdom.", metadata={}),
        Document(page_content="More Stoic wisdom.", metadata={}),
    ]
    result = grade(_make_state(retrieved_docs=docs))
    assert result["grade_result"] == "relevant"


def test_grade_node_returns_not_relevant_when_majority_score_no():
    from app.graph.nodes.grade import create_grade_node, GradeOutput
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(return_value=GradeOutput(score="no"))
    grade = create_grade_node(mock_llm)

    docs = [Document(page_content="Recipes for pasta.", metadata={})]
    result = grade(_make_state(retrieved_docs=docs))
    assert result["grade_result"] == "not_relevant"


def test_grade_node_returns_not_relevant_for_empty_docs():
    from app.graph.nodes.grade import create_grade_node
    mock_llm = MagicMock()
    grade = create_grade_node(mock_llm)
    result = grade(_make_state(retrieved_docs=[]))
    assert result["grade_result"] == "not_relevant"
