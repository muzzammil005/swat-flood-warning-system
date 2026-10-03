from application.ports.repositories import AlertRepository
from domain.entities.alert import Alert


class AlertUseCases:
    """Use cases for querying and managing alerts."""

    def __init__(self, alert_repo: AlertRepository):
        self.alert_repo = alert_repo

    async def list_active_alerts(self, limit: int = 20) -> list[Alert]:
        """Fetch the most recent active alerts."""
        alerts = await self.alert_repo.list_active(limit=limit)
        return alerts
