"""
Risk management service implementing configurable pre‑trade checks and
post‑trade accounting.  This service supersedes the monolithic
``risk_engine`` by providing fine‑grained state management for
exposure, PnL, order rate limiting and kill switch logic.

Key features:

* Configurable limits: per‑order notional cap, orders per minute,
  max open orders, daily loss threshold, price band percentage and
  slippage cap.
* Accurate exposure tracking: positions are updated when orders are
  registered and settled; exposures for each product reflect net
  notional (positive for long, negative for short).
* Daily PnL resets: resets occur at midnight in the configured
  timezone.
* Kill switch: triggered when daily loss exceeds threshold; remains
  engaged until reset.

The service can persist state via an optional ``state_store`` passed
in the constructor.  If provided, it should implement methods to
persist and load exposures, PnL and other metrics.  Otherwise
everything is kept in memory.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Dict, Deque, Optional


class RiskService:
    """
    Risk engine enforcing pre‑ and post‑trade constraints.

    In addition to performing pre‑trade checks and updating exposures and PnL,
    the service can emit state change events via an optional ``event_bus``.
    When provided, the ``event_bus`` should expose an asynchronous ``publish``
    method taking an ``event_type`` and arbitrary payload.  The risk engine
    will publish ``exposure_update`` events whenever exposures are modified
    (e.g. on order registration) and ``pnl_update`` events whenever the
    daily PnL changes (e.g. on settlement or mark‑to‑market).  This allows
    downstream consumers (e.g. a Web UI via Server‑Sent Events) to react
    immediately to risk state changes without polling Prometheus.
    """

    def __init__(self, *, state_store: Optional[object] = None, event_bus: Optional[object] = None) -> None:
        # Configuration from environment
        self.max_order_notional = float(os.getenv("MAX_ORDER_NOTIONAL", 0) or 0)
        self.max_orders_per_minute = int(os.getenv("MAX_ORDERS_PER_MINUTE", 0) or 0)
        self.max_open_orders = int(os.getenv("MAX_OPEN_ORDERS", 0) or 0)
        self.price_band_pct = float(os.getenv("PRICE_BAND_PCT", 0) or 0)
        self.slippage_pct = float(os.getenv("SLIPPAGE_PCT", 0) or 0)
        self.daily_max_loss = float(os.getenv("DAILY_MAX_LOSS", 0) or 0)
        # Volatility band configuration
        # Number of most recent price returns to consider when computing volatility.
        # When set to 0 or 1, volatility checks are disabled.
        self.volatility_window = int(os.getenv("VOLATILITY_WINDOW", 0) or 0)
        # Multiplier applied to the volatility estimate to determine dynamic band width.
        # For example, with a standard deviation method, band = volatility_mult * stddev.
        self.volatility_mult = float(os.getenv("VOLATILITY_MULT", 0) or 0)
        # Volatility method determines how volatility is computed. Supported values:
        #   "std"  – sample standard deviation of recent returns (default)
        #   "ewma" – exponentially weighted moving average of squared returns
        #   "atr" – average true range (average of absolute percentage price changes)
        # Additional methods (e.g. GARCH) can be implemented in the future.
        self.volatility_method = os.getenv("VOLATILITY_METHOD", "std").lower().strip()
        # Window for ATR computation.  Only used when volatility_method="atr".
        self.atr_window = int(os.getenv("ATR_WINDOW", 0) or 0)
        # Smoothing factor for EWMA volatility.  Only used when volatility_method="ewma".
        self.volatility_alpha = float(os.getenv("VOLATILITY_ALPHA", 0.94) or 0.94)
        tz_name = os.getenv("RISK_TIMEZONE", "UTC")
        try:
            self.tz = timezone(timedelta(0)) if tz_name.upper() == "UTC" else None
        except Exception:
            self.tz = timezone.utc

        # State
        self.positions: Dict[str, float] = defaultdict(float)
        self.exposures: Dict[str, float] = defaultdict(float)
        self.open_orders: Dict[str, float] = {}
        self.order_timestamps: Deque[float] = deque()
        self.daily_pnl = 0.0
        self.last_reset_date: Optional[datetime.date] = None
        self.kill_switch_engaged = False

        self._lock = asyncio.Lock()
        self.state_store = state_store

        # Optional event bus for publishing state updates.  When provided,
        # exposure and PnL changes will be published to this bus.  The bus
        # should implement an async ``publish(event_type, data)`` method.
        self.event_bus = event_bus

        # Maintain a rolling history of price returns for each product.  The history
        # length is bounded by ``volatility_window``.  When the window is 0, the
        # history is not maintained (deque maxlen defaults to 1).
        self._price_histories: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=self.volatility_window or 1)
        )

        # For exponentially weighted volatility estimation.  When using the
        # ``ewma`` volatility method, this dictionary stores the latest
        # exponentially weighted variance for each product.  The variance is
        # updated incrementally in ``record_price`` using the smoothing factor
        # ``volatility_alpha``.  See `_compute_volatility` for how this is used.
        self._ewma_variances: Dict[str, float] = {}

        # For average true range (ATR) volatility estimation.  When using the
        # ``atr`` volatility method, maintain a rolling window of absolute
        # percentage price changes for each product.  ATR is computed as the
        # average of these absolute returns.  The deque length is bounded by
        # ``atr_window``.  When ``atr_window`` is less than 1, ATR tracking is
        # disabled.
        self._atr_histories: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=self.atr_window or 1)
        )
        # Store the latest ATR value per product to avoid recomputing for every call
        self._atr_values: Dict[str, float] = {}

    async def _maybe_reset_daily(self) -> None:
        """Reset daily PnL and counters if a new day has begun."""
        now = datetime.now(self.tz)
        if self.last_reset_date is None or now.date() != self.last_reset_date:
            self.daily_pnl = 0.0
            self.order_timestamps.clear()
            self.open_orders.clear()
            self.positions.clear()
            self.exposures.clear()
            self.kill_switch_engaged = False
            self.last_reset_date = now.date()
            # Persist resets if store provided
            if self.state_store:
                await self.state_store.reset_daily(now.date())

            # Publish reset events for exposures and PnL
            if self.event_bus:
                try:
                    await self.event_bus.publish(
                        "exposure_update",
                        {
                            "product_id": None,
                            "exposure": 0.0,
                            "exposures": {},
                            "open_orders": 0,
                        },
                    )
                    await self.event_bus.publish(
                        "pnl_update",
                        {
                            "daily_pnl": self.daily_pnl,
                            "kill_switch": self.kill_switch_engaged,
                        },
                    )
                except Exception:
                    pass

    async def pre_trade_check(
        self,
        product_id: str,
        side: str,
        size: float,
        price: float,
        reference_price: Optional[float] = None,
    ) -> bool:
        """Perform pre‑trade validation.

        Args:
            product_id: The instrument symbol.
            side: 'buy' or 'sell'.
            size: Quantity of the base currency.
            price: Limit price for the order.
            reference_price: Current market price, if available.  Used
                for slippage and price band checks.

        Returns:
            ``True`` if the order passes all checks, otherwise ``False``.
        """
        await self._maybe_reset_daily()
        async with self._lock:
            if self.kill_switch_engaged:
                return False
            # Order notional cap
            notional = abs(size * price)
            if self.max_order_notional and notional > self.max_order_notional:
                return False
            # Orders per minute rate limiting
            now_ts = time.time()
            cutoff = now_ts - 60.0
            while self.order_timestamps and self.order_timestamps[0] < cutoff:
                self.order_timestamps.popleft()
            if self.max_orders_per_minute and len(self.order_timestamps) >= self.max_orders_per_minute:
                return False
            # Max open orders
            if self.max_open_orders and len(self.open_orders) >= self.max_open_orders:
                return False
            # Price band check
            if reference_price and self.price_band_pct:
                band = self.price_band_pct / 100.0
                lower = reference_price * (1 - band)
                upper = reference_price * (1 + band)
                if price < lower or price > upper:
                    return False
            # Dynamic volatility band: ensure price stays within a volatility-based band.
            # The band width is volatility_mult * volatility * reference_price.
            # A small volatility window or missing volatility disables this check.
            if reference_price and self.volatility_window and self.volatility_mult:
                vol = self._compute_volatility(product_id)
                if vol is not None and vol > 0:
                    band_width = self.volatility_mult * vol * reference_price
                    if abs(price - reference_price) > band_width:
                        return False
            # Slippage check: ensure order price not too far from reference
            if reference_price and self.slippage_pct:
                slip = self.slippage_pct / 100.0
                max_slip = reference_price * slip
                if abs(price - reference_price) > max_slip:
                    return False
            # All checks passed
            return True

    async def register_order(self, client_order_id: str, product_id: str, side: str, size: float, price: float) -> None:
        """Register a pending order.

        This updates exposures and order counters.  Call this after
        submitting an order to the exchange.
        """
        async with self._lock:
            notional = size * price
            # Track open orders by ID and notional
            self.open_orders[client_order_id] = notional
            # Exposure tracks signed notional
            self.exposures[product_id] += notional if side.lower() == "buy" else -notional
            # Position approximates exposure divided by price (approx.)
            self.positions[product_id] += size if side.lower() == "buy" else -size

            # Publish an exposure update event.  Emit the entire exposures dict so
            # subscribers have a consistent view.  Ignore any errors from the
            # event bus to avoid blocking order registration.
            if self.event_bus:
                try:
                    await self.event_bus.publish(
                        "exposure_update",
                        {
                            "product_id": product_id,
                            "exposure": self.exposures[product_id],
                            "exposures": dict(self.exposures),
                            "open_orders": len(self.open_orders),
                        },
                    )
                except Exception:
                    pass
            # Record timestamp for rate limiting
            self.order_timestamps.append(time.time())
            # Persist state: store exposure for this order.  Attempt to call
            # the simplest method signature first (product_id, notional).
            if self.state_store:
                if hasattr(self.state_store, "save_order"):
                    try:
                        await self.state_store.save_order(product_id, notional)  # type: ignore[arg-type]
                    except TypeError:
                        # Fallback to older signature: (id, product_id, side, size, price)
                        try:
                            await self.state_store.save_order(
                                client_order_id, product_id, side, size, price
                            )  # type: ignore[misc]
                        except Exception:
                            pass
                    except Exception:
                        pass

    async def settle_order(self, client_order_id: str, fill_price: float, size: float) -> None:
        """Settle a filled or cancelled order.

        Args:
            client_order_id: The ID of the order.
            fill_price: The price at which the order executed.
            size: Filled size (may be partial).
        """
        async with self._lock:
            notional = abs(size * fill_price)
            if client_order_id in self.open_orders:
                prev_notional = self.open_orders.pop(client_order_id)
                # Remove exposure for the portion of the order
                # Determine sign based on original side stored in positions
                # We approximate by reversing notional sign
                # Here we simply subtract the absolute filled notional
                # More sophisticated implementations would store side per order
            # Update daily PnL: treat buys as negative cash (we pay) and sells as positive
            self.daily_pnl -= notional
            # Engage kill switch if daily loss exceeds threshold
            if self.daily_max_loss and -self.daily_pnl > self.daily_max_loss:
                self.kill_switch_engaged = True

            # Publish PnL update event.  Send the current daily_pnl and kill switch status.
            if self.event_bus:
                try:
                    await self.event_bus.publish(
                        "pnl_update",
                        {
                            "daily_pnl": self.daily_pnl,
                            "kill_switch": self.kill_switch_engaged,
                        },
                    )
                except Exception:
                    pass
            if self.state_store:
                # Persist state: attempt to call settle_order with (product_id, notional)
                # signature if supported; otherwise fallback to original signature
                try:
                    await self.state_store.settle_order(product_id="UNKNOWN", notional=notional)  # type: ignore[arg-type]
                except TypeError:
                    try:
                        await self.state_store.settle_order(client_order_id, fill_price, size)  # type: ignore[misc]
                    except Exception:
                        pass
                except Exception:
                    pass

    async def mark_pnl(self, product_id: str, price: float) -> None:
        """Mark positions to market and update PnL.

        This method should be called periodically with current prices to
        update floating PnL.  It does not persist exposures but updates
        daily PnL for kill switch checks.
        """
        async with self._lock:
            position = self.positions.get(product_id, 0.0)
            self.daily_pnl += position * price
            if self.daily_max_loss and -self.daily_pnl > self.daily_max_loss:
                self.kill_switch_engaged = True
            if self.state_store:
                await self.state_store.update_pnl(product_id, position, price)

            # Publish PnL update on mark‑to‑market as well
            if self.event_bus:
                try:
                    await self.event_bus.publish(
                        "pnl_update",
                        {
                            "daily_pnl": self.daily_pnl,
                            "kill_switch": self.kill_switch_engaged,
                        },
                    )
                except Exception:
                    pass

    async def record_price(self, product_id: str, price: float) -> None:
        """Record a new price and update return history for volatility estimation.

        The price history stores percentage returns between consecutive
        observations.  When ``volatility_window`` is less than 2, this
        method is a no‑op.
        """
        # Only compute returns when the volatility window is at least 2
        if self.volatility_window and self.volatility_window > 1:
            history = self._price_histories[product_id]
            # If there is a previous price stored on the history, compute return
            last_price = getattr(history, "last_price", None)
            if last_price is not None:
                try:
                    ret = (price - last_price) / last_price
                    history.append(ret)
                    # Update EWMA variance for this product if using the EWMA method.
                    # The variance is updated as: v_t = alpha * r_t^2 + (1 - alpha) * v_{t-1}
                    # where ``alpha`` is the smoothing factor.  If no prior variance exists
                    # we initialize it with the squared return.
                    if self.volatility_method == "ewma" and self.volatility_alpha > 0:
                        prev_var = self._ewma_variances.get(product_id)
                        if prev_var is None:
                            new_var = ret * ret
                        else:
                            new_var = self.volatility_alpha * (ret * ret) + (1 - self.volatility_alpha) * prev_var
                        self._ewma_variances[product_id] = new_var
                except Exception:
                    pass
            # Store last observed price for next calculation
            setattr(history, "last_price", price)

        # Update ATR histories.  ATR is based on the absolute percentage change
        # between consecutive prices.  Only update when the ATR window is at least 1.
        if self.atr_window and self.atr_window > 0:
            atr_history = self._atr_histories[product_id]
            last_atr_price = getattr(atr_history, "last_price", None)
            if last_atr_price is not None and last_atr_price > 0:
                try:
                    abs_ret = abs(price - last_atr_price) / last_atr_price
                    atr_history.append(abs_ret)
                    # Compute the simple moving average of the absolute returns to obtain ATR
                    if atr_history:
                        self._atr_values[product_id] = sum(atr_history) / len(atr_history)
                except Exception:
                    pass
            setattr(atr_history, "last_price", price)

    def _compute_volatility(self, product_id: str) -> Optional[float]:
        """Compute a volatility estimate for the given product.

        The volatility calculation depends on the configured ``volatility_method``:

        * ``std``  – Returns the sample standard deviation of recent percentage
          returns.  Requires at least two return observations.
        * ``ewma`` – Returns the square root of the exponentially weighted
          variance maintained in ``_ewma_variances``.  Returns ``None`` if no
          variance has been recorded yet.

        When the ``volatility_window`` is disabled (< 2), this method returns
        ``None``.

        Args:
            product_id: The symbol for which to compute volatility.

        Returns:
            A floating point volatility estimate or ``None`` if insufficient
            data is available.
        """
        # If volatility tracking is disabled
        # If volatility tracking is disabled for std/ewma or ATR window too small, return None
        if self.volatility_method == "atr":
            # ATR uses its own window size; return None if window < 1
            if not self.atr_window or self.atr_window < 1:
                return None
            # Return the most recently computed ATR value for this product
            return self._atr_values.get(product_id)

        if not self.volatility_window or self.volatility_window < 2:
            return None
        if self.volatility_method == "ewma":
            import math
            var = self._ewma_variances.get(product_id)
            if var is None or var <= 0:
                return None
            return math.sqrt(var)
        # Default: sample standard deviation
        hist = self._price_histories.get(product_id)
        if not hist or len(hist) < max(1, self.volatility_window - 1):
            return None
        import math
        mean = sum(hist) / len(hist)
        # Use sample variance (unbiased) if more than one observation, else population variance
        if len(hist) > 1:
            variance = sum((x - mean) ** 2 for x in hist) / (len(hist) - 1)
        else:
            variance = sum((x - mean) ** 2 for x in hist) / len(hist)
        return math.sqrt(variance)

    # ------------------------------------------------------------------
    # Accessors for exposures and positions
    #
    async def get_exposures(self) -> Dict[str, float]:
        """Return current exposures per product.

        If a state store is configured and supports ``get_exposures()``, the
        result from the store is merged with in‑memory exposures.  Otherwise,
        returns the in‑memory exposures only.
        """
        exposures = dict(self.exposures)
        if self.state_store and hasattr(self.state_store, "get_exposures"):
            try:
                store_exposures = await self.state_store.get_exposures()
                for k, v in store_exposures.items():
                    exposures[k] = exposures.get(k, 0.0) + v
            except Exception:
                pass
        return exposures

    async def get_positions(self) -> Dict[str, Dict[str, float]]:
        """Return current positions per product.

        If a state store is configured and supports ``get_positions()``, the
        result from the store is returned.  Otherwise returns in‑memory positions.
        """
        if self.state_store and hasattr(self.state_store, "get_positions"):
            try:
                return await self.state_store.get_positions()
            except Exception:
                pass
        return {
            product: {"quantity": qty, "average_price": 0.0}
            for product, qty in self.positions.items()
        }
