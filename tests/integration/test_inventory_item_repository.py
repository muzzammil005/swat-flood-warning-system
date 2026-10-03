"""Integration tests for InventoryItemRepositoryImpl.

Covers: get_by_id (hit/miss), list_for_center (filtering, ordering ASC),
add (round-trip), update (item_name, quantity, center_id).
"""

from __future__ import annotations
import pytest

from typing import TYPE_CHECKING

from domain.entities.inventory_item import InventoryItem
from domain.entities.resource_center import ResourceCenter
from domain.entities.zone import Zone
from infrastructure.db.repositories import (
    InventoryItemRepositoryImpl,
    ResourceCenterRepositoryImpl,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _item(
    *,
    id: str,
    item_name: str = "Sandbags",
    quantity: int = 500,
    center_id: str,
) -> InventoryItem:
    return InventoryItem(
        id=id,
        item_name=item_name,
        quantity=quantity,
        center_id=center_id,
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_item(
    session: AsyncSession, zone_a: Zone
) -> None:
    repo = ResourceCenterRepositoryImpl(session)
    center = await repo.add(ResourceCenter(id="rc-inv", name="Test Depot", location_zone=zone_a.id))
    item_repo = InventoryItemRepositoryImpl(session)
    await item_repo.add(_item(id="inv-1", center_id=center.id))
    found = await item_repo.get_by_id("inv-1")
    assert found is not None
    assert found.item_name == "Sandbags"
    assert found.quantity == 500
    assert found.center_id == center.id


@pytest.mark.integration
async def test_get_by_id_returns_none_for_unknown(session: AsyncSession) -> None:
    repo = InventoryItemRepositoryImpl(session)
    assert await repo.get_by_id("no-such-item") is None


# ---------------------------------------------------------------------------
# list_for_center
# ---------------------------------------------------------------------------


async def test_list_for_center_filters_by_center_id(
    session: AsyncSession, zone_a: Zone
) -> None:
    center_repo = ResourceCenterRepositoryImpl(session)
    c1 = await center_repo.add(ResourceCenter(id="rc-a", name="Depot A", location_zone=zone_a.id))
    c2 = await center_repo.add(ResourceCenter(id="rc-b", name="Depot B", location_zone=zone_a.id))
    item_repo = InventoryItemRepositoryImpl(session)
    await item_repo.add(_item(id="inv-a1", center_id=c1.id))
    await item_repo.add(_item(id="inv-a2", center_id=c1.id))
    await item_repo.add(_item(id="inv-b", center_id=c2.id))
    items_c1 = await item_repo.list_for_center(c1.id)
    assert len(items_c1) == 2
    assert all(i.center_id == c1.id for i in items_c1)


async def test_list_for_center_orders_asc_by_item_name(
    session: AsyncSession, zone_a: Zone
) -> None:
    center_repo = ResourceCenterRepositoryImpl(session)
    center = await center_repo.add(ResourceCenter(id="rc-order", name="Depot", location_zone=zone_a.id))
    item_repo = InventoryItemRepositoryImpl(session)
    await item_repo.add(_item(id="inv-z", item_name="Zinc tablets", center_id=center.id))
    await item_repo.add(_item(id="inv-a", item_name="Ammonium nitrate", center_id=center.id))
    items = await item_repo.list_for_center(center.id)
    names = [i.item_name for i in items]
    assert names == sorted(names)


async def test_list_for_center_empty_when_no_items(
    session: AsyncSession, zone_a: Zone
) -> None:
    center_repo = ResourceCenterRepositoryImpl(session)
    center = await center_repo.add(ResourceCenter(id="rc-empty", name="Empty Depot", location_zone=zone_a.id))
    item_repo = InventoryItemRepositoryImpl(session)
    assert await item_repo.list_for_center(center.id) == []


# ---------------------------------------------------------------------------
# add — round-trip
# ---------------------------------------------------------------------------


async def test_add_roundtrips_all_fields(
    session: AsyncSession, zone_a: Zone
) -> None:
    center_repo = ResourceCenterRepositoryImpl(session)
    center = await center_repo.add(ResourceCenter(id="rc-add", name="Add Depot", location_zone=zone_a.id))
    item_repo = InventoryItemRepositoryImpl(session)
    item = InventoryItem(
        id="inv-full",
        item_name="Life jackets",
        quantity=120,
        center_id=center.id,
    )
    saved = await item_repo.add(item)
    assert saved.item_name == "Life jackets"
    assert saved.quantity == 120
    assert saved.center_id == center.id


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_changes_item_name(
    session: AsyncSession, zone_a: Zone
) -> None:
    center_repo = ResourceCenterRepositoryImpl(session)
    center = await center_repo.add(ResourceCenter(id="rc-update", name="Update Depot", location_zone=zone_a.id))
    item_repo = InventoryItemRepositoryImpl(session)
    item = await item_repo.add(_item(id="inv-name", center_id=center.id))
    renamed = InventoryItem(
        id=item.id,
        item_name="Plywood sheets",
        quantity=item.quantity,
        center_id=item.center_id,
    )
    updated = await item_repo.update(renamed)
    assert updated.item_name == "Plywood sheets"


async def test_update_changes_quantity(
    session: AsyncSession, zone_a: Zone
) -> None:
    center_repo = ResourceCenterRepositoryImpl(session)
    center = await center_repo.add(ResourceCenter(id="rc-qty", name="Qty Depot", location_zone=zone_a.id))
    item_repo = InventoryItemRepositoryImpl(session)
    item = await item_repo.add(_item(id="inv-qty", center_id=center.id, quantity=100))
    restocked = InventoryItem(
        id=item.id,
        item_name=item.item_name,
        quantity=350,
        center_id=item.center_id,
    )
    updated = await item_repo.update(restocked)
    assert updated.quantity == 350


async def test_update_can_move_item_to_different_center(
    session: AsyncSession, zone_a: Zone
) -> None:
    center_repo = ResourceCenterRepositoryImpl(session)
    c1 = await center_repo.add(ResourceCenter(id="rc-orig", name="Origin", location_zone=zone_a.id))
    c2 = await center_repo.add(ResourceCenter(id="rc-dest", name="Destination", location_zone=zone_a.id))
    item_repo = InventoryItemRepositoryImpl(session)
    item = await item_repo.add(_item(id="inv-move", center_id=c1.id))
    moved = InventoryItem(
        id=item.id,
        item_name=item.item_name,
        quantity=item.quantity,
        center_id=c2.id,
    )
    updated = await item_repo.update(moved)
    assert updated.center_id == c2.id
