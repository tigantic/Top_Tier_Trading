# API Service

The `api` directory contains the TypeScript/Node.js service that exposes REST and GraphQL endpoints for external clients.  The service also provides a streaming SSE endpoint for real‑time risk metrics.

## Running Offline

In offline development environments you can start the API service using the provided Docker Compose configuration, which builds the Node image using the locally vendored `package-lock.json` and `package.json` files.  No internet access is required during the build.

```bash
# Build and run only the API container
docker compose -f docker/docker-compose.yml build api
docker compose -f docker/docker-compose.yml up api

# The API will start on port 8000 by default.  You can verify it is running:
curl -s http://localhost:8000/healthz
```

Alternatively, if Node.js is installed locally and dependencies have already been installed (via `npm ci` or `npm install` before going offline), you can start the development server:

```bash
cd api
npm run dev  # or npm run build && npm start
```

The API exposes routes under `/api/*`.  See `api/src/routes` for individual route definitions.  Server‑Sent Events (SSE) are served at `/api/streams/sse` and provide live updates when connected to Redis.

## Linking to Other Components

The API service depends on the worker services for market data, risk management and execution.  For the full system to operate, start the entire stack via Docker Compose (`docker/docker-compose.yml`).  In offline mode, the service will still expose its routes but will return empty responses for data queries.

For architectural details, refer to [01_architecture.md](../docs/01_architecture.md).  For SSE and SDK toggling behaviour, see [COINBASE_INTEGRATION.md](../docs/COINBASE_INTEGRATION.md).