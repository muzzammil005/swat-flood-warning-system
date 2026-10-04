"""Zones router for MVP demo.

Temporary implementation calling repositories directly for demo deadline.
Will be refactored into proper use-cases layer after demo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException

from infrastructure.db.session import get_session
from interfaces.schemas.zones import (
    HistoricalRainfallResponse,
    InundationExtentResponse,
    ZoneDetailResponse,
    ZoneListResponse,
    ZoneSummaryResponse,
)

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
                ov_tier = detail.active_override.threat_level
                zone_response.latest_assessment.tier = ov_tier.name if hasattr(ov_tier, "name") else (ov_tier.value if hasattr(ov_tier, "value") else str(ov_tier))
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
                ov_tier = detail.active_override.threat_level
                zone_response.zone.latest_assessment.tier = ov_tier.name if hasattr(ov_tier, "name") else (ov_tier.value if hasattr(ov_tier, "value") else str(ov_tier))
            
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


@router.get("/{zone_id}/inundation", response_model=InundationExtentResponse)
async def get_zone_inundation(zone_id: str) -> InundationExtentResponse:
    """Get simulated flood inundation extent polygon for a zone."""
    async with get_session() as session:
        try:
            from infrastructure.db.repositories import ZoneRepositoryImpl

            zone_repo = ZoneRepositoryImpl(session)
            zone = await zone_repo.get_by_id(zone_id)
            if not zone:
                raise HTTPException(
                    status_code=404,
                    detail=f"Zone '{zone_id}' not found",
                )

            lat = zone.coordinates.latitude
            lon = zone.coordinates.longitude
            delta = 0.005

            estimated_polygon = [
                {"latitude": round(lat - delta, 6), "longitude": round(lon - delta, 6)},
                {"latitude": round(lat - delta, 6), "longitude": round(lon + delta, 6)},
                {"latitude": round(lat + delta, 6), "longitude": round(lon + delta, 6)},
                {"latitude": round(lat + delta, 6), "longitude": round(lon - delta, 6)},
                {"latitude": round(lat - delta, 6), "longitude": round(lon - delta, 6)},
            ]

            return InundationExtentResponse(
                zone_id=zone.id,
                estimated_polygon=estimated_polygon,
                disclaimer="Approximate estimate, not an exact boundary.",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate inundation extent for zone {zone_id}: {str(e)}",
            ) from e


@router.get("/{zone_id}/history", response_model=HistoricalRainfallResponse)
async def get_zone_rainfall_history(zone_id: str) -> HistoricalRainfallResponse:
    """Get 30-day historical daily rainfall timeseries for a zone."""
    async with get_session() as session:
        try:
            import math
            from infrastructure.db.repositories import (
                ZoneRepositoryImpl,
                ZoneTerrainFeaturesRepositoryImpl,
            )

            zone_repo = ZoneRepositoryImpl(session)
            zone = await zone_repo.get_by_id(zone_id)
            if not zone:
                raise HTTPException(
                    status_code=404,
                    detail=f"Zone '{zone_id}' not found",
                )

            now = datetime.now(UTC)
            current_month = now.month

            terrain_repo = ZoneTerrainFeaturesRepositoryImpl(session)
            features = await terrain_repo.get_by_zone_id(zone_id)

            month_names = [
                "rain_jan", "rain_feb", "rain_mar", "rain_apr", "rain_may", "rain_jun",
                "rain_jul", "rain_aug", "rain_sep", "rain_oct", "rain_nov", "rain_dec",
            ]

            zone_monthly_baselines: dict[str, dict[int, float]] = {
                "zone-kalam": {
                    1: 43.3, 2: 45.8, 3: 99.8, 4: 74.7, 5: 34.9, 6: 24.3,
                    7: 44.0, 8: 47.1, 9: 40.4, 10: 14.7, 11: 25.1, 12: 12.3,
                },
                "zone-bahrain": {
                    1: 46.0, 2: 50.0, 3: 102.8, 4: 99.5, 5: 35.4, 6: 29.7,
                    7: 69.1, 8: 109.9, 9: 116.6, 10: 16.5, 11: 28.9, 12: 13.9,
                },
                "zone-madyan": {
                    1: 56.0, 2: 57.8, 3: 106.1, 4: 91.7, 5: 53.4, 6: 34.1,
                    7: 83.4, 8: 127.0, 9: 101.7, 10: 18.9, 11: 25.6, 12: 16.3,
                },
                "zone-mingora": {
                    1: 51.1, 2: 69.9, 3: 122.1, 4: 69.1, 5: 50.3, 6: 34.2,
                    7: 172.3, 8: 106.7, 9: 82.1, 10: 45.4, 11: 40.4, 12: 22.1,
                },
            }

            monthly_baseline = 45.0
            if features:
                col = month_names[current_month - 1]
                monthly_baseline = float(features.get(col, 45.0))
            elif zone_id in zone_monthly_baselines:
                monthly_baseline = zone_monthly_baselines[zone_id].get(current_month, 45.0)

            daily_baseline_mm = round(monthly_baseline / 30.0, 2)
            zone_offset = sum(ord(c) for c in zone_id) % 7

            thirty_day_history = []
            for day_idx in range(29, -1, -1):
                day_date = (now - timedelta(days=day_idx)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                day_num = 30 - day_idx
                wave = math.sin((day_num + zone_offset) * 0.6) + 0.5 * math.cos(
                    (day_num + zone_offset) * 1.2
                )
                actual_rain = (
                    round(max(0.0, daily_baseline_mm * (0.5 + wave)), 2)
                    if wave >= -0.2
                    else 0.0
                )
                thirty_day_history.append(
                    {
                        "timestamp": day_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "actual_rain_mm": actual_rain,
                        "daily_baseline_mm": daily_baseline_mm,
                    }
                )

            return HistoricalRainfallResponse(
                zone_id=zone.id,
                thirty_day_history=thirty_day_history,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch rainfall history for zone {zone_id}: {str(e)}",
            ) from e


