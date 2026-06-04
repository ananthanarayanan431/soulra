import pytest
import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_pipeline_run_returns_chunk_count(mock_vectorstore):
    from app.services.ingestion.pipeline import IngestionPipeline

    mock_embeddings = MagicMock()
    pipeline = IngestionPipeline(vectorstore=mock_vectorstore, embeddings=mock_embeddings)
    mock_vectorstore.aadd_documents = AsyncMock(return_value=["id1", "id2"])

    with patch("app.services.ingestion.pipeline.extract_text_from_pdf") as mock_parse, \
         patch("app.services.ingestion.pipeline.chunk_documents") as mock_chunk:
        from langchain_core.documents import Document
        mock_parse.return_value = [Document(page_content="text", metadata={})]
        mock_chunk.return_value = [
            Document(page_content="chunk1", metadata={"tradition": "stoic"}),
            Document(page_content="chunk2", metadata={"tradition": "stoic"}),
        ]

        result = await pipeline.run(
            file=io.BytesIO(b"pdf"),
            filename="test.pdf",
            metadata={"tradition": "stoic", "author": "Marcus", "source": "Meditations", "era": "ancient"},
        )

    assert result["chunks_created"] == 2
    mock_vectorstore.aadd_documents.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_run_raises_ingestion_error_on_failure(mock_vectorstore):
    from app.services.ingestion.pipeline import IngestionPipeline
    from app.core.exceptions import IngestionError

    mock_vectorstore.aadd_documents = AsyncMock(side_effect=Exception("DB error"))
    pipeline = IngestionPipeline(vectorstore=mock_vectorstore, embeddings=MagicMock())

    with patch("app.services.ingestion.pipeline.extract_text_from_pdf") as mock_parse, \
         patch("app.services.ingestion.pipeline.chunk_documents") as mock_chunk:
        from langchain_core.documents import Document
        mock_parse.return_value = [Document(page_content="t", metadata={})]
        mock_chunk.return_value = [Document(page_content="c", metadata={})]

        with pytest.raises(IngestionError):
            await pipeline.run(file=io.BytesIO(b"pdf"), filename="f.pdf", metadata={})
