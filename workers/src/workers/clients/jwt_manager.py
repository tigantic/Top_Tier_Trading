"""
JWT manager for the user channel.

This module provides a helper class to fetch and refresh JSON Web Tokens
(JWTs) required by the Coinbase Advanced Trade user channel.  JWTs expire
approximately every two minutes, so the user channel worker must refresh
its token periodically.  In this scaffolding implementation, the token is
simply read from an environment variable and reloaded at a configurable
interval.  In future phases, this class will call the appropriate REST
endpoint to obtain fresh JWTs using OAuth.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional


logger = logging.getLogger(__name__)


class JwtManager:
    def __init__(self, refresh_interval: int = 110) -> None:
        """
        :param refresh_interval: Seconds between token refreshes.  Coinbase
            recommends refreshing JWTs approximately every 2 minutes (120s).  We
            default to 110 seconds to allow a safety margin.
        """
        self.refresh_interval = refresh_interval
        self._jwt: Optional[str] = os.environ.get("COINBASE_JWT")

    @property
    def token(self) -> str:
        if not self._jwt:
            raise RuntimeError(
                "COINBASE_JWT not set. Please obtain a JWT via the REST API and set it as an environment variable."
            )
        return self._jwt

    async def refresh_token(self) -> None:
        """Refresh the JWT by re-reading it from the environment.

        In a future implementation, this method will call Coinbase's token
        refresh endpoint using OAuth credentials.
        """
        while True:
            await asyncio.sleep(self.refresh_interval)
            new_token = os.environ.get("COINBASE_JWT")
            if new_token and new_token != self._jwt:
                logger.info("JWT refreshed")
                self._jwt = new_token
