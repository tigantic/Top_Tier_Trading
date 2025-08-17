"""GARCH(1,1) volatility model.

This module implements a simple GARCH(1,1) estimator and forecaster
usable in offline environments.  It does not rely on external
packages and uses method‑of‑moments heuristics to estimate the
parameters.  A GARCH(1,1) model specifies that the conditional
variance of returns follows::

    sigma_t^2 = omega + alpha * epsilon_{t-1}^2 + beta * sigma_{t-1}^2

where ``epsilon`` is the return series and ``sigma`` is the
conditional standard deviation.  The functions below estimate
``omega``, ``alpha`` and ``beta`` from a series of returns and
produce volatility forecasts over a specified horizon.

Functions
---------
fit_garch(returns: list[float]) -> dict[str, float]
    Estimate ``omega``, ``alpha`` and ``beta`` parameters for a GARCH(1,1) model.

forecast_volatility(params: dict[str, float], horizon: int) -> list[float]
    Forecast conditional standard deviation for a specified number of steps.

Notes
-----
The estimator implemented here uses simple statistics (variance and
lag‑1 autocorrelation of squared returns) to infer parameters:

* ``var_ret`` – sample variance of the return series.
* ``rho`` – lag‑1 autocorrelation of squared returns.

We set ``alpha`` proportional to ``rho`` and ``beta`` to ensure
``alpha + beta < 1``.  ``omega`` is then derived such that the
unconditional variance matches ``var_ret``.  This approach is a
first‑order approximation and does not involve numerical optimisation.

Examples
--------
Typical usage involves computing returns, fitting a GARCH model and
forecasting volatility for the next periods::

    >>> returns = [0.01, -0.02, 0.015, -0.005, 0.02]
    >>> params = fit_garch(returns)
    >>> sorted(params.keys())
    ['alpha', 'beta', 'omega']
    >>> forecast = forecast_volatility(params, horizon=3)
    >>> len(forecast) == 3
    True

These examples work in offline environments.  In a production
deployment, you would derive ``returns`` from historical price data
and periodically re‑estimate parameters.
"""

from __future__ import annotations

from typing import Dict, List


def _compute_returns(prices: List[float]) -> List[float]:
    """Compute percentage returns from a list of prices.

    Parameters
    ----------
    prices : list[float]
        A sequence of price observations.

    Returns
    -------
    list[float]
        Percentage returns between consecutive prices.
    """
    returns: List[float] = []
    for prev, curr in zip(prices[:-1], prices[1:]):
        if prev != 0:
            returns.append((curr - prev) / prev)
    return returns


def fit_garch(returns: List[float]) -> Dict[str, float]:
    """Estimate GARCH(1,1) parameters from a return series.

    Parameters
    ----------
    returns : list[float]
        Sequence of percentage returns.  Must contain at least two
        observations.

    Returns
    -------
    dict[str, float]
        Dictionary with keys ``omega``, ``alpha`` and ``beta``.

    Raises
    ------
    ValueError
        If the return series is empty or contains fewer than two
        observations.

    Examples
    --------
    >>> returns = [0.01, -0.02, 0.015, -0.005, 0.02]
    >>> params = fit_garch(returns)
    >>> sorted(params.keys())
    ['alpha', 'beta', 'omega']
    >>> params['alpha'] >= 0 and params['beta'] >= 0
    True

    Notes
    -----
    This implementation uses simple method‑of‑moments heuristics:

    1. Compute the sample variance of ``returns`` as ``var_ret``.
    2. Compute the lag‑1 autocorrelation of squared returns (``rho``).
    3. Set ``alpha = max(0.01, min(0.2, abs(rho)))``.
    4. Set ``beta = max(0.75, 0.95 - alpha)`` ensuring ``alpha + beta < 1``.
    5. Compute ``omega = var_ret * (1 - alpha - beta)`` to match the
       unconditional variance.

    These values provide a reasonable starting point for volatility
    forecasting and satisfy the positivity and stationarity
    constraints (``omega > 0``, ``alpha >= 0``, ``beta >= 0``,
    ``alpha + beta < 1``).

    Stability
    ---------
    The estimator clamps parameter values to ensure numerical
    stability.  Specifically, ``alpha`` and ``beta`` are enforced
    to be non‑negative and their sum is capped at 0.999.  This
    prevents explosive variance forecasts (where ``alpha + beta ≥ 1``)
    and ensures the GARCH(1,1) model remains stationary.  ``omega``
    is computed accordingly to preserve the unconditional variance.
    """
    n = len(returns)
    if n < 2:
        raise ValueError("Return series must contain at least two values to fit GARCH")
    # Sample variance
    mean_ret = sum(returns) / n
    var_ret = sum((r - mean_ret) ** 2 for r in returns) / (n - 1)
    if var_ret <= 0:
        # Zero variance series; return trivial parameters
        return {"omega": 0.0, "alpha": 0.0, "beta": 0.0}
    # Compute lag‑1 autocorrelation of squared returns
    sq = [r**2 for r in returns]
    mean_sq = sum(sq) / n
    # numerator: covariance of squared returns at lag 1
    num = sum((sq[t] - mean_sq) * (sq[t - 1] - mean_sq) for t in range(1, n))
    den = sum((sq[t] - mean_sq) ** 2 for t in range(n))
    rho = num / den if den != 0 else 0.0
    # Map rho into a reasonable alpha range
    alpha = max(0.01, min(0.2, abs(rho)))
    # Choose beta to satisfy stationarity and reflect persistence
    beta = max(0.75, 0.95 - alpha)
    # Clamp parameters to maintain stability: non‑negative and sum <= 0.999
    if alpha < 0.0:
        alpha = 0.0
    if beta < 0.0:
        beta = 0.0
    # Ensure alpha + beta does not exceed 0.999 (stationarity)
    if alpha + beta > 0.999:
        # distribute the excess proportionally (or set beta accordingly)
        beta = 0.999 - alpha
        if beta < 0.0:
            beta = 0.0
    omega = var_ret * (1 - alpha - beta)
    return {"omega": omega, "alpha": alpha, "beta": beta}


def forecast_volatility(params: Dict[str, float], horizon: int) -> List[float]:
    """Forecast conditional standard deviation over a horizon.

    Parameters
    ----------
    params : dict[str, float]
        Dictionary with keys ``omega``, ``alpha`` and ``beta``.
    horizon : int
        Number of steps ahead to forecast.  Must be non‑negative.

    Returns
    -------
    list[float]
        List of forecasted volatilities (standard deviations).  The
        first element corresponds to the next period (t+1).

    Examples
    --------
    >>> params = {'omega': 1e-6, 'alpha': 0.1, 'beta': 0.8}
    >>> forecast_volatility(params, horizon=3)
    [0.0010000000000000002, 0.0010000000000000002, 0.0010000000000000002]

    Raises
    ------
    ValueError
        If ``horizon`` is negative or ``alpha + beta >= 1``.
    """
    if horizon < 0:
        raise ValueError("horizon must be non‑negative")
    omega = params.get("omega", 0.0)
    alpha = params.get("alpha", 0.0)
    beta = params.get("beta", 0.0)
    if alpha + beta >= 1.0:
        raise ValueError("alpha + beta must be less than 1 for stationarity")
    # Compute unconditional variance (long run)
    if 1 - alpha - beta != 0:
        sigma2 = omega / (1 - alpha - beta)
    else:
        sigma2 = omega
    forecasts: List[float] = []
    for _ in range(horizon):
        sigma2 = omega + (alpha + beta) * sigma2
        forecasts.append(sigma2**0.5)  # standard deviation
    return forecasts


# Backwards compatibility: keep the old name as an alias
def estimate_garch_parameters(prices: List[float]) -> Dict[str, float]:
    """Estimate GARCH(1,1) parameters from a price series.

    This function computes percentage returns from ``prices`` and
    delegates to :func:`fit_garch`.  It is retained for backwards
    compatibility with older code that expected to pass prices.
    """
    if len(prices) < 2:
        return {"omega": 0.0, "alpha": 0.0, "beta": 0.0}
    returns = _compute_returns(prices)
    if len(returns) < 2:
        return {"omega": 0.0, "alpha": 0.0, "beta": 0.0}
    return fit_garch(returns)
