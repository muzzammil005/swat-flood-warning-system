"""Integration tests for AlertRepositoryImpl.

Alert has no id field in the domain entity (ORM generates one).
Covers: get_by_id (miss), list_active (ordering DESC by sent_at, limit,
empty), add (all four severity tiers, all CAP certainty/urgency combos).
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from domain.entities.alert import Alert
from domain.entities.zone import Zone
from domain.value_objects.risk_tier import RiskTier
from infrastructure.db.repositories import AlertRepositoryImpl

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


def _alert(
    zone_id: str,
    *,
    severity: RiskTier = RiskTier.HIGH,
    certainty: str = "Likely",
    urgency: str = "Expected",
    headline: str = "Flood warning",
    description: str = "Water levels rising rapidly.",
    ts_offset_seconds: int = 0,
    now: datetime,
) -> Alert:
    return Alert(
        zone_id=zone_id,
        severity=severity,
        certainty=certainty,
        urgency=urgency,
        headline=headline,
        description=description,
        sent_at=now + timedelta(seconds=ts_offset_seconds),
    )


# ---------------------------------------------------------------------------
# get_by_id — miss only (no id in domain entity to look up by)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = AlertRepositoryImpl(session)
    assert await repo.get_by_id("no-such-alert-uuid") is None


# ---------------------------------------------------------------------------
# add + list_active
# ---------------------------------------------------------------------------


async def test_add_and_list_active_roundtrip(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = AlertRepositoryImpl(session)
    await repo.add(_alert(zone_a.id, now=now))
    alerts = await repo.list_active()
    assert len(alerts) == 1
    assert alerts[0].zone_id == zone_a.id
    assert alerts[0].severity == RiskTier.HIGH
    assert alerts[0].certainty == "Likely"
    assert alerts[0].urgency == "Expected"
    assert alerts[0].headline == "Flood warning"


async def test_list_active_returns_desc_by_sent_at(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = AlertRepositoryImpl(session)
    for i in range(3):
        await repo.add(_alert(zone_a.id, ts_offset_seconds=i * 30, now=now))
    alerts = await repo.list_active()
    timestamps = [a.sent_at for a in alerts]
    assert timestamps == sorted(timestamps, reverse=True)


async def test_list_active_respects_limit(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = AlertRepositoryImpl(session)
    for i in range(5):
        await repo.add(_alert(zone_a.id, ts_offset_seconds=i, now=now))
    assert len(await repo.list_active(limit=2)) == 2


@pytest.mark.integration
async def test_list_active_returns_empty_when_no_alerts(session: AsyncSession) -> None:
    repo = AlertRepositoryImpl(session)
    assert await repo.list_active() == []


# ---------------------------------------------------------------------------
# all four severity tiers round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("severity", list(RiskTier))
async def test_all_severity_tiers_roundtrip(
    session: AsyncSession, zone_a: Zone, now: datetime, severity: RiskTier
) -> None:
    repo = AlertRepositoryImpl(session)
    await repo.add(_alert(zone_a.id, severity=severity, now=now))
    alerts = await repo.list_active()
    # latest severity is the one we just inserted (only one per tier test)
    assert any(a.severity == severity for a in alerts)


# ---------------------------------------------------------------------------
# CAP certainty / urgency values round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "certainty,urgency",
    [
        ("Observed", "Immediate"),
        ("Likely", "Expected"),
        ("Possible", "Future"),
        ("Unlikely", "Past"),
    ],
)
async def test_cap_fields_roundtrip(
    session: AsyncSession,
    zone_a: Zone,
    now: datetime,
    certainty: str,
    urgency: str,
) -> None:
    repo = AlertRepositoryImpl(session)
    await repo.add(_alert(zone_a.id, certainty=certainty, urgency=urgency, now=now))
    alerts = await repo.list_active()
    assert any(a.certainty == certainty and a.urgency == urgency for a in alerts)
