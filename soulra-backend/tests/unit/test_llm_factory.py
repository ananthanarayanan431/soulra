from unittest.mock import patch


def test_make_chat_llm_uses_openrouter_base():
    with patch("soulra.services.llm.factory.settings") as mock_settings:
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.smart_model = "anthropic/claude-opus-4-8"
        from soulra.services.llm.factory import make_chat_llm
        llm = make_chat_llm("anthropic/claude-opus-4-8")
        assert "openrouter" in llm.openai_api_base


def test_make_smart_llm_uses_smart_model():
    with patch("soulra.services.llm.factory.settings") as mock_settings:
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.smart_model = "anthropic/claude-opus-4-8"
        mock_settings.fast_model = "anthropic/claude-sonnet-4-6"
        mock_settings.embedding_model = "openai/text-embedding-3-small"
        from soulra.services.llm.factory import make_smart_llm, make_fast_llm
        smart = make_smart_llm()
        fast = make_fast_llm()
        assert smart.model_name == "anthropic/claude-opus-4-8"
        assert fast.model_name == "anthropic/claude-sonnet-4-6"


def test_make_embeddings_uses_openrouter():
    with patch("soulra.services.llm.factory.settings") as mock_settings:
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.embedding_model = "openai/text-embedding-3-small"
        from soulra.services.llm.factory import make_embeddings
        emb = make_embeddings()
        assert "openrouter" in emb.openai_api_base


def test_make_chat_llm_uses_temperature_zero():
    with patch("soulra.services.llm.factory.settings") as mock_settings:
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.smart_model = "anthropic/claude-opus-4-8"
        from soulra.services.llm.factory import make_chat_llm
        llm = make_chat_llm("anthropic/claude-opus-4-8")
        assert llm.temperature == 0, \
            f"LLM temperature must be 0 for deterministic RAG output, got {llm.temperature}"
