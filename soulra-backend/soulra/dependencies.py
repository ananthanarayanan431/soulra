# app/dependencies.py
from functools import lru_cache
from soulra.config import settings


@lru_cache
def get_embeddings():
    from soulra.services.llm.factory import make_embeddings
    return make_embeddings()


@lru_cache
def get_vectorstore():
    from langchain_postgres import PGVector
    return PGVector(
        embeddings=get_embeddings(),
        collection_name="wisdom_passages",
        connection=settings.database_url,
    )


@lru_cache
def get_retriever():
    from soulra.services.retrieval.retriever import WisdomRetriever
    return WisdomRetriever(vectorstore=get_vectorstore())


@lru_cache
def get_smart_llm():
    from soulra.services.llm.factory import make_smart_llm
    return make_smart_llm()


@lru_cache
def get_fast_llm():
    from soulra.services.llm.factory import make_fast_llm
    return make_fast_llm()
