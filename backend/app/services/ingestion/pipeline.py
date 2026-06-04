from typing import IO
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from app.services.ingestion.pdf_parser import extract_text_from_pdf
from app.services.ingestion.chunker import chunk_documents
from app.core.exceptions import IngestionError
from app.core.logging import logger


class IngestionPipeline:
    def __init__(self, vectorstore: PGVector, embeddings: OpenAIEmbeddings):
        self.vectorstore = vectorstore
        self.embeddings = embeddings

    async def run(
        self,
        file: IO[bytes],
        filename: str,
        metadata: dict,
    ) -> dict:
        try:
            logger.info("ingestion_started", filename=filename)
            documents = extract_text_from_pdf(file, metadata=metadata)
            if not documents:
                raise IngestionError(f"No extractable text found in {filename}")

            chunks = chunk_documents(documents)
            if not chunks:
                raise IngestionError(f"No chunks produced from {filename}")

            await self.vectorstore.aadd_documents(chunks)
            logger.info("ingestion_complete", filename=filename, chunks=len(chunks))
            return {"chunks_created": len(chunks), "tokens_used": 0}
        except IngestionError:
            raise
        except Exception as e:
            logger.error("ingestion_failed", filename=filename, error=str(e))
            raise IngestionError(f"Ingestion failed for {filename}: {e}") from e
