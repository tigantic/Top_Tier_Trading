## Security Guidelines

[← Back to docs index](./_index.md)

This document outlines best practices for managing secrets, access tokens and API keys used by the trading platform.  It also describes how to configure the various secrets backends and rotate credentials securely.

### Secrets Matrix

| Component              | Environment Variable           | Vault Path (example)                                      | Notes                                      |
|------------------------|--------------------------------|-----------------------------------------------------------|--------------------------------------------|
| Coinbase API Key       | `COINBASE_API_KEY`             | `secret/data/trading-platform/coinbase/api_key`           | Use read‑only keys when possible.          |
| Coinbase API Secret    | `COINBASE_API_SECRET`          | `secret/data/trading-platform/coinbase/api_secret`        | Store PEM file path in `COINBASE_API_SECRET_FILE` if using key file. |
| Coinbase Passphrase    | `COINBASE_PASSPHRASE`          | `secret/data/trading-platform/coinbase/passphrase`        | Optional depending on auth mode.           |
| Slack Bot Token        | `SLACK_BOT_TOKEN`              | `secret/data/trading-platform/slack/bot_token`            | Bot token for posting messages.            |
| Slack App Token        | `SLACK_APP_TOKEN`              | `secret/data/trading-platform/slack/app_token`            | Required for Socket Mode.                  |
| Slack Signing Secret   | `SLACK_SIGNING_SECRET`         | `secret/data/trading-platform/slack/signing_secret`       | Verifies incoming requests.                |
| Slack Alert Channel    | `SLACK_ALERT_CHANNEL`          | `secret/data/trading-platform/slack/alert_channel`        | Channel ID (e.g. `C12345`).                |
| Teams Webhook URL      | `TEAMS_WEBHOOK_URL`            | `secret/data/trading-platform/teams/webhook_url`          | Optional – Teams incoming webhook.         |
| AWS Secrets Prefix     | `AWS_SECRETS_PREFIX`           | N/A                                                       | Path prefix in AWS Secrets Manager.        |
| Vault Address          | `VAULT_ADDR`                   | N/A                                                       | E.g. `https://vault.yourcompany.com`.      |
| Vault Token            | `VAULT_TOKEN`                  | N/A                                                       | Service token with read access.            |

### Secrets Backends

The platform supports three secret backends selected via `SECRETS_BACKEND`:

1. **env** – Reads secrets directly from environment variables and files specified via `*_FILE`.  This is the default and easiest to use in development but should not be used for production secrets.
2. **aws** – Fetches secrets from AWS Secrets Manager.  Set `AWS_SECRETS_PREFIX` and `AWS_REGION`.  Secrets are flattened so nested JSON can be accessed via dot notation (e.g. `COINBASE_API_KEY` inside a JSON blob).
3. **vault** – Retrieves secrets from HashiCorp Vault using `VAULT_ADDR` and `VAULT_TOKEN`.  Set `VAULT_PREFIX` to the base path for your secrets (e.g. `trading-platform`).  The `VaultSecretsManager` falls back to environment variables if Vault is unavailable.

If `SECRETS_BACKEND` is not specified or fails to initialise, the manager will attempt each backend in order: `env` → `aws` → `vault`.

### Rotation & RBAC

* **Rotation** – Rotate your API keys and tokens regularly.  For Coinbase, generate a new API key with minimal permissions (e.g. trade and view) and update the secret in your backend.  For Slack and Teams, rotate tokens via the provider’s admin interface and update the secret values.  Deployments should be restarted to pick up new credentials.
* **Least Privilege** – Assign the minimal scopes required for the service.  For Slack, use bot tokens rather than user tokens and restrict channels.  For Coinbase, only enable the products you intend to trade.
* **Access Control** – Restrict who can read or update secrets in your secrets manager.  Use Vault policies or AWS IAM roles to enforce least privilege and audit access.

### What Not To Commit

* **Never commit API keys, secrets or PEM files** to the repository.  Use environment variables or secret files mounted at runtime.
* **Avoid committing database dumps or personal data**.  Event logs should be anonymised before sharing.
* **Do not commit build artefacts or credentials** generated during local testing.

### Token Rotation Steps

1. Generate a new token in the provider’s console (Coinbase, Slack, Teams).  Do not delete the old token yet.
2. Update the secret in your secrets manager under the path specified in the matrix above.
3. Restart the affected services (workers, ops bot) to load the new secret.  Monitor logs for authentication errors.
4. Once the new token is confirmed to be working, revoke the old token from the provider.

Following these practices will help ensure that sensitive data is protected and that your trading infrastructure remains secure.