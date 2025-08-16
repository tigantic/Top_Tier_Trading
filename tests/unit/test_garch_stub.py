"""Test the GARCH(1,1) stub estimator.

This unit test verifies that the ``estimate_garch_parameters`` function
returns a dictionary with the expected keys and that the values are
non‑negative.  The test uses a simple synthetic price series to
exercise the variance calculation.  Because the GARCH estimator in
offline mode uses heuristics, we only assert structural properties.
"""

from workers.risk.garch import estimate_garch_parameters


def test_garch_stub_returns_dict() -> None:
    prices = [100.0, 101.0, 102.5, 101.5, 103.0]
    params = estimate_garch_parameters(prices)
    assert isinstance(params, dict)
    assert set(params.keys()) == {"omega", "alpha", "beta"}
    assert params["omega"] >= 0.0
    assert 0.0 <= params["alpha"] <= 1.0
    assert 0.0 <= params["beta"] <= 1.0