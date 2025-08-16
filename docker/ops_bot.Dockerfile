FROM python:3.10-slim

# Install runtime dependencies
RUN pip install --no-cache-dir slack_bolt aiohttp redis

# Copy the async ops bot script and default requirements
WORKDIR /app
COPY scripts/ops_bot_async.py ./
COPY workers/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint
CMD ["python", "ops_bot_async.py"]