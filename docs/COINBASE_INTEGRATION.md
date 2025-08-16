## Coinbase SDK Integration

> 🚦 **Documentation Freeze**
>
> The content of this document is frozen for the 1.0.0 release.  Any
> updates to the SDK integration, event schema, or toggle behaviour will be
> recorded in `CHANGELOG.md`.  Please consult the changelog before making
> modifications.

> **Release Freeze (v1.0.0)**
>
> The API and event schema described in this document are frozen for
> the 1.0.0 release.  Ticker and user update events
> must conform to the canonical definitions in
> `workers/src/workers/models/events.py`.  All publishers — both the raw
> WebSocket clients and the SDK wrappers — **MUST** normalise and
> publish events via `services/publishers.py` to ensure parity.  Any
> changes to the schema or event contract will be considered breaking
> changes and should be proposed in a future minor release.

[← Back to docs index](./_index.md)

This document describes how the trading platform integrates with the Coinbase Advanced Trade SDK and how to toggle between the native WebSocket implementation and the SDK-based clients.  Because this repository is designed to run in offline and CI environments, the default behaviour uses the raw WebSocket clients built into the workers.  When you are ready to adopt the official SDK, follow the guidelines below.

### Toggle Diagram

```
USE_OFFICIAL_SDK=false                USE_OFFICIAL_SDK=true
┌───────────┐                         ┌───────────┐
│ market_data│  ───────────────┐     │ market_data│  ───────────────┐
│  (raw WS) │                  │     │ (SDK stub)│                  │
└───────────┘                  │     └───────────┘                  │
                              v                                    v
                         EventBus                             EventBus
                              │                                    │
┌───────────┐                  │     ┌───────────┐                  │
│ user_chan.│  ───────────────┘     │ user_chan.│  ───────────────┘
│  (raw WS) │                        │ (SDK stub)│
└───────────┘                        └───────────┘
```

When `USE_OFFICIAL_SDK=false` (default), the `market_data` and `user_channel` workers connect directly to the Coinbase WebSocket endpoint and publish events onto the event bus.  When `USE_OFFICIAL_SDK=true`, the workers initialise the SDK wrappers (`sdk_market_data.py`, `sdk_user_channel.py`) instead.  In offline environments the SDK wrappers yield no data but maintain the same interface and publish events to the event bus via the same `publish('ticker', msg)` and `publish('user_update', msg)` methods.

### Event Schema

Regardless of the source (raw WebSocket or SDK wrapper), published events should conform to the following minimal schema so that downstream consumers can process them without caring about the origin:

| Event Type   | Key         | Type   | Description                                        |
|--------------|-------------|--------|----------------------------------------------------|
| `ticker`     | `product_id`| str    | Trading pair identifier (e.g. `BTC-USD`)          |
|              | `price`     | float  | Last traded price                                  |
| `user_update`| `product_id`| str    | Product associated with the fill or account change |
|              | `price`     | float  | Fill price (if applicable)                         |
|              | `size`      | float  | Fill quantity (if applicable)                      |
|              | `side`      | str    | `buy` or `sell`                                    |
|              | `balance`   | float  | Updated account balance (optional)                 |

Every event published by the market data or user channel workers is also sent over the internal event bus via the same API used by the raw WebSocket implementation.  This ensures downstream services (risk engine, execution service, metrics, SSE) receive the same message format regardless of the selected data source.  See the integration tests in ``tests/integration/test_event_schema_parity.py`` for examples of how schema parity is enforced.

Your implementation may add additional keys, but consumers should be prepared to handle at least the fields above.

### Schema contract

The canonical definitions of ticker and user update events live in
``workers/src/workers/models/events.py``.  This module exports
typed dictionaries ``TickerEvent`` and ``UserUpdateEvent`` as well as
normalisation functions ``normalize_ticker_event()`` and
``normalize_user_update_event()``.  These helpers coerce numeric
fields to floats, enforce the presence of required keys and may
raise exceptions on invalid input.  All publishers (raw WebSocket
clients, SDK wrappers and helper functions in
``services/publishers.py``) use these functions to ensure a
consistent payload shape before publishing to the event bus.

Refer to the code in that module for the precise definitions of
allowed keys and their types.

### Local Mock Flow

In offline development and CI, the SDK wrappers are used solely as no‑op stubs.  They implement the same API as the real SDK but yield no data and simply sleep in a loop.  When an `event_bus` is provided to the wrapper constructors, each emitted message (when the real SDK is present) will be published to the bus via `publish('ticker', msg)` or `publish('user_update', msg)`.  In offline mode the wrappers log a warning that no SDK is available.

To exercise the code path locally:

```bash
export USE_OFFICIAL_SDK=true
python scripts/sdk_integration_harness.py
```

This harness initialises both the market data and user channel clients and prints any events.  In offline environments you will only see the log message indicating that no data is being produced.

### Production Flow

In a production environment with network access and the `coinbase-advanced-py` package installed:

1. Set `USE_OFFICIAL_SDK=true` and supply your API credentials via environment variables (`COINBASE_API_KEY`, `COINBASE_API_SECRET`, `COINBASE_PASSPHRASE`) or via the secrets manager.
2. Install the official SDK in the `workers` Python environment.
3. Modify `sdk_market_data.py` and `sdk_user_channel.py` to replace the placeholder code with real SDK calls (e.g. `WebSocketClient(...).subscribe(...)`) and update event field names if necessary to match the schema above.
4. Monitor the logs to ensure that events are being published onto the event bus.  The parity tests in `tests/integration/test_event_schema_parity.py` should pass both offline and online.

### Minimal Production Checklist

1. **Set environment variables**: `USE_OFFICIAL_SDK=true`, provide API credentials, and leave fallback variables intact.
2. **Install SDK**: Run `pip install coinbase-advanced-py` (or the appropriate package) in your worker image.
3. **Update wrappers**: Replace stubbed sections with real SDK logic.
4. **Deploy**: Restart the worker services and verify that they start consuming from the SDK.  Check the logs for any errors.
5. **Validate parity**: Run the integration test suite to ensure that the event schema matches the expectations and that toggling `USE_OFFICIAL_SDK` behaves correctly.

