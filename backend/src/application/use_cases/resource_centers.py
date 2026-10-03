from dataclasses import dataclass

from application.ports.repositories import InventoryItemRepository, ResourceCenterRepository
from domain.entities.inventory_item import InventoryItem
from domain.entities.resource_center import ResourceCenter


@dataclass(frozen=True)
class ResourceCenterDetail:
    center: ResourceCenter
    inventory: list[InventoryItem]


class ResourceCenterUseCases:
    """Use cases for querying resource centers and their inventory."""

    def __init__(
        self,
        center_repo: ResourceCenterRepository,
        item_repo: InventoryItemRepository,
    ):
        self.center_repo = center_repo
        self.item_repo = item_repo

    async def get_all_centers(self) -> list[ResourceCenterDetail]:
        """Fetch all resource centers with their inventory items."""
        centers = await self.center_repo.list_all()
        result = []
        for center in centers:
            items = await self.item_repo.list_for_center(center.id)
            result.append(ResourceCenterDetail(center=center, inventory=items))
        return result
