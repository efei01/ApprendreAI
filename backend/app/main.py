"""Entry point: builds the FastAPI app. Run with `uvicorn app.main:app`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze, health
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="ApprendreAI API", version="0.1.0")

# The browser loads the page from localhost:3000 but calls the API on localhost:8000.
# That is a different "origin", so the browser only allows it if the API says so.
# We list allowed origins explicitly instead of "*" (see docs/architecture.md).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(analyze.router)
