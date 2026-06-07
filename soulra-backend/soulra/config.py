from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str
    openrouter_api_key: str
    redis_url: str = "redis://localhost:6379/0"
    cohere_api_key: str

    smart_model: str = "openai/gpt-4o-mini"
    fast_model: str = "openai/gpt-4o-mini"
    embedding_model: str = "openai/text-embedding-3-small"

    max_upload_mb: int = 50
    allowed_origins: list[str] = ["http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v


def get_settings() -> "Settings":
    """Return a Settings instance. Deferred so imports don't fail in test environments."""
    return Settings()


# Module-level singleton — only materialised outside of test collection.
# Tests that need an unconfigured Settings should call Settings() directly.
try:
    settings = Settings()
except ValidationError:  # pragma: no cover
    settings = None  # type: ignore[assignment]
