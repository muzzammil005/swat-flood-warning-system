from __future__ import annotations

import uuid
from datetime import timedelta

from application.use_cases.zones import ZoneUseCases
from domain.entities.manual_override import ManualOverride
from domain.entities.risk_assessment import RiskAssessment
from domain.entities.zone import Zone
from domain.value_objects.coordinates import Coordinates
from domain.value_objects.risk_tier import RiskTier
from infrastructure.db.repositories import (
    ManualOverrideRepositoryImpl,
    RiskAssessmentRepositoryImpl,
    ZoneRepositoryImpl,
    ZoneThresholdsRepositoryImpl,
    SensorReadingRepositoryImpl,
)

async def test_zone_summary_counts_manual_override_tier(now, session):
    zone_repo = ZoneRepositoryImpl(session)
    risk_repo = RiskAssessmentRepositoryImpl(session)
    override_repo = ManualOverrideRepositoryImpl(session)
    use_case = ZoneUseCases(zone_repo, risk_repo, ZoneThresholdsRepositoryImpl(session), SensorReadingRepositoryImpl(session), override_repo)

    summary_before = await use_case.get_zone_summary()
    zone_id = f"zone-override-summary-{uuid.uuid4()}"

    zone = await zone_repo.add(
        Zone(
            id=zone_id,
            name="Override Summary Test Zone",
            coordinates=Coordinates(latitude=35.1, longitude=72.2),
            upstream_zone_id=None,
        )
    )

    await risk_repo.add(
        RiskAssessment(
            zone_id=zone.id,
            tier=RiskTier.LOW,
            probability=0.25,
            explanation="baseline",
            computed_at=now,
        )
    )
    await override_repo.add(
        ManualOverride(
            id=f"override-{uuid.uuid4()}",
            zone_id=zone.id,
            threat_level=RiskTier.HIGH,
            reason="storm wall breach",
            admin_username="ops-admin",
            timestamp=now + timedelta(minutes=1),
        )
    )

    summary_after = await use_case.get_zone_summary()
    assert summary_after.high == summary_before.high + 1
    assert summary_after.low == summary_before.low


async def test_zone_detail_uses_override_tier(now, session):
    zone_repo = ZoneRepositoryImpl(session)
    risk_repo = RiskAssessmentRepositoryImpl(session)
    override_repo = ManualOverrideRepositoryImpl(session)
    use_case = ZoneUseCases(zone_repo, risk_repo, ZoneThresholdsRepositoryImpl(session), SensorReadingRepositoryImpl(session), override_repo)

    zone_id = f"zone-override-detail-{uuid.uuid4()}"

    zone = await zone_repo.add(
        Zone(
            id=zone_id,
            name="Override Detail Test Zone",
            coordinates=Coordinates(latitude=35.2, longitude=72.3),
            upstream_zone_id=None,
        )
    )

    await risk_repo.add(
        RiskAssessment(
            zone_id=zone.id,
            tier=RiskTier.MEDIUM,
            probability=0.55,
            explanation="rising river",
            computed_at=now,
        )
    )
    await override_repo.add(
        ManualOverride(
            id=f"override-{uuid.uuid4()}",
            zone_id=zone.id,
            threat_level=RiskTier.DANGER,
            reason="flood control escalation",
            admin_username="ops-admin",
            timestamp=now + timedelta(minutes=2),
        )
    )

    detail = await use_case.get_zone_by_id(zone_id)
    assert detail.active_override is not None
    assert detail.active_override.threat_level.name == "DANGER"
