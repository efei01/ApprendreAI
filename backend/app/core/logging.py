import logging


def configure_logging(level: str) -> None:
    """Plain stdout logging; Docker collects stdout, so `docker compose logs backend` shows it."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    # The OpenAI SDK's HTTP library (httpx2) logs every request at INFO. Keep it quieter.
    logging.getLogger("httpx2").setLevel(logging.WARNING)
