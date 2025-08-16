# syntax=docker/dockerfile:1.4

FROM python:3.11-slim AS base

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/usr/src/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Healthcheck script placeholder
COPY src/healthcheck.py /usr/local/bin/backtester-healthcheck.py
RUN chmod +x /usr/local/bin/backtester-healthcheck.py

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python /usr/local/bin/backtester-healthcheck.py

# Default command runs the backtester CLI
CMD ["python", "-m", "backtester.backtester_main"]
