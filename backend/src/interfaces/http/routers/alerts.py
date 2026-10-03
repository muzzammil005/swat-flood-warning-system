"""Alerts router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel

from application.use_cases.alerts import AlertUseCases
from infrastructure.db.repositories import AlertRepositoryImpl
from infrastructure.db.session import get_session
from interfaces.schemas.alerts import AlertListResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertListResponse])
@router.get("/", response_model=list[AlertListResponse])
async def get_alerts() -> list[AlertListResponse]:
    """Get most recent 20 alerts across all zones, newest first."""
    async with get_session() as session:
        alert_repo = AlertRepositoryImpl(session)
        use_cases = AlertUseCases(alert_repo)
        alerts = await use_cases.list_active_alerts(limit=20)
        return [AlertListResponse.from_entity(alert) for alert in alerts]


class BroadcastRequest(BaseModel):
    zone_id: str
    severity: str = "DANGER"
    headline: str
    description: str

@router.post("/broadcast", response_model=AlertListResponse)
async def broadcast_alert(request: BroadcastRequest) -> AlertListResponse:
    """Manually broadcast an emergency alert (MVP)."""
    from domain.entities.alert import Alert
    from domain.value_objects import RiskTier
    
    # Create the domain entity
    alert = Alert(
        zone_id=request.zone_id,
        severity=RiskTier[request.severity],
        certainty="Observed",
        urgency="Immediate",
        headline=request.headline,
        description=request.description,
        sent_at=datetime.now(timezone.utc)
    )
    
    async with get_session() as session:
        alert_repo = AlertRepositoryImpl(session)
        # Using the repository directly for the MVP backdoor
        saved_alert = await alert_repo.add(alert)
        await session.commit()
        return AlertListResponse.from_entity(saved_alert)