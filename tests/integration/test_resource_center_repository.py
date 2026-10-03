"""Integration tests for ResourceCenterRepositoryImpl.

Covers: get_by_id (hit/miss), list_all (ordering ASC), list_for_zone
(filtering), add (round-trip), update (name + location_zone).
"""

from __future__ import annotations
import pytest

from typing import TYPE_CHECKING

from domain.entities.resource_center import ResourceCenter
from domain.entities.zone import Zone
from infrastructure.db.repositories import ResourceCenterRepositoryImpl

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _center(
    *,
    id: str,
    name: str = "Kalam Depot",
    location_zone: str,
) -> ResourceCenter:
    return ResourceCenter(
        id=id,
        name=name,
        location_zone=location_zone,
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_center(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    await repo.add(_center(id="rc-1", location_zone=zone_a.id))
    found = await repo.get_by_id("rc-1")
    assert found is not None
    assert found.name == "Kalam Depot"
    assert found.location_zone == zone_a.id


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    assert await repo.get_by_id("no-such-center") is None


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


async def test_list_all_returns_asc_order_by_name(
    session: AsyncSession, zone_a: Zone, zone_b: Zone
) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    await repo.add(_center(id="rc-z", name="Zebra Depot", location_zone=zone_a.id))
    await repo.add(_center(id="rc-a", name="Alpha Warehouse", location_zone=zone_b.id))
    centers = await repo.list_all()
    names = [c.name for c in centers]
    assert names == sorted(names)


@pytest.mark.integration
async def test_list_all_returns_empty_when_no_centers(session: AsyncSession) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    assert await repo.list_all() == []


# ---------------------------------------------------------------------------
# list_for_zone
# ---------------------------------------------------------------------------


async def test_list_for_zone_filters_by_location_zone(
    session: AsyncSession, zone_a: Zone, zone_b: Zone
) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    await repo.add(_center(id="rc-a1", location_zone=zone_a.id))
    await repo.add(_center(id="rc-a2", location_zone=zone_a.id))
    await repo.add(_center(id="rc-b", location_zone=zone_b.id))
    centers_a = await repo.list_for_zone(zone_a.id)
    assert len(centers_a) == 2
    assert all(c.location_zone == zone_a.id for c in centers_a)


async def test_list_for_zone_empty_for_zone_without_centers(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    assert await repo.list_for_zone(zone_a.id) == []


# ---------------------------------------------------------------------------
# add — round-trip
# ---------------------------------------------------------------------------


async def test_add_roundtrips_name_and_location(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    center = ResourceCenter(
        id="rc-add",
        name="Mingora Emergency Store",
        location_zone=zone_a.id,
    )
    saved = await repo.add(center)
    assert saved.name == "Mingora Emergency Store"
    assert saved.location_zone == zone_a.id


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_changes_name(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    center = await repo.add(_center(id="rc-rename", location_zone=zone_a.id))
    renamed = ResourceCenter(
        id=center.id,
        name="Renamed Depot",
        location_zone=center.location_zone,
    )
    updated = await repo.update(renamed)
    assert updated.name == "Renamed Depot"


async def test_update_changes_location_zone(
    session: AsyncSession, zone_a: Zone, zone_b: Zone
) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    center = await repo.add(_center(id="rc-move", location_zone=zone_a.id))
    moved = ResourceCenter(
        id=center.id,
        name=center.name,
        location_zone=zone_b.id,
    )
    updated = await repo.update(moved)
    assert updated.location_zone == zone_b.id
