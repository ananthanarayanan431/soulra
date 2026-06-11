from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr
from soulra.config import settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def make_chat_llm(model: str, streaming: bool = True) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=OPENROUTER_BASE,
        api_key=SecretStr(settings.openrouter_api_key),
        streaming=streaming,
        temperature=0,
    )


def make_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=OPENROUTER_BASE,
        api_key=SecretStr(settings.openrouter_api_key),
    )


def make_smart_llm(streaming: bool = True) -> ChatOpenAI:
    return make_chat_llm(settings.smart_model, streaming=streaming)


def make_fast_llm(streaming: bool = True) -> ChatOpenAI:
    return make_chat_llm(settings.fast_model, streaming=streaming)
