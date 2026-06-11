# tests/unit/test_graph_builder.py
from unittest.mock import MagicMock


def test_graph_builds_without_error():
    from langgraph.checkpoint.memory import MemorySaver
    from soulra.graph.builder import build_graph

    mock_cohere = MagicMock()
    graph = build_graph(
        retriever=MagicMock(),
        fast_llm=MagicMock(),
        smart_llm=MagicMock(),
        checkpointer=MemorySaver(),
        cohere_client=mock_cohere,
    )
    assert graph is not None


def test_graph_contains_rerank_nodes():
    from langgraph.checkpoint.memory import MemorySaver
    from soulra.graph.builder import build_graph

    graph = build_graph(
        retriever=MagicMock(),
        fast_llm=MagicMock(),
        smart_llm=MagicMock(),
        checkpointer=MemorySaver(),
        cohere_client=MagicMock(),
    )
    node_names = set(graph.nodes.keys())
    assert "rerank" in node_names, "Graph must contain a 'rerank' node"
    assert "rerank_refined" in node_names, "Graph must contain a 'rerank_refined' node"


def test_route_after_grade_returns_rewrite_when_not_relevant():
    from soulra.graph.edges import route_after_grade

    state = {
        "grade_result": "not_relevant",
        "rewrite_count": 0,
        "situation": "",
        "tradition_hints": [],
        "query": "",
        "retrieved_docs": [],
        "reranked_docs": [],
        "clarify_question": "",
        "clarify_chips": [],
        "clarify_answer": None,
        "refined_docs": [],
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
    }
    assert route_after_grade(state) == "rewrite_query"


def test_route_after_grade_returns_clarify_when_relevant():
    from soulra.graph.edges import route_after_grade

    state = {
        "grade_result": "relevant",
        "rewrite_count": 0,
        "situation": "",
        "tradition_hints": [],
        "query": "",
        "retrieved_docs": [],
        "reranked_docs": [],
        "clarify_question": "",
        "clarify_chips": [],
        "clarify_answer": None,
        "refined_docs": [],
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
    }
    assert route_after_grade(state) == "clarify"


def test_route_after_grade_forces_clarify_after_max_rewrites():
    from soulra.graph.edges import route_after_grade

    state = {
        "grade_result": "not_relevant",
        "rewrite_count": 2,
        "situation": "",
        "tradition_hints": [],
        "query": "",
        "retrieved_docs": [],
        "reranked_docs": [],
        "clarify_question": "",
        "clarify_chips": [],
        "clarify_answer": None,
        "refined_docs": [],
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
    }
    assert route_after_grade(state) == "clarify"
