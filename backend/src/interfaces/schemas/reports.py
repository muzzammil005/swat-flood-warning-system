"""Report-related Pydantic schemas for HTTP responses.

Temporary MVP schemas for demo deadline.
Will be refined and moved to proper DTO layer after demo.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003  (Pydantic V2 needs runtime for from_attributes=True)

from pydantic import BaseModel, ConfigDict, Field


class CommunityReportCreateRequest(BaseModel):
    """Request schema for submitting a community report."""
    report_type: str = Field(..., description="Type of report: flooding, blocked_drain, high_river_level, etc.")
    description: str = Field(..., description="Detailed description of the issue")
    reporter_name: str | None = Field(None, description="Optional reporter name")
    reporter_phone: str | None = Field(None, description="Optional reporter phone number")
    zone_id: str | None = Field(None, description="Zone ID (if known)")
    latitude: float | None = Field(None, description="Latitude coordinate (if zone_id not provided)")
    longitude: float | None = Field(None, description="Longitude coordinate (if zone_id not provided)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_type": "flooding",
                "description": "Water level rising rapidly near bridge",
                "reporter_name": "John Doe",
                "reporter_phone": "+1234567890",
                "latitude": 35.1234,
                "longitude": 72.5678
            }
        }
    )


class CommunityReportUpdateRequest(BaseModel):
    """Request schema for updating a report status."""
    status: str = Field(..., description="New status: Approved or Rejected")
    admin_notes: str | None = Field(None, description="Optional admin notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "Approved",
                "admin_notes": "Verified with local authorities"
            }
        }
    )


class CommunityReportResponse(BaseModel):
    """Response schema for a community report."""
    id: str
    zone_id: str
    report_type: str
    description: str
    reporter_name: str | None = None
    reporter_phone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    submitted_at: datetime
    status: str
    admin_notes: str | None = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_entity(cls, report) -> CommunityReportResponse:
        """Create response from domain entity."""
        
        # For demo, extract report_type and description from observation
        # Format is: "[report_type] description"
        observation = report.observation
        report_type = "general"
        description = observation
        
        if observation.startswith("[") and "]" in observation:
            end_bracket = observation.find("]")
            report_type = observation[1:end_bracket]
            description = observation[end_bracket + 1:].strip()
        
        return cls(
            id=report.id,
            zone_id=report.zone_id,
            report_type=report_type,
            description=description,
            reporter_name=None,  # Entity doesn't have these fields
            reporter_phone=None,
            latitude=None,
            longitude=None,
            submitted_at=report.submitted_at,
            status=report.status,
            admin_notes=None,
        )


class CommunityReportListResponse(BaseModel):
    """Response schema for list of community reports."""
    reports: list[CommunityReportResponse]
    reports_by_zone: dict[str, list[CommunityReportResponse]] | None = None
    
    model_config = ConfigDict(from_attributes=True)
