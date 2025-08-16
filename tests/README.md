# Test Suite

This directory contains unit and integration tests for the trading platform.  The tests are designed to run **offline** using only the code in this repository and its optional stubs.  No external APIs or SDKs are required.

## Running Tests

To execute the full test suite, install the worker dependencies and run `pytest` on the `trading_platform/tests` directory:

```bash
# Install dependencies for the workers
pip install -r trading_platform/workers/requirements.txt
# Run pytest in quiet mode
pytest -q trading_platform/tests
```

CI pipelines run this command by default.  If you have additional tests in the project root (`tests/`), they will be discovered automatically.  Tests that rely on optional packages (e.g. ML libraries) will skip gracefully when those packages are not installed.

## Test Categories

* **Unit tests** – Validate isolated components such as the replay buffer (`tests/unit/test_replay_buffer.py`), alert deduplication (`test_bot_idempotency.py`) and configuration loading.
* **Integration tests** – Exercise multiple components together.  For example, `tests/integration/test_event_schema_parity.py` ensures that the event schema emitted by the SDK stubs matches that of the raw WebSocket client, and `test_bot_health.py` checks that the ops bot’s health endpoint can parse metrics without error.
* **Secrets & Backends** – Tests under `tests/test_alert_service_secrets.py` and `test_vault_secrets_manager.py` verify that secrets are loaded correctly from environment variables, AWS Secrets Manager and Vault (when configured).

To focus on a single test module or function, use Pytest’s `-k` and `-m` options.  For example:

```bash
pytest -q trading_platform/tests -k test_replay_buffer
```

For more information about the architecture and how these tests fit into the system, see [01_architecture.md](../docs/01_architecture.md) and the individual guides in the `docs/` directory.