# syntax=docker/dockerfile:1.4

# Stage 1: Build stage with Poetry
FROM python:3.11-slim AS builder

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry

# Copy the root pyproject.toml to install dependencies
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
COPY ./backtester/src ./backtester/src

WORKDIR /

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python /app/backtester/src/backtester/healthcheck.py

CMD ["python", "-m", "backtester.backtester_main"]