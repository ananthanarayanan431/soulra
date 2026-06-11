# app/graph/nodes/retrieve.py
import asyncio
from typing import cast

from langchain_core.documents import Document
from soulra.graph.state import SoulraState
from soulra.services.retrieval.retriever import WisdomRetriever


def create_retrieve_node(retriever: WisdomRetriever, output_key: str = "retrieved_docs"):
    async def retrieve(state: SoulraState) -> dict:
        query = state["query"]
        hints = cast("list[str | None]", state["tradition_hints"] or [None])

        results = await asyncio.gather(
            *[retriever.search(query, tradition_filter=hint, k=10) for hint in hints]
        )

        all_docs: list[Document] = []
        seen_contents: set[str] = set()
        for docs in results:
            for doc in docs:
                if doc.page_content not in seen_contents:
                    all_docs.append(doc)
                    seen_contents.add(doc.page_content)

        return {output_key: all_docs}

    return retrieve
