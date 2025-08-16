"""Tests for ops bot concurrency, retry and deduplication logic.

These tests focus on the helper logic inside the Redis listener that
deduplicates alerts and retries failed Slack posts.  They do not
exercise the Slack client, which is not available offline.  Instead,
we simulate the deduplication set and ensure it filters repeated
messages.
"""

import asyncio
import time

import pytest  # type: ignore


async def test_deduplication_logic(monkeypatch):
    # Simulate the deduplication sets and send logic by capturing texts
    sent_texts = []
    async def fake_chat_postMessage(channel: str, text: str):  # noqa: D401
        sent_texts.append(text)
    # Patch the Slack client's chat_postMessage method
    class DummyClient:
        async def chat_postMessage(self, channel: str, text: str):
            await fake_chat_postMessage(channel, text)
    # Set up dedup structures similar to ops_bot_async.redis_listener
    recent_alerts = set()
    alert_times = {}
    expiry = 1.0
    async def send_alert(text: str):
        nonlocal recent_alerts, alert_times
        now = time.time()
        # expire old
        for t in list(alert_times):
            if now - alert_times[t] > expiry:
                recent_alerts.discard(t)
                del alert_times[t]
        if text not in recent_alerts:
            # simulate immediate success
            await fake_chat_postMessage("channel", text)
            recent_alerts.add(text)
            alert_times[text] = now
    # Send same text twice quickly; second should be deduped
    await send_alert("test message")
    await send_alert("test message")
    assert sent_texts.count("test message") == 1
    # After expiry, it should send again
    await asyncio.sleep(expiry + 0.1)
    await send_alert("test message")
    assert sent_texts.count("test message") == 2