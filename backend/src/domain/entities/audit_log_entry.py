from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.exceptions import DomainError

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class AuditLogEntry:
    """Append-only record of every human-driven action that changes system state.

    Every ManualOverride issue/revoke, CommunityReport moderation decision,
    User/APIKey creation, threshold edit, etc. writes one of these rows. The
    presence of ``actor_username`` + ``action`` + ``target`` (the thing the
    action touched) plus the monotonic ``timestamp`` is what turns a
    "database changed and nobody knows why" mess into an auditable trail.
    """

    id: str
    actor_username: str
    action: str
    target: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if not self.actor_username:
            raise DomainError(
                "AuditLogEntry.actor_username must be non-empty — every action must be attributable"
            )
        if not self.action:
            raise DomainError("AuditLogEntry.action must be non-empty")
        if not self.target:
            raise DomainError(
                "AuditLogEntry.target must be non-empty (e.g. zone_id, report_id, resource_center_id)"
            )
