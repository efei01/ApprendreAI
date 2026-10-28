"""Shared test fixtures.

Tests never call OpenAI and never need Docker:
- the LLM is replaced by `FakeLLM`, which returns canned results or raises errors;
- the database is an in-memory SQLite database created fresh for each test.
"""

import os

# Settings are read at import time, so set safe dummy values before importing the app.
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("OPENAI_MODEL", "test-model")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.dependencies import get_llm_service  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.analysis import AnalysisResult  # noqa: E402
from app.services.llm_service import LLMAnalysis, LLMServiceError  # noqa: E402

VALID_ANALYSIS = {
    "translation": "J'ai commencé à apprendre le français le mois dernier.",
    "grammar_points": [
        {
            "phrase": "J'ai commencé",
            "concept": "passé composé",
            "explanation": "The passé composé describes a completed action in the past.",
            "level": "A2",
        }
    ],
    "vocabulary": [
        {"french": "le mois dernier", "english": "last month", "level": "A2"},
    ],
}


class FakeLLM:
    """Stands in for FrenchAnalysisLLM. Returns `VALID_ANALYSIS` or raises `error`."""

    model_name = "fake-model"

    def __init__(self, error: LLMServiceError | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    def analyze(self, english_text: str) -> LLMAnalysis:
        self.calls.append(english_text)
        if self.error:
            raise self.error
        return LLMAnalysis(
            result=AnalysisResult.model_validate(VALID_ANALYSIS),
            input_tokens=120,
            output_tokens=80,
        )


@pytest.fixture
def db_session() -> Iterator[Session]:
    # StaticPool keeps a single connection so the in-memory database survives across the test.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(db_session: Session, fake_llm: FakeLLM) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_llm_service] = lambda: fake_llm
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
