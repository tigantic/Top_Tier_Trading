"""Unit tests for ops bot idempotency and deduplication.

These tests simulate the deduplication logic used in the ops bot
(`redis_listener`) to ensure that duplicate messages are suppressed
within a configurable TTL and that messages expire correctly.
"""

import time


def test_dedup_cache_ttl(monkeypatch):
    # Simulate the deduplication cache structure used in redis_listener
    dedup_cache: dict[str, float] = {}
    expiry_seconds = 1.0

    def should_send(msg: str) -> bool:
        # Evict expired
        now = time.time()
        expired = [m for m, ts in dedup_cache.items() if now > ts]
        for m in expired:
            dedup_cache.pop(m, None)
        if msg in dedup_cache:
            return False
        dedup_cache[msg] = now + expiry_seconds
        return True

    # First send should pass
    assert should_send("alert") is True
    # Immediate duplicate should be suppressed
    assert should_send("alert") is False
    # After TTL expires, message should be allowed again
    time.sleep(expiry_seconds + 0.1)
    assert should_send("alert") is True