from langchain_core.documents import Document
from langchain_postgres import PGVector
from soulra.core.exceptions import RetrievalError
from soulra.core.logging import logger


class WisdomRetriever:
    def __init__(self, vectorstore: PGVector):
        self.vectorstore = vectorstore

    async def search(
        self,
        query: str,
        tradition_filter: str | None = None,
        k: int = 5,
    ) -> list[Document]:
        try:
            kwargs: dict = {"k": k}
            if tradition_filter:
                kwargs["filter"] = {"tradition": tradition_filter}
            return await self.vectorstore.asimilarity_search(query, **kwargs)
        except Exception as e:
            logger.error("retrieval_failed", query=query, error=str(e))
            raise RetrievalError(f"Vector search failed: {e}") from e
