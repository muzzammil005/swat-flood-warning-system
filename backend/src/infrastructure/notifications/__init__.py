"""Notifications infrastructure adapters.

Exports the FCM stub concrete implementation from Prompt 8.
"""

from infrastructure.notifications.fcm_stub import FCMStubNotifier

__all__ = ["FCMStubNotifier"]