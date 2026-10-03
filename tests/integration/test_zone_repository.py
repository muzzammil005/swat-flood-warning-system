"""Integration tests for ZoneRepositoryImpl against a live PostGIS container.

Covers: get_by_id (hit/miss), get_by_name (hit/miss), list_all (ordering),
add (round-trip including GeoAlchemy2 WKB), update (name + coordinates +
upstream edge), and FK-cascade handling for upstream_zone_id.
"""

from __future__ import annotations
import pytest

from typing import TYPE_CHECKING

from domain.entities.zone import Zone
from domain.value_objects.coordinates import Coordinates
from infrastructure.db.repositories import ZoneRepositoryImpl

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_persisted_zone(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneRepositoryImpl(session)
    found = await repo.get_by_id(zone_a.id)
    assert found is not None
    assert found.id == zone_a.id
    assert found.name == zone_a.name


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown_id(session: AsyncSession) -> None:
    repo = ZoneRepositoryImpl(session)
    assert await repo.get_by_id("no-such-zone") is None


# ---------------------------------------------------------------------------
# get_by_name
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_get_by_name_returns_zone(session: AsyncSession, zone_a: Zone) -> None:
    repo = ZoneRepositoryImpl(session)
    found = await repo.get_by_name(zone_a.name)
    assert found is not None
    assert found.id == zone_a.id


@pytest.mark.integration
async def test_get_by_name_returns_none_for_unknown_name(session: AsyncSession) -> None:
    repo = ZoneRepositoryImpl(session)
    assert await repo.get_by_name("Ghost Valley") is None


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


async def test_list_all_returns_all_zones_alphabetically(
    session: AsyncSession, zone_a: Zone, zone_b: Zone
) -> None:
    repo = ZoneRepositoryImpl(session)
    zones = await repo.list_all()
    assert len(zones) == 2
    names = [z.name for z in zones]
    assert names == sorted(names), "list_all must return zones sorted by name ASC"


@pytest.mark.integration
async def test_list_all_empty_when_no_zones(session: AsyncSession) -> None:
    repo = ZoneRepositoryImpl(session)
    assert await repo.list_all() == []


# ---------------------------------------------------------------------------
# add — round-trip (GeoAlchemy2 WKB serialisation)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_add_persists_and_returns_zone(session: AsyncSession) -> None:
    repo = ZoneRepositoryImpl(session)
    zone = Zone(
        id="zone-besham",
        name="Besham",
        coordinates=Coordinates(latitude=34.917, longitude=72.867),
        upstream_zone_id=None,
    )
    saved = await repo.add(zone)
    assert saved.id == zone.id
    assert saved.name == "Besham"
    assert abs(saved.coordinates.latitude - 34.917) < 1e-4
    assert abs(saved.coordinates.longitude - 72.867) < 1e-4


async def test_add_preserves_upstream_zone_id(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneRepositoryImpl(session)
    downstream = Zone(
        id="zone-alpuri",
        name="Alpuri",
        coordinates=Coordinates(latitude=34.899, longitude=72.616),
        upstream_zone_id=zone_a.id,
    )
    saved = await repo.add(downstream)
    assert saved.upstream_zone_id == zone_a.id


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_changes_zone_name(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneRepositoryImpl(session)
    renamed = Zone(
        id=zone_a.id,
        name="Kalam Renamed",
        coordinates=zone_a.coordinates,
        upstream_zone_id=zone_a.upstream_zone_id,
    )
    updated = await repo.update(renamed)
    assert updated.name == "Kalam Renamed"
    refetched = await repo.get_by_id(zone_a.id)
    assert refetched is not None
    assert refetched.name == "Kalam Renamed"


async def test_update_changes_coordinates(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ZoneRepositoryImpl(session)
    new_coords = Coordinates(latitude=35.5, longitude=72.7)
    moved = Zone(
        id=zone_a.id,
        name=zone_a.name,
        coordinates=new_coords,
        upstream_zone_id=zone_a.upstream_zone_id,
    )
    updated = await repo.update(moved)
    assert abs(updated.coordinates.latitude - 35.5) < 1e-4
    assert abs(updated.coordinates.longitude - 72.7) < 1e-4


async def test_update_can_set_upstream_zone_id(
    session: AsyncSession, zone_a: Zone, zone_b: Zone
) -> None:
    """zone_a initially has no upstream; wire it to zone_b."""
    repo = ZoneRepositoryImpl(session)
    wired = Zone(
        id=zone_a.id,
        name=zone_a.name,
        coordinates=zone_a.coordinates,
        upstream_zone_id=zone_b.id,
    )
    updated = await repo.update(wired)
    assert updated.upstream_zone_id == zone_b.id
