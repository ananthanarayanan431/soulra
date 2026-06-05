import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


@pytest.mark.asyncio
async def test_search_returns_documents(mock_vectorstore):
    from soulra.services.retrieval.retriever import WisdomRetriever
    retriever = WisdomRetriever(vectorstore=mock_vectorstore)
    results = await retriever.search("How to refuse gracefully?", k=5)
    assert len(results) == 2
    assert all(isinstance(d, Document) for d in results)


@pytest.mark.asyncio
async def test_search_with_tradition_filter(mock_vectorstore):
    from soulra.services.retrieval.retriever import WisdomRetriever
    retriever = WisdomRetriever(vectorstore=mock_vectorstore)
    await retriever.search("wisdom", tradition_filter="stoic", k=3)
    call_kwargs = mock_vectorstore.asimilarity_search.call_args.kwargs
    assert call_kwargs.get("filter") == {"tradition": "stoic"}


@pytest.mark.asyncio
async def test_search_raises_retrieval_error_on_failure():
    from soulra.services.retrieval.retriever import WisdomRetriever
    from soulra.core.exceptions import RetrievalError
    bad_vs = MagicMock()
    bad_vs.asimilarity_search = AsyncMock(side_effect=Exception("connection refused"))
    retriever = WisdomRetriever(vectorstore=bad_vs)
    with pytest.raises(RetrievalError):
        await retriever.search("query")
