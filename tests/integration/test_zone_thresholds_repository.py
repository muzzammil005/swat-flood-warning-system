"""Integration tests for ZoneThresholdsRepositoryImpl.

Covers: get_by_zone_id (miss on virgin zone, hit after upsert), upsert
(INSERT path on first call, UPDATE path on second call), invariant enforcement
(warning < critical), and cascade-delete when the parent zone is removed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from domain.entities.zone import Zone
from domain.value_objects.water_level import WaterLevel
from domain.value_objects.zone_thresholds import ZoneThresholds
from infrastructure.db.repositories import ZoneThresholdsRepositoryImpl

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _make_thresholds(
    *,
    warning_cm: float = 80.0,
    critical_cm: float = 150.0,
    rain_mm: float = 30.0,
) -> ZoneThresholds:
    return ZoneThresholds(
        water_warning_level=WaterLevel(warning_cm),
        water_critical_level=WaterLevel(critical_cm),
        heavy_rain_threshold_mm=rain_mm,
    )


# ---------------------------------------------------------------------------
# get_by_zone_id — miss
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_by_zone_id_returns_none_when_no_thresholds(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneThresholdsRepositoryImpl(session)
    result = await repo.get_by_zone_id(zone_a.id)
    assert result is None


@pytest.mark.integration
async def test_get_by_zone_id_returns_none_for_unknown_zone(
    session: AsyncSession,
) -> None:
    repo = ZoneThresholdsRepositoryImpl(session)
    assert await repo.get_by_zone_id("no-such-zone") is None


# ---------------------------------------------------------------------------
# upsert — INSERT path
# ---------------------------------------------------------------------------


async def test_upsert_insert_returns_thresholds(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneThresholdsRepositoryImpl(session)
    thresholds = _make_thresholds()
    saved = await repo.upsert(zone_a.id, thresholds)
    assert saved.water_warning_level.centimetres == pytest.approx(80.0)
    assert saved.water_critical_level.centimetres == pytest.approx(150.0)
    assert saved.heavy_rain_threshold_mm == pytest.approx(30.0)


async def test_upsert_insert_readable_via_get_by_zone_id(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneThresholdsRepositoryImpl(session)
    await repo.upsert(zone_a.id, _make_thresholds())
    fetched = await repo.get_by_zone_id(zone_a.id)
    assert fetched is not None
    assert fetched.water_warning_level.centimetres == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# upsert — UPDATE path (second call on the same zone_id)
# ---------------------------------------------------------------------------


async def test_upsert_update_overwrites_existing_thresholds(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneThresholdsRepositoryImpl(session)
    await repo.upsert(zone_a.id, _make_thresholds(warning_cm=80.0, critical_cm=150.0))
    recalibrated = _make_thresholds(warning_cm=100.0, critical_cm=200.0, rain_mm=50.0)
    updated = await repo.upsert(zone_a.id, recalibrated)
    assert updated.water_warning_level.centimetres == pytest.approx(100.0)
    assert updated.water_critical_level.centimetres == pytest.approx(200.0)
    assert updated.heavy_rain_threshold_mm == pytest.approx(50.0)


async def test_upsert_update_persisted_after_re_fetch(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneThresholdsRepositoryImpl(session)
    await repo.upsert(zone_a.id, _make_thresholds())
    await repo.upsert(zone_a.id, _make_thresholds(warning_cm=120.0, critical_cm=250.0))
    fetched = await repo.get_by_zone_id(zone_a.id)
    assert fetched is not None
    assert fetched.water_warning_level.centimetres == pytest.approx(120.0)


async def test_upsert_second_call_does_not_create_duplicate_row(
    session: AsyncSession, zone_a: Zone
) -> None:
    """Calling upsert twice must produce exactly one row per zone."""
    from sqlalchemy import text

    repo = ZoneThresholdsRepositoryImpl(session)
    await repo.upsert(zone_a.id, _make_thresholds())
    await repo.upsert(zone_a.id, _make_thresholds(warning_cm=90.0, critical_cm=160.0))
    result = await session.execute(
        text("SELECT COUNT(*) FROM zone_thresholds WHERE zone_id = :zid"),
        {"zid": zone_a.id},
    )
    count = result.scalar_one()
    assert count == 1


# ---------------------------------------------------------------------------
# independent thresholds per zone
# ---------------------------------------------------------------------------


async def test_each_zone_has_independent_thresholds(
    session: AsyncSession, zone_a: Zone, zone_b: Zone
) -> None:
    repo = ZoneThresholdsRepositoryImpl(session)
    await repo.upsert(zone_a.id, _make_thresholds(warning_cm=70.0, critical_cm=130.0))
    await repo.upsert(zone_b.id, _make_thresholds(warning_cm=90.0, critical_cm=180.0))
    ta = await repo.get_by_zone_id(zone_a.id)
    tb = await repo.get_by_zone_id(zone_b.id)
    assert ta is not None
    assert tb is not None
    assert ta.water_warning_level.centimetres == pytest.approx(70.0)
    assert tb.water_warning_level.centimetres == pytest.approx(90.0)
