"""Application settings, read from environment variables.

pydantic-settings maps each field to an env var of the same name
(case-insensitive), e.g. `openai_model` <- OPENAI_MODEL, and validates types.
If a required variable is missing, the app fails at startup with a clear error
instead of failing later in the middle of a request.
"""

from decimal import Decimal
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty: treat `VAR=` (empty) as "not set", so optional fields fall back to defaults.
    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    # SecretStr hides the value in logs/reprs: str(settings.openai_api_key) -> "**********"
    openai_api_key: SecretStr
    openai_model: str
    openai_timeout_seconds: float = 60.0

    # Optional pricing (USD per 1 million tokens). If either is unset,
    # estimated_cost is stored as NULL rather than guessed.
    openai_input_price_per_1m_tokens: Decimal | None = None
    openai_output_price_per_1m_tokens: Decimal | None = None

    database_url: str

    # Comma-separated list, e.g. "http://localhost:3000,http://127.0.0.1:3000"
    backend_cors_origins: str = "http://localhost:3000"

    log_level: str = "INFO"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Build settings once and reuse them (environment does not change at runtime)."""
    return Settings()
