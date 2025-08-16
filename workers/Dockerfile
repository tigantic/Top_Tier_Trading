# syntax=docker/dockerfile:1.4

FROM python:3.11-slim AS base

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/usr/src/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Expose no ports; this service runs workers in the background

# Healthcheck script
COPY src/healthcheck.py /usr/local/bin/worker-healthcheck.py
RUN chmod +x /usr/local/bin/worker-healthcheck.py

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python /usr/local/bin/worker-healthcheck.py

# Start the default worker manager
CMD ["python", "-m", "workers.worker_main"]
