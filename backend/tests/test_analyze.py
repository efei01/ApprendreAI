from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_llm_service
from app.db.session import get_db
from app.main import app
from app.models.model_run import ModelRun
from app.prompts.french_analysis import PROMPT_VERSION
from app.schemas.analysis import MAX_INPUT_CHARS
from app.services.llm_service import LLMOutputValidationError, LLMProviderError
from tests.conftest import VALID_ANALYSIS, FakeLLM

ENDPOINT = "/api/v1/analyze"


def _runs(db: Session) -> list[ModelRun]:
    return list(db.scalars(select(ModelRun)))


def test_analyze_returns_structured_result(client: TestClient, fake_llm: FakeLLM) -> None:
    response = client.post(ENDPOINT, json={"text": "I started learning French last month."})

    assert response.status_code == 200
    assert response.json() == VALID_ANALYSIS
    assert fake_llm.calls == ["I started learning French last month."]


def test_analyze_saves_successful_run(client: TestClient, db_session: Session) -> None:
    client.post(ENDPOINT, json={"text": "I started learning French last month."})

    [run] = _runs(db_session)
    assert run.success is True
    assert run.error_type is None
    assert run.input_text == "I started learning French last month."
    assert run.model_name == "fake-model"
    assert run.prompt_version == PROMPT_VERSION
    assert run.translation == VALID_ANALYSIS["translation"]
    assert run.analysis == VALID_ANALYSIS
    assert run.input_tokens == 120
    assert run.output_tokens == 80
    assert run.latency_ms is not None and run.latency_ms >= 0
    assert run.estimated_cost is None  # no prices configured in tests


def test_analyze_rejects_empty_text(client: TestClient, fake_llm: FakeLLM) -> None:
    response = client.post(ENDPOINT, json={"text": "   "})
    assert response.status_code == 422
    assert fake_llm.calls == []  # the LLM is never called for invalid input


def test_analyze_rejects_missing_text_field(client: TestClient) -> None:
    assert client.post(ENDPOINT, json={}).status_code == 422


def test_analyze_rejects_text_over_limit(client: TestClient, fake_llm: FakeLLM) -> None:
    response = client.post(ENDPOINT, json={"text": "a" * (MAX_INPUT_CHARS + 1)})
    assert response.status_code == 422
    assert fake_llm.calls == []


def test_analyze_llm_provider_failure(client: TestClient, db_session: Session) -> None:
    app.dependency_overrides[get_llm_service] = lambda: FakeLLM(error=LLMProviderError("boom"))

    response = client.post(ENDPOINT, json={"text": "Hello."})

    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"]
    assert "boom" not in response.text  # internal details are not leaked
    [run] = _runs(db_session)
    assert run.success is False
    assert run.error_type == "llm_provider_error"
    assert run.translation is None


def test_analyze_invalid_llm_output(client: TestClient, db_session: Session) -> None:
    app.dependency_overrides[get_llm_service] = lambda: FakeLLM(error=LLMOutputValidationError("bad"))

    response = client.post(ENDPOINT, json={"text": "Hello."})

    assert response.status_code == 502
    assert "invalid response" in response.json()["detail"]
    [run] = _runs(db_session)
    assert run.success is False
    assert run.error_type == "llm_invalid_output"


def test_analyze_database_write_failure(client: TestClient) -> None:
    broken_session = MagicMock()
    broken_session.commit.side_effect = OperationalError("INSERT", {}, Exception("disk full"))
    app.dependency_overrides[get_db] = lambda: broken_session

    response = client.post(ENDPOINT, json={"text": "Hello."})

    assert response.status_code == 500
    assert response.json() == {"detail": "The analysis could not be saved. Please try again."}
    broken_session.rollback.assert_called_once()
