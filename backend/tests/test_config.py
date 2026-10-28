from decimal import Decimal

import pytest

from app.core.config import Settings


def test_empty_optional_prices_are_treated_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    # docker compose passes blank .env values through as empty strings
    monkeypatch.setenv("OPENAI_INPUT_PRICE_PER_1M_TOKENS", "")
    monkeypatch.setenv("OPENAI_OUTPUT_PRICE_PER_1M_TOKENS", "")
    settings = Settings()
    assert settings.openai_input_price_per_1m_tokens is None
    assert settings.openai_output_price_per_1m_tokens is None


def test_prices_are_parsed_as_decimals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_INPUT_PRICE_PER_1M_TOKENS", "0.25")
    assert Settings().openai_input_price_per_1m_tokens == Decimal("0.25")


def test_cors_origins_are_split_and_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:3000, http://127.0.0.1:3000 ,")
    assert Settings().cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_api_key_is_hidden_in_repr() -> None:
    assert "test-key-not-real" not in repr(Settings())
