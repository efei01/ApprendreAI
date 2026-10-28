FROM python:3.13-slim

# Don't write .pyc files; flush logs immediately so `docker compose logs` is live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini start.sh ./
COPY alembic ./alembic
COPY app ./app

# Run as an unprivileged user rather than root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["./start.sh"]
