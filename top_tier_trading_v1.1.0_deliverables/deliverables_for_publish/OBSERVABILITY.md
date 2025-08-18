# Observability and Hardening Guide

This document describes the improvements made in **Phase 3** (Hardening & Observability) for the `Top_Tier_Trading` platform.  The goal of these changes is to make failures diagnosable, provide meaningful telemetry, and harden the runtime environment to minimise the blast radius of incidents.

## 1. Structured Logging

* **Node/TypeScript (API and Ops UI)** – Use [pino](https://getpino.io/) or [winston](https://github.com/winstonjs/winston) for JSON‑formatted logs.  Initialise a single logger per service and include request IDs, user IDs and other contextual metadata.  Example:

  ```ts
  import pino from 'pino';
  const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
  export default logger;

  // within Express handler
  logger.info({ reqId: req.id, route: req.path }, 'received request');
  ```

* **Python Workers/Backtester** – Use [structlog](https://www.structlog.org/en/stable/) or [loguru](https://github.com/Delgan/loguru) to emit JSON logs.  Configure the default logger to include timestamps, log level and contextual keys (e.g. trade ID, user ID).  Example:

  ```py
  import structlog, logging, sys
  logging.basicConfig(stream=sys.stdout, level=logging.INFO)
  logger = structlog.get_logger()
  logger.info('order_executed', order_id=order_id, size=size, price=price)
  ```

* **Log Shipping** – Forward container logs to a central aggregator (e.g. Loki, Elasticsearch) via a sidecar or Fluent Bit.  The logs are JSON, making them easy to search and filter.

## 2. Distributed Tracing (OpenTelemetry)

* **Instrumentation** – Integrate [OpenTelemetry](https://opentelemetry.io/) SDKs in each service.
  * Node: install `@opentelemetry/sdk-node`, `@opentelemetry/auto-instrumentations-node` and configure an exporter (e.g. OTLP over HTTP).  Wrap HTTP clients (Axios, node‑fetch) and Express servers to create spans automatically.
  * Python: install `opentelemetry-sdk`, `opentelemetry-instrumentation-aiohttp`, `opentelemetry-instrumentation-redis`, etc.  Use an OTLP or Jaeger exporter.
  * Next.js: instrumentation is similar to Node.  For API routes, wrap handlers with `trace.getTracer().startSpan()` to measure latency.
* **Propagation** – Use W3C Trace Context headers to propagate trace and span IDs between services.  Ensure that the event bus (Redis or RabbitMQ) also carries trace context in message metadata.
* **Collector** – Deploy the OpenTelemetry Collector (via Docker Compose or Kubernetes) to receive spans and forward them to a tracing backend (e.g. Jaeger, Zipkin, Tempo).  Configure exporters in each service to send data to `otel-collector:4317`.

## 3. Metrics and Alerts

* **Metrics** – Expose Prometheus metrics in all services:
  * API: `express-prom-bundle` provides request latency histograms and error counters.
  * Workers: existing Prometheus exporter now includes gauges for exposures, open orders, kill switch and PnL.  Add histograms for order processing duration.
  * Backtester: expose gauges for total jobs, running jobs, and counters for completed/failed backtests.
* **Alerting Rules** – Configure Prometheus alert rules (in `prometheus.yml` or a separate `alerts.yml`) such as:

  ```yaml
  groups:
    - name: trading_platform_alerts
      rules:
        - alert: HighErrorRate
          expr: rate(http_requests_total{status!~"2.."}[5m]) / rate(http_requests_total[5m]) > 0.05
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "High error rate (>5%) on API"
            description: "More than 5% of HTTP requests failed in the last 5 minutes."

        - alert: HighLatency
          expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.2
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High API latency (p95 > 200ms)"
            description: "The 95th percentile response time exceeds 200ms."

        - alert: RedisSaturation
          expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Redis memory usage high (>80%)"
            description: "Redis is nearing its memory limit; consider scaling or cleaning up."
  ```

* **Dashboards** – Provision Grafana dashboards showing request rates, error rates, response time distributions, worker throughput, backtest job status, database/Redis metrics and message queue metrics.  Provide separate panels for p50/p95 latencies and event bus lag.

## 4. Security Hardening

* **NextAuth** – Use secure, HTTP‑only cookies with `SameSite=Strict` and `secure: true`.  In production, enforce HTTPS by setting `NEXTAUTH_URL=https://yourdomain.com` and configure CSRF protection.
* **Dockerfiles** – Refactor all Dockerfiles to:
  * Use multi‑stage builds (already present).
  * Drop privileges using non‑root users (`USER node` for Node images, `USER 1000` for Python).  Ensure files and directories under `/app` are readable by this user.
  * Minimise the attack surface by removing build tools from the runtime stage and cleaning package caches (`npm cache clean --force`, `rm -rf /root/.cache/pip`).
  * Use `COPY --chown` to ensure correct file ownership.
* **Secrets Management** – Do not embed secrets in images.  Use environment variables from `conf/secrets.env` during local development and Kubernetes Secrets for production.  The GitHub Actions workflow uses `${{ secrets.GH_TOKEN }}` rather than committing tokens.

Implementing these practices provides deep visibility into the system’s behaviour and ensures secure, resilient operations.