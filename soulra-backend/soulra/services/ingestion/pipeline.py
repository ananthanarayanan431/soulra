from typing import IO
import tiktoken
from langchain_postgres import PGVector
from langchain_core.documents import Document
from soulra.services.ingestion.pdf_parser import extract_text_from_pdf
from soulra.services.ingestion.chunker import chunk_documents
from soulra.core.exceptions import IngestionError
from soulra.core.logging import logger

_ENC = tiktoken.get_encoding("cl100k_base")


def _count_tokens(chunks: list[Document]) -> int:
    return sum(len(_ENC.encode(c.page_content)) for c in chunks)


def _extract_documents(file: IO[bytes], filename: str, metadata: dict) -> list[Document]:
    """Route to PDF parser or plain text reader based on filename extension."""
    if filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file, metadata=metadata)
    # Plain text fallback (for .txt, URLs, raw text ingestion)
    raw = file.read()
    text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        return []
    return [Document(page_content=text, metadata={**metadata, "page": 1})]


class IngestionPipeline:
    def __init__(self, vectorstore: PGVector):
        self.vectorstore = vectorstore

    async def run(
        self,
        file: IO[bytes],
        filename: str,
        metadata: dict,
    ) -> dict:
        try:
            logger.info("ingestion_started", filename=filename)
            documents = _extract_documents(file, filename, metadata)
            if not documents:
                raise IngestionError(f"No extractable text found in {filename}")

            chunks = chunk_documents(documents)
            if not chunks:
                raise IngestionError(f"No chunks produced from {filename}")

            tokens_used = _count_tokens(chunks)
            await self.vectorstore.aadd_documents(chunks)
            logger.info(
                "ingestion_complete", filename=filename, chunks=len(chunks), tokens=tokens_used
            )
            return {"chunks_created": len(chunks), "tokens_used": tokens_used}
        except IngestionError:
            raise
        except Exception as e:
            logger.error("ingestion_failed", filename=filename, error=str(e))
            raise IngestionError(f"Ingestion failed for {filename}: {e}") from e
