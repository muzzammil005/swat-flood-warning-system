"""Outbound notification port.

Implementations live in :mod:`infrastructure.notifications` (FCM stub in
Prompt 8; real Firebase-admin swap-in later). Stage 3 will wire the
:class:`EscalationEngine`'s DANGER-tier output through this port so field
responders and subscribed civilians get a push alert.

The port only carries a domain :class:`Alert` (CAP-inspired) plus a recipient
list — any FCM-specific formatting (topic names, APNs headers, etc.) is the
adapter's job, never the caller's.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.entities.alert import Alert


class NotificationPort(ABC):
    """Broadcast a domain Alert to a list of recipient identifiers."""

    @abstractmethod
    async def send_alert(
        self, alert: Alert, /, *, recipients: list[str]
    ) -> None:
        """Send the alert. Implementations *must not* raise on transient
        delivery failure — log-and-continue so a single dead FCM token
        doesn't abort the whole risk cycle.
        """
        ...
