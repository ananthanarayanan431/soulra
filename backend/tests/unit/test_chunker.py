from langchain_core.documents import Document
from app.services.ingestion.chunker import chunk_documents


def test_chunk_documents_splits_long_text():
    long_text = "word " * 300  # ~1500 chars
    docs = [Document(page_content=long_text, metadata={"tradition": "stoic"})]
    chunks = chunk_documents(docs)
    assert len(chunks) > 1


def test_chunk_documents_preserves_metadata():
    docs = [Document(page_content="Short text.", metadata={"tradition": "stoic", "author": "Marcus"})]
    chunks = chunk_documents(docs)
    assert all(c.metadata["tradition"] == "stoic" for c in chunks)
    assert all(c.metadata["author"] == "Marcus" for c in chunks)


def test_chunk_documents_no_empty_chunks():
    docs = [Document(page_content="A" * 1000, metadata={})]
    chunks = chunk_documents(docs)
    assert all(len(c.page_content.strip()) > 0 for c in chunks)
