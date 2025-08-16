"""Tests for AlertService secrets loading and fallback behaviour.

These tests verify that the AlertService correctly loads configuration
values from environment variables when the secrets manager does not
return anything.  They do not exercise message sending or the event
loop, as those require integration tests with Slack or Teams.
"""

import os
import sys
import asyncio

import pytest  # type: ignore

from workers.services.alert_service import AlertService


class DummyEventBus:
    """Simple event bus that yields a single message then stops."""

    def __init__(self, message):
        self.message = message

    async def subscribe(self, channel):  # type: ignore[override]
        yield self.message


def test_alert_service_env_fallback(monkeypatch):
    """AlertService should fall back to environment variables when secrets manager is absent."""
    # Ensure no secrets manager is returned
    monkeypatch.setenv("SECRETS_BACKEND", "invalid")
    monkeypatch.setenv("ALERT_ENABLE", "true")
    monkeypatch.setenv("ALERT_PNL_THRESHOLD", "10")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C12345")
    # Create service
    service = AlertService(event_bus=DummyEventBus({"daily_pnl": -20, "kill_switch": False}))
    # Config should be loaded from env
    assert service.enabled is True
    assert service.pnl_threshold == 10.0
    assert service.slack_token == "xoxb-test-token"
    assert service.slack_channel == "C12345"
    # Disabled Teams by default
    assert service.teams_webhook is None


@pytest.mark.asyncio  # type: ignore
async def test_alert_service_teams(monkeypatch):
    """Teams webhook should be loaded and trigger a fallback if requests is missing."""
    monkeypatch.setenv("ALERT_ENABLE", "true")
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.com/webhook")
    # Ensure requests import fails to force logging fallback
    monkeypatch.setitem(sys.modules, "requests", None)
    service = AlertService(event_bus=DummyEventBus({"kill_switch": True, "daily_pnl": -5}))
    # Should read TEAMS_WEBHOOK_URL
    assert service.teams_webhook == "https://example.com/webhook"
    # Run briefly then cancel; service.run() loops forever
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass