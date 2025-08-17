"""
Alert Service
=============

This service subscribes to PnL update events on the internal event bus
and sends notifications when certain conditions are met.  The primary
use cases are to notify operators via Slack or Microsoft Teams when the
risk kill switch is engaged or when the daily PnL drops below a
configurable negative threshold.  The service can be extended to
support additional alert conditions (e.g. exposure spikes,
connectivity issues) or additional notification channels.

Configuration
-------------

Alerts are controlled via environment variables or entries in your
secrets manager (see ``workers/src/workers/secrets_manager.py``).  The
following keys are recognised:

``ALERT_ENABLE``
    Set to ``true``/``1``/``yes`` to enable alerting.  If not set,
    the service will consume events but will not send notifications.

``ALERT_PNL_THRESHOLD``
    A positive float specifying the absolute value of daily PnL at
    which to trigger an alert.  For example, ``1000`` will send an
    alert when the daily PnL is –1000 or lower.  A value of ``0``
    disables PnL threshold alerts and only kill‑switch alerts are sent.

``SLACK_BOT_TOKEN`` / ``SLACK_CHANNEL_ID``
    Credentials for Slack notifications.  If both are provided,
    Slack alerts are enabled.  These may be stored in a secrets
    manager; see below.

``TEAMS_WEBHOOK_URL``
    Incoming webhook URL for Microsoft Teams.  If provided, alerts
    will also be sent to Teams using a simple JSON payload.  Teams
    notifications are optional and can be used alongside or instead of
    Slack.

Secrets Management
------------------

The alert service loads its configuration via the default secrets
manager (``get_default_secrets_manager``).  This means that values
may be retrieved from environment variables, ``*_FILE`` paths,
AWS Secrets Manager, or HashiCorp Vault depending on the
``SECRETS_BACKEND`` setting.  If a value is not found in the secret
manager, the service will fall back to ``os.getenv`` for backward
compatibility.

If the Slack SDK or the ``requests`` library (for Teams) are not
available, the service logs alerts to the console.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

try:
    # Optional dependency for Teams webhooks
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore

try:
    from slack_sdk import WebClient  # type: ignore
except ImportError:
    WebClient = None  # type: ignore

try:
    # base class for secrets manager typing; imported lazily to avoid circular
    from ..secrets_manager import BaseSecretsManager  # type: ignore
except Exception:
    BaseSecretsManager = None  # type: ignore

logger = logging.getLogger(__name__)


class AlertService:
    """Subscribe to PnL updates and send Slack alerts on anomalies."""

    def __init__(self, event_bus: Any) -> None:
        self.event_bus = event_bus
        # Load configuration via the default secrets manager.  Fallback
        # to os.getenv for backward compatibility.  This allows
        # operators to store tokens and channel IDs in files or
        # external secret stores without modifying code.
        self._secrets = None  # type: Optional[BaseSecretsManager]
        try:
            from ..secrets_manager import get_default_secrets_manager  # type: ignore

            self._secrets = get_default_secrets_manager()
        except Exception:
            self._secrets = None

        def get_secret(name: str) -> Optional[str]:
            if self._secrets:
                try:
                    val = self._secrets.get_secret(name)
                    if val:
                        return val
                except Exception:
                    pass
            return os.getenv(name)

        # Alert configuration
        self.enabled = str(get_secret("ALERT_ENABLE") or "false").lower() in {
            "true",
            "1",
            "yes",
        }
        try:
            self.pnl_threshold = float(get_secret("ALERT_PNL_THRESHOLD") or "0")
        except Exception:
            self.pnl_threshold = 0.0
        self.slack_token = get_secret("SLACK_BOT_TOKEN")
        # Support alternative channel key: SLACK_ALERT_CHANNEL as override
        self.slack_channel = get_secret("SLACK_ALERT_CHANNEL") or get_secret("SLACK_CHANNEL_ID")
        self.teams_webhook = get_secret("TEAMS_WEBHOOK_URL")
        self.client = None
        if self.enabled and self.slack_token and WebClient:
            try:
                self.client = WebClient(token=self.slack_token)
            except Exception as exc:
                logger.error("Failed to initialize Slack client: %s", exc)
                self.client = None
        if self.enabled and self.slack_token and not WebClient:
            logger.warning("slack_sdk not available; Slack alerts will be logged")
        if self.enabled and not self.slack_token and not self.teams_webhook:
            logger.warning(
                "Alerts enabled but no Slack or Teams credentials provided; falling back to console logging"
            )

    async def _send_slack_message(self, text: str) -> None:
        """Send a message to Slack if configured; otherwise log."""
        if not self.slack_channel:
            # No channel configured; treat as no-op
            logger.warning("ALERT: %s", text)
            return
        if self.client:
            try:
                await asyncio.to_thread(
                    self.client.chat_postMessage, channel=self.slack_channel, text=text
                )
                logger.info("Sent Slack alert: %s", text)
                return
            except Exception as exc:
                logger.error("Failed to send Slack alert: %s", exc)
        # Slack client unavailable; log message
        logger.warning("ALERT: %s", text)

    async def _send_teams_message(self, text: str) -> None:
        """Send a message to Microsoft Teams via incoming webhook."""
        if not self.teams_webhook:
            return
        if requests is None:
            logger.warning("Requests library not available; cannot send Teams alert: %s", text)
            logger.warning("ALERT: %s", text)
            return
        payload = {"text": text}

        # Send in a thread to avoid blocking the event loop
        def post():  # pragma: no cover
            try:
                resp = requests.post(self.teams_webhook, json=payload, timeout=5)
                if resp.status_code >= 400:
                    logger.error(
                        "Failed to send Teams alert (status %s): %s",
                        resp.status_code,
                        resp.text,
                    )
            except Exception as exc:
                logger.error("Error sending Teams alert: %s", exc)

        await asyncio.to_thread(post)

    async def run(self) -> None:
        """Main loop: listen for PnL updates and send alerts when needed.

        The service will monitor the ``pnl_update`` channel on the event bus.
        When the kill switch flag is true it immediately sends an alert.
        If the daily PnL drops below the negative threshold, it sends a PnL
        alert.  Notifications are dispatched to Slack and/or Teams depending
        on which channels are configured.  If neither channel is configured
        or the alert service is disabled, events are logged for observability.
        """
        if self.event_bus is None:
            logger.error("AlertService requires an event bus")
            return
        logger.info(
            "AlertService started; enabled=%s, pnl_threshold=%s, slack_channel=%s, teams=%s",
            self.enabled,
            self.pnl_threshold,
            self.slack_channel,
            bool(self.teams_webhook),
        )
        async for message in self.event_bus.subscribe("pnl_update"):
            # Ensure we have a mapping; skip invalid messages
            if not isinstance(message, Dict):
                continue
            daily_pnl = message.get("daily_pnl")
            kill_switch = message.get("kill_switch")
            # If alerts disabled, just log and continue
            if not self.enabled:
                logger.info("PnL update: kill_switch=%s, daily_pnl=%s", kill_switch, daily_pnl)
                continue
            alert_text: Optional[str] = None
            if kill_switch:
                alert_text = f"⚠️ Kill switch engaged! Daily PnL: {daily_pnl:.2f}"
            elif (
                daily_pnl is not None and self.pnl_threshold and (-daily_pnl) >= self.pnl_threshold
            ):
                alert_text = (
                    f"🔻 PnL alert: Daily PnL = {daily_pnl:.2f} (threshold {self.pnl_threshold})"
                )
            if alert_text:
                # Send to Slack
                await self._send_slack_message(alert_text)
                # Send to Teams
                await self._send_teams_message(alert_text)
