"""Database engine and session management.

- The *engine* owns a pool of connections to PostgreSQL (one per app process).
- A *session* is a short-lived unit of work: we open one per HTTP request,
  use it to add/query rows, commit, and close it when the request ends.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

# pool_pre_ping checks a pooled connection is still alive before using it,
# which avoids errors after the database restarts.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
