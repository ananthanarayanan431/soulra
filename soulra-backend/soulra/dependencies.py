# app/dependencies.py
from functools import lru_cache


@lru_cache
def get_embeddings():
    from soulra.services.llm.factory import make_embeddings
    return make_embeddings()


# Module-level singletons initialised during app lifespan.
# NOT cached with @lru_cache because PGVector holds async connections
# bound to the event loop at construction time.  Caching them causes
# "attached to a different loop" errors on uvicorn --reload.

_vectorstore = None
_retriever = None


def set_vectorstore(vs) -> None:
    global _vectorstore
    _vectorstore = vs


def set_retriever(r) -> None:
    global _retriever
    _retriever = r


def get_vectorstore():
    if _vectorstore is None:
        raise RuntimeError(
            "Vectorstore not initialised — call set_vectorstore() during app lifespan"
        )
    return _vectorstore


def get_retriever():
    if _retriever is None:
        raise RuntimeError(
            "Retriever not initialised — call set_retriever() during app lifespan"
        )
    return _retriever


@lru_cache
def get_smart_llm():
    from soulra.services.llm.factory import make_smart_llm
    return make_smart_llm()


@lru_cache
def get_fast_llm():
    from soulra.services.llm.factory import make_fast_llm
    return make_fast_llm()


_cohere_client = None


def set_cohere_client(c) -> None:
    global _cohere_client
    _cohere_client = c


def get_cohere_client():
    if _cohere_client is None:
        raise RuntimeError(
            "Cohere client not initialised — call set_cohere_client() during app lifespan"
        )
    return _cohere_client
