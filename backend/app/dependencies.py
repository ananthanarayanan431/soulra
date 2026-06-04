from functools import lru_cache
from app.config import settings


@lru_cache
def get_vectorstore():
    from langchain_postgres import PGVector
    from app.services.llm.factory import make_embeddings
    return PGVector(
        embeddings=make_embeddings(),
        collection_name="wisdom_passages",
        connection=settings.database_url,
    )
