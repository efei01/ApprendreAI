"""The only module that talks to OpenAI.

Everything OpenAI-specific (client, request format, error classes, usage
fields) stays in this file. The rest of the app depends only on
`FrenchAnalysisLLM.analyze()` and the exceptions defined here, so changing the
model (via OPENAI_MODEL) or swapping providers later only touches this file.
"""

import logging
from dataclasses import dataclass

import openai
from pydantic import ValidationError

from app.prompts.french_analysis import SYSTEM_INSTRUCTIONS, build_user_input
from app.schemas.analysis import AnalysisResult

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base class. `error_type` is the short code stored in model_runs.error_type."""

    error_type = "llm_error"


class LLMProviderError(LLMServiceError):
    """The API call itself failed: network problem, timeout, bad key, rate limit, 5xx..."""

    error_type = "llm_provider_error"


class LLMOutputValidationError(LLMServiceError):
    """The API answered, but not with a valid AnalysisResult (or it refused)."""

    error_type = "llm_invalid_output"


@dataclass(frozen=True)
class LLMAnalysis:
    result: AnalysisResult
    # None if the provider did not report usage. We never invent numbers.
    input_tokens: int | None
    output_tokens: int | None


class FrenchAnalysisLLM:
    def __init__(self, client: openai.OpenAI, model_name: str) -> None:
        self._client = client
        self.model_name = model_name

    def analyze(self, english_text: str) -> LLMAnalysis:
        try:
            # responses.parse() converts AnalysisResult into a strict JSON schema,
            # asks the model to follow it, and validates the reply with Pydantic.
            response = self._client.responses.parse(
                model=self.model_name,
                instructions=SYSTEM_INSTRUCTIONS,
                input=build_user_input(english_text),
                text_format=AnalysisResult,
            )
        except ValidationError as exc:
            # Reply was not valid JSON for our schema (e.g. truncated output).
            logger.warning("LLM output failed schema validation: %d error(s)", exc.error_count())
            raise LLMOutputValidationError("LLM output did not match the schema") from exc
        except openai.APIError as exc:
            # Log the class name and status only: never the request (it carries the API key header).
            logger.error("OpenAI API call failed: %s (status=%s)", type(exc).__name__, getattr(exc, "status_code", None))
            raise LLMProviderError("OpenAI API call failed") from exc

        result = response.output_parsed
        if result is None:
            # No parsed output usually means the model refused or the response was incomplete.
            logger.warning("LLM returned no structured output (status=%s)", response.status)
            raise LLMOutputValidationError("LLM returned no structured output")

        usage = response.usage
        return LLMAnalysis(
            result=result,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
        )
