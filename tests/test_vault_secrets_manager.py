"""Tests for VaultSecretsManager fallback behaviour.

This test verifies that when Vault is not configured the
VaultSecretsManager falls back to reading from environment variables.
"""

from workers.src.workers.secrets_manager import VaultSecretsManager


def test_vault_fallback(monkeypatch):
    """VaultSecretsManager should use EnvFileSecretsManager when Vault is not configured."""
    # Ensure VAULT_ADDR and VAULT_TOKEN are not set
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    monkeypatch.setenv("COINBASE_API_KEY", "dummy_key")
    mgr = VaultSecretsManager(prefix=None)
    val = mgr.get_secret("COINBASE_API_KEY")
    assert val == "dummy_key"
