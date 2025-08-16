## Vault Secrets Paths

This document lists the expected key paths in HashiCorp Vault when using the `vault` secrets backend.  Secrets are stored under a common prefix configured via the `VAULT_PREFIX` environment variable.  The default prefix is `trading-platform`.

| Secret Name           | Environment Variable        | Vault Path Example                                               |
|-----------------------|-----------------------------|------------------------------------------------------------------|
| Coinbase API Key      | `COINBASE_API_KEY`          | `secret/data/trading-platform/coinbase/api_key`                  |
| Coinbase API Secret   | `COINBASE_API_SECRET`       | `secret/data/trading-platform/coinbase/api_secret`               |
| Coinbase Passphrase   | `COINBASE_PASSPHRASE`       | `secret/data/trading-platform/coinbase/passphrase`               |
| Slack Bot Token       | `SLACK_BOT_TOKEN`           | `secret/data/trading-platform/slack/bot_token`                   |
| Slack App Token       | `SLACK_APP_TOKEN`           | `secret/data/trading-platform/slack/app_token`                   |
| Slack Signing Secret  | `SLACK_SIGNING_SECRET`      | `secret/data/trading-platform/slack/signing_secret`              |
| Slack Alert Channel   | `SLACK_ALERT_CHANNEL`       | `secret/data/trading-platform/slack/alert_channel`               |
| Teams Webhook URL     | `TEAMS_WEBHOOK_URL`         | `secret/data/trading-platform/teams/webhook_url`                 |

When retrieving a secret, the secrets manager constructs the full path as:

```
{VAULT_PREFIX}/{name}
```

for example, if `VAULT_PREFIX=trading-platform` and you request `COINBASE_API_KEY`, the manager attempts to read from `secret/data/trading-platform/coinbase/api_key`.  The manager falls back to environment variables if the secret is not found.