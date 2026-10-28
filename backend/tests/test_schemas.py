import copy

import pytest
from pydantic import ValidationError

from app.schemas.analysis import MAX_INPUT_CHARS, AnalysisResult, AnalyzeRequest
from tests.conftest import VALID_ANALYSIS


def test_valid_analysis_passes_validation() -> None:
    result = AnalysisResult.model_validate(VALID_ANALYSIS)
    assert result.translation.startswith("J'ai commencé")
    assert result.grammar_points[0].level == "A2"
    assert result.vocabulary[0].english == "last month"


def test_analysis_from_json_string_passes_validation() -> None:
    # This is the path the OpenAI SDK uses: raw JSON text -> model.
    result = AnalysisResult.model_validate_json(AnalysisResult.model_validate(VALID_ANALYSIS).model_dump_json())
    assert result.model_dump() == VALID_ANALYSIS


def _broken(mutate) -> dict:
    data = copy.deepcopy(VALID_ANALYSIS)
    mutate(data)
    return data


@pytest.mark.parametrize(
    "malformed",
    [
        pytest.param(_broken(lambda d: d.pop("translation")), id="missing-translation"),
        pytest.param(_broken(lambda d: d["grammar_points"][0].update(level="Z9")), id="invalid-cefr-level"),
        pytest.param(_broken(lambda d: d["vocabulary"][0].pop("english")), id="vocab-missing-english"),
        pytest.param(_broken(lambda d: d.update(grammar_points="passé composé")), id="grammar-not-a-list"),
        pytest.param(_broken(lambda d: d.update(notes="extra field")), id="unexpected-field"),
    ],
)
def test_malformed_analysis_fails_validation(malformed: dict) -> None:
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(malformed)


def test_truncated_json_fails_validation() -> None:
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate_json('{"translation": "Bonjour", "grammar_poi')


def test_request_strips_surrounding_whitespace() -> None:
    assert AnalyzeRequest(text="  Hello.  ").text == "Hello."


@pytest.mark.parametrize("text", ["", "   \n\t "], ids=["empty", "whitespace-only"])
def test_request_rejects_empty_text(text: str) -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(text=text)


def test_request_rejects_text_over_limit() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="a" * (MAX_INPUT_CHARS + 1))
