import asyncio
import random
import math
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from domain.entities.risk_assessment import RiskAssessment
from domain.entities.weather_snapshot import WeatherSnapshot
from domain.value_objects.risk_tier import RiskTier
from domain.value_objects.rainfall_window import RainfallWindow
from infrastructure.db.session import get_session
from infrastructure.db.repositories import (
    RiskAssessmentRepositoryImpl,
    WeatherSnapshotRepositoryImpl,
    ZoneRepositoryImpl,
)

async def generate_history(session: AsyncSession) -> None:
    print("Generating 12 hours of historical mock data (every 15 minutes)...")
    zone_repo = ZoneRepositoryImpl(session)
    risk_repo = RiskAssessmentRepositoryImpl(session)
    weather_repo = WeatherSnapshotRepositoryImpl(session)
    
    zones = await zone_repo.list_all()
    if not zones:
        print("No zones found! Please run seed_demo_data.py first.")
        return
        
    base_time = datetime.now(UTC)
    
    # Let's generate 48 points (12 hours * 4 points/hour)
    num_points = 48
    interval_minutes = 15
    
    # Clean up old data except the very latest ones
    print("Cleaning up old mock assessments and weather...")
    await session.execute(text("DELETE FROM risk_assessments"))
    await session.execute(text("DELETE FROM weather_snapshots"))
    
    for zone in zones:
        print(f"Generating data for {zone.name}...")
        
        # Base probability offset by zone
        zone_offsets = {
            "zone-kalam": 0.1,
            "zone-bahrain": 0.2,
            "zone-madyan": 0.4,
            "zone-mingora": 0.6,
        }
        base_prob = zone_offsets.get(zone.id, 0.2)
        
        for i in range(num_points, -1, -1):
            time_offset = timedelta(minutes=i * interval_minutes)
            recorded_at = base_time - time_offset
            
            # Create a wave pattern for probability
            # Use sine wave to simulate a storm rolling in and out
            wave = math.sin((num_points - i) / 8.0) * 0.3
            noise = random.uniform(-0.05, 0.05)
            
            prob = base_prob + wave + noise
            prob = max(0.01, min(0.99, prob))
            
            # Determine tier
            if prob >= 0.8:
                tier = RiskTier.DANGER
            elif prob >= 0.6:
                tier = RiskTier.HIGH
            elif prob >= 0.35:
                tier = RiskTier.MEDIUM
            else:
                tier = RiskTier.LOW
                
            # Rainfall trend
            rain_mm = max(0.0, (prob * 60) + random.uniform(-5, 5))
            
            weather = WeatherSnapshot(
                zone_id=zone.id,
                rainfall=RainfallWindow(millimetres=rain_mm, duration_hours=24.0),
                fetched_at=recorded_at,
                ttl_seconds=3600
            )
            await weather_repo.add(weather)
            
            assessment = RiskAssessment(
                zone_id=zone.id,
                tier=tier,
                probability=prob,
                explanation=f"Mock data point for {recorded_at.strftime('%H:%M')}",
                computed_at=recorded_at,
                expected_rain_mm=rain_mm
            )
            await risk_repo.add(assessment)
            
    await session.commit()
    print("Done! Refresh the dashboard.")

async def main():
    async with get_session() as session:
        try:
            await generate_history(session)
        except Exception as e:
            await session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
