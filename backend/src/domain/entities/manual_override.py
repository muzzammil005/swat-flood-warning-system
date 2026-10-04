from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.exceptions import DomainError
from domain.value_objects.risk_tier import RiskTier

if TYPE_CHECKING:
    from datetime import datetime


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
        if not isinstance(self.threat_level, RiskTier):
            if hasattr(self.threat_level, "name"):
                name = str(self.threat_level.name).upper()
            elif hasattr(self.threat_level, "value"):
                name = str(self.threat_level.value).upper()
            else:
                name = str(self.threat_level).upper()

            if name in RiskTier.__members__:
                self.threat_level = RiskTier[name]
            elif name in ("1", "2", "3", "4"):
                self.threat_level = RiskTier(int(name))
            else:
                self.threat_level = RiskTier.HIGH

        if not self.reason:
            raise DomainError("ManualOverride.reason must be non-empty — auditable trail required")
        if not self.admin_username:
            raise DomainError("ManualOverride.admin_username must be non-empty")
