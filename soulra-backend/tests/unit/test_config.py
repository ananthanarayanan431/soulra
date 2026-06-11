import pytest
from pydantic import ValidationError


def test_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from soulra.config import Settings
    from pydantic_settings import SettingsConfigDict

    # Override env_file to None so a local .env doesn't satisfy required fields
    class SettingsNoFile(Settings):
        model_config = SettingsConfigDict(env_file=None)

    with pytest.raises(ValidationError):
        SettingsNoFile()


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    from soulra.config import Settings

    s = Settings()
    assert s.smart_model == "openai/gpt-4o-mini"
    assert s.fast_model == "openai/gpt-4o-mini"
    assert s.embedding_model == "openai/text-embedding-3-small"
    assert s.max_upload_mb == 50
    assert s.allowed_origins == ["http://localhost:3000"]


def test_clerk_and_token_limit_defaults(monkeypatch):
    from soulra.config import Settings

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://soulra:soulra@localhost:5432/soulra")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("COHERE_API_KEY", "test")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    monkeypatch.delenv("CLERK_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("DEFAULT_TOKEN_LIMIT", raising=False)

    settings = Settings()

    assert settings.clerk_publishable_key == "pk_test_placeholder"
    assert settings.clerk_secret_key == "sk_test_placeholder"
    assert settings.clerk_jwks_url.endswith("/.well-known/jwks.json")
    assert settings.clerk_webhook_secret == "whsec_placeholder"
    assert settings.default_token_limit == 1_000_000
