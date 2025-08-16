"""
Authentication provider abstractions for Coinbase APIs.

These classes encapsulate the logic for constructing HTTP headers for
different authentication modes.  Separating auth concerns from the HTTP
client allows switching between API key and OAuth flows without
modifying the client code.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Dict, Optional


class AuthProvider:
    """Abstract base class for authentication providers."""

    async def get_headers(self, method: str, path: str, body: str) -> Dict[str, str]:
        """Return headers for the given request.

        Subclasses must implement this method.
        """
        raise NotImplementedError


class ApiKeyProvider(AuthProvider):
    """HMAC-based authentication using API key, secret and optional passphrase."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, passphrase: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("COINBASE_API_KEY", "")
        # Secret may be provided directly or via file defined by COINBASE_API_SECRET_FILE
        secret_value = api_secret or os.getenv("COINBASE_API_SECRET")
        if not secret_value:
            secret_path = os.getenv("COINBASE_API_SECRET_FILE")
            if secret_path and os.path.exists(secret_path):
                try:
                    with open(secret_path, "r", encoding="utf-8") as f:
                        secret_value = f.read().strip()
                except Exception:
                    secret_value = ""
        self.api_secret = secret_value or ""
        self.passphrase = passphrase or os.getenv("COINBASE_PASSPHRASE", "")

    def _sign(self, timestamp: str, method: str, path: str, body: str) -> str:
        """Sign the request using HMAC-SHA256 and return a base64-encoded signature."""
        message = f"{timestamp}{method.upper()}{path}{body}".encode()
        try:
            key = base64.b64decode(self.api_secret)
        except Exception:
            key = self.api_secret.encode()
        return base64.b64encode(hmac.new(key, message, hashlib.sha256).digest()).decode()

    async def get_headers(self, method: str, path: str, body: str) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        signature = self._sign(timestamp, method, path, body)
        headers: Dict[str, str] = {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "CB-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        return headers


class OAuthProvider(AuthProvider):
    """OAuth-based authentication for Coinbase Advanced Trade.

    Uses a bearer token stored in the ``COINBASE_ACCESS_TOKEN`` environment
    variable.  A retail portfolio ID may be provided via ``COINBASE_RETAIL_PORTFOLIO_ID``,
    which is required for spot orders when using OAuth.
    """

    def __init__(self, access_token: Optional[str] = None, portfolio_id: Optional[str] = None) -> None:
        self.access_token = access_token or os.getenv("COINBASE_ACCESS_TOKEN", "")
        self.portfolio_id = portfolio_id or os.getenv("COINBASE_RETAIL_PORTFOLIO_ID", "")

    async def get_headers(self, method: str, path: str, body: str) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        # Include the retail portfolio ID when available for spot orders
        if self.portfolio_id:
            headers["CB-RETAIL-PORTFOLIO-ID"] = self.portfolio_id
        return headers