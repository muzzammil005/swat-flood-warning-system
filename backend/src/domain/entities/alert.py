from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.exceptions import DomainError

if TYPE_CHECKING:
    from datetime import datetime

    from domain.value_objects import RiskTier


@dataclass
class Alert:
    """A CAP (Common Alerting Protocol) inspired public-facing alert.

    Not every ``RiskAssessment`` produces an ``Alert`` — the application layer
    decides which tiers warrant a broadcast (typically HIGH+), deduplicates
    against the active-alert set, and only then constructs one of these. The
    fields mirror CAP's core severity/certainty/urgency triplet so we can one
    day emit real CAP XML for national disaster-management integrations
    without a schema rewrite.
    """

    zone_id: str
    severity: RiskTier
    certainty: str
    urgency: str
    headline: str
    description: str
    sent_at: datetime

    def __post_init__(self) -> None:
        if not self.headline:
            raise DomainError("Alert.headline must be non-empty")
        if not self.description:
            raise DomainError("Alert.description must be non-empty")
        if self.certainty not in {"Observed", "Likely", "Possible", "Unlikely"}:
            raise DomainError(
                f"Alert.certainty must be a CAP-standard value, got {self.certainty!r}"
            )
        if self.urgency not in {"Immediate", "Expected", "Future", "Past"}:
            raise DomainError(
                f"Alert.urgency must be a CAP-standard value, got {self.urgency!r}"
            )
