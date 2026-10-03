"""Integration tests for ManualOverrideRepositoryImpl.

Covers: get_by_id (hit/miss), active_for_zone (most recent per zone),
add (round-trip of all four threat_level values), update (overwrites
all mutable fields, reason + admin_username).
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from domain.entities.manual_override import ManualOverride
from domain.entities.zone import Zone
from domain.value_objects.risk_tier import RiskTier
from infrastructure.db.repositories import ManualOverrideRepositoryImpl

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


def _override(
    *,
    id: str,
    zone_id: str,
    threat_level: RiskTier = RiskTier.HIGH,
    reason: str = "Local evacuation order issued",
    admin_username: str = "admin_muzzammil",
    ts_offset_seconds: int = 0,
    now: datetime,
) -> ManualOverride:
    return ManualOverride(
        id=id,
        zone_id=zone_id,
        threat_level=threat_level,
        reason=reason,
        admin_username=admin_username,
        timestamp=now + timedelta(seconds=ts_offset_seconds),
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_override(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = ManualOverrideRepositoryImpl(session)
    await repo.add(_override(id="mo-1", zone_id=zone_a.id, now=now))
    found = await repo.get_by_id("mo-1")
    assert found is not None
    assert found.threat_level == RiskTier.HIGH
    assert found.reason == "Local evacuation order issued"


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = ManualOverrideRepositoryImpl(session)
    assert await repo.get_by_id("no-such-override") is None


# ---------------------------------------------------------------------------
# active_for_zone
# ---------------------------------------------------------------------------


async def test_active_for_zone_returns_latest_by_timestamp(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = ManualOverrideRepositoryImpl(session)
    await repo.add(_override(id="mo-old", zone_id=zone_a.id, threat_level=RiskTier.LOW, ts_offset_seconds=0, now=now))
    await repo.add(_override(id="mo-new", zone_id=zone_a.id, threat_level=RiskTier.DANGER, ts_offset_seconds=60, now=now))
    active = await repo.active_for_zone(zone_a.id)
    assert active is not None
    assert active.id == "mo-new"
    assert active.threat_level == RiskTier.DANGER


async def test_active_for_zone_returns_none_when_empty(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ManualOverrideRepositoryImpl(session)
    assert await repo.active_for_zone(zone_a.id) is None


async def test_active_for_zone_isolates_by_zone(
    session: AsyncSession, zone_a: Zone, zone_b: Zone, now: datetime
) -> None:
    repo = ManualOverrideRepositoryImpl(session)
    await repo.add(_override(id="mo-a", zone_id=zone_a.id, threat_level=RiskTier.LOW, now=now))
    await repo.add(_override(id="mo-b", zone_id=zone_b.id, threat_level=RiskTier.HIGH, now=now))
    active_a = await repo.active_for_zone(zone_a.id)
    active_b = await repo.active_for_zone(zone_b.id)
    assert active_a is not None and active_a.threat_level == RiskTier.LOW
    assert active_b is not None and active_b.threat_level == RiskTier.HIGH


# ---------------------------------------------------------------------------
# add — all four threat_level values round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tier", list(RiskTier))
async def test_all_threat_levels_roundtrip(
    session: AsyncSession, zone_a: Zone, now: datetime, tier: RiskTier
) -> None:
    repo = ManualOverrideRepositoryImpl(session)
    override = _override(id="mo-tier", zone_id=zone_a.id, threat_level=tier, now=now)
    saved = await repo.add(override)
    assert saved.threat_level == tier


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_overwrites_all_mutable_fields(
    session: AsyncSession, zone_a: Zone, zone_b: Zone, now: datetime
) -> None:
    repo = ManualOverrideRepositoryImpl(session)
    original = await repo.add(_override(id="mo-update", zone_id=zone_a.id, now=now))
    updated_override = ManualOverride(
        id=original.id,
        zone_id=zone_b.id,  # zone_id change allowed (FK) - use existing zone_b
        threat_level=RiskTier.DANGER,
        reason="New emergency directive",
        admin_username="admin_ali",
        timestamp=now + timedelta(hours=1),
    )
    updated = await repo.update(updated_override)
    assert updated.zone_id == zone_b.id  # zone_b.id is "zone-mingora"
    assert updated.threat_level == RiskTier.DANGER
    assert updated.reason == "New emergency directive"
    assert updated.admin_username == "admin_ali"
    # fetch again to ensure update persisted
    refetched = await repo.get_by_id("mo-update")
    assert refetched is not None
    assert refetched.threat_level == RiskTier.DANGER


async def test_update_preserves_admin_username_and_reason(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = ManualOverrideRepositoryImpl(session)
    orig = await repo.add(_override(id="mo-reason", zone_id=zone_a.id, reason="first", admin_username="admin1", now=now))
    updated = ManualOverride(
        id=orig.id,
        zone_id=zone_a.id,
        threat_level=RiskTier.HIGH,
        reason="second",
        admin_username="admin2",
        timestamp=now,
    )
    saved = await repo.update(updated)
    assert saved.reason == "second"
    assert saved.admin_username == "admin2"
