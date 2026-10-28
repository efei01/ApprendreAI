"""Business logic for one "Analyze" request: call the LLM, record the run, return the result.

This module knows nothing about HTTP (no status codes, no FastAPI imports).
That keeps it easy to test and reusable later, e.g. from a batch evaluation script.
"""

import logging
import time

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.model_run import ModelRun
from app.prompts.french_analysis import PROMPT_VERSION
from app.schemas.analysis import AnalysisResult
from app.services.llm_service import FrenchAnalysisLLM, LLMServiceError
from app.services.pricing import estimate_cost_usd

logger = logging.getLogger(__name__)


class DatabaseWriteError(Exception):
    """The analysis succeeded but the model run could not be saved."""


def analyze_passage(
    english_text: str,
    llm: FrenchAnalysisLLM,
    db: Session,
    settings: Settings,
) -> AnalysisResult:
    logger.info("Analysis started (chars=%d, model=%s, prompt=%s)", len(english_text), llm.model_name, PROMPT_VERSION)
    started = time.perf_counter()

    try:
        llm_output = llm.analyze(english_text)
    except LLMServiceError as exc:
        _record_failed_run(db, english_text, llm.model_name, _elapsed_ms(started), exc.error_type)
        raise

    latency_ms = _elapsed_ms(started)
    run = ModelRun(
        input_text=english_text,
        model_name=llm.model_name,
        prompt_version=PROMPT_VERSION,
        translation=llm_output.result.translation,
        analysis=llm_output.result.model_dump(),
        latency_ms=latency_ms,
        input_tokens=llm_output.input_tokens,
        output_tokens=llm_output.output_tokens,
        estimated_cost=estimate_cost_usd(
            llm_output.input_tokens,
            llm_output.output_tokens,
            settings.openai_input_price_per_1m_tokens,
            settings.openai_output_price_per_1m_tokens,
        ),
        success=True,
    )
    try:
        db.add(run)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to save model run: %s", type(exc).__name__)
        raise DatabaseWriteError("Could not save model run") from exc

    logger.info(
        "Analysis finished (run_id=%s, latency_ms=%d, input_tokens=%s, output_tokens=%s)",
        run.id, latency_ms, llm_output.input_tokens, llm_output.output_tokens,
    )
    return llm_output.result


def _record_failed_run(db: Session, english_text: str, model_name: str, latency_ms: int, error_type: str) -> None:
    """Best effort: a failure to record a failure must not hide the original error."""
    try:
        db.add(
            ModelRun(
                input_text=english_text,
                model_name=model_name,
                prompt_version=PROMPT_VERSION,
                latency_ms=latency_ms,
                success=False,
                error_type=error_type,
            )
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to save failed model run: %s", type(exc).__name__)


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
