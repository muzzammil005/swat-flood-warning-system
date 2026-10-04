"""Alert-related Pydantic schemas for HTTP responses.

Temporary MVP schemas for demo deadline.
Will be refined and moved to proper DTO layer after demo.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003  (Pydantic V2 needs runtime for from_attributes=True)
from typing import TYPE_CHECKING  # noqa: F401  (may be needed for future field types)

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from domain.value_objects.risk_tier import (
    RiskTier,  # noqa: TC001  (Pydantic V2 needs runtime for from_attributes=True)
)


class AlertListResponse(BaseModel):
    """Alert list item response schema."""
    id: str | None = None
    zone_id: str
    severity: RiskTier
    certainty: str
    urgency: str
    headline: str
    description: str
    sent_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('severity', mode='before')
    @classmethod
    def validate_severity(cls, value: object) -> RiskTier:
        if isinstance(value, RiskTier):
            return value
        if hasattr(value, 'name'):
            val = str(value.name).upper()
        elif hasattr(value, 'value'):
            val = str(value.value).upper()
        else:
            val = str(value).upper()
        if val in RiskTier.__members__:
            return RiskTier[val]
        return RiskTier.HIGH

    @field_serializer('severity')
    def serialize_severity(self, value: RiskTier | str | object) -> str:
        """Serialize RiskTier enum to its name string (LOW, MEDIUM, HIGH)."""
        if hasattr(value, 'name'):
            return value.name
        if hasattr(value, 'value'):
            return str(value.value)
        return str(value)
    
    @classmethod
    def from_entity(cls, alert) -> AlertListResponse:
        """Create response from domain entity."""
        return cls(
            id=f"{alert.zone_id}_{int(alert.sent_at.timestamp())}",
            zone_id=alert.zone_id,
            severity=alert.severity,
            certainty=alert.certainty,
            urgency=alert.urgency,
            headline=alert.headline,
            description=alert.description,
            sent_at=alert.sent_at,
        )