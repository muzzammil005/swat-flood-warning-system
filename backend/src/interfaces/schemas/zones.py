"""Zone-related Pydantic schemas for HTTP responses.

Temporary MVP schemas for demo deadline.
Will be refined and moved to proper DTO layer after demo.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003  (Pydantic V2 needs runtime for from_attributes=True)
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from domain.value_objects.risk_tier import (
    RiskTier,  # noqa: TC001  (Pydantic V2 needs runtime for from_attributes=True)
)

if TYPE_CHECKING:
    from domain.value_objects.coordinates import Coordinates
    from domain.value_objects.rainfall_window import RainfallWindow
    from domain.value_objects.water_level import WaterLevel
    from domain.value_objects.zone_thresholds import ZoneThresholds


# Base schemas
class CoordinatesSchema(BaseModel):
    """Coordinates schema for HTTP response."""
    latitude: float
    longitude: float
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_vo(cls, coordinates: Coordinates) -> CoordinatesSchema:
        return cls(latitude=coordinates.latitude, longitude=coordinates.longitude)


class WaterLevelSchema(BaseModel):
    """Water level schema for HTTP response."""
    metres: float
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_vo(cls, water_level: WaterLevel) -> WaterLevelSchema:
        # Convert centimetres to metres
        return cls(metres=water_level.centimetres / 100.0)


class ZoneThresholdsSchema(BaseModel):
    """Zone thresholds schema for HTTP response."""
    water_warning_level: WaterLevelSchema
    water_critical_level: WaterLevelSchema
    heavy_rain_threshold_mm: float
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_vo(cls, thresholds: ZoneThresholds) -> ZoneThresholdsSchema:
        return cls(
            water_warning_level=WaterLevelSchema.from_vo(thresholds.water_warning_level),
            water_critical_level=WaterLevelSchema.from_vo(thresholds.water_critical_level),
            heavy_rain_threshold_mm=thresholds.heavy_rain_threshold_mm,
        )


class RiskAssessmentSchema(BaseModel):
    """API schema for a zone risk assessment."""

    tier: str = Field(..., description="The risk tier (SAFE, LOW, MEDIUM, HIGH, DANGER).")
    probability: float = Field(
        ..., description="Confidence score [0, 1] of the assessment."
    )
    explanation: str = Field(..., description="Human-readable explanation of the risk.")
    computed_at: datetime = Field(..., description="When this assessment was generated.")
    combined_rain_mm: float | None = Field(default=None, description="Combined 10-day rainfall (past 7d + forecast 72h).")
    expected_rain_mm: float | None = Field(default=None, description="Expected 10-day baseline rainfall.")
    rainfall_anomaly_ratio: float | None = Field(default=None, description="Ratio of actual vs expected rainfall.")
    top_contributing_features: list[str] | None = Field(default=None, description="Top SHAP contributing features from the ML model.")

    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('tier')
    def serialize_tier(self, value: RiskTier | str) -> str:
        """Serialize RiskTier enum to its name string (e.g., DANGER, HIGH, MEDIUM, LOW)."""
        return value.name if hasattr(value, 'name') else str(value)


class SensorReadingSchema(BaseModel):
    """Sensor reading schema for HTTP response."""
    id: str
    zone_id: str
    water_level: WaterLevelSchema
    source: str
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RainfallWindowSchema(BaseModel):
    """Rainfall window schema for HTTP response."""
    millimetres: float
    duration_hours: float
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_vo(cls, rainfall_window: RainfallWindow) -> RainfallWindowSchema:
        return cls(
            millimetres=rainfall_window.millimetres,
            duration_hours=rainfall_window.duration_hours,
        )


class WeatherSnapshotSchema(BaseModel):
    """Weather snapshot schema for HTTP response."""
    zone_id: str
    rainfall: RainfallWindowSchema
    fetched_at: datetime
    ttl_seconds: int
    
    model_config = ConfigDict(from_attributes=True)


# Response schemas
class ZoneSummaryResponse(BaseModel):
    """Zone summary counts by risk tier."""
    danger: int
    high: int
    medium: int
    low: int
    safe: int
    total_zones: int


class ZoneListResponse(BaseModel):
    """Zone list item response schema."""
    id: str
    name: str
    coordinates: CoordinatesSchema
    upstream_zone_id: str | None = None
    latest_assessment: RiskAssessmentSchema | None = None
    thresholds: ZoneThresholdsSchema | None = None
    sensor_health: str | None = None  # "online" or "offline"
    is_manual_override: bool = False
    
    @classmethod
    def from_entities(
        cls,
        zone,
        latest_assessment,
        thresholds,
        sensor_health: str | None = None,
        is_manual_override: bool = False,
    ) -> ZoneListResponse:
        """Create response from domain entities."""
        
        return cls(
            id=zone.id,
            name=zone.name,
            coordinates=CoordinatesSchema.from_vo(zone.coordinates),
            upstream_zone_id=zone.upstream_zone_id,
            latest_assessment=(
                RiskAssessmentSchema(
                    id=None,
                    zone_id=latest_assessment.zone_id,
                    tier=latest_assessment.tier.name if hasattr(latest_assessment.tier, 'name') else str(latest_assessment.tier),
                    probability=latest_assessment.probability,
                    explanation=latest_assessment.explanation,
                    computed_at=latest_assessment.computed_at,
                )
                if latest_assessment else None
            ),
            thresholds=(
                ZoneThresholdsSchema.from_vo(thresholds)
                if thresholds else None
            ),
            sensor_health=sensor_health,
            is_manual_override=is_manual_override,
        )


class ZoneDetailResponse(BaseModel):
    """Zone detail response schema."""
    zone: ZoneListResponse
    recent_readings: list[SensorReadingSchema]
    risk_history: list[RiskAssessmentSchema]
    recent_rainfall: WeatherSnapshotSchema | None = None
    latest_sensor_reading: SensorReadingSchema | None = None
    is_manual_override: bool = False
    
    @classmethod
    def from_entities(
        cls,
        zone,
        latest_assessment,
        recent_readings,
        risk_history,
        thresholds,
        recent_rainfall=None,
        latest_sensor_reading=None,
        is_manual_override: bool = False,
    ) -> ZoneDetailResponse:
        """Create response from domain entities."""
        zone_response = ZoneListResponse.from_entities(
            zone=zone,
            latest_assessment=latest_assessment,
            is_manual_override=is_manual_override,
            thresholds=thresholds,
        )
        
        return cls(
            zone=zone_response,
            recent_readings=[
                SensorReadingSchema(
                    id=reading.id,
                    zone_id=reading.zone_id,
                    water_level=WaterLevelSchema.from_vo(reading.water_level),
                    source=reading.source,
                    timestamp=reading.timestamp,
                )
                for reading in recent_readings
            ],
            risk_history=[
                RiskAssessmentSchema(
                    id=None,  # RiskAssessment domain entity doesn't have id
                    zone_id=assessment.zone_id,
                    tier=assessment.tier.name if hasattr(assessment.tier, 'name') else str(assessment.tier),
                    probability=assessment.probability,
                    explanation=assessment.explanation,
                    computed_at=assessment.computed_at,
                )
                for assessment in risk_history
            ],
            recent_rainfall=(
                WeatherSnapshotSchema(
                    zone_id=recent_rainfall.zone_id,
                    rainfall=RainfallWindowSchema.from_vo(recent_rainfall.rainfall),
                    fetched_at=recent_rainfall.fetched_at,
                    ttl_seconds=recent_rainfall.ttl_seconds,
                )
                if recent_rainfall else None
            ),
            latest_sensor_reading=(
                SensorReadingSchema(
                    id=latest_sensor_reading.id,
                    zone_id=latest_sensor_reading.zone_id,
                    water_level=WaterLevelSchema.from_vo(latest_sensor_reading.water_level),
                    source=latest_sensor_reading.source,
                    timestamp=latest_sensor_reading.timestamp,
                )
                if latest_sensor_reading else None
            ),
            is_manual_override=is_manual_override,
        )