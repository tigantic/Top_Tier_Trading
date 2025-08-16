# Risk Management Policy

Effective risk management is paramount when designing an automated trading platform.  The following policies and limits should be enforced at all times.  These values are configurable via environment variables or configuration files.

## Pre‑Trade Checks

1. **Order Notional Cap** – Each individual order must not exceed the configured `MAX_ORDER_NOTIONAL`.  Orders with a notional value greater than this cap are rejected.
2. **Allowed Markets** – Only products listed in `ALLOWED_MARKETS` may be traded.  Attempts to trade other instruments are blocked.
3. **Slippage Tolerance** – The expected slippage between the requested price and the last traded price must remain within a configured percentage band.
4. **Max Open Orders** – The total number of open orders across all markets must not exceed `MAX_ORDERS_PER_MINUTE` per minute (or another specified time window).

## Post‑Trade Checks

1. **Daily Max Loss** – The platform tracks realized and unrealized PnL throughout the day.  If the cumulative loss exceeds a predefined threshold, all open positions are closed and no new orders are accepted until the next trading day.
2. **Kill Switch** – Under certain conditions (e.g., extreme market volatility, unexpected exchange errors), a kill switch is triggered to halt trading immediately.  Manual intervention is required to resume operations.
3. **Drawdown Monitoring** – Monitor maximum drawdown and issue alerts when it exceeds predefined thresholds.  Drawdowns beyond critical levels may automatically disable the strategy.

## Governance

* All changes to risk limits require approval by the designated risk officer.
* Live trading cannot be enabled without explicit human confirmation (see `enable-live` script).
* All risk checks must log their decisions for auditability, without exposing sensitive information.
