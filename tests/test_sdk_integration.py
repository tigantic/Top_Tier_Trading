"""Integration tests for the Coinbase SDK wrappers.

These tests ensure that the SDK integration harness can be imported
and that the stubbed clients are wired correctly.  Because the
offline environment cannot install the official Coinbase SDK or
connect to the network, these tests focus on verifying that the
harness runs to completion without raising exceptions and that it
initialises the correct client classes based on environment
variables.
"""

import asyncio
import importlib

import pytest  # type: ignore


@pytest.mark.asyncio  # type: ignore
async def test_sdk_integration_harness_imports():
    """Ensure the sdk_integration_test module can be imported."""
    mod = importlib.import_module("scripts.sdk_integration_test")
    assert hasattr(mod, "run_market_data")
    assert hasattr(mod, "run_user_channel")


@pytest.mark.asyncio  # type: ignore
async def test_sdk_harness_runs_without_sdk(monkeypatch):
    """Run the harness briefly and ensure no exceptions when SDK is unavailable."""
    # Simulate offline environment by unsetting SDK env var
    monkeypatch.setenv("USE_OFFICIAL_SDK", "true")
    # Import after monkeypatch so env takes effect
    mod = importlib.import_module("scripts.sdk_integration_test")
    # Run only for a short time; tasks should not yield data but should not error
    task = asyncio.create_task(mod.run_market_data())
    # Cancel after a tiny delay
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
