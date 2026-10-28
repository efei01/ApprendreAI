"""Tests for FrenchAnalysisLLM using a fake OpenAI client (no network calls)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest
from pydantic import ValidationError

from app.prompts.french_analysis import SYSTEM_INSTRUCTIONS
from app.schemas.analysis import AnalysisResult
from app.services.llm_service import FrenchAnalysisLLM, LLMOutputValidationError, LLMProviderError
from tests.conftest import VALID_ANALYSIS


def _llm_returning(response=None, error: Exception | None = None) -> FrenchAnalysisLLM:
    client = MagicMock()
    client.responses.parse.return_value = response
    client.responses.parse.side_effect = error
    return FrenchAnalysisLLM(client=client, model_name="test-model")


def test_returns_parsed_result_and_usage() -> None:
    response = SimpleNamespace(
        output_parsed=AnalysisResult.model_validate(VALID_ANALYSIS),
        usage=SimpleNamespace(input_tokens=150, output_tokens=90),
        status="completed",
    )
    llm = _llm_returning(response)

    analysis = llm.analyze("I started learning French last month.")

    assert analysis.result.translation == VALID_ANALYSIS["translation"]
    assert (analysis.input_tokens, analysis.output_tokens) == (150, 90)
    call = llm._client.responses.parse.call_args.kwargs
    assert call["model"] == "test-model"
    assert call["instructions"] == SYSTEM_INSTRUCTIONS
    assert call["text_format"] is AnalysisResult
    assert "I started learning French last month." in call["input"]


def test_missing_usage_is_stored_as_none() -> None:
    response = SimpleNamespace(output_parsed=AnalysisResult.model_validate(VALID_ANALYSIS), usage=None, status="completed")
    analysis = _llm_returning(response).analyze("Hello.")
    assert analysis.input_tokens is None and analysis.output_tokens is None


def test_no_parsed_output_raises_validation_error() -> None:
    # e.g. the model refused, so there is no parsed content
    response = SimpleNamespace(output_parsed=None, usage=None, status="completed")
    with pytest.raises(LLMOutputValidationError):
        _llm_returning(response).analyze("Hello.")


def test_schema_mismatch_raises_validation_error() -> None:
    # Build the same kind of error the SDK raises when the JSON doesn't fit the schema.
    with pytest.raises(ValidationError) as schema_error:
        AnalysisResult.model_validate_json('{"translation": "Bonjour"}')
    with pytest.raises(LLMOutputValidationError):
        _llm_returning(error=schema_error.value).analyze("Hello.")


def test_api_failure_raises_provider_error() -> None:
    connection_error = openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    with pytest.raises(LLMProviderError):
        _llm_returning(error=connection_error).analyze("Hello.")
