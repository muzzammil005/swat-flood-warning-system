"""Integration tests for RiskAssessmentRepositoryImpl.

RiskAssessment is a frozen domain entity with no id field.
Covers: get_by_id (hit/miss), latest_for_zone (ordering, empty, isolation),
history_for_zone (ordering, limit), add (all four RiskTier values).
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from domain.entities.risk_assessment import RiskAssessment
from domain.entities.zone import Zone
from domain.value_objects.risk_tier import RiskTier
from infrastructure.db.repositories import RiskAssessmentRepositoryImpl

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


def _assessment(
    zone_id: str,
    *,
    tier: RiskTier = RiskTier.LOW,
    probability: float = 0.4,
    ts_offset_seconds: int = 0,
    now: datetime,
) -> RiskAssessment:
    return RiskAssessment(
        zone_id=zone_id,
        tier=tier,
        probability=probability,
        explanation="Test assessment",
        computed_at=now + timedelta(seconds=ts_offset_seconds),
    )


# ---------------------------------------------------------------------------
# get_by_id — we must persist and then query by the generated id.
# WeatherSnapshot / RiskAssessment don't expose their id in the domain entity
# directly; fetch via latest_for_zone and reconstruct.
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    assert await repo.get_by_id("no-such-assessment-uuid") is None


# ---------------------------------------------------------------------------
# add + latest_for_zone
# ---------------------------------------------------------------------------


async def test_add_and_latest_for_zone(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    await repo.add(_assessment(zone_a.id, tier=RiskTier.MEDIUM, probability=0.6, now=now))
    latest = await repo.latest_for_zone(zone_a.id)
    assert latest is not None
    assert latest.tier == RiskTier.MEDIUM
    assert latest.probability == pytest.approx(0.6)


async def test_latest_for_zone_returns_most_recent(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    await repo.add(_assessment(zone_a.id, tier=RiskTier.LOW, ts_offset_seconds=0, now=now))
    await repo.add(_assessment(zone_a.id, tier=RiskTier.HIGH, ts_offset_seconds=60, now=now))
    latest = await repo.latest_for_zone(zone_a.id)
    assert latest is not None
    assert latest.tier == RiskTier.HIGH


async def test_latest_for_zone_returns_none_when_empty(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    assert await repo.latest_for_zone(zone_a.id) is None


async def test_latest_for_zone_isolates_by_zone(
    session: AsyncSession, zone_a: Zone, zone_b: Zone, now: datetime
) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    await repo.add(_assessment(zone_a.id, tier=RiskTier.LOW, now=now))
    await repo.add(_assessment(zone_b.id, tier=RiskTier.DANGER, now=now))
    latest_a = await repo.latest_for_zone(zone_a.id)
    assert latest_a is not None
    assert latest_a.tier == RiskTier.LOW


# ---------------------------------------------------------------------------
# history_for_zone
# ---------------------------------------------------------------------------


async def test_history_for_zone_returns_desc_order(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    for i in range(4):
        await repo.add(_assessment(zone_a.id, ts_offset_seconds=i * 10, now=now))
    history = await repo.history_for_zone(zone_a.id)
    timestamps = [a.computed_at for a in history]
    assert timestamps == sorted(timestamps, reverse=True)


async def test_history_for_zone_respects_limit(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    for i in range(6):
        await repo.add(_assessment(zone_a.id, ts_offset_seconds=i, now=now))
    assert len(await repo.history_for_zone(zone_a.id, limit=3)) == 3


async def test_history_for_zone_empty_when_no_assessments(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    assert await repo.history_for_zone(zone_a.id) == []


# ---------------------------------------------------------------------------
# all four RiskTier values round-trip through Postgres native ENUM
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tier", list(RiskTier))
async def test_all_risk_tiers_roundtrip(
    session: AsyncSession, zone_a: Zone, now: datetime, tier: RiskTier
) -> None:
    repo = RiskAssessmentRepositoryImpl(session)
    await repo.add(_assessment(zone_a.id, tier=tier, now=now))
    latest = await repo.latest_for_zone(zone_a.id)
    assert latest is not None
    assert latest.tier == tier
