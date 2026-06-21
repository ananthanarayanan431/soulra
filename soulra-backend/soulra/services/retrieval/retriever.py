import hashlib

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
        user_id: str | None = None,
        k: int = 5,
    ) -> list[Document]:
        try:
            kwargs: dict = {"k": k}
            filter_dict: dict = {}
            if tradition_filter:
                filter_dict["tradition"] = tradition_filter
            if user_id:
                filter_dict["user_id"] = user_id
            if filter_dict:
                kwargs["filter"] = filter_dict
            return await self.vectorstore.asimilarity_search(query, **kwargs)
        except Exception as e:
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]
            logger.error("retrieval_failed", query_hash=query_hash, error=str(e))
            raise RetrievalError(f"Vector search failed: {e}") from e
