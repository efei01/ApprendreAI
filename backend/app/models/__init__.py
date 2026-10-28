# Importing models here registers them on Base.metadata (needed by Alembic).
from app.models.model_run import ModelRun

__all__ = ["ModelRun"]
