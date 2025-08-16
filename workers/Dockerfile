# syntax=docker/dockerfile:1.4

# Stage 1: Build stage with Poetry
FROM python:3.11-slim AS builder

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev

# Stage 2: Final runtime stage
FROM python:3.11-slim AS final

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY ./workers/src ./workers/src
COPY ./scripts ./scripts

# Set the working directory to the project root for consistent pathing
WORKDIR /

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python /app/workers/src/workers/healthcheck.py

CMD ["python", "-m", "workers.worker_main_refactored"]