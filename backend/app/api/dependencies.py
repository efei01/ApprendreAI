"""FastAPI dependencies: objects that routes receive via `Depends(...)`.

Tests replace these with fakes using `app.dependency_overrides`, which is how
we test the endpoint without calling the paid OpenAI API.
"""

from functools import lru_cache

import openai

from app.core.config import get_settings
from app.services.llm_service import FrenchAnalysisLLM


@lru_cache
def get_llm_service() -> FrenchAnalysisLLM:
    """One shared client for the whole app (it holds a reusable HTTP connection pool)."""
    settings = get_settings()
    client = openai.OpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_seconds,
    )
    return FrenchAnalysisLLM(client=client, model_name=settings.openai_model)
