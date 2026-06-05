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
    assert s.smart_model == "anthropic/claude-opus-4-8"
    assert s.fast_model == "anthropic/claude-sonnet-4-6"
    assert s.embedding_model == "openai/text-embedding-3-small"
    assert s.max_upload_mb == 50
    assert s.allowed_origins == ["http://localhost:3000"]
