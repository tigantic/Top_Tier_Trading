# Operations Runbook

This runbook provides guidance for deploying, monitoring, and troubleshooting the crypto trading platform.  It will be expanded with detailed procedures as the platform matures.

## Deployment

1. **Bootstrap:** Create a `.env` file with `make bootstrap` and populate all secret values.
2. **Build Images:** Run `make build` to build Docker images for all services.
3. **Start Services:** Use `make up` to start the stack in detached mode.  Check the container health status with `docker compose ps` or `make logs`.
4. **Database Migrations:** Run `make migrate` to apply database schema migrations.

## Monitoring

* **Logs:** Tail logs from all services with `make logs`.  The logs should indicate successful health checks for each service.
* **Metrics:** Prometheus and Grafana integration will be added in a later phase.  Telemetry data will be exposed on a dedicated port.
* **Alerts:** Future versions will integrate with Slack or email for alerting.  Critical events such as exchange disconnections, failed orders, or kill switch activations will trigger alerts.

## Troubleshooting

* **Service Unhealthy:** Check the container logs for stack traces or connection errors.  Restart the service with `docker compose restart <service>`.
* **Database Connection Issues:** Verify that Postgres is running and accepting connections on the expected port.  Review the `.env` configuration for correct credentials.
* **WebSocket Disconnects:** The market data worker includes automatic reconnection logic with backoff.  Persistent failures may indicate network issues or API outages.
* **Rate Limit Errors:** The REST client will be enhanced to respect Coinbase rate limits.  If you encounter HTTP 429 responses, consider reducing request frequency.

## Enabling Live Trading

Live trading is disabled by default.  To enable it, run `make enable-live` and follow the interactive prompt.  Ensure that your API keys have appropriate permissions and that you understand the associated risks.
