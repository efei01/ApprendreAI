from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelRun(Base):
    """One row per LLM call (successful or failed).

    This table is the raw material for later milestones: comparing prompt
    versions, models, latency, token usage and failure rates.
    """

    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    input_text: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(50), index=True)

    # Null when the run failed.
    translation: Mapped[str | None] = mapped_column(Text)
    # The full validated AnalysisResult. JSONB in PostgreSQL; plain JSON elsewhere
    # (lets the unit tests use SQLite).
    analysis: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql")
    )

    latency_ms: Mapped[int | None] = mapped_column(Integer)
    # Null when the provider did not report usage (e.g. the request failed).
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    # USD. Numeric (not float) avoids rounding errors with money. Null if prices are not configured.
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))

    success: Mapped[bool]
    error_type: Mapped[str | None] = mapped_column(String(50))
