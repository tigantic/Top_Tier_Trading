"""Integration test for the ops bot health endpoint.

This test ensures that the helper functions used to implement the
health endpoint do not raise exceptions and that ``fetch_metrics``
returns a dictionary even when the Prometheus endpoint is not
reachable (in which case it returns an empty dict).  In a real
deployment you would perform an HTTP GET against ``/healthz`` on
the running bot and assert the returned JSON contains a ``status``
field.  Offline we limit ourselves to functional testing of the
underlying call.
"""

import pytest  # type: ignore

from scripts import ops_bot_async


@pytest.mark.asyncio  # type: ignore
async def test_fetch_metrics_returns_dict():
    data = await ops_bot_async.fetch_metrics()
    assert isinstance(data, dict)
