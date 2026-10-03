"""Integration tests for SensorReadingRepositoryImpl.

Covers: get_by_id (hit/miss), list_for_zone (ordering DESC, limit, empty,
cross-zone isolation), add (round-trip for both source values).
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from domain.entities.sensor_reading import SensorReading
from domain.entities.zone import Zone
from domain.value_objects.water_level import WaterLevel
from infrastructure.db.repositories import SensorReadingRepositoryImpl

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


def _reading(
    zone_id: str,
    *,
    id: str,
    level_cm: float = 55.0,
    source: str = "real",
    ts_offset_seconds: int = 0,
    now: datetime,
) -> SensorReading:
    return SensorReading(
        id=id,
        zone_id=zone_id,
        water_level=WaterLevel(level_cm),
        timestamp=now + timedelta(seconds=ts_offset_seconds),
        source=source,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_reading(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = SensorReadingRepositoryImpl(session)
    r = _reading(zone_a.id, id="sr-1", now=now)
    await repo.add(r)
    found = await repo.get_by_id("sr-1")
    assert found is not None
    assert found.id == "sr-1"
    assert found.zone_id == zone_a.id
    assert found.water_level.centimetres == pytest.approx(55.0)


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = SensorReadingRepositoryImpl(session)
    assert await repo.get_by_id("no-such-reading") is None


# ---------------------------------------------------------------------------
# add — round-trip
# ---------------------------------------------------------------------------


async def test_add_roundtrips_source_real(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = SensorReadingRepositoryImpl(session)
    r = _reading(zone_a.id, id="sr-real", source="real", now=now)
    saved = await repo.add(r)
    assert saved.source == "real"


async def test_add_roundtrips_source_test(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = SensorReadingRepositoryImpl(session)
    r = _reading(zone_a.id, id="sr-test", source="test", now=now)
    saved = await repo.add(r)
    assert saved.source == "test"


# ---------------------------------------------------------------------------
# list_for_zone
# ---------------------------------------------------------------------------


async def test_list_for_zone_returns_desc_order(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = SensorReadingRepositoryImpl(session)
    for i, offset in enumerate([0, 10, 20]):
        await repo.add(_reading(zone_a.id, id=f"sr-ord-{i}", ts_offset_seconds=offset, now=now))
    readings = await repo.list_for_zone(zone_a.id)
    timestamps = [r.timestamp for r in readings]
    assert timestamps == sorted(timestamps, reverse=True)


async def test_list_for_zone_respects_limit(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = SensorReadingRepositoryImpl(session)
    for i in range(5):
        await repo.add(_reading(zone_a.id, id=f"sr-lim-{i}", ts_offset_seconds=i, now=now))
    results = await repo.list_for_zone(zone_a.id, limit=3)
    assert len(results) == 3


async def test_list_for_zone_returns_empty_for_zone_with_no_readings(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = SensorReadingRepositoryImpl(session)
    assert await repo.list_for_zone(zone_a.id) == []


async def test_list_for_zone_isolates_by_zone(
    session: AsyncSession, zone_a: Zone, zone_b: Zone, now: datetime
) -> None:
    repo = SensorReadingRepositoryImpl(session)
    await repo.add(_reading(zone_a.id, id="sr-za", now=now))
    await repo.add(_reading(zone_b.id, id="sr-zb", now=now))
    results_a = await repo.list_for_zone(zone_a.id)
    assert len(results_a) == 1
    assert results_a[0].id == "sr-za"
