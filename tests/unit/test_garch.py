"""Unit tests for the GARCH(1,1) estimator and forecaster.

This module validates the implementation in
``workers/src/workers/risk/garch.py`` by checking that parameter
estimates are returned for a non‑degenerate returns series and
that forecasts are positive.  It also ensures that invalid inputs
raise errors.

The tests are designed to run offline without external packages.
"""

from __future__ import annotations

import pytest  # type: ignore

from workers.risk.garch import fit_garch, forecast_volatility


def test_fit_garch_returns_positive_parameters() -> None:
    """fit_garch should return non‑negative parameters for typical returns."""
    # Construct a simple returns series with moderate variance
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01]
    params = fit_garch(returns)
    assert "omega" in params and "alpha" in params and "beta" in params
    # Parameters should be non‑negative
    assert params["omega"] >= 0.0
    assert params["alpha"] >= 0.0
    assert params["beta"] >= 0.0
    # alpha + beta must be less than 1 for stationarity
    assert params["alpha"] + params["beta"] < 1.0


def test_fit_garch_constant_returns() -> None:
    """Constant return series should yield zero parameters and zero volatility."""
    returns = [0.01] * 5
    params = fit_garch(returns)
    assert params["omega"] == 0.0
    assert params["alpha"] == 0.0
    assert params["beta"] == 0.0
    forecast = forecast_volatility(params, horizon=3)
    # All forecasts should be exactly zero
    assert forecast == [0.0, 0.0, 0.0]


def test_forecast_volatility_positive() -> None:
    """forecast_volatility should return a positive volatility for each horizon step."""
    params = {"omega": 1e-6, "alpha": 0.1, "beta": 0.8}
    forecast = forecast_volatility(params, horizon=5)
    assert len(forecast) == 5
    for v in forecast:
        # Each forecasted volatility should be a positive float
        assert isinstance(v, float)
        assert v > 0.0


def test_fit_garch_invalid_input_raises() -> None:
    """fit_garch should raise ValueError when given insufficient data."""
    with pytest.raises(ValueError):
        fit_garch([])  # empty list
    with pytest.raises(ValueError):
        fit_garch([0.01])  # only one observation
    # If returns series has no variance and length < 2, should raise


def test_fit_garch_clamps_unstable_params() -> None:
    """fit_garch should clamp alpha+beta to at most 0.999 when the heuristic would produce >1."""
    # Create returns with large autocorrelation to force a high rho and alpha
    returns = [0.05, 0.05, 0.05, -0.05, -0.05, -0.05]
    params = fit_garch(returns)
    assert params["alpha"] >= 0.0
    assert params["beta"] >= 0.0
    assert params["alpha"] + params["beta"] <= 0.999


def test_forecast_volatility_non_negative_non_nan() -> None:
    """Forecast volatilities should be non‑negative and not NaN for horizon >= 1."""
    params = {"omega": 1e-6, "alpha": 0.15, "beta": 0.8}
    forecast = forecast_volatility(params, horizon=3)
    for v in forecast:
        assert v >= 0.0
        assert v == v  # check not NaN



def test_forecast_volatility_invalid_horizon_raises() -> None:
    """forecast_volatility should raise ValueError on invalid inputs."""
    params = {"omega": 1e-6, "alpha": 0.1, "beta": 0.8}
    # Negative horizon
    with pytest.raises(ValueError):
        forecast_volatility(params, -1)
    # Non‑stationary parameters (alpha + beta >= 1)
    with pytest.raises(ValueError):
        forecast_volatility({"omega": 1e-6, "alpha": 0.6, "beta": 0.5}, 1)


def test_fit_garch_returns_snapshot_keys() -> None:
    """The parameter dictionary should always have the keys 'omega', 'alpha', 'beta'."""
    params = fit_garch([0.01, -0.02, 0.03])
    assert sorted(params.keys()) == ["alpha", "beta", "omega"]