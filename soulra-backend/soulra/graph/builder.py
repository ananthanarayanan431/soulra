from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_openai import ChatOpenAI

from soulra.graph.state import SoulraState
from soulra.graph.edges import route_after_grade
from soulra.graph.nodes.intake import create_intake_node
from soulra.graph.nodes.retrieve import create_retrieve_node
from soulra.graph.nodes.rerank import create_rerank_node
from soulra.graph.nodes.grade import create_grade_node
from soulra.graph.nodes.rewrite import create_rewrite_node
from soulra.graph.nodes.clarify import create_clarify_node
from soulra.graph.nodes.synthesize import create_synthesize_node
from soulra.services.retrieval.retriever import WisdomRetriever


def build_graph(
    retriever: WisdomRetriever,
    fast_llm: ChatOpenAI,
    smart_llm: ChatOpenAI,
    checkpointer: BaseCheckpointSaver,
    cohere_client,
):
    workflow = StateGraph(SoulraState)

    workflow.add_node("intake", create_intake_node(fast_llm))
    workflow.add_node("retrieve", create_retrieve_node(retriever))
    workflow.add_node("rerank", create_rerank_node(cohere_client, input_key="retrieved_docs", output_key="reranked_docs"))
    workflow.add_node("grade_docs", create_grade_node(fast_llm))
    workflow.add_node("rewrite_query", create_rewrite_node(fast_llm))
    workflow.add_node("clarify", create_clarify_node(fast_llm))
    workflow.add_node("retrieve_refined", create_retrieve_node(retriever, output_key="refined_docs"))
    workflow.add_node("rerank_refined", create_rerank_node(cohere_client, input_key="refined_docs", output_key="reranked_docs"))
    workflow.add_node("synthesize", create_synthesize_node(smart_llm))

    workflow.add_edge(START, "intake")
    workflow.add_edge("intake", "retrieve")
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "grade_docs")
    workflow.add_conditional_edges("grade_docs", route_after_grade)
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("clarify", "retrieve_refined")
    workflow.add_edge("retrieve_refined", "rerank_refined")
    workflow.add_edge("rerank_refined", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["retrieve_refined"],
    )
