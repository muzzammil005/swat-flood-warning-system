"""Zones router for MVP demo.

Temporary implementation calling repositories directly for demo deadline.
Will be refactored into proper use-cases layer after demo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException

from infrastructure.db.session import get_session
from interfaces.schemas.zones import ZoneDetailResponse, ZoneListResponse, ZoneSummaryResponse

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("/summary", response_model=ZoneSummaryResponse)
async def get_zone_summary() -> ZoneSummaryResponse:
    """Get a high-level summary of all zones and their current risk tiers."""
    async with get_session() as session:
        from infrastructure.db.repositories import (
            ManualOverrideRepositoryImpl,
            RiskAssessmentRepositoryImpl,
            SensorReadingRepositoryImpl,
            ZoneRepositoryImpl,
            ZoneThresholdsRepositoryImpl,
        )
        from application.use_cases.zones import ZoneUseCases

        use_cases = ZoneUseCases(
            zone_repo=ZoneRepositoryImpl(session),
            risk_repo=RiskAssessmentRepositoryImpl(session),
            thresholds_repo=ZoneThresholdsRepositoryImpl(session),
            sensor_repo=SensorReadingRepositoryImpl(session),
            override_repo=ManualOverrideRepositoryImpl(session),
        )

        summary = await use_cases.get_zone_summary()
        return ZoneSummaryResponse(
            danger=summary.danger,
            high=summary.high,
            medium=summary.medium,
            low=summary.low,
            safe=summary.safe,
            total_zones=summary.total_zones,
        )


@router.get("", response_model=list[ZoneListResponse])
@router.get("/", response_model=list[ZoneListResponse])
async def get_zones() -> list[ZoneListResponse]:
    """Get all zones with their most recent risk assessment, thresholds, and sensor health.
    Zones with active manual overrides will show the override's threat_level instead of computed tier.
    """
    async with get_session() as session:
        from infrastructure.db.repositories import (
            ManualOverrideRepositoryImpl,
            RiskAssessmentRepositoryImpl,
            SensorReadingRepositoryImpl,
            ZoneRepositoryImpl,
            ZoneThresholdsRepositoryImpl,
        )
        from application.use_cases.zones import ZoneUseCases
        
        use_cases = ZoneUseCases(
            zone_repo=ZoneRepositoryImpl(session),
            risk_repo=RiskAssessmentRepositoryImpl(session),
            thresholds_repo=ZoneThresholdsRepositoryImpl(session),
            sensor_repo=SensorReadingRepositoryImpl(session),
            override_repo=ManualOverrideRepositoryImpl(session),
        )
        
        zone_details = await use_cases.get_all_zones()
        
        response = []
        for detail in zone_details:
            zone_response = ZoneListResponse.from_entities(
                zone=detail.zone,
                latest_assessment=detail.latest_assessment,
                thresholds=detail.thresholds,
                sensor_health=detail.sensor_health,
                is_manual_override=detail.active_override is not None,
            )
            if detail.active_override and zone_response.latest_assessment:
                zone_response.latest_assessment.tier = detail.active_override.threat_level.name
            response.append(zone_response)
            
        return response


@router.get("/nearest")
async def get_nearest_zone(
    lat: float,
    lon: float,
) -> dict:
    """Find the nearest zone to given coordinates using PostGIS.
    
    Used for mobile geolocation.
    
    TODO: Move to use-cases layer, add proper error handling.
    """
    async with get_session() as session:
        try:
            from sqlalchemy.sql import text

            from infrastructure.db.repositories import ZoneRepositoryImpl
            
            zone_repo = ZoneRepositoryImpl(session)
            
            # Create WKT point from coordinates
            point_wkt = f"POINT({lon} {lat})"
            
            # Find nearest zone using PostGIS distance operator
            stmt = text("""
                SELECT id, name, ST_AsText(coordinates) as coords,
                       ST_Distance(coordinates::geography, ST_GeogFromText(:point)) as distance_m
                FROM zones
                ORDER BY coordinates::geography <-> ST_GeogFromText(:point)
                LIMIT 1
            """).bindparams(point=point_wkt)
            
            result = await session.execute(stmt)
            row = result.first()
            
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="No zones found"
                )
            
            # Get zone details
            zone = await zone_repo.get_by_id(row.id)
            if not zone:
                raise HTTPException(
                    status_code=404,
                    detail=f"Zone {row.id} not found"
                )
            
            # Parse zone coordinates from ST_AsText WKT ("POINT(lon lat)")
            coords_match = None
            zone_lat: float | None = None
            zone_lon: float | None = None
            if isinstance(row.coords, str):
                import re as _re
                coords_match = _re.match(
                    r"POINT\(([-\d.]+)\s+([-\d.]+)\)", row.coords
                )
            if coords_match:
                zone_lon = float(coords_match.group(1))
                zone_lat = float(coords_match.group(2))
            else:
                zone_lat = zone.coordinates.latitude
                zone_lon = zone.coordinates.longitude

            return {
                "zone_id": row.id,
                "zone_name": row.name,
                "coordinates": {
                    "latitude": zone_lat,
                    "longitude": zone_lon,
                },
                "distance_meters": float(row.distance_m),
                "zone_details": {
                    "name": zone.name,
                    "coordinates": {
                        "latitude": zone.coordinates.latitude,
                        "longitude": zone.coordinates.longitude,
                    },
                    "upstream_zone_id": zone.upstream_zone_id,
                },
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # TODO(post-demo): Proper error handling
            raise HTTPException(
                status_code=500,
                detail=f"Failed to find nearest zone: {str(e)}"
            ) from e


@router.get("/{zone_id}", response_model=ZoneDetailResponse)
async def get_zone(zone_id: str) -> ZoneDetailResponse:
    """Get detailed information for a specific zone."""
    async with get_session() as session:
        from infrastructure.db.repositories import (
            ManualOverrideRepositoryImpl,
            RiskAssessmentRepositoryImpl,
            SensorReadingRepositoryImpl,
            WeatherSnapshotRepositoryImpl,
            ZoneRepositoryImpl,
            ZoneThresholdsRepositoryImpl,
        )
        from application.use_cases.zones import ZoneUseCases
        
        use_cases = ZoneUseCases(
            zone_repo=ZoneRepositoryImpl(session),
            risk_repo=RiskAssessmentRepositoryImpl(session),
            thresholds_repo=ZoneThresholdsRepositoryImpl(session),
            sensor_repo=SensorReadingRepositoryImpl(session),
            override_repo=ManualOverrideRepositoryImpl(session),
            weather_repo=WeatherSnapshotRepositoryImpl(session),
        )
        
        detail = await use_cases.get_zone_by_id(zone_id)
        
        zone_response = ZoneDetailResponse.from_entities(
            zone=detail.zone,
            latest_assessment=detail.latest_assessment,
            recent_readings=detail.recent_readings,
            risk_history=detail.risk_history,
            thresholds=detail.thresholds,
            recent_rainfall=detail.recent_rainfall,
            latest_sensor_reading=detail.recent_readings[0] if detail.recent_readings else None,
        )
        
        if detail.active_override:
            zone_response.is_manual_override = True
            zone_response.zone.is_manual_override = True
            if zone_response.zone.latest_assessment:
                zone_response.zone.latest_assessment.tier = detail.active_override.threat_level.name
            
        return zone_response


@router.get("/{zone_id}/risk-trend")
async def get_zone_risk_trend(
    zone_id: str,
    window: str = "24h",
) -> list[dict]:
    """Get time-ordered list of risk assessments within the requested window.
    
    Used for dashboard's risk-trend chart.
    
    TODO: Move to use-cases layer, add proper error handling.
    """
    async with get_session() as session:
        try:
            # Import repositories here to avoid circular imports
            from infrastructure.db.repositories import RiskAssessmentRepositoryImpl
            
            risk_repo = RiskAssessmentRepositoryImpl(session)
            
            # Parse window parameter
            if window == "24h":
                hours = 24
            elif window == "48h":
                hours = 48
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid window parameter. Must be '24h' or '48h'."
                )
            
            # Get risk assessments within window
            window_start = datetime.now(UTC) - timedelta(hours=hours)
            assessments = await risk_repo.list_for_zone_in_window(
                zone_id,  # positional argument
                start_time=window_start,  # keyword argument
            )
            
            # Transform to response format
            response = []
            for assessment in assessments:
                response.append({
                    "timestamp": assessment.computed_at,
                    "tier": assessment.tier.name,
                    "probability": assessment.probability,
                })
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            # TODO(post-demo): Proper error handling with DomainError mapping
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch risk trend for zone {zone_id}: {str(e)}"
            ) from e


@router.get("/{zone_id}/rainfall-vs-risk")
async def get_zone_rainfall_vs_risk(
    zone_id: str,
    window: str = "24h",
) -> list[dict]:
    """Get paired time-ordered list of rainfall and risk data within the requested window.
    
    Used for dashboard's rainfall-vs-risk chart.
    
    TODO: Move to use-cases layer, add proper error handling.
    """
    async with get_session() as session:
        try:
            # Import repositories here to avoid circular imports
            from infrastructure.db.repositories import (
                RiskAssessmentRepositoryImpl,
                WeatherSnapshotRepositoryImpl,
            )
            
            risk_repo = RiskAssessmentRepositoryImpl(session)
            weather_repo = WeatherSnapshotRepositoryImpl(session)
            
            # Parse window parameter
            if window == "24h":
                hours = 24
            elif window == "48h":
                hours = 48
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid window parameter. Must be '24h' or '48h'."
                )
            
            window_start = datetime.now(UTC) - timedelta(hours=hours)
            
            # Get risk assessments within window
            risk_assessments = await risk_repo.list_for_zone_in_window(
                zone_id,  # positional argument
                start_time=window_start,
            )
            
            # Get weather snapshots within window
            weather_snapshots = await weather_repo.list_for_zone_in_window(
                zone_id,  # positional argument
                start_time=window_start,
            )
            
            # Build response with aligned data by matching closest weather snapshot
            response = []
            for assessment in risk_assessments:
                rainfall_mm = 0.0
                if weather_snapshots:
                    closest = min(
                        weather_snapshots,
                        key=lambda s: abs((s.fetched_at - assessment.computed_at).total_seconds())
                    )
                    if abs((closest.fetched_at - assessment.computed_at).total_seconds()) <= 7200:
                        rainfall_mm = closest.rainfall.millimetres

                response.append({
                    "timestamp": assessment.computed_at,
                    "rainfall_mm": rainfall_mm,
                    "risk_probability": assessment.probability,
                })
            
            # If no risk assessments but we have weather data, return just weather data
            if not response and weather_snapshots:
                for snapshot in weather_snapshots:
                    response.append({
                        "timestamp": snapshot.fetched_at,
                        "rainfall_mm": snapshot.rainfall.millimetres,
                        "risk_probability": 0.0,  # Default
                    })
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            # TODO(post-demo): Proper error handling with DomainError mapping
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch rainfall vs risk data for zone {zone_id}: {str(e)}"
            ) from e
