from domain.exceptions.base import DomainError

class NotFoundError(DomainError):
    """Base class for all not-found errors."""
    pass

class ZoneNotFoundError(NotFoundError):
    """Raised when a Zone is not found."""
    def __init__(self, zone_id: str) -> None:
        super().__init__(f"Zone with ID '{zone_id}' not found.")
        self.zone_id = zone_id

class ReportNotFoundError(NotFoundError):
    """Raised when a CommunityReport is not found."""
    def __init__(self, report_id: str) -> None:
        super().__init__(f"Report with ID '{report_id}' not found.")
        self.report_id = report_id

class AlertNotFoundError(NotFoundError):
    """Raised when an Alert is not found."""
    def __init__(self, alert_id: str) -> None:
        super().__init__(f"Alert with ID '{alert_id}' not found.")
        self.alert_id = alert_id
