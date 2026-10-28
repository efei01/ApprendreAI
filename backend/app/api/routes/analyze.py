from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_llm_service
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.analysis import AnalysisResult, AnalyzeRequest
from app.services.analysis_service import DatabaseWriteError, analyze_passage
from app.services.llm_service import FrenchAnalysisLLM, LLMOutputValidationError, LLMProviderError

router = APIRouter(prefix="/api/v1", tags=["analysis"])


# A plain `def` (not `async def`): FastAPI runs it in a worker thread, so the
# blocking OpenAI and database calls don't freeze other requests.
@router.post("/analyze", response_model=AnalysisResult)
def analyze(
    request: AnalyzeRequest,
    llm: Annotated[FrenchAnalysisLLM, Depends(get_llm_service)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnalysisResult:
    # Translate internal errors into HTTP errors with safe, user-readable messages.
    # Details (stack traces, provider messages) stay in the server logs.
    try:
        return analyze_passage(request.text, llm=llm, db=db, settings=settings)
    except LLMProviderError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="The translation service is unavailable right now. Please try again in a moment.",
        )
    except LLMOutputValidationError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="The translation service returned an invalid response. Please try again.",
        )
    except DatabaseWriteError:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The analysis could not be saved. Please try again.",
        )
