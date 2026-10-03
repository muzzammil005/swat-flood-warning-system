from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from domain.exceptions import DomainError

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class CommunityReport:
    """A civilian-submitted ground-truth report (flood waters, blocked roads, etc.).

    Reports start ``Pending`` and are triaged by a responder into ``Approved``
    (surfaced on the dashboard and used as a soft signal to the risk engine)
    or ``Rejected`` (dropped with an audit log entry).
    """

    id: str
    zone_id: str
    observation: str
    status: Literal["Pending", "Approved", "Rejected"]
    submitted_at: datetime

    def __post_init__(self) -> None:
        if self.status not in {"Pending", "Approved", "Rejected"}:
            raise DomainError(
                "CommunityReport.status must be 'Pending', 'Approved', or 'Rejected', "
                f"got {self.status!r}"
            )
        if not self.observation:
            raise DomainError("CommunityReport.observation must be non-empty")
