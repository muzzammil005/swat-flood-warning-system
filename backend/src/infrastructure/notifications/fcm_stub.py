"""FCM (Firebase Cloud Messaging) stub adapter for the NotificationPort.

This is a **stub** implementation that logs the alert instead of sending real
push notifications. A real implementation would use the firebase‑admin SDK
to deliver alerts to iOS/Android devices via FCM topics or device tokens.

The stub honours the port's contract: it never raises on "delivery" failure
(which in this case means a logging failure) — the risk‑assessment cycle must
continue even if notifications are temporarily unavailable.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from application.ports.notifications import NotificationPort

if TYPE_CHECKING:
    from domain.entities.alert import Alert

logger = logging.getLogger(__name__)


class FCMStubNotifier(NotificationPort):
    """Stub notifier that logs alerts instead of sending real pushes."""

    async def send_alert(
        self, alert: Alert, /, *, recipients: list[str]
    ) -> None:
        """Log the alert to the application log (stdout/stderr in dev).

        In a production deployment, this would be replaced with a real
        firebase‑admin‑sdk call that formats the alert as a FCM data
        payload and broadcasts it to the recipient list.
        """
        if not recipients:
            logger.info(
                "FCMStubNotifier: Alert for zone %r (severity=%s) has no recipients, skipping",
                alert.zone_id,
                alert.severity,
            )
            return

        # severity is a RiskTier IntEnum (LOW=1..DANGER=4). Use .name to get
        # the canonical uppercase string for display, then compare enum values
        # directly against RiskTier to avoid string/enum type mismatches.
        from domain.value_objects.risk_tier import RiskTier

        severity_str: str = alert.severity.name if isinstance(alert.severity, RiskTier) else str(alert.severity)

        # Format a human‑readable summary of the alert
        summary = (
            f"Zone {alert.zone_id} — {severity_str} ALERT\n"
            f"Headline: {alert.headline}\n"
            f"Description: {alert.description}\n"
            f"Certainty: {alert.certainty}, Urgency: {alert.urgency}\n"
            f"Sent at: {alert.sent_at.isoformat()}"
        )

        # Log at appropriate severity level — direct enum comparison (not string)
        is_high_severity = (
            isinstance(alert.severity, RiskTier)
            and alert.severity >= RiskTier.HIGH
        )
        if is_high_severity:
            logger.warning(
                "FCMStubNotifier would send HIGH‑severity alert to %d recipient(s):\n%s",
                len(recipients),
                summary,
            )
        else:
            logger.info(
                "FCMStubNotifier would send alert to %d recipient(s):\n%s",
                len(recipients),
                summary,
            )

        # In a real FCM adapter, we would now:
        # 1. Convert the domain Alert to FCM DataMessage format
        # 2. Determine whether to send via topic (/topics/zone_<id>) or
        #    individual device tokens
        # 3. Call firebase_admin.messaging.send_each() with error handling
        # 4. Log delivery outcomes (success/failure counts)
        #
        # The stub intentionally does none of that, keeping the system
        # deployable without Firebase credentials.


# Export only the concrete implementation
__all__ = ["FCMStubNotifier"]