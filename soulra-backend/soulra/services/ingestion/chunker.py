from datetime import datetime, timezone

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    length_function=len,
)


def chunk_documents(documents: list[Document]) -> list[Document]:
    now = datetime.now(timezone.utc).isoformat()
    chunks = _splitter.split_documents(documents)
    for chunk in chunks:
        chunk.metadata.setdefault("ingested_at", now)
    return [c for c in chunks if c.page_content.strip()]
