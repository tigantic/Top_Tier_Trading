"""
secrets_manager
================

This module provides a simple abstraction for loading secrets in a secure and
extensible way.  At runtime, secrets may be loaded from environment
variables, a configuration file, or an external secrets manager such as AWS
Secrets Manager or HashiCorp Vault.  The default implementation here is
minimal: it first attempts to read a value from the environment, then
optionally from a file if the corresponding ``*_FILE`` environment variable
is set.  This design allows operators to mount secrets as files in Docker
containers (e.g., via Kubernetes secrets) without leaking them into the
environment.  To integrate with a real secrets manager, subclass
``BaseSecretsManager`` and override ``get_secret`` to fetch and cache
secrets from the appropriate backend.

Example usage::

    from workers.secrets_manager import SecretsManager

    secrets = SecretsManager()
    api_key = secrets.get_secret("COINBASE_API_KEY")
    api_secret = secrets.get_secret("COINBASE_API_SECRET")
    private_key = secrets.get_secret("COINBASE_API_SECRET_FILE")

```
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import boto3  # type: ignore
except ImportError:
    boto3 = None  # type: ignore


class BaseSecretsManager:
    """Abstract base class for secrets managers."""

    def get_secret(self, name: str) -> Optional[str]:  # pragma: no cover - override
        """Return the secret value for ``name`` or ``None`` if unavailable."""
        raise NotImplementedError


class EnvFileSecretsManager(BaseSecretsManager):
    """
    Loads secrets from environment variables and optional ``*_FILE`` paths.

    If an environment variable ``{name}_FILE`` is set, its contents are read
    from the specified file.  This allows secrets to be mounted into
    containers via Kubernetes secrets or Docker secrets.  If both
    ``{name}`` and ``{name}_FILE`` are set, the file takes precedence.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        #: Optional base directory to resolve relative file paths.
        self.base_path = base_path
        #: Simple cache to avoid repeated file reads.
        self._cache: Dict[str, Optional[str]] = {}

    def get_secret(self, name: str) -> Optional[str]:
        # Return cached value if present
        if name in self._cache:
            return self._cache[name]

        file_env = f"{name}_FILE"
        # File path takes precedence over direct environment variables
        file_path = os.getenv(file_env)
        if file_path:
            # Resolve relative paths against ``base_path`` if provided
            path = Path(file_path)
            if not path.is_absolute() and self.base_path is not None:
                path = self.base_path / path
            try:
                value = path.read_text().strip()
            except Exception:
                value = None
        else:
            value = os.getenv(name)

        # Cache and return
        self._cache[name] = value
        return value


class AwsSecretsManager(BaseSecretsManager):
    """
    Secrets manager backend for AWS Secrets Manager.

    This implementation fetches secrets from AWS Secrets Manager at runtime.
    It requires the ``boto3`` library and valid AWS credentials.  Secrets
    are expected to be stored with names following the pattern
    ``{prefix}/{name}``, where ``prefix`` is configured via the
    ``AWS_SECRETS_PREFIX`` environment variable.

    Secrets are cached in memory after the first retrieval to avoid
    repeated network calls.  Fetched secrets may be JSON strings or
    plain strings; if JSON is detected, the value is deserialised and
    the top‑level keys are merged into the cache with dot notation.
    """

    def __init__(self, *, prefix: Optional[str] = None, region_name: Optional[str] = None) -> None:
        if boto3 is None:
            raise RuntimeError(
                "boto3 is required for AwsSecretsManager; please install with `pip install boto3`"
            )
        self.prefix = prefix or os.getenv("AWS_SECRETS_PREFIX", "")
        self.region_name = region_name or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        self._cache: Dict[str, Optional[str]] = {}
        # Lazily initialise client to avoid unnecessary dependency if unused
        self._client: Any | None = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("secretsmanager", region_name=self.region_name)
        return self._client

    def get_secret(self, name: str) -> Optional[str]:
        # Check cache first
        if name in self._cache:
            return self._cache[name]
        # Construct secret id with optional prefix
        secret_id = f"{self.prefix}/{name}" if self.prefix else name
        try:
            response = self.client.get_secret_value(SecretId=secret_id)
            secret_string = response.get("SecretString")
        except Exception:
            secret_string = None
        # Cache the raw string; if JSON, store each field under name.field
        if secret_string:
            value = secret_string
            # Attempt to parse JSON
            if secret_string.strip().startswith("{"):
                try:
                    import json

                    data = json.loads(secret_string)
                    # Flatten top-level keys into cache: name.key
                    for key, val in data.items():
                        self._cache[f"{name}.{key}"] = val  # type: ignore[index]
                except Exception:
                    pass
        else:
            value = None
        self._cache[name] = value
        return value


class VaultSecretsManager(BaseSecretsManager):
    """Secrets manager backend for HashiCorp Vault.

    This implementation is intentionally minimal and serves as a
    placeholder for future integration with Vault.  It supports two
    modes:

    * If ``VAULT_ADDR`` and ``VAULT_TOKEN`` are provided, it will
      attempt to fetch a secret from the path ``{prefix}/{name}``
      using a simple HTTP GET to ``{VAULT_ADDR}/v1/secret/data/{path}``.  A
      JSON response is expected with the secret value under
      ``data.data.value``.
    * If Vault is not configured or the request fails, it falls back
      to reading from environment variables and ``*_FILE`` paths via
      ``EnvFileSecretsManager``.
    """

    def __init__(self, *, prefix: Optional[str] = None) -> None:
        self.prefix = prefix or os.getenv("VAULT_PREFIX", "")
        # Fallback delegate
        self.fallback = EnvFileSecretsManager(base_path=Path(os.getenv("SECRETS_BASE_PATH", "/")))

    def get_secret(self, name: str) -> Optional[str]:  # pragma: no cover
        addr = os.getenv("VAULT_ADDR")
        token = os.getenv("VAULT_TOKEN")
        if not (addr and token):
            # No Vault configured; fall back
            return self.fallback.get_secret(name)
        path = f"{self.prefix}/{name}" if self.prefix else name
        url = f"{addr.rstrip('/')}/v1/secret/data/{path}"
        import json
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers={"X-Vault-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            # Expect structure: {"data": {"data": {"value": "..."}}}
            return data.get("data", {}).get("data", {}).get("value")
        except Exception:
            # On failure, fall back
            return self.fallback.get_secret(name)


def get_default_secrets_manager() -> BaseSecretsManager:
    """
    Return the default secrets manager instance based on the
    ``SECRETS_BACKEND`` environment variable.  Supported values:

    * ``env`` (default) – use ``EnvFileSecretsManager`` to read from
      environment variables and optional ``*_FILE`` paths.
    * ``aws`` – use ``AwsSecretsManager`` to fetch secrets from AWS
      Secrets Manager.  Requires ``boto3`` and appropriate AWS credentials.
    """
    backend = os.getenv("SECRETS_BACKEND", "env").lower()
    if backend == "aws":
        try:
            return AwsSecretsManager()
        except Exception:
            # Fall back to environment if AWS backend fails to initialise
            return EnvFileSecretsManager(base_path=Path(os.getenv("SECRETS_BASE_PATH", "/")))
    if backend == "vault":
        # Prefer Vault; fall back gracefully if not configured
        return VaultSecretsManager(prefix=os.getenv("VAULT_PREFIX"))
    # Default to environment/file
    return EnvFileSecretsManager(base_path=Path(os.getenv("SECRETS_BASE_PATH", "/")))


__all__ = [
    "BaseSecretsManager",
    "EnvFileSecretsManager",
    "AwsSecretsManager",
    "VaultSecretsManager",
    "get_default_secrets_manager",
]