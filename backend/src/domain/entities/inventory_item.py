from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import DomainError, InvalidInventoryQuantity


@dataclass
class InventoryItem:
    """A single SKU tracked inside a :class:`ResourceCenter`.

    Quantity is a non-negative integer; we never allow "negative stock" even
    as a transient allocation placeholder — the application layer must
    decrement atomically inside a transaction and raise a domain error if it
    would go below zero. ``center_id`` points at the owning ResourceCenter.
    """

    id: str
    item_name: str
    quantity: int
    center_id: str

    def __post_init__(self) -> None:
        if not self.item_name:
            raise DomainError("InventoryItem.item_name must be non-empty")
        if not self.center_id:
            raise DomainError("InventoryItem.center_id must be non-empty")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            # bool is a subclass of int in Python; block True/False being
            # silently accepted as 1/0.
            raise InvalidInventoryQuantity(
                f"InventoryItem.quantity must be int, got {type(self.quantity).__name__}"
            )
        if self.quantity < 0:
            raise InvalidInventoryQuantity(
                f"InventoryItem.quantity must be >= 0, got {self.quantity!r}"
            )
