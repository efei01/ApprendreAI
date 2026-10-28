"""Pydantic schemas for the analysis feature.

These classes do double duty:
1. They validate the HTTP request and shape the HTTP response.
2. `AnalysisResult` is also sent to OpenAI as a JSON schema (structured output),
   and the model's reply is validated against it before we trust it.

The `description=` texts are included in that JSON schema, so the LLM sees them.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_INPUT_CHARS = 2000

CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class AnalyzeRequest(BaseModel):
    # strip_whitespace runs before min_length, so "   " is rejected as empty.
    text: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_INPUT_CHARS),
    ]


class GrammarPoint(BaseModel):
    # extra="forbid" -> unexpected fields are an error, not silently dropped.
    model_config = ConfigDict(extra="forbid")

    phrase: str = Field(description="The exact French phrase from the translation that shows this concept.")
    concept: str = Field(description="Short name of the grammar concept, e.g. 'passé composé'.")
    explanation: str = Field(description="Plain-English explanation aimed at an A1-B1 learner.")
    level: CEFRLevel = Field(description="Approximate CEFR level at which this concept is usually learned.")


class VocabularyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    french: str = Field(description="French word or phrase as it appears in the translation (dictionary form if clearer).")
    english: str = Field(description="English meaning in this context.")
    level: CEFRLevel = Field(description="Approximate CEFR level of this vocabulary item.")


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    translation: str = Field(description="Natural French translation of the full English passage.")
    grammar_points: list[GrammarPoint]
    vocabulary: list[VocabularyItem]
