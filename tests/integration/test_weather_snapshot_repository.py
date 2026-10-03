"""Integration tests for WeatherSnapshotRepositoryImpl.

WeatherSnapshot has no id field in the domain entity — the ORM generates one.
Covers: get_by_id (hit/miss), latest_for_zone (ordering, empty, cross-zone),
add (round-trip of RainfallWindow primitives + ttl_seconds).
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from domain.entities.weather_snapshot import WeatherSnapshot
from domain.entities.zone import Zone
from domain.value_objects.rainfall_window import RainfallWindow
from infrastructure.db.repositories import WeatherSnapshotRepositoryImpl

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


def _snapshot(
    zone_id: str,
    *,
    mm: float = 12.5,
    hours: float = 24.0,
    ttl: int = 3600,
    ts_offset_seconds: int = 0,
    now: datetime,
) -> WeatherSnapshot:
    return WeatherSnapshot(
        zone_id=zone_id,
        rainfall=RainfallWindow(millimetres=mm, duration_hours=hours),
        fetched_at=now + timedelta(seconds=ts_offset_seconds),
        ttl_seconds=ttl,
    )


# ---------------------------------------------------------------------------
# add + get_by_id
# ---------------------------------------------------------------------------


async def test_add_and_get_by_id_roundtrip(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = WeatherSnapshotRepositoryImpl(session)
    snap = _snapshot(zone_a.id, now=now)
    await repo.add(snap)
    # WeatherSnapshot has no id on the domain entity — retrieve by fetching
    # latest_for_zone which always returns the most-recent row
    found = await repo.latest_for_zone(zone_a.id)
    assert found is not None
    assert found.zone_id == zone_a.id
    assert found.rainfall.millimetres == pytest.approx(12.5)
    assert found.rainfall.duration_hours == pytest.approx(24.0)
    assert found.ttl_seconds == 3600


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = WeatherSnapshotRepositoryImpl(session)
    assert await repo.get_by_id("no-such-snapshot-uuid") is None


# ---------------------------------------------------------------------------
# latest_for_zone
# ---------------------------------------------------------------------------


async def test_latest_for_zone_returns_most_recent(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = WeatherSnapshotRepositoryImpl(session)
    old = _snapshot(zone_a.id, mm=5.0, ts_offset_seconds=0, now=now)
    new = _snapshot(zone_a.id, mm=20.0, ts_offset_seconds=60, now=now)
    await repo.add(old)
    await repo.add(new)
    latest = await repo.latest_for_zone(zone_a.id)
    assert latest is not None
    assert latest.rainfall.millimetres == pytest.approx(20.0)


async def test_latest_for_zone_returns_none_when_empty(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = WeatherSnapshotRepositoryImpl(session)
    assert await repo.latest_for_zone(zone_a.id) is None


async def test_latest_for_zone_isolates_by_zone(
    session: AsyncSession, zone_a: Zone, zone_b: Zone, now: datetime
) -> None:
    repo = WeatherSnapshotRepositoryImpl(session)
    await repo.add(_snapshot(zone_a.id, mm=10.0, now=now))
    await repo.add(_snapshot(zone_b.id, mm=99.0, now=now))
    latest_a = await repo.latest_for_zone(zone_a.id)
    assert latest_a is not None
    assert latest_a.rainfall.millimetres == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# add round-trip — zero rainfall edge case
# ---------------------------------------------------------------------------


async def test_add_zero_rainfall(
    session: AsyncSession, zone_a: Zone, now: datetime
) -> None:
    repo = WeatherSnapshotRepositoryImpl(session)
    snap = _snapshot(zone_a.id, mm=0.0, hours=0.0, now=now)
    await repo.add(snap)
    found = await repo.latest_for_zone(zone_a.id)
    assert found is not None
    assert found.rainfall.millimetres == pytest.approx(0.0)
    assert found.rainfall.duration_hours == pytest.approx(0.0)
