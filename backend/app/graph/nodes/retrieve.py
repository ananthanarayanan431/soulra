# app/graph/nodes/retrieve.py
from langchain_core.documents import Document
from app.graph.state import SoulraState
from app.services.retrieval.retriever import WisdomRetriever


def create_retrieve_node(retriever: WisdomRetriever):
    async def retrieve(state: SoulraState) -> dict:
        query = state["query"]
        hints = state["tradition_hints"] or [None]
        all_docs: list[Document] = []
        seen_contents: set[str] = set()

        for hint in hints:
            docs = await retriever.search(query, tradition_filter=hint, k=4)
            for doc in docs:
                if doc.page_content not in seen_contents:
                    all_docs.append(doc)
                    seen_contents.add(doc.page_content)

        return {"retrieved_docs": all_docs}

    return retrieve
