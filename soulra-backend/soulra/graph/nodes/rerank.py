from langchain_core.documents import Document
from soulra.core.logging import logger
from soulra.graph.state import SoulraState


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def _near_dedup(docs: list[Document], threshold: float = 0.8) -> list[Document]:
    accepted: list[Document] = []
    for doc in docs:
        lead = doc.page_content[:100]
        if not any(_jaccard(lead, a.page_content[:100]) > threshold for a in accepted):
            accepted.append(doc)
    return accepted


def _u_shape(docs: list[Document]) -> list[Document]:
    n = len(docs)
    if n == 0:
        return []
    result: list[Document | None] = [None] * n
    front, back = 0, n - 1
    for i, doc in enumerate(docs):
        if i % 2 == 0:
            result[front] = doc
            front += 1
        else:
            result[back] = doc
            back -= 1
    return [d for d in result if d is not None]


def create_rerank_node(cohere_client, input_key: str = "retrieved_docs", output_key: str = "reranked_docs"):
    async def rerank(state: SoulraState) -> dict:
        docs: list[Document] = state.get(input_key) or []
        if not docs:
            return {output_key: []}

        try:
            response = await cohere_client.rerank(
                model="rerank-v3.5",
                query=state["query"],
                documents=[d.page_content for d in docs],
                top_n=min(5, len(docs)),
            )
            ranked = [docs[r.index] for r in response.results]
        except Exception as exc:
            logger.warning("rerank_failed_fallback", error=str(exc))
            ranked = docs[:5]

        deduped = _near_dedup(ranked)
        shaped = _u_shape(deduped)
        return {output_key: shaped}

    return rerank
