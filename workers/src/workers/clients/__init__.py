"""
Client utilities for interacting with external services.

This package currently provides a generic HTTP exchange client with
rate limiting and retry logic, as well as a JWT manager for refreshing
user channel tokens.  Additional clients (e.g., for databases or caches)
should live here.
"""

from .http_exchange import HttpExchangeClient  # noqa: F401
from .jwt_manager import JwtManager  # noqa: F401
