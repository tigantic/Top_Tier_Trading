"""
HTTP exchange client with signing, rate limiting, and retries.

This module defines a lightweight asynchronous client for interacting with
the Coinbase Advanced Trade REST API.  It supports API key authentication
with HMAC-SHA256 signing (legacy keys) and is designed to work in DRY_RUN
mode where requests are routed to the static sandbox via the `X-Sandbox`
header.  Simple rate limiting is enforced via an asyncio semaphore.

Note: Coinbase introduced Ed25519 secrets for CDP API keys in February 2025.
This implementation does not yet support Ed25519 signing; it falls back to
HMAC for compatibility.  JWT-based authentication for the user channel is
handled separately in the JwtManager.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientResponse
from tenacity import retry, stop_after_attempt, wait_exponential

# Import authentication provider abstraction.  This import is optional to avoid
# circular dependencies when the provider module is not used.
try:
    from .auth_providers import AuthProvider  # type: ignore
except Exception:
    AuthProvider = None  # type: ignore


logger = logging.getLogger(__name__)


class HttpExchangeClient:
    """Asynchronous Coinbase REST API client with simple rate limiting."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        *,
        auth_provider: Optional["AuthProvider"] = None,
        base_url: str = "https://api.exchange.coinbase.com",
        dry_run: bool = True,
        max_requests_per_minute: int = 120,
    ) -> None:
        """Construct the HTTP client.

        Args:
            api_key: API key for HMAC authentication.  Ignored when
                ``auth_provider`` is supplied; defaults to environment ``COINBASE_API_KEY``.
            api_secret: API secret (base64 or raw).  Ignored when
                ``auth_provider`` is supplied.
            passphrase: API passphrase for legacy keys.  Ignored when
                ``auth_provider`` is supplied.
            auth_provider: Optional authentication provider; if supplied,
                headers will be delegated to it.  See ``auth_providers.py``.
            base_url: Coinbase REST base URL.
            dry_run: When true, include the ``X-Sandbox`` header on requests.
            max_requests_per_minute: Maximum number of REST requests per minute.
        """
        # Store authentication provider
        self.auth_provider: Optional[AuthProvider] = auth_provider  # type: ignore[assignment]
        # Fallback to env credentials if no provider is specified
        self.api_key = api_key or os.getenv("COINBASE_API_KEY", "")
        # If the secret is not provided directly, attempt to load from file or env
        secret_value: str | None = api_secret or os.getenv("COINBASE_API_SECRET")
        if not secret_value:
            secret_path = os.environ.get("COINBASE_API_SECRET_FILE")
            if secret_path and os.path.exists(secret_path):
                try:
                    with open(secret_path, "r", encoding="utf-8") as f:
                        secret_value = f.read().strip()
                        logger.debug("Loaded API secret from %s", secret_path)
                except Exception as exc:
                    logger.warning("Failed to load API secret file %s: %s", secret_path, exc)
        self.api_secret = secret_value or ""
        self.passphrase = passphrase or os.getenv("COINBASE_PASSPHRASE", "")
        self.base_url = base_url
        self.dry_run = dry_run
        # Token bucket to enforce per‑minute request limit.  Tokens are
        # consumed on each request and replenished over time.  This
        # ensures that bursts are smoothed across the minute.
        self.max_requests_per_minute = max_requests_per_minute
        self.tokens = max_requests_per_minute
        self._token_lock = asyncio.Lock()
        self._last_refill = time.monotonic()
        # Interval (in seconds) at which a token becomes available.
        self._token_interval = (
            60.0 / max_requests_per_minute if max_requests_per_minute > 0 else 60.0
        )

    def _sign_request(self, timestamp: str, method: str, request_path: str, body: str) -> str:
        """Generate a HMAC-SHA256 signature for the request."""
        message = f"{timestamp}{method.upper()}{request_path}{body}".encode()
        try:
            key = base64.b64decode(self.api_secret)
        except Exception:
            key = self.api_secret.encode()
        return hmac.new(key, message, hashlib.sha256).digest().hex()

    def _build_default_headers(self, method: str, request_path: str, body: str) -> Dict[str, str]:
        """Build default HMAC-based authentication headers.

        This is used when no custom authentication provider is supplied.
        """
        timestamp = str(int(time.time()))
        signature = self._sign_request(timestamp, method, request_path, body)
        headers = {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "CB-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        if self.dry_run:
            headers["X-Sandbox"] = "true"
        return headers

    async def _acquire_token(self) -> None:
        """Wait until a request token is available based on the token bucket."""
        while True:
            async with self._token_lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                # Refill tokens according to elapsed time
                if elapsed > 0 and self.max_requests_per_minute > 0:
                    new_tokens = int(elapsed / self._token_interval)
                    if new_tokens > 0:
                        self.tokens = min(self.max_requests_per_minute, self.tokens + new_tokens)
                        self._last_refill = now
                if self.tokens > 0:
                    self.tokens -= 1
                    return
            # If no tokens available, sleep for one interval
            await asyncio.sleep(self._token_interval)

    async def _request(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None
    ) -> Any:
        # Rate limiting: acquire token
        await self._acquire_token()
        url = f"{self.base_url}{path}"
        body = json.dumps(payload) if payload else ""
        # Build headers using custom auth provider if available, else default
        if self.auth_provider is not None:
            try:
                headers = await self.auth_provider.get_headers(method, path, body)
            except Exception as exc:
                logger.error("Auth provider failed to build headers: %s", exc)
                # Fallback to default headers
                headers = self._build_default_headers(method, path, body)
            # Propagate sandbox header if dry_run is enabled
            if self.dry_run:
                headers = dict(headers)
                headers["X-Sandbox"] = "true"
        else:
            headers = self._build_default_headers(method, path, body)
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, data=body) as resp:
                await self._handle_response_errors(resp)
                return await resp.json()

    @staticmethod
    async def _handle_response_errors(resp: ClientResponse) -> None:
        if resp.status >= 400:
            # Avoid logging full response bodies; truncate to prevent leakage
            text = await resp.text()
            truncated = text[:200] if text else ""
            logger.error("REST API error %s: %s", resp.status, truncated)
            raise RuntimeError(f"REST API error {resp.status}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def get(self, path: str) -> Any:
        return await self._request("GET", path)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def post(self, path: str, payload: Dict[str, Any]) -> Any:
        return await self._request("POST", path, payload)

    # Convenience methods for common endpoints
    async def list_accounts(self) -> Any:
        return await self.get("/api/v3/brokerage/accounts")

    async def list_products(self) -> Any:
        return await self.get("/api/v3/brokerage/products")

    async def create_order(self, payload: Dict[str, Any]) -> Any:
        return await self.post("/api/v3/brokerage/orders", payload)
