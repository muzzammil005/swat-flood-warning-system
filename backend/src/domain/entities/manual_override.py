from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.exceptions import DomainError

if TYPE_CHECKING:
    from datetime import datetime

    from domain.value_objects import RiskTier


@dataclass
class ManualOverride:
    """A signed-off admin/responder action that forces a zone's risk tier.

    Manual overrides always win over :class:`RiskEngine` output for as long as
    they're active (the application layer handles expiry / revocation). The
    ``admin_username`` + ``timestamp`` pair feeds directly into
    :class:`AuditLogEntry` for accountability.
    """

    id: str
    zone_id: str
    threat_level: RiskTier
    reason: str
    admin_username: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if not self.reason:
            raise DomainError("ManualOverride.reason must be non-empty — auditable trail required")
        if not self.admin_username:
            raise DomainError("ManualOverride.admin_username must be non-empty")
