import pytest


def test_get_vectorstore_raises_when_not_initialised():
    """get_vectorstore() must raise RuntimeError before set_vectorstore() is called."""
    import soulra.dependencies as deps
    # Reset module state
    deps._vectorstore = None
    with pytest.raises(RuntimeError, match="Vectorstore not initialised"):
        deps.get_vectorstore()


def test_get_vectorstore_returns_value_after_set():
    """set_vectorstore() + get_vectorstore() must return the same object."""
    import soulra.dependencies as deps
    sentinel = object()
    deps.set_vectorstore(sentinel)
    assert deps.get_vectorstore() is sentinel
    deps._vectorstore = None  # cleanup


def test_get_retriever_raises_when_not_initialised():
    """get_retriever() must raise RuntimeError before set_retriever() is called."""
    import soulra.dependencies as deps
    deps._retriever = None
    with pytest.raises(RuntimeError, match="Retriever not initialised"):
        deps.get_retriever()


def test_lru_cache_not_on_vectorstore():
    """get_vectorstore must NOT use @lru_cache (it holds async connections)."""
    import soulra.dependencies as deps
    # lru_cache-decorated functions have a `cache_info` attribute
    assert not hasattr(deps.get_vectorstore, "cache_info"), \
        "get_vectorstore must not use @lru_cache — caches async connections bound to wrong loop"


def test_lru_cache_not_on_retriever():
    """get_retriever must NOT use @lru_cache."""
    import soulra.dependencies as deps
    assert not hasattr(deps.get_retriever, "cache_info"), \
        "get_retriever must not use @lru_cache"


def test_get_cohere_client_raises_when_not_initialised():
    import soulra.dependencies as deps
    deps._cohere_client = None
    with pytest.raises(RuntimeError, match="Cohere client not initialised"):
        deps.get_cohere_client()


def test_get_cohere_client_returns_value_after_set():
    import soulra.dependencies as deps
    sentinel = object()
    deps.set_cohere_client(sentinel)
    assert deps.get_cohere_client() is sentinel
    deps._cohere_client = None


def test_lru_cache_not_on_cohere_client():
    import soulra.dependencies as deps
    assert not hasattr(deps.get_cohere_client, "cache_info")
