from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from application.ports.repositories import (
    ManualOverrideRepository,
    RiskAssessmentRepository,
    SensorReadingRepository,
    WeatherSnapshotRepository,
    ZoneRepository,
    ZoneThresholdsRepository,
)
from domain.entities.manual_override import ManualOverride
from domain.entities.risk_assessment import RiskAssessment
from domain.entities.sensor_reading import SensorReading
from domain.entities.weather_snapshot import WeatherSnapshot
from domain.entities.zone import Zone
from domain.exceptions import ZoneNotFoundError
from domain.value_objects.zone_thresholds import ZoneThresholds


@dataclass(frozen=True)
class ZoneSummary:
    """DTO representing the aggregated risk summary across all zones."""
    danger: int
    high: int
    medium: int
    low: int
    safe: int
    total_zones: int


@dataclass(frozen=True)
class ZoneDetail:
    """DTO representing a zone with all its related current state."""
    zone: Zone
    latest_assessment: RiskAssessment | None
    thresholds: ZoneThresholds | None
    sensor_health: str
    active_override: ManualOverride | None


@dataclass(frozen=True)
class ZoneFullDetail:
    """DTO representing a zone with its full detail and history."""
    zone: Zone
    latest_assessment: RiskAssessment | None
    thresholds: ZoneThresholds | None
    sensor_health: str
    active_override: ManualOverride | None
    recent_readings: list[SensorReading]
    risk_history: list[RiskAssessment]
    recent_rainfall: WeatherSnapshot | None


class ZoneUseCases:
    """Use cases for querying zones and their current state."""

    def __init__(
        self,
        zone_repo: ZoneRepository,
        risk_repo: RiskAssessmentRepository,
        thresholds_repo: ZoneThresholdsRepository,
        sensor_repo: SensorReadingRepository,
        override_repo: ManualOverrideRepository,
        weather_repo: WeatherSnapshotRepository = None,
    ):
        self.zone_repo = zone_repo
        self.risk_repo = risk_repo
        self.thresholds_repo = thresholds_repo
        self.sensor_repo = sensor_repo
        self.override_repo = override_repo
        self.weather_repo = weather_repo

    async def get_zone_summary(self) -> ZoneSummary:
        """Calculate the risk tier distribution across all zones."""
        zones = await self.zone_repo.list_all()
        counts = {"DANGER": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "SAFE": 0}

        for zone in zones:
            override = await self.override_repo.active_for_zone(zone.id)
            latest_assessment = await self.risk_repo.latest_for_zone(zone.id)
            
            if override:
                tier_name = override.threat_level.name
                if tier_name in counts:
                    counts[tier_name] += 1
                else:
                    counts["SAFE"] += 1
            elif latest_assessment:
                tier_name = latest_assessment.tier.name
                if tier_name in counts:
                    counts[tier_name] += 1
                else:
                    counts["SAFE"] += 1
            else:
                counts["SAFE"] += 1
        
        return ZoneSummary(
            danger=counts["DANGER"],
            high=counts["HIGH"],
            medium=counts["MEDIUM"],
            low=counts["LOW"],
            safe=counts["SAFE"],
            total_zones=len(zones),
        )

    async def get_all_zones(self) -> list[ZoneDetail]:
        """Fetch all zones with their latest state and health."""
        zones = await self.zone_repo.list_all()
        result = []
        for zone in zones:
            detail = await self._build_zone_detail(zone)
            result.append(detail)
        return result

    async def get_zone_by_id(self, zone_id: str) -> ZoneFullDetail:
        """Fetch a single zone with its full state and history."""
        zone = await self.zone_repo.get_by_id(zone_id)
        if not zone:
            raise ZoneNotFoundError(zone_id)
        
        detail = await self._build_zone_detail(zone)
        
        recent_readings = await self.sensor_repo.list_for_zone(zone_id, limit=5)
        risk_history = await self.risk_repo.history_for_zone(zone_id, limit=5)
        recent_rainfall = await self.weather_repo.latest_for_zone(zone_id) if self.weather_repo else None
        
        return ZoneFullDetail(
            zone=detail.zone,
            latest_assessment=detail.latest_assessment,
            thresholds=detail.thresholds,
            sensor_health=detail.sensor_health,
            active_override=detail.active_override,
            recent_readings=recent_readings,
            risk_history=risk_history,
            recent_rainfall=recent_rainfall,
        )

    async def _build_zone_detail(self, zone: Zone) -> ZoneDetail:
        """Helper to assemble a zone's current state."""
        latest_assessment = await self.risk_repo.latest_for_zone(zone.id)
        override = await self.override_repo.active_for_zone(zone.id)
        thresholds = await self.thresholds_repo.get_by_zone_id(zone.id)
        latest_readings = await self.sensor_repo.list_for_zone(zone.id, limit=1)
        
        sensor_health = "online"
        if latest_readings:
            reading_time = latest_readings[0].timestamp
            three_hours_ago = datetime.now(UTC) - timedelta(hours=3)
            if reading_time < three_hours_ago:
                sensor_health = "offline"
        else:
            sensor_health = "offline"
            
        return ZoneDetail(
            zone=zone,
            latest_assessment=latest_assessment,
            thresholds=thresholds,
            sensor_health=sensor_health,
            active_override=override,
        )
